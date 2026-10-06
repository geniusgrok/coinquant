"""Original measurement venue only; current production strategy is imported directly."""
from datetime import datetime, timezone
from decimal import Decimal as D
from coinquant.types import Unknown
from research.session_exchange import SessionExchange
DAY=86400000
class ResearchExchange(SessionExchange):
    def __init__(self, *args, fx, initial_cny=D(10000), terminal_ms=None, **kwargs):
        self.terminal_ms = terminal_ms
        self.initial_cny = D(initial_cny)
        if not self.initial_cny.is_finite() or self.initial_cny <= 0:
            raise ValueError("initial CNY must be positive and finite")
        self._initial_peak_pending = True
        # Initial metric point must use the same prior FX and exit conversion.
        self.fx, self.exit_conversion = fx, D('.001')
        self.daily = {}
        super().__init__(*args, **kwargs)

    def _record(self, cny, kind):
        if self._initial_peak_pending:
            self.peak_cny = self.peak_envelope_cny = self.initial_cny
            self._initial_peak_pending = False
        super()._record(cny, kind)

    def capture(self, stamp, price=None):
        if self.q and price is None:
            return
        price = D(price or 0)
        equity = self.wallet + (self.q*(price-self.entry) if self.q else D(0))
        # Closing boundary belongs to the day that just finished.
        day = (stamp-1)//DAY if stamp % DAY == 0 else stamp//DAY
        self.daily[day] = {'date': datetime.fromtimestamp(day*DAY/1000, timezone.utc).date().isoformat(), 'stamp_ms': stamp,
            'equity_usdt': str(equity), 'equity_cny': str(equity*self.fx(stamp)*(1-self.exit_conversion)),
            'wallet_usdt': str(self.wallet), 'quantity_btc': str(self.q), 'mark_usdt': str(price),
            'net_btc_exposure_usdt': str(self.q*price), 'gross_btc_exposure_usdt': str(abs(self.q)*price),
            'fees_usdt': str(self.fees), 'funding_paid_usdt': str(self.funding_paid)}

    def _note_cash(self):
        super()._note_cash()
        if not self.q:
            self.capture(self.now_ms)

    def _on_minute(self, open_ms):
        super()._on_minute(open_ms)
        if (open_ms+60000) % DAY == 0:
            row = self.market.minute('mark', open_ms) or self.market.minute('trade', open_ms)
            if row is not None:
                self.capture(open_ms+60000, row[3])

    def _partial(self, open_ms, at_boundary):
        super()._partial(open_ms, at_boundary)
        if at_boundary and (open_ms+60000) % DAY == 0:
            row = self.market.minute('mark', open_ms) or self.market.minute('trade', open_ms)
            if row is not None:
                self.capture(open_ms+60000, row[3])

    def _pay_funding(self, start_ms, end_ms):
        terminal = self.terminal_ms is not None and end_ms == self.terminal_ms
        super()._pay_funding(start_ms, end_ms-1 if terminal else end_ms)
        if terminal and self.q:
            # Value the closing boundary without the next day's settlement.
            row = self.market.minute('mark', end_ms-60000)
            if row is None:
                raise Unknown('official terminal mark missing')
            self.now_ms = end_ms
            self._note(row[3], 'close')
        if self.q and end_ms % DAY == 0 and self.now_ms == end_ms:
            row = self.market.minute('mark', end_ms-60000)
            if row is not None:
                self.capture(end_ms, row[3])

