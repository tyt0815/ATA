import ccxt
import pandas as pd
import time

from ata.exchange.baseexchangesimulator import BaseExchangeSimulator
from ata.utils.log import log, save_log

class UpbitExchangeSimulator(BaseExchangeSimulator):
    def __init__(
        self,
        file_path,
        balance = 100000
        ):
        super().__init__(balance=balance)
        self.file_path = file_path
        self.exchange: ccxt.upbit = None
    
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
        self.update()
        log('done')       
        return super().init()
    
    def update(self):
        self.ohlcvs_1m = {}
        self.ohlcvs_15m = {}
        self.ohlcvs_1h = {}
        self.tickers = self.exchange.fetch_tickers()
        
        return super().update()

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
    
    def get_time(self):
        return time.time()
    
    def __preprocess_ohlcv(self, ohlcv):
        df = pd.DataFrame(ohlcv, columns=['datetime', 'open', 'high', 'low', 'close', 'volume'])
        pd_ts = pd.to_datetime(df['datetime'], utc=True, unit='ms')     # unix timestamp to pandas Timeestamp
        pd_ts = pd_ts.dt.tz_convert("Asia/Seoul")                       # convert timezone
        pd_ts = pd_ts.dt.tz_localize(None)
        df.set_index(pd_ts, inplace=True)
        df = df[['open', 'high', 'low', 'close', 'volume']]
        return df