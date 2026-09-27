"""Rebuild trials on the production session runner and the frozen schedule.

Every trial runs `session.run` against SessionExchange. Knobs here are
research inputs only; they never reach a live reader.
"""
import argparse
import json
import shutil
from decimal import Decimal as D
from pathlib import Path

from coinquant import native_preview
from research import session_schedule
from research.session_b0 import run_account
from research.session_market import load_base

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evidence' / 'rebuild-20260927'


def trial(name, *, sequence='primary', participation='0.01', print_window_ms=1000, side='both',
          market='/data/coinquant-market', prints='/data/coinquant-prints', state=None, limit=0):
    schedule = session_schedule.load()
    starts = (schedule['primary'] if sequence == 'primary' else schedule['stress'][sequence])['starts_ms']
    starts = starts[:limit or None]
    native_preview.BOOK_PARTICIPATION = D(participation)
    state = Path(state or f'/dev/shm/cq-{name}')
    if state.exists():
        shutil.rmtree(state)
    state.mkdir(parents=True)
    result = run_account(load_base(market), starts, state, matcher='trade_print', prints=prints, side=side,
                         exchange_options={'print_window_ms': int(print_window_ms)})
    result.update(trial=name, sequence=sequence, schedule_sha256=schedule['primary']['sha256'],
                  book_participation=participation, print_window_ms=int(print_window_ms))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f'{name}.json').write_text(json.dumps(result, default=str) + '\n', encoding='utf-8')
    return result


def main():
    parser = argparse.ArgumentParser(description='One rebuild trial on the production session runner',
                                     epilog='Example: python3 -m research.rebuild R0 --participation 0.01')
    parser.add_argument('name')
    parser.add_argument('--sequence', default='primary', choices=('primary', 'absence', 'random_skip', 'block_21d'))
    parser.add_argument('--participation', default='0.01')
    parser.add_argument('--print-window-ms', type=int, default=1000)
    parser.add_argument('--side', default='both', choices=('long', 'short', 'both'))
    parser.add_argument('--limit', type=int, default=0)
    args = parser.parse_args()
    result = trial(args.name, sequence=args.sequence, participation=args.participation,
                   print_window_ms=args.print_window_ms, side=args.side, limit=args.limit)
    print(json.dumps({k: result[k] for k in ('trial', 'final_cny', 'cagr', 'mdd_close', 'mdd_envelope',
                                             'known_path', 'funnel')}, default=str))


if __name__ == '__main__':
    main()
