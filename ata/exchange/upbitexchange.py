import ccxt
import time
import pandas as pd
import requests

from ata.exchange.baseexchange import BaseExchange
from ata.utils.log import log

class UpbitExchange(BaseExchange):
    def __init__(
        self,
        end_condition,
        file_path
        ):
        super().__init__()
        self.end_condition = end_condition
        self.end_value = None
        self.file_path = file_path
    
    def init(self):
        log('init upbit exchange...')
        while True:
            try:
                with open(self.file_path) as f:
                    lines = f.readlines()
                    api_key = lines[0].strip()
                    api_secret = lines[1].strip()

                self.exchange = ccxt.upbit(config={
                    'apiKey': api_key,
                    'secret': api_secret,
                    'enableRateLimit': True
                    }
                )
                self.exchange.options['createMarketBuyOrderRequiresPrice'] = False
                break
            except:
                log('login fail')
        if self.end_value is None:
            if self.end_condition >= 1.0:
                self.end_value = self.end_condition
            else:
                self.end_value = 0
        self.update()
        log('done')
        return True
    
    def update(self) -> bool:
        self.ohlcvs_1m = {}
        self.ohlcvs_5m = {}
        self.ohlcvs_15m = {}
        self.ohlcvs_1h = {}
        self.market_events = self.__get_market_events()
        self.balance = self.exchange.fetch_balance()
        self.tickers = self.exchange.fetch_tickers()
        if self.end_condition < 1.0 and self.end_value < self.get_total_balance() * self.end_condition:
            self.end_value = self.get_total_balance() * self.end_condition
        if self.get_total_balance() < self.end_value:
            return False
        
        return True
    
    def create_buy_order(self, item, price, amount_item):
        resp = self.exchange.create_limit_buy_order(
            symbol=f'{item}/KRW',
            amount=amount_item,
            price=price
        )
        self.balance = self.exchange.fetch_balance()
        return resp['id']
    
    def create_buy_order_at_market_price(self, item, amount_krw):
        resp = self.exchange.create_market_buy_order(
            symbol=f'{item}/KRW',
            amount=amount_krw
            )
        self.balance = self.exchange.fetch_balance()
        return resp['id']
    
    def create_sell_order(self, item, price, amount_item):
        resp = self.exchange.create_limit_sell_order(
            symbol=f'{item}/KRW',
            amount=amount_item,
            price=price
        )
        self.balance = self.exchange.fetch_balance()
        return resp['id']
    
    def create_sell_order_at_market_price(self, item, amount_item):
        resp = self.exchange.create_market_sell_order(
            symbol=f'{item}/KRW',
            amount=amount_item
            )
        self.balance = self.exchange.fetch_balance()
        return resp['id']
    
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
    
    def get_ohlcv_per_5m(self, item):
        if not item in self.ohlcvs_5m:
            try:
                ohlcv = self.exchange.fetch_ohlcv(
                    symbol=f'{item}/KRW',
                    timeframe='5m'
                )
                self.ohlcvs_5m[item] = self.__preprocess_ohlcv(ohlcv)
            except:
                return None
        return self.ohlcvs_5m[item]
    
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
    
    def get_ohlcv_per_1h(self, item):
        if not item in self.ohlcvs_1h:
            try:
                ohlcv = self.exchange.fetch_ohlcv(
                    symbol=f'{item}/KRW',
                    timeframe='1h'
                )
                self.ohlcvs_1h[item] = self.__preprocess_ohlcv(ohlcv)
            except:
                return None
        return self.ohlcvs_1h[item]
    
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
            
    def __preprocess_ohlcv(self, ohlcv):
        df = pd.DataFrame(ohlcv, columns=['datetime', 'open', 'high', 'low', 'close', 'volume'])
        pd_ts = pd.to_datetime(df['datetime'], utc=True, unit='ms')     # unix timestamp to pandas Timeestamp
        pd_ts = pd_ts.dt.tz_convert("Asia/Seoul")                       # convert timezone
        pd_ts = pd_ts.dt.tz_localize(None)
        df.set_index(pd_ts, inplace=True)
        df = df[['open', 'high', 'low', 'close', 'volume']]
        return df
    
    def get_time(self):
        return time.time()
    
    def get_tickers(self):
        return self.tickers
    
    def __get_market_events(self) -> dict:
        url = "https://api.upbit.com/v1/market/all?is_details=true"
        headers = {"accept": "application/json"}
        res = requests.get(url, headers=headers)
        infos = res.json()
        result = {}
        for info in infos:
            data = {
                'warning': info['market_event']['warning'],
                'caution':
                {
                    'CONCENTRATION_OF_SMALL_ACCOUNTS': info['market_event']['caution']['CONCENTRATION_OF_SMALL_ACCOUNTS'],
                    'DEPOSIT_AMOUNT_SOARING': info['market_event']['caution']['DEPOSIT_AMOUNT_SOARING'],
                    'GLOBAL_PRICE_DIFFERENCES': info['market_event']['caution']['GLOBAL_PRICE_DIFFERENCES'],
                    'PRICE_FLUCTUATIONS': info['market_event']['caution']['PRICE_FLUCTUATIONS'],
                    'TRADING_VOLUME_SOARING': info['market_event']['caution']['TRADING_VOLUME_SOARING']
                },
            }
            
            result[info['market'].split('-')[-1]] = data
        return result
    
    def get_market_events(self):
        return self.market_events
    
    def get_order_book(self, item):
        return self.exchange.fetch_order_book(symbol=f'{item}/KRW')