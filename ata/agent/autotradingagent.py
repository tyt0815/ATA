from collections import deque
import numpy as np
import traceback
import time
from pprint import pprint
from itertools import count

from ata.algorithm import trading
from ata.exchange.baseexchange import BaseExchange
from ata.utils.log import log, save_log
from ata.utils.markerorderpriceunit import upbit_price_unit

class AutoTradingAgent:
    def __init__(
        self,
        exchange:BaseExchange,
        wait_time_for_iter,
        wait_iter_for_sell_order,
        log_path = './log'
        ):
        self.exchange = exchange
        self.wait_time_for_iter = max(0, wait_time_for_iter)
        self.wait_iter_for_sell_order = max(0, wait_iter_for_sell_order)
        self.log_path = log_path
        
    def run(self):
        log('run ATA...')
        self.trading_data: dict[str, dict] = {}
        monitoring_target = set()
        
        # 거래 루프
        self.exchange.init()
        log(f'trading start (total: {self.exchange.get_total_balance()})')
        for t in count():
            try:
                start = time.time()
                self.log_str = ''
                total_profit = int(sum([data['profit'] for data in self.trading_data.values()]))
                self.__append_str(f'total: {int(self.exchange.get_total_balance()):>10}, total profit: {total_profit}')
                self.b_log = False
                if self.exchange.update() == False:
                    break
                
                # 매수 주문 알고리즘
                buying_candidates = monitoring_target.union(self.exchange.get_buying_candidates())
                for target in buying_candidates:
                    ohlcv_per_1m = self.exchange.get_ohlcv_per_1m(target)
                    ohlcv_per_1h = self.exchange.get_ohlcv_per_1h(target)
                    if ohlcv_per_1m is None:
                        continue
                    
                    self.__init_trading_data(target)
                    data = self.trading_data[target]
                    
                    # 매수 주문 타이밍 시 매수 주문
                    if self._is_buy_timing(ohlcv_per_1m, ohlcv_per_1h):
                        monitoring_target.add(target)
                        
                        data['buy_cnt'] += 1
                        data['sell_cnt'] = 0
                        buy_skip_criterion = np.median(data['buy_cnt_histories']) - 1
                        if data['buy_cnt'] > buy_skip_criterion:
                            krw = min(self.exchange.get_total_balance() / 5 * (data['buy_cnt'] - buy_skip_criterion), self.exchange.balance['KRW']['free'] - 100)
                            if krw > 6000:
                                curr_price = self.exchange.get_current_price(target)
                                unit = upbit_price_unit(item=target, price=curr_price)
                                price = curr_price - unit * max(2 + buy_skip_criterion - data['buy_cnt'], 0)
                                amount_item = krw / price
                                try:
                                    buy_order_id = self.exchange.create_buy_order(item=target, price=price, amount_item=amount_item)
                                    data['buy_order_infos'].append({'id':buy_order_id, 'cnt': t})
                                    buy_order = self.exchange.get_order(buy_order_id)
                                    self.__append_str(f'Buy order  {target}(current_price{curr_price:>12}, price: {buy_order["price"]:>12}, amount_krw: {buy_order["price"] * buy_order["amount"]:>7})')
                                except:
                                    save_log(traceback.format_exc(), self.log_path)
            
                # 매도 주문 알고리즘
                selling_candidates = monitoring_target.union(self.exchange.balance)
                for target in selling_candidates:
                    ohlcv_per_1m = self.exchange.get_ohlcv_per_1m(target)
                    if ohlcv_per_1m is None:
                        continue
                    self.__init_trading_data(target)
                    data = self.trading_data[target]
                    if self._is_sell_timing(ohlcv_per_1m) or self.exchange.is_plunge(item=target):
                        curr_price = self.exchange.get_current_price(item=target)
                        
                        # 채결 안된 매수 주문 취소
                        buy_prices = []
                        buy_amounts = []
                        for order_info in data['buy_order_infos']:
                            order = self.exchange.get_order(order_info['id'])
                            if order['status'] == 'open':
                                self.exchange.cancel_order_by_id(order_info['id'])
                                order = self.exchange.get_order(order_info['id'])
                                self.__append_str(f'Cancel buy order {target}(current_price{curr_price:>12}, price: {order["price"]:>12}, amount_krw: {order["price"] * (order["amount"] - order["filled"]):>7})')
                            if order['filled'] > 0:
                                buy_prices.append(order['price'])
                                buy_amounts.append(order['filled'])
                        data['buy_order_infos'].clear()
                        if len(buy_amounts) > 0:
                            buy_price_avg = np.average(buy_prices, weights=buy_amounts)
                            buy_amount = np.sum(buy_amounts)
                            self.__append_str(f'Buy {target}(current_price{curr_price:>12}, price: {buy_price_avg:>12}, amount_krw: {buy_price_avg * buy_amount:>7})')
                            data['buy_price_avg'] = (data['buy_price_avg'] * data['buy_amount'] + buy_price_avg * buy_amount) / (data['buy_amount'] + buy_amount)
                            data['buy_amount'] += buy_amount
                        
                        monitoring_target.discard(target)
                            
                        if data['buy_cnt'] > 0:
                            data['buy_cnt_histories'].append(data['buy_cnt'])
                        data['buy_cnt'] = 0
                        if target in self.exchange.balance:
                            data['sell_cnt'] += 1 
                            denominator = 2.0
                            weight = min(denominator, data['sell_cnt']) / denominator
                            amount_item = self.exchange.balance[target]['free']  * weight
                            unit = upbit_price_unit(item=target, price=curr_price)
                            sell_price = curr_price + unit * max(0, 2 - data['sell_cnt'])
                            krw = sell_price * amount_item
                            if krw > 6000:
                                try:
                                    sell_order_id = self.exchange.create_sell_order(item=target, price=sell_price, amount_item=amount_item)
                                    data['sell_order_infos'].append({'id':sell_order_id, 'cnt': t})
                                    sell_order = self.exchange.get_order(sell_order_id)
                                    self.__append_str(f'Sell order {target}(current_price{curr_price:>12}, price: {sell_order["price"]:>12}, amount_krw: {sell_order["price"] * sell_order["amount"]:>7})')
                                except:
                                    save_log(traceback.format_exc(), self.log_path)
                
                # 최종 거래 내역(매수 -> 매도까지) 로그
                for item in self.trading_data:
                    curr_price = self.exchange.get_current_price(item)
                    data = self.trading_data[item]
                    sell_order_infos_copy = data['sell_order_infos'][:]
                    sell_prices = []
                    sell_amounts = []
                    for order_info in sell_order_infos_copy:
                        order = self.exchange.get_order(order_info['id'])
                        if order['status'] == 'open' and t - order_info['cnt'] >= self.wait_iter_for_sell_order:
                            self.exchange.cancel_order_by_id(order_info['id'])
                            order = self.exchange.get_order(order_info['id'])
                            self.__append_str(f'Cancel sell order {item}(current_price{curr_price:>12}, price: {order["price"]:>12}, amount_krw: {order["price"] * (order["amount"] - order["filled"]):>7})')
                            sell_order_id = self.exchange.create_sell_order_at_market_price(item=item, amount_item=order['amount'] - order['filled'])
                            data['sell_order_infos'].append({'id':sell_order_id, 'cnt': order_info['cnt']})
                            
                        if order['status'] != 'open':
                            if order['filled'] > 0:
                                sell_prices.append(order['price'])
                                sell_amounts.append(order['filled'])
                            data['sell_order_infos'].remove(order_info)
                    
                    if len(sell_amounts) > 0:
                        sell_price_avg = np.average(sell_prices, weights=sell_amounts)
                        sell_amount = np.sum(sell_amounts)
                        profit = (sell_price_avg - data['buy_price_avg']) * min(sell_amount, data['buy_amount'])
                        data['profit'] += profit
                        data['buy_amount'] = max(0, data['buy_amount'] - sell_amount)
                        total_profit += profit
                        self.__append_str(f'Sell {target}(current_price{curr_price:>12}, price: {buy_price_avg:>12}, amount_krw: {buy_price_avg * buy_amount:>7}, profit: {int(profit):>6}), {item} total profit: {int(data["profit"]):>10}')
                        
                if self.b_log:
                    log(self.log_str)
                processing_time = time.time() - start
                time.sleep(max(0, self.wait_time_for_iter - processing_time))
            except:
                save_log(traceback.format_exc(), self.log_path)
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
    
    def __init_trading_data(self, item):
        if item in self.trading_data:
            return
        self.trading_data[item] = {
            'buy_cnt' : 0,
            'sell_cnt' : 0,
            'buy_cnt_histories' : deque([0, 0, 0], maxlen=3),
            'buy_order_infos' : [],
            'sell_order_infos' : [],
            'buy_price_avg' : 0,
            'buy_amount' : 0,
            'profit' : 0
        }
        
    def __append_str(self, additional_content: str):
        self.b_log = True
        self.log_str += additional_content + '\n'