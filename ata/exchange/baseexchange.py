from abc import abstractmethod

class BaseExchange:
    def __init__(
        self,
        ):
        pass
    
    def _buy_log(self, coin):
        print(f"Buy  {coin} at {self.get_current_price(coin=coin):<12}, Balance {self.get_balance():<12}")
        
    def _sell_log(self, coin, difference):
        print(f"Sell {coin} at {self.get_current_price(coin=coin):<12}, Balance {self.get_balance():<12}({difference})")
    
    @abstractmethod
    def update(self) -> bool:
        pass
    
    @abstractmethod
    def buy(self, coin):
        pass
    
    @abstractmethod
    def sell(self, coin):
        pass
    
    @abstractmethod
    def get_ohlcv(self, coin, length):
        pass
    
    @abstractmethod
    def get_current_price(self, coin):
        pass
    
    @abstractmethod
    def get_balance(self):
        pass
    @abstractmethod
    def calc_rvol(self, coin):
        pass