import zlib
import websocket
try:
    import thread
except ImportError:
    import _thread as thread
import time


g_trade_books = []



def _decompress(data):
    decompress = zlib.decompressobj(
        -zlib.MAX_WBITS  # see above
    )
    inflated = decompress.decompress(data)
    inflated += decompress.flush()
    return inflated.decode()

def on_message(ws, msg):
    msg = _decompress(msg) if isinstance(msg, bytes) else msg
    data = eval(msg)
    channel = data[0]['channel']
    print('channel==>', channel)

    if channel == "pong": #'{"event":"pong"}':
        print('pong ================================')
        # return self.pingpong.on_pong(msg)
    elif channel == 'ok_sub_futureusd_eos_trade_quarter':
        # print('msg=======>', msg)
        # print('data=======>', data[0]['data'][0][2])
        # print('data type=======>', type(data))
        # print('data asks len=======>', len(data[0]['data']['asks']))
        for x in data[0]['data']:
            g_trade_books.append({
                'price': float(x[1]),
                'volume': float(x[2]),
                'type': x[4],
                'time': x[3],
                'create_at': time.time()
            })
        calc_trade(g_trade_books)




def on_error(ws, error):
    print(error)

def on_close(ws):
    print("### closed ###")

def on_open(ws):
    def run(*args):
        # for i in range(3):
        #     time.sleep(1)
        #     ws.send("Hello %d" % i)
        # time.sleep(1)

        # ws.send("{'event':'addChannel','channel':'ok_sub_futureusd_eos_depth_quarter_20'}")
        ws.send("{'event':'addChannel','channel':'ok_sub_futureusd_eos_trade_quarter'}")
        # ws.close()
        print("thread terminating...")
    thread.start_new_thread(run, ())


def calc_trade(g_trade_books):
    # print('g_trade_books=>', g_trade_books)
    trade_books = []
    sec_60 = time.time() - 30
    ask_volume = 0
    bid_volume = 0
    for x in g_trade_books:
        if x['create_at'] >= sec_60:
            trade_books.append(x)
            if x['type'] == 'ask':
                ask_volume += x['volume']
            else:
                bid_volume += x['volume']

    g_trade_books = trade_books

    print('g_trade_books len ==>', len(g_trade_books))
    print('ask_volume ==>', ask_volume)
    print('bid_volume ==>', bid_volume)



if __name__ == "__main__":
    websocket.enableTrace(True)
    # ws_url = "ws://echo.websocket.org/"
    # ws_url = "wss://ws-feed.okex.com/"
    ws_future_url = "wss://real.okex.com:10440/ws/v1" # "wss://real.okex.com:10440/websocket/okexapi/"  #
    ws = websocket.WebSocketApp(ws_future_url,
                              on_message = on_message,
                              on_error = on_error,
                              on_close = on_close)
    ws.on_open = on_open
    ws.run_forever()
