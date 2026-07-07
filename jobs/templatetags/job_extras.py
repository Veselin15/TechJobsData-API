"""Presentation helpers for job listings (salary formatting, avatars, freshness)."""
from datetime import date

from django import template

register = template.Library()

CURRENCY_SYMBOLS = {
    'USD': '$', 'EUR': '€', 'GBP': '£', 'CAD': 'CA$', 'AUD': 'A$',
    'CHF': 'CHF ', 'PLN': 'zł', 'BGN': 'лв', 'SEK': 'kr', 'NOK': 'kr',
    'DKK': 'kr', 'INR': '₹', 'JPY': '¥',
}

# Deterministic avatar palette for companies without a logo
AVATAR_CLASSES = [
    'bg-indigo-500/20 text-indigo-300 border-indigo-500/30',
    'bg-cyan-500/20 text-cyan-300 border-cyan-500/30',
    'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
    'bg-amber-500/20 text-amber-300 border-amber-500/30',
    'bg-pink-500/20 text-pink-300 border-pink-500/30',
    'bg-purple-500/20 text-purple-300 border-purple-500/30',
    'bg-sky-500/20 text-sky-300 border-sky-500/30',
    'bg-rose-500/20 text-rose-300 border-rose-500/30',
]


def _get(job, attr):
    """Field access that works for Job instances AND serialized dicts
    (the API renders the same partial with serializer data)."""
    if isinstance(job, dict):
        return job.get(attr)
    return getattr(job, attr, None)


def _as_date(value):
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return value


def _compact_amount(value):
    """94000 -> '94k'; 1200000 -> '1.2M'; keeps small numbers as-is."""
    if value >= 1_000_000:
        text = f"{value / 1_000_000:.1f}".rstrip('0').rstrip('.')
        return f"{text}M"
    if value >= 1000:
        return f"{round(value / 1000)}k"
    return str(value)


@register.filter
def salary_compact(job):
    """Card-sized salary: '$80k – $120k', '€65k+', 'Up to $90k' or ''."""
    salary_min = _get(job, 'salary_min')
    salary_max = _get(job, 'salary_max')
    if not (salary_min or salary_max):
        return ""
    currency = _get(job, 'currency') or 'USD'
    symbol = CURRENCY_SYMBOLS.get(currency.upper(), f"{currency} ")
    if salary_min and salary_max and salary_min != salary_max:
        return f"{symbol}{_compact_amount(salary_min)} – {symbol}{_compact_amount(salary_max)}"
    if salary_min:
        return f"{symbol}{_compact_amount(salary_min)}+"
    return f"Up to {symbol}{_compact_amount(salary_max)}"


@register.filter
def company_initials(name):
    """'Acme Corp' -> 'AC'; 'stripe' -> 'ST'."""
    if not name:
        return '?'
    words = [w for w in name.split() if w and w[0].isalnum()]
    if len(words) >= 2:
        return (words[0][0] + words[1][0]).upper()
    return name[:2].upper()


@register.filter
def avatar_class(name):
    """Stable color classes for a company-name avatar."""
    return AVATAR_CLASSES[sum(ord(c) for c in (name or '?')) % len(AVATAR_CLASSES)]


@register.filter
def freshness(posted_at):
    """'Today', 'Yesterday', '3d ago', then 'Jun 12'."""
    posted_at = _as_date(posted_at)
    if not posted_at:
        return ""
    days = (date.today() - posted_at).days
    if days <= 0:
        return "Today"
    if days == 1:
        return "Yesterday"
    if days <= 13:
        return f"{days}d ago"
    return posted_at.strftime("%b %d")


@register.filter
def is_new(posted_at):
    """True for jobs posted within the last 2 days."""
    posted_at = _as_date(posted_at)
    return bool(posted_at) and (date.today() - posted_at).days <= 2
