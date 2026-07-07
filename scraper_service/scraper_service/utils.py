import re
from datetime import date, timedelta
from typing import Iterable, List, Tuple, Optional, Set
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from .constants import (
    TECH_KEYWORDS, NEGATION_PATTERNS, SENIORITY_MAP,
    SALARY_IGNORE_TERMS, SALARY_HINTS, SALARY_MULTIPLIERS,
    SKILL_ALIASES, NOISE_TAGS, TITLE_NOISE_PATTERNS,
    HYBRID_PATTERNS, ONSITE_PATTERNS, REMOTE_PATTERNS,
    EMPLOYMENT_PATTERNS, ROLE_CATEGORY_TITLE_RULES, ROLE_CATEGORY_SKILL_HINTS,
    CURRENCY_TO_USD, SUMMARY_BOILERPLATE_PATTERNS,
)

# --- 1. PRE-COMPILE PATTERNS FOR PERFORMANCE ---
# compiling regex once at the module level is much faster than doing it for every job


def _bounded(fragment: str, first_char: str, last_char: str) -> str:
    """
    Wrap a regex fragment in word-boundary lookarounds, but only on the sides
    that start/end with a word character. Plain \\b breaks on keywords with
    punctuation: \\bsr\\.\\b can never match "Sr. Developer" because there is
    no boundary between '.' and the following space.
    """
    prefix = r'(?<!\w)' if re.match(r'\w', first_char) else ''
    suffix = r'(?!\w)' if re.match(r'\w', last_char) else ''
    return prefix + fragment + suffix


# Skills: exact keywords, escaped; boundaries applied only where they make sense
# (so "C++", "C#" and ".NET" still match, and ".NET" matches inside "ASP.NET").
SKILL_PATTERNS = []
for skill in TECH_KEYWORDS:
    lower = skill.lower()
    pattern = _bounded(re.escape(lower), lower[0], lower[-1])
    SKILL_PATTERNS.append((skill, re.compile(pattern)))

NEGATION_REGEXES = [re.compile(p) for p in NEGATION_PATTERNS]

# Seniority: values in SENIORITY_MAP are regex fragments (may contain escapes
# like "sr\."), so boundaries are applied based on their effective edges.
SENIORITY_PATTERNS = {
    level: [
        re.compile(_bounded(kw, kw.lstrip('\\')[0], kw[-1]))
        for kw in kws
    ]
    for level, kws in SENIORITY_MAP.items()
}

# Salary Ignore Terms
SALARY_IGNORE_REGEX = re.compile(r'\b(' + '|'.join(SALARY_IGNORE_TERMS) + r')\b')

# Canonical casing for every known skill, keyed by lowercase form
CANONICAL_SKILLS = {kw.lower(): kw for kw in TECH_KEYWORDS}

TITLE_NOISE_REGEXES = [re.compile(p, re.IGNORECASE) for p in TITLE_NOISE_PATTERNS]
HYBRID_REGEXES = [re.compile(p) for p in HYBRID_PATTERNS]
ONSITE_REGEXES = [re.compile(p) for p in ONSITE_PATTERNS]
REMOTE_REGEXES = [re.compile(p) for p in REMOTE_PATTERNS]
EMPLOYMENT_REGEXES = {
    label: [re.compile(p) for p in patterns]
    for label, patterns in EMPLOYMENT_PATTERNS.items()
}
CATEGORY_TITLE_REGEXES = [
    (category, [re.compile(p) for p in patterns])
    for category, patterns in ROLE_CATEGORY_TITLE_RULES
]
SUMMARY_BOILERPLATE_REGEXES = [
    re.compile(p, re.IGNORECASE) for p in SUMMARY_BOILERPLATE_PATTERNS
]

# Tracking params that make identical jobs look like different URLs
_TRACKING_PARAMS_RE = re.compile(
    r'^(utm_\w+|ref|referer|referrer|source|src|gh_src|lever-source|fbclid|gclid|mc_cid|mc_eid)$',
    re.IGNORECASE,
)


