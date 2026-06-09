import scrapy
from datetime import datetime
from ..items import JobItem

class RemoteOKSpider(scrapy.Spider):
    name = "remoteok"
    allowed_domains = ["remoteok.com"]

    async def start(self):
        # FIX: Use 'impersonate' to avoid 403 Forbidden blocks
        yield scrapy.Request(
            "https://remoteok.com/rss",
            callback=self.parse,
            meta={'impersonate': 'chrome110'}
        )

    def parse(self, response):
        response.selector.register_namespace('content', 'http://purl.org/rss/1.0/modules/content/')

        for item in response.xpath('//item'):
            title = item.xpath('title/text()').get()
            link = item.xpath('link/text()').get()
            pub_date_str = item.xpath('pubDate/text()').get()
            description = item.xpath('description/text()').get()

            # Extract Company from title (Format: "Company: Job")
            company = "RemoteOK"
            if title and ":" in title:
                parts = title.split(":", 1)
                company = parts[0].strip()
                title = parts[1].strip()

            try:
                posted_at = datetime.strptime(pub_date_str, "%a, %d %b %Y %H:%M:%S %z").date()
            except:
                posted_at = datetime.today().date()

            yield JobItem(
                title=title,
                company=company,
                location="Remote",
                url=link,
                posted_at=posted_at,
                description=description,
                source="RemoteOK",
                skills=[],
                salary_min=None,
                salary_max=None,
                currency=None
            )