"""Read-only shared model evaluation. A preview never consumes an opportunity."""
from .campaign import Campaign
from .types import Blocked
from decimal import Decimal as D


def advance(state, venue):
    saved=state.get('linear_campaign')
    model=Campaign.restore(saved) if saved is not None else Campaign()
    if model.model.mechanism!='impulse_hold' or model.model.interval!=14400000:
        raise Blocked('checkpoint does not match current L model')
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
    if bootstrap:
        # Price reconstruction cannot establish historical fill ownership.
        model.consumed=model.model.active.identity if model.model.active else None
    state.set('linear_campaign',model.checkpoint())
    state.set('market_bootstrap',False)
    return model,market,bootstrap


def preview(model,snapshot, *, side='long'):
    quantity=D(snapshot['quantity_btc'])
    if not quantity.is_finite():raise Blocked('invalid native quantity')
    action=model.action(quantity,side)
    return dict(action=action,opportunity=model.model.active,
                protection_required=bool(quantity) and not (snapshot.get('native_full_position_protected') and snapshot.get('stop_before_liquidation')),
                consumed_campaign=model.consumed,position_campaign=model.position_campaign,
                target_fraction=str(model.fraction('3.6','.0011')) if action=='enter' else None,
                quantity_btc=str(quantity) if action=='hold' else '0' if action in ('exit','flat','consumed') else None,
                quantity_status='native preflight required' if action=='enter' else 'shared inventory decision',
                model='L3.6',qualification='NOT_QUALIFIED')
