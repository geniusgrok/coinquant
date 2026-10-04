"""New completed-bar signal families, single protected owned Coin campaign."""
from contextlib import contextmanager
from decimal import Decimal as D
from unittest.mock import patch

from coinquant import campaign, linear_preview
from coinquant.opportunities import Opportunity, FOUR_HOURS
from coinquant.types import Blocked
from research import alpha_perp as alpha, complete_perp as meter, persistent_routes as routes

BASE=alpha.AlphaCampaign


class StateCampaign(BASE):
    name='state-trend'
    causal_bars={}

    def update(self,end,high,low,close):
        super().update(end,high,low,close)
        # Replace only newly generated primary opportunities, preserve already
        # held/current campaigns, real macro ownership and original expiry logic.
        created=self.model.active is not None and self.model.active.identity==end
        if created:self.model.active=None;self.trigger=None
        event=routes.signal(self.causal_bars,end-FOUR_HOURS,self.name,'coin')
        if self.model.active is None and event:
            self.model.active=Opportunity(end,1,event['stop'],event['take'],end+event['life_ms'])
            atr=sum(self.model.tr)/14 if len(self.model.tr)==14 else None
            self.trigger=dict(identity=end,close=str(close),prior_atr=str(atr) if atr else None,
                              direction=1,kind='impulse',signal_family=self.name)
            if self.journal is not None:self.journal.append(dict(event='opportunity',at_ms=end,**self.trigger))
        return self.model.active

    def checkpoint(self):
        saved=super().checkpoint()
        saved['body']['persistent']=dict(name=self.name,spec_sha256=alpha.file_hash(routes.SPEC))
        saved['sha256']=meter.checksum(saved['body'])
        return saved

    @classmethod
    def restore(cls,saved):
        try:
            body=dict(saved['body'])
            if saved['sha256']!=meter.checksum(body):raise ValueError('digest')
            extra=body.pop('persistent')
            if extra!=dict(name=cls.name,spec_sha256=alpha.file_hash(routes.SPEC)):raise ValueError('foreign persistent identity')
            return BASE.restore.__func__(cls,dict(body=body,sha256=meter.checksum(body)))
        except (KeyError,ValueError,TypeError) as error:raise Blocked('invalid persistent campaign') from error


class UniformCampaign(BASE):
    def entry_fraction(self,friction):
        return alpha.BaseCampaign.entry_fraction(self,friction)*D('.75')


@contextmanager
def variant(name,bars,journal):
    if name not in ('state-trend','state-range','uniform'):raise ValueError('unregistered full account candidate')
    klass=UniformCampaign if name=='uniform' else StateCampaign
    with patch.object(alpha,'AlphaCampaign',klass),patch.object(StateCampaign,'name',name),patch.object(StateCampaign,'causal_bars',bars),alpha.variant(
            'incumbent',binding=dict(persistent_spec=alpha.file_hash(routes.SPEC),name=name,
            quote_input='Pinned original completed quote bars, explicit research supplement; native volume bridge unverified'),
            journal=journal):
        yield
