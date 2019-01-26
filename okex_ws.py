#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import abc
import argparse
import itertools
import logging
import re
import datetime
import os
import traceback
import websocket
import redis
import json
import copy
import zlib
# import config
import ccxt
import threading
import time
# from factory import Factory, Pairs, PingPong, Timer, to_statsd

# from okex_websocket_module import (
#     OkexDeals as OKExDeals,
#     OkexOrderBooks as OKExOrderBooks,
#     OKExKLineBasic,
#     OKExKLine1,
#     OKExKLine5,
#     OKExKLineD,
#     OKExKLineW
# )

class BooksAnalysis(object):
    def __init__(self):
        pass

    def calc_trade(self, g_trade_books):
        # print('g_trade_books=>', g_trade_books)
        trade_books = []
        sec_60 = time.time() - 30
        ask_volume = 0
        bid_volume = 0
        for x in g_trade_books:
            if x['create_at'] >= sec_60:
                trade_books.append(x)
                if x['transactionType'] == 'ask':
                    ask_volume += x['volume']
                else:
                    bid_volume += x['volume']

        g_trade_books = trade_books

        print('g_trade_books len ==>', len(g_trade_books))
        print('ask_volume ==>', ask_volume)
        print('bid_volume ==>', bid_volume)
        return g_trade_books

class Timer(object):

    def __init__(self, period, action=None):
        self.period = period
        self.action = action or (lambda: None)
        self._event = threading.Event()
        self.thread = threading.Thread(target=self._run)

    def _run(self):
        next_time = time.time() + self.period
        while not self._event.wait(next_time - time.time()):
            next_time += self.period
            self.action()

    def start(self):
        self.thread.start()

    def stop(self):
        self._event.set()

class Pairs:
    @staticmethod
    def get_ccxt_market_pairs(ignores=None, join='_'):

        if not ignores:
            ignores = set()

        pairs = []

        for pair in ccxt.okex().load_markets().keys():
            p, q = pair.lower().split('/')
            if p not in ignores and q not in ignores:
                pairs += [(p, q)]

        return [join.join(pair) for pair in pairs] if join else list(pairs)

class PingPong(object):

    def __init__(self, ws, msg, period=10.0, timeout=1.0, fails_allow=6):
        self.ws = ws
        self.msg = msg
        self.period = period
        self.timeout = timeout
        self.fails = 0
        self.fails_allow = fails_allow
        # Initialize later
        self._start = None
        self._end = None
        self.timer = Timer(period, self.ping)
        # self.LOG = log

    def start(self):
        self.timer.start()

    def stop(self):
        self.timer.stop()

    def ping(self):
        self._start = datetime.datetime.now()
        self.ws.send(self.msg)
        print('Sent ping message: {msg}...'.format(msg=self.msg))

    def on_pong(self, msg):
        # TODO: If `self.period` < `self.timeout`, the duration of
        # ping-pong is not accurate since `self._start` is overwritten
        # by subsequent `ping()`s
        self._end = datetime.datetime.now()
        took = (self._end - self._start).seconds
        if took > self.timeout:
            # print('Ping-Pong took too long ({took} > {timeout})'.format(
            #     took=took, timeout=self.timeout))
            self.fails += 1
            if self.fails >= self.fails_allow:
                print('ping-pong error')
                # self.LOG.error(
                #     'Too many fails on ping-pong (allow = {allow})'.format(
                #         allow=self.fails_allow))
        else:
            self.fails = 0
            # self.LOG.info('Received pong... (took: {took}s)'.format(took=took))

    def pong(self, msg):
        self.ws.send(msg)
        # self.LOG.info('Sent pong message: {msg}...'.format(msg=msg))


# r = redis.Redis(host='localhost', port=6379, password='nowdone2go', decode_responses=True)


LOG = None


def re_findone(regexp, string):
    results = re.findall(re.compile(regexp), string)
    return results[0] if results else None


def convert_type(lists, type_, iter_types=(list, tuple)):
    return [
        type_(el) if not isinstance(el, iter_types) else convert_type(
            el, type_, iter_types) for el in lists
    ]

