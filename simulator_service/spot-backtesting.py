
import csv
from mongo_service.mongodb import MongoService
from signals.macd import MacdSignal
from signals.ema import EMASignal
from signals.kdj import KDJignal
from signals.sar import SARSignal
from signals.stability import SDSignal
from signals.net_grid import NetGridSignal
from signals import net_grid
import config
import uuid 
import datetime
import time
import numpy as np
import utils

import plotly.offline as py
import plotly.graph_objs as go
import pandas as pd
import talib

class Broker(object):
    def __init__(self, pair):
        self.order_router = []
        self.order_history = []
        self.pair = pair
        self.init_quote_amount = 1000
        self.init_base_amount = 1000
        self.base, self.quote = self.pair.split('/')
        self.context = {
            'base': self.base,
            'quote': self.quote,
            'init_amount': {
                self.base: self.init_base_amount,
                self.quote: self.init_quote_amount
            },#初始资金
            'balance': {
                self.base: {'free': self.init_base_amount, 'use': 0, 'total': self.init_base_amount},
                self.quote: {'free': self.init_quote_amount, 'use': 0, 'total': self.init_quote_amount} 
            },
            'portfolio': []
        }
        print('context=>', self.context)

    def get_quote_free(self):
        return self.context['balance'][self.quote]['free']

    def get_base_free(self):
        return self.context['balance'][self.base]['free']

    def get_base_total(self):
        return self.context['balance'][self.base]['total']

    def get_quote_total(self):
        return self.context['balance'][self.quote]['total']

    def get_position(self):
        return self.context['balance'][self.base]['total']

    def set_quote_use(self, amount):
        self.context['balance'][self.quote]['free'] -= amount
        self.context['balance'][self.quote]['use'] += amount

    def set_base_use(self, amount):
        self.context['balance'][self.base]['free'] -= amount
        self.context['balance'][self.base]['use'] += amount

    def update_balance(self, side, size, amount):
        if side == 'buy':
            self.context['balance'][self.quote]['use'] -= amount
            self.context['balance'][self.quote]['total'] -= amount
            self.context['balance'][self.base]['free'] += size
            self.context['balance'][self.base]['total'] += size
        elif side == 'sell':
            self.context['balance'][self.base]['use'] -= size
            self.context['balance'][self.base]['total'] -= size
            self.context['balance'][self.quote]['free'] += amount
            self.context['balance'][self.quote]['total'] += amount
        # print('update_balance=>context=>', self.context)

    def update_portfolio(self, bar):
        base = self.get_base_total()
        quote = self.get_quote_total()
        close = float(bar['close'])
        market_value = quote + base * close
        self.context['portfolio'].append({
            'quote': quote,
            'base': base,
            'price': close,
            'market_value': market_value,
            'datetime': bar['datetime']
        })
    @property
    def get_portfolio(self):
        return self.context['portfolio']

    def sumbit_order(self, instrument_id, price, size, time, side='buy',type='limit'):
        amount = price*size
        if side == 'buy' and self.get_quote_free() < amount: # 检查quote是否足够
            return 'quote 余额不足'
        elif side == 'self' and self.get_base_free() < size: # 检查free是否足够
            return 'quote 余额不足'

        if side == 'buy':
            self.set_quote_use(amount)
        elif side == 'sell':
            self.set_base_use(size)

        order_info = {
                'order_id': str(uuid.uuid1()),
                'instrument_id': instrument_id,
                'price': price,
                'size': size,
                'side': side,
                'type': type,
                'filled_notional': 0,
                'status': 'open', # open part_filled canceling cancelled filled ordering failure
                'datetime': time,
                'created_at': time,
                'updated_at': time
            }
        self.order_router.append(order_info)
        return order_info
    
    def fill_order(self, bar):
        new_order_router = []
        high = float(bar['high'])
        low = float(bar['low'])
        close = float(bar['close'])
        for order in self.order_router:
            if order['status'] == 'open':
                # if (order['side'] == 'buy' and order['price'] >= low) or (order['side'] == 'sell' and order['price'] <= high):
                if (order['side'] == 'buy' and order['price'] >= close) or (order['side'] == 'sell' and order['price'] <= close):
                    order['status'] = 'filled'
                    order['filled_notional'] = order['price'] * order['size']
                    order['updated_at'] = bar['datetime']
                    self.update_balance(order['side'], order['size'], order['filled_notional'])
                    # self.update_portfolio(bar)
            elif order['status'] == 'canceling': #TODO 处理cancel订单
                pass

            if order['status'] == 'open':
                new_order_router.append(order)
            else:
                self.order_history.append(order)
        
        self.order_router = new_order_router

    def cancle_order(self, order_id):
        pass


    def get_order_num(self):
        return len(self.order_router)

