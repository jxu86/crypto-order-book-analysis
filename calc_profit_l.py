import sys
sys.path.append('../lsmmp')
# from communicate_v2 import OKexSpotV3
# from communicate_func import gene_id,http_run2

import asyncio
import _thread
from datetime import datetime as dt
import pandas as pd
import requests
import pytz
import hmac
import base64
import time
import config 
import datetime
# loop = asyncio.new_event_loop()
# _thread.start_new_thread(http_run2,(loop,))


class OKexSpotV3_local:
    def __init__(self,url,apikey,secretkey,PASSPHRASE):
        #www.coinall.com
        self.__url = url
        self.__apikey = apikey
        self.__secretkey = secretkey
        self.PASSPHRASE = PASSPHRASE

    def parse_params_to_str(self,params):
        url = '?'
        for key, value in params.items():
            url = url + str(key) + '=' + str(value) + '&'
        return url[0:-1]

    def signature(self,timestamp, method, request_path, body, secret_key):
        if str(body) == '{}' or str(body) == 'None':
            body = ''
        message = str(timestamp) + str.upper(method) + request_path + str(body)
        print (message)
        mac = hmac.new(bytes(secret_key, encoding='utf8'), bytes(message, encoding='utf-8'), digestmod='sha256')
        d = mac.digest()
        return str(base64.b64encode(d),'utf-8')
        return base64.b64encode(d)

    def get_header(self,api_key, sign, timestamp, passphrase):
        CONTENT_TYPE = 'Content-Type'
        OK_ACCESS_KEY = 'OK-ACCESS-KEY'
        OK_ACCESS_SIGN = 'OK-ACCESS-SIGN'
        OK_ACCESS_TIMESTAMP = 'OK-ACCESS-TIMESTAMP'
        OK_ACCESS_PASSPHRASE = 'OK-ACCESS-PASSPHRASE'
        header = dict()
        header[CONTENT_TYPE] = 'application/json'
        header[OK_ACCESS_KEY] = api_key
        header[OK_ACCESS_SIGN] = sign
        header[OK_ACCESS_TIMESTAMP] = str(timestamp)
        header[OK_ACCESS_PASSPHRASE] = passphrase
        return header

    def get_utc_iso_time(self,timezone = None,target_dt = None,):
        # utc_tz = pytz.timezone('UTC')
        if target_dt != None:
            return target_dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        if timezone == None:
            now = dt.now()
        else:
            now = dt.now(timezone)
        return now.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    async def _get(self,url,params,header,id,name):
        # print (url,params)
        headers = header
        async with ClientSession as conn_get:
            async with conn_get.get(url,params=params,headers = headers) as resp:
                text = await (resp.text())
                # print (text)
                self.results[id] = (resp.status,text,name)
                # future.set_result((id,resp.status,text))
        return True

    def fills(self,symbol,status = None,from_page = None,to_page = None,name = 'strategy_manager'):
        symbol = symbol.replace('_','-').upper()
        FILLS_RESOURCE = '/api/spot/v3/orders/'  #+ '?from=2&to=4&limit=30&instrument_id=BTC-USD-181228'
        select_api = 0
        timestamp = self.get_utc_iso_time( pytz.timezone('UTC'))[:-4] + 'Z'
        params = {
                    'status':'filled%7Cpart_filled',
                    'instrument_id':symbol,
                    # 'limit':100,
                    # 'from':'2386869858338816',
                    # 'to':to_page,
                    # 'order_id':'1663148946529280',
                    # 'instrument_id':'btc-usdt',#'BTC-USD-181228',
                    # 'from':1,
                    # 'to':3,
                    }
        if from_page is not None:
            params['from'] = from_page
        if to_page is not None:
            params['to'] = to_page
        sign = self.signature(timestamp,'GET', FILLS_RESOURCE + self.parse_params_to_str(params), '{}', self.__secretkey[select_api])
        header = self.get_header(self.__apikey[select_api], sign, timestamp, self.PASSPHRASE)

        print (select_api,self.__apikey[select_api],self.__secretkey[select_api],FILLS_RESOURCE + self.parse_params_to_str(params))
        # a = asyncio.run_coroutine_threadsafe(self._get('https://'+self.__url+FILLS_RESOURCE ,params=params,header = header), self.loop)
        response = requests.get('https://'+self.__url+FILLS_RESOURCE+ self.parse_params_to_str(params)  ,data="",headers = header)
        return response.json()

    def depth(self,symbol):
        DEPTH_RESOURCE = '/api/spot/v3/products/'
        params = {'size': 5}
        product_id = symbol.upper().replace('_','-')
        select_api = 0
        response = requests.get('https://'+self.__url+DEPTH_RESOURCE + str(product_id) + '/book'+ self.parse_params_to_str(params)  ,data="")
        # return self.httpGet(DEPTH_RESOURCE,params)
        # response = asyncio.run_coroutine_threadsafe(self._get('https://'+self.__url+DEPTH_RESOURCE + str(product_id) + '/book',params=param_dict,header = {},id = task_id,name = 'depth'), self.loop)
        return response.json()

