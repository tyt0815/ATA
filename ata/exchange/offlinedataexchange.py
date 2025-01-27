import pandas as pd

from ata.exchange.virtualexchange import VirtualExchange

class OfflineDataExchange(VirtualExchange):
    def __init__(
        self,
        file_path,
        balance = 100000
        ):
        super().__init__(balance=balance)
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
        
        self.__ohlcv_len = 20
        
        offset = 60 * self.__ohlcv_len # 60분 * self.__ohlcv_len
        assert offset <= len(self.data), f"error: not enough offline data ({offset} {len(self.data)})"
        self.idx = offset - 2
        
    def init(self):
        return super().init()
    
    def update(self) -> bool:
        self.idx += 1
        if len(self.data) <= self.idx:
            return False
        
        self.ohlcvs_1m = {'BTC/KRW':self.data.iloc[self.idx + 1 - self.__ohlcv_len:self.idx + 1].copy()}
        self.ohlcvs_15m = {'BTC/KRW':self.__to_per_minute(15)}
        self.ohlcvs_1h = {'BTC/KRW':self.__to_per_minute(60)}
        self.tickers = {'BTC/KRW': self.data.iloc[self.idx]}
        
        
        return super().update()
    
    def get_buying_candidates(self):
        return ['BTC']

    def get_ohlcv_per_1m(self, item):
        if item == 'KRW':
            return None
        return self.ohlcvs_1m[item+'/KRW']
    
    def get_ohlcv_per_15m(self, item):
        if item == 'KRW':
            return None
        return self.ohlcvs_15m[item+'/KRW']
    
    def get_ohlcv_per_1h(self, item):
        if item == 'KRW':
            return None
        return self.ohlcvs_1h[item+'/KRW']
    
    def get_time(self):
        return (self.idx + 1) * 60
    
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