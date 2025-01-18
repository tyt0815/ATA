import numpy as np
import pandas as pd

def calc_sma(df, period, force_calc = False):
    '''
    df: "close"를 가지고 있어야 함
    return: f"sma{period}" 컬럼을 포함한 df
    '''
    sma_key = f"sma{period}"
    if not (sma_key in df.columns and not force_calc):
        df[sma_key] = df["close"].rolling(window=period).mean()
    return df, sma_key

def calc_ema(df, period, force_calc = False):
    '''
    df: "clsoe"를 가지고 있어야 함
    return: f"ema{period}" 컬럼을 포함한 df
    '''
    ema_key = f"ema{period}"
    if not (ema_key in df.columns and not force_calc):
        df[ema_key] = df["close"].ewm(span=period, adjust=False).mean()
    return df, ema_key

def calc_std(df, period, force_calc = False):
    '''
    df: "close"를 가지고 있어야 함
    return: f"std{period}" 컬럼을 포함한 df
    '''
    std_key = f"std{period}"
    if not (std_key in df.columns and not force_calc):
        df[f"std{period}"] = df["close"].rolling(window=period).std()
    return df, std_key

def calc_bollinger_bands(df, period, num_std_dev, force_calc = False):
    '''
    df: "close"를 가지고 있어야 함.
    return: f"upper_band{period}_{num_std_dev}", f"lower_band{period}_{num_std_dev}", f"bollinger_b{period}_{num_std_dev}",
        컬럼을 포함한 df
    '''
    upper_key = f"upper_band{period}_{num_std_dev}"
    lower_key = f"lower_band{period}_{num_std_dev}"
    b_key = f"bollinger_b{period}_{num_std_dev}"
    columns_to_check = [upper_key, lower_key, b_key]
    
    if not (all(col in df.columns for col in columns_to_check) and not force_calc):
        df, sma_key = calc_sma(df, period)
        df, std_key = calc_std(df, period)
        
        # 상단 밴드와 하단 밴드 계산
        df[upper_key] = df[sma_key] + (df[std_key] * num_std_dev)
        df[lower_key] = df[sma_key] - (df[std_key] * num_std_dev)
        
        # 볼린저 %b 계산
        
        df[b_key] = (
            (df["close"] - df[lower_key]) / 
            (df[upper_key] - df[lower_key])
            )
    
    # 결과를 데이터프레임으로 반환
    return df, {
        'upper_key' : upper_key,
        'lower_key' : lower_key,
        'b_key': b_key
    }

    
def calc_mfi(df, period=14, force_calc = False):
    '''
    df: 'high', 'low', 'close', 'volume' 가지고 있어야 함.
    return: f"mfi{period}" 컬럼을 포함한 df
    '''
    mfi_key = f"mfi{period}"
    if not (mfi_key in df.columns and not force_calc):
        # Typical Price 계산
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        
        # Raw Money Flow 계산
        raw_money_flow = typical_price * df['volume']
        
        # Positive/Negative Money Flow 구분
        price_change = typical_price.diff()
        positive_money_flow = np.where(price_change > 0, raw_money_flow, 0)
        negative_money_flow = np.where(price_change < 0, raw_money_flow, 0)
        
        # Rolling sums for the given period
        positive_mf_sum = pd.Series(positive_money_flow).rolling(window=period).sum()
        negative_mf_sum = pd.Series(negative_money_flow).rolling(window=period).sum()
        
        # Money Flow Ratio and MFI 계산
        money_flow_ratio = positive_mf_sum / negative_mf_sum
        df[mfi_key] = 100 - (100 / (1 + money_flow_ratio))
    
    return df, mfi_key

def calc_rvol(self, df, period=10, force_calc = False):
    '''
    df: 'volume' 가지고 있어야 함.
    return: f'rvol{period}' 컬럼을 포함한 df
    '''
    rvol_key = f'rvol{period}'
    if not (rvol_key in df.columns and not force_calc):
        rolling_mean = df['volume'].rolling(window=period).mean()

        # 현재 거래량(baseVolume)과 평균 거래량(rolling_mean) 비교
        df[rvol_key] = df['volume'] / rolling_mean
    return df, rvol_key

