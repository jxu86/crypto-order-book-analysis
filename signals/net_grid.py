#! /usr/bin/env python
# -*- coding: utf-8 -*-


class NetGridSignal(object):
    def __init__(self,
                 h_price,
                 l_price,
                 grid_num,
                 precision=3,
                 grid_scale=False):
        self.h_price = h_price
        self.l_price = l_price
        self.grid_num = grid_num
        # self.price_list = []
        self.precision = precision
        self.grid_scale = grid_scale

    def calc_price_interval(self):
        price_list = []
        if self.gird_scale:
            # TODO
            pass
        else:
            price_interval = (self.h_price - self.l_price) / self.grid_num
            for g in range(self.grid_num + 1):
                p = self.l_price + g * price_interval
                price_list.append(round(p, self.precision))
        return price_list

    def calc_position(self):
        pass

    def calc_loss(self, s_price, o_price):
        total_lost = 0
        for price in self.price_list:
            if price > s_price:
                lost = (o_price - price) / price
                total_lost += lost
        print('total_lost=>', total_lost)
