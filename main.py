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
        default=0.8
    )
    
    parser.add_argument(
        '--only-btc',
        type=bool,
        default=False
    )
    
    parser.add_argument(
        '--wait-time-for-iter',
        type=float,
        default=60
    )
    
    parser.add_argument(
        '--wait-iter-for-sell-order',
        type=int,
        default=1
    )
    
    return parser.parse_args()

if __name__ == "__main__":
    print(os.getpid())
    args = get_args()
    
    if args.mod == "Offline":
        exchange = OfflineExchange(args.file_path)
        wait_time_for_iter = 0
    elif args.mod == 'Upbit':
        exchange = UpbitExchange(
            end_condition=args.end_condition,
            file_path=args.file_path,
            only_btc=args.only_btc
        )
        wait_time_for_iter = args.wait_time_for_iter
        
    agent = AutoTradingAgent(
        exchange=exchange,
        wait_time_for_iter=wait_time_for_iter,
        wait_iter_for_sell_order=args.wait_iter_for_sell_order
    )
    
    agent.run()