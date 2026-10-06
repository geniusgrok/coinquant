"""Normalize an observed full BTC perpetual account for a read-only report."""
from decimal import Decimal as D
from .types import Unknown, number


def export(actual, config):
    if actual['account_uid'] != config.account_uid:
        raise Unknown('export UID differs from the configured account')
    if not 0 <= actual['wallet_observed_until_ms'] - actual['wallet_observed_from_ms'] <= 5000:
        raise Unknown('account collection exceeded five seconds')
    stamp = actual['wallet_observed_from_ms']
    q, wallet, entry, price = (number(actual[key]) for key in
                              ('quantity_btc', 'wallet_usdt', 'entry', 'mark_price'))
    if price <= 0 or abs(actual['mark_time'] - actual['observed_at_ms']) > 5000:
        raise Unknown('valuation price is stale or invalid')
    liquidation = number(actual['native_liquidation_price'])
    stops=[number(a['trigger'],positive=True) for a in actual.get('protective_algos',[])
           if a.get('type')=='STOP_MARKET']
    stop_loss=(max(D(0),q*(entry-min(stops))) if q>0 else
               max(D(0),-q*(max(stops)-entry))) if q and stops else None
    return {'known': True, 'symbol': 'BTCUSDT', 'market': 'perpetual',
            'environment': config.environment, 'account_uid': config.account_uid,
            'observed_at_ms': stamp, 'collected_until_ms': actual['observed_at_ms'],
            'equity_usdt': str(wallet + q * (price - entry)), 'wallet_usdt': str(wallet),
            'entry_price_usdt': str(entry), 'btc_position': str(q), 'btc_price_usdt': str(price),
            'btc_direction': 'long' if q>0 else 'short' if q<0 else 'flat',
            'btc_notional_usdt': str(abs(q)*price),
            'stop_distance_loss_usdt': str(stop_loss) if stop_loss is not None else None,
            'unprotected_notional_usdt': str(abs(q)*price) if q and not actual['native_full_position_protected'] else '0',
            'available_usdt': actual['available_usdt'],
            'liquidation_price_usdt': str(liquidation),
            'liquidation_buffer_fraction': str((price - liquidation) / price if q > 0 else
                                               (liquidation - price) / price) if q and liquidation > 0 else None,
            'native_full_position_protected': actual['native_full_position_protected'],
            'possible_entry_remainders': actual['possible_entry_remainders'],
            'native_execution_verified': False, 'write_attempted': False}
