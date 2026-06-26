import scrapy
from scrapy import Selector
from datetime import datetime
from ..items import JobItem


class WWRSpider(scrapy.Spider):
    name = "wwr"
    allowed_domains = ["weworkremotely.com"]

    async def start(self):
        yield scrapy.Request(
            "https://weworkremotely.com/remote-jobs.rss",
            callback=self.parse,
            meta={'impersonate': 'chrome110'}
        )

    def parse(self, response):
        # Force XML parsing — scrapy_impersonate returns HtmlResponse,
        # which treats <link> as a void element and loses the URL text.
        sel = Selector(text=response.text, type='xml')
        sel.remove_namespaces()

        for item in sel.xpath('//item'):
            full_title = item.xpath('title/text()').get()
            if not full_title:
                continue

            company = "WeWorkRemotely"
            title = full_title
            if ":" in full_title:
                parts = full_title.split(":", 1)
                company = parts[0].strip()
                title = parts[1].strip()

            pub_date_raw = item.xpath('pubDate/text()').get()
            try:
                posted_at = datetime.strptime(pub_date_raw, "%a, %d %b %Y %H:%M:%S %z").date()
            except Exception:
                posted_at = datetime.today().date()

            url = item.xpath('link/text()').get() or item.xpath('guid/text()').get()
            if not url:
                continue

            description = item.xpath('description/text()').get() or ""
            location = item.xpath('region/text()').get() or "Remote"

            skills_raw = item.xpath('skills/text()').get() or ""
            skills = [s.strip() for s in skills_raw.split(',') if s.strip()] if skills_raw else []

            yield JobItem(
                title=title,
                company=company,
                location=location,
                url=url,
                posted_at=posted_at,
                description=description,
                source="WeWorkRemotely",
                skills=skills,
                salary_min=None,
                salary_max=None,
                currency=None,
            )
