"""USDT linear account arithmetic; economic rules remain explicit proxy assumptions."""
from dataclasses import dataclass
from decimal import Decimal as D
from .types import ZERO, Blocked

FEE = D('.00075')
MMR = D('.005')
LOT = D('.0001')  # hypothetical linear BTC quantity precision, NOT dated OKX fact
TICK = D('.5')


@dataclass
class Account:
    wallet: D
    q: D = ZERO
    entry: D = ZERO
    margin: D = ZERO
    sl: D = ZERO
    tp: D = ZERO
    fees: D = ZERO
    funding: D = ZERO

    def equity(self, mark):
        return self.wallet + self.q * (mark - self.entry)

    def liquidation(self, maintenance=MMR, fee=FEE):
        if not self.q:
            raise Blocked('liquidation requires a position')
        return (self.q * self.entry - self.margin) / (self.q - abs(self.q) * (maintenance + fee))

    def open(self, q, price, sl, tp):
        if self.q or not q or min(price, sl, tp) <= 0:
            raise Blocked('invalid linear entry')
        if not ((q > 0 and sl < price < tp) or (q < 0 and tp < price < sl)):
            raise Blocked('unsafe linear protection')
        margin = abs(q) * price / 20
        fee = abs(q) * price * FEE
        if margin + 2 * fee > self.wallet:
            raise Blocked('insufficient linear initial margin')
        self.wallet -= fee; self.fees += fee
        self.q, self.entry, self.margin, self.sl, self.tp = q, price, margin, sl, tp

    def close(self, amount, price):
        if amount <= 0 or amount > abs(self.q) or price <= 0:
            raise Blocked('invalid linear reduction')
        delta = amount if self.q > 0 else -amount
        fee = amount * price * FEE
        self.wallet += delta * (price - self.entry) - fee
        self.fees += fee
        self.margin *= 1 - amount / abs(self.q)
        self.q -= delta
        if not self.q:
            self.entry = self.margin = self.sl = self.tp = ZERO

    def pay_funding(self, mark, rate):
        self.apply_funding_cost(self.q * mark * rate)

    def apply_funding_cost(self, cost):
        """Post an actual or explicitly bounded settlement, including collateral draw."""
        if not cost.is_finite():
            raise ValueError('nonfinite funding cashflow')
        self.wallet -= cost; self.funding += cost
        if self.q and self.wallet < self.margin:
            self.margin = max(ZERO, self.wallet)
