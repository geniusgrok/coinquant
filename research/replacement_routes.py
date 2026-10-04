"""Three BTC research predicates; no account, order, scheduler or adoption writes."""
import argparse
from decimal import Decimal as D
import json
from pathlib import Path

DAY = 86400000


def number(value, *, positive=False, nonnegative=False):
    if isinstance(value, bool):
        raise ValueError('boolean amount')
    result = D(str(value))
    if not result.is_finite() or positive and result <= 0 or nonnegative and result < 0:
        raise ValueError('invalid financial amount')
    return result


def causal(row, now, age):
    if (type(now) is not int or type(row['end_ms']) is not int
            or type(row['available_ms']) is not int
            or not row['end_ms'] <= row['available_ms'] <= now
            or not 0 <= now-row['end_ms'] <= age):
        raise ValueError('future or stale observation')
    sources = row['source_sha256']
    if not sources or any(not isinstance(s, str) or len(s) != 64
                          or any(c not in '0123456789abcdef' for c in s) for s in sources):
        raise ValueError('raw receipt bindings required')
    if row['base'] != 'BTC' or row['quote'] != 'USDT':
        raise ValueError('BTC/USDT units required; no implicit USD/USDC conversion')


def absorption(row, now):
    """Completed four-hour OI contraction plus liquidations and spot absorption."""
    if row is None:
        return dict(status='WAIT_INFORMATION',reason='OI, sell liquidations and signed spot flow absent')
    causal(row, now, 4*3600000)
    if row['end_ms']-row['start_ms'] != 4*3600000 or row['oi_unit'] != 'BTC':
        raise ValueError('same completed four-hour BTC flow/OI window required')
    before = number(row['oi_start_btc'], positive=True)
    after = number(row['oi_end_btc'], positive=True)
    buys = number(row['spot_buy_btc'], nonnegative=True)
    sells = number(row['spot_sell_btc'], nonnegative=True)
    forced = number(row['sell_liquidation_usdt'], nonnegative=True)
    turnover = number(row['perp_turnover_usdt'], positive=True)
    if not buys+sells or forced > turnover:
        raise ValueError('invalid flow denominator')
    contraction = 1-after/before
    imbalance = (buys-sells)/(buys+sells)
    trigger = contraction >= D('.05') and forced/turnover >= D('.01') and imbalance >= D('.10')
    return dict(status='EVENT_CANDIDATE' if trigger else 'NO_EVENT',
                oi_contraction=str(contraction),spot_imbalance=str(imbalance),
                earliest_decision_ms=row['available_ms'],holding_days=7,
                account_entrant=False,reason='requires matured non-overlapping outcomes and momentum/DFII10 controls')


def option_risk(row, now):
    """Near-25-delta IV is a disclosed risk proxy, never an ATM-IV substitute."""
    if row is None:
        return dict(status='WAIT_INFORMATION',reason='causal option and realized-volatility pair absent')
    causal(row, now, 60000)
    term = number(row['tenor_days'], positive=True)
    if not 20 <= term <= 40:
        raise ValueError('near thirty-day options required')
    if not D('.20') <= number(row['call_delta']) <= D('.30') or not D('-.30') <= number(row['put_delta']) <= D('-.20'):
        raise ValueError('near 25-delta greeks required')
    put = number(row['put_iv'], positive=True)
    call = number(row['call_iv'], positive=True)
    realized = number(row['realized_rms20_annual'], positive=True)
    if row['rv_completed_ms'] > row['available_ms'] or row['rv_available_ms'] > row['available_ms']:
        raise ValueError('future realized volatility')
    if not 0 <= row['end_ms']-row['rv_completed_ms'] <= 2*DAY:
        raise ValueError('stale realized volatility')
    risk = (put+call)/2/realized >= D('1.25') and put > call
    return dict(status='RISK_CANDIDATE' if risk else 'NO_EVENT',
                proposed_new_risk_factor='.5' if risk else '1',held_position_action='none',
                account_entrant=False,reason='compare future tail prediction and lost profits with fixed half-budget control')


