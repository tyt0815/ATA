import os
import pandas as pd
import numpy as np
import math
import torch
from torch.utils.data import Dataset
import torchvision.transforms as transforms

from ata.algorithm import trading

class OfflineDataset(Dataset):
    def __init__(self, file_path, sequence_len):
        self.data = pd.read_csv(file_path)
        self.data = self.data.rename(columns={"baseVolume": "volume"})
        self.sequence_len = sequence_len
        
        self.bollinger_period = 20
        self.bollinger_num_std_dev = 2
        self.data, bollinger_keys = trading.calc_bollinger_bands(
            df=self.data, 
            period=self.bollinger_period, 
            num_std_dev=self.bollinger_num_std_dev
            )
        self.upper_key = bollinger_keys['upper_key']
        self.lower_key = bollinger_keys['lower_key']
        self.b_key = bollinger_keys['b_key']
        
        self.mfi_peirod = 14
        self.data, self.mfi_key = trading.calc_mfi(
            df=self.data, 
            period=self.mfi_peirod
            )
        
        # self.idx_offset = max([self.bollinger_period, self.mfi_peirod]) - 1
        self.idx_offset = max([self.bollinger_period, self.mfi_peirod]) - 1
        
        # self.data, self.label_key = self.label_by_bollinger_mfi(self.data)
        self.data, self.label_key = self.label_by_future_close(self.data)
        
        # NaN 값이 포함된 행의 인덱스 확인
        nan_indices = self.data[self.data.isna().any(axis=1)].index

        # NaN이 포함된 행을 제거
        self.data = self.data.dropna()

        # 제거된 인덱스 출력
        print("제거된 행의 인덱스:", nan_indices)

    def __len__(self):
        return len(self.data) - self.sequence_len - self.idx_offset + 1

    def __getitem__(self, idx):
        start = self.idx_offset + idx
        end = self.idx_offset + idx + self.sequence_len
        data = self.data[start:end]
        label = data[self.label_key].iloc[-1]
        data = data.drop(columns=['datetime', self.label_key])
        data = data.iloc[::-1].reset_index(drop=True).values
        
        # 각 열에 대해 min-max 정규화 (최댓값 - 최솟값이 0인 경우 처리)
        min_vals = data.min(axis=0)
        max_vals = data.max(axis=0)

        # (최댓값 - 최솟값이 0인 경우 1로 나누는 대신 0으로 설정)
        range_vals = max_vals - min_vals
        range_vals[range_vals == 0] = 1  # 최댓값과 최솟값이 같으면 1로 처리

        # 정규화
        normalized_data = (data - min_vals) / range_vals

        # normalized_data = np.nan_to_num(normalized_data, nan=0.0)
        
        return torch.tensor(np.array([normalized_data]),dtype=torch.float32), torch.tensor(label)
    
    def label_by_bollinger_mfi(self, df):
        start_idx = self.idx_offset
        label = [0 for _ in range(len(df))]
        
        oversold_idx = []
        overbought_idx = []
        
        for idx in range(start_idx, len(df)):
            param = (df[idx - self.idx_offset:idx + 1], self.bollinger_period, self.bollinger_num_std_dev, self.mfi_peirod)
            if trading.check_oversold_by_bollinger_mfi(*param):
                if len(overbought_idx) > 0:
                    for buy_idx in oversold_idx:
                        if df['close'][buy_idx] < df['close'][overbought_idx[0]]:
                            label[buy_idx] = 1
                    
                    for sell_idx in overbought_idx:
                        label[sell_idx] = 2
                    
                    
                    oversold_idx.clear()
                    overbought_idx.clear() 
                
                oversold_idx.append(idx)
            elif trading.check_overbought_by_bollinger_mfi(*param):
                overbought_idx.append(idx)
        
        label_key = 'label'
        df[label_key] = label
                
        return df, label_key
    
    def label_by_future_close(self, df, factor=0.001, future_period=10):
        start_idx = self.idx_offset
        label = [0 for _ in range(len(df))]
        
        for idx in range(start_idx, len(df) - future_period - 1):
            if df['close'].iloc[idx] * (1 + factor) < df['close'].iloc[idx + 1:idx + 1 + future_period].values:
                label[idx] = 1
            elif df['close'].iloc[idx] * (1 - factor) > df['close'].iloc[idx + future_period]:
                label[idx] = 2
        
        label_key = 'label'
        df[label_key] = label
                
        return df, label_key