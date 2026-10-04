"""Causal/money failure checks for continuous route decisions."""
from decimal import Decimal as D
import unittest

from research.continuous_routes import fit, risk_gate, stress
from research.flow_risk import DAY, START


class ContinuousRouteChecks(unittest.TestCase):
    def test_risk_reduction_may_sacrifice_profit_but_must_beat_simple_control(self):
        events = [dict(time_ms=START if i<5 else START+3*365*DAY, closed=True,
                       notional=D(100), removed_downside_usdt=D(20), gain=D(-1)) for i in range(10)]
        control = [dict(e, removed_downside_usdt=D(5)) for e in events]
        self.assertEqual(risk_gate(events, control)['status'], 'RISK_ACCOUNT_ENTRANT')
        self.assertEqual(risk_gate(events, events)['status'], 'REJECT_RISK_TRADEOFF')

    def test_pre_entry_and_post_exit_lows_never_count_as_owned_loss(self):
        event = dict(time_ms=START+3600000, mark=D(100), removed=D(1))
        detail = dict(trades=[dict(side='SELL',time=START+2*DAY+3600000,qty='1',price='110')])
        bars = {START:(D(100),D(100),D(1),D(100)), START+DAY:(D(100),D(100),D(90),D(100)),
                START+2*DAY:(D(100),D(100),D(2),D(100))}
        self.assertEqual(stress(detail,event,bars,'coin'),(D(10),1))

    def test_regression_without_both_flag_states_never_qualifies(self):
        self.assertFalse(fit([dict(veto=False) for _ in range(10)])['identifiable'])

