"""Strict decoding for the documented current Bybit inverse/UNIFIED schema."""
from .types import D, ZERO, SYMBOL, Blocked, Unknown, Position, Rules, Snapshot, number


def one(rows: list[dict], name: str) -> dict:
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise Unknown(f'{name} must contain exactly one authoritative record')
    return rows[0]


def position(row: dict) -> Position:
    try:
        if row['symbol'] != SYMBOL or row['positionStatus'] != 'Normal':
            raise Blocked('unexpected instrument or position status')
        if row['autoAddMargin'] != 0 or row['isReduceOnly'] is not False:
            raise Blocked('automatic margin addition or exchange reduce-only restriction is active')
        size = number(row['size'])
        if size < 0 or row['side'] not in ('Buy', 'Sell', ''):
            raise Unknown('invalid position side or quantity')
        if (size > 0 and row['side'] == '') or (size == 0 and row['side'] not in ('', 'Buy', 'Sell')):
            raise Unknown('inconsistent position direction')
        sign = 1 if row['side'] == 'Buy' else -1
        return Position(size * sign, number(row['avgPrice']) if size else ZERO,
                        number(row['positionIM']), number(row['liqPrice'], positive=True) if size else ZERO,
                        number(row['takeProfit']), number(row['stopLoss']),
                        number(row['leverage'], positive=True), int(row['positionIdx']))
    except (KeyError, ValueError, TypeError) as exc:
        raise Unknown('incomplete position schema; never assume flat') from exc


def rules(instrument: dict, tiers: list[dict], fee: dict, mark: D) -> Rules:
    try:
        if (instrument['symbol'], instrument['contractType'], instrument['settleCoin']) != (SYMBOL, 'InversePerpetual', 'BTC'):
            raise Blocked('expected BTC-settled BTCUSD inverse perpetual')
        tier = one([t for t in tiers if str(t['isLowestRisk']) == '1' and t['symbol'] == SYMBOL], 'base risk tier')
        # Current inverse API documentation expresses rates in percentage points
        # and position limits in BTC. Reject a changed unit convention, do not
        # silently guess from magnitude or apply a linear-contract parser.
        im, max_leverage = number(tier['initialMargin']), number(tier['maxLeverage'])
        if abs(im * max_leverage - 100) > D('0.1'):
            raise Blocked('inverse risk-rate units differ from the verified documentation')
        if max_leverage < 20 or not number(instrument['leverageFilter']['minLeverage']) <= 20 <= number(instrument['leverageFilter']['maxLeverage']):
            raise Blocked('20x not supported by current instrument or risk tier')
        size = instrument['lotSizeFilter']
        return Rules(number(instrument['priceFilter']['tickSize']), number(size['qtyStep']),
                     number(size['minOrderQty']), min(number(size['maxOrderQty']), number(size['maxMktOrderQty'])),
                     number(tier['riskLimitValue']) * mark, number(tier['maintenanceMargin']) / 100,
                     number(fee['takerFeeRate']), int(instrument['launchTime']), instrument['status'])
    except (KeyError, TypeError, ValueError) as exc:
        raise Unknown('incomplete native instrument, fee or risk-tier data') from exc


def snapshot(uid: str, timestamp: int, account: dict, wallet: dict, row: dict,
             instrument: dict, tiers: list[dict], fee: dict, ticker: dict,
             book: dict, orders: list[dict], fills: list[dict], slippage: D) -> Snapshot:
    try:
        if wallet['accountType'] != 'UNIFIED':
            raise Blocked('only current UNIFIED account schema is implemented')
        coins = wallet['coin']
        if any(c['coin'] != 'BTC' and any(number(c[k]) != 0 for k in ('equity', 'walletBalance', 'borrowAmount')) for c in coins):
            raise Blocked('use a dedicated BTC-funded account; other assets are not managed')
        btc = one([c for c in coins if c['coin'] == 'BTC'], 'BTC collateral')
        if any(number(btc[k]) != 0 for k in ('borrowAmount', 'accruedInterest', 'spotBorrow', 'bonus', 'locked')):
            raise Blocked('borrowed, bonus or spot-locked collateral is not supported')
        p = position(row)
        mark, bid, ask = (number(ticker[k], k, positive=True) for k in ('markPrice', 'bid1Price', 'ask1Price'))
        if ticker['symbol'] != SYMBOL or book['s'] != SYMBOL or abs(timestamp - int(book['ts'])) > 10_000:
            raise Unknown('wrong or stale BTC quotation')
        bids, asks = book['b'], book['a']
        if not bids or not asks or number(bids[0][0]) > number(asks[0][0]):
            raise Unknown('missing or crossed orderbook')
        depth_buy = sum((number(q) for price, q in asks if number(price) <= ask * (1 + slippage)), ZERO)
        depth_sell = sum((number(q) for price, q in bids if number(price) >= bid * (1 - slippage)), ZERO)
        balance = number(btc['walletBalance'])
        available = balance - sum((number(btc[k]) for k in ('totalPositionIM', 'totalOrderIM', 'locked', 'bonus')), ZERO)
        # Verify that BTC P&L belongs to the reconciled BTCUSD position, not an
        # unrelated BTC-settled option/future. Price differences use source mark.
        reported_pnl = number(row['unrealisedPnl'])
        at_source_mark = p.pnl(number(row['markPrice'], positive=True))
        if abs(reported_pnl - at_source_mark) > D('0.00000003'):
            raise Unknown('position P&L is inconsistent with inverse contract arithmetic')
        if abs(number(btc['unrealisedPnl']) - reported_pnl) > D('0.00000003'):
            raise Unknown('wallet and BTCUSD P&L do not reconcile')
        if abs(number(btc['equity']) - balance - number(btc['unrealisedPnl'])) > D('0.00000003'):
            raise Unknown('wallet equity contains unsupported positions or liabilities')
        result = Snapshot(uid, timestamp, balance, available, mark, bid, ask, depth_buy, depth_sell,
                          p, rules(instrument, tiers, fee, mark), tuple(orders), tuple(fills),
                          account['marginMode'], number(ticker['fundingRate']))
        result.validate()
        return result
    except (KeyError, TypeError, ValueError) as exc:
        raise Unknown('account or market snapshot schema incomplete') from exc