_TAG_RE = re.compile(r'<[^>]+>')
_BLOCK_TAG_RE = re.compile(r'</?(p|div|br|li|ul|ol|h[1-6]|tr|table)[^>]*>', re.IGNORECASE)
_WS_RE = re.compile(r'[ \t]+')
_MULTI_NL_RE = re.compile(r'\n{3,}')


def clean_html_text(raw: Optional[str]) -> str:
    """
    Converts an HTML fragment to readable plain text.
    Sources like RemoteOK, Remotive and Glassdoor return HTML descriptions;
    storing them raw means the site renders escaped tags as visible text.
    """
    if not raw:
        return ""
    import html as html_module
    text = _BLOCK_TAG_RE.sub('\n', raw)
    text = _TAG_RE.sub(' ', text)
    text = html_module.unescape(text)
    text = _WS_RE.sub(' ', text)
    text = '\n'.join(line.strip() for line in text.splitlines())
    text = _MULTI_NL_RE.sub('\n\n', text)
    return text.strip()


def extract_skills(text: str) -> List[str]:
    """
    Extracts tech skills from text, filtering out negated contexts.
    Example: "No Python experience required" -> Python is NOT extracted.
    """
    if not text:
        return []

    text_lower = text.lower()
    found_skills = set()

    for skill_name, pattern in SKILL_PATTERNS:
        # Fast search
        for match in pattern.finditer(text_lower):
            start, end = match.span()

            # Directly negated skill: "no PHP experience", "no PHP knowledge"
            pre = text_lower[max(0, start - 12):start]
            post = text_lower[end:end + 30]
            if re.search(r'\bno\s+$', pre) and \
                    re.match(r'\s*(experience|knowledge|skills?|background)', post):
                continue

            # Context Window: Check 40 chars before/after for negation
            ctx_start = max(0, start - 40)
            ctx_end = min(len(text_lower), end + 40)
            context = text_lower[ctx_start:ctx_end]

            # Check negation
            if not any(neg.search(context) for neg in NEGATION_REGEXES):
                found_skills.add(skill_name)
                # Once found valid, break loop for this specific skill
                # (no need to find the same skill twice)
                break

    return list(found_skills)


def extract_seniority(title: str, description: str) -> str:
    """
    Determines seniority. Title has higher priority than description.
    Includes logic to ignore "Reporting to Senior Manager" type phrases.
    """
    text_title = title.lower() if title else ""
    text_desc = description.lower() if description else ""

    # 1. Title Scan (High Confidence)
    for level, patterns in SENIORITY_PATTERNS.items():
        for pattern in patterns:
            if pattern.search(text_title):
                return level

    # 2. Description Scan (Lower Confidence + Context Check)
    # Exclude phrases indicating a supervisor, not the role itself
    exclusion_pattern = re.compile(r'(report(ing|s)?\s+to|supervised\s+by)\s+[\w\s]*$')

    for level, patterns in SENIORITY_PATTERNS.items():
        for pattern in patterns:
            # Find all matches in description
            for match in pattern.finditer(text_desc):
                # Check context 25 chars before the match
                start = match.start()
                pre_context = text_desc[max(0, start - 25):start]

                # Only accept if NOT preceded by "reporting to"
                if not exclusion_pattern.search(pre_context):
                    return level

    return "Not Specified"


