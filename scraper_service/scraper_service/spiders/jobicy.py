import json
import scrapy
from datetime import datetime
from ..items import JobItem


class JobicySpider(scrapy.Spider):
    """
    Jobicy's free public API (https://jobicy.com/jobs-rss-feed) serves remote
    tech jobs with unusually rich structure: annual salary min/max with
    currency, company logos, seniority levels and employment types — exactly
    the fields our enrichment layer otherwise has to guess.
    """
    name = "jobicy"
    allowed_domains = ["jobicy.com"]

    API_URL = "https://jobicy.com/api/v2/remote-jobs?count=100&industry=dev"

    LEVEL_MAP = {
        'junior': 'Junior',
        'middle': 'Mid-Level',
        'mid': 'Mid-Level',
        'senior': 'Senior',
        'lead': 'Lead',
        'expert': 'Senior',
    }

    TYPE_MAP = {
        'full-time': 'Full-time',
        'part-time': 'Part-time',
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
            self.logger.error("Jobicy API returned invalid JSON")
            return

        for job in data.get('jobs', []):
            url = job.get('url')
            title = job.get('jobTitle')
            if not url or not title:
                continue

            posted_at = datetime.today().date()
            pub_date = job.get('pubDate')
            if pub_date:
                try:
                    posted_at = datetime.fromisoformat(str(pub_date)).date()
                except ValueError:
                    pass

            seniority = None
            level = job.get('jobLevel')
            if isinstance(level, str):
                seniority = self.LEVEL_MAP.get(level.strip().lower())

            employment = None
            job_types = job.get('jobType')
            if isinstance(job_types, str):
                job_types = [job_types]
            for jt in job_types or []:
                employment = self.TYPE_MAP.get(str(jt).strip().lower())
                if employment:
                    break

            logo = job.get('companyLogo') or ""
            if not isinstance(logo, str) or not logo.startswith('http'):
                logo = ""

            def to_int(value):
                try:
                    return int(value) if value else None
                except (TypeError, ValueError):
                    return None

            salary_min = to_int(job.get('annualSalaryMin'))
            salary_max = to_int(job.get('annualSalaryMax'))
            currency = job.get('salaryCurrency') or ("USD" if (salary_min or salary_max) else None)

            yield JobItem(
                title=title,
                company=job.get('companyName') or "Unknown",
                location=job.get('jobGeo') or "Remote",
                url=url,
                posted_at=posted_at,
                description=job.get('jobDescription') or job.get('jobExcerpt') or "",
                source="Jobicy",
                skills=[],
                seniority=seniority,
                salary_min=salary_min,
                salary_max=salary_max,
                currency=currency,
                company_logo=logo,
                employment_type=employment,
                remote_type="Remote",  # Jobicy lists remote jobs only
            )
