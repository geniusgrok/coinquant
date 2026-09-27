"""Continuous session account on the production runner.

The schedule is the frozen 795 invocation timestamps used as session starts.
It is regenerated from the draw file and checked against the committed schedule
before any account is measured. The strategy never receives this list.
"""
from decimal import Decimal as D
import argparse
import json
import sqlite3
from collections import Counter
from pathlib import Path

from coinquant.config import Config
from coinquant.research import invocations, iso, spec, timestamp
from coinquant.session import run
from research.session_exchange import SessionExchange
from research.session_market import TradePrints, load_base


ROOT = Path(__file__).resolve().parents[1]
SCHEDULE_PATH = ROOT / 'evidence' / 'session-b0-20260927' / 'SCHEDULE.json'
END = '2026-09-20T00:00:00Z'
FX = D('6.9762')
CONVERSION = D('0.001')
YEAR_MS = 31_556_952_000


def schedule_body():
    """Timestamps only. Legacy spec supplies the frozen gaps, not Binance economics."""
    frozen = spec()
    primary = list(invocations(frozen))
    absence = list(invocations(frozen, stress=True))
    if len(primary) != 795 or len(absence) != 787:
        raise ValueError('frozen invocation count changed')
    if primary[0] < timestamp(frozen['start']) or primary[-1] >= timestamp(frozen['end']):
        raise ValueError('session starts leave the frozen window')
    return {
        'identity': 'session starts, not the legacy single-decision sample',
        'timezone': 'UTC',
        'start': frozen['start'],
        'end': frozen['end'],
        'session_seconds': 300,
        'poll_seconds': 5,
        'request_latency_ms': 1000,
        'draws_sha256': frozen['invocation_draws_sha256'],
        'gap_hours': frozen['gap_hours'],
        'count': len(primary),
        'starts_ms': primary,
        'absence_count': len(absence),
        'absence_starts_ms': absence,
        'development_end': frozen['development_end'],
        'development_sessions': sum(item < timestamp(frozen['development_end']) for item in primary),
    }


def write_schedule():
    body = schedule_body()
    SCHEDULE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCHEDULE_PATH.write_text(json.dumps(body) + '\n', encoding='utf-8')
    return body


def load_schedule():
    committed = json.loads(SCHEDULE_PATH.read_text(encoding='utf-8'))
    fresh = schedule_body()
    if committed['starts_ms'] != fresh['starts_ms'] or committed['absence_starts_ms'] != fresh['absence_starts_ms']:
        raise ValueError('committed session schedule does not match the frozen draws')
    if committed['request_latency_ms'] != 1000 or committed['session_seconds'] != 300 or committed['poll_seconds'] != 5:
        raise ValueError('committed session clock does not match the frozen protocol')
    return committed


def _harvest(state_dir):
    database = Path(state_dir) / 'intents.sqlite'
    connection = sqlite3.connect(database)
    rows = [json.loads(payload) for payload, in connection.execute('SELECT payload FROM observations')]
    connection.execute('DELETE FROM observations')
    connection.commit()
    connection.close()
    actions, reasons, constraints = Counter(), Counter(), Counter()
    fresh = 0
    for row in rows:
        preview = row.get('model_preview') or {}
        if preview.get('action'):
            actions[preview['action']] += 1
        if preview.get('entry_constraint'):
            constraints[preview['entry_constraint']] += 1
        if row.get('reason'):
            reasons[row['reason']] += 1
        if row.get('observation_current'):
            fresh += 1
    return dict(cycles=len(rows), fresh_observations=fresh, actions=dict(actions),
                reasons=dict(reasons), constraints=dict(constraints),
                status=rows[-1].get('status') if rows else 'missing',
                cleanup=rows[-1].get('cleanup') if rows else None)


