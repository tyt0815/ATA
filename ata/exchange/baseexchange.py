from abc import abstractmethod

class BaseExchange:
    def __init__(
        self,
        ):
        self.balance: dict = {}
    
    def create_sell_all_order(self, item, price):
        return self.create_sell_order(item=item, price=price, amount_item=self.balance[item]['free'])
    
    def create_sell_all_order_at_market_price(self, item):
        return self.create_sell_order_at_market_price(item=item,amount_item=self.balance[item]['free'])
    
    def get_current_price(self, item):
        ohlcv = self.get_ohlcv_per_1m(item)
        if ohlcv is None:
            return 0
        return ohlcv['close'].iloc[-1]
    
    def is_tradable(self, item):
        if self.get_ohlcv_per_1m(item) is None:
            return False
        return True
    
    @abstractmethod
    def init(self):
        pass
    
    @abstractmethod
    def update(self) -> bool:
        pass
    
    @abstractmethod
    def create_buy_order(self, item, price, amount_item):
        pass
    
    @abstractmethod
    def create_buy_order_at_market_price(self, item, amount_krw):
        pass
    
    @abstractmethod
    def create_sell_order(self, item, price, amount_item):
        pass
    
    @abstractmethod
    def create_sell_order_at_market_price(self, item, amount_item):
        pass
    
    @abstractmethod
    def get_ohlcv_per_1m(self, item):
        pass
    
    @abstractmethod
    def get_ohlcv_per_15m(self, item):
        pass
    
    @abstractmethod
    def get_ohlcv_per_1h(self, item):
        pass

    @abstractmethod
    def get_total_balance(self):
        pass
    
    @abstractmethod
    def get_order(self, order_id):
        pass
    
    @abstractmethod
    def cancel_order_by_id(self, order_id):
        pass
    
    @abstractmethod
    def get_time(self):
        pass
    
    @abstractmethod
    def get_tickers(self):
        pass
    
    @abstractmethod
    def get_market_events(self):
        pass