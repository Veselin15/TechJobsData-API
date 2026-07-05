import scrapy
from datetime import date, datetime
from ..items import JobItem


class RemotePythonSpider(scrapy.Spider):
    name = "pyjobs"
    allowed_domains = ["python.org"]

    async def start(self):
        yield scrapy.Request(
            "https://www.python.org/jobs/",
            callback=self.parse,
            meta={'impersonate': 'chrome110'}
        )

    def parse(self, response):
        # Python.org lists jobs in an <ol> with class 'list-recent-jobs'
        for job in response.css("ol.list-recent-jobs li"):
            title_tag = job.css("h2.listing-company a")
            title = title_tag.css("::text").get()
            href = title_tag.css("::attr(href)").get()
            if not title or not href:
                continue

            # Extract company name
            company_text = job.css("span.listing-company-name::text").getall()
            company = "".join(company_text).strip().split('\n')[-1].strip()

            # Listing shows the posted date, e.g. "05 July 2026"
            posted_at = date.today()
            date_text = (job.css("span.listing-posted time::attr(datetime)").get()
                         or job.css("span.listing-posted time::text").get())
            if date_text:
                for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d", "%d %B %Y"):
                    try:
                        posted_at = datetime.strptime(date_text.strip(), fmt).date()
                        break
                    except ValueError:
                        continue

            item = JobItem(
                title=title.strip(),
                company=company or "Unknown",
                location=job.css("span.listing-location a::text").get()
                         or job.css("span.listing-location::text").get()
                         or "Not Specified",
                url=response.urljoin(href),
                posted_at=posted_at,
                description="",
                source="Python.org",
                skills=[],
                salary_min=None,
                salary_max=None,
                currency=None,
            )

            # Follow the detail page to get the full description
            # (enables skill/salary/seniority extraction in the pipeline)
            yield scrapy.Request(
                response.urljoin(href),
                callback=self.parse_detail,
                meta={'item': item, 'impersonate': 'chrome110'},
            )

    def parse_detail(self, response):
        item = response.meta['item']
        text_parts = response.css("div.job-description *::text").getall()
        item['description'] = " ".join(t.strip() for t in text_parts if t.strip())
        yield item
