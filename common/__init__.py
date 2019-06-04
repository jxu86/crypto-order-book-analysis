# -*- coding: utf-8 -*-

from dataclasses import dataclass
import datetime
import enum


redis_subscribe_msg = {
    'EOS-USDT': 'okex.order_book.EOS/USDT',
    'ETH-USDT': 'okex.order_book.ETH/USDT',
    'ATOM-USDT': 'okex.order_book.ATOM/USDT',
    'XRP-USDT':'okex.order_book.XRP/USDT',
    'EOS-ETH': 'okex.order_book.ETH/USDT'
}

@dataclass
class StrategyParams:
    apikey: str
    secretkey: str
    passphrase: str
    name: str
    high_price: float
    low_price: float
    grid_num: int
    order_size: float
    pair: str