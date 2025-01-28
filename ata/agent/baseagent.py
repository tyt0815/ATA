from abc import abstractmethod
from collections import deque
import numpy as np
import traceback
from pprint import pprint

from ata.exchange.baseexchange import BaseExchange
from ata.utils.format import format_float
from ata.utils.log import log, save_log

class BaseAgent():
    def __init__(
        self,
        exchange:BaseExchange,
        wait_time_for_buy_order,
        wait_time_for_sell_order,
        wait_time_for_cancel_sell_order,
        only_btc,
        end_condition,
        log_path = './log'
        ):
        self.exchange = exchange
        self.trading_data: dict[str, dict] = {}
        self.wait_time_for_buy_order = max(0, wait_time_for_buy_order)
        self.wait_time_for_sell_order = max(0, wait_time_for_sell_order)
        self.wait_time_for_cancel_sell_order = wait_time_for_cancel_sell_order
        self.only_btc = only_btc
        self.log_path = log_path
        self.end_condition = end_condition
        
    def run(self):
        log('run ATA...')
        monitoring_target = set()
        # 거래 루프
        self.exchange.init()
        top_value = self.exchange.get_total_balance()
        log(f'trading start \ntotal: {format_float(self.exchange.get_total_balance(), 10):<10}')
        while True:
            try:
                if self.exchange.update() == False:
                    break
                top_value = max(top_value, self.exchange.get_total_balance())
                if self.exchange.get_total_balance() < top_value * self.end_condition:
                    log(f'Top value: {top_value}, Current balance: {self.exchange.get_total_balance()}')
                    break
                # 매수 주문 알고리즘
                buying_candidates = monitoring_target.union(self._get_buying_candidates())
                for target in buying_candidates:
                    if not self.exchange.is_tradable(target):
                        continue
                    
                    self.__init_trading_data(target)
                    data = self.trading_data[target]
                    
                    # 매수 주문 타이밍 시 매수 주문
                    if self.exchange.get_time() - data['last_buy_time'] >= self.wait_time_for_buy_order and self._is_buy_timing(target):
                        monitoring_target.add(target)
                        curr_price = self.exchange.get_current_price(target)
                        data['last_buy_time'] = self.exchange.get_time()
                        data['buy_cnt'] += 1
                        data['sell_cnt'] = 0
                        if data['buy_cnt'] > self._calc_buy_skip_criterion(target):
                            buy_price, buy_amount_item, buy_amount_krw = self._calc_values_for_buy_order(target)
                            if buy_amount_krw > 6000:
                                try:
                                    if buy_price is None:
                                        buy_order_id = self.exchange.create_buy_order_at_market_price(target, buy_amount_krw)
                                    else:
                                        buy_order_id = self.exchange.create_buy_order(item=target, price=buy_price, amount_item=buy_amount_item)
                                    data['buy_order_infos'].append({'id':buy_order_id, 'time': self.exchange.get_time()})
                                    buy_order = self.exchange.get_order(buy_order_id)
                                    log(f'Buy order {target}\ntotal: {format_float(self.exchange.get_total_balance(), 10):<10}, total profit: {format_float(self.total_profit, 10):<10}, current_price: {format_float(curr_price, 12):<12}, price: {format_float(buy_order["price"], 12):<12}, amount_krw: {format_float(buy_order["price"] * buy_order["amount"], 7):<7}')
                                except:
                                    save_log(traceback.format_exc(), self.log_path)
            
                # 매도 주문 알고리즘
                selling_candidates = monitoring_target.union(self.exchange.balance)
                for target in selling_candidates:
                    if not self.exchange.is_tradable(target):
                        continue
                    
                    self.__init_trading_data(target)
                    data = self.trading_data[target]
                    if self.exchange.get_time() - data['last_sell_time'] >= self.wait_time_for_sell_order and self._is_sell_timing(target):
                        monitoring_target.discard(target)
                        curr_price = self.exchange.get_current_price(item=target)
                        data['last_sell_time'] = self.exchange.get_time()
                        
                        # 채결 안된 매수 주문 취소
                        buy_prices = []
                        buy_amounts = []
                        for order_info in data['buy_order_infos']:
                            order = self.exchange.get_order(order_info['id'])
                            if order['status'] == 'open':
                                self.exchange.cancel_order_by_id(order_info['id'])
                                order = self.exchange.get_order(order_info['id'])
                                log(f'Cancel buy order {target}\ntotal: {format_float(self.exchange.get_total_balance(), 10):<10}, total profit: {format_float(self.total_profit, 10):<10}, current_price: {format_float(curr_price, 12):<12}, price: {format_float(order["price"], 12):<12}, amount_krw: {format_float(order["price"] * (order["amount"] - order["filled"]), 7):<7}')
                            if order['filled'] > 0:
                                buy_prices.append(order['price'])
                                buy_amounts.append(order['filled'])
                        data['buy_order_infos'].clear()
                        if len(buy_amounts) > 0:
                            buy_price_avg = np.average(buy_prices, weights=buy_amounts)
                            buy_amount = np.sum(buy_amounts)
                            log(f'Buy {target}\ntotal: {format_float(self.exchange.get_total_balance(), 10):<10}, total profit: {format_float(self.total_profit, 10):<10}, current_price: {format_float(curr_price, 12):<12}, price: {format_float(buy_price_avg, 12):<12}, amount_krw: {format_float(buy_price_avg * buy_amount, 7):<7}')
                            data['buy_price_avg'] = (data['buy_price_avg'] * data['buy_amount'] + buy_price_avg * buy_amount) / (data['buy_amount'] + buy_amount)
                            data['buy_amount'] += buy_amount
                        if data['buy_cnt'] > 0:
                            data['buy_cnt_histories'].append(data['buy_cnt'])
                        data['buy_cnt'] = 0
                        
                        if target in self.exchange.balance:
                            data['sell_cnt'] += 1 
                            if data['sell_cnt'] > self._calc_sell_skip_criterion(target):
                                sell_price, sell_amount_item, sell_amount_krw = self._calc_values_for_sell_order(target)
                                if sell_amount_krw > 6000:
                                    try:
                                        if sell_price is None:
                                            sell_order_id = self.exchange.create_sell_order_at_market_price(target, sell_amount_item)
                                        else:
                                            sell_order_id = self.exchange.create_sell_order(item=target, price=sell_price, amount_item=sell_amount_item)
                                        data['sell_order_infos'].append({'id':sell_order_id, 'time': self.exchange.get_time()})
                                        sell_order = self.exchange.get_order(sell_order_id)
                                        log(f'Sell order {target}\ntotal: {format_float(self.exchange.get_total_balance(), 10):<10}, total profit: {format_float(self.total_profit, 10):<10}, current_price: {format_float(curr_price, 12):<12}, price: {format_float(sell_order["price"], 12):<12}, amount_krw: {int(sell_order["price"] * sell_order["amount"]):<7}')
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
                        if order['status'] == 'open' and self.exchange.get_time() - order_info['time'] >= self.wait_time_for_cancel_sell_order:
                            self.exchange.cancel_order_by_id(order_info['id'])
                            order = self.exchange.get_order(order_info['id'])
                            log(f'Cancel sell order {item}\ntotal: {format_float(self.exchange.get_total_balance(), 10):<10}, total profit: {format_float(self.total_profit, 10):<10}, current_price: {format_float(curr_price, 12):<12}, price: {format_float(order["price"], 12):<12}, amount_krw: {format_float(order["price"] * (order["amount"] - order["filled"]), 7):<7}')
                            sell_order_id = self.exchange.create_sell_order_at_market_price(item=item, amount_item=order['amount'] - order['filled'])
                            data['sell_order_infos'].append({'id':sell_order_id, 'time': order_info['time']})
                            
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
                        log(f'Sell {item}\ntotal: {format_float(self.exchange.get_total_balance(), 10):<10}, total profit: {format_float(self.total_profit, 10):<10}, current_price: {format_float(curr_price, 12):<12}, price: {format_float(sell_price_avg, 12):<12}, amount_krw: {format_float(sell_price_avg * sell_amount, 7):<7}, profit: {format_float(profit, 6):<6}')
                        self.print_profits()
                
            except KeyboardInterrupt as e:
                break
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
            except:
                save_log(content=traceback.format_exc(), file_path=self.log_path)
                self.exchange.init()
            finally:
                continue
        self.print_profits()
        log('end trading')
        return
    
    def __init_trading_data(self, item):
        if item in self.trading_data:
            return
        self.trading_data[item] = {
            'buy_cnt' : 0,
            'sell_cnt' : 0,
            'buy_cnt_histories' : deque([0], maxlen=5),
            'buy_order_infos' : [],
            'sell_order_infos' : [],
            'buy_price_avg' : 0,
            'buy_amount' : 0,
            'profit' : 0,
            'last_buy_time': 0,
            'last_sell_time' : 0
        }
        
    def print_profits(self):
        pprint({temp:format_float(self.trading_data[temp]['profit'], 10) for temp in self.trading_data})
        
    @property
    def total_profit(self):
        return sum([data['profit'] for data in self.trading_data.values()])
                
    @abstractmethod
    def _is_buy_timing(self, item) -> bool:
        pass
    
    @abstractmethod
    def _is_sell_timing(self, item) -> bool:
        pass
    
    @abstractmethod
    def _get_buying_candidates(self) -> set:
        pass
    
    @abstractmethod
    def _calc_values_for_buy_order(self, item) -> tuple[float, float, float]:
        '''
        return buy_price, buy_amount_item, buy_amount_krw
        '''
        pass
    
    @abstractmethod
    def _calc_values_for_sell_order(self, item) -> tuple[float, float, float]:
        '''
        return sell_price, sell_amount_item, sell_amount_krw
        '''
        pass
    
    # property
    @abstractmethod
    def _calc_buy_skip_criterion(self, item) -> int:
        pass
    
    @abstractmethod
    def _calc_sell_skip_criterion(self, item) -> int:
        pass