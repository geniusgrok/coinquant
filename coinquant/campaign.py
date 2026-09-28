"""Exact resumable completed-bar state for the default SX60+DFII10 model (not qualified for live trading).

Market state and execution ownership are separate. Replaying prices can rebuild
the first, never prove past fills. No exchange writes are performed here.
"""
from collections import deque
from dataclasses import asdict
from decimal import Decimal as D
import hashlib
import json

from .opportunities import Opportunities, Opportunity
from .linear_sizing import target_fraction
from .types import Blocked, Unknown

PRIMARY_RISK = '7.5'
MACRO_RISK = '3.6'
ORIGIN = 1575158400000  # 2019-12-01T00:00Z, fixed model warmup origin
DAY = 86400000
VERSION = 4


def disposition(opportunity, quantity, consumed):
    direction = opportunity.direction if opportunity else 0
    if quantity:
        return 'hold' if quantity*direction>0 and opportunity.identity==consumed else 'exit'
    if not direction:return 'flat'
    return 'consumed' if opportunity.identity==consumed else 'enter'


class Campaign:
    def __init__(self):
        self.model=Opportunities()
        self.returns=deque(maxlen=20)
        self.previous_daily=None
        self.last=ORIGIN
        self.consumed=None
        self.primary_consumed=None
        self.macro_consumed=None
        self.position_campaign=None
        self.day_low=None
        self.daily_lows=deque(maxlen=10)
        self.macro_epoch=None
        self.macro_opportunity=None
        self.macro_observation=None

    def update(self, end, high, low, close):
        if type(end) is not int or end!=self.last+self.model.interval:
            raise Blocked('complete history from fixed origin or matching checkpoint required')
        values=[D(high),D(low),D(close)]
        if not all(v.is_finite() for v in values):raise Blocked('nonfinite candle')
        opportunity=self.model.update(end,*values)
        self.day_low=min(self.day_low,values[1]) if self.day_low is not None else values[1]
        if end%DAY==0:
            if self.previous_daily is not None:self.returns.append(values[2]/self.previous_daily-1)
            self.previous_daily=values[2]
            self.daily_lows.append(self.day_low)
            self.day_low=None
        self.last=end
        return opportunity

    def fraction(self, risk, friction):
        return D(risk)*target_fraction(self.returns,D(friction))

    @property
    def active(self):
        # The default model gives an owned macro position priority while its
        # state remains true; otherwise the SX60 long leads. Shorts are never active.
        if self.position_campaign is not None and self.position_campaign<0:
            return self.macro_opportunity
        primary=self.model.active
        if primary is not None and primary.direction>0 and (
                self.position_campaign==primary.identity or primary.identity!=self.primary_consumed):
            return primary
        return self.macro_opportunity

    def macro_relevant(self):
        """Whether DFII10 can change this decision. A primary position, or a flat
        account with an unconsumed primary long, decides without it."""
        if self.position_campaign is not None:
            return self.position_campaign<0
        primary=self.model.active
        return not (primary is not None and primary.direction>0 and primary.identity!=self.primary_consumed)

    def select_macro(self, row, mark, call, *, bootstrap=False):
        """`row` None means DFII10 was not read; valid only when it is irrelevant."""
        from .dfii10 import eligible
        if type(call) is not int or not self.last<=call<self.last+self.model.interval:
            raise Blocked('macro decision precedes completed market')
        if row is None:
            if self.macro_relevant():
                raise Unknown('DFII10 observation required for this decision')
            self.macro_observation=None
            self.macro_epoch=self.macro_opportunity=None
            return
        self.macro_observation=row
        active=eligible(row,call)
        primary=self.model.active
        if not active:
            self.macro_epoch=self.macro_opportunity=None
        elif self.position_campaign is not None and self.position_campaign<0:
            if self.macro_opportunity is None or self.macro_opportunity.identity!=self.position_campaign:
                raise Blocked('owned macro geometry unavailable')
        elif self.position_campaign is not None:
            self.macro_epoch=self.macro_opportunity=None
        elif primary is not None and primary.direction>0 and primary.identity!=self.primary_consumed:
            self.macro_epoch=self.macro_opportunity=None
        else:
            if self.macro_epoch is None:self.macro_epoch=-call
            if bootstrap:self.macro_consumed=self.macro_epoch
            if self.macro_opportunity is None:
                price=D(mark)
                if len(self.daily_lows)!=10 or not price.is_finite() or price<=0:
                    raise Blocked('ten completed daily lows and current mark required')
                stop=min(self.daily_lows)
                if stop<=0 or stop>=price:
                    self.macro_opportunity=None
                else:
                    self.macro_opportunity=Opportunity(self.macro_epoch,1,stop,price*(price/stop)**20,None)

    def entry_fraction(self, friction):
        return self.fraction(MACRO_RISK if self.macro_opportunity is not None and
                             self.active is self.macro_opportunity else PRIMARY_RISK,friction)

    def action(self, quantity):
        if quantity and self.position_campaign is None:
            raise Blocked('position campaign unknown; market replay cannot reconstruct fills')
        selected=self.active
        consumed=(self.position_campaign if quantity else
                  self.macro_consumed if selected is self.macro_opportunity else self.primary_consumed)
        return disposition(selected,quantity,consumed)

    def filled(self, identity):
        if self.active is None or identity!=self.active.identity:
            raise Blocked('fill must be linked to its recorded campaign')
        self.consumed=self.position_campaign=identity
        if identity<0:self.macro_consumed=identity
        else:self.primary_consumed=identity

    def checkpoint(self):
        def encode(v):
            if isinstance(v,D):return {'decimal':str(v)}
            if isinstance(v,Opportunity):return {'opportunity':encode(asdict(v))}
            if isinstance(v,Opportunities):return {'opportunities':encode(vars(v))}
            if isinstance(v,deque):return {'deque':[encode(x) for x in v],'maxlen':v.maxlen}
            if isinstance(v,(tuple,list)):return [encode(x) for x in v]
            if isinstance(v,dict):return {k:encode(x) for k,x in v.items()}
            return v
        body={'version':VERSION,'last':self.last,'model':encode(vars(self.model)),
              'returns':[str(x) for x in self.returns],
              'previous_daily':str(self.previous_daily) if self.previous_daily is not None else None,
              'consumed':self.consumed,'position_campaign':self.position_campaign,
              'primary_consumed':self.primary_consumed,'macro_consumed':self.macro_consumed,
              'day_low':str(self.day_low) if self.day_low is not None else None,
              'daily_lows':[str(v) for v in self.daily_lows],
              'macro_epoch':self.macro_epoch,'macro_opportunity':encode(self.macro_opportunity),
              'macro_observation':self.macro_observation}
        return {'body':body,'sha256':hashlib.sha256(json.dumps(body,sort_keys=True).encode()).hexdigest()}

    @classmethod
    def restore(cls, saved):
        try:
            body=saved['body']
            if (saved['sha256']!=hashlib.sha256(json.dumps(body,sort_keys=True).encode()).hexdigest()
                    or body['version']!=VERSION):
                raise ValueError('state identity')
            def decode(v):
                if isinstance(v,list):return [decode(x) for x in v]
                if isinstance(v,dict):
                    if set(v)=={'decimal'}:
                        d=D(v['decimal'])
                        if not d.is_finite():raise ValueError('nonfinite state')
                        return d
                    if set(v)=={'opportunity'}:return Opportunity(**decode(v['opportunity']))
                    if set(v)=={'opportunities'}:
                        fields=decode(v['opportunities'])
                        model=Opportunities()
                        if set(fields)!=set(vars(model)):raise ValueError('nested model fields')
                        model.__dict__.update(fields)
                        return model
                    if set(v)=={'deque','maxlen'}:return deque((decode(x) for x in v['deque']),maxlen=v['maxlen'])
                    return {k:decode(x) for k,x in v.items()}
                return v
            data=decode(body['model']);result=cls()
            if set(data)!=set(vars(result.model)):raise ValueError('state fields')
            result.model.__dict__.update(data)
            result.last=body['last']
            interval=result.model.interval
            if type(result.last) is not int or result.last<ORIGIN or result.last%interval:
                raise ValueError('state clock')
            if data['last']!=(result.last if result.last>ORIGIN else None):raise ValueError('model clock')
            result.returns=deque((D(v) for v in body['returns']),maxlen=20)
            if len(body['returns'])>20 or not all(v.is_finite() for v in result.returns):raise ValueError('returns')
            result.previous_daily=D(body['previous_daily']) if body['previous_daily'] is not None else None
            if result.previous_daily is not None and (not result.previous_daily.is_finite() or result.previous_daily<=0):raise ValueError('daily close')
            for name in ('consumed','position_campaign'):
                v=body[name]
                if v is not None and (type(v) is not int or not (ORIGIN<v<=result.last or -(result.last+interval)<v<0)):
                    raise ValueError('campaign identity')
                setattr(result,name,v)
            if result.position_campaign is not None and result.position_campaign!=result.consumed:raise ValueError('ownership')
            result.primary_consumed=body['primary_consumed']
            result.macro_consumed=body['macro_consumed']
            if (result.primary_consumed is not None and
                (type(result.primary_consumed) is not int or not ORIGIN<result.primary_consumed<=result.last)):
                raise ValueError('primary consumed')
            if (result.macro_consumed is not None and
                (type(result.macro_consumed) is not int or not -(result.last+interval)<result.macro_consumed<0)):
                raise ValueError('macro consumed')
            result.day_low=D(body['day_low']) if body['day_low'] is not None else None
            result.daily_lows=deque((D(v) for v in body['daily_lows']),maxlen=10)
            if (result.day_low is not None and (not result.day_low.is_finite() or result.day_low<=0)
                    or len(body['daily_lows'])>10 or
                    any(not v.is_finite() or v<=0 for v in result.daily_lows)):
                raise ValueError('daily lows')
            result.macro_epoch=body['macro_epoch']
            result.macro_opportunity=decode(body['macro_opportunity'])
            result.macro_observation=body['macro_observation']
            if (result.macro_epoch is not None and
                (type(result.macro_epoch) is not int or not -(result.last+interval)<result.macro_epoch<0)):
                raise ValueError('macro epoch')
            if result.macro_opportunity is not None and (
                not isinstance(result.macro_opportunity,Opportunity) or result.macro_epoch is None or
                result.macro_opportunity.identity!=result.macro_epoch or result.macro_opportunity.direction!=1 or
                not 0<result.macro_opportunity.stop<result.macro_opportunity.take or
                not result.macro_opportunity.stop.is_finite() or not result.macro_opportunity.take.is_finite()):
                raise ValueError('macro geometry')
            return result
        except (KeyError,TypeError,ValueError,ArithmeticError) as exc:
            raise Blocked('invalid model checkpoint; do not silently restart from short history') from exc
