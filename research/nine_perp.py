"""Registered information expressions through one owned Coin campaign."""
from collections import deque
from contextlib import contextmanager
from decimal import Decimal as D
from unittest.mock import patch

from coinquant.opportunities import Opportunity, FOUR_HOURS
from coinquant.types import Blocked
from research import alpha_perp as alpha, complete_perp as meter, nine_routes as r
from coinquant import lifecycle

BASE=alpha.AlphaCampaign


class RouteCampaign(BASE):
    family='oi-deleveraging';expression=0;book=None;context=None

    def __init__(self):
        super().__init__();self.route_lows=deque(maxlen=10);self.route_signal_ms=None

    def update(self,end,high,low,close):
        result=super().update(end,high,low,close);self.route_lows.append(D(low))
        if (self.family=='oi-deleveraging' and self.expression==0 and self.position_campaign is None
                and self.model.active is None and len(self.route_lows)==10 and self.book is not None):
            feature=self.book.at(self.family,end,self.context(end))
            effect=r.alpha_expression(self.family,0,feature,dict(symbol='BTCUSDT',side='BUY'))
            stop=min(self.route_lows);price=D(close)
            signal_ms=feature.get('available_ms')
            if (effect['status']=='PROPOSE_NEW_PRIMARY_RESEARCH' and type(signal_ms) is int
                    and 0<=signal_ms<=end and signal_ms!=self.route_signal_ms and 0<stop<price):
                self.route_signal_ms=signal_ms
                self.model.active=Opportunity(end,1,stop,price*(price/stop)**20,end+7*r.DAY)
                atr=sum(self.model.tr)/14 if len(self.model.tr)==14 else None
                self.trigger=dict(identity=end,direction=1,kind='impulse',signal_family=self.family,
                                  close=str(price),prior_atr=str(atr) if atr else None)
                result=self.model.active
        return result

    def entry_fraction(self,friction):
        original=super().entry_fraction(friction)
        if self.position_campaign is not None or self.book is None:return original
        at=self.decision_ms if self.decision_ms is not None else self.last
        feature=self.book.at(self.family,at,self.context(at))
        effect=r.alpha_expression(self.family,self.expression,feature,dict(symbol='BTCUSDT',side='BUY'))
        return original*D(effect['factor']) if effect.get('factor') is not None else original

    def checkpoint(self):
        saved=super().checkpoint()
        saved['body']['nine']=dict(family=self.family,expression=self.expression,
            spec_sha256=r.sha(r.SPEC.read_bytes()),feature_book=self.book.sha256 if self.book else None,
            lows=list(map(str,self.route_lows)),signal_ms=self.route_signal_ms)
        saved['sha256']=meter.checksum(saved['body']);return saved

    @classmethod
    def restore(cls,saved):
        try:
            body=dict(saved['body'])
            if saved['sha256']!=meter.checksum(body):raise ValueError('digest')
            extra=dict(body.pop('nine'));lows=list(map(D,extra.pop('lows')));signal_ms=extra.pop('signal_ms')
            if signal_ms is not None and (type(signal_ms) is not int or not 0<=signal_ms<=body['last']):
                raise ValueError('future information identity')
            expected=dict(family=cls.family,expression=cls.expression,spec_sha256=r.sha(r.SPEC.read_bytes()),feature_book=cls.book.sha256 if cls.book else None)
            if extra!=expected or len(lows)>10 or any(not v.is_finite() or v<=0 for v in lows):raise ValueError('foreign information checkpoint')
            model=BASE.restore.__func__(cls,dict(body=body,sha256=meter.checksum(body)))
            model.route_lows=deque(lows,maxlen=10);model.route_signal_ms=signal_ms;return model
        except (KeyError,TypeError,ValueError,ArithmeticError) as error:raise Blocked('invalid information campaign') from error


@contextmanager
def variant(family,expression,book,context,journal):
    if family not in ('oi-deleveraging','option-insurance','dollar-financing') or expression not in (0,1):
        raise ValueError('unregistered Coin information expression')
    original_decide=lifecycle.Lifecycle.decide
    def record_control(engine,model,snapshot):
        row=model.macro_observation;stamp=int(engine.reader.clock()*1000)
        if row and row.get('missing_reason') is None and type(row.get('latest_value_available_ms')) is int and row['latest_value_available_ms']<stamp:
            value=r.number(row['latest_value'])
            if journal and journal[-1].get('event')=='decision':
                journal[-1]['causal_dfii10']=dict(value=str(value),available_ms=row['latest_value_available_ms'],
                    observation_date=row['latest_observation_date'],raw_observation=row)
        return original_decide(engine,model,snapshot)
    with patch.object(lifecycle.Lifecycle,'decide',record_control),patch.object(alpha,'AlphaCampaign',RouteCampaign),patch.object(RouteCampaign,'family',family),patch.object(RouteCampaign,'expression',expression),patch.object(RouteCampaign,'book',book),patch.object(RouteCampaign,'context',staticmethod(context)),alpha.variant('incumbent',
        binding=dict(nine_spec=r.sha(r.SPEC.read_bytes()),family=family,expression=expression,feature_book=book.sha256),journal=journal):
        yield
