import argparse

from ata.agent.autotradingagent import AutoTradingAgent
from ata.exchange.offlineexchange import OfflineExchange

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mod",
        type=str,
        default="Offline",
        choices=["Offline"]
    )
    
    # 오프라인 모드 전용 옵션션
    parser.add_argument(
        "--file-path",
        type=str,
        default="BTC_Data.csv"
    )
    
    parser.add_argument(
        "--danger",
        type=int,
        default=1,
        choices=[0, 1, 2, 3]
    )
    
    return parser.parse_args()

if __name__ == "__main__":
    args = get_args()
    
    if args.mod == "Offline":
        exchange = OfflineExchange(args.file_path)
        
    agent = AutoTradingAgent(
        exchange=exchange,
        danger=args.danger
    )
    
    agent.run()