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

        # 拿到slowk 和slowd最近的一个值
        slowk = slowk[-1]
        slowd = slowd[-1]
        
        # 如果 slowk <10 或者 slowd 小于 20, 那么股票处于超卖阶段，我们选择买入
        # in the portfolio.
        if (slowk < 10 or slowd < 20):
            sig = 'buy'
        
        # 如果 slowk 或者 slowd 小于 10, 那么股票处于超买阶段，我们选择卖出
        elif (slowk > 90 or slowd > 80):
            sig = 'sell'

        return sig, slowk, slowd

    

    # def signal_2(self, df):
    #     n = 30
    #     # low_list= pd.rolling(df['low'], n)
    #     low_list= df[['low']].rolling(n)
    #     low_list.fillna(value=pd.expanding(df['low']), inplace=True)
    #     high_list = df['high'].rolling(n)
    #     high_list.fillna(value=pd.expanding(df['high']), inplace=True)
    #     rsv = (df['close'] - low_list) / (high_list - low_list) * 100
    #     df['kdj_k'] = pd.ewma(rsv,com=2)
    #     df['kdj_d'] = pd.ewma(df['kdj_k'],com=2)
    #     df['kdj_j'] = 3.0 * df['kdj_k'] - 2.0 * df['kdj_d']
    #     #print('n df',len(df))
    #     print('kdj df===>',df)
    #     return df
# ref: https://bbs.pinggu.org/forum.php?mod=viewthread&ordertype=1&tid=5021042