def parse_salary(text: str) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    """
    Robust salary parser. Handles:
    - Ranges: "80-100k", "$120k - $150k"
    - Decimals: "1.5k" -> 1500
    - Rates: "$60 / hour" -> Annualized to ~124k
    - Currencies: $, €, £, etc.
    """
    if not text:
        return None, None, None

    text_lower = text.lower()

    # 1. Currency Detection
    # Currency codes must be whole words: a bare 'eur' substring check would
    # flag every job mentioning "Europe" as EUR.
    currency = "USD"  # Default
    if '€' in text or re.search(r'\beur\b', text_lower):
        currency = "EUR"
    elif '£' in text or re.search(r'\bgbp\b', text_lower):
        currency = "GBP"
    else:
        code_match = re.search(r'\b(bgn|aud|cad|chf|pln|sek|nok|dkk|inr|jpy)\b', text_lower)
        if code_match:
            currency = code_match.group(1).upper()

    # 2. Helper: Determine multiplier (Yearly vs Monthly vs Hourly)
    def get_period_multiplier(match_end_pos):
        # Look ahead 40 chars for "per month", "/hr", etc.
        suffix = text_lower[match_end_pos:match_end_pos + 40]
        for period, patterns in SALARY_MULTIPLIERS.items():
            for pattern in patterns:
                if re.search(pattern, suffix):
                    if period == 'monthly':
                        return 12
                    elif period == 'hourly':
                        return 2080  # 40h * 52w
                    elif period == 'daily':
                        return 260  # 5d * 52w
        return 1  # Default to Yearly

    # 3. Helper: Parse number string
    def parse_num(num_str, suffix_k):
        clean = num_str
        if re.fullmatch(r'\d{1,3}(?:[.,]\d{3})+', clean):
            # Grouped thousands: "100,000" or European "100.000"
            clean = re.sub(r'[.,]', '', clean)
        else:
            clean = clean.replace(',', '')
        try:
            val = float(clean)
            if suffix_k:
                val *= 1000
            return int(val)
        except ValueError:
            return None

    candidates = []

    # Matches "100,000", "100.000" (European), "80000", "1.5"
    NUM = r'\d{1,3}(?:[,.]\d{3})+|\d+(?:\.\d+)?'

    # --- PATTERN A: Ranges (e.g. "80-100k", "80k - 100k", "$80,000 - $120,000") ---
    range_pattern = re.compile(
        rf'([$£€]?\s*(?:{NUM}))\s*([kK])?\s*(?:-|–|—|\bto\b)\s*([$£€]?\s*(?:{NUM}))\s*([kK])?')

    for m in range_pattern.finditer(text_lower):
        raw_n1 = re.sub(r'[$£€\s]', '', m.group(1))  # Clean symbols
        raw_n2 = re.sub(r'[$£€\s]', '', m.group(3))

        k1 = bool(m.group(2))  # First K?
        k2 = bool(m.group(4))  # Second K?

        # Logic: If "80-100k", apply 'k' to both
        if k2 and not k1: k1 = True

        v1 = parse_num(raw_n1, k1)
        v2 = parse_num(raw_n2, k2)

        if v1 and v2:
            if v1 > v2:  # "150k - 120k" — store as a proper range
                v1, v2 = v2, v1
            mult = get_period_multiplier(m.end())
            candidates.append((v1 * mult, v2 * mult))

    # --- PATTERN B: Single Numbers (e.g. "$120k", "5000 / month") ---
    # Only if A didn't find anything or to supplement
    single_pattern = re.compile(rf'([$£€])?\s*({NUM})\s*([kK])?')

    for m in single_pattern.finditer(text_lower):
        start, end = m.span()

        # Ignore if followed by invalid terms (e.g. "250,000 users").
        # But "5,000 per month" is a RATE, not a count — an ignore term
        # directly preceded by "per"/"/"/"a" must not disqualify the number.
        suffix_window = text_lower[end:end + 20]
        ignore_match = SALARY_IGNORE_REGEX.search(suffix_window)
        if ignore_match:
            before_term = suffix_window[:ignore_match.start()]
            if not re.search(r'(\bper|/|\ban?|\beach)\s*$', before_term):
                continue

        raw_val = m.group(2)
        has_k = bool(m.group(3))
        has_curr = bool(m.group(1))

        # Valid salary must have a Currency Symbol OR 'k' OR 'salary' keyword nearby
        window = text_lower[max(0, start - 30):min(len(text_lower), end + 30)]
        is_valid_context = any(h in window for h in SALARY_HINTS) or has_curr or has_k

        if is_valid_context:
            val = parse_num(raw_val, has_k)
            if val:
                mult = get_period_multiplier(end)
                candidates.append((val * mult, val * mult))

    # 4. Selection Logic
    if not candidates:
        return None, None, None

    # Filter sanity (Annualized between 5k and 1M)
    valid_candidates = [
        (mn, mx) for mn, mx in candidates
        if 5000 <= mn <= 1000000
    ]

    if not valid_candidates:
        return None, None, None

    # Pick the best candidate (widest range usually indicates the main salary block)
    best = max(valid_candidates, key=lambda x: x[1])
    return best[0], best[1], currency


