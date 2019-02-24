

# ticker接口 20次/2s
# order下单接口 40次/2s
# 获取合约信息 20次/2s
import argparse
import okex.futures_api as futures_api
import datetime
import time
import config


class CheckApi(object):
    def __init__(self, instrument_id, ctype):
        self.instrument_id = instrument_id #'EOS-USD-190329'
        self.future_api = futures_api.FutureAPI(
            config.apikey, config.secretkey, config.password, True)
        self.ctype = ctype
    def check_ticker(self):
        try:
            ticker = self.future_api.get_specific_ticker(
                            instrument_id=self.instrument_id)
            print('ticker==>',ticker)
            print('time=>',datetime.datetime.now())
        except:
            print('ticker err')

    def check_submit_order(self):
        try:  
            order = self.future_api.take_order(
                    client_oid='',
                    instrument_id=self.instrument_id,
                    otype='1',
                    match_price='0',
                    size=1,
                    price=2,
                    leverage='10')
            print('order==>',order)
            print('time=>',datetime.datetime.now())
        except:
            print('order err')


    def run(self):
        if self.ctype == 'ticker':
            while True:
                self.check_ticker()
                time.sleep(0.200)
        elif self.ctype == 'order':
            while True:
                self.check_submit_order()
                time.sleep(0.055)
            
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--instrument_id', type=str, required=True, help='instrument_id')

    parser.add_argument(
        '--ctype', type=str, required=True, help='ctype')

    return parser.parse_args()

def main():
    print('#main start#')
    args = parse_args()
    instrument_id = args.instrument_id
    ctype = args.ctype
    print('args=>', args)
    c = CheckApi(instrument_id,ctype)
    c.run()
    print('#main end#')

if __name__ == '__main__':
    main()

# python check_api.py --instrument_id=EOS-USD-190301 --ctype=ticker
# python check_api.py --instrument_id=EOS-USD-190308 --ctype=ticker
# python check_api.py --instrument_id=EOS-USD-190329 --ctype=ticker

# python check_api.py --instrument_id=EOS-USD-190301 --ctype=order
# python check_api.py --instrument_id=EOS-USD-190308 --ctype=order
# python check_api.py --instrument_id=EOS-USD-190329 --ctype=order

# pm2 start check_api.py --name=EOS-USD-190301-ticker -- --instrument_id=EOS-USD-190301 --ctype=ticker
# pm2 start check_api.py --name=EOS-USD-190308-ticker -- --instrument_id=EOS-USD-190308 --ctype=ticker
# pm2 start check_api.py --name=EOS-USD-190329-ticker -- --instrument_id=EOS-USD-190329 --ctype=ticker

# pm2 start check_api.py --name=EOS-USD-190301-ticker -- --instrument_id=EOS-USD-190301 --ctype=order
# pm2 start check_api.py --name=EOS-USD-190308-ticker -- --instrument_id=EOS-USD-190308 --ctype=order
# pm2 start check_api.py --name=EOS-USD-190329-ticker -- --instrument_id=EOS-USD-190329 --ctype=order