def get_fills_order(message = None,set_time = None,begin_time = None,communicate_engine = None,symbol = None):
    #'2018-11-06T07:22:10.000Z'
    volume = 0
    order_id_list = []
    total_order = []
    anchor_message = []
    if message == None:
        init_from = None
        while True:
            if init_from == None:
                message = communicate_engine.fills(symbol = symbol )
                time.sleep(0.1)
                try:
                    init_from = message[-1]['order_id']
                except:
                    print (message,'may the bug has been triggered')
                    return volume,total_order
                print (init_from,message[0]['created_at'],message[-1]['created_at'])
            else:
                message = communicate_engine.fills(symbol = symbol,to_page = init_from )
                time.sleep(0.1)
                try:
                    init_from = message[-1]['order_id']
                except:
                    print (message,'may the bug has been triggered')
                    return volume,total_order
                print (init_from,message[0]['created_at'],message[-1]['created_at'])
            if message == anchor_message:
                print ('order message equals to anchor message',message)
                return volume,total_order
            anchor_message = message
            if isinstance(message,list) == True:

                for sample in message:
                    # print ((dt.strptime(sample['timestamp'], "%Y-%m-%dT%H:%M:%S.%fZ") - time).total_seconds())
                    # print (dt.strptime(sample['timestamp'], "%Y-%m-%dT%H:%M:%S.%fZ"),time)
                    # print (dt.strptime(sample['timestamp'], "%Y-%m-%dT%H:%M:%S.%fZ") > time)
                    if dt.strptime(sample['timestamp'], "%Y-%m-%dT%H:%M:%S.%fZ") > set_time :
                        if (begin_time == None or dt.strptime(sample['timestamp'], "%Y-%m-%dT%H:%M:%S.%fZ") < begin_time):
                            if sample['order_id'] not in order_id_list:
                                volume += abs(float(sample['filled_size']))
                                order_id_list.append(sample['order_id'])
                                total_order.append(sample)
                    else:
                        return volume,total_order
    if isinstance(message,list) == True:
        total_order = message
        for sample in message:
            # print ((dt.strptime(sample['timestamp'], "%Y-%m-%dT%H:%M:%S.%fZ") - time).total_seconds())
            # print (dt.strptime(sample['timestamp'], "%Y-%m-%dT%H:%M:%S.%fZ"),time)
            # print (dt.strptime(sample['timestamp'], "%Y-%m-%dT%H:%M:%S.%fZ") > time)
            if time == None or dt.strptime(sample['timestamp'], "%Y-%m-%dT%H:%M:%S.%fZ") > time:
                if sample['order_id'] not in order_id_list:
                    volume += abs(float(sample['filled_size']))
                    order_id_list.append(sample['order_id'])
        return volume
    else:
        print ('no info ')
        return False

class analysis_tradelog():
    def __init__(self,tradelog,price = None):
        self.tradelog = tradelog
        self.price = price
        self.set_direction()
    def set_direction(self):
        if self.tradelog.shape[0] == 0:
            print ('empth tradelog found')
            return
        self.tradelog['direction'] = [1 if s == 'buy' else -1 for s in self.tradelog['side']]
    def cal_diff(self,diff = None):
        if self.tradelog.shape[0] == 0:
            print ('empth tradelog found')
            return diff
        symbol_name = self.tradelog['instrument_id'].values[0]
        if diff == None:
            diff = {n:0 for n in symbol_name.split('-')}
        for n in symbol_name.split('-'):
            if n == symbol_name.split('-')[0]:
                diff[n] = diff.get(n,0) + (self.tradelog['direction'] * self.tradelog['filled_size'].astype('float')).sum()
            else:
                diff[n] = diff.get(n,0) + (-1 * self.tradelog['direction'] * self.tradelog['filled_notional'].astype('float')).sum()
        return diff

    def cal_profit(self,diff,base = 'usdt'):
        profit = 0
        if diff == None or len(list(diff.keys())) == 0:
            print ('diff dict is empty')
            return profit
        for n in diff.keys():
            if n.lower() == base:
                profit += diff[n]
            else:
                pair_name = n.lower() + '_' + base
                if pair_name in self.price:
                    profit += diff[n] * self.price[pair_name]
                else:
                    self.price[pair_name] = get_ticker(pair_name)
                    profit += diff[n] * self.price[pair_name]
        return profit

    def cal_volume(self,base = 'btc'):
        volume = 0
        if self.tradelog.shape[0] == 0:
            print ('empth tradelog found')
            return volume
        volume = self.tradelog['filled_size'].astype('float').sum()
        symbol_name = self.tradelog['instrument_id'].values[0]
        n = symbol_name.split('-')[0]
        pair_name = n.lower() + '_' + base
        if pair_name in self.price:
            volume = volume * self.price[pair_name]
        else:
            self.price[pair_name] = get_ticker(pair_name)
            volume = volume * self.price[pair_name]
        return volume

