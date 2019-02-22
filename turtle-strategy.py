import numpy as np
import talib
import math

def getExtremem(arrayHighPriceResult, arrayLowPriceResult):
    np_arrayHighPriceResult = np.array(arrayHighPriceResult[:-1])
    np_arrayLowPriceResult = np.array(arrayLowPriceResult[:-1])
    maxResult = np_arrayHighPriceResult.max()
    minResult = np_arrayLowPriceResult.min()
    return [maxResult, minResult]
    
def getAtrAndUnit(atrArrayResult, atrLengthResult, portfolioValueResult):
    atr = atrArrayResult[atrLengthResult-1]
    unit = math.floor(portfolioValueResult * .01 / atr)
    return [atr, unit]
    
def getStopPrice(firstOpenPriceResult, units_hold_result, atrResult):
    stopPrice =  firstOpenPriceResult - 2*atrResult + (units_hold_result-1)*0.5*atrResult
    return stopPrice


def init(context):
    context.tradedayNum = 0
    context.unit = 0
    context.atr = 0
    context.tradingSignal = 'start' 
    context.preTradingSignal = ''
    context.units_hold_max = 4
    context.units_hold = 0
    context.quantity = 0
    context.max_add = 0
    context.firstOpenPrice = 0
    context.s = 'CSI300.INDX'
    update_universe([context.s])
    context.openObserveTime = 55;
    context.closeObserveTime = 20;
    context.atrTime = 20;

def handle_bar(context, bar_dict):
    portfolioValue = context.portfolio.portfolio_value
    highPrice = history(context.openObserveTime+1, '1d', 'high')[context.s]
    lowPriceForAtr = history(context.openObserveTime+1, '1d', 'low')[context.s]
    lowPriceForExtremem = history(context.closeObserveTime+1, '1d', 'low')[context.s]
    closePrice = history(context.openObserveTime+2, '1d', 'close')[context.s]
    closePriceForAtr = closePrice[:-1]
    
    atrArray = talib.ATR(highPrice.values, lowPriceForAtr.values, closePriceForAtr.values, timeperiod=context.atrTime)
    
    maxx = getExtremem(highPrice.values, lowPriceForExtremem.values)[0]
    minn = getExtremem(highPrice.values, lowPriceForExtremem.values)[1]
    atr = atrArray[-2]
    

    if (context.tradingSignal != 'start'):
        if (context.units_hold != 0):
            context.max_add += 0.5 * getAtrAndUnit(atrArray, atrArray.size, portfolioValue)[0]
    else:
        context.max_add = bar_dict[context.s].last
        
    
    curPosition = context.portfolio.positions[context.s].quantity
    availableCash = context.portfolio.cash
    marketValue = context.portfolio.market_value
    
    
    if (curPosition > 0 and bar_dict[context.s].last < minn):
        context.tradingSignal = 'exit'
    else:
        if (curPosition > 0 and bar_dict[context.s].last < getStopPrice(context.firstOpenPrice, context.units_hold, atr)):
            context.tradingSignal = 'stop'
        else:
            if (bar_dict[context.s].last > context.max_add and context.units_hold != 0 and context.units_hold < context.units_hold_max and availableCash > bar_dict[context.s].last*context.unit):
                context.tradingSignal = 'entry_add'
            else:
                if (bar_dict[context.s].last > maxx and context.units_hold == 0):
                    context.max_add = bar_dict[context.s].last
                    context.tradingSignal = 'entry'
                    
                
    atr = getAtrAndUnit(atrArray, atrArray.size, portfolioValue)[0]
    if context.tradedayNum % 5 == 0:
        context.unit = getAtrAndUnit(atrArray, atrArray.size, portfolioValue)[1]
    context.tradedayNum += 1
    context.quantity = context.unit
    
    
    
    if (context.tradingSignal != context.preTradingSignal or (context.units_hold < context.units_hold_max and context.units_hold > 1) or context.tradingSignal == 'stop'):
        
        if context.tradingSignal == 'entry':
            context.quantity = context.unit
            if availableCash > bar_dict[context.s].last*context.quantity:
                order_shares(context.s, context.quantity)
                context.firstOpenPrice = bar_dict[context.s].last
                context.units_hold = 1
                
                
        if context.tradingSignal == 'entry_add':
            context.quantity = context.unit
            order_shares(context.s, context.quantity)
            context.units_hold += 1
            
            
        if context.tradingSignal == 'stop':
            if (context.units_hold > 0):
                order_shares(context.s, -context.quantity)
                context.units_hold -= 1
                
                
        if context.tradingSignal == 'exit':
            if curPosition > 0:
                order_shares(context.s, -curPosition)
                context.units_hold = 0
                
                
    context.preTradingSignal = context.tradingSignal










