'''
sudden rise agent
급등하는 코인을 찾아 매수후 고점에서 매도하는 에이전트
'''
import time
import numpy as np
from ata.agent.baseagent import BaseAgent
from ata.utils.markerorderpriceunit import upbit_price_unit
from ata.utils import trade


class SRAgent(BaseAgent):
    def _is_buy_timing(self, item) -> bool:
        ohlcv_1m = self.exchange.get_ohlcv_per_1m(item)
        # ohlcv_1m, keys = trade.calc_bollinger_bands(ohlcv_1m, 20, 2)
        # upper_key = keys['upper_key']
        # lower_key = keys['lower_key']
        # b_key = keys['b_key']
        # ohlcv_1m, mfi_key = trade.calc_mfi(ohlcv_1m)
        volume_mean = np.mean(ohlcv_1m['volume'].iloc[-6:-1])
        volume_rise_rate = ohlcv_1m['volume'].iloc[-1] / volume_mean
        price_rise_rate = ohlcv_1m['close'].iloc[-1] / ohlcv_1m['close'].iloc[-2]
        order_book = self.exchange.get_order_book(item)
        # 매수벽
        bid_volume = sum(bid[1] for bid in order_book["bids"])
        # 매도벽
        ask_volume = sum(ask[1] for ask in order_book["asks"])
        if (
            volume_rise_rate >= 3
            and price_rise_rate >= 1.02
            and bid_volume > ask_volume * 3
        ):
            return True
        return False
    
    def _is_sell_timing(self, item) -> bool:
        order_book = self.exchange.get_order_book(item)
        # 매수벽
        bid_volume = sum(bid[1] for bid in order_book["bids"])
        # 매도벽
        ask_volume = sum(ask[1] for ask in order_book["asks"])
        if(
            bid_volume < ask_volume * 1.5
        ):
            return True
        return False
    
    def _get_buying_candidates(self) -> set:
        buying_candidates = set()
        buying_candidates.add('BTC')
        if not self.only_btc:
            tickers = self.exchange.get_tickers()
            symbols = tickers.keys()
            krw_symbols = [x for x in symbols if x.endswith('KRW')]
            for symbol in krw_symbols:
                if symbol in ['BTC/KRW']:
                    continue
                ticker = tickers[symbol]
                percentage = ticker['percentage']
                if float(ticker['info']['acc_trade_price_24h']) > 5000000000:
                    buying_candidates.add(symbol.split('/')[0])
        return buying_candidates
    
    def _calc_values_for_buy_order(self, item) -> tuple[float, float, float]:
        '''
        return buy_price, buy_amount_item, buy_amount_krw
        '''
        curr_price = self.exchange.get_current_price(item)
        buy_price = curr_price
        buy_amount_krw = self.exchange.balance['KRW']['free'] * 0.94
        buy_amount_item = buy_amount_krw / buy_price
        return None, buy_amount_item, buy_amount_krw
    
    def _calc_values_for_sell_order(self, item) -> tuple[float, float, float]:
        '''
        return sell_price, sell_amount_item, sell_amount_krw
        '''
        curr_price = self.exchange.get_current_price(item)
        # sell_price = max(curr_price, self.trading_data[item]['buy_price_avg'])
        # sell_price *= 1.1
        sell_price = curr_price
        sell_amount_item = self.exchange.balance[item]['free']
        sell_amount_krw = sell_amount_item * sell_price
        return None, sell_amount_item, sell_amount_krw
    
    def _calc_buy_skip_criterion(self, item) -> int:
        # return np.median(self.trading_data[item]['buy_cnt_histories']) - 1
        return 0
    
    def _calc_sell_skip_criterion(self, item) -> int:
        return 0