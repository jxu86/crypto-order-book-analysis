
import csv
from mongo_service.mongodb import MongoService
from signals.macd import MacdSignal
from signals.ema import EMASignal
from signals.kdj import KDJignal
import config
import uuid 
import datetime
import numpy as np
import utils

import plotly.offline as py
import plotly.graph_objs as go
import pandas as pd

class Broker(object):
    def __init__(self):
        self.order_router = []
        self.order_history = []
        self.balance = {'free':{'eos':10000,'usd':10000}}
        self.portfolio = []

    def sumbit_order(self, instrument_id, price, size, time, side='buy',type='limit'):
        order_info = {
                'order_id': str(uuid.uuid1()),
                'instrument_id': instrument_id,
                'price': price,
                'c_price': 0,
                'size': size,
                'side': side,
                'type': type,
                'match_price': '',
                'fee': 0,
                'profit': 0,
                'status': 'pending', # pending -> holding closing -> closed cancel 
                'leverage': 10,
                'created_at': time,
                'updated_at': time
            }
        self.order_router.append(order_info)
        return order_info
    
    def close_order(self, order_id, c_price, time, size=0, type='limit'):
        for order in self.order_router:
            if order['order_id'] == order_id and order['status'] == 'holding':
                order['c_price'] = c_price
                order['updated_at'] = time
                order['status'] = 'closing'
                return order

            if order['order_id'] == order_id and order['status'] == 'pending':
                order['updated_at'] = time
                order['status'] = 'cancel'
                return order

        return {}
    def calc_profit(self, order):
        side = order['side']
        if side == 'buy':
            profit = order['c_price'] - order['price']
        if side == 'sell':
            profit = order['price'] - order['c_price']
        # print('order=>',order)
        if order['status'] != 'closed':
            returns = 0
        else:
            returns = profit / min(order['price'], order['c_price'])
        print('returns=>',returns)
        return profit * order['leverage'], returns


            
    def fill_order(self, bar):
        new_order_router = []
        close = float(bar['close'])
        for order in self.order_router:
            if order['status'] == 'pending':
                if order['side'] == 'buy' and order['price'] >= close:
                    order['status'] = 'holding'
                    order['updated_at'] = bar['datetime']

                if order['side'] == 'sell' and order['price'] <= close:
                    order['status'] = 'holding'
                    order['updated_at'] = bar['datetime']

            # 平仓
            elif order['status'] == 'closing':
                if order['side'] == 'buy' and order['c_price'] <= close:
                    order['status'] = 'closed'
                    order['updated_at'] = bar['datetime']

                if order['side'] == 'sell' and order['c_price'] >= close:
                    order['status'] = 'closed'
                    order['updated_at'] = bar['datetime']
            
            if order['status'] != 'closed' and order['status'] != 'cancel':
                new_order_router.append(order)
            else:
                order['profit'], order['returns'] = self.calc_profit(order)
                self.order_history.append(order)
        
        self.order_router = new_order_router

    def get_order_num(self):
        return len(self.order_router)

