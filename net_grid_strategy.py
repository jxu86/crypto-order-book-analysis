
import sys
import redis
import json
import okex.spot_api as spot_api
import config
import utils
from utils import JSONDateTimeDecoder
import datetime
import time
import uuid
import argparse
import math
from signals import net_grid
# from interval import Interval
import pandas as pd
import common
from common import StrategyParams
from order_service import OrderRouter

class Strategy():
    def __init__(self, params):

        self.r = redis.Redis(
            host='127.0.0.1',   
            # host='10.10.20.60',
            port=6379,
            password='nowdone2go',
            decode_responses=True)

        self.spot_pair = 'EOS-USDT'
        self.base = 'EOS'
        self.quote = 'USDT'
        # subscribe_msg = 'okex.order_book.EOS/USDT'
        subscribe_msg = common.redis_subscribe_msg[self.spot_pair]
        print('subscribe_msg=>', subscribe_msg)
        self.ps = self.r.pubsub()
        self.ps.subscribe([subscribe_msg])  #订阅消息

        self.net_grid = net_grid.NetGridSignal(params.high_price, params.low_price, params.grid_num)
        # 格子价格list
        self.grid_list = self.net_grid.calc_price_interval()
        # 格子序号
        self.grid_index = [i for i in range(len(self.grid_list)-1)]

        self.start_flag = False
        # 当前价格所在的格子
        self.current_index = 0
        # 当前订单list
        self.order_list = []

        self.order_router =  OrderRouter(params.apikey, params.secretkey, params.passphrase)
        self.order_size = params.order_size
        self.base_init_amount = 0
        self.quote_init_amount = 0
        self.grid_num = params.grid_num
        self.pending_orders = self.get_pending_orders(self.spot_pair)
        print('grid_list=>', self.grid_list)
        print('grid_index=>', self.grid_index)

    # 计算一开始撒网的价格
    def get_net_order(self, bid, ask):
        mid_price = round((bid+ask)/2, 3)
        low_price = min(self.grid_list)
        high_price = max(self.grid_list)
        self.base_init_amount = 0
        self.quote_init_amount = 0
        if mid_price < low_price:
            # 全部卖
            self.current_index = 0
        elif mid_price >= high_price:
            # 全部买
            self.current_index = len(self.grid_list) - 1 
        else:
            #当前价格在格子的位置
            self.current_index = pd.cut([mid_price], self.grid_list, right=False, labels=self.grid_index)[0]

        order_list = []
        for index in range(len(self.grid_list)):
            # print('index=>', index)
            if index < self.current_index:
                order_list.append({
                    'side': 'buy',
                    'price': self.grid_list[index]
                })
                self.quote_init_amount += self.order_size * self.grid_list[index]
            elif index > self.current_index:
                order_list.append({
                    'side': 'sell',
                    'price': self.grid_list[index]
                })
                self.base_init_amount += self.order_size
            else:
                order_list.append({
                    'side': 'hold',
                    'price': self.grid_list[index]
                })

        self.base_init_amount = round(self.base_init_amount, 10)
        self.quote_init_amount = round(self.quote_init_amount, 10)
        print('mid_price=>', mid_price)
        print('order_list=>', order_list)
        print('current_index=>', self.current_index)
        print('base_init_amount=>', self.base_init_amount)
        print('quote_init_amount=>', self.quote_init_amount)
        return order_list

    # 检查订单是否已经存在
    def find_open_order(self, side, price):
        order = [o for o in self.pending_orders if o['side']==side and o['price']==price]
        if len(order) == 0:
            return None
        else:
            return order[0]
    # 撒网
    def throw_net(self, bid, ask):
        orders = self.get_net_order(bid, ask)
        
        for o in orders:
            if o['side'] == 'hold':
                self.order_list.append(o)
                continue

            open_order = self.find_open_order(o['side'], o['price'])
            print('###open_order=>', open_order)

            #检查订单是否存在
            if open_order != None:
                self.order_list.append(open_order)
                continue
            
            c_time = str(int(time.time()*1000))
            client_oid = 'grid'+c_time + 's'
            print(client_oid)
            order_info = self.order_router.submit_spot_order(client_oid, 'limit', o['side'], self.spot_pair, o['price'], self.order_size, '')
            # TODO 处理下单不成功的情况
            self.order_list.append(order_info)

        print('self.order_list=>', self.order_list)

    # 补网
    def fix_net(self, index, fix_index, side):
        trade_price = self.grid_list[fix_index]
        # filled_order = self.order_list[index]
        filled_client_oid = self.order_list[index]['client_oid']
        # 后面根据client_oid计算realized profit
        if filled_client_oid[-1] == 's':
            client_oid = filled_client_oid.replace('s', 'e')
        else:
            c_time = str(int(time.time()*1000))
            client_oid = 'grid'+c_time + 's'
        
        order_info = self.order_router.submit_spot_order(client_oid, 'limit', side, self.spot_pair, trade_price, self.order_size, '')
        self.order_list[fix_index] = order_info
        self.current_index = index

    # 检查
    def check_net(self, bid, ask):
        previous_index = self.current_index - 1
        next_index = self.current_index + 1
        previous_order = self.order_list[previous_index]
        next_order = self.order_list[next_index]

        previous_order_info = self.order_router.get_order_info(previous_order['order_id'], self.spot_pair)
        print('previous_order_info=>', previous_order_info)
        # 买单成交
        if previous_order_info['status'] == 'filled':
            self.order_list[previous_index] = previous_order_info
            self.fix_net(previous_index, self.current_index, 'sell')
            return
        time.sleep(0.05)
        next_order_info = self.order_router.get_order_info(next_order['order_id'], self.spot_pair)
        print('next_order_info=>', next_order_info)
        # 卖单成交
        if next_order_info['status'] == 'filled':
            self.order_list[next_index] = next_order_info
            self.fix_net(next_index, self.current_index, 'buy')
            return

        print('self.order_list =>', self.order_list)


    def get_pending_orders(self, instrument_id):
        pending_orders = self.order_router.get_orders_pending(instrument_id)
        pending_orders = list(pending_orders[0])
        print('pending_orders=>', pending_orders)
        print('pending_orders len=>', len(pending_orders))
        return pending_orders

    def handle_data(self, data):
        ask_one = data['asks'][-1]['price']
        bid_one = data['bids'][0]['price']
        print('ask_one=>', ask_one)
        print('bid_one=>', bid_one)
        if self.start_flag:
            print('###check net status')
            #检查网格状态
            self.check_net(bid_one, ask_one)
        else:
            # 第一次进来需要布网
            self.throw_net(bid_one, ask_one)
            self.start_flag = True

    def run(self):
        for item in self.ps.listen():  #监听状态：有消息发布了就拿过来
            if item['type'] == 'message':
                data = json.loads(item['data'], cls=JSONDateTimeDecoder)
                self.handle_data(data)

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--apikey',
        type=str,
        help='apikey')
    parser.add_argument(
        '--secretkey',
        type=str,
        help='secretkey')
    parser.add_argument(
        '--passphrase',
        type=str,
        help='passphrase')

    args = parser.parse_args()
    return args


def main():
    print('#main start#')
    args = parse_args()
    print('args ==>', args)

    params = {
        'apikey': args.apikey, 
        'secretkey': args.secretkey, 
        'passphrase': args.passphrase, 
        'high_price': 5.5, 
        'low_price': 4.9, 
        'grid_num': 30,
        'order_size': 0.1
    }
    strategy = Strategy(StrategyParams(**params))
    strategy.run()

if __name__ == '__main__':
    main()