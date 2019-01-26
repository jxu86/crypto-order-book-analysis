import okex.spot_api as spot_api
import okex.futures_api as futures_api
import utils
import math
import numpy as np
import time
import datetime
import config



class FutureSpotStrategy(object):
    def __init__(self):
        self.spot_pair = 'EOS-USDT'
        self.future_pair = 'EOS-USD-190329'
        self.spot_api = spot_api.SpotAPI(config.apikey, config.secretkey, config.password, True)
        self.future_api = futures_api.FutureAPI(config.apikey, config.secretkey, config.password, True)
        self.trade_info = []

    def get_kline(self, instrument_id, start='', end='', granularity=60, size = 300):
        limit = 300
        count = math.ceil(size/limit)
        ret = []
        send = ''
        for i in range(count):
            rdatas = self.future_api.get_kline(instrument_id=instrument_id, start=start, end=send, granularity=granularity)
            fields = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'currency_volume']
            kline_datas = [dict(zip(fields, r)) for r in rdatas]
            ret += kline_datas
            send = min(x['timestamp'] for x in kline_datas)

        ret.sort(key = lambda k: (k.get('timestamp', 0)))
        print('ret=>', len(ret))
        return ret
    def get_last(self):
        ticker = self.future_api.get_specific_ticker(instrument_id = self.future_pair)
        return float(ticker['last'])

    def start_new_predict(self, price, t_price, side):
        self.trade_info.append({
                's_price': price,
                't_price': t_price,
                'e_price': 0,
                'side': side,
                'type': 'pending',
                'stime': datetime.datetime.now(),
                'etime': 0
            })
    def check_predict(self):
        if len(self.trade_info) == 0:
            return 'done'

        info = self.trade_info[-1]
        if info['type'] == 'pending':
            last = self.get_last()
            print('self.trade_info=>', self.trade_info)
            print('##check predict last==>', last)
            if (info['side'] == 'buy' and info['t_price'] <= last) or (info['side'] == 'sell' and info['t_price'] >= last):
                info['type'] = 'done'
                info['e_price'] = last
                info['etime'] = datetime.datetime.now()
        return info['type']

    def run(self):
        while True:
            time.sleep(1)
            if(self.check_predict() == 'pending'):
                continue

            kline_datas = self.get_kline(instrument_id = self.future_pair,size=300)[200:-1]
            close_datas = [float(k['close']) for k in kline_datas] 
            macd_signal = utils.macd_signal(np.array(close_datas))
            print('######macd_signal=>',macd_signal)
            # 检测到交易信号
            if macd_signal != 'no':
                ticker = self.future_api.get_specific_ticker(instrument_id = self.future_pair)
                last = float(ticker['last'])
                target_price = utils.calc_profit(price=last,fee_rate=0.0002,profit_point=0.0001, side=macd_signal)
                self.start_new_predict(last, target_price, macd_signal)
                print('#last==>', last)
                print('#target_price==>', target_price)
            # print('self.trade_info=>', self.trade_info)
            
            


def main():
    future_spot = FutureSpotStrategy()
    future_spot.run()



if __name__ == '__main__':
    main()