
import okex.spot_api as spot_api
import time
import datetime
import utils
class OrderRouter(object):
    def __init__(self, apikey, secretkey, password):
        self.spot_api = spot_api.SpotAPI(apikey, secretkey, password, True)

    def check_position(self, symbol):
        return self.spot_api.get_coin_account_info(symbol)

    def submit_spot_order(self,
                          client_oid,
                          otype,
                          side,
                          instrument_id,
                          price,
                          size,
                          notional,
                          timeout=20,
                          wait_flag=False):
        print('###submit_spot_order=>side==>',side,' ==>', price)
        order_info = None
        try:
            order_info = self.spot_api.take_order(
                client_oid=client_oid,
                instrument_id=instrument_id,
                otype=otype,
                side=side,
                size=size,
                price=price)
            print('submit_spot_order=>order_info==>', order_info)
        except:
            print('#######submit_spot_order=>e==>')
            return None

        time.sleep(0.08)
        order_id = order_info['order_id']
        try:
            order = self.spot_api.get_order_info(order_id, instrument_id)
            print('spot order2==>', order)
        except:
            # self.add_order(instrument_id=instrument_id, price=price, t_price=0, size=size, side=side, order=order_info)
            print('spot read order info err')
            return order_info

        while wait_flag:
            time.sleep(0.2)
            try:
                order = self.spot_api.get_order_info(order_id, instrument_id)
                if order['status'] == 'filled':  #部分成交 全部成交 撤单
                    return order
            except:
                print('spot read order info err')
        # self.add_order(instrument_id=instrument_id, price=price, t_price=0, size=size, side=side, order=order)

        return order

    def get_order_info(self, order_id, instrument_id):
        return self.spot_api.get_order_info(order_id, instrument_id)


    def cancel_order(self, order_id, instrument_id):
        ret = self.spot_api.revoke_order(order_id, instrument_id)
        return ret

    def cancel_orders(self, instrument_id, order_ids):
        ret = self.spot_api.revoke_orders(instrument_id, order_ids)
        return ret
    

    def get_orders_pending(self, instrument_id):
        return self.spot_api.get_orders_pending(froms='', to='', limit='100', instrument_id=instrument_id)

    def get_kline(self, instrument_id, start, end, granularity):
        klines = self.spot_api.get_kline(instrument_id, start, end, granularity)
        if klines and len(klines):
            fields = [
                'timestamp', 'open', 'high', 'low', 'close', 'volume'
            ]
            return [dict(zip(fields, r)) for r in klines]
        return None 

    def get_ticker(self, instrument_id):
        return self.spot_api.get_specific_ticker(instrument_id)

    def get_orders(self, symbol, stime, etime, status=''):
        to = None
        order_list = []
        last_order = {}
        after = ''
        while True:
            if to == None:
                orders = self.spot_api.get_orders_list(status, symbol)
            else:
                orders = self.spot_api.get_orders_list(status, symbol, to=to)
            order_position = orders[1]
            orders = list(orders[0])
            # print('order_position=>', order_position)
            
            if len(orders) <= 0:
                break 
        
            after = order_position['after']
            if len(order_list) and order_list[-1] == orders[0]:
                order_list = order_list + orders[1:]
            else:
                order_list = order_list + orders

            if stime == '' and etime == '':
                break
            # print('orders len=>', len(order_list))
            if utils.utcstr_to_datetime(order_list[-1]['timestamp']) <= stime:
                break

            if to == order_list[-1]['order_id']:
                break
            to = order_list[-1]['order_id']
            time.sleep(1)
        new_order_list = []
        for l in order_list:
            l['created_at'] = utils.utcstr_to_datetime(l['created_at'])
            l['datetime'] = utils.utcstr_to_datetime(l['timestamp'])
            l['filled_notional'] = float(l['filled_notional'])
            l['filled_size'] = float(l['filled_size'])
            if l['price']:
                l['price'] = float(l['price'])
            else:
                l['price'] = 0
            l['size'] = float(l['size'])
            if stime == '' and etime == '':
                new_order_list.append(l)
            elif l['datetime'] >= stime and l['datetime']<=etime:
                new_order_list.append(l)
            l = str(l)
        return new_order_list