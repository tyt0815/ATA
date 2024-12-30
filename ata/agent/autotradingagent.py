from datetime import datetime
from itertools import count
import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd
import sys
import traceback

from ata.algorithm import trading
from ata.exchange.baseexchange import BaseExchange

class AutoTradingAgent:
    def __init__(
        self,
        exchange:BaseExchange
        ):
        self.exchange = exchange
        
    def run(self):        
        buy_cnt = {}
        # 거래 루프
        self.exchange.init()
        try:
            while True:
                if self.exchange.update() == False:
                    break
                # 매수 주문 넣기
                buying_candidates = self.exchange.get_buying_candidates()
                for target in buying_candidates:
                    ohlcv = self.exchange.get_ohlcv_per_1m(target)
                    if self.exchange.balance['KRW']['total'] > 0 and self._is_buy_timing(ohlcv):
                        self.exchange.cancel_order_by_item(target)
                        curr_price = self.exchange.get_current_price(item=target)
                        if not target in buy_cnt:
                            buy_cnt[target] = 0
                        krw = min(self.exchange.get_total_balance() / 9 * (buy_cnt[target] + 1), self.exchange.balance['KRW']['free'])
                        amount = krw / curr_price
                        buy_id = self.exchange.create_buy_order(item=target, price=curr_price, amount=amount)
                
                # 매도 주문 넣기
                selling_candidates = self.exchange.balance
                for target in selling_candidates:
                    ohlcv = self.exchange.get_ohlcv_per_1m(target)
                    if ohlcv is None:
                        continue
                    if self.exchange.balance[target]['total'] > 0 and self._is_sell_timing(ohlcv):
                        self.exchange.cancel_order_by_item(target)
                        curr_price = self.exchange.get_current_price(item=target)
                        amount = self.exchange.balance[target]['free']
                        sell_id = self.exchange.create_sell_order(target, price=curr_price, amount=amount)
                
                # 주문 현황 확인
                for target in self.exchange.order_ids:
                    order_ids = self.exchange.order_ids[target][:]
                    for order_id in order_ids:
                        order = self.exchange.get_order(order_id)
                        # 주문이 진행중일때
                        if order['status'] == 'open':
                            # 매수 주문
                            if order['side'] == 'bid':
                                # 매수 주문 금액이 너무 낮을 때, 주문을 취소
                                if order['price'] * 1.05 < self.exchange.get_current_price(target):
                                    self.exchange.cancel_order_by_id(order_id)
                            # 매도 주문
                            elif order['side'] == 'ask':
                                # 매도 주문 금액이 너무 높을 때, 주문을 시장가 매도로 전환
                                if order['price'] * 0.95 > self.exchange.get_current_price(target):
                                    self.exchange.cancel_order_by_id(order_id)
                        # 주문이 채결되었을때
                        elif order['status'] == 'closed':
                            # 매수 주문
                            if order['side'] == 'bid':
                                buy_cnt[target] += 1
                                self._log(f'Close buy order ({order_id}). buy  {target:>4} at {order["price"]}, {self.exchange.get_total_balance()}')
                            # 매도 주문
                            elif order['side'] == 'ask':
                                buy_cnt[target] = 0
                                self._log(f'Close sell order({order_id}). sell {target:>4} at {order["price"]}, {self.exchange.get_total_balance()}')
                            else:
                                raise Exception(f'unexpected order side({order["side"]})')

                            self.exchange.remove_order_id(item=target, order_id=order_id)
                        # 취소된 주문이 남아있을 때 order_id에서 제거
                        elif order['status'] == 'canceled':
                            if order['side'] == 'bid':
                                self._log(f'Cancel buy order ({order_id}). order amount: {order["amount"]}, filled: {order["filled"]}')
                            elif order['side'] == 'ask':
                                self._log(f'Cancel sell order({order_id}). order amount: {order["amount"]}, filled: {order["filled"]}')
                            self.exchange.remove_order_id(item=target, order_id=order_id)
                        # 에러
                        else:
                            raise Exception(f'unexpected order status({order["status"]})')
        except Exception as e:
            self._log(f'unexpected error: {e}')
            print(traceback.format_exc())
        finally:
            self._end_trading()
            
    def _end_trading(self):
        selling_candidates = self.exchange.balance
        self.exchange.init()
        for target in selling_candidates:
            try:
                self.exchange.cancel_order_by_item(target)
                self.exchange.create_sell_order_at_market_price(item=target, amount=self.exchange.balance[target]['free'])
            except Exception as e:
                self._log(e)
                print(traceback.format_exc())
            finally:
                continue
        return
                
    def _is_buy_timing(self, ohlcv):
        # 볼린저
        bollinger_period = 20
        bollinger_num_std_dev = 2
        ohlcv = trading.calc_bollinger_bands(df=ohlcv, period=bollinger_period, num_std_dev=bollinger_num_std_dev)
        
        # 가격이 볼린저 밴드 하단을 터치치하였는가
        if ohlcv[f"lower_band{bollinger_period}_{bollinger_num_std_dev}"].iloc[-1] < ohlcv["close"].iloc[-1]:
            return False
        
        # 볼린저 %b가 0이하인가
        if ohlcv[f"bollinger_b{bollinger_period}_{bollinger_num_std_dev}"].iloc[-1] > 0:
            return False
        
        # mfi가 20이하인가
        mfi_peirod = 14
        ohlcv = trading.calc_mfi(df=ohlcv, period=mfi_peirod)
        if ohlcv[f'mfi{mfi_peirod}'].iloc[-1] > 20:
            return False
        
        return True
    
    def _is_sell_timing(self, ohlcv):
        # 볼린저
        bollinger_period = 20
        bollinger_num_std_dev = 2
        ohlcv = trading.calc_bollinger_bands(df=ohlcv, period=bollinger_period, num_std_dev=bollinger_num_std_dev)
        
        # 가격이 볼린저 밴드 상단을 터치하였는가
        if ohlcv[f"upper_band{bollinger_period}_{bollinger_num_std_dev}"].iloc[-1] > ohlcv["close"].iloc[-1]:
            return False
        
        # 볼린저 %b가 1이상인가
        if ohlcv[f"bollinger_b{bollinger_period}_{bollinger_num_std_dev}"].iloc[-1] < 1:
            return False
        
        # mfi가 80이상인가
        mfi_peirod = 14
        ohlcv = trading.calc_mfi(df=ohlcv, period=mfi_peirod)
        if ohlcv[f'mfi{mfi_peirod}'].iloc[-1] < 80:
            return False
        
        return True
        
    def _log(self, content):
        now = datetime.now()
        now_str = now.strftime("[%Y-%m-%d %H:%M:%S]")
        print(now_str, content)