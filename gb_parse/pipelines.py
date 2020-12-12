# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

from pymongo import MongoClient


class GbParsePipeline:

    def __init__(self):
        self.db = MongoClient()['headhunters']

    def process_item(self, item, spider):

        collection = self.db[spider.name]
        collection.insert_one(item)
        return item
