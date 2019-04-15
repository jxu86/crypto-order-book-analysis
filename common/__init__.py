# -*- coding: utf-8 -*-

from dataclasses import dataclass
import datetime
import enum


redis_subscribe_msg = {
    'EOS-USDT': 'okex.order_book.EOS/USDT'
}

@dataclass
class StrategyParams:
    apikey: str
    secretkey: str
    passphrase: str
    high_price: float
    low_price: float
    grid_num: int
    order_size: float