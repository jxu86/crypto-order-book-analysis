# -*- coding: utf-8 -*-

# from exchange.okex.futures_api import future as okex_future_api


import exchange.okex.futures_api as okex_future

class BooksAnalysis(object):

    def __init__(self, exchange='okex'):
        self._exchange = exchange
        self.okex_future_api = okex_future.FutureAPI('21312408-9af7-4572-a6db-930e40f7ce61', '7A3ACA71DBC68F5A8A37B60C65740122', 'Xjc12345', True)

    def get_order_book(self, instrument_id, size=200):
        print('###get_order_book')
        ret = []
        if self._exchange == 'okex':
            ret = self.okex_future_api.get_depth(instrument_id, size)
        return ret

    def order_book_analysis(self, instrument_id, size=200):

        order_books = self.get_order_book(instrument_id, size)
        print('order_books =>', order_books)





def main():
    print('main start ...')
    books_analysis = BooksAnalysis('okex')
    books_analysis.order_book_analysis('EOS-USD-181228', 200)
    print('main end ...')

if __name__ == '__main__':
    main()


