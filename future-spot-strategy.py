import okex.spot_api as spot_api
import okex.futures_api as futures_api
import utils
import math
import numpy as np
import time
import datetime
import config
from mongo_service.mongodb import MongoService
import uuid

class FutureSpotStrategy(object):
    def __init__(self):
        self.mongodb = MongoService(host=config.mongo_host, port=config.mongo_port)
        self.spot_pair = 'EOS-USDT'
        self.future_pair = 'EOS-USD-190329'
        self.spot_api = spot_api.SpotAPI(config.apikey, config.secretkey, config.password, True)
        self.future_api = futures_api.FutureAPI(config.apikey, config.secretkey, config.password, True)
        self.trade_info = self.get_pending_info()
        self.order_size = 1



    def get_pending_info(self):
        ret = self.mongodb.find(self.mongodb.predict_info, {'type':'pending'})
        print('##get_pending_info=>ret==>', ret)
        return ret
        
    def update_info(self, data):
        self.mongodb.update(self.mongodb.predict_info, {'stime': data['stime'], 's_price': data['s_price']}, {'$set': data})

    # client_oid 由您设置的订单ID来识别您的订单
    # instrument_id
    # otype string 1:开多2:开空3:平多4:平空
    # price string 每张合约的价格
    # size Number 买入或卖出合约的数量（以张计数）
    # match_price string 是否以对手价下单(0:不是 1:是)，默认为0，当取值为1时。price字段无效
    # leverage Number 要设定的杠杆倍数，10或20
    def submit_order(self, client_oid, otype, instrument_id, price, size, match_price='0',leverage='10', timeout=20, wait_flag=True):
        try:
            order_info = self.future_api.take_order(client_oid=client_oid, instrument_id=instrument_id, otype=otype,match_price=match_price,size=size,price=price, leverage=leverage)
        except:
            print('#######submit_order=>e==>')
        order_id = order_info['order_id']
        time.sleep(0.5)
        order = self.future_api.get_order_info(order_id, instrument_id)
        while wait_flag:
            time.sleep(0.5)
            order = self.future_api.get_order_info(order_id, instrument_id)
            print('####submit_order=>order==>',order)
            if order['status'] != '0': #部分成交 全部成交 撤单
                return order
        return order
    
    def cancel_order(self,instrument_id, order_id):
        order_info = self.future_api.revoke_order(instrument_id, order_id)
        if 'result' in order_info.keys() and order_info['result'] == True:
            return True
        return False

    # def order_info(self, instrument_id, order_id):



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

    def start_new_predict(self, price, t_price, side, size):
        # 下单
        otype = ''
        if side == 'buy': # 开多
            otype = '1'
        elif side == 'sell': # 开空
            otype = '2'

        order = self.submit_order(client_oid='',otype=otype, instrument_id=self.future_pair, price=price, size=size)
        
        #判断平多还是平空
        otype = ''
        if order['type'] == '1':
            otype = '3'
        elif order['type'] == '2':
            otype = '4'

        p_order = self.submit_order(client_oid='',otype=otype, instrument_id=self.future_pair, price=t_price, size=order['filled_qty'], wait_flag=False)
        # 记录下单
        order_status = order['status']
        predict = {
                'order_id': order['order_id'],
                'filled_qty': order['filled_qty'],
                's_price': price,
                't_price': t_price,
                'e_price': 0,
                'side': side,
                'size': order['size'],
                'type': 'pending',
                'stime': datetime.datetime.now(),
                'etime': 0,
                'order_status':order_status,
                'order': order,
                'p_order': p_order,
                'p_order_status': p_order['status'],
                'p_order_id': p_order['order_id']
            }
        self.trade_info.append(predict)
        self.update_info(predict)
        
    def check_predict(self):
        if len(self.trade_info) == 0:
            return 'done'

        info = self.trade_info[-1]
        if info['type'] == 'pending' and 'p_order' in info.keys():
            # if info['order_status'] == '0': #订单没成交
            #     # 检查订单状态
            #     order = self.future_api.get_order_info(info['order_id'], self.future_pair)
            #     print('######check_predict=>order==>', order)
            #     if order['status'] == '2':
            #         info['order_status'] = order['status']
            #         info['order'] = order
            #         info['filled_qty'] = order['filled_qty']
            #     else:
            #         return info['type']
            # if info['order_status'] == '-1': #已经撤单
            #     info['type'] = 'done'
            #     info['etime'] = datetime.datetime.now()
            #     self.update_info(info)
            p_order_id = info['p_order_id']
            p_order = self.future_api.get_order_info(p_order_id, self.future_pair)
            if p_order['status'] == '2':
                info['type'] = 'done'
                info['e_price'] = p_order['price_avg']
                info['etime'] = datetime.datetime.now()
                self.update_info(info)

            last = self.get_last()
            # 平仓
            print('self.trade_info=>', self.trade_info)
            print('##check predict last==>', last)
            # if (info['side'] == 'buy' and info['t_price'] <= last) or (info['side'] == 'sell' and info['t_price'] >= last):
            #     order_id = info['order_id']
            #     order = self.future_api.get_order_info(order_id, self.future_pair)
            #     # 平仓
            #     if order['status'] == '1' or order['status'] == '2':
            #         otype = ''
            #         if order['type'] == '1':
            #             otype = '3'
            #         elif order['type'] == '2':
            #             otype = '4'
            #         p_order = self.submit_order(client_oid='',otype=otype, instrument_id=self.future_pair, price=info['t_price'],size=order['filled_qty'])
            #         if p_order['status'] == '1' or p_order['status'] == '2':
            #             info['type'] = 'done'
            #             info['e_price'] = last
            #             info['etime'] = datetime.datetime.now()
            #             self.update_info(info)

        return info['type']

    def run(self):
        # p_order = self.submit_order(client_oid='',otype='4', instrument_id=self.future_pair, price=2.326,size=1)
        while True:
            time.sleep(1)
            # p_order = self.submit_order(client_oid='',otype='4', instrument_id=self.future_pair, price=2.326,size=1)
            # 检查是否需要平仓和检查平仓是否成功
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
                target_price = utils.calc_profit(price=last,fee_rate=0.0002,profit_point=0.0003, side=macd_signal)
                # 记录并且下单
                self.start_new_predict(last, target_price, macd_signal, self.order_size)
                print('#last==>', last)
                print('#target_price==>', target_price)
            # print('self.trade_info=>', self.trade_info)
            
def main():
    future_spot = FutureSpotStrategy()
    future_spot.run()

if __name__ == '__main__':
    main()