import okex.spot_api as spot_api
import okex.futures_api as futures_api
import utils
import math
import numpy as np
import time
import datetime
import config
from mongo_service.mongodb import MongoService
import signals.ema as ema
import order_service.order as order
import risk_service.risk as risk

# TODO
# 强行平仓止损
# 撤单处理
# 风控
# 加入order book分析，以便可以以最优方式下单
# 两个任务同时进行
# 计算收益
# paper trading
# 回测
# 策略任务订单存储可以是给接口，例如redis


class Strategy(object):
    def __init__(self):
        self.strategy_name = 'future_ema'
        self.spot_pair = 'EOS-USDT'
        self.future_pair = 'EOS-USD-190329'
        self.order_size = config.future_order_size
        self.max_running_order = config.max_running_order
        self.order_router = order.OrderRouter()
        self.future_api = futures_api.FutureAPI(
            config.sub_apikey, config.sub_secretkey, config.sub_password, True)
        self.ema = ema.EMASignal()
        self.risk_control = risk.RiskControl()

    # load config from
    def _load_config(self):
        pass

    def get_kline(self,
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

        ret.sort(key=lambda k: (k.get('timestamp', 0)))
        print('ret=>', len(ret))
        return ret

    def get_last(self):
        ticker = self.future_api.get_specific_ticker(
            instrument_id=self.future_pair)
        return float(ticker['last'])

    def run(self):
        while True:
            # 处理订单
            order_count = self.order_router.run()
            should_order_time = datetime.datetime.now() - datetime.timedelta(
                minutes=5)  # init time
            if len(self.order_router.order_router) > 0:
                last_order_time = min(
                    x['stime'] for x in self.order_router.order_router)
                should_order_time = last_order_time + datetime.timedelta(
                    minutes=3)

            now_time = datetime.datetime.now()
            print('###should_order_time=>', should_order_time)
            print('###now_time=>', now_time)

            kline_datas = self.get_kline(
                instrument_id=self.future_pair, size=300)[200:-1]
            close_datas = [float(k['close']) for k in kline_datas]
            ticker = self.future_api.get_specific_ticker(
                instrument_id=self.future_pair)
            last = float(ticker['last'])

            signal, fast_avg, slow_avg = self.ema.signal(np.array(close_datas))
            print('#####signal=>', signal)
            print('#####fast_avg=>', fast_avg)
            print('#####slow_avg=>', slow_avg)

            best_ask = float(ticker['best_ask'])
            best_bid = float(ticker['best_bid'])
            print('##best_ask=>', best_ask)
            print('##best_bid=>', best_bid)

            # if signal != 'no' and order_count < self.max_running_order and now_time > should_order_time:
            #     target_price = utils.calc_profit(
            #         price=last,
            #         fee_rate=0.0002,
            #         profit_point=0.0008,
            #         side=signal)
            #     s_price = best_ask - 0.001
            #     if signal == 'buy':
            #         s_price = best_bid + 0.001

            #     sl_price = self.risk_control.calc_stop_loss_price(
            #         s_price, signal)
            #     self.order_router.add_order(
            #         self.future_pair, s_price, target_price, sl_price,
            #         self.order_size, signal, self.strategy_name)
            # time.sleep(0.5)
        
            future_position = self.order_router.get_future_position(self.future_pair)
            print('#####future_position=>', future_position)
            long_avail_qty = 0
            short_avail_qty = 0
            if future_position != {}:
                long_avail_qty = float(future_position['long_avail_qty'])
                short_avail_qty = float(future_position['short_avail_qty'])
            
            print('#####long_avail_qty=>', long_avail_qty)
            print('#####short_avail_qty=>', short_avail_qty)
            
            if signal != 'no' and order_count < self.max_running_order and now_time > should_order_time:
                if signal == 'buy':
                    self.order_router.submit_order( client_oid='',
                                                    otype='1',
                                                    instrument_id=self.future_pair,
                                                    price=best_bid+0.001,
                                                    size=1)
                    if long_avail_qty != 0: 
                        self.order_router.submit_order( client_oid='',
                                                        otype='3',
                                                        instrument_id=self.future_pair,
                                                        price=best_ask-0.001,
                                                        size=long_avail_qty)
                elif signal == 'sell':
                    self.order_router.submit_order( client_oid='',
                                                    otype='2',
                                                    instrument_id=self.future_pair,
                                                    price=best_ask-0.001,
                                                    size=1)
                    if short_avail_qty != 0:
                        self.order_router.submit_order( client_oid='',
                                                        otype='4',
                                                        instrument_id=self.future_pair,
                                                        price=best_bid+0.001,
                                                        size=short_avail_qty)
            time.sleep(0.5)
                                                




def main():
    print('#main start#')
    strategy = Strategy()
    strategy.run()


if __name__ == '__main__':
    main()