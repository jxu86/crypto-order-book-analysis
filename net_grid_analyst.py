import argparse
from order_service import OrderRouter
import time
import datetime
from display import Display
import math
from mongo_service.mongodb import MongoService
import utils
class Analyst():
    def __init__(self, apikey, secretkey, passphrase, pair):
        self.order_router =  OrderRouter(apikey, secretkey, passphrase)
        self.pair = pair
        self.display = Display()
        self.display.set_win()
        # self._mongodb = MongoService('47.244.112.38', 57017, 'nowdone', 'nowdone2go')
        self._mongodb = MongoService('10.10.20.90', 3717, 'nowdone_read', 'klg2go', 'admin')

    def get_open_order(self, instrument_id):
        open_orders = self.order_router.get_orders_pending(instrument_id)
        open_orders = list(open_orders[0])
        return open_orders

    def wave_index(self):
        klines = self.order_router.get_kline('ETH-USDT','','',86400)

        period_kilne = klines[:7]
        print('period_kilne=>', period_kilne)
        highs = [float(k['high']) for k in period_kilne]
        lows = [float(k['low']) for k in period_kilne]

        highest = max(highs)
        lowest = max(lows)
        high = highs[0]
        low = lows[0]
        b = (high-low)/(highest-lowest)
        a = (high-low)/low
        wave_index = a * b
        print('wave_index=>', wave_index)

    def dis_profit_detail(self, strategy_info, orders, filled_orders, price):
        # display = Display()
        # display.set_win()
        # self.display.get_ch_and_continue()
        display = self.display
        x_axis = 0
        y_axis = 0
        y_axis_interval = 30
        base, quote = self.pair.split('-')
        display.display_info('投资回报分析(单位: {})'.format(quote), y_axis, x_axis)
        display.display_info('币对: {}'.format(self.pair), y_axis+30, x_axis)
        display.display_info('当前时间: {}'.format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), y_axis+60, x_axis)

        x_axis += 1
        # init_amount = strategy_info['init_base_amount'] * strategy_info['init_price'] + strategy_info['init_quote_amount']
        # init_amount = round(init_amount, 6)
        init_amount_text = '总成本: {init_amount}'.format(init_amount=strategy_info['init_amount'])
        display.display_info(init_amount_text, y_axis, x_axis)

        realized_profit_text = '实现利润: {realized_profit}({rate}%)'.format(realized_profit=strategy_info['realized_profit'], rate=round(strategy_info['rate']*100, 2))
        display.display_info(realized_profit_text, y_axis+y_axis_interval, x_axis)

        annual_rate_text = '年化利率: {annual_rate}%'.format(annual_rate=round(strategy_info['annual_rate'] * 100, 2))
        display.display_info(annual_rate_text, y_axis+y_axis_interval*2, x_axis)

        x_axis += 1

        fee_text = '手续费: {fee}'.format(fee=strategy_info['fee'])
        display.display_info(fee_text, y_axis, x_axis)

        unrealized_profit_text = '浮动盈亏: {unrealized_profit}'.format(unrealized_profit=strategy_info['unrealized_profit'])
        display.display_info(unrealized_profit_text, y_axis+y_axis_interval, x_axis)

        total_profit_text = '总利润: {total_profit}({total_rate}%)'.format(total_profit=strategy_info['total_profit'], total_rate=round(strategy_info['total_rate']*100, 2))
        display.display_info(total_profit_text, y_axis+y_axis_interval*2, x_axis)

        x_axis += 1
        price_text = '当前价格: {price}'.format(price=price)
        display.display_info(price_text, y_axis, x_axis)

        volume_text = '成交量: {}'.format(strategy_info['volume'])
        display.display_info(volume_text, y_axis + y_axis_interval, x_axis)

        x_axis += 2
        display.display_info('-'*100, y_axis, x_axis)
        x_axis += 1
        display.display_info('策略信息', y_axis, x_axis)
        x_axis += 2
        text = '开仓时间: {}'.format(strategy_info['stime'].strftime("%Y-%m-%d %H:%M:%S"))
        display.display_info(text, y_axis, x_axis)

        text = '运行了: {}'.format(strategy_info['run_time'])
        display.display_info(text, y_axis + y_axis_interval*2, x_axis)

        x_axis += 1
        text = '最高价: {}'.format(strategy_info['high_price'])
        display.display_info(text, y_axis, x_axis)
        text = '最低价: {}'.format(strategy_info['low_price'])
        display.display_info(text, y_axis+30, x_axis)

        text = '开仓价格: {}'.format(strategy_info['init_price'])
        display.display_info(text, y_axis+30*2, x_axis)

        x_axis += 1
        text = '网格数: {}'.format(strategy_info['grid_num'])
        display.display_info(text, y_axis, x_axis)

 
        text = '单网格买入数量: {}'.format(strategy_info['order_size'])
        display.display_info(text, y_axis+y_axis_interval, x_axis)

        text = '交易数: {}'.format(len(filled_orders))
        display.display_info(text, y_axis+y_axis_interval*2, x_axis)

        text = '配对数: {}'.format(strategy_info['pair_count'])
        display.display_info(text, y_axis+y_axis_interval*3, x_axis)
    

        x_axis += 1
        display.display_info('-'*100, y_axis, x_axis)



        # x_axis += 1
        # display.display_info('当前订单详情', y_axis, x_axis)

        x_axis += 1
        display.display_info('待成交订单({})'.format(len(orders)), y_axis, x_axis)
        x_axis += 2
        # def init_axis():
        buy_x_axis = x_axis
        buy_y_axis = y_axis
        sell_x_axis = x_axis
        sell_y_axis = y_axis + 20
        b_size = 0
        s_size = 0
        size_limit = 20

        
        buy_orders = [o for o in orders if o['side']=='buy']
        buy_orders.sort(key=lambda k: (k.get('price', 0)), reverse=True)
        sell_orders = [o for o in orders if o['side']=='sell']

        b_len = len(buy_orders)
        b_lows = math.ceil(b_len/size_limit)

        buy_y_axis += (b_lows - 1) * 20
        sell_y_axis = buy_y_axis + 20

        # for i in range(size_limit):
        #     display.display_info('|', buy_y_axis + 14, buy_x_axis + i)


        for o in buy_orders:
            order_text = '买: {}'.format(o['price'])
            display.display_info(' '*20, buy_y_axis, buy_x_axis)
            display.display_info(order_text, buy_y_axis, buy_x_axis, 2)
            b_size += 1
            buy_x_axis += 1
            if b_size % size_limit == 0:
                buy_x_axis = x_axis
                buy_y_axis -= 20   

        for o in sell_orders:
            order_text = '卖: {}'.format(o['price'])
            display.display_info(' '*20, sell_y_axis, sell_x_axis)
            display.display_info(order_text, sell_y_axis, sell_x_axis, 1)
            sell_x_axis += 1
            s_size += 1
            if s_size % size_limit == 0:
                sell_x_axis = x_axis
                sell_y_axis += 20 

        x_axis += size_limit
        if strategy_info['unpair_orders']:
            display.display_info('-'*100, y_axis, x_axis)
            x_axis += 1
            display.display_info('待匹配订单({})'.format(len(strategy_info['unpair_orders'])), 0, x_axis)
            x_axis += 2
            f_y_axis = 0
            f_x_axis = x_axis
            f_size = 0
            for o in strategy_info['unpair_orders']:
                side = '买'
                c = 2
                if o['side'] == 'sell':
                    side = '卖'
                    c = 1
                filled_order_info = '{dt} {client_oid} {side} {size} {price}'.format(dt=o['datetime'].strftime("%Y-%m-%d %H:%M:%S"), side=side, price=o['price'], size=o['size'], client_oid=o['client_oid'])
                display.display_info(filled_order_info, f_y_axis, f_x_axis, c)
                f_x_axis += 1
                f_size += 1
                if f_size % size_limit == 0:
                    f_x_axis = x_axis
                    f_y_axis += 60 


        # 已成交订单
        # x_axis += size_limit
        # display.display_info('-'*100, y_axis, x_axis)
        # x_axis += 1
        # display.display_info('最新成交订单', 0, x_axis)
        # x_axis += 2
        # f_y_axis = 0
        # f_x_axis = x_axis
        # f_size = 0
        # if len(filled_orders):
        #     filled_orders = filled_orders[:80]
        #     for o in filled_orders:
        #         side = '买'
        #         c = 2
        #         if o['side'] == 'sell':
        #             side = '卖'
        #             c = 1
        #         filled_order_info = '{dt} {client_oid} {side} {size} {price}'.format(dt=o['datetime'].strftime("%Y-%m-%d %H:%M:%S"), side=side, price=o['price'], size=o['size'], client_oid=o['client_oid'])
        #         display.display_info(filled_order_info, f_y_axis, f_x_axis, c)
        #         f_x_axis += 1
        #         f_size += 1
        #         if f_size % size_limit == 0:
        #             f_x_axis = x_axis
        #             f_y_axis += 60 


        # display.display_info('Press any key to continue...', 0, x_axis)
        # display.get_ch_and_continue()
    def read_strategy_info(self):
        strategy_info = self._mongodb.find(self._mongodb.strategy, {'name': 'g001'})
        print('strategy_info=>', strategy_info)
        return strategy_info

    def clac_profit(self, filled_orders, c_price):
        realized_profit = 0
        unrealized_profit = 0
        pair_count = 0
        unpair_orders = []
        
        s_orders_obj = {}
        s_orders = [o for o in filled_orders if o['client_oid'][-1] == 's']
        e_orders = [o for o in filled_orders if o['client_oid'][-1] == 'e']
        # print('s_orders=>', s_orders)
        for o in s_orders:
            s_orders_obj[o['client_oid']] = o

        for o in e_orders:
            s_order_client_oid = o['client_oid'].replace('e', 's')
            if s_order_client_oid in s_orders_obj.keys():
                if o['side'] == 'sell':
                    realized_profit += (o['price'] - s_orders_obj[s_order_client_oid]['price'])  * o['filled_size']
                else:
                    realized_profit += (s_orders_obj[s_order_client_oid]['price'] - o['price'])  * s_orders_obj[s_order_client_oid]['filled_size']
                s_orders_obj.pop(s_order_client_oid)
                pair_count += 1
            else:
                unpair_orders.append(o)
    
        if s_orders_obj:
            for k in s_orders_obj:
                unpair_orders.append(s_orders_obj[k])
                if s_orders_obj[k]['side'] == 'buy':
                    unrealized_profit += (c_price - s_orders_obj[k]['price']) * s_orders_obj[k]['filled_size']


        realized_profit = round(realized_profit, 6)
        unrealized_profit = round(unrealized_profit, 6)
        total_profit = realized_profit + unrealized_profit
        total_profit = round(total_profit, 6)
        return {
            'realized_profit': realized_profit,
            'unrealized_profit': unrealized_profit,
            'total_profit': total_profit,
            'pair_count': pair_count,
            'unpair_orders': unpair_orders
        }


    def clac_annual_rate(self, rate, stime, etime):
        hours_delta = max(math.ceil((etime.timestamp() - stime.timestamp())/3600), 1)
        total_hours = 365 * 24
        annual_rate = rate * total_hours / hours_delta
        annual_rate = round(annual_rate, 4)

        return annual_rate
    def clac_volume(self, filled_orders):
        volume = 0
        for o in filled_orders:
            volume += float(o['filled_size']) * float(o['price'])

        volume = round(volume)
        return volume


    def calc_indicator(self, strategy_info, filled_orders, c_price):
        indicator = {}
        indicator['init_amount'] = strategy_info['init_base_amount'] * strategy_info['init_price'] + strategy_info['init_quote_amount']
        indicator['init_amount'] = round(indicator['init_amount'], 6)

        profit_info = self.clac_profit(filled_orders, c_price)
        indicator.update(profit_info)
        # indicator['realized_profit'], indicator['unrealized_profit'], indicator['total_profit'], indicator['pair_count'], indicator['pair_count'] = profit_info['realized_profit'], \
        #     profit_info['unrealized_profit'], profit_info['total_profit'], profit_info['pair_count']


        indicator['rate'] = round(indicator['realized_profit'] / indicator['init_amount'], 4)
        indicator['annual_rate'] = self.clac_annual_rate(indicator['rate'], strategy_info['stime'], datetime.datetime.now())
        indicator['total_rate'] = round(indicator['total_profit'] / indicator['init_amount'], 4)
        indicator['volume'] = self.clac_volume(filled_orders)
        indicator['fee'] = round(indicator['volume'] * 0.001 * 0.15, 6)
        run_time = utils.diff_datetime(strategy_info['stime'], datetime.datetime.now())
        if run_time['days']:
            indicator['run_time'] = '{days}天{hours}小时{minutes}分'.format(days=run_time['days'], hours=run_time['hours'], minutes=run_time['minutes'])
        elif run_time['hours']:
            indicator['run_time'] = '{hours}小时{minutes}分'.format( hours=run_time['hours'], minutes=run_time['minutes'])
        else:
            indicator['run_time'] = '{minutes}分'.format(minutes=run_time['minutes'])
        return indicator

    def run(self):
        # self.wave_index()
        strategy_info = self.read_strategy_info()
        strategy_info = strategy_info[0]
        stime = strategy_info['stime']
        while True:
            open_orders = self.get_open_order(self.pair)
            open_orders.sort(key=lambda k: (k.get('price', 0)))
            ticker = self.order_router.get_ticker(self.pair)
            last = float(ticker['last'])

            etime = datetime.datetime.now()
            filled_orders = self.order_router.get_orders(self.pair, stime=stime, etime=etime, status='filled')
            filled_orders = [o for o in filled_orders if o['client_oid'][:4] == strategy_info['name']]
            strategy_info.update(self.calc_indicator(strategy_info, filled_orders, last))
            self.dis_profit_detail(strategy_info, open_orders, filled_orders, last)
            time.sleep(30)


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
    parser.add_argument(
        '--pair',
        type=str,
        help='pair')

    args = parser.parse_args()
    return args

def main():
    print('#main start#')
    args = parse_args()
    print('args ==>', args)

    analyst = Analyst(args.apikey, args.secretkey, args.passphrase, args.pair)
    analyst.run()

if __name__ == '__main__':
    main()
