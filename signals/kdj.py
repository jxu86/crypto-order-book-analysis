import talib
import numpy as np
import pandas as pd

class KDJignal(object):
    def __init__(self):
        pass

    def signal(self, data_list):
        sig = 'no'
        high = np.array([np.float(k['high']) for k in data_list])
        low = np.array([np.float(k['low']) for k in data_list])
        close = np.array([np.float(k['close']) for k in data_list])
        slowk, slowd = talib.STOCH(high,low,close,
                            fastk_period=9,
                            slowk_period=3,
                            slowk_matype=0,
                            slowd_period=3,
                            slowd_matype=0)

   
        slowk = slowk[-15:]
        slowk_max = max(slowk)
        slowk_min = min(slowk)
        # print('slowk len=>',slowk)
        # print('slowk_max=>',slowk_max)
        # print('slowk_min=>',slowk_min)
        # 拿到slowk 和slowd最近的一个值
        slowk = slowk[-1]
        slowd = slowd[-1]
        # TODO 判断是不是震荡

        # 如果 slowk <10 或者 slowd 小于 20, 那么股票处于超卖阶段，我们选择买入
        # in the portfolio.
        if (slowk < 10 or slowd < 20) and slowk_max > 80:
            sig = 'buy'
        
        # 如果 slowk 或者 slowd 小于 10, 那么股票处于超买阶段，我们选择卖出
        elif (slowk > 90 or slowd > 80) and slowk_min < 20:
            sig = 'sell'

        return sig, slowk, slowd




