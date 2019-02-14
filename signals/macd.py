import talib



class MacdSignal(object):
    def __init__(self):
        self.SHORTPERIOD = 12
        self.LONGPERIOD = 26
        self.SMOOTHPERIOD = 9
        self.OBSERVATION = 100

    def signal(self, price_list):
        sig = 'no'
        macd, signal, hist = talib.MACD(price_list, fastperiod=self.SHORTPERIOD, slowperiod=self.LONGPERIOD, signalperiod=self.SMOOTHPERIOD)
        sample_hist = hist[-5:len(hist)]
        hist_sign = 0

        for h in sample_hist:
            if h > 0:
                hist_sign += 1
            else:
                hist_sign -= 1
        if hist_sign == -5 and sample_hist[-2] < sample_hist[-1] and min(sample_hist) == sample_hist[-2]:
            print('#####macd buy signal')
            sig = 'buy'
        elif hist_sign == 5 and sample_hist[-2] > sample_hist[-1] and max(sample_hist) == sample_hist[-2]:
            print('#####macd sell signal')
            sig = 'sell'

        # # 如果macd从上往下跌破macd_signal, 卖信号
        # if macd[-1] - signal[-1] < 0 and macd[-2] - signal[-2] > 0:
        #     print('#####macd sell signal')
        #     sig = 'sell'

        # # 如果短均线从下往上突破长均线，买信号
        # if macd[-1] - signal[-1] > 0 and macd[-2] - signal[-2] < 0:
        #     print('#####macd buy signal')
        #     sig = 'buy'

        # print('hist=>',hist)
        # print('sample_hist=>',sample_hist)
        # print('hist_sign=>',hist_sign)
        # print('macd=>',macd[-5:len(macd)])
        # print('signal=>',signal[-5:len(signal)])
        return sig, macd[-1], signal[-1]