# https://www.cnblogs.com/alonecat06/p/9503331.html

    # 导入函数库
from jqdata import *
import pandas as pd
import numpy as np

## 初始化函数，设定基准等等
def initialize(context):
    set_params(context)
    # 设定所交易期货指数作为基准
    set_benchmark(get_future_code(g.future_index))
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    # 过滤掉order系列API产生的比error级别低的log
    # log.set_level('order', 'error')
    # 输出内容到日志 log.info()
    log.info('初始函数开始运行且全局只运行一次')

    ### 期货相关设定 ###
    # 设定账户为金融账户
    set_subportfolios([SubPortfolioConfig(cash=context.portfolio.starting_cash, type='index_futures')])
    # 期货类每笔交易时的手续费是：买入时万分之0.23,卖出时万分之0.23,平今仓为万分之23
    set_order_cost(OrderCost(open_commission=0.000023, close_commission=0.000023,close_today_commission=0.0023), type='index_futures')
    # 设定保证金比例
    set_option('futures_margin_rate', 0.15)

    # 设置期货交易的滑点
    set_slippage(FixedSlippage(0.2))
    # 运行函数（reference_security为运行时间的参考标的；传入的标的只做种类区分，因此传入'IF1512.CCFX'或'IH1602.CCFX'是一样的）
      # 开盘前运行
    run_daily( before_market_open, time='before_open', reference_security=get_future_code(g.future_index))
      # 开盘时运行
    run_daily( market_open, time='open', reference_security=get_future_code(g.future_index))
      # 收盘后运行
    run_daily( after_market_close, time='after_close', reference_security=get_future_code(g.future_index))


## 开盘前运行函数
def before_market_open(context):
    # 输出运行时间
    log.info('函数运行时间(before_market_open)：'+str(context.current_dt.time()))

    # 给微信发送消息（添加模拟交易，并绑定微信生效）
    #send_message('美好的一天~')

    ## 获取要操作的股票(g.为全局变量)
      # 获取当月期货合约
    g.future = get_dominant_future(g.future_index)


