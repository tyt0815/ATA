import numpy as np
import pandas as pd

def calc_sma(df, period, force_calc = False):
    '''
    df: "close"를 가지고 있어야 함
    return: f"sma{period}" 컬럼을 포함한 df
    '''
    if f"sma{period}" in df.columns and not force_calc:
        return df
    
    df[f"sma{period}"] = df["close"].rolling(window=period).mean()
    return df

def calc_ema(df, period, force_calc = False):
    '''
    df: "clsoe"를 가지고 있어야 함
    return: f"ema{period}" 컬럼을 포함한 df
    '''
    if f"ema{period}" in df.columns and not force_calc:
        return df
    
    df[f"ema{period}"] = df["close"].ewm(span=period, adjust=False).mean()
    return df

def calc_std(df, period, force_calc = False):
    '''
    df: "close"를 가지고 있어야 함
    return: f"std{period}" 컬럼을 포함한 df
    '''
    if f"std{period}" in df.columns and not force_calc:
        return df
    
    df[f"std{period}"] = df["close"].rolling(window=period).std()
    return df 

def calc_bollinger_bands(df, period, num_std_dev, force_calc = False):
    '''
    df: "close"를 가지고 있어야 함.
    return: f"upper_band{period}_{num_std_dev}", f"lower_band{period}_{num_std_dev}", f"bollinger_b{period}_{num_std_dev}",
        컬럼을 포함한 df
    '''
    columns_to_check = [f"upper_band{period}_{num_std_dev}", f"lower_band{period}_{num_std_dev}", f"bollinger_b{period}_{num_std_dev}"]
    
    if all(col in df.columns for col in columns_to_check) and not force_calc:
        return df
    
    df = calc_sma(df, period)
    df = calc_std(df, period)
    
    # 상단 밴드와 하단 밴드 계산
    df[f"upper_band{period}_{num_std_dev}"] = df[f"sma{period}"] + (df[f"std{period}"] * num_std_dev)
    df[f"lower_band{period}_{num_std_dev}"] = df[f"sma{period}"] - (df[f"std{period}"] * num_std_dev)
    
    # 볼린저 %b 계산
    
    df[f"bollinger_b{period}_{num_std_dev}"] = (
        (df["close"] - df[f"lower_band{period}_{num_std_dev}"]) / 
        (df[f"upper_band{period}_{num_std_dev}"] - df[f"lower_band{period}_{num_std_dev}"])
        )
    
    # 결과를 데이터프레임으로 반환
    return df

    
def calc_mfi(df, period=14, force_calc = False):
    '''
    df: 'high', 'low', 'close', 'volume' 가지고 있어야 함.
    return: f"mfi{period}" 컬럼을 포함한 df
    '''
    if f"mfi{period}" in df.columns and not force_calc:
        return df
    
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
    df[f"mfi{period}"] = 100 - (100 / (1 + money_flow_ratio))
    
    return df

def calc_rvol(self, df, period=10, force_calc = False):
    '''
    df: 'volume' 가지고 있어야 함.
    return: f'rvol{period}' 컬럼을 포함한 df
    '''
    if f'rvol{period}' in df.columns and not force_calc:
        return df
    
    rolling_mean = df['volume'].rolling(window=period).mean()

    # 현재 거래량(baseVolume)과 평균 거래량(rolling_mean) 비교
    df[f'rvol{period}'] = df['volume'] / rolling_mean
    return df

def calc_williams_r(df, period=10, force_calc = False):
    '''
    df: 'high', 'low', 'close' 가지고 있어야 함.
    return: f'williams_r{period}' 컬럼을 포함한 df
    '''
    if f'williams_r{period}' in df.columns and not force_calc:
        return df
    
    # 최고가, 최저가, 종가 계산
    df[f'williams_r{period}'] = ((df['high'].rolling(window=period).max() - df['close']) / 
                         (df['high'].rolling(window=period).max() - df['low'].rolling(window=period).min())) * -100
    return df

def calc_deviation_from_sma(df, period=20, force_calc = False):
    '''
    df: 'close' 가지고 있어야 함.
    return: f'deviation_sma{period}' 컬럼을 포함한 df
    '''
    if f'deviation_sma{period}' in df.columns and not force_calc:
        return df
    
    # 이동 평균 계산 (SMA)
    df = calc_sma(df, period)
    # 이격도 계산
    df[f'deviation_sma{period}'] = ((df['close'] - df[f'sma{period}']) / df[f'sma{period}']) * 100
    return df