def get_order_df(symbol = 'xrp_usdt',time =  dt(2019,2,18,16,0),begin_time = None):
    a,order_list = get_fills_order(message = None,set_time = time,begin_time = begin_time,communicate_engine = communicate_engine,symbol = symbol)
    if len(order_list) == 0:
        return pd.DataFrame()
    order_dict = {k:[] for k in order_list[0].keys()}
    for sample in order_list:
        for k in order_dict.keys():
            order_dict[k].append(sample[k])
    df = pd.DataFrame.from_dict(order_dict)
    return df

def get_ticker( symbol):
    if symbol.split('_')[0] == symbol.split('_')[1]:
        return 1
    try:
        data = communicate_engine.depth(symbol)
        ask = float(data['asks'][0][0])
        bid = float(data['bids'][0][0])
        return (ask+bid) / 2
    except:
        symbol = symbol.split('_')[1] + '_' + symbol.split('_')[0]
        data = communicate_engine.depth(symbol)
        ask = float(data['asks'][0][0])
        bid = float(data['bids'][0][0])
        return 1./((ask+bid) / 2)


if __name__ == '__main__':
    # import global_config as cf
    apikey = config.yy_apikey #cf.okex_v3_config['apikey']
    secretkey = config.yy_secretkey  #cf.okex_v3_config['secretkey']
    passphrase = config.yy_passphrase
    # set_time = dt(2019,2,1,16,0)
    # end_time = dt(2019,3,4,16,0)
    # c_time = set_time
    subscribe_okex = ['xrp_eth','eos_eth','neo_btc']
    base_for_cal_profit = 'eth'
    base_for_cal_volume = 'eth'
    # time_list = [dt(2019,2,1,14,0),dt(2019,2,26,16,0),dt(2019,2,26,16,0),dt(2019,2,27,16,0),dt(2019,2,28,16,0),dt(2019,3,1,16,0)]
    time_list = pd.date_range('2/1/2019', periods=32, freq='1D')
    ret = []
    for t in time_list:
        # print('t=>', t)
        # t = datetime.datetime.strptime(t,'%Y-%m-%d')
        print('t=>', t)
        print('t=>', t+datetime.timedelta(days=1))
        communicate_engine = OKexSpotV3_local('www.okex.com',[apikey],[secretkey],PASSPHRASE = passphrase)
        all_trade_log = {}
        for symbol in subscribe_okex:#subscribe_okex:
            all_trade_log[symbol] = get_order_df(symbol,time = t,begin_time =t+datetime.timedelta(days=1))
        diff = None
        volume = 0
        for symbol in all_trade_log:
            a = analysis_tradelog(all_trade_log[symbol],price = {})
            diff = a.cal_diff(diff)
            profit = a.cal_profit(diff,base = base_for_cal_profit)
            volume = a.cal_volume( base = base_for_cal_volume)
            if diff:
                diff['datetime'] = t
                diff['profit'] = profit
                diff['symbol'] = symbol
                diff['volume'] = volume
                diff['return'] = profit/volume
                print (symbol,'profit:',profit,diff,a.price)

                ret.append(diff)
            diff = None
            # for base in ['btc','usdt','eth']:
            #     profit = a.cal_profit(diff,base = base)
            #     print (symbol,'profit:',profit,diff,a.price)

        # print ('volume : ',volume)
        print('ret:', ret)
    pd.DataFrame.from_dict(ret).to_csv('./data/total_summary.csv')
    # print (all_trade_log)
