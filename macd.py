# -*- coding: utf-8 -*-

# from exchange.okex.futures_api import future as okex_future_api


import exchange.okex.futures_api as okex_future
import time
import datetime
import date_utils
import talib
import numpy as np
import pandas as pd
import simulator_service.simulator as simulator


class KlineAnalysis(object):
    def __init__(self, exchange='okex'):
        self.trade_signal = 0
        self.trade_count = 0
        self.last_trade_type = None
        self.test_count = 0
        self._exchange = exchange
        self.okex_future_api = okex_future.FutureAPI('21312408-9af7-4572-a6db-930e40f7ce61', '7A3ACA71DBC68F5A8A37B60C65740122', 'Xjc12345', True)
        self.simulator = simulator.SimulatorService()

    def get_kline(self, instrument_id, granularity, start, end):
        if self._exchange == 'okex':
            r_data = self.okex_future_api.get_kline(instrument_id,granularity, start, end)
            fields = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'currency_volume']
            ret = [dict(zip(fields, r)) for r in r_data]
        return ret

    def get_ticker(self, instrument_id):
        ticker = self.okex_future_api.get_ticker()
        for x in ticker:
            if x['instrument_id'] == instrument_id:
                ticker = x
                break
        print('####ticker=>', ticker)
        return ticker

    def calc_macd(self, instrument_id):
        etime = time.time()
        stime = etime - 60 * 60
        stime_utc = date_utils.local_to_utc(stime)
        etime_utc = date_utils.local_to_utc(etime)

        print('stime_utc=>', stime_utc)
        print('etime_utc=>', etime_utc)
        data = self.get_kline(instrument_id, 60, stime_utc, etime_utc)
        close = np.array([x['close'] for x in data])
        print('close=>', close)
        # close = np.array(close)
        # df = pd.DataFrame()
        # df['EMA12'] = talib.EMA(np.array(close), timeperiod=6)
        # df['EMA26'] = talib.EMA(np.array(close), timeperiod=12)
        # print('df =>', df)

        macd, signal, hist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
        print('macd ==>', macd)
        print('signal ==>', signal)
        print('hist ==>', hist)

    def show_plt(self):
        import matplotlib
        matplotlib.use('TkAgg')
        import matplotlib.pyplot as plt

        # Fixing random state for reproducibility
        np.random.seed(19680801)

        dt = 0.01
        t = np.arange(0, 30, dt)
        nse1 = np.random.randn(len(t))  # white noise 1
        nse2 = np.random.randn(len(t))  # white noise 2

        # Two signals with a coherent part at 10Hz and a random part
        s1 = np.sin(2 * np.pi * 10 * t) + nse1
        s2 = np.sin(2 * np.pi * 10 * t) + nse2

        fig, axs = plt.subplots(2, 1)
        axs[0].plot(t, s1, t, s2)
        axs[0].set_xlim(0, 2)
        axs[0].set_xlabel('time')
        axs[0].set_ylabel('s1 and s2')
        axs[0].grid(True)

        cxy, f = axs[1].cohere(s1, s2, 256, 1. / dt)
        axs[1].set_ylabel('coherence')

        fig.tight_layout()
        plt.show()

    def macd_strategy(self, instrument_id):
        # 使用MACD需要设置长短均线和macd平均线的参数
        SHORTPERIOD = 12
        LONGPERIOD = 26
        SMOOTHPERIOD = 9
        OBSERVATION = 100

        etime = time.time()
        stime = etime - 150 * 60
        stime_utc = date_utils.local_to_utc(stime)
        etime_utc = date_utils.local_to_utc(etime)

        print('stime_utc=>', stime_utc)
        print('etime_utc=>', etime_utc)
        # 用Talib计算MACD取值，得到三个时间序列数组，分别为macd, signal 和 hist
        data = self.get_kline(instrument_id, 60, stime_utc, etime_utc)
        print('data len==>', len(data))
        close = np.array([x['close'] for x in data])
        macd, signal, hist = talib.MACD(close, fastperiod=SHORTPERIOD, slowperiod=LONGPERIOD, signalperiod=SMOOTHPERIOD)

        print('macd[-1] =>', macd[-1])
        print('macd[-2] =>', macd[-2])
        print('signal[-1] =>', signal[-1])
        print('signal[-2] =>', signal[-2])
        # 如果macd从上往下跌破macd_signal, 卖信号
        if macd[-1] - signal[-1] < 0 and macd[-2] - signal[-2] > 0:
            last = self.get_ticker(instrument_id)['last']
            last = float(last)

            self.simulator.submit_order('sell', 'eos', 100, last)
            print('sell signal ----------------')

        # 如果短均线从下往上突破长均线，买信号

        if macd[-1] - signal[-1] > 0 and macd[-2] - signal[-2] < 0:
            last = self.get_ticker(instrument_id)['last']
            last = float(last)
            self.simulator.submit_order('buy', 'eos', 100, last)
            print('buy signal +++++++++++++++++')

        # 止盈

        # 止损
def main():
    print('main start ...')
    kline_analysis = KlineAnalysis('okex')

    # kline_analysis.show_plt()
    while True:
        print('######################################')
        # print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        instrument_id = 'EOS-USD-190329'
        kline_analysis.macd_strategy(instrument_id)
        # kline_analysis.get_ticker(instrument_id)
        time.sleep(30)

if __name__ == '__main__':
    main()
