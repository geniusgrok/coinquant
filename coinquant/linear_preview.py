"""Read-only shared model evaluation. A preview never consumes an opportunity."""
from .campaign import Campaign
from .types import Blocked, number
from decimal import Decimal as D

_CURRENT_PROTECTION=object()


def advance(state, venue, fill=None, *, effective_protection=_CURRENT_PROTECTION):
    saved=state.get('linear_campaign')
    model=Campaign.restore(saved) if saved is not None else Campaign()
    if saved is None:state.set('market_bootstrap',True)
    if fill is not None:
        price=D(fill)
        if price.is_finite() and price>0:
            model.entry_fill=price
    bootstrap=bool(state.get('market_bootstrap'))
    protection=(state.get('position_protection') if effective_protection is _CURRENT_PROTECTION
                else effective_protection)
    pending=state.get('protection_catchup') or []
    if not isinstance(pending,list):
        raise Blocked('invalid protection catch-up history')
    periods=[]
    def geometry(item):
        return (item['campaign'],number(item['stop'],positive=True),number(item['take'],positive=True))
    for item in pending:
        if (not isinstance(item,dict) or type(item.get('accepted_at_ms')) is not int
                or type(item.get('ended_at_ms')) is not int
                or item['ended_at_ms']<item['accepted_at_ms']):
            raise Blocked('invalid protection catch-up boundary')
        geometry(item)
        periods.append(dict(item))
    candidates=[protection]
    if pending:
        # A completed replacement may have happened before this catch-up. Its
        # accepted successor completes same-price continuity across that handoff.
        current=state.get('position_protection')
        if current and any(item['campaign']==current.get('campaign') for item in pending):
            candidates.append(current)
    for candidate in candidates:
        if candidate and type(candidate.get('accepted_at_ms')) is int:
            # A prior-cycle snapshot may have since been retired. Its durable end
            # takes precedence; never append an unbounded copy of that same pair.
            if not any(item['accepted_at_ms']==candidate['accepted_at_ms']
                       and geometry(item)==geometry(candidate) for item in periods):
                periods.append(dict(candidate))
    periods.sort(key=lambda item:item['accepted_at_ms'])
    continuous=[]
    for item in periods:
        if continuous and geometry(continuous[-1])==geometry(item):
            # Same-price renewal accepts the new pair before retiring the old
            # one. Their geometry is continuous despite conservative timestamps.
            continuous[-1]['ended_at_ms']=item.get('ended_at_ms')
        else:
            continuous.append(item)
    def update(bar):
        end=bar['time']+model.model.interval
        covered=next((item for item in reversed(continuous)
                      if item['accepted_at_ms']<=bar['time']
                      and (item.get('ended_at_ms') is None or end<=item['ended_at_ms'])),{})
        model.update(end,bar['high'],bar['low'],bar['close'],effective_protection=covered)
    def save():
        # Persist the model and removal of spent geometry together. A failed
        # later page or a restart must retain every not-yet-replayed period.
        state.set_many({'linear_campaign':model.checkpoint(),
                        'protection_catchup':[item for item in pending if item['ended_at_ms']>model.last]})
    def save_page(bars):
        for bar in bars:
            update(bar)
        save()
    market=venue.completed_market(start=model.last,on_page=save_page)
    if market.get('interval_ms')!=model.model.interval:
        raise Blocked('missing complete model history')
    for bar in market['candles']:
        if bar['time']+model.model.interval>model.last:
            update(bar)
    if model.last!=market['complete_through']:
        raise Blocked('market and checkpoint boundaries differ')
    if bootstrap:
        # Price reconstruction cannot establish historical fill ownership, so a
        # cold start consumes a still-active impulse. The flag clears only when
        # the macro step of the same cold start has completed (session.cycle).
        model.consumed=model.primary_consumed=model.model.active.identity if model.model.active else None
    save()
    return model,market,bootstrap


def preview(model,snapshot):
    quantity=D(snapshot['quantity_btc'])
    if not quantity.is_finite():raise Blocked('invalid native quantity')
    action=model.action(quantity)
    return dict(action=action,opportunity=model.active,
                protection_required=bool(quantity) and not (snapshot.get('native_full_position_protected') and snapshot.get('stop_before_liquidation')),
                consumed_campaign=(model.macro_consumed if model.macro_opportunity is not None and
                                   model.active is model.macro_opportunity
                                   else model.primary_consumed),position_campaign=model.position_campaign,
                target_fraction=None,
                quantity_btc=str(quantity) if action=='hold' else '0' if action in ('exit','flat','consumed') else None,
                quantity_status='native preflight required' if action=='enter' else 'shared inventory decision',
                model='SX60+DFII10',macro_observation=model.macro_observation)
