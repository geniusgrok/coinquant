"""Economic meter: the production session runner over the frozen session schedule.

Every session runs `session.run` against SessionExchange, which replays Binance
trade prints, marks and funding. Knobs here are research inputs only; they
never reach a live reader.
"""
import argparse
import hashlib
import json
import shutil
import sqlite3
import subprocess
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal as D
from pathlib import Path

from coinquant import campaign, native_preview
from coinquant.config import Config
from coinquant.session import run
from research import session_schedule
from research.fx import BASIS as FX_BASIS, DatedFX
from research.session_exchange import SessionExchange
from research.session_market import TradePrints, load_base

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evidence' / 'rebuild-20260927'
PARTIAL = Path('/tmp/coinquant-partial')
START = '2020-01-01T00:00:00Z'
END = '2026-09-20T00:00:00Z'
CONVERSION = D('0.001')
YEAR_MS = 31_556_952_000


def timestamp(text):
    return int(datetime.fromisoformat(text.replace('Z', '+00:00')).timestamp() * 1000)


def iso(value):
    return datetime.fromtimestamp(value / 1000, timezone.utc).isoformat().replace('+00:00', 'Z')


def _harvest(state_dir):
    connection = sqlite3.connect(Path(state_dir) / 'intents.sqlite')
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
    return dict(fresh_observations=fresh, actions=dict(actions), reasons=dict(reasons),
                constraints=dict(constraints))


def run_account(market, starts, state_dir, prints, options):
    """One continuous CNY 10,000 account; exchange state persists between sessions."""
    wallet = (D(10000) / options['fx'](starts[0])) * (1 - CONVERSION)
    exchange = SessionExchange(market, starts[0], wallet, matcher='trade_print', prints=TradePrints(prints))
    for key, value in options.items():
        setattr(exchange, key, value)
    config = Config('1', str(state_dir), 300, 5)
    sessions = []
    for index, start in enumerate(starts):
        if exchange.now_ms > start:
            raise ValueError('session start is behind the exchange clock')
        if exchange.now_ms < start:
            exchange.advance_unattended(start)
        before = dict(exchange.funnel)
        report = run(config, exchange, execute=True, monotonic=exchange.monotonic, wait=exchange.wait)
        delta = {key: exchange.funnel[key] - before.get(key, 0) for key in exchange.funnel}
        sessions.append(dict(index=index, start=iso(start), report_status=report.get('status'),
                             cleanup=report.get('cleanup'), stop_reason=report.get('stop_reason'),
                             cycles=report.get('cycles'), funnel=delta, **_harvest(state_dir)))
        if index % 25 == 0:
            print(f'session {index} {iso(start)} status={report.get("status")} q={exchange.q} wallet={exchange.wallet}', flush=True)
    end = timestamp(END)
    if exchange.now_ms < end:
        exchange.advance_unattended(end)
    equity = exchange.wallet + (exchange.q * (exchange._mark_state()[1] - exchange.entry) if exchange.q else D(0))
    final_cny = equity * exchange._cny()
    years = D(end - timestamp(START)) / D(YEAR_MS)
    growth = D(final_cny) / D(10000)
    cagr = (float(growth) ** (1 / float(years)) - 1) if growth > 0 else -1
    return dict(matcher='trade_print', qualification='NOT_QUALIFIED', execution_class='print_quantity_upper_bound',
                sessions=len(sessions), final_usdt=str(equity), final_cny=str(final_cny),
                cagr=cagr, mdd_close=str(exchange.mdd_close), mdd_envelope=str(exchange.mdd_envelope),
                mdd_close_at=exchange.mdd_close_at, mdd_envelope_at=exchange.mdd_envelope_at,
                known_path=exchange.known_path, unknown_from=exchange.unknown_from,
                mark_gap_policy=exchange.mark_gap, mark_gap_minutes=len(exchange.bounded_minutes),
                hindsight_bounded=exchange.hindsight_bounded,
                path_complete=exchange.known_path and not exchange.hindsight_bounded,
                position=str(exchange.q), fees=str(exchange.fees), funding=str(exchange.funding_paid),
                funnel=dict(exchange.funnel), trades=exchange.trades, bounded_mark_minutes=exchange.bounded_minutes,
                print_miss_days=sorted(exchange.print_miss_days), session_rows=sessions,
                funding_ledger=[[row['time'], row['income']] for row in exchange.income
                                if row['incomeType'] == 'FUNDING_FEE'],
                daily_close_cny=[[iso(day * 86_400_000)[:10], str(value)]
                                 for day, value in sorted(exchange.daily_cny.items())]), exchange


def source_identity():
    """Git HEAD, dirty flag and a digest of the tracked production and meter sources."""
    def git(*args):
        return subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    files = sorted(git('ls-files', 'coinquant', 'research').split())
    digest = hashlib.sha256()
    for name in files:
        if name.endswith('.py'):
            digest.update(name.encode() + b'\0' + (ROOT / name).read_bytes() + b'\0')
    return dict(git_head=git('rev-parse', 'HEAD').strip(),
                dirty=bool(git('status', '--porcelain', '--', 'coinquant', 'research').strip()),
                python_sources_sha256=digest.hexdigest())


