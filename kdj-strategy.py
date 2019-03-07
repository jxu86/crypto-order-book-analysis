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
import constant
import signals.kdj as kdj
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

class OrderRouter(object):
    def __init__(self):
        self.mongodb = MongoService(
            host=config.mongo_host, port=config.mongo_port)
        self.order_router = self.get_pending_order()
        self.future_api = futures_api.FutureAPI(
            config.apikey, config.secretkey, config.password, True)
        self.strategy_status = [
            'start', 'order_submit', 'order_filled', 'p_order_sumbit',
            'p_order_filled', 'stop_loss', 'done'
        ]

    def get_pending_order(self):
        ret = self.mongodb.find(self.mongodb.order_router,
                                {'status': 'pending'})
        print('##get_pending_order=>ret==>', ret)
        return ret

    # 下单程序
    # client_oid 由您设置的订单ID来识别您的订单
    # instrument_id
    # otype string 1:开多2:开空3:平多4:平空
    # price string 每张合约的价格
    # size Number 买入或卖出合约的数量（以张计数）
    # match_price string 是否以对手价下单(0:不是 1:是)，默认为0，当取值为1时。price字段无效
    # leverage Number 要设定的杠杆倍数，10或20
    def submit_order(self,
                     client_oid,
                     otype,
                     instrument_id,
                     price,
                     size,
                     match_price='0',
                     leverage='10',
                     timeout=20,
                     wait_flag=False):
        try:
            order_info = self.future_api.take_order(
                client_oid=client_oid,
                instrument_id=instrument_id,
                otype=otype,
                match_price=match_price,
                size=size,
                price=price,
                leverage=leverage)
        except:
            print('#######submit_order=>e==>')

        order_id = order_info['order_id']
        time.sleep(0.1)
        order = self.future_api.get_order_info(order_id, instrument_id)
        while wait_flag:
            time.sleep(0.5)
            order = self.future_api.get_order_info(order_id, instrument_id)
            print('####submit_order=>order==>', order)
            if order['status'] != '0':  #部分成交 全部成交 撤单
                return order
        return order

    # instrument_id
    # order_id order id
    # wait_flag是否等待完成
    def cancel_order(self, instrument_id, order_id, wait_flag=True):
        try:
            order_info = self.future_api.revoke_order(instrument_id, order_id)
            if 'result' in order_info.keys() and order_info['result'] == True:
                return True
        except:
            return False

    def get_last(self, instrument_id):
        ticker = self.future_api.get_specific_ticker(
            instrument_id=instrument_id)
        return float(ticker['last'])


    def get_order_info(self, instrument_id, order_id):
        return self.future_api.get_order_info(order_id, instrument_id)

    def get_order_otype(self, side):
        order_type = ''
        p_order_type = ''
        if side == 'buy':  # 开多
            order_type = '1'
            p_order_type = '3'
        elif side == 'sell':  # 开空
            order_type = '2'
            p_order_type = '4'
        return order_type, p_order_type

    def save_order(self, data):
        self.mongodb.update(self.mongodb.order_router, {'uuid': data['uuid']},
                            {'$set': data})

    def next_strategy_status(self, c_status, step=1):
        idx = self.strategy_status.index(c_status) + step
        return self.strategy_status[idx]

    def add_order(self, instrument_id, price, t_price, sl_price, size, side):
        order = {
            'uuid': str(uuid.uuid1()),
            'type': 'future',  #合约
            'instrument_id': instrument_id,
            'strategy_name': 'future_kdj',  #策略名称
            's_price': price,  # 开始价格
            't_price': t_price,  # 目标价格
            'sl_price': sl_price, # 止损价格
            'e_price': 0,  # 最后价格
            # 'o_price':
            'side': side,  # buy or sell
            'size': size,  # 目标下单数量，张数
            'status': 'pending',  # 状态 'pending' 'done' 'cancel'
            'stime': datetime.datetime.now(),  #开始时间
            'etime': 0,  #结束时间
            'strategy_status': 'start',  #策略状态，start, order_submit, order_filled, p_order_sumbit, p_order_filled, stop_loss,done, cancel
            'order': None,  #交易订单信息
            'p_order': None,  # 平仓订单信息
            'created_at': datetime.datetime.now(),
            'updated_at': datetime.datetime.now()
        }
        self.order_router.append(order)
        self.save_order(order)
            
    def get_next_strategy_status(self, current_status, order_status):
        status = current_status
        print('##########get_next_strategy_status=>current_status==>',
              current_status)
        print('##########get_next_strategy_status=>order_status==>',
              order_status)
        if order_status == constant.OrderStatus.CANCELED.value: # 取消订单
            status = 'cancel'
        elif current_status == 'start' or current_status == 'order_filled':
            status = self.next_strategy_status(current_status)
        elif self.strategy_status.index(
                current_status
        ) <= self.strategy_status.index(
                'order_submit'
        ) and order_status == constant.OrderStatus.FULLY_FILLED.value:  # 下单
            status = 'order_filled'
        elif self.strategy_status.index(
                current_status
        ) >= self.strategy_status.index(
                'order_filled'
        ) and order_status == constant.OrderStatus.FULLY_FILLED.value:  # 平仓
            status = 'p_order_filled'
        elif order_status == constant.OrderStatus.PENDING.value or order_status == constant.OrderStatus.PARTIALLY_FILLED.value:
            print('######################order pending')
        print('##########get_next_strategy_status=>status==>', status)
        return status

    def execute_order(self, order):
        strategy_status = order['strategy_status']
        print('#####execute_order==>strategy_status==>', order)

        if strategy_status == 'start':  #下单
            otype, _ = self.get_order_otype(order['side'])
            order_info = self.submit_order(
                client_oid='',
                otype=otype,
                instrument_id=order['instrument_id'],
                price=order['s_price'],
                size=order['size'])
            order['order'] = order_info
            order['strategy_status'] = self.get_next_strategy_status(
                order['strategy_status'], order_info['status'])

            # TODO 处理cancel的订单

        elif strategy_status == 'order_submit':  #do 检查下单状态
            order_info = self.get_order_info(order['instrument_id'],
                                             order['order']['order_id'])
            order['order'] = order_info
            order['strategy_status'] = self.get_next_strategy_status(
                order['strategy_status'], order_info['status'])

        elif strategy_status == 'order_filled':  #do 平仓下单
            _, otype = self.get_order_otype(order['side'])

            p_order_info = self.submit_order(
                client_oid='',
                otype=otype,
                instrument_id=order['instrument_id'],
                price=order['t_price'],
                size=order['order']['filled_qty'])
            order['p_order'] = p_order_info
            order['strategy_status'] = self.get_next_strategy_status(
                order['strategy_status'], p_order_info['status'])

        elif strategy_status == 'p_order_sumbit':  #do 检查平仓订单状态 
            order_info = self.get_order_info(order['instrument_id'],
                                             order['p_order']['order_id'])
            # 风控
            if (self.get_last(order['instrument_id']) <= order['sl_price'] and order['side'] == 'buy') \
            or (self.get_last(order['instrument_id']) >= order['sl_price'] and order['side'] == 'sell'):
                self.cancel_order(order['instrument_id'], order_info['order_id'])
                order['strategy_status'] = 'stop_loss_sumbit'
            else:
                order['p_order'] = order_info
                order['strategy_status'] = self.get_next_strategy_status(
                    order['strategy_status'], order_info['status'])
                if order['strategy_status'] == 'p_order_filled':  # 策略订单已经完成
                    order['e_price'] = order_info['price_avg']
                    order['strategy_status'] = 'done'
                    order['status'] = 'done'
                    order['etime'] = datetime.datetime.now()
        elif strategy_status == 'stop_loss_sumbit': # 止损
            _, otype = self.get_order_otype(order['side'])
            order['strategy_status'] = 'stop_loss_filled'
            sl_order_info = self.submit_order(
                client_oid='',
                otype=otype,
                instrument_id=order['instrument_id'],
                price=order['sl_price'],
                size=order['order']['filled_qty'])
            order['p_order'] = sl_order_info

        elif strategy_status == 'stop_loss_filled': # 止损
            order_info = self.get_order_info(order['instrument_id'], order['p_order']['order_id'])
            order['p_order'] = order_info
            if order_info['status'] == constant.OrderStatus.FULLY_FILLED.value:
                order['e_price'] = order_info['price_avg']
                order['strategy_status'] = 'done'
                order['status'] = 'stoploss'
                order['etime'] = datetime.datetime.now()
        elif strategy_status == 'cancel':
            order['strategy_status'] = 'cancel'
            order['status'] = 'cancel'

        else:
            print('err => strategy_status==>', order['strategy_status'])
            
        return order

    def run(self):
        if len(self.order_router) == 0: # 没有需要执行的订单任务
            return 0

        new_order_router = []
        for order in self.order_router:
            if order['status'] != 'pending':
                return
            old_strategy_status = order['strategy_status']
            order_info = self.execute_order(order)
            if order_info['status'] == 'pending':
                new_order_router.append(order_info)

            if order_info[
                    'status'] != 'pending' or old_strategy_status != order_info[
                        'strategy_status']: # 状态有变化需要update到mongo
                self.save_order(order_info)
        self.order_router = new_order_router
        return len(self.order_router)


