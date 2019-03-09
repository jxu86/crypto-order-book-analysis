import okex.swap_api as swap_api
import okex.spot_api as spot_api
import okex.futures_api as futures_api
from mongo_service.mongodb import MongoService
import config
import utils
import datetime
import time
from utils import JSONDateTimeDecoder
import redis
import json
import talib
import numpy as np


class Swap(object):
    def __init__(self):
        self.future_quarter_instrument_id = 'EOS-USD-190329'
        self.swap_instrument_id = 'EOS-USD-SWAP'
        self.future_quarter_endtime = datetime.datetime.strptime('2019-03-29','%Y-%m-%d')
        self.future_nextweek_instrument_id = 'EOS-USD-190301'
        self.future_nextweek_endtime = datetime.datetime.strptime('2019-03-01','%Y-%m-%d')
        self.spot_instrument_id = 'EOS-USDT'
        # self.spot_base = 'EOS'
        # self.spot_quote = 'USDT'

        self.spot_api = spot_api.SpotAPI(config.apikey, config.secretkey, config.password, True)
        self.future_api = futures_api.FutureAPI(config.apikey, config.secretkey, config.password, True)
        self.swap_api = swap_api.SwapAPI(config.apikey, config.secretkey, config.password, True)

        self.mongodb = MongoService(host=config.mongo_host, port=config.mongo_port)

        r = redis.Redis(host='10.10.20.60', port=6379, password='nowdone2go', decode_responses=True)
        self.ps = r.pubsub()
        subscribe_msg = ['okex.swap_order_book.EOS-USD-SWAP']#['okex.future_order_book.EOS-USD-190329','okex.swap_order_book.EOS-USD-SWAP']
        
        self.ps.subscribe(subscribe_msg)  #订阅消息
        self.swap_fee_list = [0] * 10000
        self.count = 0


    def get_instrument_ids(self):
        instruments = self.swap_api.get_instruments()
        instrument_ids = [i['instrument_id'] for i in instruments]
        return instrument_ids


    def get_historical_funding(self, instrument_id, froms='1'):
        h_fund = self.swap_api.get_historical_funding_rate(instrument_id=instrument_id, froms=froms, limit='100')
        # print('h_fund=>',h_fund)
        return h_fund

    def save_data(self,data):
        for d in data:
            # d['instrument_id'] =  instrument_id
            d['created_at'] = datetime.datetime.now()
            d['funding_time'] =  utils.utcstr_to_datetime(d['funding_time'])
            d['funding_rate'] = float(d['funding_rate'])
            d['realized_rate'] = float(d['realized_rate'])
            d['interest_rate'] = float(d['interest_rate'])
            self.mongodb.update(self.mongodb.swap_funding_rate, {'instrument_id': d['instrument_id'], 'funding_time': d['funding_time']},{'$set': d})

    def calc_interest(self):
        future_quarter_ticker = self.future_api.get_specific_ticker(instrument_id=self.future_quarter_instrument_id)
        future_quarter_price = float(future_quarter_ticker['last'])
        print('future_quarter_price =>', future_quarter_price)

        future_nextweek_ticker = self.future_api.get_specific_ticker(instrument_id=self.future_nextweek_instrument_id)
        future_nextweek_price = float(future_nextweek_ticker['last'])
        print('future_nextweek_price =>', future_nextweek_price)

        index = self.future_api.get_index(self.future_quarter_instrument_id)
        index_price = float(index['index'])
        print('quarter index_price =>', index_price)
        

        # index = self.future_api.get_index(self.future_nextweek_instrument_id)
        # print('nextweek index =>', index)

        # spot_ticker = self.spot_api.get_specific_ticker(instrument_id=self.spot_instrument_id)
        # spot_price = float(spot_ticker['last'])
        # print('spot_price =>', spot_price)

        r2 = utils.calc_future_interest(future_quarter_price, index_price, self.future_quarter_endtime)
        print('r2=>', r2)

        r1 = utils.calc_future_interest(future_nextweek_price, index_price, self.future_nextweek_endtime)
        print('r1=>', r1)

    def calc_future_fee_rate(self, price):
        index = self.future_api.get_index(self.future_quarter_instrument_id)
        index_price = float(index['index'])
        return utils.calc_future_interest(price, index_price, self.future_quarter_endtime)


    def calc_fee_rate(self, price):
        index_price = 0
        try:
            index = self.swap_api.get_index(self.swap_instrument_id)
            index_price = float(index['index'])
        except:
            print('#####get index price err')
        swap_fee =  (price-index_price)/index_price
        return index_price, swap_fee
        # self.fee_list.append((mid_one-index_price)/index_price)


    def handle_data(self, data):
        # print('data=>',data)
        # self.count += 1
        # if self.count < 10:
        #     return

        self.count = 0
        ask_one = data['asks'][0]['price']
        bid_one = data['bids'][0]['price']
        instrument_id = data['instrument_id']
        
        mid_one = (ask_one+bid_one)/2

        if instrument_id == self.future_quarter_instrument_id:
            r = self.calc_future_fee_rate(mid_one)
            print('r2==>', r)
        elif instrument_id == self.swap_instrument_id:
            index_price, r = self.calc_fee_rate(mid_one)
            ret = {
                'instrument_id': instrument_id,
                'datetime': data['datetime'],
                'ask_one': ask_one,
                'bid_one': bid_one,
                'index_price': index_price,
                'rate': r,
                'created_at': datetime.datetime.now()
            }

            self.mongodb.update(self.mongodb.swap_calc_rate, {'instrument_id': ret['instrument_id'], 'datetime': ret['datetime']},{'$set': ret})
            print('r0==>', r)


            # self.swap_fee_list.append(r)
            # self.swap_fee_list.pop(0)
            # print('ma r0',talib.EMA(np.array(self.swap_fee_list), timeperiod = 500)[-1])


        # mid_one = (ask_one+bid_one)/2

        # index = self.swap_api.get_index('EOS-USD-SWAP')
        # index_price = float(index['index'])
        # swap_fee =  (mid_one-index_price)/index_price
        # # self.fee_list.append((mid_one-index_price)/index_price)
        # self.swap_fee_list.append(swap_fee)
        # self.swap_fee_list.pop(0)
        # ma = talib.EMA(np.array(self.swap_fee_list), timeperiod = 500)

        # print('ask_one=>', ask_one)
        # print('bid_one=>', bid_one)
        # print('mid_one=>', mid_one)

        # print('spread=>', ask_one-bid_one)
        # print('swap_fee=>', swap_fee)
        # print('ma=>', ma[-1])
        
    
    def run(self):
        for item in self.ps.listen():		#监听状态：有消息发布了就拿过来
            if item['type'] == 'message':
                data = json.loads(item['data'], cls=JSONDateTimeDecoder)
                # print('data=>', data['asks'])
                self.handle_data(data)

        # while True:
        #     self.calc_interest()
        #     time.sleep(1)

        # instrument_ids = self.get_instrument_ids()
        # for instrument_id in instrument_ids:
        #     print('####instrument_id=>', instrument_id)
        #     froms = 1
        #     while True:
        #         funding_datas = self.get_historical_funding(instrument_id, froms=str(froms))
        #         if len(funding_datas) == 0:
        #             break
        #         self.save_data(funding_datas)
        #         froms += 1

def main():
    print('###main start###')
    swap = Swap()
    swap.run()
    print('###main end###')


if __name__ == '__main__':
    main()



    