def trial(name, *, sequence='primary', participation=None, print_window_ms=1000,
          trigger_slippage='0.001', market_slippage='0.0005', fee='0.00075',
          primary_risk=None, mark_gap='bound', market='/data/coinquant-market', prints='/data/coinquant-prints',
          state=None, limit=0, out=None):
    source = source_identity()
    schedule = session_schedule.load()
    frozen = (schedule['primary'] if sequence == 'primary' else schedule['stress'][sequence])['starts_ms']
    starts = frozen[:limit or None]
    complete = len(starts) == len(frozen)
    if out is None:
        out = OUT if complete else PARTIAL
    saved = native_preview.BOOK_PARTICIPATION, campaign.PRIMARY_RISK
    try:
        if participation is not None:
            native_preview.BOOK_PARTICIPATION = D(participation)
        if primary_risk is not None:
            campaign.PRIMARY_RISK = str(primary_risk)
        effective = dict(book_participation=str(native_preview.BOOK_PARTICIPATION),
                         primary_risk=campaign.PRIMARY_RISK, macro_risk=campaign.MACRO_RISK)
        state = Path(state or f'/dev/shm/cq-{name}')
        if state.exists():
            shutil.rmtree(state)
        state.mkdir(parents=True)
        options = {'print_window_ms': int(print_window_ms), 'fx': DatedFX(), 'exit_conversion': CONVERSION,
                   'trigger_slippage': D(trigger_slippage), 'market_slippage': D(market_slippage),
                   'fee': D(fee), 'mark_gap': mark_gap}
        base = load_base(market)
        result, exchange = run_account(base, starts, state, prints, options)
    finally:
        native_preview.BOOK_PARTICIPATION, campaign.PRIMARY_RISK = saved
    identity = dict(base.identity)
    identity['loaded_minute_files'] = dict(sorted(base.loaded.items()))
    identity['loaded_print_files'] = dict(sorted(exchange.prints.loaded.items()))
    result.update(trial=name, sequence=sequence, schedule_sha256=schedule['primary']['sha256'],
                  sessions_requested=len(frozen), sessions_executed=len(starts), complete=complete,
                  print_window_ms=int(print_window_ms),
                  trigger_slippage=str(trigger_slippage), market_slippage=str(market_slippage), fee=str(fee),
                  mark_gap=mark_gap, fx=FX_BASIS, conversion='0.001 each way',
                  latency_ms=1000, price_stamp='last trade print at or before the request',
                  source=source, market_identity=identity, **effective)
    Path(out).mkdir(parents=True, exist_ok=True)
    (Path(out) / f'{name}.json').write_text(json.dumps(result, default=str) + '\n', encoding='utf-8')
    return result


def main():
    parser = argparse.ArgumentParser(description='One rebuild trial on the production session runner',
                                     epilog='Example: python3 -m research.rebuild P7 --limit 20')
    parser.add_argument('name')
    parser.add_argument('--sequence', default='primary', choices=('primary', 'absence', 'random_skip', 'block_21d'))
    parser.add_argument('--participation', default=None)
    parser.add_argument('--trigger-slippage', default='0.001')
    parser.add_argument('--market-slippage', default='0.0005')
    parser.add_argument('--fee', default='0.00075')
    parser.add_argument('--primary-risk', default=None)
    parser.add_argument('--print-window-ms', type=int, default=1000)
    parser.add_argument('--limit', type=int, default=0,
                        help='first N sessions only; a partial run is written under /tmp/coinquant-partial')
    parser.add_argument('--out', default=None, help='result directory (default: evidence for complete runs)')
    parser.add_argument('--market', default='/data/coinquant-market')
    parser.add_argument('--prints', default='/data/coinquant-prints')
    parser.add_argument('--mark-gap', default='bound', choices=('forfeit', 'bound'),
                        help='missing official mark minute: hindsight trade-range bound (owner-accepted basis, '
                             'default) or forfeit the isolated wallet')
    args = parser.parse_args()
    result = trial(args.name, sequence=args.sequence, participation=args.participation,
                   print_window_ms=args.print_window_ms, limit=args.limit, out=args.out,
                   trigger_slippage=args.trigger_slippage, market_slippage=args.market_slippage, fee=args.fee,
                   primary_risk=args.primary_risk, mark_gap=args.mark_gap, market=args.market, prints=args.prints)
    print(json.dumps({k: result[k] for k in ('trial', 'final_cny', 'cagr', 'mdd_close', 'mdd_envelope',
                                             'known_path', 'path_complete', 'mark_gap_minutes', 'complete',
                                             'funnel')}, default=str))


if __name__ == '__main__':
    main()
