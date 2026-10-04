"""Continuous BTC target campaign; legacy Campaign remains a historical comparator."""
from collections import deque
from decimal import Decimal as D
import hashlib
import json

from .campaign import Campaign as Legacy, DAY, ORIGIN
from .opportunities import Opportunity
from .target import RULE, exposure
from .types import Blocked


class Campaign(Legacy):
    continuous_entry = True
    core_rule = RULE
    mode = 'uptrend'

    def __init__(self):
        super().__init__()
        self.closes = deque(maxlen=64)
        self.core_active = None
        self.target = D(0)
        self.extreme = None
        self.base_take = None
        self.peak_after = None
        self.stop_crossed = False

    def update(self, end, high, low, close):
        super().update(end, high, low, close)
        if end % DAY == 0:
            self.closes.append(D(close))
        self.target = exposure(self.closes, mode=self.mode)
        direction = 1 if self.target > 0 else -1 if self.target < 0 else 0
        old = self.core_active
        if not direction:
            self.core_active = None
        elif old is None or old.direction != direction or (
                self.position_campaign is None and self.primary_consumed == old.identity):
            self.extreme = D(close)
            self.base_take = D(close)*(4 if direction > 0 else D('.25'))
            self.core_active = Opportunity(end, direction,
                D(close)*(D('.75') if direction > 0 else D('1.25')), self.base_take, None)
        elif self.position_campaign == old.identity:
            eligible = self.peak_after is not None and end-self.model.interval >= self.peak_after
            self.extreme = (max(self.extreme, D(high) if eligible else D(close)) if direction > 0
                            else min(self.extreme, D(low) if eligible else D(close)))
            stop = self.extreme*(D('.75') if direction > 0 else D('1.25'))
            self.core_active = Opportunity(old.identity, direction, stop, old.take, None)
        return self.core_active

    @property
    def active(self):
        return self.core_active

    def macro_relevant(self):
        return False

    def select_macro(self, row, mark, call, *, bootstrap=False):
        if row is not None or type(call) is not int or not self.last <= call < self.last+self.model.interval:
            raise Blocked('core decision requires its completed price boundary')
        self.macro_observation = None
        self.stop_crossed = bool(self.core_active and self.position_campaign is not None and
            (D(mark) <= self.core_active.stop if self.core_active.direction > 0
             else D(mark) >= self.core_active.stop))
        if self.core_active is not None and self.position_campaign is None:
            # Entry geometry starts at the current causal quote, not a stale
            # reconstructed forecast's price. No fill is claimed here.
            p = D(mark)
            if not p.is_finite() or p <= 0:
                raise Blocked('invalid entry mark')
            a = self.core_active
            self.extreme = p
            self.peak_after = (call//self.model.interval+1)*self.model.interval
            self.base_take = p*(4 if a.direction > 0 else D('.25'))
            self.core_active = Opportunity(a.identity, a.direction,
                p*(D('.75') if a.direction > 0 else D('1.25')), self.base_take, None)

    def entry_fraction(self, friction):
        return abs(self.target)

    def action(self, quantity):
        if quantity and self.stop_crossed:
            return 'exit'
        return super().action(quantity)

    def checkpoint(self):
        saved = super().checkpoint()
        saved['body']['core'] = dict(rule=RULE, mode=self.mode,
            closes=[str(x) for x in self.closes], target=str(self.target),
            active=None if self.core_active is None else dict(identity=self.core_active.identity,
                direction=self.core_active.direction, stop=str(self.core_active.stop),
                take=str(self.core_active.take), expires=None),
            extreme=None if self.extreme is None else str(self.extreme),
            base_take=None if self.base_take is None else str(self.base_take),
            peak_after=self.peak_after, stop_crossed=self.stop_crossed)
        saved['sha256'] = hashlib.sha256(json.dumps(saved['body'], sort_keys=True).encode()).hexdigest()
        return saved

    @classmethod
    def restore(cls, saved):
        try:
            body = dict(saved['body'])
            if hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest() != saved['sha256']:
                raise ValueError('checkpoint digest')
            core = body.pop('core')
            if core['rule'] != RULE or core['mode'] != cls.mode:
                raise ValueError('core identity')
            stripped = dict(body=body, sha256=hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest())
            result = super().restore(stripped)
            result.closes = deque((D(x) for x in core['closes']), maxlen=64)
            if (len(core['closes']) != min(64, (result.last-ORIGIN)//DAY)
                    or any(not x.is_finite() or x <= 0 for x in result.closes)
                    or result.closes and result.closes[-1] != result.previous_daily):
                raise ValueError('daily history')
            result.target = D(core['target'])
            if result.target != exposure(result.closes, mode=cls.mode):
                raise ValueError('forecast integrity')
            a = core['active']
            if a is not None:
                result.core_active = Opportunity(a['identity'], a['direction'], D(a['stop']), D(a['take']), None)
                if (type(a['identity']) is not int or not 1575158400000 < a['identity'] <= result.last
                        or a['direction'] not in (-1, 1) or a['direction']*result.target <= 0
                        or min(result.core_active.stop, result.core_active.take) <= 0
                        or not all(x.is_finite() for x in (result.core_active.stop, result.core_active.take))
                        or (result.core_active.take-result.core_active.stop)*a['direction'] <= 0):
                    raise ValueError('campaign geometry')
            result.extreme = D(core['extreme']) if core['extreme'] is not None else None
            result.base_take = D(core['base_take']) if core['base_take'] is not None else None
            result.peak_after = core['peak_after']
            result.stop_crossed = core['stop_crossed']
            if (type(result.stop_crossed) is not bool or result.peak_after is not None and
                    (type(result.peak_after) is not int or result.peak_after % result.model.interval
                     or result.peak_after > result.last+result.model.interval)):
                raise ValueError('owned peak clock')
            if any(x is not None and (not x.is_finite() or x <= 0) for x in (result.extreme, result.base_take)):
                raise ValueError('price state')
            if result.core_active is not None and (result.extreme is None or result.base_take != result.core_active.take):
                raise ValueError('missing catastrophe geometry')
            return result
        except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
            raise Blocked('incompatible BTC core checkpoint; no automatic account reset') from exc


def restore_campaign(saved):
    """Internal recovery of an already selected campaign, never a default migration."""
    if 'core' not in saved.get('body', {}):
        # Explicit historical research may scope its own strict checkpoint
        # class. Default session.advance still rejects foreign core identities.
        from .campaign import Campaign as SelectedHistorical
        return SelectedHistorical.restore(saved)
    from .target import MODES
    mode = saved['body']['core'].get('mode')
    if mode not in MODES:
        raise Blocked('unknown core recovery mode')
    cls = Campaign if mode == Campaign.mode else type('ResearchCampaign', (Campaign,), {'mode': mode})
    return cls.restore(saved)
