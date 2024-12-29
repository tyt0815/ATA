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
        
        self.krw = balance
        self.coin = 0
        self.buying_amount = 0
        self.ohlcv_per_1m = None
        self.ohlcv_per_15m = None
    
        offset = 300
        assert offset <= len(self.data), f"error: not enough offline data ({offset} {len(self.data)})"
        self.idx = offset - 2
        self.update()
    
    def update(self) -> bool:
        self.idx += 1
        if len(self.data) <= self.idx:
            return False
        
        self.ohlcv_per_1m = self.data[max(self.idx + 1 - 20, 0):self.idx + 1].copy()
        columns_to_resample = ['open', 'high', 'low', 'close', 'volume']
        
        temp_data = self.data[columns_to_resample].iloc[max(self.idx + 1 - 300, 0):self.idx + 1]
        group = temp_data.index // 15
        self.ohlcv_per_15m = (
            temp_data
            .groupby(group)
            .agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
        }).reset_index(drop=True)).copy()  # 그룹 컬럼 제거
        
        return True
    
    def buy(self, coin, amount_krw):
        amount_krw = min(amount_krw, self.krw)
        self.buying_amount += amount_krw
        curr_price = self.get_current_price(coin=coin)
        self.coin += amount_krw / curr_price
        self.krw -= amount_krw
        self._buy_log(coin)
        return amount_krw, curr_price
    
    def sell(self, coin, amount_krw):
        curr_price = self.get_current_price(coin=coin)
        amount_krw = min(amount_krw, self.coin * curr_price)
        amount_coin = amount_krw / curr_price
        self.krw += amount_krw
        self.coin -= amount_coin
        self._sell_log(coin=coin, difference=amount_krw - self.buying_amount)
        self.buying_amount = 0
        return amount_krw, curr_price
    
    def get_ohlcv_per_1m(self, coin):
        return self.ohlcv_per_1m
    
    def get_ohlcv_per_15m(self, coin):
        return self.ohlcv_per_15m
    
    def get_current_price(self, coin):
        return self.data["close"].iloc[self.idx]
    
    def get_balance(self):
        return self.krw + self.coin * self.get_current_price(coin="")