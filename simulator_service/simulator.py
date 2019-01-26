import datetime
from mongo_service.mongodb import MongoService

class SimulatorService(object):

    def __init__(self):
        self.accountId = '1'
        self.mongodb = MongoService()


    def _add_order(self, side, pair, num, price):
        data = {
            'accountId': self.accountId,
            'side': side,
            'pair': pair,
            'num': num,
            'price': price,
            'total': num*price,
            'createdAt': datetime.datetime.now(),
            'updatedAt': datetime.datetime.now()
        }
        self.mongodb.update(self.mongodb.order, {'createdAt': data['createdAt']}, {'$set': data})


    def _update_account(self, side, pair, num, price):
        data = {
            'usd': -num*price,
            pair: num
        }
        if side == 'sell':
            data['usd'] = num*price
            data[pair] = -num

        self.mongodb.update(self.mongodb.account, {'accountId': self.accountId}, {'$inc': {'usd': data['usd'], pair: data[pair]}})


    def submit_order(self, side, pair, num, price):
        self._add_order(side, pair, num, price)
        self._update_account(side, pair, num, price)




def main():
    simulator = SimulatorService()
    # simulator.submit_order('buy', 'eos', 100, 2)
    simulator.submit_order('sell', 'eos', 100, 2)



if __name__ == '__main__':
    main()










