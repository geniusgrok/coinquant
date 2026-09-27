"""Strategies for the screening account. Production signal code where it exists."""
from decimal import Decimal as D

import numpy as np

from coinquant.campaign import Campaign
from research.screen import Order, FOUR


_H4 = None


def decimal_h4(root='/data/coinquant-market'):
    """Exact Decimal 4h bars from the verified vision set (same as the meter)."""
    global _H4
    if _H4 is None:
        from research.session_market import load_base
        _H4 = sorted(load_base(root).h4.items())
    return _H4


class ProductionCampaign:
    """Feeds completed 4h bars into the production Campaign and follows its
    enter/hold/exit disposition. `side` limits new entries as the session does.
    DFII10 is off here (screening of the price model only)."""

    def __init__(self, data, mechanism='impulse_hold', risk=None, side='long', friction='.0011', macro=False):
        self.data = data
        self.macro = None
        if macro:
            from research.dfii10_history import History
            self.macro = History()
        self.started = False
        self.model = Campaign(mechanism)
        self.fed = 0
        self.risk = risk
        self.side = side
        self.friction = friction
        self.owned = None
        # warmup bars start at the campaign origin
        self.times = data.h4_time

    def _catch_up(self, rows):
        h4 = decimal_h4()
        while self.fed < rows:
            t, (o, h, l, c, v) = h4[self.fed]
            self.model.update(t + FOUR, h, l, c)
            self.fed += 1

    def __call__(self, data, view, state):
        self._catch_up(view['h4_rows'])
        if not self.started:
            self._first = view['n']
        m = self.model
        if not self.started:
            # production cold start: an already active campaign is consumed
            self.started = True
            m.consumed = m.primary_consumed = m.model.active.identity if m.model.active else None
        if self.macro is not None:
            m.select_macro(self.macro.snapshot(view['time']), D(str(float(view['mark']))), int(view['time']),
                           bootstrap=view['n'] == self._first)
        if not view['q'] and self.owned is not None:
            self.owned = None
            m.position_campaign = None
        quantity = D(str(float(view['q']))) if view['q'] else D(0)
        if quantity and m.position_campaign is None:
            m.position_campaign = self.owned
        action = m.action(quantity, self.side)
        if action == 'enter':
            opp = m.active
            fraction = float(m.fraction(self.risk, self.friction)) if self.risk else float(m.entry_fraction(self.friction))
            if fraction <= 0:
                return None
            if opp is m.macro_opportunity:
                price = view['price']
                if price <= float(opp.stop):
                    return None
                fraction = min(fraction, 0.03 * price / (price - float(opp.stop)))
            m.filled(opp.identity)
            self.owned = opp.identity
            return Order(opp.direction * fraction, stop=float(opp.stop), take=float(opp.take))
        if action == 'exit':
            m.position_campaign = None
            self.owned = None
            return Order(0.0)
        if action == 'hold':
            return Order(0, keep=True)
        return None
