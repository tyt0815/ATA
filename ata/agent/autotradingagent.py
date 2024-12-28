from datetime import datetime
from itertools import count
import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd
import sys

from ata.algorithm import trading
from ata.exchange.baseexchange import BaseExchange

class AutoTradingAgent:
    def __init__(
        self,
        exchange:BaseExchange,
        targets: list=["BTC", "ETH", "DOGE"],
        end_condition=0.3
        ):
        
        self.exchange = exchange
        self.targets = targets
        
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
                
            # 시각화
            if t > 0:
                offset = 200
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
        ohlcv_per_1m = self.exchange.get_ohlcv_per_1m(coin=coin)
        
        bollinger_band_per_1m = trading.calc_bollinger_bands(prices=ohlcv_per_1m["close"], window_size=20)
        
        # 차트
        self.prev_price_history.append(ohlcv_per_1m["close"].iloc[-1])
        self.prev_moving_avg_history.append(bollinger_band_per_1m["moving_avg"].iloc[-1])
        self.prev_upper_band_history.append(bollinger_band_per_1m["upper_band"].iloc[-1])
        self.prev_lower_band_history.append(bollinger_band_per_1m["lower_band"].iloc[-1])
        
        self.price_history.append(ohlcv_per_1m["close"].iloc[-1])
        self.moving_avg_history.append(bollinger_band_per_1m["moving_avg"].iloc[-1])
        self.upper_band_history.append(bollinger_band_per_1m["upper_band"].iloc[-1])
        self.lower_band_history.append(bollinger_band_per_1m["lower_band"].iloc[-1])
        
        # 가격이 볼린저 밴드 하단을 터이하였는가
        if bollinger_band_per_1m["lower_band"].iloc[-1] < ohlcv_per_1m["close"].iloc[-1]:
            return False
        
        # 볼린저 %b가 0이하인가
        if bollinger_band_per_1m["b"].iloc[-1] > 0:
            return False
        
        # mfi가 20이하인가
        mfi_per_1m = trading.calc_mfi(ohlcv=ohlcv_per_1m)
        if mfi_per_1m.iloc[-1] > 20:
            return False
        
        return True
    
    def _is_sell_timing(self, coin):
        ohlcv_per_1m = self.exchange.get_ohlcv_per_1m(coin=coin)
        bollinger_band_per_1m = trading.calc_bollinger_bands(prices=ohlcv_per_1m["close"],window_size=20)
        
        self.price_history.append(ohlcv_per_1m["close"].iloc[-1])
        self.moving_avg_history.append(bollinger_band_per_1m["moving_avg"].iloc[-1])
        self.upper_band_history.append(bollinger_band_per_1m["upper_band"].iloc[-1])
        self.lower_band_history.append(bollinger_band_per_1m["lower_band"].iloc[-1])
        
        if bollinger_band_per_1m["upper_band"].iloc[-1] > ohlcv_per_1m["close"].iloc[-1]:
            return False
        if bollinger_band_per_1m["b"].iloc[-1] < 1:
            return False
        
        mfi_per_1m = trading.calc_mfi(ohlcv=ohlcv_per_1m)
        if mfi_per_1m.iloc[-1] < 80:
            return False
        
        return True