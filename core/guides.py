"""
Registry for the Career Guides section.

Guides are hand-written editorial articles shipped as templates (no DB,
no admin) — the point is a body of original, substantial content. To add
one: write templates/core/guides/<slug>.html extending guide_base.html,
then register it here. Order = display order on /guides/.
"""
from datetime import date

GUIDES = [
    {
        'slug': 'how-to-read-a-tech-job-listing',
        'title': 'How to Read a Tech Job Listing Like an Engineer',
        'description': 'Salary ranges, seniority inflation, skill soup and the quiet red flags — a field guide to decoding what job ads actually say.',
        'published': date(2026, 7, 18),
        'minutes': 8,
    },
    {
        'slug': 'remote-hybrid-onsite-what-listings-say',
        'title': 'Remote, Hybrid or On-site: What the Listings Actually Say in 2026',
        'description': 'What thousands of live listings reveal about where tech work happens now, and how to filter for the work model you actually want.',
        'published': date(2026, 7, 18),
        'minutes': 7,
    },
    {
        'slug': 'use-demand-data-to-plan-your-learning',
        'title': 'Stop Guessing What to Learn: Using Job Demand Data to Plan Your Skills',
        'description': 'A practical method for turning skill-demand statistics into a personal learning roadmap, without chasing every hyped framework.',
        'published': date(2026, 7, 18),
        'minutes': 9,
    },
    {
        'slug': 'how-we-clean-thirteen-thousand-job-listings',
        'title': 'How We Clean and Structure 13,000 Job Listings',
        'description': 'The engineering behind TechJobsData: deduplication, salary parsing, seniority detection and the messy reality of job-board data.',
        'published': date(2026, 7, 18),
        'minutes': 10,
    },
    {
        'slug': 'salary-negotiation-with-market-data',
        'title': 'Negotiating Your Salary With Market Data (Not Vibes)',
        'description': 'How to build a defensible salary number from advertised ranges, present it without friction, and handle the counter-offer.',
        'published': date(2026, 7, 18),
        'minutes': 9,
    },
]

GUIDES_BY_SLUG = {g['slug']: g for g in GUIDES}
