# -*- coding: utf-8 -*-

# from exchange.okex.futures_api import future as okex_future_api


import exchange.okex.futures_api as okex_future

class BooksAnalysis(object):

    def __init__(self, exchange='okex'):
        self._exchange = exchange
        self.okex_future_api = okex_future.FutureAPI('XXX', 'XXX', 'XXX', True)

    def get_order_book(self, instrument_id, size=200):
        print('###get_order_book')
        ret = {'asks': [], 'bids': []}
        if self._exchange == 'okex':
            r_data = self.okex_future_api.get_depth(instrument_id, size)
            for ask in r_data['asks']:
                ret['asks'].append({'price': ask[0], 'volume': ask[1], 'count': ask[3]})
            for bid in r_data['bids']:
                ret['bids'].append({'price': bid[0], 'volume': bid[1], 'count': bid[3]})
        return ret

    def order_book_analysis(self, instrument_id, size=200):
        order_books = self.get_order_book(instrument_id, size)
        ask_volume = sum(x['volume'] for x in order_books['asks'])
        bid_volume = sum(x['volume'] for x in order_books['bids'])
        gap_volume = bid_volume - ask_volume
        gap_rate = str(round((gap_volume*100 / min(bid_volume, ask_volume)), 2)) + '%'
        print('ask_volume =>', ask_volume)
        print('bid_volume =>', bid_volume)
        print('gap_volume =>', gap_volume)
        print('gap_rate =>', gap_rate)






def main():
    print('main start ...')
    books_analysis = BooksAnalysis('okex')
    books_analysis.order_book_analysis('EOS-USD-181228', 200)

    print('main end ...')

if __name__ == '__main__':
    main()