## 开盘时运行函数
def market_open(context):
    calc_window = int(3.45*(g.ATRLength + 1))
    price_list = attribute_history(g.future, calc_window + 1, '1d', ['close','high','low'])
    
    if len(price_list) == 0:
        return # 如果没有数据，返回
    
    AvgTR = XAverage(TrueRange(price_list, calc_window),g.ATRLength)
    N = AvgTR[-2]
    TurtleUnits = get_unit(context.portfolio.total_value, N, g.future_index, g.RiskRatio)

    DonchianHi = HighestFC(price_list['high'], g.boLength)
    DonchianLo = LowestFC(price_list['low'], g.boLength)
    
    ExitLowestPrice = LowestFC(price_list['low'], g.teLength)
    ExitHighestPrice = HighestFC(price_list['high'], g.teLength)
    
    High = price_list['high'].iloc[-1]
    Low = price_list['low'].iloc[-1]
    
    # 当不使用过滤条件，或者使用过滤条件并且条件为PreBreakoutFailure为True进行后续操作
    if g.MarketPosition == 0:
        log.info(context.current_dt.time(), ' High:', High, ' DonchianHi:', DonchianHi, ' Low:', Low, ' DonchianLo:', DonchianLo)
        # 突破开仓
        if High > DonchianHi and TurtleUnits >= 1:
            # 开仓价格取突破上轨+一个价位和最高价之间的较小值，这样能更接近真实情况，并能尽量保证成交
            # myEntryPrice = min(High, DonchianHi)# + MinPoint)
            # myEntryPrice = Open if myEntryPrice < Open else myEntryPrice # 大跳空的时候用开盘价代替
            order(g.future, TurtleUnits, side='long')
            g.MarketPosition = 1

        if Low < DonchianLo and TurtleUnits >= 1:
            # 开仓价格取突破下轨-一个价位和最低价之间的较大值，这样能更接近真实情况，并能尽量保证成交
            # myEntryPrice = max(Low,DonchianLo)# - MinPoint)
            # myEntryPrice = Open if myEntryPrice > Open else myEntryPrice # 大跳空的时候用开盘价代替
            order(g.future, TurtleUnits, side='short')
            g.MarketPosition = -1

    if g.MarketPosition == 1:
        # 有多仓的情况
        log.info('ExitLowestPrice=', ExitLowestPrice)
        if Low < ExitLowestPrice:
            # myExitPrice = max(Low,ExitLowestPrice)# - MinPoint)
            # myExitPrice = Open if myExitPrice > Open else myExitPrice # 大跳空的时候用开盘价代替
            order_target(g.future, 0, side='long') # 数量用0的情况下将全部平仓
            g.MarketPosition = 0
    elif g.MarketPosition == -1:
        # 有空仓的情况
        log.info('ExitHighestPrice=', ExitHighestPrice)
        if High > ExitHighestPrice:
            # myExitPrice = Min(High,ExitHighestPrice)# + MinPoint)
            # myExitPrice = Open if myExitPrice < Open else myExitPrice # 大跳空的时候用开盘价代替
            order_target(g.future, 0, side='short') # 数量用0的情况下将全部平仓
            g.MarketPosition = 0

## 收盘后运行函数
def after_market_close(context):
    log.info('函数运行时间(after_market_close):', context.current_dt.time())
    # 得到当天所有成交记录
    trades = get_trades()
    for _trade in trades.values():
        log.info('成交记录：'+str(_trade))
    log.info('一天结束')
    log.info('##############################################################')
    

########################## 自定义函数 #################################
def set_params(context):
    g.RiskRatio = 10 # % Risk Per N ( 0 - 100)
    g.ATRLength = 6 # 平均波动周期 ATR Length
    g.boLength = 0 # 短周期 BreakOut Length
    g.teLength = 0 # 离市周期 Trailing Exit Length
    g.future_index = 'RB' # 合约
    g.MarketPosition = 0
    
# 求指数平均
def XAverage(Price, Length):
    alpha = 2 / (Length + 1)
    res = []
    for i in range(0, len(Price)):
        res.append(ema_calc(alpha, Price, i))
    return res
    
def ema_calc(alpha, price, t):
    if (t == 0):
        return price[t]
    else:
        return alpha*price[t] + (1-alpha) * ema_calc(alpha, price, t-1)
        
def TrueRange(price_list, T):
    return [max(price_list['high'].iloc[i]-price_list['low'].iloc[i], abs(price_list['high'].iloc[i]-price_list['close'].iloc[i-1]), abs(price_list['close'].iloc[i-1]-price_list['low'].iloc[i])) for i in range(1, T+1)]
    