class OKExSpotTask(object):

    prefix = ''

    def __init__(self, event, channel, parameters=None, init_data=None):
        self.event = event
        self.channel = channel
        self.parameters = parameters
        self.init_data = init_data or []

    def pack(self, x, y=None):

        def _to_list(x):
            return x if isinstance(x, list) else [x]

        def _pack(x, y):
            item = {
                'event': self.event,
                'channel': self.channel.format(x=x, y=y)
            }

            if self.parameters:
                item.update({'parameters': self.parameters})

            return item

        x, y = _to_list(x), _to_list(y)
        data = [_pack(_x, _y) for _x, _y in itertools.product(x, y)]

        return str(data)

    @property
    def hello(self):
        return self.pack(*self.init_data)

    @property
    def matcher(self):
        return re.compile(re.sub(r'\{[a-z]\}', '.*', self.channel))

    @abc.abstractclassmethod
    def parse(cls, data):
        pass

    @abc.abstractclassmethod
    def save(cls, data):
        pass


    @classmethod
    # @to_statsd(lambda cls, *args, **kwargs: cls.prefix)
    def on_message(cls, data):
        cls.save(cls.parse(data))

    @classmethod
    def set_prefixes(cls, prefix):
        prefixes = [] if not prefix else [prefix]
        prefixes += [cls.__name__, 'getDataCount']
        cls.prefix = '.'.join(prefixes)
        print('cls.prefix=====', cls.prefix)

    @classmethod
    def start(cls, prefix=None):
        cls.set_prefixes(prefix)

    @classmethod
    def stop(cls):
        cls.prefix = None


class OKExFutureTask(object):

    prefix = ''

    def __init__(self, op, args, parameters=None, init_data=None):
        self.op = op
        self.args = args
        self.parameters = parameters
        self.init_data = init_data or []

    def pack(self, x, y=None):

        def _to_list(x):
            return x if isinstance(x, list) else [x]

        def _pack(x, y):
            item = {
                'op': self.op,
                'args': self.args.format(x=x, y=y)
            }

            if self.parameters:
                item.update({'parameters': self.parameters})

            return item

        x, y = _to_list(x), _to_list(y)
        data = [_pack(_x, _y) for _x, _y in itertools.product(x, y)]

        return str(data)

    @property
    def hello(self):
        return self.pack(*self.init_data)

    @property
    def matcher(self):
        return re.compile(re.sub(r'\{[a-z]\}', '.*', self.args))

    @abc.abstractclassmethod
    def parse(cls, data):
        pass

    @abc.abstractclassmethod
    def save(cls, data):
        pass


    @classmethod
    # @to_statsd(lambda cls, *args, **kwargs: cls.prefix)
    def on_message(cls, data):
        cls.save(cls.parse(data))

    @classmethod
    def set_prefixes(cls, prefix):
        prefixes = [] if not prefix else [prefix]
        prefixes += [cls.__name__, 'getDataCount']
        cls.prefix = '.'.join(prefixes)
        print('cls.prefix=====', cls.prefix)

    @classmethod
    def start(cls, prefix=None):
        cls.set_prefixes(prefix)

    @classmethod
    def stop(cls):
        cls.prefix = None
    



class OKExFutureDepthTask(OKExFutureTask):

    # collection = OKExOrderBooks

    @classmethod
    def parse(cls, data):
        print('parse ==>data=>', data)
        # data = data[0]
        # re_pair = re.compile('spot_(.*?)_depth', re.S)
        # return {
        #     'pair': re.findall(re_pair, data['channel'])[0],
        #     'asks': convert_type(data['data']['asks'], float),
        #     'bids': convert_type(data['data']['bids'], float),
        #     'timestamp': data['data']['timestamp'],
        #     'createdAt': datetime.datetime.now(),
        # }

    @classmethod
    def save(cls, data):
        print('data==>', type(data))


