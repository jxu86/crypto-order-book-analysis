
import okex.futures_api as futures_api
import config
import math
import time
from mongo_service.mongodb import MongoService




class Exchange(object):
    def __init__(self):
        self.future_api = futures_api.FutureAPI(
            config.apikey, config.secretkey, config.password, True)
        self.mongodb = MongoService(
            host=config.mongo_host, port=config.mongo_port)

    def get_future_kline(self,
                  instrument_id,
                  start='',
                  end='',
                  granularity=60,
                  size=300):
        limit = 300
        count = math.ceil(size / limit)
        ret = []
        send = ''
        for i in range(count):
            rdatas = self.future_api.get_kline(
                instrument_id=instrument_id,
                start=start,
                end=send,
                granularity=granularity)
            fields = [
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'currency_volume'
            ]
            kline_datas = [dict(zip(fields, r)) for r in rdatas]
            ret += kline_datas
            send = min(x['timestamp'] for x in kline_datas)
            time.sleep(0.15)
   
        d = {}
        for r in ret:
            d[r['timestamp']] = r
    
        ret = list(d.values())
        ret.sort(key=lambda k: (k.get('timestamp', 0)))
        print('ret=>', len(ret))
        return ret

    def save_data(self, instrument_id, data):
        for d in data:
            d['instrument_id'] =  instrument_id
            self.mongodb.update(self.mongodb.kline_1min, {'instrument_id': d['instrument_id'], 'timestamp': d['timestamp']},{'$set': d})


def main():
    print('#main start#')
    instrument_id = 'EOS-USD-190329'
    exchange = Exchange()
    klines = exchange.get_future_kline(instrument_id='EOS-USD-190329',size=6000,granularity=6)
    exchange.save_data(instrument_id, klines)

    print('main end =>')



if __name__ == '__main__':
    main()