def calc_williams_r(df, period=10, force_calc = False):
    '''
    df: 'high', 'low', 'close' 가지고 있어야 함.
    return: f'williams_r{period}' 컬럼을 포함한 df
    '''
    williams_key = f'williams_r{period}'
    if not (williams_key in df.columns and not force_calc):
        # 최고가, 최저가, 종가 계산
        df[f'williams_r{period}'] = ((df['high'].rolling(window=period).max() - df['close']) / 
                            (df['high'].rolling(window=period).max() - df['low'].rolling(window=period).min())) * -100
    return df, williams_key

def calc_deviation_from_sma(df, period=20, force_calc = False):
    '''
    df: 'close' 가지고 있어야 함.
    return: f'deviation_sma{period}' 컬럼을 포함한 df
    '''
    deviation_sma_key = f'deviation_sma{period}'
    if not (deviation_sma_key in df.columns and not force_calc):
        # 이동 평균 계산 (SMA)
        df, sma_key = calc_sma(df, period)
        # 이격도 계산
        df[deviation_sma_key] = ((df['close'] - df[sma_key]) / df[sma_key]) * 100
    return df, deviation_sma_key

def check_oversold_by_bollinger_mfi(ohlcv_per_1m, bollinger_period = 20, bollinger_num_std_dev = 2, mfi_peirod = 14):
    # 볼린저
    ohlcv_per_1m, keys = calc_bollinger_bands(df=ohlcv_per_1m, period=bollinger_period, num_std_dev=bollinger_num_std_dev)
    upper_key = keys['upper_key']
    lower_key = keys['lower_key']
    b_key = keys['b_key']
    
    # 가격이 볼린저 밴드 하단을 터치치하였는가
    if ohlcv_per_1m[lower_key].iloc[-1] < ohlcv_per_1m["close"].iloc[-1]:
        return False
    
    # 볼린저 %b가 0이하인가
    if ohlcv_per_1m[b_key].iloc[-1] > 0:
        return False
    
    # mfi가 20이하인가
    ohlcv_per_1m, mfi_key = calc_mfi(df=ohlcv_per_1m, period=mfi_peirod)
    if ohlcv_per_1m[mfi_key].iloc[-1] > 20:
        return False
    
    return True

def check_overbought_by_bollinger_mfi(ohlcv_per_1m, bollinger_period = 20, bollinger_num_std_dev = 2, mfi_peirod = 14):
    # 볼린저
    ohlcv_per_1m, keys = calc_bollinger_bands(df=ohlcv_per_1m, period=bollinger_period, num_std_dev=bollinger_num_std_dev)
    upper_key = keys['upper_key']
    lower_key = keys['lower_key']
    b_key = keys['b_key']
    
    # 가격이 볼린저 밴드 상단을 터치하였는가
    if ohlcv_per_1m[upper_key].iloc[-1] > ohlcv_per_1m["close"].iloc[-1]:
        return False
    
    # 볼린저 %b가 1이상인가
    if ohlcv_per_1m[b_key].iloc[-1] < 1:
        return False
    
    # mfi가 80이상인가
    ohlcv_per_1m, mfi_key = calc_mfi(df=ohlcv_per_1m, period=mfi_peirod)
    if ohlcv_per_1m[mfi_key].iloc[-1] < 80:
        return False
    
    return True

def upbit_price_unit(item, price):
    if item in [
        'ADA', 'ALGO', 'BLUR', 'CELO', 'ELF', 'EOS', 'GRS', 'GRT',
        'ICX', 'MANA', 'MINA', 'POL', 'SAND', 'SEI', 'STG', 'TRX'
        ]:
        return 1
    '''
    https://docs.upbit.com/docs/krw-market-info
    '''
    if 0.0001 > price:
        return 0.00000001
    elif 0.001 > price:
        return 0.0000001
    elif 0.01 > price:
        return 0.000001
    elif 0.1 > price:
        return 0.00001
    elif 1 > price:
        return 0.0001
    elif 10 > price:
        return 0.001
    elif 100 > price:
        return 0.01
    elif 1000 > price:
        return 0.1
    elif 10000 > price:
        return 1
    elif 100000 > price:
        return 10
    elif 500000 > price:
        return 50
    elif 1000000 > price:
        return 100
    elif 1000000 > price:
        return 500
    return 1000