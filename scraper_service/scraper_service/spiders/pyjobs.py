import scrapy
from datetime import date


class RemotePythonSpider(scrapy.Spider):
    name = "pyjobs"
    allowed_domains = ["python.org"]

    async def start(self):
        # FIX: Use 'impersonate' to look like a real browser
        yield scrapy.Request(
            "https://www.python.org/jobs/",
            callback=self.parse,
            meta={'impersonate': 'chrome110'}
        )

    def parse(self, response):
        # Python.org lists jobs in an <ol> with class 'list-recent-jobs'
        for job in response.css("ol.list-recent-jobs li"):
            title_tag = job.css("h2.listing-company a")

            # Extract company name
            company_text = job.css("span.listing-company-name::text").getall()
            company = "".join(company_text).strip().split('\n')[-1].strip()

            # Note: Returning a dict is fine, your pipeline handles it.
            # Ideally use JobItem() here too if you want to be consistent.
            yield {
                'title': title_tag.css("::text").get(),
                'company': company,
                'location': job.css("span.listing-location::text").get(),
                'url': response.urljoin(title_tag.css("::attr(href)").get()),
                'source': "Python.org",
                'posted_at': date.today()
            }