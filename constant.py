from enum import Enum


class OrderStatus(Enum):
    CANCELED = '-1'
    PENDING = '0'
    PARTIALLY_FILLED = '1'
    FULLY_FILLED = '2'
