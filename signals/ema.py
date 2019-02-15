
import talib
import numpy as np

class EMASignal(object):
    def __init__(self):
        self.fast = 7
        self.slow = 30

    def signal(self, price_list):
        sig = 'no'
        fast_avg = talib.EMA(price_list, timeperiod = self.fast)
        slow_avg = talib.EMA(price_list, timeperiod = self.slow)

        # 针对回测前三个数据不要
        if len(slow_avg) < 3:
            return sig, fast_avg[-1], slow_avg[-1]

        # distance_avg = np.array(fast_avg) - np.array(slow_avg)
        

        # 均线下穿，做空
        if slow_avg[-2] < fast_avg[-2] and slow_avg[-1] >= fast_avg[-1]:
            sig = 'sell'

        # if distance_avg[-2] >= distance_avg[-1]:
        #     sig = 'sell'

    
        # 均线上穿，做多
        if fast_avg[-2] < slow_avg[-2] and fast_avg[-1] >= slow_avg[-1]:
            sig = 'buy'


        # 
        if fast_avg[-1] > slow_avg[-1] and fast_avg[-1] < fast_avg[-2] and fast_avg[-2] < fast_avg[-3]:
            sig = 'close_buy'
        
        if fast_avg[-1] < slow_avg[-1] and fast_avg[-1] > fast_avg[-2] and fast_avg[-2] > fast_avg[-3]:
            sig = 'close_sell'

        return sig, fast_avg[-1], slow_avg[-1]