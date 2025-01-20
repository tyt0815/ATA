import argparse
import os

from ata.agent.autotradingagent import AutoTradingAgent
from ata.exchange.offlineexchange import OfflineExchange
from ata.exchange.upbitexchange import UpbitExchange

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mod",
        type=str,
        default="Upbit",
        choices=["Offline", "Upbit"]
    )
    
    parser.add_argument(
        "--file-path",
        type=str,
        default="upbit.key"
    )
    
    parser.add_argument(
        '--end-condition',
        type=float,
        default=0.7
    )
    
    return parser.parse_args()

if __name__ == "__main__":
    print(os.getpid())
    args = get_args()
    
    if args.mod == "Offline":
        exchange = OfflineExchange(args.file_path)
        wait_a_minute = False
    elif args.mod == 'Upbit':
        exchange = UpbitExchange(
            end_condition=args.end_condition,
            file_path=args.file_path
        )
        wait_a_minute = True
        
    agent = AutoTradingAgent(
        exchange=exchange,
        wait_a_minute=wait_a_minute
    )
    
    agent.run()