class SimulationEngine(object):
    def __init__(self, broker, pair, stime, etime, data_type='mongo'):
        self.stime = stime
        self.etime = etime
        self.pair = pair
        self.base, self.quote = self.pair.split('/')
        print('pair=>', self.pair)
        print('stime=>', self.stime)
        print('etime=>', self.etime)
        self.path = ''
        self._broker = broker
        self._data_type = data_type
        # self._mongodb = MongoService(host='10.10.20.90', port=57017)
        self._mongodb = MongoService(host='127.0.0.1', port=27017)
        self.data_pointer = 0
        self.data_array = self.load_data()
        self.data_len = len(self.data_array)
        self.current_time = self.data_array[0]['datetime']
        self.indicate = []
        self.count = 0
        self.order_count = 0
        self.non_trading = []
        self.non_trading_tmp = []
        self.tttmp = []
        self.context = {}

        # net grid
        self.start_flag = False
        self.precision = 3
        self.grid_num = 400
        self.net_grid = net_grid.NetGridSignal(7, 3, self.grid_num, self.precision)
        # 格子价格list
        self.grid_list = self.net_grid.calc_price_interval()
        # 格子序号
        self.grid_index = [i for i in range(len(self.grid_list)-1)]
        # 当前价格所在的格子
        self.current_index = 0
        # 当前订单list
        self.order_list = []
        self.order_size = 0.1
        self.base_init_amount = 0
        self.quote_init_amount = 0
        self.pending_orders = []
        self.get_pending_orders()


    def _load_csv(self, path):
        csv_data = open(path, 'r')
        dict_reader = csv.DictReader(csv_data)
        csv_dict = []
        for d in dict_reader:
            csv_dict.append(d)
        return csv_dict
    
    def _load_mongo(self):
        print('load mongo data')
        query = {
            'pair': self.pair,
            'period' : '1min',
            'datetime': {'$gte': self.stime, '$lt': self.etime}
        }
        print('_load_mongo=>query==>', query)
        data = self._mongodb.find(self._mongodb.kline_history_1min, query=query)
        print('data len==>', len(data))
        return data
        
    def load_data(self):
        if self._data_type == 'csv':
            return self._load_csv()
        elif self._data_type == 'mongo':
            return self._load_mongo()
        else:
            return []

    # 默认当前时间点往前拿limit个数据
    def get_data(self, stime='', etime='', limit=100):
        if self.data_pointer == 1:
            return []
        history_data = self.data_array[:(self.data_pointer-1)]
        data_len = len(history_data)
        s_pointer = max(0, data_len - limit)
        return history_data[s_pointer: data_len]

    def get_one_data(self):
        ret = self.data_array[self.data_pointer]
        self.current_time = ret['datetime'] # update time
        self.data_pointer += 1
        return ret

    def handle_data(self, bar):
        self._broker.fill_order(bar)
        self._broker.update_portfolio(bar)

    def before(self):
        pass

    def after(self):
        pass

    def on_bar(self, bar):
        self.strategy(bar)
        
    def returns(self, order_list):
        total_profit = 0
        returns = 0
        for order in order_list:
            if order['status'] == 'closed':
                total_profit += order['profit']
                returns += order['returns']
        print('#########total_profit -->', total_profit)
        print('#########returns -->', returns)
        return total_profit

    def run(self):
        while True:
            data = self.get_one_data()
            self.before()
            self.handle_data(data)
            self.on_bar(data)
            self.after()
            if self.data_pointer >= self.data_len:
                break
        
        portfolio = self._broker.get_portfolio

        # print('order_history==>', self._broker.order_history)
        print('portfolio 0=>', portfolio[0])
        print('portfolio 1=>', portfolio[-1])
        print('open orders len=>', len(self._broker.order_router))
        print('base free: ', self._broker.get_base_free())
        print('base total: ', self._broker.get_base_total())

        print('base use: ', self._broker.context['balance'][self.base]['use'])
        print('quote free: ', self._broker.get_quote_free())
        print('quote total: ', self._broker.get_quote_total())
        buy_orders = [o for o in self._broker.order_history if o['side'] == 'buy']
        sell_orders = [o for o in self._broker.order_history if o['side'] == 'sell']
        buy_open_orders = [o for o in self._broker.order_router if o['side'] == 'buy']
        sell_open_orders = [o for o in self._broker.order_router if o['side'] == 'sell']

        buy_volume = sum([o['size'] for o in buy_orders])
        sell_volume = sum([o['size'] for o in sell_orders])

        print('buy order num: ', len(buy_orders))
        print('sell order num: ', len(sell_orders))
        print('buy volume: ', buy_volume)
        print('sell volume: ', sell_volume)
        print('buy open order num: ', len(buy_open_orders))
        print('sell open order num: ', len(sell_open_orders))

        print('cum return: ', round(((portfolio[-1]['market_value'] - portfolio[0]['market_value'])/portfolio[0]['market_value']),6))
        # print('cum return: ', (portfolio[-1]['market_value'] - 1000)/1000)
        self.plot()
        

    def strategy_ema(self, bar):
        
        h_data = self.get_data(limit=101)
        if len(h_data) <= 0:
            return
        close_datas = [float(k['close']) for k in h_data]
        close = float(bar['close'])
        time = bar['datetime']
        signal, fast_avg, slow_avg= EMASignal().signal(np.array(close_datas))
        # # signal, fast_avg, slow_avg = MacdSignal().signal(np.array(close_datas))

        if signal == 'buy':
            order_info = self._broker.sumbit_order(self.pair, close, 10, time, 'buy')
        elif signal == 'sell':
            amount = self._broker.get_base_free()
            if amount >= 0:
                order_info = self._broker.sumbit_order(self.pair, close, amount, time, 'sell')

        self.indicate.append({
            'datetime': bar['datetime'],
            'fast_avg': fast_avg,
            'slow_avg': slow_avg
        })

       # 撒网
    

    def get_pending_orders(self):
        self.pending_orders = self._broker.order_router

    # 计算一开始撒网的价格
    def get_net_order(self, price):
        mid_price = price
        low_price = min(self.grid_list)
        high_price = max(self.grid_list)
        base_init_amount = 0
        quote_init_amount = 0
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
                quote_init_amount += self.order_size * self.grid_list[index]
            elif index > self.current_index:
                order_list.append({
                    'side': 'sell',
                    'price': self.grid_list[index]
                })
                base_init_amount += self.order_size
            else:
                order_list.append({
                    'side': 'hold',
                    'price': self.grid_list[index]
                })

        if self.start_flag == False:
            self.base_init_amount = round(base_init_amount, 10)
            self.quote_init_amount = round(quote_init_amount, 10)
            print('self.base_init_amount=>', self.base_init_amount)
            print('self.quote_init_amount=>', self.quote_init_amount)
        # self.strategy_info['init_base_amount'] = self.base_init_amount
        # self.strategy_info['init_quote_amount'] = self.quote_init_amount
        # self.strategy_info['init_price'] = mid_price
        # print('strategy_info=>', self.strategy_info)
        # self.update_strategy_info(self.strategy_info)
        # print('self.base_init_amount=>', self.base_init_amount)
        # print('self.quote_init_amount=>', self.quote_init_amount)
        
        return order_list


    # 检查订单是否已经存在
    def find_open_order(self, side, price):
        self.get_pending_orders()
        # print('self.pending_orders len=>', len(self.pending_orders))
        order = [o for o in self.pending_orders if o['side']==side and o['price']==price]
        if len(order) == 0:
            return None
        else:
            return order[0]

    def throw_net(self, price, time):
        orders = self.get_net_order(price)
        self.order_list = []
        for o in orders:
            if o['side'] == 'hold':
                self.order_list.append(o)
                continue

            open_order = self.find_open_order(o['side'], o['price'])
            # c_time = str(int(time.time()*1000))
            # client_oid = self.name + c_time + 's'
            # print(client_oid)

            #检查订单是否存在
            if open_order != None:
                self.order_list.append(open_order)
                continue

            # order_info = self.order_router.submit_spot_order(client_oid, 'limit', o['side'], self.spot_pair, o['price'], self.order_size, '')
            order_info = self._broker.sumbit_order(self.pair, o['price'], self.order_size, time, o['side'])
            self.order_list.append(order_info)

        # print('self.order_list=>', self.order_list)
        # print('self.order_list len=>', len(self.order_list))

    def strategy(self, bar):

        close = float(bar['close'])
        bar_time = bar['datetime']
        print('datetime=>', bar_time, '  close=>', close)
        self.throw_net(close, bar_time)
        if self.start_flag == False:
            self.start_flag = True
       


    def plot(self):
        print(self.tttmp)
        scatter_data = []
        closes = [float(d['close']) for d in self.data_array]
        opens = [float(d['open']) for d in self.data_array]
        highs = [float(d['high']) for d in self.data_array]
        lows = [float(d['low']) for d in self.data_array]
        dtime = [d['datetime'] for d in self.data_array]
  



        layout = go.Layout(
            title = self.pair,
            xaxis = dict(domain = [0.05,0.95]),
            yaxis = dict(title = 'amount',titlefont = dict(color = 'blue'),tickfont = dict(color = 'blue')),
            yaxis2 = dict(title = 'alpha',anchor = 'free',overlaying = 'y',side = 'right',position = 1),
            yaxis3 = dict(title = 'total_base',anchor = 'free',overlaying = 'y',position = 1,titlefont = dict(color = 'red'),tickfont = dict(color = 'red')),
            yaxis4 = dict(title = 'total_quote',anchor = 'free',overlaying = 'y',titlefont = dict(color = 'red'),tickfont = dict(color = 'red'))
        )

        # for b in bands:
            # scatter_data.append(go.Scatter(x=bands[b].index, y=bands[b], name=b))
        
        # scatter_data.append(go.Scatter(x=fast_avg.index, y=fast_avg, name='fast_avg'))
        # scatter_data.append(go.Scatter(x=slow_avg.index, y=slow_avg, name='slow_avg'))
        # scatter_data.append(go.Scatter(x=mean.index, y=mean, name='mean'))
        # scatter_data.append(go.Scatter(x=upper_band.index, y=upper_band, name='upper_band'))
        # scatter_data.append(go.Scatter(x=lower_band.index, y=lower_band, name='lower_band'))

        portfolio = self._broker.get_portfolio
        portfolio_dt = [p['datetime'] for p in portfolio]
        market_value = [p['market_value'] for p in portfolio]

        market_value_series = pd.Series(index=portfolio_dt, data=market_value)
        market_value_series = market_value_series.resample('D').last().fillna(method='ffill')

        closes_series = pd.Series(index=dtime, data=closes)
        closes_series = closes_series.resample('D').last().fillna(method='ffill')

        scatter_data.append(go.Scatter(x=market_value_series.index, y=market_value_series, name='market-value', mode = 'lines', yaxis='y2', marker=dict(color='green')))

        scatter_data.append(go.Scatter(x=closes_series.index, y=closes_series, name='close', mode = 'lines', marker=dict(color='red')))

        # traces = go.Candlestick(x=dtime,
        #                         open=opens,
        #                         high=highs,
        #                         low=lows,
        #                         close=closes,
        #                         name='kline')
        # scatter_data.append(traces)
        fig = go.Figure(scatter_data, layout=layout)
        file_name = 'data/kline-tmp-plot.html'
        py.plot(fig, auto_open=True, filename=file_name)

    
    def plot_bk(self):
        print(self.tttmp)
        scatter_data = []
        closes = [float(d['close']) for d in self.data_array]
        opens = [float(d['open']) for d in self.data_array]
        highs = [float(d['high']) for d in self.data_array]
        lows = [float(d['low']) for d in self.data_array]
        dtime = [d['datetime'] for d in self.data_array]

        # fast_avg = pd.Series(
        #     index=[p['datetime'] for p in self.indicate],
        #     data=[p['fast_avg'] for p in self.indicate])

        # slow_avg = pd.Series(
        #     index=[p['datetime'] for p in self.indicate],
        #     data=[p['slow_avg'] for p in self.indicate])


        # dt = [p['datetime'] for p in self.indicate]
        # mean = pd.Series(
        #     index=[p['datetime'] for p in self.indicate],
        #     data=[p['mean'] for p in self.indicate])

        # std = pd.Series(
        #     index=[p['datetime'] for p in self.indicate],
        #     data=[p['std'] for p in self.indicate])

        # cov = pd.Series(
        #     index=[p['datetime'] for p in self.indicate],
        #     data=[p['cov'] for p in self.indicate])

        # non_trend = pd.Series(
        #     index=[p['datetime'] for p in self.non_trading],
        #     data=[p['value'] for p in self.non_trading])


        # std_limit = pd.Series(
        #     index= dt,
        #     data=[np.mean([p['std'] for p in self.indicate])]*len(dt))

        # std_limit = pd.Series(
        #     index= dt,
        #     data=[np.mean([p['std'] for p in self.indicate])]*len(dt))

        # var = pd.Series(
        #     index=[p['datetime'] for p in self.indicate],
        #     data=[p['var'] for p in self.indicate])

        upper_band = pd.Series(
            index=[p['datetime'] for p in self.indicate],
            data=[p['upper_band'] for p in self.indicate])

        lower_band = pd.Series(
            index=[p['datetime'] for p in self.indicate],
            data=[p['lower_band'] for p in self.indicate])

        trade_buy = pd.Series(
            index=[p['datetime'] for p in self._broker.order_history if p['status'] == 'filled' and p['side'] == 'buy'],
            data=[p['price'] for p in self._broker.order_history if p['status'] == 'filled' and p['side'] == 'buy'])

        trade_sell = pd.Series(
            index=[p['datetime'] for p in self._broker.order_history if p['status'] == 'filled' and p['side'] == 'sell'],
            data=[p['price'] for p in self._broker.order_history if p['status'] == 'filled' and p['side'] == 'sell'])

        layout = go.Layout(
            title = self.pair,
            xaxis = dict(domain = [0.05,0.95]),
            yaxis = dict(title = 'amount',titlefont = dict(color = 'blue'),tickfont = dict(color = 'blue')),
            yaxis2 = dict(title = 'alpha',anchor = 'free',overlaying = 'y',side = 'right',position = 1),
            yaxis3 = dict(title = 'total_base',anchor = 'free',overlaying = 'y',position = 1,titlefont = dict(color = 'red'),tickfont = dict(color = 'red')),
            yaxis4 = dict(title = 'total_quote',anchor = 'free',overlaying = 'y',titlefont = dict(color = 'red'),tickfont = dict(color = 'red'))
        )


        # scatter_data.append(go.Scatter(x=fast_avg.index, y=fast_avg, name='fast_avg'))
        # scatter_data.append(go.Scatter(x=slow_avg.index, y=slow_avg, name='slow_avg'))
        # scatter_data.append(go.Scatter(x=mean.index, y=mean, name='mean'))
        scatter_data.append(go.Scatter(x=upper_band.index, y=upper_band, name='upper_band'))
        scatter_data.append(go.Scatter(x=lower_band.index, y=lower_band, name='lower_band'))
        # scatter_data.append(go.Scatter(x=std.index, y=std, name='std', yaxis='y3'))
        # scatter_data.append(go.Scatter(x=cov.index, y=cov, name='cov', yaxis='y3'))
        # scatter_data.append(go.Scatter(x=non_trend.index, y=non_trend, name='non_trend',fill='tozeroy',mode= 'none', yaxis='y4'))
        # scatter_data.append(go.Scatter(x=std_limit.index, y=std_limit, name='std-limit', yaxis='y3'))
        # scatter_data.append(go.Scatter(x=var.index, y=var, name='var', yaxis='y4'))
        # scatter_data.append(go.Scatter(x=trade_buy.index, y=trade_buy, name='trade_buy', mode = 'markers', marker=dict(color='red')))
        # scatter_data.append(go.Scatter(x=trade_sell.index, y=trade_sell, name='trade_sell', mode = 'markers', marker=dict(color='blue')))
        # scatter_data.append(go.Scatter(x=trade_close.index, y=trade_close, name='trade_close', mode = 'markers', marker=dict(color='green')))
        portfolio = self._broker.get_portfolio
        portfolio_dt = [p['datetime'] for p in portfolio]
        market_value = [p['market_value'] for p in portfolio]
        # scatter_data.append(go.Scatter(x=portfolio_dt, y=market_value, name='market-value', mode = 'lines', yaxis='y2', marker=dict(color='green')))

        traces = go.Candlestick(x=dtime,
                                open=opens,
                                high=highs,
                                low=lows,
                                close=closes,
                                name='kline')
        scatter_data.append(traces)
        fig = go.Figure(scatter_data, layout=layout)
        # file_name = 'data/kline-{pair}-{t}'.format(pair=self.pair.replace('/', '-'), t=str(int(time.time())))
        file_name = 'data/kline-tmp-plot.html'
        py.plot(fig, auto_open=True, filename=file_name)

def main():
    print('#main start#')
    #  pair = 'TRX/ETH'
    pair = 'EOS/USDT'
    stime = datetime.datetime(2019,5,1)
    etime = datetime.datetime(2019,5,2)
    # stime = datetime.datetime(2019,3,31,12)
    # etime = datetime.datetime(2019,4,10)
    broker = Broker(pair)
    simulation = SimulationEngine(broker, pair, stime, etime)
    simulation.run()
    print('#main end')

if __name__ == '__main__':
    main()