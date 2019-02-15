import okex.spot_api as spot_api
import okex.futures_api as futures_api
import config
import time


# TODO 
# 爆仓处理

class Strategy(object):
    def __init__(self):
        self.future_instrument_id = 'EOS-USD-190329'
        self.spot_instrument_id = 'EOS-USDT'
        self.spot_base = 'EOS'
        self.spot_quote = 'USDT'
        self.spread_rate = 0.034
        self.future_size = 1
        self.spot_api = spot_api.SpotAPI(config.sub_apikey, config.sub_secretkey, config.sub_password, True)
        self.future_api = futures_api.FutureAPI(config.sub_apikey, config.sub_secretkey, config.sub_password, True)

    def get_future_position(self, margin_mode='crossed'):
        position = self.future_api.get_specific_position(self.future_instrument_id)
        # print('######position=>', position)
        if position['result'] == True:
            for h in position['holding']:
                if h['instrument_id'] == self.future_instrument_id and h['margin_mode'] == margin_mode:
                    return h
        return {}

    def check_spread(self):
        future_ticker = self.future_api.get_specific_ticker(instrument_id=self.future_instrument_id)
        future_last = float(future_ticker['last'])
        spot_ticker = self.spot_api.get_specific_ticker(instrument_id=self.spot_instrument_id)
        spot_last = float(spot_ticker['last'])
        spread = round(spot_last-future_last, 5)
        min_last = min(spot_last, future_last)
        spread_rate = spread/min_last
        return spread, spread_rate

    def is_close_order(self):
        pass

    def signal(self):
        sig = 'no'
        spread, spread_rate = self.check_spread()
        print('####spread, spread_rate==>', spread, spread_rate)
        if abs(spread_rate) >= self.spread_rate and spread_rate > 0:
            sig = 'future_buy'
        elif abs(spread_rate) >= self.spread_rate and spread_rate < 0:
            sig = 'future_sell'
        sig = 'future_sell'
        print('########signal=>', sig)
        return sig
    
    # 检查是否已经交易=>检查合约账户是否有持仓
    def is_trade_complete(self):
        future_position = self.get_future_position()
        print('#####future_position=>', future_position)
        if future_position == {}:
            return False

        if float(future_position['long_avail_qty']) != 0 or float(future_position['short_avail_qty']) != 0:
            return True
        else:
            return False

    # 下单程序
    # client_oid 由您设置的订单ID来识别您的订单
    # instrument_id
    # otype string 1:开多2:开空3:平多4:平空
    # price string 每张合约的价格
    # size Number 买入或卖出合约的数量（以张计数）
    # match_price string 是否以对手价下单(0:不是 1:是)，默认为0，当取值为1时。price字段无效
    # leverage Number 要设定的杠杆倍数，10或20
    def submit_future_order(self,
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
            print('#######submit_future_order=>e==>')

        order_id = order_info['order_id']
        time.sleep(0.1)
        order = self.future_api.get_order_info(order_id, instrument_id)
        while wait_flag: 
            time.sleep(0.5)
            order = self.future_api.get_order_info(order_id, instrument_id)
            if order['status'] != '0':  #部分成交 全部成交 撤单
                return order
        return order

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
        try:
            order_info = self.spot_api.take_order(
                client_oid=client_oid,
                instrument_id=instrument_id,
                otype=otype,
                side=side,
                size=size,
                price=price)
        except:
            print('#######submit_spot_order=>e==>')

        order_id = order_info['order_id']
        time.sleep(0.1)
        print('#####instrument_id=>', instrument_id)
        print('#####order_id=>', order_id)
        order = self.spot_api.get_order_info(order_id, instrument_id)
        while wait_flag: 
            time.sleep(0.5)
            order = self.spot_api.get_order_info(order_id, instrument_id)
            if order['status'] == 'filled':  #部分成交 全部成交 撤单
                return order
        return order



    # 下单，合约为限价单，币币为市价单
    def make_order(self, future_side):
        otype = '1'
        spot_side = 'sell'
        future_ticker = self.future_api.get_specific_ticker(instrument_id=self.future_instrument_id)
        future_price = float(future_ticker['best_ask'])

        spot_ticker = self.spot_api.get_specific_ticker(instrument_id=self.spot_instrument_id)
        spot_price = float(spot_ticker['best_bid'])

        if future_side == 'future_sell':
            otype = '2'
            future_price = float(future_ticker['best_bid'])
            spot_side = 'buy'
            spot_price = float(spot_ticker['best_ask'])
        print('###instrument_id=>',self.future_instrument_id)
        print('###otype=>',otype)
        print('###future_price=>',future_price)
        print('###self.future_size=>',self.future_size)
        
        # 合约下单
        # future_order_info = self.submit_future_order(client_oid='',
        #                                                 otype=otype,
        #                                                 instrument_id=self.future_instrument_id,
        #                                                 price=future_price,
        #                                                 size=self.future_size,
        #                                                 wait_flag=True)
        # print('###future_order_info==>', future_order_info)

        # future_size = future_order_info['size']
        # price_avg = future_order_info['price_avg']
        # spot_size = future_size * 10 / price_avg  # 10美元一张合约，btc为100美元
        # notional = spot_size * spot_price

        # 现货下单
        # spot_order_info = self.submit_spot_order(client_oid='',otype='market', side=spot_side, instrument_id=self.spot_instrument_id,size=spot_size,price=spot_price, notional=notional)

    #平仓
    def close_order(self):
        # 合约平仓
        future_position = self.get_future_position()
        long_avail_qty = float(future_position['long_avail_qty'])
        short_avail_qty = float(future_position['short_avail_qty'])

        future_side = ''
        if long_avail_qty != 0:
            future_side = 'future_buy'
        elif short_avail_qty != 0:
            future_side = 'future_sell'

        otype = '3'
        future_ticker = self.future_api.get_specific_ticker(instrument_id=self.future_instrument_id)
        future_price = float(future_ticker['best_ask'])
        if future_side == 'future_sell':
            otype = '4'
            future_price = float(future_ticker['best_bid'])

        # 合约下单
        future_order_info = self.submit_future_order(client_oid='',
                                                        otype=otype,
                                                        instrument_id=self.future_instrument_id,
                                                        price=future_price,
                                                        size=self.future_size)
        
        # 现货平仓
        spot_ticker = self.spot_api.get_specific_ticker(instrument_id=self.spot_instrument_id)
        if future_side == 'future_buy': # 买单
            spot_side = 'buy'
            spot_quote_info = self.spot_api.get_coin_account_info(self.spot_quote)
            notional = spot_quote_info['available']
            spot_size = notional/float(spot_ticker['best_ask'])
            spot_order_info = self.submit_spot_order(client_oid='',otype='market', side=spot_side, instrument_id=self.spot_instrument_id, size=spot_size, price=spot_price, notional=notional)
        elif future_side == 'future_sell': # 卖单
            spot_side = 'sell'
            spot_base_info = self.spot_api.get_coin_account_info(self.spot_base)
            spot_size = spot_base_info['available']
            notional = float(spot_ticker['best_bid']) * spot_size
            spot_order_info = self.submit_spot_order(client_oid='',otype='market', side=spot_side, instrument_id=self.spot_instrument_id, size=spot_size, price=spot_price, notional=notional)
        
    def run(self):

        # spot_order_info = self.submit_spot_order(client_oid='',otype='limit', side='sell', instrument_id=self.spot_instrument_id,size=0.1,price=10, notional='', wait_flag=True)
        # print('######spot_order_info=>', spot_order_info)

        # spot_base_info = self.spot_api.get_coin_account_info(self.spot_quote)
        # print('######spot_base_info=>', spot_base_info)

        # while True:
        #     # 已经下单，等平仓
        #     if self.is_trade_complete() == True:
        #         # if self.is_close_order():
        #         #     self.close_order()
        #         print('########wait close order')
        #     else:
        #         sig = self.signal() # 等待开仓信号
        #         if  sig != 'no': 
        #             self.make_order(sig)
        #     time.sleep(1)

def main():
    print('###main start###')
    strategy = Strategy()
    strategy.run()
    print('###main end###')


if __name__ == '__main__':
    main()