class OKExOrderBookTask(OKExSpotTask):

    # collection = OKExOrderBooks

    @classmethod
    def parse(cls, data):
        print('parse ==>data=>', data)
        data = data[0]
        re_pair = re.compile('spot_(.*?)_depth', re.S)
        return {
            'pair': re.findall(re_pair, data['channel'])[0],
            'asks': convert_type(data['data']['asks'], float),
            'bids': convert_type(data['data']['bids'], float),
            'timestamp': data['data']['timestamp'],
            'createdAt': datetime.datetime.now(),
        }

    @classmethod
    def save(cls, data):
        # r_data = copy.copy(data)
        # r_data['createdAt'] = r_data['createdAt'].strftime("%Y-%m-%d %H:%M:%S.%f")
        print('data==>', type(data))
        # s_data = json.dumps(r_data)
        # r.set('ob_' + data['pair'], s_data)  # add redis
        # r.publish('ob_' + data['pair'], s_data)  # publish msg
        # cls.collection(
        #     asks=data['asks'],
        #     bids=data['bids'],
        #     createdAt=data['createdAt'],
        #     pair=data['pair'],
        #     timestamp=data['timestamp']
        #     ).save()


trade_book_datas = []
class OKExDealTask(OKExSpotTask):

    @classmethod
    def parse(cls, data):
        data_list = data[0]['data'][0]
        re_deal = re.compile('spot_(.*?)_deals', re.S)
        # print('data_list==>', data_list)
        return {
            'pair': re.findall(re_deal, data[0]['channel'])[0],
            'orderId': data_list[0],
            'price': float(data_list[1]),
            'volume': float(data_list[2]),
            'time': data_list[-2],
            'transactionType': data_list[-1],
            'createdAt': datetime.datetime.now(),
            'create_at': time.time()
        }

    @classmethod
    def save(cls, data):
        r_data = copy.copy(data)
        # r_data['createdAt'] = r_data['createdAt'].strftime("%Y-%m-%d %H:%M:%S.%f")
        # r_data['created_at'] = time.time() #r_data['createdAt'].strftime("%Y-%m-%d %H:%M:%S.%f")
        # s_data = json.dumps(r_data)
        # r.set('tb_' + data['pair'], s_data)  # add redis
        # r.publish('tb_' + data['pair'], s_data)  # publish msg
        # print('data==>', r_data)
        # print('data==>', type(data))
        trade_book_datas.append(r_data)
        # print('self.trade_book_datas==>', trade_book_datas)
        boos_analysis = BooksAnalysis()
        boos_analysis.calc_trade(trade_book_datas)



class OKExKlineBasicTask(OKExSpotTask):
    # collection = OKExKLineBasic

    @classmethod
    def parse(cls, data):
        data_list = data[0]['data']
        re_deal = re.compile('spot_(.*?)_kline', re.S)
        pair = re.findall(re_deal, data[0]['channel'])[0]
        return [{
            'pair': pair,
            'exchange': config.EXCHANGES['OKEX'],  # 交易所
            'ts': int(d[0]),
            'open': float(d[1]),
            'high': float(d[2]),
            'low': float(d[3]),
            'close': float(d[4]),
            'vol': float(d[5]),
            'createdAt': datetime.datetime.now()
        } for d in data_list]

    @classmethod
    def save(cls, data):
        pass
        # for d in data:
        #     cls.collection.objects(
        #         pair=d['pair'].replace('_', '/').upper(), ts=d['ts'], exchange=d['exchange']).upsert_one(
        #             open=d['open'],
        #             high=d['high'],
        #             low=d['low'],
        #             close=d['close'],
        #             vol=d['vol'],
        #             createdAt=d['createdAt']
        #     )


# class OKExKline1Task(OKExKlineBasicTask):
#     collection = OKExKLine1
#
#
# class OKExKline5Task(OKExKlineBasicTask):
#     collection = OKExKLine5
#
#
# class OKExKlineDTask(OKExKlineBasicTask):
#     collection = OKExKLineD
#
#
# class OKExKlineWTask(OKExKlineBasicTask):
#     collection = OKExKLineW


