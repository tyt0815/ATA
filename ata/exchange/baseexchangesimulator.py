from abc import abstractmethod

from ata.exchange.baseexchange import BaseExchange

class BaseExchangeSimulator(BaseExchange):
    def __init__(
        self,
        balance = 100000
        ):
        super().__init__()
        
        self.balance = {
                'KRW': {'free': balance, 'used': 0, 'total': balance}
            }
        
        self.__order = {}
        self.__open_order_id = []
        self.ohlcvs_1m: dict = {}
        self.ohlcvs_15m: dict = {}
        self.ohlcvs_1h: dict = {}
        self.__id_cnt = 0
    
    def init(self):
        self.update()
        return True
    
    def update(self) -> bool:
        for order_id in self.__open_order_id:
            self.__process_order(order_id)
        
        return True
    
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
        order_id = self.create_buy_order(item=item, price=curr_price,amount_item=amount_krw / curr_price)
        self.__process_order(order_id)
        return order_id
    
    def create_sell_order(self, item, price, amount_item):
        if amount_item > self.balance[item]['free']:
            raise Exception(f'{item} 부족(request: {amount_item}, remained: {self.balance[item]["free"]})')
        self.balance[item]['free'] -= amount_item
        self.balance[item]['used'] += amount_item
        order_id = self.__make_order(item, status='open', side='ask', price=price, amount=amount_item, filled=0)
        return order_id
    
    def create_sell_order_at_market_price(self, item, amount_item):
        order_id = self.create_sell_order(item=item, price=self.get_current_price(item=item), amount_item=amount_item)
        self.__process_order(order_id)
        return order_id
    
    def get_total_balance(self):
        total = 0
        for item in self.balance:
            if item == 'KRW':
                total += self.balance[item]['total']
            else:
                total += (self.balance[item]['total'] * self.get_current_price(item=item))
        return total
    
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
                    item = order['symbol'].split('/')[0]
                    self.balance[item]['free'] += order['amount']
                    self.balance[item]['used'] -= order['amount']
    
    
    def __make_order(self, item, status, side, price, amount, filled):
        order_id = f'{self.__id_cnt}'
        self.__id_cnt += 1
        self.__order[order_id] = {'status': status, 'side': side, 'price': price, 'amount': amount, 'filled': filled,
                                  'id': order_id, 'symbol': item+'/KRW'}
        if status == 'open':
            self.__open_order_id.append(order_id)
        return order_id
        
    def __process_order(self, order_id):
        order = self.__order[order_id]
        item = order['symbol'].split('/')[0]
        if item not in self.balance:
            self.balance[item] = {'free': 0, 'used': 0, 'total': 0}
        if order['status'] == 'open':
            # 매수 주문
            if order['side'] == 'bid' and order['price'] >= self.get_current_price(item):
                amount_krw = order['amount'] * order['price']
                self.balance[item]['free'] += order['amount']
                self.balance[item]['total'] += order['amount']
                self.balance['KRW']['total'] -= amount_krw
                self.balance['KRW']['used'] -= amount_krw
                order['filled'] = order['amount']
                order['status'] = 'closed'
                self.__open_order_id.remove(order_id)
            
            # 매도 주문    
            elif order['side'] == 'ask' and order['price'] <= self.get_current_price(item):
                self.balance['KRW']['free'] += order['amount'] * order['price']
                self.balance['KRW']['total'] += order['amount'] * order['price']
                self.balance[item]['total'] -= order['amount']
                self.balance[item]['used'] -= order['amount']
                order['filled'] = order['amount']
                order['status'] = 'closed'
                self.__open_order_id.remove(order_id)

    def get_tickers(self):
        return self.tickers
    
    @abstractmethod
    def get_ohlcv_per_1m(self, item):
        pass
    
    @abstractmethod
    def get_ohlcv_per_5m(self, item):
        pass
    
    @abstractmethod
    def get_ohlcv_per_15m(self, item):
        pass
    
    @abstractmethod
    def get_ohlcv_per_1h(self, item):
        pass
    
    @abstractmethod
    def get_time(self):
        pass
    
    @abstractmethod
    def get_market_events(self):
        pass
    