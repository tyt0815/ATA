import numpy as np
import pandas as pd

def calc_ma(prices, period):
    return prices.rolling(window=period).mean()

def calc_ema(price, period):
    df = pd.DataFrame(price)
    return df.ewm(span=period, adjust=False).mean()

def calc_bollinger_bands(prices, window_size):
        # 이동평균 계산
        rolling_mean = calc_ma(prices, window_size)
        
        # 표준편차 계산
        rolling_std = prices.rolling(window=window_size).std()
        
        # 상단 밴드와 하단 밴드 계산
        upper_band = rolling_mean + (rolling_std * 2)
        lower_band = rolling_mean - (rolling_std * 2)
        
        # 볼린저 %b 계산
        bollinger_b = (prices - lower_band) / (upper_band - lower_band)
        
        # 결과를 데이터프레임으로 반환
        return pd.DataFrame({
            'moving_avg': rolling_mean,
            'upper_band': upper_band,
            'lower_band': lower_band,
            "b": bollinger_b
        })
    
def calc_mfi(ohlcv, period=14):
        # Typical Price 계산
    typical_price = (ohlcv['high'] + ohlcv['low'] + ohlcv['close']) / 3
    
    # Raw Money Flow 계산
    raw_money_flow = typical_price * ohlcv['volume']
    
    # Positive/Negative Money Flow 구분
    price_change = typical_price.diff()
    positive_money_flow = np.where(price_change > 0, raw_money_flow, 0)
    negative_money_flow = np.where(price_change < 0, raw_money_flow, 0)
    
    # Rolling sums for the given period
    positive_mf_sum = pd.Series(positive_money_flow).rolling(window=period).sum()
    negative_mf_sum = pd.Series(negative_money_flow).rolling(window=period).sum()
    
    # Money Flow Ratio and MFI 계산
    money_flow_ratio = positive_mf_sum / negative_mf_sum
    mfi = 100 - (100 / (1 + money_flow_ratio))
    
    return mfi

def calc_rvol(self, volumes, window=10):
    pd.DataFrame(volumes)
    rolling_mean = volumes.rolling(window=window).mean()

    # 현재 거래량(baseVolume)과 평균 거래량(rolling_mean) 비교
    rvol = volumes / rolling_mean
    return rvol

def calc_williams_r(ohlcv, period=10):
    # 최고가, 최저가, 종가 계산
    williams_r = ((ohlcv['high'].rolling(window=period).max() - ohlcv['close']) / 
                         (ohlcv['high'].rolling(window=period).max() - ohlcv['low'].rolling(window=period).min())) * -100
    return williams_r

def deviation_from_ma(price, ma):
    # 이동 평균 계산 (SMA 또는 EMA)
    # 이격도 계산
    return ((price - ma) / ma) * 100