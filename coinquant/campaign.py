"""Exact resumable completed-bar state for the unqualified linear candidate.

Market state and execution ownership are separate. Replaying prices can rebuild
the first, never prove past fills. No exchange writes are performed here.
"""
from collections import deque
from dataclasses import asdict
from decimal import Decimal as D
import hashlib
import json

from .opportunities import Opportunities, Opportunity, FOUR_HOURS
from .linear_sizing import target_fraction
from .types import Blocked, ZERO

ORIGIN = 1575158400000  # 2019-12-01T00:00Z, fixed research warmup identity
DAY = 86400000


def disposition(opportunity, quantity, consumed, side='long'):
    direction = opportunity.direction if opportunity else 0
    if side=='long' and direction<0 or side=='short' and direction>0:
        direction=0
    if quantity:
        if opportunity is not None and getattr(opportunity,'parent_identity',None) is not None:
            return 'hold'
        return 'hold' if quantity*direction>0 and opportunity.identity==consumed else 'exit'
    if not direction:return 'flat'
    return 'consumed' if opportunity.identity==consumed else 'enter'


class Campaign:
    def __init__(self, mechanism='impulse_hold', interval=FOUR_HOURS):
        self.model=Opportunities(mechanism,interval)
        self.returns=deque(maxlen=20)
        self.previous_daily=None
        self.last=ORIGIN
        self.consumed=None
        self.position_campaign=None

    def update(self, end, high, low, close):
        if type(end) is not int or end!=self.last+self.model.interval:
            raise Blocked('complete history from fixed origin or matching checkpoint required')
        values=[D(high),D(low),D(close)]
        if not all(v.is_finite() for v in values):raise Blocked('nonfinite candle')
        opportunity=self.model.update(end,*values)
        if end%DAY==0:
            if self.previous_daily is not None:self.returns.append(values[2]/self.previous_daily-1)
            self.previous_daily=values[2]
        self.last=end
        return opportunity

    def fraction(self, risk, friction):
        return D(risk)*target_fraction(self.returns,D(friction))

    def action(self, quantity, side='long'):
        if quantity and self.position_campaign is None:
            raise Blocked('position campaign unknown; market replay cannot reconstruct fills')
        return disposition(self.model.active,quantity,self.consumed,side)

    def filled(self, identity):
        if self.model.active is None or identity!=self.model.active.identity:
            raise Blocked('fill must be linked to its recorded campaign')
        self.consumed=self.position_campaign=identity

    def checkpoint(self):
        def encode(v):
            if isinstance(v,D):return {'decimal':str(v)}
            if isinstance(v,Opportunity):
                body=asdict(v)
                if body['parent_identity'] is None:body.pop('parent_identity')
                return {'opportunity':encode(body)}
            if isinstance(v,Opportunities):return {'opportunities':encode(vars(v))}
            if isinstance(v,deque):return {'deque':[encode(x) for x in v],'maxlen':v.maxlen}
            if isinstance(v,(tuple,list)):return [encode(x) for x in v]
            if isinstance(v,dict):return {k:encode(x) for k,x in v.items()}
            return v
        version=2 if self.model.mechanism=='post_impulse_restart' else 1
        body={'version':version,'last':self.last,'model':encode(vars(self.model)),
              'returns':[str(x) for x in self.returns],
              'previous_daily':str(self.previous_daily) if self.previous_daily is not None else None,
              'consumed':self.consumed,'position_campaign':self.position_campaign}
        return {'body':body,'sha256':hashlib.sha256(json.dumps(body,sort_keys=True).encode()).hexdigest()}

    @classmethod
    def restore(cls, saved):
        try:
            body=saved['body']
            if (saved['sha256']!=hashlib.sha256(json.dumps(body,sort_keys=True).encode()).hexdigest()
                    or body['version'] not in (1,2)):
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
                        model=Opportunities(fields['mechanism'],fields['interval'])
                        if set(fields)!=set(vars(model)):raise ValueError('nested model fields')
                        model.__dict__.update(fields)
                        return model
                    if set(v)=={'deque','maxlen'}:return deque((decode(x) for x in v['deque']),maxlen=v['maxlen'])
                    return {k:decode(x) for k,x in v.items()}
                return v
            data=decode(body['model']);result=cls(data['mechanism'],data['interval'])
            if (body['version']==2) != (data['mechanism']=='post_impulse_restart'):
                raise ValueError('campaign version')
            if set(data)!=set(vars(result.model)):raise ValueError('state fields')
            result.model.__dict__.update(data)
            result.last=body['last']
            if type(result.last) is not int or result.last<ORIGIN or result.last%data['interval']:
                raise ValueError('state clock')
            if data['last']!=(result.last if result.last>ORIGIN else None):raise ValueError('model clock')
            result.returns=deque((D(v) for v in body['returns']),maxlen=20)
            if len(body['returns'])>20 or not all(v.is_finite() for v in result.returns):raise ValueError('returns')
            result.previous_daily=D(body['previous_daily']) if body['previous_daily'] is not None else None
            if result.previous_daily is not None and (not result.previous_daily.is_finite() or result.previous_daily<=0):raise ValueError('daily close')
            for name in ('consumed','position_campaign'):
                v=body[name]
                if v is not None and (type(v) is not int or not ORIGIN<v<=result.last):raise ValueError('campaign identity')
                setattr(result,name,v)
            if result.position_campaign is not None and result.position_campaign!=result.consumed:raise ValueError('ownership')
            return result
        except (KeyError,TypeError,ValueError,ArithmeticError) as exc:
            raise Blocked('invalid model checkpoint; do not silently restart from short history') from exc
