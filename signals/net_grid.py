# import talib
import numpy as np


# class NetGridSignal(object):
#     def __init__(self):
#         self.weight = [0.1, 0.1, 0.1, 0.1, 0.0, 0.1, 0.1, 0.1, 0.1, 0.1]

#     def signal(self, price_list):
#         sig = 'no'
#         std = 0.015#np.std(price_list)
#         mean = np.mean(price_list)
#         band = mean + np.array([-5, -4, -3, -2, -1, 0, 1, 2, 3, 4, 5]) * std
#         # print('std=>', std)
#         return band, self.weight, mean

class NetGridSignal(object):
    def __init__(self, h_price, l_price, grid_num, precision=3):
        self.h_price = h_price
        self.l_price = l_price
        self.grid_num = grid_num
        self.price_list = []
        self.precision = precision
        
    def calc_price_interval(self):
        price_list = []
        price_interval = (self.h_price-self.l_price)/self.grid_num
        
        for g in range(self.grid_num+1):
            p = self.l_price + g * price_interval
            self.price_list.append(round(p, self.precision))
            
        print(self.price_list)
        return self.price_list

    def calc_position(self):
        pass
        
    def calc_loss(self, s_price, o_price):
        total_lost = 0
        for price in self.price_list:
            if price > s_price:
                lost = (o_price - price) / price
                total_lost += lost
                
        print('total_lost=>', total_lost)
