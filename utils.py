import dateutil
import dateutil.parser
import datetime
import time
import pytz
import numpy as np
import talib

TIME_ZONE = 'Asia/Shanghai'


def timestamp_to_datetime(timestamp: int):
    return datetime.datetime.fromtimestamp(float(timestamp) / 1000)


def utcstr_to_datetime(string):
    return dateutil.parser.parse(string).replace(
        tzinfo=dateutil.tz.tzutc()).astimezone(
            dateutil.tz.gettz(TIME_ZONE)).replace(tzinfo=None)

def local_to_utc(local_ts, utc_format='%Y-%m-%dT%H:%M:%SZ'):
    local_tz = pytz.timezone('Asia/Shanghai')
    local_format = "%Y-%m-%d %H:%M:%S"
    time_str = time.strftime(local_format, time.localtime(local_ts))
    dt = datetime.datetime.strptime(time_str, local_format)
    local_dt = local_tz.localize(dt, is_dst=None)
    utc_dt = local_dt.astimezone(pytz.utc)
    return utc_dt.strftime(utc_format)


def profit(frist_price, last_price, fee_rate=0.001, side='buy'):
    if side == 'buy':
        return (last_price - frist_price)/frist_price - 2 * fee_rate
    else:
        return (frist_price - last_price)/last_price - 2 * fee_rate

def calc_profit(price, fee_rate=0.001, profit_point=0.001, side='buy'):
    if side == 'buy':
        return price * (1 + 2 * fee_rate + profit_point)
    else:
        return price * (1 - 2 * fee_rate - profit_point)

# def check_profit(a1,a2,b1,b2):
#     return (a1-a2)/a2+(b2-b1)/b1 -0.006


def macd_signal(price_list):
        sig = 'no'
        SHORTPERIOD = 12
        LONGPERIOD = 26
        SMOOTHPERIOD = 9
        OBSERVATION = 100
        macd, signal, hist = talib.MACD(price_list, fastperiod=SHORTPERIOD, slowperiod=LONGPERIOD, signalperiod=SMOOTHPERIOD)
        sample_hist = hist[-5:len(hist)]
        hist_sign = 0

        for h in sample_hist:
            if h > 0:
                hist_sign += 1
            else:
                hist_sign -= 1
                
        if hist_sign == -5 and sample_hist[-2] < sample_hist[-1]:# and min(sample_hist) == sample_hist[-2]:
            print('#####macd buy signal')
            sig = 'buy'
        elif hist_sign == 5 and sample_hist[-2] > sample_hist[-1] and max(sample_hist) == sample_hist[-2]:
            print('#####macd sell signal')
            sig = 'sell'

        print('hist=>',hist[-5:len(hist)])
        print('hist_sign=>',hist_sign)
        return sig