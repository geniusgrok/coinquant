"""One causal daily trend campaign, independent of exchange/account mutations.

M60 is research-only. A market checkpoint never establishes position ownership.
The execution caller freezes protection when a fill is confirmed, not here.
"""
from collections import deque
from dataclasses import dataclass
from decimal import Decimal as D
import hashlib
import json

from .campaign import disposition
from .linear_sizing import target_fraction
from .types import Blocked, ZERO

DAY = 86_400_000
PUBLICATION_LAG = 60_000
HORIZONS = (7, 28, 84)


def published_daily_key(now):
    """Latest UTC day close whose fixed publication lag has elapsed."""
    if type(now) is not int:
        raise ValueError("integer invocation timestamp required")
    return (now-PUBLICATION_LAG)//DAY*DAY+PUBLICATION_LAG


def direction_score(closes):
    """The preregistered normalized log-return score; no partial-scale fallback."""
    values = tuple(D(x) for x in closes)
    if any(not x.is_finite() or x <= 0 for x in values):
        raise ValueError('invalid daily close')
    if len(values) < 85:
        return None, ()
    values = values[-85:]
    returns = tuple((b / a).ln() for a, b in zip(values, values[1:]))
    components = []
    for h in HORIZONS:
        scale = sum((r*r for r in returns[-h:]), ZERO).sqrt()
        component = (values[-1]/values[-h-1]).ln()/scale if scale else ZERO
        components.append(max(D(-1), min(D(1), component)))
    return sum(components, ZERO)/3, tuple(components)


@dataclass(frozen=True)
class TrendOpportunity:
    """No synthetic take price: non-impulse TP requires the invocation quote."""
    identity: int
    stop: D
    direction: int = 1
    entry_limit: None = None


@dataclass(frozen=True)
class TrendSnapshot:
    bar_end: int
    available_at: int
    score: D | None
    components: tuple
    opportunity: TrendOpportunity | None
    fraction: D

    def record(self):
        return dict(bar_end=self.bar_end, available_at=self.available_at,
                    score=str(self.score) if self.score is not None else None,
                    components=[str(x) for x in self.components],
                    campaign=self.opportunity.identity if self.opportunity else None,
                    stop=str(self.opportunity.stop) if self.opportunity else None,
                    fraction=str(self.fraction))


