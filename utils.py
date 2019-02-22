import dateutil
import dateutil.parser
import datetime
import time
import pytz
import numpy as np


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
        return round(price * (1 + 2 * fee_rate + profit_point), 3)
    else:
        return round(price * (1 - 2 * fee_rate - profit_point), 3)

def calc_future_interest(future_price, spot_price, end_time):
    t = (end_time - datetime.datetime.now()).days + 1
    print('t==>', t)
    return (future_price / spot_price - 1) / t

# def check_profit(a1,a2,b1,b2):
#     return (a1-a2)/a2+(b2-b1)/b1 -0.006


