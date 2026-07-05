import scrapy
import json
from datetime import datetime
from ..items import JobItem


class TheMuseSpider(scrapy.Spider):
    name = "themuse"
    allowed_domains = ["themuse.com"]

    # Map The Muse's level short_names onto our seniority buckets
    LEVEL_MAP = {
        'internship': 'Junior',
        'entry': 'Junior',
        'mid': 'Mid-Level',
        'senior': 'Senior',
        'management': 'Lead',
    }

    async def start(self):
        # We ask for page 0, descending order (newest first)
        url = "https://www.themuse.com/api/public/jobs?category=Software%20Engineering&page=0&descending=true"

        # FIX: Use 'impersonate' to look like a real browser
        yield scrapy.Request(
            url,
            callback=self.parse,
            meta={'impersonate': 'chrome110'}
        )

    def parse(self, response):
        data = json.loads(response.text)

        # 1. Loop through the results
        for job in data.get('results', []):
            # Parse Date (Format: "2023-10-25T14:30:00Z")
            try:
                date_str = job.get('publication_date', '').split('T')[0]
                posted_at = datetime.strptime(date_str, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                posted_at = datetime.now().date()

            # Parse Location
            locations = [loc.get('name') for loc in job.get('locations', [])]
            location_str = ", ".join(locations) if locations else "Remote"

            # The API provides structured seniority levels — use them instead
            # of guessing from the title later
            seniority = None
            for level in job.get('levels', []):
                seniority = self.LEVEL_MAP.get(level.get('short_name'))
                if seniority:
                    break

            # Create the Job Item
            yield JobItem(
                title=job.get('name'),
                company=job.get('company', {}).get('name'),
                location=location_str,
                url=job.get('refs', {}).get('landing_page'),
                posted_at=posted_at,
                description=job.get('contents'),
                source="TheMuse",
                skills=[],
                seniority=seniority,
                salary_min=None,
                salary_max=None,
                currency=None
            )

        # 2. Pagination
        current_page = data.get('page', 0)
        page_count = data.get('page_count', 0)

        if current_page < page_count - 1:
            next_page = current_page + 1
            next_url = f"https://www.themuse.com/api/public/jobs?category=Software%20Engineering&page={next_page}&descending=true"

            # FIX: Ensure the next page also uses impersonation
            yield scrapy.Request(
                next_url,
                callback=self.parse,
                meta={'impersonate': 'chrome110'}
            )