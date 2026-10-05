"""Bounded, separately funded comparisons for the benefits/harms policy."""
import argparse
from contextlib import contextmanager
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
import subprocess
import types

from research.core_accounts import baseline, serial, stamp
from research.history_core import Signals, runtime

ROOT = Path(__file__).resolve().parents[1]
KIND = ROOT.name.removesuffix('quant')
DAY = 86400000


def signal_book(packet, policy, digest):
    bars = [(int(t), *(D(row[k]) for k in ('open', 'high', 'low', 'close')))
            for t, row in sorted(packet['bars'].items(), key=lambda item: int(item[0]))]
    mode = 'channel' if KIND == 'coin' else 'defensive-base'
    book = Signals(bars, mode, digest)
    if policy == 'channel-short':
        book.mode = policy
        for row in book.rows:
            row['direction'] = min(0, row['direction'])
    elif policy in ('tactical', 'constant25'):
        book.mode = policy
        for row in book.rows:
            row['components'][30] = D('.25') if policy == 'constant25' else D(0)
            row['components'][40] = D(0) if policy == 'constant25' else row['components'][40]
            row['fraction'] = sum(row['components'].values(), D(0))
    return book, bars


@contextmanager
def policy_runtime(policy, book):
    from importlib import import_module
    from types import SimpleNamespace
    risk = import_module('coinquant.campaign') if KIND == 'coin' else None
    saved = (risk.PRIMARY_RISK, risk.MACRO_RISK) if risk else None
    if policy == 'uniform75' and risk:
        risk.PRIMARY_RISK, risk.MACRO_RISK = (str(D(x)*D('.75')) for x in saved)
    context = baseline() if policy in ('baseline', 'uniform75') else runtime(book)
    try:
        with context as selected:
            def run(config, venue, **kwargs):
                if not getattr(venue, 'offline', False):
                    raise ValueError('tradeoff accounts require an offline venue')
                return selected.run(config, venue, **kwargs)
            yield SimpleNamespace(run=run)
    finally:
        if risk:
            risk.PRIMARY_RISK, risk.MACRO_RISK = saved


def bounded_market(spec, scratch):
    """Reuse accepted parsed packs; retain at most one derived binary day."""
    from research.core_accounts import optimize_market
    market, tape = optimize_market(Path(spec['market']), Path(spec['prints']), scratch)
    private = scratch/'private-parsed-prints-cache'
    private.mkdir()
    link = scratch/'selected-prints-cache'
    link.unlink()
    link.symlink_to(private)
    tape.cache_dir = private
    for directory in spec['parsed_pack_roots']:
        for packed in Path(directory).glob('*.bin.gz'):
            target = private/packed.name
            if not target.exists():
                target.symlink_to(packed)
    original = tape._load
    def one_day(self, day):
        if day != self._day_ms:
            for binary in private.glob('*.bin'):
                binary.unlink()  # task-owned, regenerable; no wallet or source deletion
            self.days.clear()
        return original(day)
    tape._load = types.MethodType(one_day, tape)
    return market, tape


