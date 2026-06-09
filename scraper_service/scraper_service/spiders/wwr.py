import scrapy
from datetime import datetime
from ..items import JobItem


class WWRSpider(scrapy.Spider):
    name = "wwr"
    allowed_domains = ["weworkremotely.com"]

    async def start(self):
        # We must manually yield the request to attach the browser fingerprint
        yield scrapy.Request(
            "https://weworkremotely.com/remote-jobs.rss",
            callback=self.parse,
            meta={'impersonate': 'chrome110'}  # <--- THIS IS THE FIX
        )

    def parse(self, response):
        # RSS feeds are XML. We iterate over every <item> tag.
        # We need to register the namespace to extract the full content.
        response.selector.register_namespace('content', 'http://purl.org/rss/1.0/modules/content/')

        for item in response.xpath('//item'):
            # 1. Extract Title (Format: "Company: Job Title")
            full_title = item.xpath('title/text()').get()
            company = "WeWorkRemotely"
            title = full_title

            if ":" in full_title:
                parts = full_title.split(":", 1)
                company = parts[0].strip()
                title = parts[1].strip()

            # 2. Extract Date
            pub_date_raw = item.xpath('pubDate/text()').get()
            # Format is usually: "Sat, 11 Jan 2026 09:33:04 +0000"
            try:
                posted_at = datetime.strptime(pub_date_raw, "%a, %d %b %Y %H:%M:%S %z").date()
            except:
                posted_at = datetime.today().date()

            # 3. Extract URL & ID
            url = item.xpath('link/text()').get()
            # We use the URL as a unique ID to prevent duplicates

            # 4. Description (HTML content)
            description = item.xpath('description/text()').get() or ""

            # 5. Yield Item
            yield JobItem(
                title=title,
                company=company,
                location="Remote",  # WWR is 100% remote
                url=url,
                posted_at=posted_at,
                description=description,
                source="WeWorkRemotely",
                skills=[],  # RSS doesn't give skills tags, we rely on search
                salary_min=None,
                salary_max=None,
                currency=None
            )