def parse_relative_date(text: str) -> date:
    """
    Parses '3 days ago', '1 week ago', 'just now'.
    """
    if not text:
        return date.today()

    text = text.lower().strip()
    today = date.today()

    if any(k in text for k in ['just now', 'today', 'hour', 'minute', 'second']):
        return today

    # Regex to capture specific number and unit
    match = re.search(r'(\d+)\+?\s*(day|week|month)', text)
    if match:
        num = int(match.group(1))
        unit = match.group(2)

        if 'day' in unit:
            return today - timedelta(days=num)
        if 'week' in unit:
            return today - timedelta(weeks=num)
        if 'month' in unit:
            return today - timedelta(days=num * 30)

    return today


# --- ENRICHMENT LAYER -------------------------------------------------------
# Everything below turns a raw scraped listing into structured, comparable
# data. All functions are pure (no Django, no network) so they can run both
# inside the Scrapy pipeline and from the `reprocess_jobs` management command.


def clean_title(title: Optional[str]) -> str:
    """
    Strips recruiter decorations from job titles:
    "Senior Python Dev (m/f/d) - Remote 🚀" -> "Senior Python Dev".
    """
    if not title:
        return ""
    text = title
    for pattern in TITLE_NOISE_REGEXES:
        text = pattern.sub(' ', text)
    # Collapse leftover separators and whitespace
    text = re.sub(r'\s*[|/•·]+\s*$', '', text)
    text = re.sub(r'\s{2,}', ' ', text).strip(' -–—:,')
    return text.strip() or title.strip()


