# -*- coding: utf-8 -*-

# from exchange.okex.futures_api import future as okex_future_api


import exchange.okex.futures_api as okex_future
import time
import datetime
import json
class BooksAnalysis(object):

    def __init__(self, exchange='okex'):
        self._exchange = exchange
        self.okex_future_api = okex_future.FutureAPI('21312408-9af7-4572-a6db-930e40f7ce61', '7A3ACA71DBC68F5A8A37B60C65740122', 'Xjc12345', True)

    def get_order_book(self, instrument_id, size=200):
        ret = {'asks': [], 'bids': []}
        if self._exchange == 'okex':
            r_data = self.okex_future_api.get_depth(instrument_id, size)
            for ask in r_data['asks']:
                ret['asks'].append({'price': ask[0], 'volume': ask[1], 'count': ask[3]})
            for bid in r_data['bids']:
                ret['bids'].append({'price': bid[0], 'volume': bid[1], 'count': bid[3]})
        return ret

    def get_trade_book(self, instrument_id, limit=100):
        if self._exchange == 'okex':
            r_data = self.okex_future_api.get_trades(instrument_id, 3, 4, limit)
            return r_data[0]


    def order_book_analysis(self, instrument_id, size=200):
        order_books = self.get_order_book(instrument_id, size)
        bid_volume = sum(x['volume'] for x in order_books['bids'])
        ask_volume = sum(x['volume'] for x in order_books['asks'])
        bid_count = sum(x['count'] for x in order_books['bids'])
        ask_count = sum(x['count'] for x in order_books['asks'])
        gap_volume = bid_volume - ask_volume
        gap_rate = str(round((gap_volume*100 / min(bid_volume, ask_volume)), 2)) + '%'
        print('ask_volume =>', ask_volume)
        print('bid_volume =>', bid_volume)
        print('bid_count =>', bid_count)
        print('ask_count =>', ask_count)
        print('gap_volume =>', gap_volume)
        print('gap_rate =>', gap_rate)



    def trade_book_analysis(self, instrument_id, limit=100):
        trade_books = self.get_trade_book(instrument_id, limit)
        sell_trade_volume = 0
        buy_trade_volume = 0
        for r in trade_books:
            if r['side'] == 'sell':
                sell_trade_volume += int(r['qty'])
            elif r['side'] == 'buy':
                buy_trade_volume += int(r['qty'])
        print('sell_trade_volume =>', sell_trade_volume)
        print('buy_trade_volume =>', buy_trade_volume)
        print('gap_trade_volume =>', buy_trade_volume - sell_trade_volume)

        # min_date_ms = min(x['date_ms'] for x in r_data)
        # max_date_ms = max(x['date_ms'] for x in r_data)


def main():
    print('main start ...')
    books_analysis = BooksAnalysis('okex')
    while True:
        print('######################################')
        print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        instrument_id = 'EOS-USD-190329'
        books_analysis.order_book_analysis(instrument_id, 200)
        books_analysis.trade_book_analysis(instrument_id, 100)
        time.sleep(3)

if __name__ == '__main__':
    main()


