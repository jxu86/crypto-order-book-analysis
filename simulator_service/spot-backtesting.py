
import csv
from mongo_service.mongodb import MongoService
from signals.macd import MacdSignal
from signals.ema import EMASignal
from signals.kdj import KDJignal
from signals.sar import SARSignal
from signals.stability import SDSignal
from signals.net_grid import NetGridSignal
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
        self.order_count = 0
        self.non_trading = []
        self.non_trading_tmp = []
        self.tttmp = []
        self.context = {}
        
        # self.std_mean

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
        print('portfolio=>', portfolio[-1])
        print('open orders=>', self._broker.order_router)
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

        print('cum return: ', round(((portfolio[-1]['market_value'] - 1000)/1000),6))
        print('cum return: ', (portfolio[-1]['market_value'] - 1000)/1000)
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

    def strategy(self, bar):

        if self.count%1440==0:
            h_data = self.get_data(limit=101)
            if len(h_data) <= 100:
                return
            close_datas = [float(k['close']) for k in h_data]
            self.context['band'], self.context['weight'] = NetGridSignal().signal(close_datas)
        self.count += 1

        if 'band' not in self.context or len(self.context['band']) == 0:
            return

        close = float(bar['close'])
        # print('band=>', self.context['band'])
        # print('close=>', close)
        # grid = pd.cut([close], self.context['band'], labels=[0, 1, 2, 3, 4, 5, 6, 7, 8])[0]
        # print('grid=>', grid)
        
        bands = {
            'datetime': bar['datetime']
        }
        i = 0
        for band in self.context['band']:
            i += 1
            name = 'b' + str(i)
            bands[name] = band

        if 'net_grid_band' in self.context:
            self.context['net_grid_band'].append(bands)
        else:
            self.context['net_grid_band'] = [bands]



    def strategy_std(self, bar):
        # print('bar=>', bar)
        h_data = self.get_data(limit=601)
        if len(h_data) <= 600:
            return
        close_datas = [float(k['close']) for k in h_data]
        close = float(bar['close'])
        time = bar['datetime']
        
        signal, fast_avg, slow_avg= EMASignal().signal(np.array(close_datas))

        opens = np.array([float(d['open']) for d in h_data])
        highs = np.array([float(d['high']) for d in h_data])
        lows = np.array([float(d['low']) for d in h_data])
        upper_band = talib.MAX(highs, 600)[-1]
        lower_band = talib.MIN(lows, 600)[-1]
        spread = upper_band - lower_band

        # if close > upper_band and close > slow_avg and spread > 0.05 and self.order_count == 0:
        #     self.order_count += 1
        #     print('submit order=>order router=>', self._broker.order_router)
        #     order_info = self._broker.sumbit_order(self.pair, close, 50, time, 'buy')
        # elif close < slow_avg:
        #     amount = self._broker.get_base_free()
        #     if amount > 0:
        #         self.order_count = 0
        #         print('amount=>', amount)
        #         order_info = self._broker.sumbit_order(self.pair, close, amount, time, 'sell')
        signal,mean,std,var= SDSignal(20).signal(close_datas)
        cov_limit = 0.0016
        rate = 0.011
        # XLM/ETH
        # cov_limit = 0.0017
        # rate = 0.012
        # ETC/ETH
        # cov_limit = 0.0015
        # rate = 0.010

        # cov_limit = 0.0015
        # rate = 0.009

        # cov = std/mean
        # if cov < cov_limit:
        #     self.non_trading_tmp.append({
        #         'datetime': bar['datetime'],
        #         'value': 1,
        #         'close': close
        #     })
        # else:
        #     if len(self.non_trading_tmp) > 60:
        #         # print('#####=>', len(self.non_trading_tmp))
        #         # self.non_trading += self.non_trading_tmp
        #         max_v = max([n['close'] for n in self.non_trading_tmp])
        #         min_v = min([n['close'] for n in self.non_trading_tmp])
        #         if (max_v-min_v)/min_v > rate:
        #             for t in self.non_trading_tmp:
        #                 t['value'] = 0
        #         else:
        #             if len(self.non_trading_tmp):
        #                 tmp = {'account_name': 'ZxieKalengo4',
        #                     'pair': 'TRX/ETH',
        #                     'stime': min([n['datetime'] for n in self.non_trading_tmp]),
        #                     'etime': max([n['datetime'] for n in self.non_trading_tmp]),
        #                     'resample_type': '1T'}
        #             self.tttmp.append(tmp)
        #             print(tmp)

        #         self.non_trading += self.non_trading_tmp
        #     else:
        #         for t in self.non_trading_tmp:
        #             t['value'] = 0
        #         self.non_trading += self.non_trading_tmp

        #         if len(self.non_trading_tmp) == 0:
        #             self.non_trading.append({
        #                 'datetime': bar['datetime'],
        #                 'value': 0
        #             })

        #     self.non_trading_tmp = []

        
        self.indicate.append({
            'datetime': bar['datetime'],
            # 'std': std,
            # 'mean': mean,
            # 'var': var,
            'upper_band': upper_band,
            'lower_band': lower_band
            # 'slow_avg': slow_avg,
            # 'fast_avg': fast_avg,
            # 'cov': cov
        })

    def plot(self):
        print(self.tttmp)
        scatter_data = []
        closes = [float(d['close']) for d in self.data_array]
        opens = [float(d['open']) for d in self.data_array]
        highs = [float(d['high']) for d in self.data_array]
        lows = [float(d['low']) for d in self.data_array]
        dtime = [d['datetime'] for d in self.data_array]

        bands = {}
        # i = 0
        # print(self.context['band'])
        # for band in self.context['net_grid_band']:
        #     i += 1
        #     name = 'b' + str(i)
        #     bands[name] = pd.Series(
        #                         index=dtime,
        #                         data=
        #     )
        ng_bands = self.context['net_grid_band']
        ndt = [b['datetime'] for b in ng_bands]
        for i in range(1,10):
            name = 'b' + str(i)
            if name not in ng_bands[0]:
                break
            bands[name] = pd.Series(
                                index=ndt,
                                data=[b[name] for b in ng_bands]
            )


        # print('banks=>', bands)

        # upper_band = pd.Series(
        #     index=[p['datetime'] for p in self.indicate],
        #     data=[p['upper_band'] for p in self.indicate])

        # lower_band = pd.Series(
        #     index=[p['datetime'] for p in self.indicate],
        #     data=[p['lower_band'] for p in self.indicate])

        # trade_buy = pd.Series(
        #     index=[p['datetime'] for p in self._broker.order_history if p['status'] == 'filled' and p['side'] == 'buy'],
        #     data=[p['price'] for p in self._broker.order_history if p['status'] == 'filled' and p['side'] == 'buy'])

        # trade_sell = pd.Series(
        #     index=[p['datetime'] for p in self._broker.order_history if p['status'] == 'filled' and p['side'] == 'sell'],
        #     data=[p['price'] for p in self._broker.order_history if p['status'] == 'filled' and p['side'] == 'sell'])

        layout = go.Layout(
            title = self.pair,
            xaxis = dict(domain = [0.05,0.95]),
            yaxis = dict(title = 'amount',titlefont = dict(color = 'blue'),tickfont = dict(color = 'blue')),
            yaxis2 = dict(title = 'alpha',anchor = 'free',overlaying = 'y',side = 'right',position = 1),
            yaxis3 = dict(title = 'total_base',anchor = 'free',overlaying = 'y',position = 1,titlefont = dict(color = 'red'),tickfont = dict(color = 'red')),
            yaxis4 = dict(title = 'total_quote',anchor = 'free',overlaying = 'y',titlefont = dict(color = 'red'),tickfont = dict(color = 'red'))
        )

        for b in bands:
            scatter_data.append(go.Scatter(x=bands[b].index, y=bands[b], name=b))


        # scatter_data.append(go.Scatter(x=fast_avg.index, y=fast_avg, name='fast_avg'))
        # scatter_data.append(go.Scatter(x=slow_avg.index, y=slow_avg, name='slow_avg'))
        # scatter_data.append(go.Scatter(x=mean.index, y=mean, name='mean'))
        # scatter_data.append(go.Scatter(x=upper_band.index, y=upper_band, name='upper_band'))
        # scatter_data.append(go.Scatter(x=lower_band.index, y=lower_band, name='lower_band'))

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
    stime = datetime.datetime(2019,3,30)
    etime = datetime.datetime(2019,4,1)
    # stime = datetime.datetime(2019,3,31,12)
    # etime = datetime.datetime(2019,4,10)
    broker = Broker(pair)
    simulation = SimulationEngine(broker, pair, stime, etime)
    simulation.run()
    print('#main end')

if __name__ == '__main__':
    main()