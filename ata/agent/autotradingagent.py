from datetime import datetime
from itertools import count
import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd
import sys

from ata.exchange.baseexchange import BaseExchange

class AutoTradingAgent:
    def __init__(
        self,
        exchange:BaseExchange,
        targets: list=["BTC", "ETH", "DOGE"],
        window_size=20,
        end_condition=0.3,
        danger=2
        ):
        
        self.exchange = exchange
        self.window_size = window_size
        self.targets = targets
        self.danger = danger
        
        self.end_condition = self.exchange.get_balance() * (1 - end_condition)
        
    def run(self):
        file_path = os.path.abspath(sys.argv[0])
        file_path = os.path.join(os.path.dirname(file_path), "figures")
        file_path = os.path.join(file_path, datetime.now().strftime("%Y-%m-%d-%H-%M-%S"))
        os.makedirs(file_path, exist_ok=True)
        
        self.prev_price_history = []
        self.prev_moving_avg_history = []
        self.prev_upper_band_history = []
        self.prev_lower_band_history = []
        prev_buy_index = 0
        prev_sell_index = 0
        prev_buy_price = 0
        prev_sell_price = 0
        
        for t in count():
            current_target = None
            plt.figure(figsize=(25, 6))
            
            self.price_history = []
            self.moving_avg_history = []
            self.upper_band_history = []
            self.lower_band_history = []
            
            b_buy = False
            # 매수 루프
            while True:
                if self.exchange.update() == False:
                    return
                for coin in self.targets:
                    if self._is_buy_timing(coin=coin):
                        _, buy_price = self.exchange.buy(coin=coin)
                        buy_index = len(self.price_history) - 1
                        b_buy = True
                        current_target = coin
                        break
                
                if b_buy:
                    break
            
            # 매도 루프
            while True:
                if self.exchange.update() == False:
                    return
                if self._is_sell_timing(coin=current_target):
                    _, sell_price = self.exchange.sell(coin=current_target)
                    sell_index = len(self.price_history) - 1
                    break
            if t > 0:
                offset = 500
                start = max(prev_buy_index - offset, 0)
                end = min(prev_sell_index + offset, len(self.prev_price_history))
                
                self.prev_price_history = self.prev_price_history[start:end]
                self.prev_moving_avg_history = self.prev_moving_avg_history[start:end]
                self.prev_upper_band_history = self.prev_upper_band_history[start:end]
                self.prev_lower_band_history = self.prev_lower_band_history[start:end]
                prev_buy_index -= start
                prev_sell_index -= start
                
                plt.plot(self.prev_price_history, label="price", color="blue", alpha=0.5)
                plt.plot(self.prev_moving_avg_history, label='Moving Average', color='green', linestyle='--')
                plt.plot(self.prev_upper_band_history, label='Upper Band', color='red', linestyle='--')
                plt.plot(self.prev_lower_band_history,  label='Lower Band', color='red', linestyle='--')
                
                plt.fill_between(
                    [i for i in range(end - start)],
                    self.prev_upper_band_history,
                    self.prev_lower_band_history,
                    color='gray',
                    alpha=0.1,
                    label='Bollinger Band'
                )
                
                plt.scatter(prev_buy_index, prev_buy_price, color='red', marker='o', s=100, label='Buy Point')
                plt.scatter(prev_sell_index, prev_sell_price, color='black', marker='o', s=100, label='Sell Point')
                
                plt.xlabel('Time')
                plt.ylabel('Price')
                plt.legend()
                plt.grid()
                plt.savefig(os.path.join(file_path, f"{t}.png"))
            
            self.prev_price_history = self.price_history
            self.prev_moving_avg_history = self.moving_avg_history
            self.prev_upper_band_history = self.upper_band_history
            self.prev_lower_band_history = self.lower_band_history
            prev_buy_index = buy_index
            prev_sell_index = sell_index
            prev_buy_price = buy_price
            prev_sell_price = sell_price
            
        
    def _is_buy_timing(self, coin):
    
        ohlcv = self.exchange.get_ohlcv(coin=coin, length=self.window_size)
        bollinger_band = self.calc_bollinger_bands(prices=ohlcv["close"])
        
        self.prev_price_history.append(ohlcv["close"].iloc[-1])
        self.prev_moving_avg_history.append(bollinger_band["moving_avg"].iloc[-1])
        self.prev_upper_band_history.append(bollinger_band["upper_band"].iloc[-1])
        self.prev_lower_band_history.append(bollinger_band["lower_band"].iloc[-1])
        
        self.price_history.append(ohlcv["close"].iloc[-1])
        self.moving_avg_history.append(bollinger_band["moving_avg"].iloc[-1])
        self.upper_band_history.append(bollinger_band["upper_band"].iloc[-1])
        self.lower_band_history.append(bollinger_band["lower_band"].iloc[-1])
        
        if bollinger_band["lower_band"].iloc[-1] < ohlcv["close"].iloc[-1]:
            return False
        if bollinger_band["b"].iloc[-1] > 0:
            return False
        
        rvol = self.exchange.calc_rvol(coin=coin)
        if self.danger > 1 or (self.danger == 0 and rvol.iloc[-1] < 1):
            return True
        
        mfi = self.calc_mfi(ohlcv=ohlcv)
        if mfi.iloc[-1] > 20:
            return False
        
        return True
    
    def _is_sell_timing(self, coin):
        ohlcv = self.exchange.get_ohlcv(coin=coin, length=self.window_size)
        bollinger_band = self.calc_bollinger_bands(prices=ohlcv["close"])
        
        self.price_history.append(ohlcv["close"].iloc[-1])
        self.moving_avg_history.append(bollinger_band["moving_avg"].iloc[-1])
        self.upper_band_history.append(bollinger_band["upper_band"].iloc[-1])
        self.lower_band_history.append(bollinger_band["lower_band"].iloc[-1])
        
        if bollinger_band["upper_band"].iloc[-1] > ohlcv["close"].iloc[-1]:
            return False
        if bollinger_band["b"].iloc[-1] < 1:
            return False
        
        rvol = self.exchange.calc_rvol(coin=coin)
        if self.danger < 3 or (self.danger == 0 and rvol.iloc[-1] < 1):
            return True
        
        mfi = self.calc_mfi(ohlcv=ohlcv)
        if mfi.iloc[-1] < 80:
            return False
        
        return True
    
    def calc_bollinger_bands(self, prices):
        # 이동평균 계산
        rolling_mean = prices.rolling(window=self.window_size).mean()
        
        # 표준편차 계산
        rolling_std = prices.rolling(window=self.window_size).std()
        
        # 상단 밴드와 하단 밴드 계산
        upper_band = rolling_mean + (rolling_std * 2)
        lower_band = rolling_mean - (rolling_std * 2)
        
        # 볼린저 %b 계산
        bollinger_b = (prices - lower_band) / (upper_band - lower_band)
        
        # 결과를 데이터프레임으로 반환
        return pd.DataFrame({
            'moving_avg': rolling_mean,
            'upper_band': upper_band,
            'lower_band': lower_band,
            "b": bollinger_b
        })
    
    def calc_mfi(self, ohlcv, period=14):
         # Typical Price 계산
        typical_price = (ohlcv['high'] + ohlcv['low'] + ohlcv['close']) / 3
        
        # Raw Money Flow 계산
        raw_money_flow = typical_price * ohlcv['volume']
        
        # Positive/Negative Money Flow 구분
        price_change = typical_price.diff()
        positive_money_flow = np.where(price_change > 0, raw_money_flow, 0)
        negative_money_flow = np.where(price_change < 0, raw_money_flow, 0)
        
        # Rolling sums for the given period
        positive_mf_sum = pd.Series(positive_money_flow).rolling(window=period).sum()
        negative_mf_sum = pd.Series(negative_money_flow).rolling(window=period).sum()
        
        # Money Flow Ratio and MFI 계산
        money_flow_ratio = positive_mf_sum / negative_mf_sum
        mfi = 100 - (100 / (1 + money_flow_ratio))
        
        return mfi