class OKExWebSocket(object):

    def __init__(self,
                 url,
                 tasks,
                 period=10.0,
                 timeout=10.0,
                 stats=None,
                 prefix=''):
        self.url = url
        self.tasks = tasks
        self.period = period
        self.timeout = timeout
        self.prefix = prefix
        # Initialize later
        self.ws = None
        self.pingpong = None
        # Statsd support
        self._stats_obj = stats
        self._stats_timer = None

    def start_timers(self):
        # Ping-pong
        self.pingpong = PingPong(
            self.ws,
            '{"event":"ping"}',
            period=self.period,
            timeout=self.timeout)
            # timeout=self.timeout, log=LOG)
        self.pingpong.start()

        # Statsd
        self._stats_timer = Timer(self.period, self._statsd_alive)
        self._stats_timer.start()
        for task in self.tasks:
            task.start(self.prefix)

    def stop_timers(self):
        self.pingpong.stop()
        self._stats_timer.stop()
        del self.pingpong
        del self._stats_timer
        for task in self.tasks:
            task.stop()

    def start(self):
        websocket.setdefaulttimeout(self.timeout)
        print('#####################start#################')
        # Initialize
        if self.ws is not None:
            del self.ws

        self.ws = websocket.WebSocketApp(
            self.url,
            on_message=self.on_message,
            on_error=self.on_error,
            on_open=self.on_open,
            on_close=self.on_close)

        # Connect to server
        #LOG.info('Starting websocket server')
        self.ws.run_forever()

    def dispatch(self, data, handler):
        for task in self.tasks:
            if re.match(task.matcher, data[0]['channel']):
                return getattr(task.__class__, handler)

    def on_hello(self, msg):
        pass
        # result = re_findone(r'"result":(\w+)', msg)

        # if result == 'true':
        #     channel = re_findone(r'"data":.+"channel":"(\w+)"', msg)
        #     #LOG.info('Subscribed channel: {channel}'.format(channel=channel))
        # else:
        #     kwargs = {
        #         'channel': re_findone(r'"channel":"(\w+)"', msg),
        #         'msg': re_findone(r'"error_msg":"(.+?)"', msg),
        #         'code': re_findone(r'"error_code":(\d+)', msg)
        #     }
            #LOG.warn(('Faield to subscribe channel: {channel}'
                      #', msg: {msg} ({code})').format(**kwargs))

    def on_open(self, ws):
        # Start all timers, can't do this in `connect` because it's
        # blocking
        # self.start_timers()

        # Send inital subscription requests to websocket server
        # for task in self.tasks:
        #     #LOG.info('Say hello to: {channel}'.format(channel=task.channel))
        #     ws.send(task.hello)
        ws.send(json.dumps({"op": "subscribe", "args": ["futures/depth5:BTC-USD-190329"]}))
        

    @staticmethod
    def _decompress(data):
        decompress = zlib.decompressobj(
            -zlib.MAX_WBITS  # see above
        )
        inflated = decompress.decompress(data)
        inflated += decompress.flush()
        return inflated.decode()

    def on_message(self, ws, msg):
        print('##on_message')
        # Ping-Pong
        msg = self._decompress(msg) if isinstance(msg, bytes) else msg
        print('msg==>', msg)
        # if msg == '{"event":"pong"}':
        #     return self.pingpong.on_pong(msg)

        # # Hello callback
        # if '"result"' in msg:
        #     return self.on_hello(msg)

        # # Dispatch `msg` to different channel handlers
        # data = eval(msg)
        # handler = self.dispatch(data, 'on_message')

        # if not callable(handler):
        #     #LOG.error('No match handler for unkown data: {data}'.format(data=data))
        #     return

        # handler(data)

    def on_error(self, ws, error):
        traceback.print_exc()
        #LOG.error('Error caught: {}'.format(error))

    def on_close(self, ws):
        #LOG.error('Client closed')
        self.stop_timers()
        self.start()

    def _stats(self, key, value, action='gauge'):
        if self._stats_obj is None:
            return

        getattr(self._stats_obj, action)(key, value)

    def _statsd_alive(self):
        prefixes = [] if not self.prefix else [self.prefix]
        prefixes += [self.__class__.__name__, 'heartbeat']
        prefix = '.'.join(prefixes)
        #LOG.info('Ping statsd[{prefix}: {incr}]...'.format(
        #    prefix=prefix, incr=1))

        self._stats(prefix, 1, action='incr')


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--logdir',
        type=str,
        default='/log',
        help='Log directory (default: "/log")')
    parser.add_argument(
        '--period',
        type=int,
        default=10,
        help='Period for timers (default: 10)')
    parser.add_argument(
        '-t',
        '--timeout',
        type=int,
        default=10.0,
        help='Connection timeout (default: 10)')
    parser.add_argument(
        '--prefix',
        type=str,
        default='blockChainCrawlers',
        help='Prefix for application group (default: "blockChainCrawlers")')
    parser.add_argument(
        '--method',
        type=str,
        default='kline',  # or books
        help='Split kline Data (default: "kline")')

    args = parser.parse_args()

    return args


