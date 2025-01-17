import numpy as np
import pandas as pd

from ata.exchange.baseexchange import BaseExchange
from ata.utils.log import log

class OfflineExchange(BaseExchange):
    def __init__(
        self,
        file_path,
        balance = 100000
        ):
        super().__init__()
        try:
            self.data = pd.read_csv(file_path)
            self.data = self.data.rename(columns={"baseVolume": "volume"})
        except Exception as e:
            print(f"Data file read error: {e}")
            quit()
        
        self.balance = {
                'KRW': {'free': balance, 'used': 0, 'total': balance},
                'BTC': {'free': 0, 'used': 0, 'total': 0}
            }
        
        self.ohlcv_per_1m = None
        self.ohlcv_per_15m = None
        self.end_condition = self.balance['KRW']['total'] * 0.9
        self.__order = {}
        self.__ohlcv_len = 30
        
        offset = 300
        assert offset <= len(self.data), f"error: not enough offline data ({offset} {len(self.data)})"
        self.idx = offset - 2
        self.update()
        
        self.__id_cnt = 0
    
    def init(self):
        return True
    
    def update(self) -> bool:
        self.idx += 1
        if len(self.data) <= self.idx:
            return False
        
        self.ohlcv_per_1m = self.data[max(self.idx + 1 - self.__ohlcv_len, 0):self.idx + 1].copy()
        self.ohlcv_per_15m = self.__to_per_minute(15)
        self.ohlcv_per_1h = self.__to_per_minute(60)
        
        if self.get_total_balance() < self.end_condition:
            return False
        
        return True
    
    def get_buying_candidates(self):
        return ['BTC']
    
    def create_buy_order(self, item, price, amount_item):
        krw = min(price * amount_item, self.balance['KRW']['free'])
        if krw > self.balance['KRW']['free']: 
            raise Exception(f'KRW 초과(request: {krw}, remained: {self.balance["KRW"]["free"]})')
        self.balance['BTC']['free'] += amount_item
        self.balance['BTC']['total'] += amount_item
        self.balance['KRW']['free'] -= krw
        self.balance['KRW']['total'] -= krw
        return self.__make_order(item, status='closed', side='bid', price=price, amount=amount_item, filled=amount_item)
    
    def create_buy_order_at_market_price(self, item, amount_krw):
        curr_price = self.get_current_price(item=item)
        return self.create_buy_order(item=item, price=curr_price,amount_item=amount_krw / curr_price)
    
    def create_sell_order(self, item, price, amount_item):
        amount_item = min(amount_item, self.balance[item]['free'])
        krw = price * amount_item
        if amount_item > self.balance[item]['free']:
            raise Exception(f'{item} 부족(request: {amount_item}, remained: {self.balance[item]["free"]})')
        self.balance['KRW']['free'] += krw
        self.balance['KRW']['total'] += krw
        self.balance['BTC']['free'] -= amount_item
        self.balance['BTC']['total'] -= amount_item
        return self.__make_order(item, status='closed', side='ask', price=price, amount=amount_item, filled=amount_item)
    
    def create_sell_order_at_market_price(self, item, amount_item):
        return self.create_sell_order(item=item, price=self.get_current_price(item=item), amount_item=amount_item)
    
    def get_ohlcv_per_1m(self, item):
        if item == 'KRW':
            return None
        return self.ohlcv_per_1m
    
    def get_ohlcv_per_15m(self, item):
        if item == 'KRW':
            return None
        return self.ohlcv_per_15m
    
    def get_ohlcv_per_1h(self, item):
        if item == 'KRW':
            return None
        return self.ohlcv_per_1h
    
    def get_total_balance(self):
        return self.balance['KRW']['total'] + self.balance['BTC']['total'] * self.get_current_price('BTC')
    
    def get_order(self, order_id):
        return self.__order[order_id]
    
    def cancel_order_by_id(self, order_id):
        pass
    
    def cancel_order_all(self):
        pass
    
    def __make_order(self, item, status, side, price, amount, filled):
        order_id = f'{self.__id_cnt}'
        self.__id_cnt += 1
        self.__order[order_id] = {'status': status, 'side': side, 'price': price, 'amount': amount, 'filled': filled, 'id': order_id}
        return order_id
    
    def __to_per_minute(self, minute):
        columns_to_resample = ['open', 'high', 'low', 'close', 'volume']
        temp_data = self.data[columns_to_resample].iloc[max(self.idx + 1 - (minute * self.__ohlcv_len), 0):self.idx + 1]
        group = temp_data.index // minute
        return (
            temp_data
            .groupby(group)
            .agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
        }).reset_index(drop=True)).copy()  # 그룹 컬럼 제거