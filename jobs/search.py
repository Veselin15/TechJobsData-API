"""
Search engine shared by the job board (core.views.job_list) and the REST API
(jobs.views.JobListAPI).

The pipeline stores a weighted tsvector per job (title=A, company/skills=B,
description=C — maintained by a Postgres trigger, see migration
0007_search_vector). Query handling layers on top of it:

1. Normalization / synonym expansion — bare tokens are expanded with the
   scraper's alias vocabulary, so "js" finds JavaScript jobs and "k8s" finds
   Kubernetes ones. Quoted phrases, OR and -negation (websearch syntax) are
   preserved untouched.
2. Prefix completion — a token that is a prefix of a known tech term is
   completed ("javascr" -> javascript), which makes search-as-you-type work.
3. Typo correction — if a query returns nothing, tokens are spell-checked
   against the vocabulary ("pyton" -> python) and the corrected query is
   retried; the caller gets a `corrected_query` to display.
4. Trigram fallback — misspelled companies/titles outside the vocabulary
   ("Gogle") are caught with pg_trgm similarity as a last resort.

Every layer returns a `SearchResult` so callers can tell the user what
actually happened instead of showing an unexplained empty page.
"""
import difflib
import re
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Tuple

from django.conf import settings
from django.contrib.postgres.search import (
    SearchHeadline, SearchQuery, SearchRank, TrigramSimilarity,
)
from django.db.models import F, Q, QuerySet, Value
from django.db.models.functions import Greatest

# The scrapy project is not an installed package; reuse its vocabulary the
# same way jobs.management.commands.reprocess_jobs does.
SCRAPER_ROOT = Path(settings.BASE_DIR) / 'scraper_service'
if str(SCRAPER_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRAPER_ROOT))

from scraper_service.constants import SKILL_ALIASES, TECH_KEYWORDS  # noqa: E402

# Role/level words that appear in queries but are not skills. Included in the
# vocabulary so typo correction can fix "pyton develper" completely.
ROLE_WORDS = [
    'developer', 'engineer', 'programmer', 'architect', 'designer', 'manager',
    'analyst', 'scientist', 'consultant', 'administrator', 'specialist',
    'lead', 'senior', 'junior', 'intern', 'internship', 'principal', 'staff',
    'frontend', 'backend', 'fullstack', 'full-stack', 'devops', 'mobile',
    'web', 'data', 'cloud', 'security', 'machine', 'learning', 'software',
    'remote', 'engineering', 'development', 'product', 'project', 'qa',
    'tester', 'testing', 'support', 'marketing', 'sales', 'writer', 'design',
]


@dataclass
class SearchResult:
    """What the search actually did, so the UI can explain itself."""
    queryset: QuerySet
    # The query after synonym expansion, as sent to Postgres (debug/notice)
    effective_query: str = ''
    # Set when the original query found nothing and a corrected/completed
    # variant was used instead: show "Showing results for X".
    corrected_query: Optional[str] = None
    # Set when even correction failed but a close vocabulary term exists:
    # show "Did you mean X?" next to the empty state.
    suggestion: Optional[str] = None
    # 'fts' | 'fuzzy' | 'substring' | 'none' — which layer produced results
    matched_with: str = 'fts'
    # The tsquery that matched (FTS layers only) — feeds ts_headline
    query_obj: Optional[SearchQuery] = None


# Sentinels wrapped around matched terms by ts_headline. Private-use unicode
# so scraped text can never collide with them; the `highlight` template
# filter escapes the text FIRST, then swaps these for real <mark> tags.
HL_START = '\ue000'
HL_STOP = '\ue001'


def annotate_headlines(queryset: QuerySet,
                       query_obj: Optional[SearchQuery]) -> QuerySet:
    """
    Adds `title_hl` (whole title, matches wrapped in sentinels) and
    `snippet_hl` (the description fragments that matched — the "why is this
    result here" line). Call on the final page queryset only; ts_headline
    runs per fetched row.
    """
    if query_obj is None:
        return queryset
    return queryset.annotate(
        title_hl=SearchHeadline(
            'title', query_obj, config='english',
            start_sel=HL_START, stop_sel=HL_STOP, highlight_all=True,
        ),
        snippet_hl=SearchHeadline(
            'description', query_obj, config='english',
            start_sel=HL_START, stop_sel=HL_STOP,
            max_words=32, min_words=20, max_fragments=2,
            fragment_delimiter=' … ',
        ),
    )


# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _vocabulary() -> Tuple[dict, list]:
    """
    Returns (expansions, spell_words).

    expansions: lowercase token/phrase -> canonical replacement to OR in
                ("js" -> "javascript", "ror" -> '"ruby on rails"').
    spell_words: every single-word term correction may map onto.
    """
    expansions = {}
    words = set(w.lower() for w in ROLE_WORDS)

    for alias, canonical in SKILL_ALIASES.items():
        canon_low = canonical.lower()
        if alias == canon_low:
            continue
        # Multi-word canonicals become quoted phrases in websearch syntax
        replacement = f'"{canon_low}"' if ' ' in canon_low else canon_low
        expansions[alias.lower()] = replacement

    for keyword in TECH_KEYWORDS:
        low = keyword.lower()
        for part in re.split(r'[\s/]+', low):
            part = part.strip('.+#')
            if len(part) >= 3:
                words.add(part)
        if ' ' not in low:
            words.add(low.strip('.'))

    for alias in SKILL_ALIASES:
        if ' ' not in alias and len(alias) >= 3:
            words.add(alias)

    return expansions, sorted(words)


def _tokenize(query: str) -> List[str]:
    """Splits into tokens, keeping quoted phrases and -negations intact."""
    return re.findall(r'-?"[^"]*"|\S+', query)


def _is_plain(token: str) -> bool:
    """True for bare words we may rewrite (not phrases/negations/operators)."""
    return not (token.startswith('"') or token.startswith('-')
                or token.upper() == 'OR')


# ---------------------------------------------------------------------------
# Query rewriting layers
# ---------------------------------------------------------------------------

def expand_synonyms(query: str) -> str:
    """
    "js dev" -> "(js OR javascript) dev"; leaves phrases/negations alone.
    Two-word aliases ("node js", "react native") are matched greedily first.
    """
    expansions, _ = _vocabulary()
    tokens = _tokenize(query)
    out: List[str] = []
    i = 0
    while i < len(tokens):
        # Greedy 2-token alias ("node js" -> node.js)
        if i + 1 < len(tokens) and _is_plain(tokens[i]) and _is_plain(tokens[i + 1]):
            pair = f'{tokens[i].lower()} {tokens[i + 1].lower()}'
            if pair in expansions:
                out.append(f'("{pair}" OR {expansions[pair]})')
                i += 2
                continue
        token = tokens[i]
        low = token.lower().strip('.,;')
        if _is_plain(token) and low in expansions:
            out.append(f'({low} OR {expansions[low]})')
        else:
            out.append(token)
        i += 1
    return ' '.join(out)


def complete_prefixes(query: str) -> Optional[str]:
    """
    Completes unfinished tech terms: "javascr" -> "javascript".
    Returns None when nothing could be completed.
    """
    _, words = _vocabulary()
    tokens = _tokenize(query)
    changed = False
    out = []
    for token in tokens:
        low = token.lower().strip('.,;')
        if _is_plain(token) and len(low) >= 3 and low not in words:
            match = next((w for w in words if w.startswith(low)), None)
            if match:
                out.append(match)
                changed = True
                continue
        out.append(token)
    return ' '.join(out) if changed else None


def correct_typos(query: str) -> Optional[str]:
    """
    Spell-checks bare tokens against the tech vocabulary:
    "pyton develper" -> "python developer". Returns None if nothing changed.
    """
    _, words = _vocabulary()
    tokens = _tokenize(query)
    changed = False
    out = []
    for token in tokens:
        low = token.lower().strip('.,;')
        if _is_plain(token) and len(low) >= 3 and low not in words:
            close = difflib.get_close_matches(low, words, n=1, cutoff=0.75)
            if close:
                out.append(close[0])
                changed = True
                continue
        out.append(token)
    return ' '.join(out) if changed else None


# ---------------------------------------------------------------------------
# The search itself
# ---------------------------------------------------------------------------

# Skill names that are also everyday English words. Searched alone, they must
# only match title/company/skills (tsvector weights A/B) — otherwise "go"
# matches the verb "go" in every third job description.
AMBIGUOUS_SKILLS = {
    'go', 'r', 'c', 'rust', 'dart', 'shell', 'ray', 'spark', 'chef',
    'puppet', 'express', 'bun', 'unity',
}

_SAFE_LEXEME = re.compile(r'^[a-z0-9+#.\-]+$')


