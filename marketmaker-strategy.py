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
        self.spot_api = spot_api.SpotAPI(config.apikey, config.secretkey, config.password, True)
        self.order_router = []
        self.sell_list = []

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
    def del_order(self,order_id=None):
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
                     order_record=True):
        order_info =  None             
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
            return 		
        order_id = order_info['order_id']
        if side == 'sell':
            self.sell_list.append(
                {
                    'order_id': order_id,
                    'instrument_id': instrument_id,
                    'side': side,
                    'price': price
                    # 'status': 'pending'
                }
            )
            print('#self.sell_list=>', self.sell_list)

        if order_record == False:
            return order_info

        
        time.sleep(0.05)
        print('#####instrument_id=>', instrument_id)
        print('#####order_id=>', order_id)
        try:
            order = self.spot_api.get_order_info(order_id, instrument_id)
            print('spot order2==>', order)
        except:
            self.add_order(instrument_id=instrument_id, price=price, t_price=0, size=size, side=side, order=order_info)
            print('spot read order info err')
            return

        while wait_flag: 
            time.sleep(0.2)
            # order = self.spot_api.get_order_info(order_id, instrument_id)
            try:
                order = self.spot_api.get_order_info(order_id, instrument_id)
                if order['status'] == 'filled':  #部分成交 全部成交 撤单
                    return order
            except:
                print('spot read order info err')
        self.add_order(instrument_id=instrument_id, price=price, t_price=0, size=size, side=side, order=order)

        return order


    def cancel_order(self, order_id, instrument_id):
        return self.spot_api.revoke_order(order_id, instrument_id)

    def get_order_info(self, order_id, instrument_id):
        return self.spot_api.get_order_info(order_id, instrument_id)
    
    def get_last_order_info(self):
        if len(self.order_router) == 0:
            return None
        order = self.order_router[-1]
        return self.get_order_info(order['order']['order_id'], order['instrument_id'])

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

class Strategy():
    def __init__(self):
        r = redis.Redis(host='127.0.0.1', port=6379, password='nowdone2go', decode_responses=True)
        #r = redis.Redis(host='127.0.0.1', port=6379, decode_responses=True)
        self.ps = r.pubsub()
        self.spot_pair = 'EOS-USDT'
        self.base = 'EOS'
        self.quote = 'USDT'
        subscribe_msg = 'okex.order_book.EOS/USDT' 
        self.ps.subscribe([subscribe_msg])  #订阅消息
        self.order_manager = OrderManager()
        self.spot_size = 0.1
        self.limit_base_position_size = config.max_limit_base_position
        self.t_rate = 1.0005 + 0.002 * 0.13
        self.last_bid_price = 0
        self.init_base = 0
       
    

    def handle_data(self, data):
        if time.time() - data['datetime'].timestamp() > 0.1: #延时大放弃
            print('datetime==>', data['datetime'])
            return
        ask_one = data['asks'][-1]['price']
        # ask_one_amount = data['asks'][-1]['amount']
        bid_one = data['bids'][0]['price']
        # bid_one_amount = data['bids'][0]['amount']
        print('bid_one==>',bid_one)
        print('self.last_bid_price=>', self.last_bid_price)
        #检查position是否还可以下单
        base_position = self.order_manager.check_position(self.base)
        base_balance = float(base_position['balance'])
        if self.init_base == 0:
            self.init_base = base_balance
            
        if self.init_base == base_balance:
            self.last_bid_price = 0
            
        print('base_balance=>',base_balance)
        if base_balance >= self.limit_base_position_size: #position已经到上限
            return 
        #====================================================================
        order_info = self.order_manager.get_last_order_info()
        print('order_info=>', order_info)
        if order_info == None: #下第一张单
            if self.last_bid_price != 0 and (self.last_bid_price/bid_one) < self.t_rate:
                min_sell_price = self.order_manager.update_sell_list(ask_one)
                self.last_bid_price = min_sell_price/self.t_rate
                return

            spot_price = bid_one
            self.order_manager.submit_spot_order(client_oid='',
                                            otype='limit', 
                                            side='buy', 
                                            instrument_id=self.spot_pair,
                                            size=self.spot_size,
                                            price=spot_price, 
                                            notional='')

            return 

        status = order_info['status']
        last_order_price = float(order_info['price'])
        order_id = order_info['order_id']
        
        if status == 'filled': # 已经fill
            # 下相反的订单
            spot_price = last_order_price * self.t_rate
            #notional = self.spot_size * spot_price
            self.order_manager.submit_spot_order(client_oid='',
                                            otype='limit', 
                                            side='sell', 
                                            instrument_id=self.spot_pair,
                                            size=self.spot_size,
                                            price=spot_price, 
                                            notional='',
                                            order_record=False)
            #====================================================================
            t_rate = (last_order_price/bid_one)
            print('t_rate=>', t_rate, 'self.t_rate==>', self.t_rate)
            if t_rate >= self.t_rate:
                spot_price = bid_one
                #notional = self.spot_size * spot_price
                self.order_manager.submit_spot_order(client_oid='',
                                                otype='limit', 
                                                side='buy', 
                                                instrument_id=self.spot_pair,
                                                size=self.spot_size,
                                                price=spot_price, 
                                                notional='')
            self.order_manager.del_order()
            self.last_bid_price = last_order_price

        elif bid_one != last_order_price:
            # 撤销订单
            self.order_manager.cancel_order(order_id, self.spot_pair)
            self.order_manager.del_order()
        else: # 继续等
            pass

    def run(self):
        for item in self.ps.listen():		#监听状态：有消息发布了就拿过来
            if item['type'] == 'message':
                data = json.loads(item['data'], cls=JSONDateTimeDecoder)
                self.handle_data(data)

        #notional = 2 * self.spot_size
        # self.order_manager.submit_spot_order(client_oid='',
        #                                        otype='limit', 
        #                                         side='buy', 
        #                                         instrument_id=self.spot_pair,
        #                                         size=self.spot_size,
        #                                         price=2, 
        #                                         notional='')

        # base_position = self.order_manager.check_position(self.base)
        # print('base_position=>', base_position)
        # print('order router =>', self.order_manager.order_router)
        # order_info = self.order_manager.get_last_order_info()
        # print('order_info', order_info)
        # self.order_manager.cancel_order('2440319292018688', self.spot_pair)
        # order = self.order_manager.spot_api.get_order_info('2442411268776960', self.spot_pair)
        # print('order=>', order)


def main():    
    print('#main start#')
    strategy = Strategy()
    strategy.run()


if __name__ == '__main__':
    main()
