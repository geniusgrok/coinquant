"""Independent registered wallets for risk, exit and information mechanisms.

Reuse the existing financial producer. No private adapter, background work,
changed historical schedule or curve scaling is provided here.
"""
from contextlib import contextmanager
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
import sys
import types
from types import SimpleNamespace
from unittest.mock import patch

from research import tradeoff_accounts as account


@contextmanager
def uniform_control(scale, *, binding):
    from coinquant import campaign, session
    from coinquant.types import Blocked
    scale = D(scale)
    if not scale.is_finite() or not D(0) < scale <= D(2):
        raise ValueError('finite preregistered initial dose required')
    identity = dict(family='fixed-initial-dose-control', scale=str(scale), binding=binding)
    old_guard = session._guard_strategy

    def guard(state):
        saved = state.get('lifecycle_identity')
        if saved != identity:
            if saved is not None or state.get('linear_campaign') is not None or state.db.execute(
                    'SELECT 1 FROM intents LIMIT 1').fetchone():
                raise Blocked('fixed-dose identity mismatch before recovery')
            state.set('lifecycle_identity', identity)
        return old_guard(state)

    with (patch.object(campaign, 'PRIMARY_RISK', str(D(campaign.PRIMARY_RISK)*scale)),
          patch.object(campaign, 'MACRO_RISK', str(D(campaign.MACRO_RISK)*scale)),
          patch.object(session, '_LIFECYCLE_IDENTITY', identity),
          patch.object(session, '_guard_strategy', guard), account.baseline() as selected):
        yield selected


def cached_market(spec, scratch, original, journal):
    """Progress-only immutable print packs; never shared account state."""
    import gzip
    import os
    import shutil
    import tempfile
    from datetime import datetime, timezone
    from research import session_market
    market, tape = original(spec, scratch)
    if not spec.get('shared_parsed_cache'):
        return market, tape
    limit = spec.get('shared_parsed_cache_max_bytes', 128_000_000)
    if type(limit) is not int or not 1 <= limit <= 256_000_000:
        raise ValueError('bounded derived print cache capacity required')
    # Current binary parser source and original ZIP digest bind each pack.
    parser = hashlib.sha256(Path(session_market.__file__).read_bytes()).hexdigest()
    shared = Path(spec['shared_parsed_cache'])/parser
    shared.mkdir(parents=True, exist_ok=True)
    private = scratch/'private-parsed-prints-cache'
    load = tape._load

    def cached(self, day):
        changed = day != self._day_ms
        name = f'BTCUSDT-aggTrades-{datetime.fromtimestamp(day/1000,timezone.utc):%Y-%m-%d}.zip'
        hit = False
        if changed:
            checksum = Path(spec['prints'])/(name+'.CHECKSUM')
            if checksum.exists():
                expected = checksum.read_text().split()[0]
                packed = shared/(name+'.'+expected+'.bin.gz')
                target = private/packed.name
                if packed.is_file() and not target.exists():
                    target.symlink_to(packed)
                    hit = True
        # Original load verifies selected official ZIP before reading a pack;
        # missing or unknown source remains original unknown, never empty data.
        rows = load(day)
        if not changed or rows is None:
            return rows
        qualified = self.loaded.get(name)
        binary = private/(name+'.'+str(qualified)+'.bin')
        packed = shared/(binary.name+'.gz')
        event = dict(event='parsed-cache', name=name, zip_sha256=qualified,
                     parser_sha256=parser, shared_hit=hit)
        if not binary.is_file():
            event['status'] = 'no-binary'
        elif packed.is_file():
            event['status'] = 'shared-hit' if hit else 'already-published'
        else:
            try:
                fd, temporary = tempfile.mkstemp(prefix='.publish-', dir=shared)
            except OSError as exc:
                event.update(status='cache-io-skip', error_type=type(exc).__name__)
                journal.append(event)
                return rows
            try:
                with os.fdopen(fd, 'wb') as dst, binary.open('rb') as src:
                    with gzip.GzipFile(filename='', fileobj=dst, mode='wb', compresslevel=1, mtime=0) as gz:
                        shutil.copyfileobj(src, gz)
                size = Path(temporary).stat().st_size
                used = sum(p.stat().st_size for p in shared.glob('*.bin.gz'))
                if used+size <= limit:
                    os.chmod(temporary, 0o400)
                    try:
                        os.link(temporary, packed)  # atomic immutable publish, no overwrite
                        event.update(status='published', gzip_bytes=size)
                    except FileExistsError:
                        event['status'] = 'already-published'
                else:
                    event.update(status='capacity-skip', gzip_bytes=size)
            except OSError as exc:
                event.update(status='cache-io-skip', error_type=type(exc).__name__)
            finally:
                Path(temporary).unlink(missing_ok=True)
        journal.append(event)
        return rows

    tape._load = types.MethodType(cached, tape)
    return market, tape


