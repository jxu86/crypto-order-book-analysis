
import config

class RiskControl(object):
    def __init__(self):
        self.stop_loss_rate = config.stop_loss_rate

    def calc_stop_loss_price(self, s_price, otype):
        if otype == 'buy':
            return s_price - s_price * self.stop_loss_rate
        elif otype == 'sell':
            return s_price + s_price * self.stop_loss_rate