class MultiscaleCampaign:
    """Reconstruct daily market state; consume only explicitly confirmed fills."""
    def __init__(self):
        self.bars = deque(maxlen=85)
        self.active_since = None
        self.consumed = None
        self.position_campaign = None
        self.snapshot = None
        self.friction = ZERO

    def update(self, end, high, low, close, friction=ZERO):
        high, low, close, friction = map(D, (high, low, close, friction))
        if (type(end) is not int or end <= 0 or end % DAY
                or (self.bars and end != self.bars[-1][0]+DAY)):
            raise ValueError('daily data gap/order; backfill before adding risk')
        if (not all(x.is_finite() for x in (high, low, close, friction))
                or not ZERO < low <= close <= high or friction < 0):
            raise ValueError('invalid completed daily data')
        bars = (list(self.bars)+[(end, high, low, close)])[-85:]
        closes = [b[3] for b in bars]
        score, components = direction_score(closes)
        positive = score is not None and score > 0
        active = self.active_since if positive else None
        if positive and active is None:
            active = end+PUBLICATION_LAG
        opportunity = TrendOpportunity(active, min(b[2] for b in bars[-10:])) if positive else None
        returns = [b/a-1 for a, b in zip(closes, closes[1:])]
        fraction = target_fraction(returns, friction) if score is not None else ZERO
        snapshot = TrendSnapshot(end, end+PUBLICATION_LAG, score, components, opportunity, fraction)
        # All validation/calculation precedes mutation: bad input is not a reversal.
        self.bars = deque(bars, maxlen=85)
        self.active_since, self.snapshot, self.friction = active, snapshot, friction
        return snapshot

    def visible(self, now):
        if self.snapshot is None or self.snapshot.available_at > now:
            raise Blocked('daily snapshot not published at this invocation')
        return self.snapshot

    def action(self, quantity, now):
        snapshot = self.visible(now)
        if quantity and self.position_campaign is None:
            raise Blocked('position ownership is unknown; market state cannot recover fills')
        identity = self.position_campaign if quantity else self.consumed
        return disposition(snapshot.opportunity, quantity, identity, 'long')

    def filled(self, identity):
        if type(identity) is not int or self.active_since is None or identity != self.active_since:
            raise Blocked('confirmed fill does not belong to the visible campaign')
        if self.position_campaign not in (None, identity):
            raise Blocked('another position campaign is still unresolved')
        self.consumed = self.position_campaign = identity

    def closed(self):
        self.position_campaign = None

    def checkpoint(self):
        body = dict(model='M60', version=1, friction=str(self.friction),
                    bars=[[t, str(h), str(l), str(c)] for t,h,l,c in self.bars],
                    active_since=self.active_since, consumed=self.consumed,
                    position_campaign=self.position_campaign,
                    snapshot=self.snapshot.record() if self.snapshot else None)
        return dict(body=body, sha256=hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest())

    @classmethod
    def restore(cls, saved):
        try:
            body = saved['body']
            if (body['model'] != 'M60' or body['version'] != 1 or
                    saved['sha256'] != hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()):
                raise ValueError('model/version/checksum mismatch')
            result = cls()
            if not 0 <= len(body['bars']) <= 85:
                raise ValueError('invalid history length')
            # Rebuild price-derived state, but retain the durable historical identity:
            # its first positive day can be older than the rolling 85-bar window.
            for end, high, low, close in body['bars']:
                result.update(end, high, low, close, body['friction'])
            snapshot = body['snapshot']
            if (snapshot is None) != (not result.bars):
                raise ValueError('missing market snapshot')
            for name in ('active_since', 'consumed', 'position_campaign'):
                value = body[name]
                if value is not None and (type(value) is not int or not result.bars
                        or value <= 0 or value % DAY != PUBLICATION_LAG
                        or value > result.snapshot.available_at):
                    raise ValueError('invalid campaign identity')
                setattr(result, name, value)
            if result.position_campaign is not None and result.position_campaign != result.consumed:
                raise ValueError('ownership mismatch')
            if snapshot is not None:
                actual = result.snapshot.record()
                if any(snapshot[k] != actual[k] for k in ('bar_end','available_at','score','components','stop','fraction')):
                    raise ValueError('market state mismatch')
                if (result.active_since is not None) != (result.snapshot.score is not None and result.snapshot.score > 0):
                    raise ValueError('campaign direction mismatch')
                if snapshot['campaign'] != result.active_since:
                    raise ValueError('snapshot identity mismatch')
                fraction = D(snapshot['fraction'])
                if not fraction.is_finite() or fraction < 0:
                    raise ValueError('invalid fraction')
                op = TrendOpportunity(result.active_since, result.snapshot.opportunity.stop) if result.active_since else None
                result.snapshot = TrendSnapshot(result.snapshot.bar_end, result.snapshot.available_at,
                    result.snapshot.score, result.snapshot.components, op, fraction)
            return result
        except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
            raise Blocked('invalid M60 checkpoint; do not reset account or campaign') from exc


def daily_snapshots(warm, trade, start, end, friction, extra_daily=()):
    """Causally fold verified hourly originals into completed UTC daily bars."""
    model = MultiscaleCampaign()
    snapshots = {}
    warm_start = min(warm)
    if warm_start % DAY:
        raise ValueError('warmup must start on a complete UTC day')
    for bar in extra_daily:
        if bar[0] > warm_start:
            raise ValueError('supplementary warmup overlaps hourly originals')
        snap = model.update(*bar, friction=friction)
        snapshots[snap.available_at] = snap
    for bt in range(warm_start, end, DAY):
        source = warm if bt < start else trade
        rows = [source[t] for t in range(bt, bt+DAY, 3_600_000)]
        snap = model.update(bt+DAY, max(D(r[2]) for r in rows), min(D(r[3]) for r in rows),
                            D(rows[-1][4]), friction)
        snapshots[snap.available_at] = snap
    return snapshots
