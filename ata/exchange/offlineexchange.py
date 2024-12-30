import numpy as np
import pandas as pd

from ata.exchange.baseexchange import BaseExchange

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
        self.__id_cnt = 0
        self.__order = {}
        
        offset = 300
        assert offset <= len(self.data), f"error: not enough offline data ({offset} {len(self.data)})"
        self.idx = offset - 2
        self.update()
    
    def init(self):
        return True
    
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
        
        if self.get_total_balance() < self.end_condition:
            return False
        
        return True
    
    def get_buying_candidates(self):
        return ['BTC']
    
    def create_buy_order(self, item, price, amount):
        krw = price * amount
        if krw > self.balance['KRW']['free']: 
            raise Exception(f'금액 초과(request: {krw}, remained: {self.balance["KRW"]["free"]})')
        self.balance['BTC']['free'] += amount
        self.balance['BTC']['total'] += amount
        self.balance['KRW']['free'] -= krw
        self.balance['KRW']['total'] -= krw
        return self.__make_order(item, status='closed', side='bid', price=price, amount=amount, filled=amount)
    
    def create_buy_order_at_market_price(self, item, amount):
        return self.create_buy_order(item, item, self.get_current_price(item=item), amount)
    
    def create_sell_order(self, item, price, amount):
        krw = price * amount
        if amount > self.balance[item]['free']:
            raise Exception(f'{item} 부족(request: {amount}, remained: {self.balance[item]["free"]})')
        self.balance['KRW']['free'] += krw
        self.balance['KRW']['total'] += krw
        self.balance['BTC']['free'] -= amount
        self.balance['BTC']['total'] -= amount
        return self.__make_order(item, status='closed', side='ask', price=price, amount=amount, filled=amount)
    
    def create_sell_order_at_market_price(self, item, amount):
        return self.create_sell_order(item=item, price=self.get_current_price(item=item), amount=amount)
    
    def get_ohlcv_per_1m(self, item):
        if item == 'KRW':
            return None
        return self.ohlcv_per_1m
    
    def get_ohlcv_per_15m(self, item):
        if item == 'KRW':
            return None
        return self.ohlcv_per_15m
    
    def get_total_balance(self):
        return self.balance['KRW']['total'] + self.balance['BTC']['total'] * self.get_current_price('BTC')
    
    def get_order(self, order_id):
        return self.__order[order_id]
    
    def cancel_order_by_id(self, order_id):
        pass
    
    def cancel_order_by_item(self, item):
        pass
    
    def cancel_order_all(self):
        pass
    
    def __make_order(self, item, status, side, price, amount, filled):
        order_id = f'{self.__id_cnt}'
        self.__id_cnt += 1
        self._save_order_id(item=item, order_id=order_id)
        self.__order[order_id] = {'status': status, 'side': side, 'price': price, 'amount': amount, 'filled': filled}
        return order_id