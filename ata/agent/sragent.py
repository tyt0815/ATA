'''
sudden rise agent
급등하는 코인을 찾아 매수후 고점에서 매도하는 에이전트
'''

from ata.agent.baseagent import BaseAgent

class SRAgent(BaseAgent):
    def _is_buy_timing(self, item) -> bool:
        pass
    
    def _is_sell_timing(self, item) -> bool:
        pass
    
    def _get_buying_candidates(self) -> set:
        pass
    
    def _calc_values_for_buy_order(self, item) -> tuple[float, float, float]:
        '''
        return buy_price, buy_amount_item, buy_amount_krw
        '''
        pass
    
    def _calc_values_for_sell_order(self, item) -> tuple[float, float, float]:
        '''
        return sell_price, sell_amount_item, sell_amount_krw
        '''
        pass
    
    def _calc_buy_skip_criterion(self, item) -> int:
        pass
    
    def _calc_sell_skip_criterion(self, item) -> int:
        pass