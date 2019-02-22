import okex.spot_api as spot_api
import okex.futures_api as futures_api
from mongo_service.mongodb import MongoService
import config
import email_service.e as e
import uuid
import datetime
import time
import constant

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
        self.e = e.EmailService()

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
            time.sleep(0.1)
            order = self.future_api.get_order_info(order_id, instrument_id)
            print('####submit_order=>order==>', order)
            if order['status'] != '0':  #部分成交 全部成交 撤单
                return order
        try:
            self.e.sumit_order(order)
        except:
            pass

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

    def add_order(self,
                  instrument_id,
                  price,
                  t_price,
                  sl_price,
                  size,
                  side,
                  strategy_name='future_ema'):
        order = {
            'uuid': str(uuid.uuid1()),
            'type': 'future',  #合约
            'instrument_id': instrument_id,
            'strategy_name': strategy_name,  #策略名称
            's_price': price,  # 开始价格
            't_price': t_price,  # 目标价格
            'sl_price': sl_price,  # 止损价格
            'e_price': 0,  # 最后价格
            'side': side,  # buy or sell
            'size': size,  # 目标下单数量，张数
            'status': 'pending',  # 状态 'pending' 'done' 'cancel'
            'stime': datetime.datetime.now(),  #开始时间
            'etime': 0,  #结束时间
            'strategy_status':
            'start',  #策略状态，start, order_submit, order_filled, p_order_sumbit, p_order_filled, stop_loss,done, cancel
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
        if order_status == constant.OrderStatus.CANCELED.value:  # 取消订单
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
                self.cancel_order(order['instrument_id'],
                                  order_info['order_id'])
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
        elif strategy_status == 'stop_loss_sumbit':  # 止损
            _, otype = self.get_order_otype(order['side'])
            order['strategy_status'] = 'stop_loss_filled'
            sl_order_info = self.submit_order(
                client_oid='',
                otype=otype,
                instrument_id=order['instrument_id'],
                price=order['sl_price'],
                size=order['order']['filled_qty'])
            order['p_order'] = sl_order_info

        elif strategy_status == 'stop_loss_filled':  # 止损
            order_info = self.get_order_info(order['instrument_id'],
                                             order['p_order']['order_id'])
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
        if len(self.order_router) == 0:  # 没有需要执行的订单任务
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
                        'strategy_status']:  # 状态有变化需要update到mongo
                self.save_order(order_info)
        self.order_router = new_order_router
        return len(self.order_router)