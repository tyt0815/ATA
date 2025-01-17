import argparse
import pandas as pd
import numpy as np
import os

from ata.algorithm import trading

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--file-path",
        type=str,
        default="BTC_Data2.csv"
    )
    
    return parser.parse_args()

def is_buy_timing(self, ohlcv_per_1m):
    # 볼린저
    bollinger_period = 20
    bollinger_num_std_dev = 2
    ohlcv_per_1m = trading.calc_bollinger_bands(df=ohlcv_per_1m, period=bollinger_period, num_std_dev=bollinger_num_std_dev)
    
    # 급락시에는 매수를 하지 않는다
    y1 = ohlcv_per_1m['high'].iloc[-2]
    y2 = ohlcv_per_1m['low'].iloc[-1]
    if (y2 - y1) / y1 < -0.1:
        return False
    
    # 가격이 볼린저 밴드 하단을 터치치하였는가
    if ohlcv_per_1m[f"lower_band{bollinger_period}_{bollinger_num_std_dev}"].iloc[-1] < ohlcv_per_1m["close"].iloc[-1]:
        return False
    
    # 볼린저 %b가 0이하인가
    if ohlcv_per_1m[f"bollinger_b{bollinger_period}_{bollinger_num_std_dev}"].iloc[-1] > 0:
        return False
    
    # mfi가 20이하인가
    mfi_peirod = 14
    ohlcv_per_1m = trading.calc_mfi(df=ohlcv_per_1m, period=mfi_peirod)
    if ohlcv_per_1m[f'mfi{mfi_peirod}'].iloc[-1] > 20:
        return False
    
    return True

def is_sell_timing(self, ohlcv_per_1m):
    # 볼린저
    bollinger_period = 20
    bollinger_num_std_dev = 2
    ohlcv_per_1m = trading.calc_bollinger_bands(df=ohlcv_per_1m, period=bollinger_period, num_std_dev=bollinger_num_std_dev)
    
    # 가격이 볼린저 밴드 상단을 터치하였는가
    if ohlcv_per_1m[f"upper_band{bollinger_period}_{bollinger_num_std_dev}"].iloc[-1] > ohlcv_per_1m["close"].iloc[-1]:
        return False
    
    # 볼린저 %b가 1이상인가
    if ohlcv_per_1m[f"bollinger_b{bollinger_period}_{bollinger_num_std_dev}"].iloc[-1] < 1:
        return False
    
    # mfi가 80이상인가
    mfi_peirod = 14
    ohlcv_per_1m = trading.calc_mfi(df=ohlcv_per_1m, period=mfi_peirod)
    if ohlcv_per_1m[f'mfi{mfi_peirod}'].iloc[-1] < 80:
        return False
    
    return True

if __name__ == '__main__':
    args = get_args()
    
    df = pd.read_csv(args.file_path)
    
    bollinger_period = 20
    bollinger_num_std_dev = 2
    mfi_period = 14
    start_index = max(bollinger_period, mfi_period)
    df = trading.calc_bollinger_bands(df=df, period=bollinger_period, num_std_dev=bollinger_num_std_dev)
    df = trading.calc_mfi(df, mfi_period)
    
    label = [0 for _ in len(df)]
    for i in range(start_index, len(df)):
        # 하락장
        if is_buy_timing(df):
            label[i] = 1
        
        # 상승장
        elif is_sell_timing(df):
            label[i] = 2
        
