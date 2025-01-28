'''
sudden rise agent
급등하는 코인을 찾아 매수후 고점에서 매도하는 에이전트
'''
import numpy as np
from ata.agent.baseagent import BaseAgent
from ata.utils.markerorderpriceunit import upbit_price_unit
from ata.utils import trade

class SRAgent(BaseAgent):
    def _is_buy_timing(self, item) -> bool:
        ohlcv_1h = self.exchange.get_ohlcv_per_1h(item)
        ohlcv_1h, keys = trade.calc_bollinger_bands(ohlcv_1h, 20, 2)
        upper_key = keys['upper_key']
        lower_key = keys['lower_key']
        b_key = keys['b_key']
        ohlcv_1h, mfi_key = trade.calc_mfi(ohlcv_1h, 14)
        if (
            ohlcv_1h[mfi_key].iloc[-2] < 20 and
            ohlcv_1h[b_key].iloc[-2] < 0
        ):
            return True
        else:
            return False
    
    def _is_sell_timing(self, item) -> bool:
        ohlcv_1h = self.exchange.get_ohlcv_per_1h(item)
        ohlcv_1h, keys = trade.calc_bollinger_bands(ohlcv_1h, 20, 2)
        upper_key = keys['upper_key']
        lower_key = keys['lower_key']
        b_key = keys['b_key']
        ohlcv_1h, mfi_key = trade.calc_mfi(ohlcv_1h, 14)
        prev_mfi = ohlcv_1h[mfi_key].iloc[-2] if ohlcv_1h[mfi_key].iloc[-2] != 80 else ohlcv_1h[mfi_key].iloc[-3]
        if (
            prev_mfi > 80 and
            (80 - ohlcv_1h[mfi_key].iloc[-1]) * (80 - prev_mfi) <= 0
        ):
            return True
        else:
            return False
    
    def _get_buying_candidates(self) -> set:
        buying_candidates = set()
        buying_candidates.add('BTC')
        if not self.only_btc:
            tickers = self.exchange.get_tickers()
            symbols = tickers.keys()
            krw_symbols = [x for x in symbols if x.endswith('KRW')]
            for symbol in krw_symbols:
                if symbol in ['BTC/KRW', 'ETH/KRW', 'XRP/KRW']:
                    continue
                ticker = tickers[symbol]
                percentage = ticker['percentage']
                if float(ticker['info']['acc_trade_price_24h']) > 100000000000 and percentage >= 0.01:
                    buying_candidates.add(symbol.split('/')[0])
        return buying_candidates
    
    def _calc_values_for_buy_order(self, item) -> tuple[float, float, float]:
        '''
        return buy_price, buy_amount_item, buy_amount_krw
        '''
        curr_price = self.exchange.get_current_price(item)
        buy_price = curr_price - upbit_price_unit(item, curr_price) * max(2 + self._calc_buy_skip_criterion(item) - self.trading_data[item]['buy_cnt'], 0)
        buy_amount_krw = min(self.exchange.get_total_balance() / 5 * (self.trading_data[item]['buy_cnt'] - self._calc_buy_skip_criterion(item)), self.exchange.balance['KRW']['free'] - 100)
        buy_amount_item = buy_amount_krw / buy_price
        return buy_price, buy_amount_item, buy_amount_krw
    
    def _calc_values_for_sell_order(self, item) -> tuple[float, float, float]:
        '''
        return sell_price, sell_amount_item, sell_amount_krw
        '''
        curr_price = self.exchange.get_current_price(item)
        sell_price = curr_price + upbit_price_unit(item, curr_price) * max(0, 2 - self.trading_data[item]['sell_cnt'])
        denominator = 2.0
        weight = min(denominator, self.trading_data[item]['sell_cnt']) / denominator
        sell_amount_item = self.exchange.balance[item]['free'] * weight
        sell_amount_krw = sell_amount_item * sell_price
        return sell_price, sell_amount_item, sell_amount_krw
    
    def _calc_buy_skip_criterion(self, item) -> int:
        return np.median(self.trading_data[item]['buy_cnt_histories']) - 1
    
    def _calc_sell_skip_criterion(self, item) -> int:
        return 0