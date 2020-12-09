import re
import scrapy
import base64
import pymongo

from urllib.parse import unquote


class AutoyoulaSpider(scrapy.Spider):
    name = 'autoyoula'
    allowed_domains = ['auto.youla.ru']
    start_urls = ['https://auto.youla.ru/']
    css_query = {
        'brands': '.TransportMainFilters_brandsList__2tIkv '
                  '.ColumnItemList_container__5gTrc .ColumnItemList_column__5gjdt a.blackLink'
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db = pymongo.MongoClient()['parse_12'][self.name]

    def parse(self, response):
        for link in response.css(self.css_query['brands']):
            yield response.follow(link.attrib['href'], callback=self.brand_page_parse)

    def brand_page_parse(self, response):
        for page in response.css('.Paginator_block__2XAPy a.Paginator_button__u1e7D'):
            yield response.follow(page.attrib['href'], callback=self.brand_page_parse)

        for item_link in response.css('article.SerpSnippet_snippet__3O1t2 a.SerpSnippet_name__3F7Yu'):
            yield response.follow(item_link.attrib['href'], callback=self.ads_parse)

    def ads_parse(self, response):
        global phone_decoded
        title = response.css('.AdvertCard_advertTitle__1S1Ak::text').get()
        images = [image.attrib['src'] for image in response.css('figure.PhotoGallery_photo__36e_r img')]
        description = response.css('.AdvertCard_descriptionInner__KnuRi::text').get()
        author = self.get_author(response)
        specifications = self.get_specifications(response)

        for item in response.css('script').extract():
            phone_string = re.compile(r"phone%22%2C%22([0-9a-zA-Z]{33}w%3D%3D)%22%2C%22time")
            phone = re.findall(phone_string, item)
            if phone:
                phone_encoded = base64.b64decode(base64.b64decode(unquote(phone[0]).encode('utf-8')))
                phone_decoded = phone_encoded.decode('utf-8')

        print(f'Phone number: {phone_decoded}')

        self.db.insert_one({
            'title': title,
            'images': images,
            'description': description,
            'url': response.url,
            'author': author,
            'phone': phone_decoded,
            'specifications': specifications,
        })

    def get_author(self, response):
        script = response.xpath('//script[contains(text(), "window.transitState =")]/text()').get()
        re_str = re.compile(r"youlaId%22%2C%22([0-9|a-zA-Z]+)%22%2C%22avatar")
        result = re.findall(re_str, script)
        if result:
            author_page = f'https://youla.ru/user/{result[0]}'
        else:
            author_page = None
        print(f'Item page: {response.url}')
        print(f'Author page: {author_page}')
        return author_page

    def get_specifications(self, response):
        spec_result = {itm.css('.AdvertSpecs_label__2JHnS::text').get(): itm.css(
            '.AdvertSpecs_data__xK2Qx::text').get() or itm.css('a::text').get() for itm in
                response.css('.AdvertSpecs_row__ljPcX')}
        print(f'Specification: {spec_result}')
        return spec_result
