"""Fixed signed BTC cores on causal spot days, scoped to offline research."""
from bisect import bisect_right
from collections import deque
from contextlib import contextmanager
from decimal import Decimal as D
import hashlib
import json
from types import SimpleNamespace

DAY = 86400000
RULE = 'btc-history-signed-core-2018-2019-v1'
MODES = ('channel', 'ma')


def features(bars, mode):
    if mode not in MODES:
        raise ValueError('unknown registered history core')
    rows, direction = [], 0
    for i, (t, o, h, l, c) in enumerate(bars):
        before = bars[:i]
        if i >= 55 and mode == 'channel':
            if c > max(r[2] for r in before[-55:]):
                direction = 1
            elif c < min(r[3] for r in before[-55:]):
                direction = -1
            elif direction > 0 and c < min(r[3] for r in before[-20:]) or direction < 0 and c > max(r[2] for r in before[-20:]):
                direction = 0
        elif mode == 'ma' and i >= 99:
            fast = sum((r[4] for r in bars[i-19:i+1]), D(0))/20
            slow = sum((r[4] for r in bars[i-99:i+1]), D(0))/100
            direction = 1 if fast > slow else -1 if fast < slow else 0
        closes = [r[4] for r in bars[max(0, i-20):i+1]]
        returns = [b/a-1 for a, b in zip(closes, closes[1:])]
        rms = (sum((r*r for r in returns), D(0))/20).sqrt() if len(returns) == 20 else D(0)
        tr = [max(row[2]-row[3], abs(row[2]-bars[j-1][4]), abs(row[3]-bars[j-1][4]))
              for j, row in enumerate(bars[max(1, i-13):i+1], start=max(1, i-13))]
        atr = sum(tr, D(0))/14 if len(tr) == 14 else D(0)
        slow = sum((r[4] for r in bars[i-99:i+1]), D(0))/100 if i >= 99 else None
        rows.append(dict(available_ms=t+DAY+60000, day_ms=t, direction=direction,
                         rms=rms, atr=atr, close=c, slow=slow,
                         fraction=min(D(2), D('.60')/(rms*D(365).sqrt())) if rms and i >= 99 else D(0),
                         trail=max(D('.08'), min(D('.30'), 3*atr/c)) if atr else D('.30')))
    return rows


class Signals:
    def __init__(self, bars, mode, source_sha256):
        self.mode, self.source_sha256 = mode, source_sha256
        self.rows = features(bars, mode)
        self.times = [r['available_ms'] for r in self.rows]

    def at(self, call):
        i = bisect_right(self.times, call)-1
        return self.rows[i] if i >= 0 else None


