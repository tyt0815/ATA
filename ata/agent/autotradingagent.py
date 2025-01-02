import traceback

from ata.algorithm import trading
from ata.exchange.baseexchange import BaseExchange
from ata.utils.log import log, save_log

class AutoTradingAgent:
    def __init__(
        self,
        exchange:BaseExchange
        ):
        self.exchange = exchange
        
    def run(self):
        log('run ATA...')
        buy_cnt = {}
        # 거래 루프
        self.exchange.init()
        log('trading start')
        while True:
            try:
                if self.exchange.update() == False:
                    break
                # 매수 주문 넣기
                buying_candidates = self.exchange.get_buying_candidates()
                for target in buying_candidates:
                    ohlcv = self.exchange.get_ohlcv_per_1m(target)
                    if ohlcv is None:
                        continue
                    if self.exchange.balance['KRW']['total'] > 0 and self._is_buy_timing(ohlcv):
                        curr_price = self.exchange.get_current_price(item=target)
                        if not target in buy_cnt:
                            buy_cnt[target] = 1
                        krw = min(max(6000, self.exchange.get_total_balance() / 5 * buy_cnt[target]), self.exchange.balance['KRW']['free'])
                        if krw > 6000:
                            buy_cnt[target] += 1
                            buy_order_id = self.exchange.create_buy_order_at_market_price(item=target, amount_krw=krw)
                            buy_order = self.exchange.get_order(buy_order_id)
                            log(f'Buy  {target} at {buy_order["price"]}(amount: {krw}, total: {self.exchange.get_total_balance()}) Debug - buy_cnt["{target}"] = {buy_cnt[target]}')
            except Exception as e:
                log_path = './log'
                log(str(e))
                save_log(content=traceback.format_exc(), file_path=log_path)
                self.exchange.init()
                
            try:
                # 매도 주문 넣기
                selling_candidates = self.exchange.balance
                for target in selling_candidates:
                    ohlcv = self.exchange.get_ohlcv_per_1m(target)
                    if ohlcv is None:
                        continue
                    if self.exchange.balance[target]['total'] > 0 and (self._is_sell_timing(ohlcv) or self.exchange.is_plunge(item=target)):
                        curr_price = self.exchange.get_current_price(item=target)
                        amount_item = self.exchange.balance[target]['free']
                        krw = curr_price * amount_item
                        if krw > 6000:
                            sell_order_id = self.exchange.create_sell_all_order_at_market_price(item=target)
                            sell_order = self.exchange.get_order(sell_order_id)
                            log(f'Sell {target} at {sell_order["price"]}({self.exchange.get_total_balance()})')
                            buy_cnt[target] = 1
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