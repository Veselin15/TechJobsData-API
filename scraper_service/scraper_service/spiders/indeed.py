import scrapy
import re
from urllib.parse import urlencode
from ..items import JobItem
from datetime import datetime


class IndeedSpider(scrapy.Spider):
    name = "indeed"
    allowed_domains = ["indeed.com"]

    def __init__(self, keyword='Python', location='Remote', *args, **kwargs):
        super(IndeedSpider, self).__init__(*args, **kwargs)
        self.keyword = keyword
        self.location = location

    async def start(self):
        # MIMIC AN ANDROID PHONE
        # Mobile endpoints often have weaker anti-bot protections
        params = {
            'q': self.keyword,
            'l': self.location,
            'sort': 'date',
            'limit': 50
        }
        url = f"https://www.indeed.com/m/jobs?{urlencode(params)}"

        yield scrapy.Request(
            url=url,
            callback=self.parse_mobile,
            meta={'impersonate': 'chrome100'},  # Standard Android fingerprint
            headers={
                'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Mobile Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Referer': 'https://www.indeed.com/m/',
                'Sec-Fetch-Site': 'same-origin',
                'Upgrade-Insecure-Requests': '1'
            }
        )

    def parse_mobile(self, response):
        # Parse the Mobile Site Layout (Simpler HTML)
        job_cards = response.css('.job_seen_beacon') or response.css('div.job_seen_beacon')

        if not job_cards:
            # Try fallback selector for mobile
            job_cards = response.css('ul#mosaic-provider-jobcards > li')

        self.logger.info(f"📱 Mobile Scrape: Found {len(job_cards)} cards on {response.url}")

        for card in job_cards:
            # Extract JK
            href = card.css('a::attr(href)').get()
            jk = None
            if href:
                jk_match = re.search(r'jk=([a-zA-Z0-9]+)', href)
                if jk_match:
                    jk = jk_match.group(1)

            if jk:
                # Go to the CLEAN desktop view for details (easier to parse)
                job_url = f"https://www.indeed.com/viewjob?jk={jk}"
                yield scrapy.Request(
                    job_url,
                    callback=self.parse_detail,
                    meta={'impersonate': 'chrome100'}
                )

    def parse_detail(self, response):
        job_item = JobItem()
        job_item['url'] = response.meta.get('listing_url', response.url)
        job_item['source'] = "Indeed"

        # HTML Extraction
        job_item['title'] = (response.css('h1.jobsearch-JobInfoHeader-title span::text').get() or
                             response.css('h1::text').get() or "Unknown Title")

        job_item['company'] = (response.css('div[data-company-name="true"] a::text').get() or
                               response.css('div.jobsearch-CompanyInfoContainer a::text').get() or "Unknown Company")

        job_item['location'] = self.location
        job_item['description'] = response.css('div#jobDescriptionText').get()
        job_item['posted_at'] = datetime.now().date()
        job_item['skills'] = []

        if job_item['title'] != "Unknown Title":
            yield job_item