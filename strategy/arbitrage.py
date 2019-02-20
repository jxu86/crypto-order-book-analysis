import okex.spot_api as spot_api
import okex.futures_api as futures_api
import config
import time


# TODO 
# 爆仓处理

class Strategy(object):
    def __init__(self):
        self.future_instrument_id = 'EOS-USD-190329'
        # self.future_instrument_id = 'EOS-USD-190301'
        self.spot_instrument_id = 'EOS-USDT'
        self.spot_base = 'EOS'
        self.spot_quote = 'USDT'
        self.spread_rate = 0.0256
        self.close_spread_rate = 0.023
        self.future_size = 1
        self.spot_api = spot_api.SpotAPI(config.jxukalengo_apikey, config.jxukalengo_secretkey, config.jxukalengo_passphrase, True)
        self.future_api = futures_api.FutureAPI(config.jxukalengo_apikey, config.jxukalengo_secretkey, config.jxukalengo_passphrase, True)

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
        print('###future_last=>', future_last)
        print('###spot_last=>', spot_last)
        return spread, spread_rate

    def is_close_order(self):
        spread, spread_rate = self.check_spread()
        print('####spread, spread_rate==>', spread, spread_rate)
        if abs(spread_rate) < self.close_spread_rate:
            return True
        return False

    def signal(self):
        sig = 'no'
        spread, spread_rate = self.check_spread()
        print('####spread, spread_rate==>', spread, spread_rate)
        if abs(spread_rate) >= self.spread_rate and spread_rate > 0:
            sig = 'future_buy'
        elif abs(spread_rate) >= self.spread_rate and spread_rate < 0:
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
                     match_price='1',
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
                     wait_flag=True):
        try:
            order_info = self.spot_api.take_order(
                client_oid=client_oid,
                instrument_id=instrument_id,
                otype=otype,
                side=side,
                size=size,
                notional=notional,
                price=price)
        except:
            print('#######submit_spot_order=>e==>')

        order_id = order_info['order_id']
        time.sleep(0.5)
        print('#####instrument_id=>', instrument_id)
        print('#####order_id=>', order_id)
        try:
            order = self.spot_api.get_order_info(order_id, instrument_id)
            print('spot order2==>', order)
        except:
            print('spot read order info err')

        while wait_flag: 
            time.sleep(0.2)
            # order = self.spot_api.get_order_info(order_id, instrument_id)
            try:
                order = self.spot_api.get_order_info(order_id, instrument_id)
                if order['status'] == 'filled':  #部分成交 全部成交 撤单
                    return order
            except:
                print('spot read order info err')
            
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
        future_order_info = self.submit_future_order(client_oid='',
                                                        otype=otype,
                                                        instrument_id=self.future_instrument_id,
                                                        price=future_price,
                                                        size=self.future_size,
                                                        wait_flag=True)
        print('###future_order_info==>', future_order_info)

        future_size = float(future_order_info['size'])
        price_avg = float(future_order_info['price_avg'])
        spot_size = future_size * 10 / price_avg  # 10美元一张合约，btc为100美元
        notional = spot_size * spot_price

        # 现货下单
        spot_order_info = self.submit_spot_order(client_oid='',otype='market', side=spot_side, instrument_id=self.spot_instrument_id,size=spot_size,price=spot_price, notional=notional)
        print('#####spot_order_info=>', spot_order_info)

    #平仓
    def close_order(self):
        # 合约平仓
        future_position = self.get_future_position()
        long_avail_qty = float(future_position['long_avail_qty'])
        short_avail_qty = float(future_position['short_avail_qty'])

        future_side = ''
        future_size = 0
        if long_avail_qty > 0:
            future_side = 'future_buy'
            future_size = long_avail_qty
        elif short_avail_qty > 0:
            future_side = 'future_sell'
            future_size = short_avail_qty

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
                                                        size=self.future_size, 
                                                        wait_flag=True)
        
        # 现货平仓
        spot_ticker = self.spot_api.get_specific_ticker(instrument_id=self.spot_instrument_id)
        spot_price = float(spot_ticker['last'])
        if future_side == 'future_buy': # 买单
            spot_side = 'buy'
            spot_quote_info = self.spot_api.get_coin_account_info(self.spot_quote)
            notional = float(spot_quote_info['available'])
            spot_size = notional/float(spot_ticker['best_ask'])
            # spot_order_info = self.submit_spot_order(client_oid='',otype='market', side=spot_side, instrument_id=self.spot_instrument_id, size=spot_size, price=spot_price, notional=notional)
        elif future_side == 'future_sell': # 卖单
            spot_side = 'sell'
            spot_base_info = self.spot_api.get_coin_account_info(self.spot_base)
            spot_size = spot_base_info['available']
            notional = float(spot_ticker['best_bid']) * spot_size
        
        print('########spot_side=>', spot_side)
        print('########spot_size=>', spot_size)
        print('########spot_price=>', spot_price)
        print('########notional=>', notional)
        spot_order_info = self.submit_spot_order(client_oid='',otype='market', side=spot_side, instrument_id=self.spot_instrument_id, size=spot_size, price=spot_price, notional=notional)
        print('########spot_order_info=>', spot_order_info)

    def run(self):
        # order = self.spot_api.get_order_info('2341139016915968', 'EOS-USDT')
        # print('#order==>', order)
        # print('#order type==>', type(order))
        while True:
            # 已经下单，等平仓
            if self.is_trade_complete() == True:
                # if self.is_close_order():
                #     print('###################is_close_order')
                #     self.close_order()
                print('########wait close order')
            else:
                sig = self.signal() # 等待开仓信号
                # if  sig != 'no': 
                #     self.make_order(sig)
            time.sleep(1)

def main():
    print('###main start###')
    strategy = Strategy()
    strategy.run()
    print('###main end###')


if __name__ == '__main__':
    main()

    # 43.6039 EOS
    # 5.1236+38.5140



    #38.43713115
    #5.1121
    # (0.0048*2.9375-(0.01537311+0.0153733)*0.15)/2.9375 = 0.0032299705531914883 EOS

    # 38.46803115+5.0876 = 43.55563115