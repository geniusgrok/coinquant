"""The only entry permitted to remain after exit: flat-account conditional FOK.

FOK has no unfilled remainder after activation. Full market TP/SL is attached to
that parent. Ordinary GTC entries and additions to an existing position must not
remain offline. This contract follows Bybit's documented order fields; actual
exchange integration remains a separate qualification, not a mock-test claim.
"""
from .model import liquidation_price, validate_risk_increase
from .state import client_id
from .types import D, SYMBOL, Blocked, Unknown, number


def prices(order):
    return tuple(number(order[key]) for key in ('price', 'triggerPrice', 'takeProfit', 'stopLoss'))


def valid(order, snapshot, cap):
    try:
        if snapshot.position.quantity or snapshot.position.index != 0:
            return False
        if (order['symbol'] != SYMBOL or not order['orderLinkId'].startswith('cq-')
                or order['orderStatus'] != 'Untriggered' or order['stopOrderType'] != 'Stop'
                or order['orderType'] != 'Limit' or order['timeInForce'] != 'FOK'
                or order['positionIdx'] != 0 or order['reduceOnly'] is not False
                or order['closeOnTrigger'] is not False or order['tpslMode'] != 'Full'
                or order['triggerBy'] != 'MarkPrice' or order['tpTriggerBy'] != 'MarkPrice'
                or order['slTriggerBy'] != 'MarkPrice' or number(order['cumExecQty']) != 0):
            return False
        q = number(order['qty'], positive=True)
        r = snapshot.rules
        if q % r.step or not r.minimum <= q <= min(cap, r.maximum, r.risk_limit_usd):
            return False
        price, trigger, tp, sl = prices(order)
        if min(price, trigger, tp, sl) <= 0 or any(x % r.tick for x in (price, trigger, tp, sl)):
            return False
        for key in ('tpLimitPrice', 'slLimitPrice'):
            if order.get(key) not in (None, '') and number(order[key]) != 0:
                return False
        if order['side'] == 'Buy' and order['triggerDirection'] == 1:
            sign = 1
            if not sl < trigger <= price < tp:
                return False
        elif order['side'] == 'Sell' and order['triggerDirection'] == 2:
            sign = -1
            if not tp < price <= trigger < sl:
                return False
        else:
            return False
        # No extra margin is assumed to appear after a future offline fill.
        initial = q / price / 20
        liq = liquidation_price(sign * q, price, initial, r.maintenance_rate, r.taker_fee)
        cushion = max(r.tick * 2, trigger * D('0.003'))
        if (sign > 0 and sl <= liq + cushion) or (sign < 0 and sl >= liq - cushion):
            return False
        return True
    except (Blocked, KeyError, TypeError, ValueError, ArithmeticError, AttributeError):
        return False


def matches(order, target):
    try:
        return (number(order['qty']) == abs(target.quantity)
                and order['side'] == ('Buy' if target.quantity > 0 else 'Sell')
                and prices(order) == (target.entry, target.trigger_price, target.take_profit, target.stop_loss))
    except (Blocked, KeyError, TypeError, ValueError, ArithmeticError):
        return False


def validate_target(snapshot, target, cap, cfg):
    if not target.trigger_price or snapshot.position.quantity:
        raise Blocked('offline entry requires a conditional target and a flat account')
    validate_risk_increase(snapshot, target, cfg, notional_limit=cap)
    if target.quantity * (target.trigger_price - snapshot.mark) <= 0:
        raise Blocked('conditional trigger has already crossed; reconcile and decide again')
    row = record('cq-validation', target)
    if not valid(row, snapshot, cap):
        raise Blocked('conditional entry lacks a safe full native FOK protection contract')


def record(link, target):
    """Expected readback contract, also used by the deterministic exchange fake."""
    return dict(symbol=SYMBOL, orderLinkId=link, orderStatus='Untriggered',
                stopOrderType='Stop', orderType='Limit', timeInForce='FOK', positionIdx=0,
                reduceOnly=False, closeOnTrigger=False, tpslMode='Full',
                triggerBy='MarkPrice', tpTriggerBy='MarkPrice', slTriggerBy='MarkPrice',
                qty=str(abs(target.quantity)), cumExecQty='0',
                side='Buy' if target.quantity > 0 else 'Sell',
                triggerDirection=1 if target.quantity > 0 else 2,
                price=str(target.entry), triggerPrice=str(target.trigger_price),
                takeProfit=str(target.take_profit), stopLoss=str(target.stop_loss))


