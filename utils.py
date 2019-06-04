import dateutil
import dateutil.parser
import datetime
import time
import pytz
import numpy as np
from json import JSONDecoder, JSONEncoder
import math

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

def diff_datetime(stime, etime):
    timedelta = etime.timestamp()-stime.timestamp()
    days = math.floor(timedelta/86400)
    timedelta = timedelta%86400                   
    hours = math.floor(timedelta/3600)
    timedelta = timedelta%3600
    minutes = math.floor(timedelta/60)
    return {'days': days, 'hours': hours, 'minutes': minutes}

def get_float_precision(data):
    s_data = str(data)
    tmp = s_data.split('.')
    if len(tmp) < 2:
        return 0
    else:
        return len(tmp[1])


class JSONDateTimeEncoder(JSONEncoder):

    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return {
                '__type__': 'datetime',
                'year': obj.year,
                'month': obj.month,
                'day': obj.day,
                'hour': obj.hour,
                'minute': obj.minute,
                'second': obj.second,
                'microsecond': obj.microsecond,
            }
        else:
            return JSONEncoder.default(self, obj)


class JSONDateTimeDecoder(JSONDecoder):

    def __init__(self, *args, **kargs):
        JSONDecoder.__init__(
            self, object_hook=self.dict_to_object, *args, **kargs)

    def dict_to_object(self, date):
        if '__type__' not in date:
            return date

        type = date.pop('__type__')
        try:
            date_obj = datetime.datetime(**date)
            return date_obj
        except ValueError:
            date['__type__'] = type

            return date