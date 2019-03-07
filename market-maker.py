
import redis
import json

r = redis.Redis(host='10.10.20.60', port=6379, password='nowdone2go', decode_responses=True)


ps = r.pubsub()
ps.subscribe(['okex.order_book.EOS/USDT'])  #订阅消息
print('##main start')


def handle_data(data):
#     ask_one = min([a['price'] for a in data['asks']])
#     bid_one = max([a['price'] for a in data['bids']])
    ask_one = data['asks'][-1]['price']
    ask_one_amount = data['asks'][-1]['amount']
    bid_one = data['bids'][0]['price']
    bid_one_amount = data['bids'][0]['amount']
    spread = ask_one-bid_one
    print('ask_one=>',ask_one, ' amount=>', ask_one_amount)
    print('bid_one=>',bid_one, ' amount=>', bid_one_amount)
    print('spread==>', spread)
    print('spread rate==>', ask_one/bid_one)

    

def check_position():
        # /api/spot/v3/accounts eos 1, 2, 3 uint=0.1

     pass

# /api/spot/v3/orders 下单
# /api/spot/v3/orders/<order_id> 检查订单状态
# /api/spot/v3/cancel_orders/<order_id> 撤单






for item in ps.listen():		#监听状态：有消息发布了就拿过来
    if item['type'] == 'message':
        # print(item['channel'])
        data = json.loads(item['data'])
        handle_data(data)
        # print(data)
        # asks = data['asks']
        # bids = data['bids']
        # asks_sum = sum([a['amount'] for a in asks])
        # bids_sum = sum([b['amount'] for b in bids])
        # print('asks_sum=>',asks_sum)
        # print('bids_sum=>',bids_sum)
        # if asks[0]['amount'] < 1000 and asks[1]['amount'] < 1000 :
        #     print('===============')

        # if bids[0]['amount'] < 1000 and bids[1]['amount'] < 1000 :
        #     print('**************')


# class OrderManager():

