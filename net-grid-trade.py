import okex.spot_api as spot_api
import utils
import numpy as np
import pandas as pd
import time
import math
import talib
import config


class NetGrid(object):
    def __init__(self):
        self.pair = 'EOS-USDT'
        self.base_symbol, self.quate_symbol= self.pair.split('-')
        self.weight = [0.5, 0.3, 0.0, 0.3, 0.5]
        self.spot_api = spot_api.SpotAPI(config.apikey, config.secretkey, config.password, True)
        # print('self.base_symbol=>',self.base_symbol)
        # print('self.quate_symbol=>',self.quate_symbol)
    def get_price_level(self, price,direction='up',percentage=0.01):
        level = np.array([i for i in range(0,11,1)])*0.01

        if direction == 'up':
            ret = price + level * price
        else:
            ret = price - level*price
        print('ret=>',ret)
        return ret
    
        

    def get_kline(self, instrument_id, start='', end='', granularity=60, size = 200):
        limit = 200
        count = math.ceil(size/limit)
        ret = []
        send = ''
        for i in range(count):
            rdatas = self.spot_api.get_kline(instrument_id=instrument_id, start=start, end=send, granularity=granularity)
            fields = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            kline_datas = [dict(zip(fields, r)) for r in rdatas]
            ret += kline_datas
            send = min(x['timestamp'] for x in kline_datas)

        ret.sort(key = lambda k: (k.get('timestamp', 0)))
        print('ret=>', len(ret))
        return ret

    def macd_signal(self, price_list):
        signal = 'no'
        SHORTPERIOD = 12
        LONGPERIOD = 26
        SMOOTHPERIOD = 9
        OBSERVATION = 100
        macd, signal, hist = talib.MACD(price_list, fastperiod=SHORTPERIOD, slowperiod=LONGPERIOD, signalperiod=SMOOTHPERIOD)
        sample_hist = hist[-5:len(hist)]
        hist_sign = 0

        for h in sample_hist:
            if h > 0:
                hist_sign += 1
            else:
                hist_sign -= 1
                
        if hist_sign == -5 and sample_hist[-2] < sample_hist[-1]:
            print('#####macd buy signal')
            signal = 'buy'
        elif hist_sign == 5 and sample_hist[-2] > sample_hist[-1]:
            print('#####macd sell signal')
            signal = 'sell'

        print('hist=>',hist[-5:len(hist)])
        print('hist_sign=>',hist_sign)
        return signal

    def net_grid_signal(self, price_list, last):
        band = np.mean(price_list) + np.array([-10, -5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 10]) * np.std(price_list)
        grid = pd.cut([last], band, labels=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])[0]
        print('net grid==>', grid)

    def run(self):
        # account = self.spot_api.get_account_info()
        # print('####account ==>',account)
        
        kline_datas = self.get_kline(instrument_id = self.pair,size=200)[100:-1]
        # print('###time=>',min(x['timestamp'] for x in kline_datas))
        close_datas = [float(k['close']) for k in kline_datas] 
        # print('std==>', np.std(close_datas))
        # print('==>', np.array([-10, -5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 10]) * np.std(close_datas))
        # band = np.mean(close_datas) + np.array([-10, -5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 10]) * np.std(close_datas)
        # print('####band ==>',band)
        ticker = self.spot_api.get_specific_ticker(instrument_id = self.pair)
        last = float(ticker['last'])
        # print('####ticker last==>',last)
        # grid = pd.cut([last], band, labels=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])[0]
        # print('####grid ==>',grid)

        self.macd_signal(np.array(close_datas))
        self.net_grid_signal(close_datas, last)

        # self.get_price_level(last, direction='up', percentage=0.005)
        # self.get_price_level(last, direction='down', percentage=0.005)
        # order = self.spot_api.get_orders_list(status='open',instrument_id='EOS-USDT')
        # order = self.spot_api.take_order(otype='limit',side='sell',instrument_id=instrument_id,size=0.1,price=5)
        # print('####order ==>',order)
    # [2.37605859 2.39906429 2.40366544 2.40826658 2.41286772 2.41746886, 2.42667114 2.43127228 2.43587342 2.44047456 2.44507571 2.46808141]


def main():
    # now = time.time()
    # print('time now==>',now)
    # print('local_to_utc=>',utils.local_to_utc(now))

    net_grid = NetGrid()
    while True:
        net_grid.run()
        time.sleep(30)

    # net_grid.get_kline(instrument_id = 'EOS-USDT',size=400) #2019-01-23T15:00:00.000Z  2019-01-23T15:05:00.000Z








if __name__ == '__main__':
    main()