def main():
    import time
    from importlib import import_module
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--spec', type=Path, required=True)
    p.add_argument('--policy', required=True)
    p.add_argument('--begin', required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--scratch', type=Path, required=True)
    a = p.parse_args()
    spec = json.loads(a.spec.read_text())
    if a.policy not in spec['policies'][KIND] or a.begin not in dict(spec['windows']):
        raise ValueError('unregistered policy/window')
    if a.out.exists() or a.scratch.exists():
        raise ValueError('preserve prior receipt and account state')
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip():
        raise ValueError('freeze producer source before account execution')
    source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    raw = Path(spec['daily_packet']).read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    if sha != spec['daily_sha256']:
        raise ValueError('qualified daily input changed')
    book, bars = signal_book(json.loads(raw), a.policy, sha)
    schedule_path = Path(spec['schedule'])
    starts = json.loads(schedule_path.read_text())['primary']['starts_ms']
    end = dict(spec['windows'])[a.begin]
    b, e = stamp(a.begin), stamp(end)
    schedule = [s for s in starts if b <= s < e]
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.scratch.mkdir(parents=True)
    fx_module = import_module('research.unified_perp' if KIND == 'coin' else 'research.complete_spot')
    fx = fx_module.PriorFX(Path(spec['fx']))
    initial = D(10000)/fx(b)*D('.999')
    config_class = import_module(ROOT.name+'.config').Config
    state_class = import_module(ROOT.name+'.state').State
    if KIND == 'coin':
        from research.complete_perp import ResearchExchange
        from research.comparison_report import audit
        market, tape = bounded_market(spec, a.scratch)
        venue = ResearchExchange(market, b, initial, fx=fx, initial_cny=D(10000),
            matcher='trade_print', prints=tape, uid=12000, terminal_ms=e)
        venue.read_latency_ms, venue.latency_ms, venue.mark_gap = 200, 1000, 'bound'
        venue.offline = True  # This constructor is the finite historical venue, never an adapter.
        config = config_class('12000', str(a.scratch/'state'), 300, 5)
        move = venue.advance_unattended
    else:
        from research.session_account import HistoricalVenue, audit
        from research.edge_features import FeatureBook
        from research.adoption_spot import risk_identity
        origin = 1546300800000 if a.policy == 'baseline' else 1504224000000
        venue = HistoricalVenue([(t, o, h, l, c, D(0)) for t, o, h, l, c in bars if t >= origin], b, initial, fx)
        features = FeatureBook(Path(spec['features']), spec['features_sha256'])
        venue.crowding_features = lambda: features
        venue._adoption_risk = risk_identity(None)
        config = config_class('1', str(a.scratch/'state'), 300, 5, 'demo', '5000000')
        move = venue.advance
    reports, failure = [], None
    started = time.monotonic()
    with policy_runtime(a.policy, book) as selected:
        for s in schedule:
            try:
                move(s)
                r = selected.run(config, venue, execute=True, monotonic=venue.monotonic, wait=venue.wait)
                reports.append(dict(start_ms=s, **{k:r.get(k) for k in ('status', 'cleanup', 'cycles', 'errors',
                    'pending_intents', 'execution_unresolved', 'state_backup', 'session_archive')}))
                if any('history must start' in str(v) or 'incompatible' in str(v) for v in r.get('errors', [])):
                    failure = dict(phase='session', start_ms=s, reason='strategy state/history incompatible')
                    break
                if r.get('pending_intents') or r.get('execution_unresolved'):
                    failure = dict(phase='session', start_ms=s, reason='unresolved execution')
                    break
            except Exception as exc:
                failure = dict(phase='session', start_ms=s, reason=str(exc), error_type=type(exc).__name__)
                break
        if failure is None:
            try:
                move(e)
            except Exception as exc:
                failure = dict(phase='terminal', reason=str(exc), error_type=type(exc).__name__)
    with state_class(str(a.scratch/'state'), config.scope) as state:
        pending = state.pending()
        ownership = state.get('entry_fill' if KIND == 'coin' else 'positions')
    if KIND == 'coin':
        from research.rebuild import _final_mark
        try:
            mark = _final_mark(venue) if venue.q else D(0)
        except Exception:
            mark = None
        final = venue.wallet+venue.q*(mark-venue.entry) if mark is not None else None
        row = dict(trades=venue.trades, funding_ledger=venue.income, position=venue.q, fees=venue.fees,
            wallet_usdt=venue.wallet, entry=venue.entry, funding=venue.funding_paid, final_mark=mark, final_usdt=final,
            daily=[v for _, v in sorted(venue.daily.items())], mdd=venue.mdd_envelope, mdd_close=venue.mdd_close,
            known_path=venue.known_path, unknown_from=venue.unknown_from, hindsight_bounded=venue.hindsight_bounded,
            bounded_minutes=venue.bounded_minutes, funnel=venue.funnel,
            loaded_minute_files=market.loaded, loaded_print_files=tape.loaded)
        row['audit'] = audit(serial(row), initial, mark) if final is not None else dict(passed=False)
        for binary in (a.scratch/'private-parsed-prints-cache').glob('*.bin'):
            binary.unlink()
    else:
        final = venue.cash+venue.btc*venue.price
        row = dict(fills=venue.fills, daily=venue.daily, cash_usdt=venue.cash, btc=venue.btc,
                   mdd=venue.mdd, audit=audit(venue))
    row.update(identity=dict(source_head=source, specification_sha256=hashlib.sha256(a.spec.read_bytes()).hexdigest(),
        price_sha256=sha, features_sha256=spec['features_sha256'], fx_sha256=hashlib.sha256(Path(spec['fx']).read_bytes()).hexdigest(),
        schedule_sha256=hashlib.sha256(schedule_path.read_bytes()).hexdigest(), matcher='trade_print' if KIND == 'coin' else 'OHLC',
        read_latency_ms=200, write_latency_ms=1000, policy=a.policy),
        case=a.begin+'-'+a.policy, policy=a.policy, window=[a.begin, end], initial_cny='10000', initial_usdt=initial,
        final_usdt=final, final_cny=final*fx(e)*D('.999') if final is not None else None,
        sessions=reports, session_count=len(reports), registered_session_count=len(schedule), failure=failure,
        pending_intents=pending, ownership=ownership, elapsed_seconds=time.monotonic()-started,
        qualification='NOT_QUALIFIED', native_verified=False,
        price_model='original minute/envelope proxy' if KIND == 'coin' else 'high-before-low OHLC proxy')
    row['return_cny'] = row['final_cny']/10000-1 if final is not None else None
    row['complete_finite'] = failure is None and not pending and len(reports) == len(schedule) and row['audit']['passed']
    if subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() != source:
        raise ValueError('producer identity changed; preserve wallet without relabeling')
    with a.out.open('x') as stream:
        stream.write(json.dumps(serial(row), indent=2)+'\n')
    print(json.dumps(serial({k:row[k] for k in ('case', 'return_cny', 'mdd', 'complete_finite',
        'session_count', 'elapsed_seconds', 'failure')})), flush=True)


if __name__ == '__main__':
    main()