class SimulationEngine(object):
    def __init__(self, broker, data_type):
        self.path = ''
        self._broker = broker
        self._data_type = data_type
        self._mongodb = MongoService(host=config.mongo_host, port=config.mongo_port)
        self.data_pointer = 0
        self.data_array = self.load_data()
        self.data_len = len(self.data_array)
        self.current_time = self.data_array[0]['datetime']
        self.context = {}
        self.future_instrument_id = 'EOS-USD-190329'
        self.order_id = ''

        self.indicate = []

    def _load_csv(self, path):
        csv_data = open(path, 'r')
        dict_reader = csv.DictReader(csv_data)
        csv_dict = []
        for d in dict_reader:
            csv_dict.append(d)
        return csv_dict
    
    def _load_mongo(self):
        data = self._mongodb.find(self._mongodb.kline_1min, query={'timestamp':{'$gte':'2019-02-17T00:00:00.000Z'}}) # 
        for d in data:
            # d['datetime'] = datetime.datetime.strptime(d['timestamp'], '%Y-%m-%dT%H:%M:%S.%fZ')
            d['datetime'] = utils.utcstr_to_datetime(d['timestamp'])
        print('##data len ==>', len(data))
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
        history_data = self.data_array[:self.data_pointer]
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
        self.returns(self._broker.order_history)
        # print('####run=>order_history==>', self._broker.order_history)
        print('####run=>order_history len==>', len(self._broker.order_history))
        print('####run=>order_router==>', self._broker.order_router)
        success_num = 0
        fail_num = 0
        for order in self._broker.order_history:
            if order['status'] == 'closed':
                if order['profit'] >= 0:
                    success_num += 1
                else:
                    fail_num += 1

        close = float(data['close'])
        print('last close==>', close)
        lose = 0
        for order in self._broker.order_router:
            if order['side'] == 'buy':
                lose +=  order['price'] - close
            elif order['side'] == 'sell':
                lose +=  close - order['price']
        print('########lose==>', lose)
        print('####run=>success_num==>', success_num)
        print('####run=>fail_num==>', fail_num)
        self.plot()
        


    def strategy_kdj(self, bar):
        h_data = self.get_data(limit=100)
        if len(h_data) < 100:
            return
        close = float(bar['close'])
        time = bar['datetime']
        signal, slowk, slowd = KDJignal().signal(h_data)

        for order in self._broker.order_router: # 止盈
            o_price = order['price'] 
            side = order['side']
            order_id = order['order_id']
            target_price = utils.calc_profit(
                                        price=o_price,
                                        fee_rate=0.0002,
                                        profit_point=0.0006,
                                        side=side)
            if (side == 'buy' and target_price <= close) or  (side == 'sell' and target_price >= close):
                order_info = self._broker.close_order(order_id, close, time)

        if signal == 'buy' and self._broker.get_order_num() <= 10:
            order_info = self._broker.sumbit_order(self.future_instrument_id, close, 100, time, 'buy')

        if signal == 'sell' and self._broker.get_order_num() <= 10:
            order_info = self._broker.sumbit_order(self.future_instrument_id, close, 100, time, 'sell')

        # self.indicate.append({
        #     'datetime': bar['datetime'],
        #     'fast_avg': slowk,
        #     'slow_avg': slowd
        # })

        

    def strategy(self, bar):
        h_data = self.get_data(limit=101)
        close_datas = [float(k['close']) for k in h_data]
        close = float(bar['close'])
        time = bar['datetime']
        signal, fast_avg, slow_avg= EMASignal(9,30).signal(np.array(close_datas))
        # signal, fast_avg, slow_avg = MacdSignal().signal(np.array(close_datas))

        # for order in self._broker.order_router: # 止盈
        #     o_price = order['price'] 
        #     side = order['side']
        #     order_id = order['order_id']
        #     target_price = utils.calc_profit(
        #                                 price=o_price,
        #                                 fee_rate=0.0002,
        #                                 profit_point=0.0008,
        #                                 side=side)
        #     if (side == 'buy' and target_price <= close) or  (side == 'sell' and target_price >= close):
        #         order_info = self._broker.close_order(order_id, close, time)

        # # signal = MacdSignal().signal(np.array(close_datas))

        if signal == 'buy': # and self._broker.get_order_num() <= 0:
            order_info = self._broker.sumbit_order(self.future_instrument_id, close, 100, time, 'buy')

            for order in self._broker.order_router: # 止盈
                o_price = order['price'] 
                side = order['side']
                order_id = order['order_id']
                if side == 'sell':
                    self._broker.close_order(order_id, close, time)

        elif signal == 'sell': #and self._broker.get_order_num() <= 1:
            order_info = self._broker.sumbit_order(self.future_instrument_id, close, 100, time, 'sell')
            for order in self._broker.order_router: # 止盈
                o_price = order['price'] 
                side = order['side']
                order_id = order['order_id']
                if side == 'buy':
                    self._broker.close_order(order_id, close, time)
        
            
        # elif signal == 'close_buy' and self._broker.get_order_num() >= 1: 
        #     for order in self._broker.order_router: # 止盈
        #         o_price = order['price'] 
        #         side = order['side']
        #         order_id = order['order_id']
        #         if side == 'buy':
        #             self._broker.close_order(order_id, close, time)

        # elif signal == 'close_sell' and self._broker.get_order_num() >= 1: 
        #     for order in self._broker.order_router: # 止盈
        #         o_price = order['price'] 
        #         side = order['side']
        #         order_id = order['order_id']
        #         if side == 'sell':
        #             self._broker.close_order(order_id, close, time)

            # order_info = self._broker.close_order(self.order_id, close, time)
        #     order_info = self._broker.sumbit_order(self.future_instrument_id, close, 100, time, 'sell')
            # self.order_id = order_info['order_id']

        
        # if signal == 'buy':
        #     self._broker.sumbit_order(self.future_instrument_id, close, 100, time, 'buy')
            
        # elif signal == 'sell':
        #     self._broker.sumbit_order(self.future_instrument_id, close, 100, time, 'sell')

        self.indicate.append({
            'datetime': bar['datetime'],
            'fast_avg': fast_avg,
            'slow_avg': slow_avg
        })

    
    def plot(self):

        scatter_data = []
        closes = [d['close'] for d in self.data_array]
        dtime = [d['datetime'] for d in self.data_array]
        
        fast_avg = pd.Series(
            index=[p['datetime'] for p in self.indicate],
            data=[p['fast_avg'] for p in self.indicate])
        slow_avg = pd.Series(
            index=[p['datetime'] for p in self.indicate],
            data=[p['slow_avg'] for p in self.indicate])

        trade_buy = pd.Series(
            index=[p['created_at'] for p in self._broker.order_history if p['status'] == 'closed' and p['side'] == 'buy'],
            data=[p['price'] for p in self._broker.order_history if p['status'] == 'closed' and p['side'] == 'buy'])

        trade_sell = pd.Series(
            index=[p['created_at'] for p in self._broker.order_history if p['status'] == 'closed' and p['side'] == 'sell'],
            data=[p['price'] for p in self._broker.order_history if p['status'] == 'closed' and p['side'] == 'sell'])

        trade_close = pd.Series(
            index=[p['updated_at'] for p in self._broker.order_history if p['status'] == 'closed'],
            data=[p['c_price'] for p in self._broker.order_history if p['status'] == 'closed'])
        
        layout = go.Layout(
            xaxis = dict(domain = [0.1,0.9]),
            yaxis = dict(title = 'amount',titlefont = dict(color = 'blue'),tickfont = dict(color = 'blue')),
            yaxis2 = dict(title = 'alpha',anchor = 'free',overlaying = 'y',side = 'right',position = 1),
            yaxis3 = dict(title = 'total_base',anchor = 'free',overlaying = 'y',position = 1,titlefont = dict(color = 'red'),tickfont = dict(color = 'red')),
            yaxis4 = dict(title = 'total_quote',anchor = 'free',overlaying = 'y',titlefont = dict(color = 'red'),tickfont = dict(color = 'red'))
        )

        scatter_data.append(go.Scatter(x=dtime, y=closes, name='close'))
        scatter_data.append(go.Scatter(x=fast_avg.index, y=fast_avg, name='fast_avg', yaxis='y2'))
        scatter_data.append(go.Scatter(x=slow_avg.index, y=slow_avg, name='slow_avg', yaxis='y2'))
        scatter_data.append(go.Scatter(x=trade_buy.index, y=trade_buy, name='trade_buy', mode = 'markers', marker=dict(color='red')))
        scatter_data.append(go.Scatter(x=trade_sell.index, y=trade_sell, name='trade_sell', mode = 'markers', marker=dict(color='blue')))
        scatter_data.append(go.Scatter(x=trade_close.index, y=trade_close, name='trade_close', mode = 'markers', marker=dict(color='green')))

        fig = go.Figure(data=scatter_data, layout=layout)
        py.plot(fig, auto_open=True, filename='tmp-plot.html')

def main():
    print('#main start#')
    broker = Broker()
    simulation = SimulationEngine(broker, data_type='mongo')
    simulation.run()
    print('#main end')

if __name__ == '__main__':
    main()