def working(snapshot, cap):
    entries = [o for o in snapshot.orders if o.get('reduceOnly') is not True
               and o.get('closeOnTrigger') is not True]
    return entries[0] if len(entries) == 1 and valid(entries[0], snapshot, cap) else None


def settle(engine, identity, link, expected, operation):
    """Acknowledge only a read-back hosted contract or a terminal parent.

    A terminal parent can have filled its OLD size while an amendment was in
    flight. Verify the actual receipt; do not send the new target a second time.
    """
    from .bybit import TERMINAL
    for _ in range(2):
        row = engine.venue.lookup(link)
        fresh = engine.observe()
        if not row:
            continue
        if row.get('orderStatus') in TERMINAL:
            if any(o.get('orderLinkId') == link for o in fresh.orders):
                continue
            qty, filled = number(row['qty'], positive=True), number(row['cumExecQty'])
            if filled not in (0, qty):
                engine.state.finish(identity, 'confirmed', {'order': row, 'safety_violation': 'partial_fok'})
                engine.report['partial'] = True
                engine.state.set('native_fok_violation', {'link': link, 'filled': filled, 'qty': qty})
                raise Unknown('native FOK returned a partial fill; disable new risk and reconcile')
            result = {'order': row, 'outcome': row['orderStatus']}
        else:
            hosted = working(fresh, engine.config.max_position_usd)
            if not hosted or hosted.get('orderLinkId') != link:
                continue
            keys = ('qty', 'price', 'triggerPrice', 'takeProfit', 'stopLoss')
            if any(number(hosted[k]) != number(expected[k]) for k in keys):
                continue
            if hosted['side'] != expected['side']:
                continue
            result = {'order': hosted, 'outcome': 'hosted_untriggered_verified'}
        engine.state.finish(identity, 'confirmed', result)
        engine.report['actions'].append(dict(operation=operation, id=link, **result))
        return fresh
    raise Unknown('conditional parent/amendment outcome remains unknown; no retry')


def reconcile(engine, intent):
    payload = intent['payload']
    return settle(engine, intent['id'], payload['link'], payload['expected'], 'reconcile_entry')


def apply(engine, snapshot, target):
    """Create or amend ONE flat-account parent, with intent-before-send."""
    if engine.state.get('native_fok_violation'):
        raise Blocked('native FOK safety contract previously failed; no additional risk')
    if engine.state.pending():
        raise Unknown('unresolved write blocks a conditional entry or amendment')
    validate_target(snapshot, target, engine.config.max_position_usd, engine.config.model)
    existing = working(snapshot, engine.config.max_position_usd)
    if existing and matches(existing, target):
        return snapshot
    operation = 'amend_entry' if existing else 'place_entry'
    # One candle's risk-increase intent is shared with immediate IOC entry.
    # Changing the execution shape after local state loss cannot create a new ID.
    link = existing['orderLinkId'] if existing else client_id(engine.state.identity, target.candle, 'increase')
    expected = record(link, target)
    identity = client_id(engine.state.identity, target.candle, 'amend:' + link) if existing else link
    if existing and existing['side'] != expected['side']:
        raise Blocked('side change requires confirmed cancellation and fresh position reconciliation')
    if not existing:
        prior = engine.venue.lookup(link)
        if prior:
            # A deterministic ID remains consumed after state loss, including a
            # parent that filled and was stopped while the process was offline.
            fresh = engine.observe()
            engine.report['actions'].append({'operation': 'reconcile_existing', 'id': link,
                                            'outcome': prior.get('orderStatus', 'unknown')})
            return fresh
    engine.state.prepare(identity, 'entry' if existing is None else 'amend',
                         {'link': link, 'expected': expected})
    engine.before_write()
    try:
        if existing:
            engine.venue.amend(link, target)
        else:
            engine.venue.place(link, target.quantity, target)
    except (Blocked, Unknown):
        pass
    return settle(engine, identity, link, expected, operation)
