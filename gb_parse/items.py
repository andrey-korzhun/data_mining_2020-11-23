import scrapy


class GbParseItem(scrapy.Item):
    pass


class HeadHuntersJobItem(scrapy.Item):
    _id = scrapy.Field()
    job_title = scrapy.Field()
    salary = scrapy.Field()
    description = scrapy.Field()
    tags = scrapy.Field()
    employer_url = scrapy.Field()


class HeadHunterCompanyItem(scrapy.Item):
    _id = scrapy.Field()
    company_name = scrapy.Field()
    company_url = scrapy.Field()
    company_desc = scrapy.Field()
    company_fields = scrapy.Field()