if __name__ == '__main__':
    print('main start ==================>')
    # Parse command line arguments
    args = parse_args()

    # Define logger
    # script_name, _ = os.path.splitext(os.path.basename(__file__))
    # args.logdir = os.path.join(args.logdir, script_name)
    # os.makedirs(args.logdir, exist_ok=True)
    # LOG = Factory.get_logger(
    #     name=script_name,
    #     fmt=logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'),
    #     filename=os.path.join(
    #         args.logdir, '{name}.log'.format(name=(script_name + '_' + args.method))),
    #     rotated=True,
    #     file_options={'when': 'midnight'},
    #     logging_=logging)

    # Define statsd client
    # stats = Factory.stats(**config.statsd)

    # Define tasks
    # url = config.urls['okex']


    # url = 'wss://real.okex.com:10441/websocket'
    url = 'wss://real.okex.com:10442/ws/v3'
    # pairs = Pairs.get_ccxt_market_pairs(ignores={'usd'})[:1]
    # # pairs_kline = Pairs.get_ccxt_market_pairs(ignores={'usd'})
    # print('############main ==================>pairs=>', pairs)
    pairs = ['eos_usdt']
    depth = 20

    future_order_book_task = OKExFutureDepthTask(
        op='subscribe',
        args=["futures/depth5:EOS-USD-190329"])
    # order_book_task = OKExOrderBookTask(
    #     event='addChannel',
    #     channel='ok_sub_spot_{x}_depth_{y}',
    #     init_data=(pairs, depth))
    # deal_task = OKExDealTask(
    #     event='addChannel',
    #     channel='ok_sub_spot_{x}_deals',
    #     init_data=(pairs, ))
    # kline1_task = OKExKline1Task(
    #     event='addChannel',
    #     channel='ok_sub_spot_{x}_kline_1min',
    #     init_data=(pairs_kline, ))
    # kline5_task = OKExKline5Task(
    #     event='addChannel',
    #     channel='ok_sub_spot_{x}_kline_5min',
    #     init_data=(pairs_kline, ))
    # klined_task = OKExKlineDTask(
    #     event='addChannel',
    #     channel='ok_sub_spot_{x}_kline_day',
    #     init_data=(pairs_kline, ))
    # klinew_task = OKExKlineWTask(
    #     event='addChannel',
    #     channel='ok_sub_spot_{x}_kline_week',
    #     init_data=(pairs_kline, ))
    # job_list = [kline1_task, kline5_task, klined_task, klinew_task] if args.method == 'kline' else [order_book_task,
    #                                                                                                 deal_task]

    job_list = [future_order_book_task]
    # Run task manager
    ws = OKExWebSocket(
        url, job_list,
        period=10, # args.period,
        timeout=10 # args.timeout,
        # stats=stats,
        # prefix=args.prefix
    )
    ws.start()