class RiskControl(object):
    def __init__(self):
        self.stop_loss_rate = config.stop_loss_rate

    def calc_stop_loss_price(self, s_price, otype):
        if otype == 'buy':
            return s_price - s_price * self.stop_loss_rate
        elif otype == 'sell':
            return s_price + s_price * self.stop_loss_rate


    # def check_stop_loss(self, s_price, n_price):



class FutureSpotStrategy(object):
    def __init__(self):
        # self.mongodb = MongoService(
        #     host=config.mongo_host, port=config.mongo_port)
        self.spot_pair = 'EOS-USDT'
        self.future_pair = 'EOS-USD-190329'
        self.order_size = config.future_order_size
        self.max_running_order = config.max_running_order
        self.order_router = OrderRouter()
        self.future_api = futures_api.FutureAPI(
            config.apikey, config.secretkey, config.password, True)
        self.kdj = kdj.KDJignal()
        self.risk_control =  RiskControl()

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
            order_count = self.order_router.run()
            should_order_time = datetime.datetime.now() - datetime.timedelta(minutes=5) # init time
            if len(self.order_router.order_router) > 0:
                last_order_time = min(x['stime'] for x in self.order_router.order_router)
                should_order_time = last_order_time + datetime.timedelta(minutes=3)

            now_time = datetime.datetime.now()
            print('###should_order_time=>', should_order_time)
            print('###now_time=>', now_time)

            kline_datas = self.get_kline(
                instrument_id=self.future_pair, size=300)[200:-1]
            close_datas = [float(k['close']) for k in kline_datas]
            ticker = self.future_api.get_specific_ticker(
                    instrument_id=self.future_pair)
            last = float(ticker['last'])
            # close_datas.append(last)

            signal, slowk, slowd = self.kdj.signal(kline_datas)
            print('#####signal=>', signal)
            print('#####slowk=>', slowk)
            print('#####slowd=>', slowd)

            best_ask = float(ticker['best_ask'])
            best_bid = float(ticker['best_bid'])
            print('##best_ask=>',best_ask)
            print('##best_bid=>',best_bid)
            # close_datas.append(last)
            if signal != 'no' and order_count < self.max_running_order and now_time > should_order_time:
                target_price = utils.calc_profit(
                    price=last,
                    fee_rate=0.0002,
                    profit_point=0.0006,
                    side=signal)
                s_price = best_ask - 0.008
                if signal == 'buy':
                    s_price = best_bid + 0.001

                sl_price = self.risk_control.calc_stop_loss_price(s_price, signal)
                self.order_router.add_order(self.future_pair, s_price,
                                            target_price, sl_price, self.order_size,
                                            signal)
            time.sleep(0.5)


def main():
    print('#main start#')
    future_spot = FutureSpotStrategy()
    future_spot.run()


if __name__ == '__main__':
    main()