def _single_token_query(raw_query: str) -> Optional[SearchQuery]:
    """
    For a single-token search of an ambiguous skill ("go", "golang", "r"),
    builds a raw tsquery restricted to weights A/B. Returns None when the
    normal websearch path should be used.
    """
    tokens = _tokenize(raw_query)
    if len(tokens) != 1 or not _is_plain(tokens[0]):
        return None
    token = tokens[0].lower().strip('.,;')
    expansions, _ = _vocabulary()
    canonical = expansions.get(token, token).strip('"')
    if canonical not in AMBIGUOUS_SKILLS:
        return None
    if not (_SAFE_LEXEME.match(token) and _SAFE_LEXEME.match(canonical)):
        return None
    raw = f'{canonical}:AB' if token == canonical else f'{token} | {canonical}:AB'
    return SearchQuery(raw, search_type='raw', config='english')


def _fts(queryset: QuerySet, query_text: str,
         prebuilt: Optional[SearchQuery] = None):
    """Index-backed full-text search on the stored weighted vector.
    Returns (queryset, query_obj) so callers can build headlines later."""
    query = prebuilt or SearchQuery(query_text, search_type='websearch',
                                    config='english')
    matched = queryset.filter(search_vector=query).annotate(
        rank=SearchRank(F('search_vector'), query),
    )
    return matched, query


def _fuzzy(queryset: QuerySet, raw_query: str) -> QuerySet:
    """pg_trgm similarity on title/company for out-of-vocabulary queries."""
    return queryset.annotate(
        rank=Greatest(
            TrigramSimilarity('title', raw_query),
            TrigramSimilarity('company', raw_query),
        )
    ).filter(rank__gt=0.25)


def _substring(queryset: QuerySet, raw_query: str) -> QuerySet:
    """Last-resort substring match (original behavior, minus the Java bug)."""
    return queryset.filter(
        Q(title__icontains=raw_query) | Q(company__icontains=raw_query)
    ).annotate(rank=Value(0.0))


def search_jobs(queryset: QuerySet, raw_query: str) -> SearchResult:
    """
    Runs the layered search over `queryset` (which may already carry
    non-search filters). The returned queryset is annotated with `rank`
    but NOT ordered — callers pick the ordering (relevance = '-rank').
    """
    raw_query = (raw_query or '').strip()[:120]
    if not raw_query:
        return SearchResult(queryset=queryset, matched_with='none')

    # Ambiguous single skills ("go", "golang", "r") get a weight-restricted
    # query BEFORE synonym expansion — the expanded form would match the
    # everyday English word all over job descriptions.
    special = _single_token_query(raw_query)
    if special is not None:
        results, query_obj = _fts(queryset, raw_query, prebuilt=special)
        if results.exists():
            return SearchResult(queryset=results, effective_query=raw_query,
                                query_obj=query_obj)

    expanded = expand_synonyms(raw_query)

    results, query_obj = _fts(queryset, expanded)
    if results.exists():
        return SearchResult(queryset=results, effective_query=expanded,
                            query_obj=query_obj)

    # Unfinished last word while typing: "javasc" -> "javascript"
    completed = complete_prefixes(raw_query)
    if completed:
        completed_expanded = expand_synonyms(completed)
        results, query_obj = _fts(queryset, completed_expanded)
        if results.exists():
            return SearchResult(
                queryset=results,
                effective_query=completed_expanded,
                corrected_query=completed,
                query_obj=query_obj,
            )

    # Typos: "pyton" -> "python"
    corrected = correct_typos(raw_query)
    if corrected:
        corrected_expanded = expand_synonyms(corrected)
        results, query_obj = _fts(queryset, corrected_expanded)
        if results.exists():
            return SearchResult(
                queryset=results,
                effective_query=corrected_expanded,
                corrected_query=corrected,
                query_obj=query_obj,
            )

    # Names outside the vocabulary ("Gogle", "Datadgo")
    results = _fuzzy(queryset, raw_query)
    if results.exists():
        return SearchResult(queryset=results, matched_with='fuzzy',
                            effective_query=raw_query)

    results = _substring(queryset, raw_query)
    if results.exists():
        return SearchResult(queryset=results, matched_with='substring',
                            effective_query=raw_query)

    return SearchResult(
        queryset=queryset.none().annotate(rank=Value(0.0)),
        matched_with='none',
        effective_query=expanded,
        suggestion=corrected,
    )
