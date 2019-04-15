
import okex.spot_api as spot_api
import time

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
            return None

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

    