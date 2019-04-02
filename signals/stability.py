
# import talib
import numpy as np

class SDSignal(object):
    def __init__(self, n=60):
        self.n = n

    def signal(self, price_list):
        sig = 'no'
        price_list = price_list[-self.n:]

        #求均值
        mean = np.mean(price_list)
        #求方差
        var = np.var(price_list)
        #求标准差
        std = np.std(price_list,ddof=1)

        return sig, mean, std, var