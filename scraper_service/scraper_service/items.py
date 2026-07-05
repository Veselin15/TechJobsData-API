import scrapy

class JobItem(scrapy.Item):
    title = scrapy.Field()
    company = scrapy.Field()
    location = scrapy.Field()
    url = scrapy.Field()
    posted_at = scrapy.Field()
    description = scrapy.Field()
    source = scrapy.Field()
    skills = scrapy.Field()
    seniority = scrapy.Field()
    salary_min = scrapy.Field()
    salary_max = scrapy.Field()
    currency = scrapy.Field()
