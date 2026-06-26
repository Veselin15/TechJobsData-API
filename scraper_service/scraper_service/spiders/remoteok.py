import scrapy
from scrapy import Selector
from datetime import datetime
from ..items import JobItem


class RemoteOKSpider(scrapy.Spider):
    name = "remoteok"
    allowed_domains = ["remoteok.com"]

    async def start(self):
        yield scrapy.Request(
            "https://remoteok.com/rss",
            callback=self.parse,
            meta={'impersonate': 'chrome110'}
        )

    def parse(self, response):
        if response.status == 403:
            self.logger.warning("RemoteOK returned 403 — site is blocking scrapers")
            return

        # Force XML parsing for RSS feeds
        sel = Selector(text=response.text, type='xml')
        sel.remove_namespaces()

        for item in sel.xpath('//item'):
            title = item.xpath('title/text()').get()
            link = item.xpath('link/text()').get() or item.xpath('guid/text()').get()
            pub_date_str = item.xpath('pubDate/text()').get()
            description = item.xpath('description/text()').get()

            if not title or not link:
                continue

            company = "RemoteOK"
            if ":" in title:
                parts = title.split(":", 1)
                company = parts[0].strip()
                title = parts[1].strip()

            try:
                posted_at = datetime.strptime(pub_date_str, "%a, %d %b %Y %H:%M:%S %z").date()
            except Exception:
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
                currency=None,
            )
