"""
Re-runs the scraper enrichment layer over jobs already in the database.

The pipeline enriches jobs at scrape time; this command backfills the same
enrichment (clean titles, canonical skills, remote/employment/category,
summaries, quality scores, USD salaries) for rows scraped before the
enrichment layer existed — no rescrape needed.

Usage:
    python manage.py reprocess_jobs
    python manage.py reprocess_jobs --batch-size 200
"""
import sys
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from jobs.models import Job

# Make the scrapy project importable from Django (it is not installed as a
# package; the pipeline normally runs with the scraper root as cwd)
SCRAPER_ROOT = Path(settings.BASE_DIR) / 'scraper_service'
if str(SCRAPER_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRAPER_ROOT))

from scraper_service.utils import (  # noqa: E402
    clean_html_text, clean_title, extract_skills, extract_seniority,
    normalize_skills, detect_remote_type, detect_employment_type,
    classify_role, to_usd, make_summary, compute_quality_score,
)

UPDATE_FIELDS = [
    'title', 'description', 'skills', 'seniority', 'company_logo',
    'remote_type', 'employment_type', 'category', 'summary',
    'quality_score', 'salary_min_usd', 'salary_max_usd',
]


class Command(BaseCommand):
    help = "Re-run scraper enrichment (skills, categories, summaries, USD salaries...) over existing jobs."

    def add_arguments(self, parser):
        parser.add_argument('--batch-size', type=int, default=500,
                            help='Rows per bulk_update batch (default 500).')

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        total = Job.objects.count()
        self.stdout.write(f"Reprocessing {total} jobs...")

        processed = 0
        batch = []
        for job in Job.objects.all().iterator(chunk_size=batch_size):
            self.enrich(job)
            batch.append(job)
            if len(batch) >= batch_size:
                Job.objects.bulk_update(batch, UPDATE_FIELDS)
                processed += len(batch)
                batch = []
                self.stdout.write(f"  {processed}/{total}")

        if batch:
            Job.objects.bulk_update(batch, UPDATE_FIELDS)
            processed += len(batch)

        self.stdout.write(self.style.SUCCESS(f"Done. {processed} jobs re-enriched."))

    @staticmethod
    def enrich(job):
        description = job.description or ""
        if '<' in description and '>' in description:
            description = clean_html_text(description)

        title = clean_title(job.title) or job.title
        text_to_scan = f"{title} {job.company} {description}"

        skills = normalize_skills(job.skills or [], extract_skills(text_to_scan))

        seniority = job.seniority
        if not seniority or seniority == "Not Specified":
            seniority = extract_seniority(title, description)

        remote_type = detect_remote_type(title, job.location, description)
        employment_type = detect_employment_type(title, description)

        job.title = title[:500]
        job.description = description
        job.skills = skills
        job.seniority = seniority[:50]
        job.remote_type = remote_type[:20]
        job.employment_type = employment_type[:20]
        job.category = classify_role(title, skills)[:40]
        job.summary = make_summary(description)[:300]
        job.salary_min_usd = to_usd(job.salary_min, job.currency)
        job.salary_max_usd = to_usd(job.salary_max, job.currency)
        job.quality_score = compute_quality_score(
            description=description,
            skills=skills,
            salary_min=job.salary_min,
            salary_max=job.salary_max,
            seniority=seniority,
            remote_type=remote_type,
            employment_type=employment_type,
            company_logo=job.company_logo or "",
            posted_at=job.posted_at,
        )
