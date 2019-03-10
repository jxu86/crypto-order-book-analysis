import sys
import redis
import json
import okex.spot_api as spot_api
import config
from utils import JSONDateTimeDecoder
import datetime
import time
import uuid


class OrderManager():
    def __init__(self):
        self.spot_api = spot_api.SpotAPI(config.apikey, config.secretkey,
                                         config.password, True)
        self.order_router = []
        self.sell_list = []
        self.buy_list = []

    def check_position(self, symbol):
        return self.spot_api.get_coin_account_info(symbol)

    def add_order(self,
                  instrument_id,
                  price,
                  t_price,
                  size,
                  side,
                  order,
                  strategy_name='marketmaker'):
        order = {
            'uuid': str(uuid.uuid1()),
            'type': 'spot',  #现货
            # 'order_id': '',
            'instrument_id': instrument_id,
            'strategy_name': strategy_name,  #策略名称
            's_price': price,  # 开始价格
            't_price': t_price,  # 目标价格
            'e_price': 0,  # 最后价格
            'side': side,  # buy or sell
            'size': size,  # 目标下单数量，张数
            'status': 'pending',  # 状态 'pending' 'done' 'cancel'
            'stime': datetime.datetime.now(),  #开始时间
            'etime': 0,  #结束时间
            # 'strategy_status':'start',  #策略状态，start, order_submit, order_filled, p_order_sumbit, p_order_filled, stop_loss,done, cancel
            'order': order,  #交易订单信息
            # 'p_order': None,  # 平仓订单信息
            'created_at': datetime.datetime.now(),
            'updated_at': datetime.datetime.now()
        }

        self.order_router.append(order)
        # self.save_order(order)
    def del_order(self, order_id=None):
        self.order_router = []

    def save_order(self, order):
        pass

    # def execute_order(self, order):
    # pass

    def submit_spot_order(self,
                          client_oid,
                          otype,
                          side,
                          instrument_id,
                          price,
                          size,
                          notional,
                          timeout=20,
                          wait_flag=False,
                          order_record=True,
                          close_record=False):
        order_info = None
        try:
            order_info = self.spot_api.take_order(
                client_oid=client_oid,
                instrument_id=instrument_id,
                otype=otype,
                side=side,
                size=size,
                price=price)
            print('order_info=>', order_info)
        except:
            print('#######submit_spot_order=>e==>')
            return None

        order_id = order_info['order_id']
        if close_record and side == 'sell':
            self.sell_list.append(
                {
                    'order_id': order_id,
                    'instrument_id': instrument_id,
                    'side': side,
                    'price': price
                }
            )
            print('#self.sell_list=>', self.sell_list)
        elif close_record and side == 'buy':
            self.buy_list.append(
                {
                    'order_id': order_id,
                    'instrument_id': instrument_id,
                    'side': side,
                    'price': price
                }
            )
            print('#self.buy_list=>', self.buy_list)

        if order_record:
            self.del_order()
            self.add_order(
                instrument_id=instrument_id,
                price=price,
                t_price=0,
                size=size,
                side=side,
                order=order_info)
        return order_info

        # time.sleep(0.05)
        # print('#####instrument_id=>', instrument_id)
        # print('#####order_id=>', order_id)
        # try:
        #     order = self.spot_api.get_order_info(order_id, instrument_id)
        #     print('spot order2==>', order)
        # except:
        #     self.add_order(instrument_id=instrument_id, price=price, t_price=0, size=size, side=side, order=order_info)
        #     print('spot read order info err')
        #     return

        # while wait_flag:
        #     time.sleep(0.2)
        #     # order = self.spot_api.get_order_info(order_id, instrument_id)
        #     try:
        #         order = self.spot_api.get_order_info(order_id, instrument_id)
        #         if order['status'] == 'filled':  #部分成交 全部成交 撤单
        #             return order
        #     except:
        #         print('spot read order info err')
        # self.add_order(instrument_id=instrument_id, price=price, t_price=0, size=size, side=side, order=order)

        # return order

    def cancel_order(self, order_id, instrument_id):
        return self.spot_api.revoke_order(order_id, instrument_id)

    def get_order_info(self, order_id, instrument_id):
        return self.spot_api.get_order_info(order_id, instrument_id)

    def get_last_order_info(self):
        if len(self.order_router) == 0:
            return None
        order = self.order_router[-1]
        return self.get_order_info(order['order']['order_id'],
                                   order['instrument_id'])

    def update_sell_list(self, ask_price):
        new_sell_list = []
        min_sell_price = 0
        for s in self.sell_list:
            if s['price'] > ask_price:
                new_sell_list.append(s)
        self.sell_list = new_sell_list
        if len(self.sell_list):
            min_sell_price = min([s['price'] for s in self.sell_list])
        print('#self.sell_list=>', self.sell_list)
        return min_sell_price

    def update_buy_list(self, bid_price):
        new_buy_list = []
        min_buy_price = 0
        for b in self.buy_list:
            if b['price'] < bid_price:
                new_buy_list.append(b)
        self.buy_list = new_buy_list
        if len(self.buy_list):
            max_buy_price = max([b['price'] for b in self.buy_list])
        print('#self.buy_list=>', self.buy_list)
        return max_buy_price

