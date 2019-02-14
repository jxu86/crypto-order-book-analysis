import okex.spot_api as spot_api
import okex.futures_api as futures_api
import config
import time



class Strategy(object):
    def __init__(self):
        self.future_instrument_id = 'EOS-USD-190329'
        self.spot_instrument_id = 'EOS-USDT'
        self.spot_base = 'EOS'
        self.spot_quote = 'USDT'
        self.spread_rate = 0.034
        self.future_size = 1
        self.spot_api = spot_api.SpotAPI(config.apikey, config.secretkey, config.password, True)
        self.future_api = futures_api.FutureAPI(config.apikey, config.secretkey, config.password, True)

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
                     instrument_id,
                     price,
                     size,
                     timeout=20,
                     wait_flag=False):
        try:
            order_info = self.spot_api.take_order(
                client_oid=client_oid,
                instrument_id=instrument_id,
                otype=otype,
                size=size,
                price=price)
        except:
            print('#######submit_spot_order=>e==>')

        order_id = order_info['order_id']
        time.sleep(0.1)
        order = self.spot_api.get_order_info(order_id, instrument_id)
        while wait_flag: 
            time.sleep(0.5)
            order = self.future_api.get_order_info(order_id, instrument_id)
            if order['status'] == 'filled':  #部分成交 全部成交 撤单
                return order
        return order


    # 下单，合约为限价单，币币为市价单
    def make_order(self, side):
        if side == 'future'
        future_order_info = self.submit_future_order(client_oid='',
                                                        otype=otype,
                                                        instrument_id=self.future_instrument_id,
                                                        price=order['s_price'],
                                                        size=order['size'])
        


        pass


    #平仓
    def close_order(self):

        pass

    def run(self):
        while True:
            # 已经下单，等平仓
            if self.is_trade_complete() == True:
                print('########wait close order')
            elif self.signal() != 'no': 

                pass
            time.sleep(1)


def main():
    print('###main start###')
    strategy = Strategy()
    strategy.run()
    print('###main end###')


if __name__ == '__main__':
    main()