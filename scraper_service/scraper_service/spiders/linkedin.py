import scrapy
from ..utils import parse_relative_date
from ..items import JobItem


class LinkedInSpider(scrapy.Spider):
    name = "linkedin"

    # LinkedIn Guest API usually caps at 1000 results (40 pages * 25 jobs)
    MAX_PAGES = 40

    async def start(self):
        keyword = getattr(self, 'keyword', 'Python')
        location = getattr(self, 'location', 'Europe')

        # Start at offset 0
        first_url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={keyword}&location={location}&start=0"

        yield scrapy.Request(
            url=first_url,
            callback=self.parse_list,
            # CRITICAL: Use impersonate to avoid 429/403 blocks
            meta={
                'impersonate': 'chrome110',
                'keyword': keyword,
                'location': location,
                'page_num': 0
            }
        )

    def parse_list(self, response):
        # 1. Parse the Job Cards
        jobs = response.css("li")
        job_count = len(jobs)

        self.logger.info(f"📄 Page {response.meta['page_num']} loaded. Found {job_count} jobs.")

        for job in jobs:
            title = job.css("h3.base-search-card__title::text").get()
            company = job.css("h4.base-search-card__subtitle a::text").get()
            location = job.css("span.job-search-card__location::text").get()
            raw_url = job.css("a.base-card__full-link::attr(href)").get()
            date_text = job.css('time.job-search-card__listdate::text').get()

            if not title or not raw_url:
                continue

            clean_title = title.strip()
            clean_company = company.strip() if company else "Unknown"
            clean_location = location.strip() if location else "Remote"
            clean_url = raw_url.split('?')[0]
            real_date = parse_relative_date(date_text)

            # --- Create the JobItem ---
            item = JobItem()
            item['title'] = clean_title
            item['company'] = clean_company
            item['location'] = clean_location
            item['url'] = clean_url
            item['source'] = "LinkedIn"
            item['posted_at'] = real_date
            item['skills'] = []
            item['salary_min'] = None
            item['salary_max'] = None
            item['currency'] = None

            # --- Extract Description ---
            try:
                # URL structure: .../view/JOB_ID/...
                if "view/" in raw_url:
                    slug = raw_url.split("view/")[1].split("/")[0].split("?")[0]
                    # Sometimes slug is "123456" or "python-dev-123456"
                    job_id = slug.split('-')[-1]
                else:
                    job_id = None

                if job_id and job_id.isdigit():
                    detail_url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"

                    # Pass the item to the detail parser
                    yield scrapy.Request(
                        url=detail_url,
                        callback=self.parse_detail,
                        meta={'item': item, 'impersonate': 'chrome110'}
                    )
                else:
                    item['description'] = ""
                    yield item

            except (IndexError, ValueError):
                item['description'] = ""
                yield item

        # 2. Pagination Logic (The "Infinite" Scroll)
        current_page = response.meta['page_num']

        # If we found jobs AND we haven't hit the limit, go to next page
        if job_count > 0 and current_page < self.MAX_PAGES:
            next_page = current_page + 1
            next_start = next_page * 25

            keyword = response.meta['keyword']
            location = response.meta['location']
            next_url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={keyword}&location={location}&start={next_start}"

            yield scrapy.Request(
                url=next_url,
                callback=self.parse_list,
                meta={
                    'impersonate': 'chrome110',
                    'keyword': keyword,
                    'location': location,
                    'page_num': next_page
                }
            )

    def parse_detail(self, response):
        item = response.meta['item']

        # Extract Description
        description_html = response.css("div.show-more-less-html__markup").get()
        if description_html:
            # Join all text nodes to get clean text
            text_content = response.css("div.show-more-less-html__markup *::text").getall()
            item['description'] = " ".join(text_content).strip()
        else:
            item['description'] = ""

        yield item