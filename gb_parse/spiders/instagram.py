import scrapy
import json
from collections import defaultdict, deque
from anytree import Node, RenderTree
from scrapy.exceptions import CloseSpider


class InstagramSpider(scrapy.Spider):
    name = 'instagram'
    allowed_domains = ['www.instagram.com']
    login_url = 'https://www.instagram.com/accounts/login/ajax/'
    graphql_url = '/graphql/query/'
    start_urls = ['https://www.instagram.com/']

    query = {
        'edge_followed_by': 'c76146de99bb02f6415203be841dd25a',
        'edge_follow': 'd04b0a864b4b54837c0d870b0e77e076'
    }

    follow_dict = defaultdict(lambda: defaultdict(list))
    tree_dict = {}

    def __init__(self, login, password, start_user, end_user, log_level, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_user = start_user
        self.end_user = end_user
        self.tree_dict[self.start_user] = Node(self.start_user)
        self.scan_que = deque()
        self.login = login
        self.password = password
        self.log_level = log_level

    @staticmethod
    def script_data(response) -> dict:
        try:
            return json.loads(response.xpath('//script[contains(text(),"window._sharedData")]/text()').get().replace(
                'window._sharedData = ', '').rstrip(';'))
        except ValueError:
            raise CloseSpider('Something wrong with JSON')

    def get_url(self, user_id, after='', flw='edge_followed_by') -> str:
        variables = {"id": user_id,
                     "include_reel": False,
                     "fetch_mutual": False,
                     "first": 100,
                     "after": after}
        return f'{self.graphql_url}?query_hash={self.query[flw]}&variables={json.dumps(variables)}'

    def parse(self, response, **kwargs):
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
                yield response.follow(f'/{self.start_user}/', callback=self.user_parse)

    def user_parse(self, response):
        json_data = self.script_data(response)
        try:
            json_user = json_data['entry_data']['ProfilePage'][0]['graphql']['user']
            user_id = json_user['id']
            user_name = json_user['username']
            followed_by_count = json_user['edge_followed_by']['count']
            follow_count = json_user['edge_follow']['count']

            for flw in self.query.keys():
                yield response.follow(self.get_url(user_id, flw=flw), callback=self.follow_parse,
                                      meta={'user_id': user_id,
                                            'user_name': user_name,
                                            'follow': flw,
                                            'followed_by_count': followed_by_count,
                                            'follow_count': follow_count,
                                            'parent': response.meta.get('parent')})
        except KeyError:
            raise CloseSpider('Wrong JSON received. Probably bad user for crawling...')

    def follow_parse(self, response):
        json_data = response.json()
        end_cursor = json_data['data']['user'][response.meta['follow']]['page_info']['end_cursor']
        next_page = json_data['data']['user'][response.meta['follow']]['page_info']['has_next_page']
        user_name = response.meta["user_name"]

        if next_page:
            yield response.follow(
                self.get_url(user_id=response.meta['user_id'], after=end_cursor, flw=response.meta['follow']),
                callback=self.follow_parse, meta=response.meta)

        for edge in json_data['data']['user'][response.meta['follow']]['edges']:
            if response.meta['follow'] == 'edge_follow':
                self.follow_dict[user_name]['follows'].append(edge['node']['username'])
            else:
                self.follow_dict[user_name]['followed_by'].append(edge['node']['username'])

        if self.log_level:
            print(f'{user_name}: follows {len(self.follow_dict[user_name]["follows"])} '
                  f'| {response.meta["follow_count"]}, '
                  f'followed_by {len(self.follow_dict[user_name]["followed_by"])} '
                  f'| {response.meta["followed_by_count"]}')

        if (len(self.follow_dict[user_name]["follows"]) == response.meta['follow_count']) and \
                (len(self.follow_dict[user_name]["followed_by"]) == response.meta['followed_by_count']):
            b_follow = []
            for user in self.follow_dict[user_name]["followed_by"]:
                if user in self.follow_dict[user_name]["follows"]:
                    b_follow.append(user)
                    if user not in self.tree_dict.keys():
                        self.tree_dict[user] = Node(user, parent=self.tree_dict[user_name])

            if self.log_level:
                print(RenderTree(self.tree_dict[self.start_user]))

            self.scan_que.extend(b_follow)

            if self.log_level:
                print(f'\nUsers: {len(self.scan_que)}')

            if self.end_user in b_follow:
                print('Path')
                print(' -> '.join([node.name for node in self.tree_dict[self.end_user].iter_path_reverse()]))
                raise CloseSpider('Connection between users found. Stopping spider')

            try:
                user = self.scan_que.popleft()
                yield response.follow(f'/{user}/', callback=self.user_parse,
                                      meta={'parent': user_name})
            except IndexError:
                raise CloseSpider("Que is empty. Can't find connection between users")
