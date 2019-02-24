import talib
import numpy as np
import pandas as pd

class SARSignal(object):
    def __init__(self):
        pass

    def signal(self, data_list):
        sig = 'no'
        high = np.array([np.float(k['high']) for k in data_list])
        low = np.array([np.float(k['low']) for k in data_list])
        close = np.array([np.float(k['close']) for k in data_list])
        # close = float(data_list[-1]['close'])

        sar_index = talib.SAR(high, low, acceleration=0.02, maximum=0.2)
        # print('sar_index==>', sar_index)

        if sar_index[-1] > close[-1]:
            sig = 'buy'
        elif sar_index[-1] < close[-1]:
            sig = 'sell'

        return sig, sar_index[-1]



