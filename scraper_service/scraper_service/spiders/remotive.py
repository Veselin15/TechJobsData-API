import json
import scrapy
from datetime import datetime
from ..items import JobItem
from ..utils import parse_salary


class RemotiveSpider(scrapy.Spider):
    """
    Remotive publishes a free public API (https://remotive.com/api/remote-jobs)
    with structured company, tags, seniority hints and salary text.
    """
    name = "remotive"
    allowed_domains = ["remotive.com"]

    API_URL = "https://remotive.com/api/remote-jobs?category=software-dev&limit=400"

    # Remotive's structured job_type values -> our employment labels
    JOB_TYPE_MAP = {
        'full_time': 'Full-time',
        'part_time': 'Part-time',
        'contract': 'Contract',
        'freelance': 'Freelance',
        'internship': 'Internship',
    }

    async def start(self):
        yield scrapy.Request(
            self.API_URL,
            callback=self.parse,
            meta={'impersonate': 'chrome110'}
        )

    def parse(self, response):
        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            self.logger.error("Remotive API returned invalid JSON")
            return

        for job in data.get('jobs', []):
            url = job.get('url')
            title = job.get('title')
            if not url or not title:
                continue

            posted_at = None
            date_str = job.get('publication_date')
            if date_str:
                try:
                    posted_at = datetime.fromisoformat(date_str).date()
                except ValueError:
                    pass
            if posted_at is None:
                posted_at = datetime.today().date()

            # Salary comes as free text like "$90k - $120k" — reuse our parser
            salary_min, salary_max, currency = parse_salary(job.get('salary') or "")

            logo = job.get('company_logo') or job.get('company_logo_url') or ""
            if not isinstance(logo, str) or not logo.startswith('http'):
                logo = ""

            yield JobItem(
                title=title,
                company=job.get('company_name') or "Unknown",
                location=job.get('candidate_required_location') or "Remote",
                url=url,
                posted_at=posted_at,
                description=job.get('description') or "",
                source="Remotive",
                skills=[t for t in (job.get('tags') or []) if isinstance(t, str)],
                salary_min=salary_min,
                salary_max=salary_max,
                currency=currency,
                company_logo=logo,
                employment_type=self.JOB_TYPE_MAP.get(job.get('job_type') or ''),
                remote_type="Remote",  # Remotive lists remote jobs only
            )
