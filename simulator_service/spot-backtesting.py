
import csv
from mongo_service.mongodb import MongoService
from signals.macd import MacdSignal
from signals.ema import EMASignal
from signals.kdj import KDJignal
from signals.sar import SARSignal
import config
import uuid 
import datetime
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
        self.init_amount = 1000
        self.base, self.quote = self.pair.split('/')
        self.context = {
            'base': self.base,
            'quote': self.quote,
            'init_amount': {
                self.base: 0,
                self.quote: self.init_amount
            },#初始资金
            'balance': {
                self.base: {'free': 0, 'use': 0, 'total': 0},
                self.quote: {'free': self.init_amount, 'use': 0, 'total': self.init_amount} 
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
            self.set_base_use(amount)

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
        for order in self.order_router:
            if order['status'] == 'open':
                if (order['side'] == 'buy' and order['price'] >= low) or (order['side'] == 'sell' and order['price'] <= high):
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
        self._mongodb = MongoService(host='10.10.20.90', port=57017)
        self.data_pointer = 0
        self.data_array = self.load_data()
        self.data_len = len(self.data_array)
        self.current_time = self.data_array[0]['datetime']
        self.indicate = []
        self.count = 0
        

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

        print('order_history==>', self._broker.order_history)
        print('portfolio=>', portfolio)

        self.plot()
        

    def strategy(self, bar):
        
        h_data = self.get_data(limit=101)
        if len(h_data) <= 0:
            return
        close_datas = [float(k['close']) for k in h_data]
        close = float(bar['close'])
        time = bar['datetime']
        signal, fast_avg, slow_avg= EMASignal().signal(np.array(close_datas))
        # # signal, fast_avg, slow_avg = MacdSignal().signal(np.array(close_datas))

        if signal == 'buy':
            order_info = self._broker.sumbit_order(self.pair, close, 1, time, 'buy')
        elif signal == 'sell':
            amount = self._broker.get_base_free()
            if amount >= 0:
                order_info = self._broker.sumbit_order(self.pair, close, amount, time, 'sell')

        self.indicate.append({
            'datetime': bar['datetime'],
            'fast_avg': fast_avg,
            'slow_avg': slow_avg
        })

    
    def plot(self):
        scatter_data = []
        closes = [float(d['close']) for d in self.data_array]
        opens = [float(d['open']) for d in self.data_array]
        highs = [float(d['high']) for d in self.data_array]
        lows = [float(d['low']) for d in self.data_array]
        dtime = [d['datetime'] for d in self.data_array]

        fast_avg = pd.Series(
            index=[p['datetime'] for p in self.indicate],
            data=[p['fast_avg'] for p in self.indicate])

        slow_avg = pd.Series(
            index=[p['datetime'] for p in self.indicate],
            data=[p['slow_avg'] for p in self.indicate])



        trade_buy = pd.Series(
            index=[p['datetime'] for p in self._broker.order_history if p['status'] == 'filled' and p['side'] == 'buy'],
            data=[p['price'] for p in self._broker.order_history if p['status'] == 'filled' and p['side'] == 'buy'])

        trade_sell = pd.Series(
            index=[p['datetime'] for p in self._broker.order_history if p['status'] == 'filled' and p['side'] == 'sell'],
            data=[p['price'] for p in self._broker.order_history if p['status'] == 'filled' and p['side'] == 'sell'])

        layout = go.Layout(
            xaxis = dict(domain = [0.05,0.95]),
            yaxis = dict(title = 'amount',titlefont = dict(color = 'blue'),tickfont = dict(color = 'blue')),
            yaxis2 = dict(title = 'alpha',anchor = 'free',overlaying = 'y',side = 'right',position = 1),
            yaxis3 = dict(title = 'total_base',anchor = 'free',overlaying = 'y',position = 1,titlefont = dict(color = 'red'),tickfont = dict(color = 'red')),
            yaxis4 = dict(title = 'total_quote',anchor = 'free',overlaying = 'y',titlefont = dict(color = 'red'),tickfont = dict(color = 'red'))
        )

        scatter_data.append(go.Scatter(x=fast_avg.index, y=fast_avg, name='fast_avg'))
        scatter_data.append(go.Scatter(x=slow_avg.index, y=slow_avg, name='slow_avg'))

        scatter_data.append(go.Scatter(x=trade_buy.index, y=trade_buy, name='trade_buy', mode = 'markers', marker=dict(color='red')))
        scatter_data.append(go.Scatter(x=trade_sell.index, y=trade_sell, name='trade_sell', mode = 'markers', marker=dict(color='blue')))
        # scatter_data.append(go.Scatter(x=trade_close.index, y=trade_close, name='trade_close', mode = 'markers', marker=dict(color='green')))
        portfolio = self._broker.get_portfolio
        portfolio_dt = [p['datetime'] for p in portfolio]
        market_value = [p['market_value'] for p in portfolio]
        scatter_data.append(go.Scatter(x=portfolio_dt, y=market_value, name='market-value', mode = 'lines', yaxis='y2', marker=dict(color='green')))

        traces = go.Candlestick(x=dtime,
                       open=opens,
                       high=highs,
                       low=lows,
                       close=closes)
        scatter_data.append(traces)
        fig = go.Figure(scatter_data, layout=layout)
        py.plot(fig, auto_open=True, filename='tmp-plot.html')

def main():
    print('#main start#')
    pair = 'EOS/USDT'
    stime = datetime.datetime(2019,3,21)
    etime = datetime.datetime(2019,3,22)
    broker = Broker(pair)
    simulation = SimulationEngine(broker, pair, stime, etime)
    simulation.run()
    print('#main end')

if __name__ == '__main__':
    main()