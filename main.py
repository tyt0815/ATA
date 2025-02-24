import argparse
import os

from ata.agent.lhagent import LHAgent
from ata.agent.sragent import SRAgent
from ata.exchange.offlineexchangesimulator import OfflineExchangeSimulator
from ata.exchange.upbitexchange import UpbitExchange
from ata.exchange.upbitexchangesimulator import UpbitExchangeSimulator

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mod",
        type=str,
        default="Upbit",
        choices=["Upbit", "OfflineSimul", "UpbitSimul"]
    )
    
    parser.add_argument(
        '--agent',
        type=str,
        default='LHA',
        choices=['LHA', 'SRA']
    )
    
    parser.add_argument(
        "--file-path",
        type=str,
        default="upbit.key"
    )
    
    parser.add_argument(
        '--end-condition',
        type=float,
        default=0.9
    )
    
    parser.add_argument(
        '--only-btc',
        action='store_true',
    )
    
    parser.add_argument(
        '--wait-time-for-buy-order',
        type=float,
        default=60
    )
    
    parser.add_argument(
        '--wait-time-for-sell-order',
        type=float,
        default=60
    )
    
    parser.add_argument(
        '--wait-time-for-cancel-sell-order',
        type=float,
        default=60
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
    )
    
    return parser.parse_args()

if __name__ == "__main__":
    print(os.getpid())
    args = get_args()
    
    for arg, value in vars(args).items():
        print(f"{arg}: {value}")
    print()
    if args.mod == 'Upbit':
        exchange = UpbitExchange(
            end_condition=args.end_condition,
            file_path=args.file_path
        )
    elif args.mod == "OfflineSimul":
        exchange = OfflineExchangeSimulator(args.file_path)
    elif args.mod == 'UpbitSimul':
        exchange=UpbitExchangeSimulator(
            file_path=args.file_path
        )
    
    if args.agent == 'LHA':
        agent = LHAgent(
            exchange=exchange,
            wait_time_for_buy_order=args.wait_time_for_buy_order,
            wait_time_for_sell_order=args.wait_time_for_sell_order,
            wait_time_for_cancel_sell_order=args.wait_time_for_cancel_sell_order,
            only_btc=args.only_btc,
            debug=args.debug,
            end_condition=args.end_condition
        )
    elif args.agent == 'SRA':
        agent = SRAgent(
            exchange=exchange,
            wait_time_for_buy_order=args.wait_time_for_buy_order,
            wait_time_for_sell_order=args.wait_time_for_sell_order,
            wait_time_for_cancel_sell_order=args.wait_time_for_cancel_sell_order,
            only_btc=args.only_btc,
            debug=args.debug,
            end_condition=args.end_condition
        )
    
    agent.run()