import ccxt
import pandas as pd

from ata.exchange.baseexchange import BaseExchange

class UpbitExchange(BaseExchange):
    def __init__(self):
        super().__init__()
    
    def init(self):
        try:
            with open("./upbit.key") as f:
                lines = f.readlines()
                api_key = lines[0].strip()
                api_secret = lines[1].strip()

            self.exchange = ccxt.upbit(config={
                'apiKey': api_key,
                'secret': api_secret,
                'enableRateLimit': True
                }
            )
        except:
            return False
        
        self.ohlcvs_1m = {}
        self.ohlcvs_15m = {}
        
        return True
    
    def update(self) -> bool:
        self.ohlcvs_1m = {}
        self.ohlcvs_15m = {}
        self.balance = self.exchange.fetch_balance()
        
        return True
    
    def get_buying_candidates(self):
        # TODO
        return ['BTC', 'ETH']
    
    def create_buy_order(self, item, price, amount):
        resp = self.exchange.create_limit_buy_order(
            symbol=f'{item}/KRW',
            amount=amount,
            price=price
        )
        self._save_order_id(item=item,order_id=resp['id'])
        return resp
    
    def create_buy_order_at_market_price(self, item, amount):
        resp = self.exchange.create_market_buy_order(
            symbol=f'{item}/KRW',
            amount=amount
            )
        self._save_order_id(item=item,order_id=resp['id'])
        return resp
    
    def create_sell_order(self, item, price, amount):
        resp = self.exchange.create_limit_sell_order(
            symbol=f'{item}/KRW',
            amount=amount,
            price=price
        )
        self._save_order_id(item=item,order_id=resp['id'])
        return resp
    
    def create_sell_order_at_market_price(self, item, amount):
        resp = self.exchange.create_market_sell_order(
            symbol=f'{item}/KRW',
            amount=amount
            )
        self._save_order_id(item=item,order_id=resp['id'])
        return resp
    
    def get_ohlcv_per_1m(self, item):
        if not item in self.ohlcvs_1m:
            try:
                ohlcv = self.exchange.fetch_ohlcv(
                    symbol=f'{item}/KRW',
                    timeframe='1m'
                )
                self.ohlcvs_1m[item] = self.__preprocess_ohlcv(ohlcv)
            except:
                return None
        return self.ohlcvs_1m[item]
    
    def get_ohlcv_per_15m(self, item):
        if not item in self.ohlcvs_15m:
            try:
                ohlcv = self.exchange.fetch_ohlcv(
                    symbol=f'{item}/KRW',
                    timeframe='15m'
                )
                self.ohlcvs_15m[item] = self.__preprocess_ohlcv(ohlcv)
            except:
                return None
        return self.ohlcvs_15m[item]
    
    def get_total_balance(self):
        total = 0
        for item in self.balance['total']:
            if item == 'KRW':
                total += self.balance[item]['total']
            else:
                total += (self.balance[item]['total'] * self.get_current_price(item=item))
        return total

    def get_order(self, order_id):
        return self.exchange.fetch_order(
            id=order_id
        )
    
    def cancel_order_by_id(self, order_id):
        try:
            return self.exchange.cancel_order(
                id=order_id
            )
        except:
            return self.get_order(order_id=order_id)
    
    def cancel_order_by_item(self, item):
        for order_id in self.order_ids[item]:
            self.cancel_order_by_id(order_id=order_id)
        
    
    def cancel_order_all(self):
        for item in self.balance:
            self.cancel_order_by_item(item=item)
            
    def __preprocess_ohlcv(self, ohlcv):
        df = pd.DataFrame(ohlcv, columns=['datetime', 'open', 'high', 'low', 'close', 'volume'])
        pd_ts = pd.to_datetime(df['datetime'], utc=True, unit='ms')     # unix timestamp to pandas Timeestamp
        pd_ts = pd_ts.dt.tz_convert("Asia/Seoul")                       # convert timezone
        pd_ts = pd_ts.dt.tz_localize(None)
        df.set_index(pd_ts, inplace=True)
        df = df[['open', 'high', 'low', 'close', 'volume']]
        return df