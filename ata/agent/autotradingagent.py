from collections import deque
import numpy as np
import traceback
import time

from ata.algorithm import trading
from ata.exchange.baseexchange import BaseExchange
from ata.utils.log import log, save_log
from ata.utils.markerorderpriceunit import upbit_price_unit

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
        buy_order_ids = {}
        sell_order_ids = {}
        buy_diffs = {}
        buy_first = {}
        buy_last = {}
        
        # 거래 루프
        self.exchange.init()
        log('trading start')
        monitoring_target = set()
        while True:
            try:
                if self.exchange.update() == False:
                    break
                for target in sell_order_ids:
                    for sell_order_id in sell_order_ids[target]:
                        order = self.exchange.get_order(sell_order_id)
                        if order['status'] == 'closed':
                            log(f'Sell {target} at {order["price"]:>12}(amount: {order["price"] * order["amount"]:>7}, total: {int(self.exchange.get_total_balance()):>7}, current_price{self.exchange.get_current_price(item=target):>12})')
                        else:
                            self.exchange.cancel_order_by_id(order_id=sell_order_id)
                            log(f'Cancel {target} sell order(amount_krw: {(order["amount"] - order["filled"]) * order["price"]}, price: {order["price"]}, amount: {order["amount"]}, filled: {order["filled"]})')
                            market_sell_id = self.exchange.create_sell_order_at_market_price(item=target, amount_item=order['amount'] - order['filled'])
                            market_order = self.exchange.get_order(market_sell_id)
                            log(f'Sell {target} at market price {market_order["price"]:>12}(amount: {market_order["price"] * market_order["amount"]:>7}, total: {int(self.exchange.get_total_balance()):>7}, current_price{self.exchange.get_current_price(item=target):>12})')
                        sell_order_ids[target].remove(sell_order_id)
                            
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
                        if not target in buy_diffs:
                            buy_diffs[target] = deque([0], maxlen=3)
                        if not target in buy_first:
                            buy_first[target] = 0
                            buy_last[target] = 0
                        if buy_first[target] == 0:
                            buy_first[target] = self.exchange.get_current_price(item=target)
                        buy_last[target] = self.exchange.get_current_price(item=target)
                        if not target in buy_cnt_histories:
                            continue
                        buy_skip_criterion = np.median(buy_cnt_histories[target]) - 1
                        # buy_skip_criterion = 0
                        if buy_cnt[target] > buy_skip_criterion:
                            krw = min(self.exchange.get_total_balance() / 5 * (buy_cnt[target] - buy_skip_criterion), self.exchange.balance['KRW']['free'] - 100)
                            if krw > 6000:
                                curr_price = self.exchange.get_current_price(target)
                                unit = upbit_price_unit(item=target, price=curr_price)
                                # diff = np.mean(buy_diffs[target]) * 0.4 * (3 - buy_cnt[target] + buy_skip_criterion)
                                # price = curr_price - (int(curr_price * diff / unit) * unit)
                                price = curr_price - unit * max(2 + buy_skip_criterion - buy_cnt[target], 0)
                                amount_item = krw / price
                                buy_order_id = self.exchange.create_buy_order(item=target, price=price, amount_item=amount_item)
                                if not target in buy_order_ids:
                                    buy_order_ids[target] = []
                                buy_order_ids[target].append(buy_order_id)
                                buy_order = self.exchange.get_order(buy_order_id)
                                log(f'Buy order {target} at {buy_order["price"]:>12}(current_price{self.exchange.get_current_price(item=target):>12}, amount_krw: {buy_order["price"] * buy_order["amount"]:>7}, total: {int(self.exchange.get_total_balance()):>7}) Debug - buy_cnt["{target}"] = {buy_cnt[target]}')
            
                # 매도 주문 넣기
                selling_candidates = monitoring_target.union(self.exchange.balance)
                for target in selling_candidates:
                    ohlcv_per_1m = self.exchange.get_ohlcv_per_1m(target)
                    if ohlcv_per_1m is None:
                        continue
                    if self._is_sell_timing(ohlcv_per_1m) or self.exchange.is_plunge(item=target):
                        if not target in buy_diffs:
                            buy_diffs[target] = deque([0], maxlen=3)
                        if not target in buy_first:
                            buy_first[target] = 0
                            buy_last[target] = 0
                        if buy_first[target] > 0:
                            buy_diffs[target].append((buy_first[target] - buy_last[target]) / buy_first[target] if buy_first[target] != 0 else 0)
                        buy_first[target] = 0
                        if not target in buy_order_ids:
                            buy_order_ids[target] = []
                        buy_prcies = []
                        buy_amounts = []
                        for buy_id in buy_order_ids[target]:
                            order = self.exchange.get_order(buy_id)
                            if order['status'] != 'closed':
                                self.exchange.cancel_order_by_id(buy_id)
                                log(f'Cancel {target} buy order(amount_krw: {(order["amount"] - order["filled"]) * order["price"]}, price: {order["price"]}, amount: {order["amount"]}, filled: {order["filled"]})')
                            if order['filled'] > 0:
                                buy_prcies.append(order['price'])
                                buy_amounts.append(order['filled'])
                        buy_order_ids[target].clear()
                        if len(buy_amounts) > 0:
                            buy_avg = np.average(buy_prcies, weights=buy_amounts)
                            amount = np.sum(buy_amounts)
                            log(f'Buy  {target} at {buy_avg:>12}(amount_krw: {buy_avg * amount:>7}, total: {int(self.exchange.get_total_balance()):>7})')
                                
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
                                unit = upbit_price_unit(item=target, price=curr_price)
                                sell_price = curr_price + unit * max(0, 2 + (sell_skip_criterion - sell_cnt[target]))
                                krw = sell_price * amount_item
                                if krw > 6000:
                                    sell_order_id = self.exchange.create_sell_order(item=target, price=sell_price, amount_item=amount_item)
                                    if target not in sell_order_ids:
                                        sell_order_ids[target] = []
                                    sell_order_ids[target].append(sell_order_id)
                                    sell_order = self.exchange.get_order(sell_order_id)
                                    log(f'Sell order {target} at {sell_order["price"]:>12}(amount: {sell_order["price"] * sell_order["amount"]:>7}, total: {int(self.exchange.get_total_balance()):>7}, current_price{self.exchange.get_current_price(item=target):>12})')
                                    
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