def campaign_class(signals):
    """Reuse funded execution; the selected strategy class owns its checkpoints."""
    from coinquant.campaign import Campaign as Legacy
    from coinquant.core import Campaign as Continuous
    from coinquant.opportunities import Opportunity
    from coinquant.types import Blocked

    class HistoryCampaign(Continuous):
        mode = signals.mode
        core_rule = RULE+':'+signals.mode

        def __init__(self):
            super().__init__()
            self.signal_call = None
            self.signal_day = None
            self.trail = D('.30')

        def update(self, end, high, low, close):
            Legacy.update(self, end, high, low, close)
            if end % DAY == 0:
                self.closes.append(D(close))
            a = self.core_active
            if a is not None and self.position_campaign == a.identity:
                eligible = self.peak_after is not None and end-self.model.interval >= self.peak_after
                extreme = D(high if a.direction > 0 else low) if eligible else D(close)
                self.extreme = max(self.extreme, extreme) if a.direction > 0 else min(self.extreme, extreme)
                stop = self.extreme*(1-self.trail if a.direction > 0 else 1+self.trail)
                stop = max(a.stop, stop) if a.direction > 0 else min(a.stop, stop)
                self.core_active = Opportunity(a.identity, a.direction, stop, a.take, None)
            return self.core_active

        def select_macro(self, row, mark, call, *, bootstrap=False):
            if row is not None or type(call) is not int or not self.last <= call < self.last+self.model.interval:
                raise Blocked('history core needs its causal market boundary')
            feature = signals.at(call)
            if feature is None:
                raise Blocked('qualified completed spot history unavailable')
            self.signal_call, self.signal_day = call, feature['day_ms']
            self.target = feature['direction']*feature['fraction']
            self.trail = feature['trail']
            direction = 1 if self.target > 0 else -1 if self.target < 0 else 0
            old = self.core_active
            if not direction:
                self.core_active = None
            elif old is None or old.direction != direction:
                p = D(mark)
                if not p.is_finite() or p <= 0:
                    raise Blocked('invalid causal entry mark')
                self.extreme, self.peak_after = p, (call//self.model.interval+1)*self.model.interval
                self.base_take = p*(4 if direction > 0 else D('.25'))
                self.core_active = Opportunity(self.last, direction,
                    p*(1-self.trail if direction > 0 else 1+self.trail), self.base_take, None)
            self.macro_observation = None
            self.stop_crossed = bool(self.core_active and self.position_campaign is not None and
                (D(mark) <= self.core_active.stop if self.core_active.direction > 0 else D(mark) >= self.core_active.stop))

        def checkpoint(self):
            saved = super().checkpoint()
            saved['body']['core'].update(rule=self.core_rule, source_sha256=signals.source_sha256,
                signal_call=self.signal_call, signal_day=self.signal_day, trail=str(self.trail))
            saved['sha256'] = hashlib.sha256(json.dumps(saved['body'], sort_keys=True).encode()).hexdigest()
            return saved

        @classmethod
        def restore(cls, saved):
            try:
                body = dict(saved['body'])
                if hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest() != saved['sha256']:
                    raise ValueError('checkpoint digest')
                core = body.pop('core')
                if core['rule'] != cls.core_rule or core['mode'] != cls.mode or core['source_sha256'] != signals.source_sha256:
                    raise ValueError('history core input identity')
                stripped = dict(body=body, sha256=hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest())
                result = Legacy.restore.__func__(cls, stripped)
                result.closes = deque((D(v) for v in core['closes']), maxlen=64)
                if (len(result.closes) != min(64, (result.last-1575158400000)//DAY)
                        or any(not v.is_finite() or v <= 0 for v in result.closes)
                        or result.closes and result.closes[-1] != result.previous_daily):
                    raise ValueError('completed contract daily state')
                result.signal_call, result.signal_day = core['signal_call'], core['signal_day']
                result.target, result.trail = D(core['target']), D(core['trail'])
                if result.signal_call is not None:
                    f = signals.at(result.signal_call)
                    if (type(result.signal_call) is not int or not 1575158400000 < result.signal_call < result.last+result.model.interval
                            or f is None or f['day_ms'] != result.signal_day or result.target != f['direction']*f['fraction']
                            or result.trail != f['trail']):
                        raise ValueError('causal forecast binding')
                elif result.target or result.signal_day is not None:
                    raise ValueError('missing forecast clock')
                a = core['active']
                result.core_active = None if a is None else Opportunity(a['identity'], a['direction'], D(a['stop']), D(a['take']), None)
                if result.core_active:
                    geometry = (0 < result.core_active.stop < result.core_active.take if a['direction'] > 0
                                else 0 < result.core_active.take < result.core_active.stop)
                    if (a['direction'] not in (-1, 1) or a['direction']*result.target <= 0
                            or type(a['identity']) is not int or not 1575158400000 < a['identity'] <= result.last
                            or not geometry or not all(v.is_finite() for v in (result.core_active.stop, result.core_active.take))):
                        raise ValueError('owned strategy geometry')
                for key in ('extreme', 'base_take'):
                    setattr(result, key, None if core[key] is None else D(core[key]))
                result.peak_after, result.stop_crossed = core['peak_after'], core['stop_crossed']
                if (type(result.stop_crossed) is not bool or any(v is not None and (not v.is_finite() or v <= 0)
                        for v in (result.extreme, result.base_take)) or result.peak_after is not None and
                        (type(result.peak_after) is not int or result.peak_after % result.model.interval)):
                    raise ValueError('fill-owned protection state')
                return result
            except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
                raise Blocked('incompatible history core checkpoint; no automatic reset') from exc

    return HistoryCampaign


@contextmanager
def runtime(signals):
    from coinquant import linear_preview, session
    from coinquant.types import Blocked
    old = linear_preview.Campaign
    linear_preview.Campaign = campaign_class(signals)

    def run(config, reader, **kwargs):
        if not getattr(reader, 'offline', False):
            raise Blocked('history core execution requires an offline research venue')
        return session.run(config, reader, **kwargs)

    def cycle(reader, *args, **kwargs):
        if not getattr(reader, 'offline', False):
            raise Blocked('history core execution requires an offline research venue')
        return session.cycle(reader, *args, **kwargs)

    try:
        yield SimpleNamespace(run=run, cycle=cycle)
    finally:
        linear_preview.Campaign = old
