"""Original measurement venue only; current production strategy is imported directly."""
from datetime import datetime, timezone
from decimal import Decimal as D
import hashlib
import json
from coinquant.types import Unknown
from research.session_exchange import SessionExchange
DAY=86400000
# Per-process evidence stream, opened by the registered driver. It observes
# existing points only and is deliberately outside serialized venue state.
PATH_TRACE = None
class ResearchExchange(SessionExchange):
    def __init__(self, *args, fx, initial_cny=D(10000), terminal_ms=None, **kwargs):
        self.terminal_ms = terminal_ms
        self.initial_cny = D(initial_cny)
        if not self.initial_cny.is_finite() or self.initial_cny <= 0:
            raise ValueError("initial CNY must be positive and finite")
        self._initial_peak_pending = True
        self._path_audit = dict(version='readonly-path-audit-v1', count=0,
            rolling_sha256='0'*64, first=None, last=None, unqualified_close_count=0,
            envelope=dict(peak_cny=self.initial_cny, peak_at_ms=None, mdd=D(0), mdd_point=None),
            close=dict(peak_cny=self.initial_cny, peak_at_ms=None, mdd=D(0), mdd_point=None))
        # Initial metric point must use the same prior FX and exit conversion.
        self.fx, self.exit_conversion = fx, D('.001')
        self.daily = {}
        super().__init__(*args, **kwargs)

    def _record(self, cny, kind):
        if self._initial_peak_pending:
            self.peak_cny = self.peak_envelope_cny = self.initial_cny
            self._initial_peak_pending = False
        super()._record(cny, kind)
        # Independent summary of the same measurement points; never feeds execution.
        audit = self._path_audit
        point = dict(stamp_ms=self.now_ms, equity_cny=cny, kind=kind,
                     known_path=self.known_path)
        encoded = json.dumps([self.now_ms, kind, str(cny), self.known_path],
                             separators=(',', ':')).encode()
        audit['rolling_sha256'] = hashlib.sha256(
            bytes.fromhex(audit['rolling_sha256']) + encoded).hexdigest()
        audit['count'] += 1
        if audit['first'] is None:
            audit['first'] = point
        audit['last'] = point
        if kind == 'close' and not self.known_path:
            audit['unqualified_close_count'] += 1
        for series in ('envelope', 'close'):
            if series == 'close' and kind != 'close':
                continue
            summary = audit[series]
            if cny > summary['peak_cny']:
                summary['peak_cny'], summary['peak_at_ms'] = cny, self.now_ms
            if kind == 'favorable' or (series == 'close' and not self.known_path):
                continue
            drawdown = D(1) - cny / summary['peak_cny']
            if drawdown > summary['mdd']:
                summary['mdd'] = drawdown
                summary['mdd_point'] = dict(point, peak_cny=summary['peak_cny'],
                                           peak_at_ms=summary['peak_at_ms'])
        if PATH_TRACE is not None:
            PATH_TRACE.write(json.dumps([
                audit['count'], self.now_ms, kind, str(cny), self.known_path,
                str(self.q), str(self.entry), str(self.wallet), str(self.margin),
                str(self.fx(self.now_ms)),
            ], separators=(',', ':'), allow_nan=False) + '\n')

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

