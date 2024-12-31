from abc import abstractmethod

class BaseExchange:
    def __init__(
        self,
        ):
        self.balance: dict = {}
        self.order_ids: dict = {}
    
    def create_sell_all_order(self, item):
        return self.sell(item, self.get_total_balance())
    
    def create_sell_all_order_at_market_price(self, item):
        return self.sell_at_market_price(item, self.get_total_balance())
    
    def get_current_price(self, item):
        ohlcv = self.get_ohlcv_per_1m(item)
        if ohlcv is None:
            return 0
        return ohlcv['close'].iloc[-1]
    
    def _save_order_id(self, item, order_id):
        if not item in self.order_ids:
            self.order_ids[item] = []
        self.order_ids[item].append(order_id)
        
    def remove_order_id(self, item, order_id):
        self.order_ids[item].remove(order_id)
    
    @abstractmethod
    def init(self):
        pass
    
    @abstractmethod
    def update(self) -> bool:
        pass
    
    @abstractmethod
    def get_buying_candidates(self):
        pass
    
    @abstractmethod
    def create_buy_order(self, item, price, amount):
        pass
    
    @abstractmethod
    def create_buy_order_at_market_price(self, item, amount):
        pass
    
    @abstractmethod
    def create_sell_order(self, item, price, amount):
        pass
    
    @abstractmethod
    def create_sell_order_at_market_price(self, item, amount):
        pass
    
    @abstractmethod
    def get_ohlcv_per_1m(self, item):
        pass
    
    @abstractmethod
    def get_ohlcv_per_15m(self, item):
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
    def cancel_order_by_item(self, item):
        pass
    
    @abstractmethod
    def cancel_order_all(self):
        pass