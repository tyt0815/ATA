from collections import deque
import numpy as np
import traceback
import time

from ata.algorithm import trading
from ata.exchange.baseexchange import BaseExchange
from ata.utils.log import log, save_log

class AutoTradingAgent:
    def __init__(
        self,
        exchange:BaseExchange,
        wait_a_minute
        ):
        self.exchange = exchange
        self.wait_a_minute = wait_a_minute
        
    def run(self):
        log('run ATA...')
        buy_cnt = {}
        sell_cnt = {}
        buy_cnt_histories = {}
        # 거래 루프
        self.exchange.init()
        log('trading start')
        monitoring_target = set()
        while True:
            try:
                if self.exchange.update() == False:
                    break
                # 매수 주문 넣기
                start = time.time()
                buying_candidates = monitoring_target.union(self.exchange.get_buying_candidates())
                for target in buying_candidates:
                    ohlcv_per_1m = self.exchange.get_ohlcv_per_1m(target)
                    ohlcv_per_1h = self.exchange.get_ohlcv_per_1h(target)
                    if ohlcv_per_1m is None:
                        continue
                    if self._is_buy_timing(ohlcv_per_1m, ohlcv_per_1h):
                        monitoring_target.add(target)
                        if not target in buy_cnt:
                            buy_cnt[target] = 0
                        buy_cnt[target] += 1
                        sell_cnt[target] = 0
                        if not target in buy_cnt_histories:
                            continue
                        buy_skip_criterion = np.median(buy_cnt_histories[target]) - 1
                        if buy_cnt[target] > buy_skip_criterion:
                            krw = min(self.exchange.get_total_balance() / 5 * (buy_cnt[target] - buy_skip_criterion), self.exchange.balance['KRW']['free'] - 100)
                            if krw > 6000:
                                buy_order_id = self.exchange.create_buy_order_at_market_price(item=target, amount_krw=krw)
                                buy_order = self.exchange.get_order(buy_order_id)
                                log(f'Buy  {target} at {buy_order["price"]:>12}(current_price{self.exchange.get_current_price(item=target):>12}, amount: {int(krw):>7}, total: {int(self.exchange.get_total_balance()):>7}) Debug - buy_cnt["{target}"] = {buy_cnt[target]}')
            
                # 매도 주문 넣기
                selling_candidates = monitoring_target.union(self.exchange.balance)
                for target in selling_candidates:
                    ohlcv_per_1m = self.exchange.get_ohlcv_per_1m(target)
                    if ohlcv_per_1m is None:
                        continue
                    if self._is_sell_timing(ohlcv_per_1m) or self.exchange.is_plunge(item=target):
                        if target in buy_cnt_histories:
                            if buy_cnt[target] > 0:
                                buy_cnt_histories[target].append(buy_cnt[target])
                        elif target in buy_cnt:
                            buy_cnt_histories[target] = deque([buy_cnt[target]], maxlen=3)
                        buy_cnt[target] = 0
                        if target in monitoring_target:
                            monitoring_target.remove(target)
                        if target in self.exchange.balance:
                            if not target in sell_cnt:
                                sell_cnt[target] = 0
                            sell_cnt[target] += 1 
                            sell_skip_criterion = 0
                            if sell_cnt[target] > sell_skip_criterion:
                                curr_price = self.exchange.get_current_price(item=target)
                                denominator = 2.0
                                weight = min(denominator, sell_cnt[target] - sell_skip_criterion) / denominator
                                amount_item = self.exchange.balance[target]['free']  * weight
                                krw = curr_price * amount_item
                                if krw > 6000:
                                    sell_order_id = self.exchange.create_sell_order_at_market_price(item=target, amount_item=amount_item)
                                    sell_order = self.exchange.get_order(sell_order_id)
                                    log(f'Sell {target} at {sell_order["price"]:>12}(current_price{self.exchange.get_current_price(item=target):>12}, amount: {int(krw):>7}, total: {int(self.exchange.get_total_balance()):>7})')
                                    buy_cnt[target] = 1
                processing_time = time.time() - start
                if self.wait_a_minute:
                    time.sleep(60 - processing_time)
            except Exception as e:
                log_path = './log'
                log(str(e))
                save_log(content=traceback.format_exc(), file_path=log_path)
                self.exchange.init()
            
                
        self._end_trading()
            
    def _end_trading(self):
        self.exchange.init()
        selling_candidates = self.exchange.balance
        for target in selling_candidates:
            ohlcv = self.exchange.get_ohlcv_per_1m(target)
            if ohlcv is None:
                continue
            try:
                self.exchange.create_sell_all_order_at_market_price(item=target)
            except Exception as e:
                log_path = './log'
                log(str(e))
                save_log(content=traceback.format_exc(), file_path=log_path)
                self.exchange.init()
            finally:
                continue
        log('end trading')
        return
                
    def _is_buy_timing(self, ohlcv_per_1m, ohlcv_per_1h):
        return trading.check_oversold_by_bollinger_mfi(ohlcv_per_1m)
    
    def _is_sell_timing(self, ohlcv_per_1m):
        return trading.check_overbought_by_bollinger_mfi(ohlcv_per_1m)