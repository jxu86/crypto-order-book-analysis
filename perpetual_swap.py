import okex.swap_api as swap_api
from mongo_service.mongodb import MongoService
import config
import utils
import datetime


class Swap(object):
    def __init__(self):
        self.swap_api = swap_api.SwapAPI(config.apikey, config.secretkey, config.password, True)
        self.mongodb = MongoService(
            host=config.mongo_host, port=config.mongo_port)

    def get_instrument_ids(self):
        instruments = self.swap_api.get_instruments()
        instrument_ids = [i['instrument_id'] for i in instruments]
        return instrument_ids


    def get_historical_funding(self, instrument_id, froms='1'):
        h_fund = self.swap_api.get_historical_funding_rate(instrument_id=instrument_id, froms=froms, limit='100')
        # print('h_fund=>',h_fund)
        return h_fund

    def save_data(self,data):
        for d in data:
            # d['instrument_id'] =  instrument_id
            d['created_at'] = datetime.datetime.now()
            d['funding_time'] =  utils.utcstr_to_datetime(d['funding_time'])
            d['funding_rate'] = float(d['funding_rate'])
            d['realized_rate'] = float(d['realized_rate'])
            d['interest_rate'] = float(d['interest_rate'])
            self.mongodb.update(self.mongodb.swap_funding_rate, {'instrument_id': d['instrument_id'], 'funding_time': d['funding_time']},{'$set': d})

    def run(self):
        instrument_ids = self.get_instrument_ids()
        for instrument_id in instrument_ids:
            print('####instrument_id=>', instrument_id)
            froms = 1
            while True:
                funding_datas = self.get_historical_funding(instrument_id, froms=str(froms))
                if len(funding_datas) == 0:
                    break
                self.save_data(funding_datas)
                froms += 1

def main():
    print('###main start###')
    swap = Swap()
    swap.run()
    print('###main end###')


if __name__ == '__main__':
    main()



    
