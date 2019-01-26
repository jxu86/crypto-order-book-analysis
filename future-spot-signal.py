import okex.spot_api as spot_api
import okex.futures_api as futures_api
import utils
import numpy as np
import pandas as pd
import time
import math
import talib
import datetime
import csv
import config


class NetGrid(object):
    def __init__(self):
        self.pair = 'EOS-USDT'
        self.future_pair = 'EOS-USD-190329'
        self.base_symbol, self.quate_symbol= self.pair.split('-')
        self.weight = [0.5, 0.3, 0.0, 0.3, 0.5]
        self.spot_api = spot_api.SpotAPI(config.apikey, config.secretkey, config.password, True)
        self.future_api = futures_api.FutureAPI(config.apikey, config.secretkey, config.password, True)
        fileHeader = [
            "time", "future_bid_one", "future_ask_one", "spot_bid_one",
            "spot_ask_one","spread"
        ]
        t_time = time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))
        csvFile = open("./data/" + t_time + self.pair + ".csv", "w")
        self.writer = csv.writer(csvFile)
        self.writer.writerow(fileHeader)

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



        # print('macd=>',macd)
        # print('signal=>',signal)
        
        print('hist=>',hist[-5:len(hist)])
        print('hist_sign=>',hist_sign)
        return signal

    def net_grid_signal(self, price_list, last):
        band = np.mean(price_list) + np.array([-10, -5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 10]) * np.std(price_list)
        grid = pd.cut([last], band, labels=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])[0]
        print('net grid==>', grid)


    def run(self):
        spot_ticker = self.spot_api.get_specific_ticker(instrument_id = self.pair)
        future_ticker = self.future_api.get_specific_ticker(instrument_id = self.future_pair)
        print('#########spot_ticker=>', spot_ticker)
        print('#########future_ticker=>', future_ticker)
        spot_last = float(spot_ticker['last'])
        future_last = float(future_ticker['last'])

        spot_ask = float(spot_ticker['best_ask'])
        future_bid = float(future_ticker['best_bid'])


        print('#########spot_ask=>', spot_ask)
        print('#########future_bid=>', future_bid)
        print('#########spread=>', (spot_ask-future_bid))

        self.writer.writerow([
            datetime.datetime.now(), future_ticker['best_bid'],future_ticker['best_ask'],
            spot_ticker['best_bid'], spot_ticker['best_ask'],(spot_ask-future_bid)
        ])





def main():
    # now = time.time()
    # print('time now==>',now)
    # print('local_to_utc=>',utils.local_to_utc(now))

    net_grid = NetGrid()
    while True:
        net_grid.run()
        time.sleep(1)

    # net_grid.get_kline(instrument_id = 'EOS-USDT',size=400) #2019-01-23T15:00:00.000Z  2019-01-23T15:05:00.000Z





if __name__ == '__main__':
    main()

    # 2.302,2.4052,0.1032
    # 2.307,2.408,0.101