def run_account(market, starts, state_dir, *, matcher='unresolved', prints=None, enter_bootstrap=False):
    wallet = (D(10000) / FX) * (1 - CONVERSION)
    book = TradePrints(prints) if matcher == 'trade_print' else None
    if matcher == 'trade_print' and prints is None:
        raise ValueError('trade_print requires --prints')
    exchange = SessionExchange(market, starts[0], wallet, matcher=matcher, prints=book)
    config = Config('1', str(state_dir), 300, 5)
    if enter_bootstrap:
        from coinquant.state import State
        with State(str(state_dir), 'binance:BTCUSDT:live:' + config.account_uid) as state:
            state.set('enter_unconsumed_bootstrap', True)
    sessions = []
    for index, start in enumerate(starts):
        if exchange.now_ms > start:
            raise ValueError('session start is behind the exchange clock')
        if exchange.now_ms < start:
            exchange.advance_unattended(start)
        before = dict(exchange.funnel)
        report = run(config, exchange, execute=True, monotonic=exchange.monotonic, wait=exchange.wait)
        harvested = _harvest(state_dir)
        delta = {key: exchange.funnel[key] - before.get(key, 0) for key in exchange.funnel}
        sessions.append(dict(index=index, start=iso(start), report_status=report.get('status'),
                             cleanup=report.get('cleanup'), stop_reason=report.get('stop_reason'),
                             cycles=report.get('cycles'), funnel=delta, **{
                                 key: harvested[key] for key in ('fresh_observations', 'actions', 'reasons', 'constraints')}))
        if index % 25 == 0:
            print(f'session {index} {iso(start)} status={report.get("status")} q={exchange.q} wallet={exchange.wallet}', flush=True)
    end = timestamp(END)
    if exchange.now_ms < end:
        exchange.advance_unattended(end)
    equity = exchange.wallet + (exchange.q * (exchange._mark_state()[1] - exchange.entry) if exchange.q else D(0))
    final_cny = equity * FX
    years = D(timestamp(END) - timestamp('2020-01-01T00:00:00Z')) / D(YEAR_MS)
    cagr = D(final_cny) / D(10000)
    cagr = (float(cagr) ** (1 / float(years)) - 1) if cagr > 0 else -1
    execution_class = {'unresolved': 'trade_print_absent', 'bar_through': 'noncausal_minute_bound',
                       'trade_print': 'print_quantity_upper_bound'}[matcher]
    return dict(matcher=matcher, qualification='NOT_QUALIFIED',
                execution_class=execution_class,
                sessions=len(sessions), final_usdt=str(equity), final_cny=str(final_cny),
                cagr=cagr, mdd_close=str(exchange.mdd_close), mdd_envelope=str(exchange.mdd_envelope),
                mdd_close_at=exchange.mdd_close_at, mdd_envelope_at=exchange.mdd_envelope_at,
                known_path=exchange.known_path, unknown_from=exchange.unknown_from,
                position=str(exchange.q), fees=str(exchange.fees), funding=str(exchange.funding_paid),
                funnel=dict(exchange.funnel), session_rows=sessions)


def main():
    parser = argparse.ArgumentParser(
        description='Frozen session schedule and B0 account',
        epilog='Examples:\n'
               '  python3 -m research.session_b0 schedule\n'
               '  python3 -m research.session_b0 run --market /tmp/coinquant-session-market '
               '--state /dev/shm/coinquant-session-b0 --matcher unresolved '
               '--output evidence/session-b0-20260927\n',
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('command', choices=('schedule', 'run'))
    parser.add_argument('--market', type=Path, default=Path('/tmp/coinquant-session-market'))
    parser.add_argument('--state', type=Path, default=Path('/dev/shm/coinquant-session-b0'))
    parser.add_argument('--matcher', choices=('unresolved', 'bar_through', 'trade_print'), default='unresolved')
    parser.add_argument('--prints', type=Path, default=None)
    parser.add_argument('--enter-bootstrap', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT / 'evidence' / 'session-b0-20260927')
    parser.add_argument('--limit', type=int, default=0)
    args = parser.parse_args()
    if args.command == 'schedule':
        body = write_schedule()
        print(json.dumps({key: body[key] for key in ('count', 'absence_count', 'development_sessions', 'request_latency_ms')}))
        return
    committed = load_schedule()
    market = load_base(args.market)
    starts = committed['starts_ms'][:args.limit or None]
    args.state.mkdir(parents=True, exist_ok=True)
    result = run_account(market, starts, args.state, matcher=args.matcher, prints=args.prints,
                         enter_bootstrap=args.enter_bootstrap)
    result['market'] = {key: market.identity[key] for key in ('four_hour_bars', 'funding_points', 'funding_gap_from',
                                                              'warmup_trade_sha256', 'warmup_funding_sha256')}
    args.output.mkdir(parents=True, exist_ok=True)
    if args.matcher == 'unresolved' and not args.limit:
        name = 'B0_SUMMARY.json'
    elif args.matcher == 'trade_print' and args.enter_bootstrap and not args.limit:
        name = 'B1_SUMMARY.json'
    elif args.matcher == 'trade_print' and not args.limit:
        name = 'PRINT_SUMMARY.json'
    else:
        name = f'SUMMARY_{args.matcher}_{len(starts)}.json'
    (args.output / name).write_text(json.dumps(result) + '\n', encoding='utf-8')
    print(json.dumps({key: result[key] for key in ('matcher', 'final_cny', 'cagr', 'mdd_close', 'mdd_envelope',
                                                    'known_path', 'position', 'funnel')}, default=str))


if __name__ == '__main__':
    main()
