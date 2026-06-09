import scrapy
import json
import re
from datetime import datetime
from ..items import JobItem
from ..utils import parse_relative_date


class GlassdoorSpider(scrapy.Spider):
    name = "glassdoor"
    allowed_domains = ["glassdoor.com"]

    # Map common locations to Glassdoor 'locId' (Country IDs)
    LOCATION_MAP = {
        'US': '1', 'USA': '1', 'United States': '1',
        'UK': '2', 'United Kingdom': '2',
        'CA': '3', 'Canada': '3',
        'Remote': '0'  # Generic fallback
    }

    def __init__(self, keyword='Python', location='US', *args, **kwargs):
        super(GlassdoorSpider, self).__init__(*args, **kwargs)
        self.keyword = keyword
        self.location_name = location
        self.loc_id = self.LOCATION_MAP.get(location, '1')

    async def start(self):
        """
        STEP 1: Warm-Up on Homepage.
        We pretend to come from Google to establish trust.
        """
        yield scrapy.Request(
            url="https://www.glassdoor.com/",
            callback=self.parse_home,
            meta={'impersonate': 'safari15_5'},
            headers={
                'Referer': 'https://www.google.com/',
                'Upgrade-Insecure-Requests': '1'
            },
            dont_filter=True
        )

    def parse_home(self, response):
        """
        STEP 2: Perform the Search.
        """
        # Build URL: sc.keyword=Python & locId=1
        url = f"https://www.glassdoor.com/Job/jobs.htm?sc.keyword={self.keyword}&locT=N&locId={self.loc_id}"

        yield scrapy.Request(
            url,
            callback=self.parse_search,
            meta={'impersonate': 'safari15_5'},
            headers={
                'Referer': 'https://www.glassdoor.com/',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Fetch-Mode': 'navigate'
            }
        )

    def parse_search(self, response):
        """
        STEP 3: Parse Job Cards.
        """
        # Glassdoor's layout changes often, but 'react-job-listing' or 'job-listing' is common
        job_listings = response.css('li[data-test="jobListing"]')

        if not job_listings:
            # Fallback for alternative layouts
            job_listings = response.css('li.react-job-listing')

        if not job_listings:
            self.logger.warning(f"⚠️ No jobs found on {response.url} (Status: {response.status})")

        for job in job_listings:
            url = job.css('a[data-test="job-link"]::attr(href)').get() or \
                  job.css('a.jobLink::attr(href)').get()

            # Extract posted date text (e.g. "3d" or "24h") from the card
            date_text = job.css('[data-test="job-age"]::text').get()

            if url:
                url = response.urljoin(url)
                yield scrapy.Request(
                    url,
                    callback=self.parse_detail,
                    meta={
                        'listing_url': url,
                        'card_date_text': date_text,
                        'impersonate': 'safari15_5'
                    }
                )

        # --- PAGINATION FIX ---
        # 1. Try the specific data attribute (most reliable when present)
        next_page = response.css('a[data-test="pagination-next"]::attr(href)').get()

        # 2. Fallback: Common 'next' class often used in web design
        if not next_page:
            next_page = response.css('.next a::attr(href)').get()

        # 3. Fallback: Look for any link containing "Next" text or class
        if not next_page:
            next_page = response.xpath(
                '//a[contains(@class, "next") or contains(@aria-label, "Next") or contains(text(), "Next")]/@href').get()

        if next_page:
            yield response.follow(
                next_page,
                callback=self.parse_search,
                meta={'impersonate': 'safari15_5'}
            )

    def parse_detail(self, response):
        job_item = JobItem()
        job_item['url'] = response.meta['listing_url']
        job_item['source'] = "Glassdoor"

        # --- STRATEGY A: JSON-LD (Best Data) ---
        json_ld_script = response.xpath('//script[@type="application/ld+json"]/text()').get()
        data = {}

        if json_ld_script:
            try:
                loaded = json.loads(json_ld_script)
                if isinstance(loaded, list):
                    # Find JobPosting schema
                    data = next((item for item in loaded if item.get('@type') == 'JobPosting'), {})
                else:
                    data = loaded if loaded.get('@type') == 'JobPosting' else {}
            except json.JSONDecodeError:
                pass

        if data:
            job_item['title'] = data.get('title')
            job_item['description'] = data.get('description')
            job_item['company'] = data.get('hiringOrganization', {}).get('name')

            # Location
            addr = data.get('jobLocation', {}).get('address', {})
            if isinstance(addr, dict):
                job_item['location'] = f"{addr.get('addressLocality', '')}, {addr.get('addressRegion', '')}".strip(', ')

            # Date
            date_str = data.get('datePosted')
            if date_str:
                try:
                    job_item['posted_at'] = datetime.strptime(date_str.split('T')[0], "%Y-%m-%d").date()
                except ValueError:
                    pass

        # --- STRATEGY B: HTML Fallback ---
        if not job_item.get('title'):
            job_item['title'] = response.css('[data-test="job-title"]::text').get() or response.css(
                'div.css-17x2pwl::text').get()

        if not job_item.get('company'):
            raw = response.css('[data-test="employer-name"]::text').get()
            job_item['company'] = raw.split('\n')[0].strip() if raw else "Unknown"

        if not job_item.get('description'):
            job_item['description'] = response.css('div#JobDescriptionContainer').get()

        # Defaults
        if not job_item.get('location'): job_item['location'] = self.location_name

        # Date Fallback
        if not job_item.get('posted_at'):
            # Use the "3d" text we grabbed from the search page
            card_date = response.meta.get('card_date_text')
            job_item['posted_at'] = parse_relative_date(card_date) if card_date else datetime.now().date()

        job_item['skills'] = []

        if job_item.get('title'):
            yield job_item