def get_unit(cash, ATR, symbol, RiskRatio):
    # 各品种期货的交易单位（一手合约包含多少计量单位，如CU:5即铜合约交易单位为5吨/手）
    future_contract_size = {'A':10, 'AG':15, 'AL':5, 'AU':1000,
                        'B':10, 'BB':500, 'BU':10, 'C':10, 
                        'CF':5, 'CS':10, 'CU':5, 'ER':10, 
                        'FB':500, 'FG':20, 'FU':50, 'GN':10, 
                        'HC':10, 'I':100, 'IC':200, 'IF':300, 
                        'IH':300, 'J':100, 'JD':5, 'JM':60, 
                        'JR':20, 'L':5, 'LR':10, 'M':10, 
                        'MA':10, 'ME':10, 'NI':1, 'OI':10, 
                        'P':10, 'PB':5, 'PM':50, 'PP':5, 
                        'RB':10, 'RI':20, 'RM':10, 'RO':10, 
                        'RS':10, 'RU':10, 'SF':5, 'SM':5, 
                        'SN':1, 'SR':10, 'T':10000, 'TA':5, 
                        'TC':100, 'TF':10000, 'V':5, 'WH':20, 
                        'WR':10, 'WS':50, 'WT':10, 'Y':10, 
                        'ZC':100, 'ZN':5}
    TurtleUnits = (cash*RiskRatio) / (100.0 * ATR * future_contract_size[symbol])
    TurtleUnits = int(TurtleUnits) # 对小数取整
    print('TurtleUnits: ', TurtleUnits)
    return TurtleUnits
    
def HighestFC(Prices, Length):
    highest = Prices[-2]
    for i in range(-2, -Length-2):
        if highest < Prices[i]:
            highest = Prices
    return highest
    
def LowestFC(Prices, Length):
    lowest = Prices[-2]
    for i in range(-2, -Length-2):
        if lowest > Prices[i]:
            lowest = Prices
    return lowest

########################## 获取期货合约信息，请保留 #################################
# 获得当天时间正在交易的期货主力合约
def get_future_code(symbol):
    future_code_list = {'A':'A9999.XDCE', 'AG':'AG9999.XSGE', 'AL':'AL9999.XSGE', 'AU':'AU9999.XSGE',
                        'B':'B9999.XDCE', 'BB':'BB9999.XDCE', 'BU':'BU9999.XSGE', 'C':'C9999.XDCE', 
                        'CF':'CF9999.XZCE', 'CS':'CS9999.XDCE', 'CU':'CU9999.XSGE', 'ER':'ER9999.XZCE', 
                        'FB':'FB9999.XDCE', 'FG':'FG9999.XZCE', 'FU':'FU9999.XSGE', 'GN':'GN9999.XZCE', 
                        'HC':'HC9999.XSGE', 'I':'I9999.XDCE', 'IC':'IC9999.CCFX', 'IF':'IF9999.CCFX', 
                        'IH':'IH9999.CCFX', 'J':'J9999.XDCE', 'JD':'JD9999.XDCE', 'JM':'JM9999.XDCE', 
                        'JR':'JR9999.XZCE', 'L':'L9999.XDCE', 'LR':'LR9999.XZCE', 'M':'M9999.XDCE', 
                        'MA':'MA9999.XZCE', 'ME':'ME9999.XZCE', 'NI':'NI9999.XSGE', 'OI':'OI9999.XZCE', 
                        'P':'P9999.XDCE', 'PB':'PB9999.XSGE', 'PM':'PM9999.XZCE', 'PP':'PP9999.XDCE', 
                        'RB':'RB9999.XSGE', 'RI':'RI9999.XZCE', 'RM':'RM9999.XZCE', 'RO':'RO9999.XZCE', 
                        'RS':'RS9999.XZCE', 'RU':'RU9999.XSGE', 'SF':'SF9999.XZCE', 'SM':'SM9999.XZCE', 
                        'SN':'SN9999.XSGE', 'SR':'SR9999.XZCE', 'T':'T9999.CCFX', 'TA':'TA9999.XZCE', 
                        'TC':'TC9999.XZCE', 'TF':'TF9999.CCFX', 'V':'V9999.XDCE', 'WH':'WH9999.XZCE', 
                        'WR':'WR9999.XSGE', 'WS':'WS9999.XZCE', 'WT':'WT9999.XZCE', 'Y':'Y9999.XDCE', 
                        'ZC':'ZC9999.XZCE', 'ZN':'ZN9999.XSGE'}
    try:
        return future_code_list[symbol]
    except:
        return 'WARNING : 无此合约'


# 获取金融期货合约到期日
def get_CCFX_end_date(fature_code):
    # 获取金融期货合约到期日
    return get_security_info(fature_code).end_date