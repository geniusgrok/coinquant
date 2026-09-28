"""Rebuild trials on the production session runner and the frozen schedule.

Every trial runs `session.run` against SessionExchange. Knobs here are
research inputs only; they never reach a live reader.
"""
import argparse
import json
import shutil
from decimal import Decimal as D
from pathlib import Path

from coinquant import campaign, native_preview
from research import session_schedule
from research.fx import DatedFX
from research.session_b0 import run_account
from research.session_market import load_base

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evidence' / 'rebuild-20260927'


def trial(name, *, sequence='primary', participation=None, print_window_ms=1000, side='both',
          trigger_slippage='0.001', market_slippage='0.0005', fee='0.00075',
          primary_risk=None, mark_gap='bound', market='/data/coinquant-market', prints='/data/coinquant-prints', state=None, limit=0):
    schedule = session_schedule.load()
    starts = (schedule['primary'] if sequence == 'primary' else schedule['stress'][sequence])['starts_ms']
    starts = starts[:limit or None]
    if participation is not None:
        native_preview.BOOK_PARTICIPATION = D(participation)
    if primary_risk is not None:
        campaign.PRIMARY_RISK = str(primary_risk)
    state = Path(state or f'/dev/shm/cq-{name}')
    if state.exists():
        shutil.rmtree(state)
    state.mkdir(parents=True)
    options = {'print_window_ms': int(print_window_ms), 'fx': DatedFX(), 'exit_conversion': D('0.001'),
               'trigger_slippage': D(trigger_slippage), 'market_slippage': D(market_slippage),
               'fee': D(fee), 'mark_gap': mark_gap}
    result = run_account(load_base(market), starts, state, matcher='trade_print', prints=prints, side=side,
                         exchange_options=options)
    result.update(trial=name, sequence=sequence, schedule_sha256=schedule['primary']['sha256'],
                  book_participation=str(native_preview.BOOK_PARTICIPATION), print_window_ms=int(print_window_ms),
                  trigger_slippage=str(trigger_slippage), market_slippage=str(market_slippage), fee=str(fee),
                  mark_gap=mark_gap, fx='FRED DEXCHUS dated', primary_risk=campaign.PRIMARY_RISK, macro_risk=campaign.MACRO_RISK, conversion='0.001 each way',
                  latency_ms=1000, price_stamp='last trade print at or before the request')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f'{name}.json').write_text(json.dumps(result, default=str) + '\n', encoding='utf-8')
    return result


def main():
    parser = argparse.ArgumentParser(description='One rebuild trial on the production session runner',
                                     epilog='Example: python3 -m research.rebuild R0 --participation 0.01')
    parser.add_argument('name')
    parser.add_argument('--sequence', default='primary', choices=('primary', 'absence', 'random_skip', 'block_21d'))
    parser.add_argument('--participation', default=None)
    parser.add_argument('--trigger-slippage', default='0.001')
    parser.add_argument('--market-slippage', default='0.0005')
    parser.add_argument('--fee', default='0.00075')
    parser.add_argument('--primary-risk', default=None)
    parser.add_argument('--print-window-ms', type=int, default=1000)
    parser.add_argument('--side', default='both', choices=('long', 'short', 'both'))
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--mark-gap', default='bound', choices=('forfeit', 'bound'),
                        help='missing official mark minute: hindsight trade-range bound (owner-accepted basis, '
                             'default) or forfeit the isolated wallet')
    args = parser.parse_args()
    result = trial(args.name, sequence=args.sequence, participation=args.participation,
                   print_window_ms=args.print_window_ms, side=args.side, limit=args.limit,
                   trigger_slippage=args.trigger_slippage, market_slippage=args.market_slippage, fee=args.fee,
                   primary_risk=args.primary_risk, mark_gap=args.mark_gap)
    print(json.dumps({k: result[k] for k in ('trial', 'final_cny', 'cagr', 'mdd_close', 'mdd_envelope',
                                             'known_path', 'path_complete', 'mark_gap_minutes', 'funnel')}, default=str))


if __name__ == '__main__':
    main()
