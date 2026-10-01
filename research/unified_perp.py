"""Three fixed candidates through their real runners on one historical venue."""
import argparse
import bisect
from contextlib import ExitStack
from dataclasses import asdict, replace
from datetime import datetime, timezone
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from coinquant.config import Config
from coinquant.session import run
from research import rebuild, session_schedule
from research.session_exchange import SessionExchange
from research.session_market import load_base, TradePrints, WARMUP_TRADE
from research.star_session import StarExchange, StarVenue
from coinquant.types import Unknown

DAY, HOUR, MINUTE = 86400000, 3600000, 60000


class PriorFX:
    """Existing peer fixing: only calendar dates strictly before today are used."""
    def __init__(self, path):
        raw = path.read_bytes()
        self.sha256 = hashlib.sha256(raw).hexdigest()
        rates = json.loads(raw)['rates']
        self.days = sorted(rates)
        self.rates = [D(str(rates[day]['CNY'])) for day in self.days]

    def __call__(self, stamp):
        day = datetime.fromtimestamp(stamp / 1000, timezone.utc).date().isoformat()
        index = bisect.bisect_left(self.days, day) - 1
        return self.rates[index] if index >= 0 else D('6.9615')

    def changes(self, start, end):
        return range((start // DAY + 1) * DAY, end + 1, DAY)


def source(path):
    def git(*args):
        return subprocess.check_output(['git', '-C', str(path), *args], text=True).strip()
    names = git('ls-files', '*.py').splitlines()
    digest = hashlib.sha256()
    for name in sorted(names):
        digest.update(name.encode() + b'\0' + (path / name).read_bytes() + b'\0')
    return {'git_head': git('rev-parse', 'HEAD'), 'dirty': bool(git('status', '--porcelain')),
            'python_sha256': digest.hexdigest()}


def star_cycle(exchange, store, cfg, minute_rows, hours, mode='run'):
    from btc_perp.bars import MinuteBar
    from btc_perp.model import Limits
    from btc_perp.runner import run_cycle
    from btc_perp.costs import MAX_NOTIONAL_20X
    now = exchange.now_ms
    cursor = store.load_book().cursor_ms
    begin = cursor if cursor else max(rebuild.timestamp(rebuild.START), now // MINUTE * MINUTE - 1000 * MINUTE)
    end = now // MINUTE * MINUTE
    bars = tuple(MinuteBar(stamp, *map(float, row[:4]), float(row[4] * row[3]), True)
                 for stamp, row in minute_rows(begin, end))
    known_hours = tuple(row for row in hours if row[0] + HOUR <= now)[-1400:]
    exchange.begin_cycle(120)
    return run_cycle(store, StarVenue(exchange), environment='demo', limits=Limits(None, None, None, 20),
        max_notional=MAX_NOTIONAL_20X, cfg=cfg, now_ms=now, bars=bars, channels=None,
        fx=float(exchange.fx(now)), mode=mode, prod_enabled=False, hour_rows=known_hours,
        clock=lambda: exchange.now_ms)


def measure(star_repo, market_root, prints_root, *, limit=None, restore_prints=False, checkpoint=None):
    sys.path.insert(0, str(star_repo))
    from btc_perp.config import load_config
    from btc_perp.store import Store
    identities = {'coinquant': source(rebuild.ROOT), 'starquant': source(star_repo)}
    if any(row['dirty'] for row in identities.values()):
        raise ValueError('commit both source trees before measurement')
    schedule = session_schedule.load()['primary']
    starts = schedule['starts_ms'][:limit]
    market = load_base(market_root)
    fx = PriorFX(star_repo / 'data/usdcny_frankfurter.json')
    cfg = load_config()
    hours = [(int(row[0]), float(row[2]), float(row[3])) for row in json.loads(WARMUP_TRADE.read_text())]
    last_hour = hours[-1][0]

    def minutes(begin, end):
        for stamp in range(begin, end, MINUTE):
            row = market.minute('trade', stamp)
            if row is None:
                raise ValueError(f'missing shared strategy minute {stamp}')
            yield stamp, row

    def extend_hours(now):
        nonlocal last_hour
        while last_hour + 2 * HOUR <= now:
            stamp = last_hour + HOUR
            rows = list(minutes(stamp, stamp + HOUR))
            hours.append((stamp, float(max(row[1][1] for row in rows)), float(min(row[1][2] for row in rows))))
            last_hour = stamp

    with tempfile.TemporaryDirectory(prefix='unified-perp-') as scratch, ExitStack() as stack:
        candidates = {}
        wallet = D(10000) / fx(starts[0]) * D('.999')
        for index, (name, config) in enumerate((('Coinquant-default', None), ('Starquant-baseline', cfg),
                                               ('Starquant-half-risk', replace(cfg, risk=.024)))):
            cls = SessionExchange if config is None else StarExchange
            if restore_prints:
                from research.rolling_prints import RollingPrints
                print_tape = RollingPrints(prints_root)
            else:
                print_tape = TradePrints(prints_root)
            exchange = cls(market, starts[0], wallet, matcher='trade_print', prints=print_tape, uid=9100 + index)
            exchange.fx, exchange.exit_conversion = fx, D('.001')
            exchange.read_latency_ms, exchange.latency_ms, exchange.mark_gap = 200, 1000, 'bound'
            directory = Path(scratch) / name
            store = None if config is None else stack.enter_context(Store(directory, 'demo'))
            candidates[name] = {'exchange': exchange, 'cfg': config, 'store': store, 'state': directory, 'sessions': []}
        failure = None
        try:
            for index, start in enumerate(starts):
                extend_hours(start + 420000)
                for name, candidate in candidates.items():
                    exchange, config = candidate['exchange'], candidate['cfg']
                    if exchange.now_ms < start:
                        exchange.advance_unattended(start)
                    if config is None:
                        report = run(Config(str(exchange.uid), str(candidate['state']), 300, 5), exchange,
                                     execute=True, monotonic=exchange.monotonic, wait=exchange.wait)
                        row = {'index': index, 'start_ms': start, 'status': report['status'],
                               'unresolved': report.get('execution_unresolved', False),
                               'actions': rebuild._harvest(candidate['state'])}
                    else:
                        deadline = start + 300000
                        cycles = []
                        while exchange.now_ms < deadline:
                            report = star_cycle(exchange, candidate['store'], config, minutes, hours)
                            cycles.append(asdict(report))
                            exchange.wait(min(5, max(0, (deadline - exchange.now_ms) / 1000)))
                        report = star_cycle(exchange, candidate['store'], config, minutes, hours, 'stop')
                        row = {'index': index, 'start_ms': start, 'cycles': cycles, 'cleanup': asdict(report),
                               'unresolved': bool(report.remaining)}
                    candidate['sessions'].append(row)
                if checkpoint is not None:
                    checkpoint.write_text(json.dumps({'sources': identities, 'last_complete_session': index,
                        'date': rebuild.iso(start), 'complete': False, 'comparable': False,
                        'accounts': {name: {'wallet': str(c['exchange'].wallet),
                            'position': str(c['exchange'].q), 'trades': len(c['exchange'].trades)}
                            for name, c in candidates.items()}}, indent=2) + '\n')
                if index % 10 == 0:
                    print(json.dumps({'session': index, 'date': rebuild.iso(start), 'positions': {
                        name: str(candidate['exchange'].q) for name, candidate in candidates.items()}}), flush=True)
        except (Unknown, OSError, ValueError, KeyError, TypeError) as exc:
            failure = {'type': type(exc).__name__, 'reason': str(exc), 'session': index}
        end = rebuild.timestamp(rebuild.END) if limit is None else starts[-1] + 420000
        results = {}
        for name, candidate in candidates.items():
            e = candidate['exchange']
            if failure is None:
                try:
                    e.advance_unattended(max(end, e.now_ms))
                except (Unknown, OSError, ValueError) as exc:
                    failure = {'type': type(exc).__name__, 'reason': str(exc), 'phase': 'finalization'}
            try:
                equity = e.wallet + (e.q * (rebuild._final_mark(e) - e.entry) if e.q else D(0))
            except (Unknown, ValueError):
                equity = None
            cny = equity * e._cny() if equity is not None else None
            years = (end - rebuild.timestamp(rebuild.START)) / rebuild.YEAR_MS
            results[name] = {'final_usdt': str(equity), 'final_cny': str(cny),
                'cagr': (float(cny / 10000) ** (1 / years) - 1 if cny > 0 else -1)
                    if cny is not None and failure is None and limit is None else None,
                'mdd': str(e.mdd_envelope), 'fees': str(e.fees), 'funding': str(e.funding_paid),
                'position': str(e.q), 'known_path': e.known_path, 'hindsight_bounded': e.hindsight_bounded,
                'unknown_from': e.unknown_from, 'complete': limit is None and failure is None,
                'execution_unresolved': sum(row['unresolved'] for row in candidate['sessions']),
                'trades': e.trades, 'sessions': candidate['sessions'],
                'loaded_print_files': e.prints.loaded, 'funding_ledger': e.income,
                'daily_cny': sorted(e.daily_cny.items()),
                'candidate_config': asdict(candidate['cfg']) if candidate['cfg'] else {'primary_risk': '7.5'}}
        return {'sources': identities, 'schedule_sha256': schedule['sha256'], 'results': results,
            'market_identity': market.identity, 'loaded_minute_files': market.loaded,
            'failure': failure, 'fx_sha256': fx.sha256, 'comparable': failure is None and limit is None and all(row['known_path']
                and not row['execution_unresolved'] for row in results.values()),
            'selected': None, 'native_execution_verified': False, 'out_of_sample': False,
            'conditions': {'fee': '.00075', 'read_latency_ms': 200, 'write_latency_ms': 1000,
                'conversion': '.001 each way', 'funding': 'same official calendar; missing means unknown',
                'fx': 'prior-date Frankfurter fixing; same for valuation and peer decision',
                'mark_gap': 'accepted 29-minute bound', 'fills': 'same print quantity upper bound',
                'operation': '795 frozen finite manual sessions; actual peer stop cleanup',
                'peer_demo_notional_ceiling_usdt': 5000000}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--star-repo', type=Path, default=Path('/workspace/starquant'))
    parser.add_argument('--market', type=Path, default=Path('/tmp/coinquant-market'))
    parser.add_argument('--prints', type=Path, default=Path('/tmp/coinquant-prints'))
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--limit', type=int)
    parser.add_argument('--restore-prints', action='store_true', help='Official on-demand task-owned rolling cache')
    args = parser.parse_args(argv)
    if args.out.exists() or (args.limit is not None and (not 1 <= args.limit <= 795 or
            not str(args.out.resolve()).startswith('/tmp/'))):
        parser.error('partial diagnostics stay in /tmp; never overwrite evidence')
    checkpoint = Path('/tmp') / ('btc-unified-' + hashlib.sha256(str(args.out.resolve()).encode()).hexdigest()[:12] + '.json')
    result = measure(args.star_repo, args.market, args.prints, limit=args.limit,
                     restore_prints=args.restore_prints, checkpoint=checkpoint)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x') as stream:
        json.dump(result, stream, default=str)
        stream.write('\n')
    print(json.dumps({'comparable': result['comparable'], 'failure': result['failure'],
                      'candidates': list(result['results'])}))
    return 2 if result['failure'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
