import scrapy
import json
import datetime as dt
from ..items import InstagramPost, InstagramTag


class InstagramSpider(scrapy.Spider):
    name = 'instagram'
    allowed_domains = ['www.instagram.com']
    login_url = 'https://www.instagram.com/accounts/login/ajax/'
    graphql_url = '/graphql/query/'
    start_urls = ['https://www.instagram.com/']
    csrf_token = ''
    checked_tags = []
    query = {
        'posts': '56a7068fea504063273cc2120ffd54f3',
        'tags': "9b498c08113f1e09617a1703c22b2f32",
    }

    def __init__(self, login, password, start_tags: list, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.start_tags = [f'/explore/tags/{tag}/' for tag in start_tags]
        self.start_tags = [f'/explore/tags/{tag}/?__a=1' for tag in start_tags]
        self.login = login
        self.password = password

    @staticmethod
    def script_data(response) -> dict:
        return json.loads(response.xpath('//script[contains(text(),"window._sharedData")]/text()').get().replace(
            'window._sharedData = ', '').rstrip(';'))

    def parse(self, response, **kwargs):
        # авторизуемся
        try:
            data = self.script_data(response)
            yield scrapy.FormRequest(
                self.login_url,
                method='POST',
                callback=self.parse,
                formdata={
                    'username': self.login,
                    'enc_password': self.password
                },
                headers={
                    'X-CSRFToken': data['config']['csrf_token']
                }
            )
        except AttributeError:
            data = response.json()
            if data['authenticated']:
                for tag in self.start_tags:
                    yield response.follow(tag, callback=self.json_parse)

    def json_parse(self, response):
        js_data = response.json()
        end_cursor = js_data['graphql']['hashtag']['edge_hashtag_to_media']['page_info']['end_cursor']

        tag = js_data["graphql"]["hashtag"]
        tag_name = tag['name']
        if tag_name not in self.checked_tags:
            self.checked_tags.append(tag_name)
            yield InstagramTag(
                date_parse=dt.datetime.utcnow(),
                data={
                    'id': tag['id'],
                    'name': tag['name'],
                    'post_count': tag['edge_hashtag_to_media']['count']
                },
                image=tag['profile_pic_url'])

        if js_data['graphql']['hashtag']['edge_hashtag_to_media']['page_info']['has_next_page']:
            yield response.follow(f'https://www.instagram.com/explore/tags/{tag["name"]}/?__a=1&max_id={end_cursor}',
                                  callback=self.json_parse)

        for edge in js_data['graphql']['hashtag']['edge_hashtag_to_media']['edges']:
            yield InstagramPost(date_parse=dt.datetime.utcnow(), data=edge['node'], image=edge['node']['display_url'])
