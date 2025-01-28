'''
sudden rise agent
급등하는 코인을 찾아 매수후 고점에서 매도하는 에이전트
'''

from ata.agent.baseagent import BaseAgent
from ata.utils import trade

class SRAgent(BaseAgent):
    def _is_buy_timing(self, item) -> bool:
        ohlcv_15m = self.exchange.get_ohlcv_per_15m(item)
        boll_period = 20
        boll_std = 2
        
        ohlcv_15m, keys = trade.calc_bollinger_bands(ohlcv_15m, boll_period, boll_std)
        upper_key = keys['upper_key']
        lower_key = keys['lower_key']
        b_key = keys['b_key']
        
        # 가격이 볼린저 밴드 상단을 터치치하였는가
        if ohlcv_15m[upper_key].iloc[-1] >= ohlcv_15m["close"].iloc[-1]:
            return False
        
        # 볼린저 %b가 0이상인가
        # if ohlcv_15m[b_key].iloc[-1] < 0:
        #     return False
        
        # mfi가 85 이상인가
        mfi_period = 14
        ohlcv_15m, mfi_key = trade.calc_mfi(ohlcv_15m, period=mfi_period)
        if ohlcv_15m[mfi_key].iloc[-1] < 85:
            return False
        
        return True
    
    def _is_sell_timing(self, item) -> bool:
        ohlcv_15m = self.exchange.get_ohlcv_per_15m(item)
        boll_period = 20
        boll_std = 2
        
        ohlcv_15m, keys = trade.calc_bollinger_bands(ohlcv_15m, boll_period, boll_std)
        upper_key = keys['upper_key']
        lower_key = keys['lower_key']
        b_key = keys['b_key']
        
        # 가격이 볼린저 밴드 상단에 닿지 못하는가
        if ohlcv_15m[upper_key].iloc[-1] < ohlcv_15m["close"].iloc[-1]:
            return False
        
        # 볼린저 %b가 0이상인가
        # if ohlcv_15m[b_key].iloc[-1] < 0:
        #     return False
        
        # mfi가 80 이하인가
        mfi_period = 14
        ohlcv_15m, mfi_key = trade.calc_mfi(ohlcv_15m, period=mfi_period)
        if ohlcv_15m[mfi_key].iloc[-1] > 80:
            return False
        
        return True
    
    def _get_buying_candidates(self) -> set:
        buying_candidates = set()
        buying_candidates.add('BTC')
        if not self.only_btc:
            tickers = self.exchange.get_tickers()
            symbols = tickers.keys()
            krw_symbols = [x for x in symbols if x.endswith('KRW')]
            for symbol in krw_symbols:
                if symbol == 'BTC/KRW':
                    continue
                ticker = tickers[symbol]
                if float(ticker['info']['acc_trade_price_24h']) > 100000000000:
                    buying_candidates.add(symbol.split('/')[0])
        return buying_candidates
    
    def _calc_values_for_buy_order(self, item) -> tuple[float, float, float]:
        '''
        return buy_price, buy_amount_item, buy_amount_krw
        '''
        buy_price = self.exchange.get_current_price(item)
        buy_amount_krw = self.exchange.balance['KRW']['free']
        buy_amount_item = buy_amount_krw / buy_price
        return buy_price, buy_amount_item, buy_amount_krw
    
    def _calc_values_for_sell_order(self, item) -> tuple[float, float, float]:
        '''
        return sell_price, sell_amount_item, sell_amount_krw
        '''
        sell_price = self.exchange.get_current_price(item)
        sell_amount_item = self.exchange.balance[item]['free']
        sell_amount_krw = sell_price * sell_amount_item
        return sell_price, sell_amount_item, sell_amount_krw
    
    def _calc_buy_skip_criterion(self, item) -> int:
        return 0
    
    def _calc_sell_skip_criterion(self, item) -> int:
        return 0