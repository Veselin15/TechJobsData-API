import json
import scrapy
from datetime import datetime, timezone
from ..items import JobItem
from ..constants import SKILL_ALIASES
from ..utils import CANONICAL_SKILLS


class ArbeitnowSpider(scrapy.Spider):
    """
    Arbeitnow's free job-board API (https://www.arbeitnow.com/api/job-board-api)
    — strong on European tech jobs, includes tags and a remote flag.
    """
    name = "arbeitnow"
    allowed_domains = ["arbeitnow.com"]

    API_URL = "https://www.arbeitnow.com/api/job-board-api"
    MAX_PAGES = 5

    async def start(self):
        yield scrapy.Request(
            self.API_URL,
            callback=self.parse,
            meta={'impersonate': 'chrome110', 'page_num': 1}
        )

    def parse(self, response):
        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            self.logger.error("Arbeitnow API returned invalid JSON")
            return

        for job in data.get('data', []):
            url = job.get('url')
            title = job.get('title')
            if not url or not title:
                continue

            posted_at = datetime.today().date()
            created_ts = job.get('created_at')
            if created_ts:
                try:
                    posted_at = datetime.fromtimestamp(int(created_ts), tz=timezone.utc).date()
                except (ValueError, OSError, OverflowError):
                    pass

            location = job.get('location') or ""
            if job.get('remote'):
                location = f"Remote — {location}" if location else "Remote"

            # job_types is a list like ["Full-time", "Home Office"] — take the
            # first value that maps onto one of our employment labels
            type_map = {'full-time': 'Full-time', 'full time': 'Full-time',
                        'part-time': 'Part-time', 'part time': 'Part-time',
                        'contract': 'Contract', 'freelance': 'Freelance',
                        'internship': 'Internship', 'intern': 'Internship'}
            employment = None
            for jt in job.get('job_types') or []:
                employment = type_map.get(str(jt).strip().lower())
                if employment:
                    break

            yield JobItem(
                title=title,
                company=job.get('company_name') or "Unknown",
                location=location or "Not Specified",
                url=url,
                posted_at=posted_at,
                description=job.get('description') or "",
                source="Arbeitnow",
                # Arbeitnow 'tags' are job-board categories ("Chief
                # Executives", "Directors"), not skills — keep only the ones
                # that resolve to a known tech skill.
                skills=[
                    t for t in (job.get('tags') or [])
                    if isinstance(t, str)
                    and (t.strip().lower() in CANONICAL_SKILLS
                         or t.strip().lower() in SKILL_ALIASES)
                ],
                salary_min=None,
                salary_max=None,
                currency=None,
                employment_type=employment,
                remote_type="Remote" if job.get('remote') else None,
            )

        # Follow pagination (capped, the feed goes very deep)
        page_num = response.meta.get('page_num', 1)
        next_url = (data.get('links') or {}).get('next')
        if next_url and page_num < self.MAX_PAGES:
            yield scrapy.Request(
                next_url,
                callback=self.parse,
                meta={'impersonate': 'chrome110', 'page_num': page_num + 1}
            )
