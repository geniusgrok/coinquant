"""Completed-daily BTC forecasts and volatility budget; no account or venue I/O."""
from decimal import Decimal as D

RULE = 'btc-target-core-20261004-v1'
MODES = ('trend', 'uptrend', 'shock', 'downside', 'state')
DEADBAND = D('.05')


def forecast(closes, mode='trend'):
    if mode not in MODES:
        raise ValueError('unknown core mechanism')
    prices = [D(x) for x in closes]
    if any(not x.is_finite() or x <= 0 for x in prices):
        raise ValueError('invalid completed price')
    if len(prices) < 61:
        return D(0), D(0)
    returns = [b / a - 1 for a, b in zip(prices, prices[1:])]
    rms = (sum((r*r for r in returns[-20:]), D(0)) / 20).sqrt()
    if not rms:
        return D(0), D(0)
    trend = sum((max(D(-1), min(D(1), (prices[-1]/prices[-1-h]-1)
                 / (rms * D(h).sqrt()))) for h in (20, 60)), D(0))/2
    shock = D(0)
    # Independent shock-and-recovery, not a dip inside an existing trend.
    # The shock's threshold uses strictly preceding returns; no future close.
    for age in (1, 2, 3):
        index = len(returns)-1-age
        prior = returns[index-20:index]
        vol = (sum((r*r for r in prior), D(0))/20).sqrt()
        if not vol:
            continue
        event = returns[index]
        shock_close = prices[index+1]
        if event <= -2*vol and prices[-1] > shock_close:
            shock = D(4-age)/3
            break
        if event >= 2*vol and prices[-1] < shock_close:
            shock = -D(4-age)/3
            break
    signal = (trend if mode == 'trend' else max(D(0), trend) if mode == 'uptrend' else min(D(0), trend) if mode == 'downside'
              else shock if mode == 'shock' else trend if abs(trend) >= D('.35') else shock)
    return signal, rms * D(365).sqrt()


def exposure(closes, *, mode='trend', spot=False):
    signal, annual_vol = forecast(closes, mode)
    if not annual_vol:
        return D(0)
    budget = min(D('.95') if spot else D(2), D('.60')/annual_vol)
    return max(D(0), signal)*budget if spot else signal*budget
