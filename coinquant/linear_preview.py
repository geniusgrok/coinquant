"""Read-only shared model evaluation. A preview never consumes an opportunity."""
from .campaign import Campaign
from .campaign import DAY
from .types import Blocked
from decimal import Decimal as D
from collections import deque


def research_side(state):
    """Live state leaves this unset, so the production book stays two-sided."""
    side=state.get('research_side') or 'both'
    if side not in ('long','short','both'):
        raise Blocked('unsupported research side')
    return side


def advance(state, venue):
    saved=state.get('linear_campaign')
    mechanism=state.get('research_mechanism') or 'impulse_hold'
    if mechanism not in ('impulse_hold','horizon_hold','average_hold'):
        raise Blocked('unsupported research mechanism')
    model=Campaign.restore(saved) if saved is not None else Campaign(mechanism)
    if model.model.mechanism!=mechanism or model.model.interval!=14400000:
        raise Blocked('checkpoint does not match current L model')
    if saved is not None and saved['body']['version']<3 and model.last>=11*DAY:
        # Reconstruct only the missing market lows. Durable order/fill ownership
        # stays untouched, and an incomplete native page cannot be promoted.
        start=(model.last//DAY-10)*DAY
        bars=venue.completed_market(start=start)['candles']
        prior=[b for b in bars if b['time']<model.last]
        if (len(prior)!=(model.last-start)//14400000 or
                any(b['time']!=start+i*14400000 for i,b in enumerate(prior))):
            raise Blocked('legacy checkpoint daily-low migration incomplete')
        complete={}
        partial=[]
        for bar in prior:
            day=bar['time']//DAY
            if day<model.last//DAY:
                complete[day]=min(complete.get(day,D(bar['low'])),D(bar['low']))
            else:partial.append(D(bar['low']))
        if len(complete)!=10:raise Blocked('ten completed daily lows unavailable')
        model.daily_lows=deque((complete[d] for d in sorted(complete)),maxlen=10)
        model.day_low=min(partial) if partial else None
        state.set('linear_campaign',model.checkpoint())
    if saved is None:state.set('market_bootstrap',True)
    bootstrap=bool(state.get('market_bootstrap'))
    def save_page(bars):
        for bar in bars:
            model.update(bar['time']+model.model.interval,bar['high'],bar['low'],bar['close'])
        state.set('linear_campaign',model.checkpoint())
    market=venue.completed_market(start=model.last,on_page=save_page)
    if market.get('interval_ms')!=model.model.interval:
        raise Blocked('missing complete model history')
    for bar in market['candles']:
        if bar['time']+model.model.interval>model.last:
            model.update(bar['time']+model.model.interval,bar['high'],bar['low'],bar['close'])
    if model.last!=market['complete_through']:
        raise Blocked('market and checkpoint boundaries differ')
    if bootstrap and not state.get('enter_unconsumed_bootstrap'):
        # Price reconstruction cannot establish historical fill ownership.
        # The research flag leaves a still-active impulse eligible. Live state
        # does not set it, so a cold start still consumes that impulse.
        model.consumed=model.primary_consumed=model.model.active.identity if model.model.active else None
    state.set('linear_campaign',model.checkpoint())
    state.set('market_bootstrap',False)
    return model,market,bootstrap


def preview(model,snapshot, *, side='long'):
    quantity=D(snapshot['quantity_btc'])
    if not quantity.is_finite():raise Blocked('invalid native quantity')
    action=model.action(quantity,side)
    return dict(action=action,opportunity=model.active,
                protection_required=bool(quantity) and not (snapshot.get('native_full_position_protected') and snapshot.get('stop_before_liquidation')),
                consumed_campaign=(model.macro_consumed if model.macro_opportunity is not None and
                                   model.active is model.macro_opportunity
                                   else model.primary_consumed),position_campaign=model.position_campaign,
                target_fraction=str(model.entry_fraction('.0011')) if action=='enter' else None,
                quantity_btc=str(quantity) if action=='hold' else '0' if action in ('exit','flat','consumed') else None,
                quantity_status='native preflight required' if action=='enter' else 'shared inventory decision',
                model='SX60+DFII10',macro_observation=model.macro_observation,
                qualification='NOT_QUALIFIED')
