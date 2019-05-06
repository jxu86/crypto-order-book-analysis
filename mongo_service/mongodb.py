import pymongo
from pymongo import MongoClient


class MongoService(object):
    def __init__(self, host, port, username='nowdone', password='nowdone2go', authSource='nowdone'):
        self.conn = MongoClient(host=host, port=port, username=username, password=password, authSource=authSource)
        # self.conn = MongoClient(host=host, port=port)
        # self.db = self.conn.exchange_data
        self.db = self.conn.nowdone
        self.order = self.db.order
        self.account = self.db.account
        self.predict_info = self.db.predict_info
        self.order_router = self.db.order_router
        self.kline_1min = self.db.kline_1min
        self.kline_5min = self.db.kline_5min
        self.kline_history_1min = self.db.kline_history_1min
        self.swap_funding_rate = self.db.swap_funding_rate
        self.swap_calc_rate = self.db.swap_calc_rate
        self.strategy = self.db.strategy

    def update(self, collection, query, udata, upsert=True):
        return collection.update(query, udata, upsert=upsert)

    def find(self, collection, query, field={}):
        ret = collection.find(query).sort([('datetime', pymongo.ASCENDING)])
        return list(ret)
