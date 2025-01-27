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
        self.__open_order_id = []
        self.__ohlcv_len = 20
        
        offset = 60 * self.__ohlcv_len
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

        for order_id in self.__open_order_id:
            self.__process_order(order_id)
        
        if self.get_total_balance() < self.end_condition:
            return False
        
        return True
    
    def get_buying_candidates(self):
        return ['BTC']
    
    def create_buy_order(self, item, price, amount_item):
        krw = price * amount_item
        if krw > self.balance['KRW']['free']: 
            raise Exception(f'KRW 초과(request: {krw}, remained: {self.balance["KRW"]["free"]})')
        self.balance['KRW']['free'] -= krw
        self.balance['KRW']['used'] += krw
        order_id = self.__make_order(item, status='open', side='bid', price=price, amount=amount_item, filled=0)
        return order_id
    
    def create_buy_order_at_market_price(self, item, amount_krw):
        curr_price = self.get_current_price(item=item)
        return self.create_buy_order(item=item, price=curr_price,amount_item=amount_krw / curr_price)
    
    def create_sell_order(self, item, price, amount_item):
        if amount_item > self.balance[item]['free']:
            raise Exception(f'{item} 부족(request: {amount_item}, remained: {self.balance[item]["free"]})')
        self.balance['BTC']['free'] -= amount_item
        self.balance['BTC']['used'] += amount_item
        order_id = self.__make_order(item, status='open', side='ask', price=price, amount=amount_item, filled=0)
        return order_id
    
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
        if order_id in self.__open_order_id:
            self.__open_order_id.remove(order_id)
            order = self.get_order(order_id=order_id)
            if order['status'] == 'open':
                order['status'] = 'canceled'
                # 매수 
                if order['side'] == 'bid':
                    amount_krw = order['amount'] * order['price']
                    self.balance['KRW']['free'] += amount_krw
                    self.balance['KRW']['used'] -= amount_krw
                else:
                    self.balance['BTC']['free'] += order['amount']
                    self.balance['BTC']['used'] -= order['amount']
            
    
    def cancel_order_all(self):
        pass
    
    def __make_order(self, item, status, side, price, amount, filled):
        order_id = f'{self.__id_cnt}'
        self.__id_cnt += 1
        self.__order[order_id] = {'status': status, 'side': side, 'price': price, 'amount': amount, 'filled': filled, 'id': order_id}
        if status == 'open':
            self.__open_order_id.append(order_id)
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
        
    def __process_order(self, order_id):
        order = self.__order[order_id]
        if order['status'] == 'open':
            # 매수 주문
            if order['side'] == 'bid' and order['price'] >= self.get_current_price('BTC'):
                amount_krw = order['amount'] * order['price']
                self.balance['BTC']['free'] += order['amount']
                self.balance['BTC']['total'] += order['amount']
                self.balance['KRW']['total'] -= amount_krw
                self.balance['KRW']['used'] -= amount_krw
                order['filled'] = order['amount']
                order['status'] = 'closed'
                self.__open_order_id.remove(order_id)
            
            # 매도 주문    
            elif order['side'] == 'ask' and order['price'] <= self.get_current_price('BTC'):
                self.balance['KRW']['free'] += order['amount'] * order['price']
                self.balance['KRW']['total'] += order['amount'] * order['price']
                self.balance['BTC']['total'] -= order['amount']
                self.balance['BTC']['used'] -= order['amount']
                order['filled'] = order['amount']
                order['status'] = 'closed'
                self.__open_order_id.remove(order_id)
                
    def get_time(self):
        return (self.idx + 1) * 60
    
    def get_tickers(self):
        return {
            'BTC/KRW': self.data.iloc[self.idx]
            }