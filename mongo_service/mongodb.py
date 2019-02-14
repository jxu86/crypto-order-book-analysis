import pymongo
from pymongo import MongoClient


class MongoService(object):
    def __init__(self, host, port, username='', password=''):
        self.conn = MongoClient(host=host, port=port)
        self.db = self.conn.exchange_data
        self.order = self.db.order
        self.account = self.db.account
        self.predict_info = self.db.predict_info
        self.order_router = self.db.order_router
        self.kline_1min = self.db.kline_1min
        self.kline_5min = self.db.kline_5min

    def update(self, collection, query, udata, upsert=True):
        return collection.update(query, udata, upsert=upsert)

    def find(self, collection, query, field={}):
        ret = collection.find(query).sort([('datetime', pymongo.ASCENDING)])
        return list(ret)