def main():
    spec_path = Path(sys.argv[sys.argv.index('--spec')+1])
    raw = spec_path.read_bytes()
    spec = json.loads(raw)
    policy = sys.argv[sys.argv.index('--policy')+1]
    begin = sys.argv[sys.argv.index('--begin')+1]
    out = Path(sys.argv[sys.argv.index('--out')+1])
    if policy != 'baseline' and [begin, dict(spec['windows'])[begin]] not in spec['policy_windows'].get(policy, []):
        raise ValueError('unregistered expression coverage window')
    scenario = 'base'
    if '--scenario' in sys.argv:
        at = sys.argv.index('--scenario')
        scenario = sys.argv[at+1]
        del sys.argv[at:at+2]
    if scenario not in ('base', 'fees-x1.5'):
        raise ValueError('unregistered cost scenario')
    binding = dict(specification_sha256=hashlib.sha256(raw).hexdigest(),
                   daily_sha256=spec['daily_sha256'], features_sha256=spec['features_sha256'],
                   window=[begin, dict(spec['windows'])[begin]], scenario=scenario)
    journal = []
    admission = None
    if policy.startswith('release-'):
        paths = spec['information_admission']
        info_raw = Path(paths['result']).read_bytes()
        admission = json.loads(info_raw)
        binding.update(information_result_sha256=hashlib.sha256(info_raw).hexdigest(),
                       information_spec_sha256=hashlib.sha256(Path(paths['spec']).read_bytes()).hexdigest())
    old_book, old_runtime = account.signal_book, account.policy_runtime
    old_market = account.bounded_market
    if account.KIND == 'coin':
        account.bounded_market = lambda selected_spec, scratch: cached_market(
            selected_spec, scratch, old_market, journal)

    def book_for(packet, expression, digest):
        book, bars = old_book(packet, 'baseline', digest)
        if expression.startswith('release-'):
            from research.incremental_information import ReleaseBook
            from research.edge_features import FeatureBook
            features = FeatureBook(Path(spec['features']), spec['features_sha256'])
            book = ReleaseBook(bars, features)
        if account.KIND == 'spot':
            bars = [row for row in bars if row[0] >= 1546300800000]
        return book, bars

    @contextmanager
    def runtime_for(expression, book):
        features = None
        if account.KIND == 'spot':
            from research.edge_features import FeatureBook
            features = FeatureBook(Path(spec['features']), spec['features_sha256'])
        prepared = False

        def run(config, venue, **kwargs):
            nonlocal prepared
            if account.KIND == 'spot':
                from research.session_account import HistoricalVenue
                expected = HistoricalVenue
            else:
                from research.complete_perp import ResearchExchange
                expected = ResearchExchange
            if not isinstance(venue, expected):
                raise ValueError('registered historical venue required before recovery')
            venue.offline = True
            if not prepared:
                if scenario == 'fees-x1.5':
                    venue.fee *= D('1.5')
                if expression == 'uniform-calibrated':
                    journal.append(dict(event='fixed-dose-control', scale=spec['control_scale'],
                                        exact_realized_exposure_match=False))
                prepared = True
            if expression == 'baseline':
                context = old_runtime(expression, book)
            elif expression == 'uniform-calibrated':
                context = uniform_control(spec['control_scale'], binding=binding)
            elif expression.startswith('release-'):
                from research.information_runtime import configured
                context = configured(expression, book=book, binding=binding, venue=venue,
                                     admission=admission, journal=journal, features=features)
            elif account.KIND == 'coin':
                from research.held_risk import configured
                context = configured(expression, binding=binding, journal=journal)
            else:
                from research.reason_exit import configured
                context = configured(expression, venue=venue, features=features,
                                     binding=binding, journal=journal)
            with context as selected:
                result = selected.run(config, venue, **kwargs)
                invalid = [error for error in result.get('errors', []) if error.get('error_type') in
                           ('TypeError', 'KeyError', 'ValueError', 'ArithmeticError') or
                           error.get('reason') == 'Invalid observation or state']
                if invalid:
                    raise ValueError('candidate integration failed: '+json.dumps(invalid))
                return result
        yield SimpleNamespace(run=run)

    account.signal_book, account.policy_runtime = book_for, runtime_for
    try:
        account.main()
        with Path(str(out)+'.journal.json').open('x') as stream:
            json.dump(account.serial(dict(binding=binding, policy=policy, scenario=scenario,
                account_sha256=hashlib.sha256(out.read_bytes()).hexdigest(), events=journal)), stream, indent=2)
            stream.write('\n')
    finally:
        account.signal_book, account.policy_runtime = old_book, old_runtime
        account.bounded_market = old_market


if __name__ == '__main__':
    main()