def expiry_basis(row, now):
    """Executable-size basis screen with two funded wallets and cost reserves."""
    if row is None:
        return dict(status='WAIT_EXECUTABLE_PAIR',reason='dated linear contract, spot ask and futures bid absent')
    causal(row, now, 1000)
    if (row['contract_type'] != 'linear-dated' or row['settlement_currency'] != 'USDT'
            or row['expiry_ms'] <= now or row['spot_venue'] == '' or row['futures_venue'] == ''):
        raise ValueError('qualified BTC USDT dated contract required')
    stamps = [row['spot_book_ms'],row['futures_book_ms']]
    if any(type(t) is not int or not 0 <= now-t <= 1000 for t in stamps) or max(stamps)-min(stamps) > 250:
        raise ValueError('fresh paired executable books required')
    qty = number(row['quantity_btc'], positive=True)
    ask = number(row['spot_ask'], positive=True)
    bid = number(row['futures_bid'], positive=True)
    if qty > min(number(row['spot_ask_size_btc'],positive=True),number(row['futures_bid_size_btc'],positive=True)):
        raise ValueError('requested size exceeds quoted depth')
    days = D(row['expiry_ms']-now)/DAY
    # Round-trip rates and all reserves must be supplied explicitly; no maker assumption.
    fees = (ask*number(row['spot_roundtrip_fee'],nonnegative=True)
            + bid*number(row['futures_roundtrip_fee'],nonnegative=True))*qty
    funding = ask*qty*number(row['financing_annual'],nonnegative=True)*days/365
    reserves = number(row['slippage_reserve_usdt'],nonnegative=True)+number(row['settlement_basis_reserve_usdt'],nonnegative=True)
    collateral = number(row['futures_collateral_usdt'],positive=True)
    stress_fraction = number(row['stress_up_fraction'],positive=True)
    if stress_fraction < D('.30'):
        raise ValueError('registered thirty-percent upward margin stress required')
    stress = bid*qty*stress_fraction
    maintenance = bid*qty*number(row['maintenance_margin_fraction'],positive=True)
    if number(row['spot_cash_usdt'],positive=True) < ask*qty+fees or collateral < stress+maintenance+fees+funding+reserves:
        raise ValueError('independent spot cash or futures stress collateral insufficient')
    net = (bid-ask)*qty-fees-funding-reserves
    stressed_net = (bid-ask)*qty-2*fees-funding-2*reserves
    capital = ask*qty+fees+collateral
    return dict(status='COST_SCREEN_POSITIVE' if min(net,stressed_net)>0 else 'REJECT_COST',
                net_usdt=str(net),stress_net_usdt=str(stressed_net),
                simple_annualized_capital_return=str(net/capital*365/days),
                account_entrant=False,reason='settlement/index risk and actual joint margin path still need evidence; not locked profit')


def economic_gate(baseline, candidate):
    """Magnitude criterion only; verified comparable account evidence is separate."""
    a,b = number(baseline['cagr']),number(candidate['cagr'])
    x,y = number(baseline['mdd'],nonnegative=True),number(candidate['mdd'],nonnegative=True)
    if a <= 0 or not 0 < x < 1 or not 0 <= y < 1:
        raise ValueError('positive incumbent and valid drawdowns required')
    returns = b >= a*D('1.10') and y <= x
    risk = b >= a*D('.95') and y <= x*D('.80')
    return dict(magnitude_pass=returns or risk,return_route=returns,risk_route=risk,
                adopted=False,reason='requires comparable actual accounts, risk controls, cross-era and stressed evidence')


def evaluate(packet):
    now = packet['decision_ms']
    result = {}
    for name,fn in [('absorption',absorption),('option-risk',option_risk),('expiry-basis',expiry_basis)]:
        try:result[name]=fn(packet.get(name),now)
        except (KeyError,ValueError,TypeError,ArithmeticError) as error:
            result[name]=dict(status='BLOCK_INFORMATION',reason=str(error),account_entrant=False)
    return dict(routes=result,account_entrants=0,orders=0,qualification='RESEARCH_ONLY',
                provenance='Caller-supplied research context; predicates do not authenticate venue receipts')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packet',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    result=evaluate(json.loads(args.packet.read_text()))
    with args.out.open('x') as stream:stream.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
