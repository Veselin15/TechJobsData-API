import re
from datetime import date, timedelta
from typing import List, Tuple, Optional, Set

from .constants import (
    TECH_KEYWORDS, NEGATION_PATTERNS, SENIORITY_MAP,
    SALARY_IGNORE_TERMS, SALARY_HINTS, SALARY_MULTIPLIERS
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