def canonicalize_url(url: Optional[str]) -> str:
    """
    Normalizes a job URL for deduplication: lowercases the host, drops
    fragments and tracking query params, and strips trailing slashes.
    The same posting shared with ?utm_source=... must not create a duplicate.
    """
    if not url:
        return ""
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return url.strip()
    kept_params = [
        (k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not _TRACKING_PARAMS_RE.match(k)
    ]
    path = parts.path.rstrip('/') or '/'
    return urlunsplit((
        parts.scheme.lower() or 'https',
        parts.netloc.lower(),
        path,
        urlencode(kept_params),
        '',
    ))


def normalize_skills(raw_tags: Iterable[str], extracted: Iterable[str]) -> List[str]:
    """
    Merges source-provided tags with our own extraction into one clean,
    canonical list: aliases resolved ("golang" -> "Go"), noise dropped
    ("digital nomad"), casing fixed ("python" -> "Python"), deduplicated.
    Unknown but plausible tags are kept with tidy casing.
    """
    merged = {}

    def add(tag: str, trusted: bool):
        cleaned = tag.strip().strip('.,;')
        if not cleaned or len(cleaned) > 40:
            return
        low = cleaned.lower()
        if low in NOISE_TAGS:
            return
        canonical = SKILL_ALIASES.get(low) or CANONICAL_SKILLS.get(low)
        if canonical is None:
            if not trusted:
                return
            # Unknown source tag: keep it, but tidy the casing
            canonical = cleaned if any(c.isupper() for c in cleaned) else cleaned.title()
        merged[canonical.lower()] = canonical

    for tag in raw_tags or []:
        if isinstance(tag, str):
            add(tag, trusted=True)
    for tag in extracted or []:
        add(tag, trusted=False)

    return sorted(merged.values(), key=str.lower)


def detect_remote_type(title: str, location: str, description: str) -> str:
    """
    Classifies the work model: 'Remote', 'Hybrid', 'On-site' or 'Not Specified'.
    Title and location are trusted more than the description, and hybrid
    beats remote when both appear ("remote 2 days a week" is hybrid).
    """
    strong = f"{title or ''} {location or ''}".lower()
    weak = (description or '').lower()[:4000]

    for source_text in (strong, weak):
        if any(p.search(source_text) for p in HYBRID_REGEXES):
            return "Hybrid"
        is_remote = any(p.search(source_text) for p in REMOTE_REGEXES)
        is_onsite = any(p.search(source_text) for p in ONSITE_REGEXES)
        if is_remote and is_onsite:
            return "Hybrid"
        if is_remote:
            return "Remote"
        if is_onsite:
            return "On-site"
    return "Not Specified"


def detect_employment_type(title: str, description: str) -> str:
    """'Full-time', 'Part-time', 'Contract', 'Freelance', 'Internship' or ''."""
    title_low = (title or '').lower()
    desc_low = (description or '').lower()[:4000]
    for source_text in (title_low, desc_low):
        for label, patterns in EMPLOYMENT_REGEXES.items():
            if any(p.search(source_text) for p in patterns):
                return label
    return ""


def classify_role(title: str, skills: Iterable[str]) -> str:
    """
    Buckets a job into a role category. The title is checked first (ordered
    rules, first match wins); if it is too generic, the skill list votes.
    """
    title_low = (title or '').lower()
    for category, patterns in CATEGORY_TITLE_REGEXES:
        if any(p.search(title_low) for p in patterns):
            return category

    skill_set = set(skills or [])
    if skill_set:
        best_category, best_hits = "", 0
        for category, hints in ROLE_CATEGORY_SKILL_HINTS.items():
            hits = len(skill_set & hints)
            if hits > best_hits:
                best_category, best_hits = category, hits
        if best_hits >= 2:
            return best_category
    return "Other"


def to_usd(amount: Optional[float], currency: Optional[str]) -> Optional[int]:
    """Converts an annual amount to USD using fixed reference rates."""
    if amount is None:
        return None
    rate = CURRENCY_TO_USD.get((currency or 'USD').upper())
    if rate is None:
        return None
    return int(round(amount * rate))


def make_summary(description: str, max_len: int = 260) -> str:
    """
    Builds a card-sized excerpt: skips boilerplate headings ("About us"),
    then takes whole sentences from the first informative paragraph.
    """
    if not description:
        return ""

    for paragraph in description.split('\n'):
        para = paragraph.strip()
        if len(para) < 60:
            continue  # headings, dates, bullets-of-one-word
        if any(p.match(para) for p in SUMMARY_BOILERPLATE_REGEXES):
            continue

        if len(para) <= max_len:
            return para
        # Cut on a sentence boundary where possible, else on a word
        cut = para[:max_len]
        sentence_end = max(cut.rfind('. '), cut.rfind('! '), cut.rfind('? '))
        if sentence_end > 80:
            return cut[:sentence_end + 1]
        return cut[:cut.rfind(' ')].rstrip(',;:') + '…'
    return ""


def compute_quality_score(*, description: str, skills: List[str],
                          salary_min: Optional[int], salary_max: Optional[int],
                          seniority: str, remote_type: str,
                          employment_type: str, company_logo: str,
                          posted_at: Optional[date]) -> int:
    """
    Scores how complete/useful a listing is (0-100). Used to rank listings
    when freshness alone is a tie and to let API users filter thin postings.
    """
    score = 0
    desc_len = len(description or '')
    if desc_len >= 1500:
        score += 25
    elif desc_len >= 400:
        score += 15
    elif desc_len >= 100:
        score += 5

    skill_count = len(skills or [])
    if skill_count >= 5:
        score += 20
    elif skill_count >= 2:
        score += 12
    elif skill_count >= 1:
        score += 5

    if salary_min or salary_max:
        score += 20
    if seniority and seniority != "Not Specified":
        score += 10
    if remote_type and remote_type != "Not Specified":
        score += 5
    if employment_type:
        score += 5
    if company_logo:
        score += 5
    if posted_at and (date.today() - posted_at).days <= 7:
        score += 10

    return min(score, 100)