class Strategy():
    def __init__(self):
        r = redis.Redis(
            host='127.0.0.1',
            port=6379,
            password='nowdone2go',
            decode_responses=True)
        self.ps = r.pubsub()
        self.spot_pair = 'EOS-USDT'
        self.base = 'EOS'
        self.quote = 'USDT'
        subscribe_msg = 'okex.order_book.EOS/USDT'
        self.ps.subscribe([subscribe_msg])  #订阅消息
        self.order_manager = OrderManager()
        self.spot_size = config.spot_step_size
        self.limit_base_position_size = config.max_limit_base_position
        self.t_rate = 1.0005 + 0.002 * 0.13
        self.last_bid_price = 0
        self.last_ask_price = 0
        self.init_base = 0
        self.main_side = config.main_side

    def submit_order(self, side, price, order_record=True, close_record=False):
        return self.order_manager.submit_spot_order(
            client_oid='',
            otype='limit',
            side=side,
            instrument_id=self.spot_pair,
            size=self.spot_size,
            price=price,
            notional='',
            order_record=order_record,
            close_record=close_record)

    #
    def signal(self, side, price):
        # if self.last_bid_price != 0 and (self.last_bid_price/bid_one) < self.t_rate:
        #         min_sell_price = self.order_manager.update_sell_list(ask_one)
        #         self.last_bid_price = min_sell_price/self.t_rate
        #         return
        print('self.last_ask_price ==>',self.last_ask_price)
        print('self.last_bid_price ==>',self.last_bid_price)
        if self.last_bid_price==0 or self.last_ask_price==0:
            return False
        if side == 'buy' and (self.last_bid_price / price) > self.t_rate:
            return True
        elif side == 'sell' and (price / self.last_ask_price) > self.t_rate:
            return True
        return False

    def update_last_price(self, side, price):

        if side == 'buy':
            min_sell_price = self.order_manager.update_sell_list(price)
            self.last_bid_price = min_sell_price/self.t_rate
        elif side == 'sell':
            max_buy_price = self.order_manager.update_buy_list(price)
            self.last_ask_price = max_buy_price*self.t_rate

    def handle_data(self, data):
        if time.time() - data['datetime'].timestamp() > 0.1:  #延时大放弃
            print('datetime==>', data['datetime'])
            return
        ask_one = data['asks'][-1]['price']
        bid_one = data['bids'][0]['price']
        bast_price = bid_one
        bast_c_price = ask_one
        if self.main_side == 'sell':
            bast_price = ask_one
            bast_c_price = bid_one

        print('bid_one==>', bid_one)
        print('ask_one==>', ask_one)
        print('bast_price==>', bast_price)
        print('bast_c_price==>', bast_c_price)
        print('self.last_bid_price=>', self.last_bid_price)
        print('self.last_ask_price=>', self.last_ask_price)

        #检查position是否还可以下单, 用base作为控仓
        base_position = self.order_manager.check_position(self.base)
        base_balance = float(base_position['balance'])
        if self.init_base == 0:  #记住当前仓位
            self.init_base = base_balance

        if self.init_base == base_balance:
            self.last_bid_price = 0
            self.last_ask_price = 0

        print('base_position=>', base_position)
        if base_balance >= self.limit_base_position_size:  #position已经到上限
            print('###over position')
            return
        #====================================================================
        order_info = self.order_manager.get_last_order_info()
        print('order_info=>', order_info)
        if order_info == None:  #下第一张单
            if (self.main_side == 'buy' and self.last_bid_price == 0) or (self.main_side == 'sell' and self.last_ask_price == 0) or self.signal(self.main_side, bast_price):
                self.submit_order(self.main_side, bast_price)
            else:
                self.update_last_price(self.main_side, bast_c_price)
            return

        status = order_info['status']
        last_order_price = float(order_info['price'])
        order_id = order_info['order_id']

        if status == 'filled':  # 已经fill
            # 下相反的订单,平仓
            price = last_order_price / self.t_rate
            side = 'buy'
            if self.main_side == 'buy':
                side = 'sell'
                price = last_order_price * self.t_rate
            self.submit_order(side, price, order_record=False, close_record=True)
            self.order_manager.del_order()
            # 下新的订单开仓
            if self.signal(self.main_side, bast_price):
                self.submit_order(self.main_side, bast_price)

            self.last_bid_price = last_order_price
            self.last_ask_price = last_order_price

        elif bast_price != last_order_price:
            # 撤销订单
            self.order_manager.cancel_order(order_id, self.spot_pair)
            self.order_manager.del_order()
        else:  # 继续等
            pass

    def run(self):
        for item in self.ps.listen():  #监听状态：有消息发布了就拿过来
            if item['type'] == 'message':
                data = json.loads(item['data'], cls=JSONDateTimeDecoder)
                self.handle_data(data)


def main():
    print('#main start#')
    strategy = Strategy()
    strategy.run()


if __name__ == '__main__':
    main()
