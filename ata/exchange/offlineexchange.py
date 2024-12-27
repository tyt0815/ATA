import numpy as np
import pandas as pd

from ata.exchange.baseexchange import BaseExchange

class OfflineExchange(BaseExchange):
    def __init__(
        self,
        file_path,
        balance = 100000
        ):
        try:
            self.data = pd.read_csv(file_path)
            self.data = self.data.rename(columns={"baseVolume": "volume"})
        except Exception as e:
            print(f"Data file read error: {e}")
            quit()
        
        self.idx = -1
        self.krw = balance
        self.coin = 0
        self.buying_amount = 0
    
        for i in range(100):
            assert self.update(), f"error: not enough offline data {i}"
    
    def update(self) -> bool:
        self.idx += 1
        if len(self.data) <= self.idx:
            return False
        return True
    
    def buy(self, coin):
        self.buying_amount += self.krw
        curr_price = self.get_current_price(coin=coin)
        self.coin += self.krw / curr_price
        self.krw -= self.krw
        self._buy_log(coin)
        return self.buying_amount, curr_price
    
    def sell(self, coin):
        curr_price = self.get_current_price(coin=coin)
        selling_amount = self.coin * curr_price
        self.krw += selling_amount
        self.coin -= self.coin
        self._sell_log(coin=coin, difference=selling_amount - self.buying_amount)
        self.buying_amount = 0
        return selling_amount, curr_price
    
    def get_ohlcv(self, coin, length):
        return self.data[max(self.idx + 1 - length, 0):self.idx + 1]
    
    def get_current_price(self, coin):
        return self.data["close"].iloc[self.idx]
    
    def get_balance(self):
        return self.krw + self.coin * self.get_current_price(coin="")
    
    def calc_rvol(self, coin, window=10):
        ohlcv = self.get_ohlcv(coin=coin, length=window)
        rolling_mean = ohlcv['volume'].rolling(window=window).mean()

        # 현재 거래량(baseVolume)과 평균 거래량(rolling_mean) 비교
        rvol = ohlcv['volume'] / rolling_mean
        return rvol