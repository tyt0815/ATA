'''
low-high agent
1분봉으로 최저가 매수, 최고가 매도하는 에이전트
'''
import numpy as np

from ata.agent.baseagent import BaseAgent
from ata.utils.markerorderpriceunit import upbit_price_unit
from ata.utils import trade

class LHAgent(BaseAgent):
    def _is_buy_timing(self, item) -> bool:
        ohlcv_per_1m = self.exchange.get_ohlcv_per_1m(item)
        return trade.check_oversold_by_bollinger_mfi(ohlcv_per_1m)
    
    def _is_sell_timing(self, item) -> bool:
        ohlcv_per_1m = self.exchange.get_ohlcv_per_1m(item)
        return trade.check_overbought_by_bollinger_mfi(ohlcv_per_1m)
    
    def _get_buying_candidates(self) -> set:
        buying_candidates = set()
        buying_candidates.add('BTC')
        if not self.only_btc:
            tickers = self.exchange.get_tickers()
            symbols = tickers.keys()
            krw_symbols = [x for x in symbols if x.endswith('KRW')]
            low_percentage = -0.05
            high_percentage = 0.05
            for symbol in krw_symbols:
                if symbol == 'BTC/KRW':
                    continue
                ticker = tickers[symbol]
                percentage = ticker['percentage']
                if float(ticker['info']['acc_trade_price_24h']) > 100000000000 and percentage >= low_percentage and percentage < high_percentage:
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
    
    