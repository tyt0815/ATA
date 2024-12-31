import argparse

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
        type=int,
        default=85000
    )
    
    return parser.parse_args()

if __name__ == "__main__":
    args = get_args()
    
    if args.mod == "Offline":
        exchange = OfflineExchange(args.file_path)
    elif args.mod == 'Upbit':
        exchange = UpbitExchange(
            end_condition=args.end_condition,
            file_path=args.file_path
        )
        
    agent = AutoTradingAgent(
        exchange=exchange
    )
    
    agent.run()