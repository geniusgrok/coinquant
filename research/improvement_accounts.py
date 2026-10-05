"""Registered finite wallets, reusing the existing money/execution producer."""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

from research import tradeoff_accounts as account


def main():
    spec_path = Path(sys.argv[sys.argv.index('--spec') + 1])
    spec_raw = spec_path.read_bytes()
    spec = json.loads(spec_raw)
    policy = sys.argv[sys.argv.index('--policy') + 1]
    begin = sys.argv[sys.argv.index('--begin') + 1]
    out = Path(sys.argv[sys.argv.index('--out') + 1])
    scenario = 'base'
    if '--scenario' in sys.argv:
        at = sys.argv.index('--scenario')
        scenario = sys.argv[at + 1]
        del sys.argv[at:at + 2]
    if scenario not in ('base', 'fees-x1.5'):
        raise ValueError('unregistered cost scenario')
    binding = dict(specification_sha256=hashlib.sha256(spec_raw).hexdigest(),
                   daily_sha256=spec['daily_sha256'], features_sha256=spec['features_sha256'],
                   window=[begin, dict(spec['windows'])[begin]], scenario=scenario)
    journal = []
    old_book = account.signal_book
    old_runtime = account.policy_runtime

    def book_for(packet, expression, digest):
        book, bars = old_book(packet, 'baseline', digest)
        if account.KIND == 'spot':
            # The existing participation model owns the canonical 2019 origin.
            bars = [row for row in bars if row[0] >= 1546300800000]
        if expression.startswith('return-'):
            from research.return_core import Forecast
            from research.edge_features import FeatureBook
            features = FeatureBook(Path(spec['features']), spec['features_sha256'])
            funding = features.records['funding']
            book = Forecast(bars, funding, mode='positive' if expression == 'return-net' else 'low-turnover')
        return book, bars

    @contextmanager
    def runtime_for(expression, book):
        features = None
        if account.KIND == 'spot' and expression != 'baseline':
            from research.edge_features import FeatureBook
            features = FeatureBook(Path(spec['features']), spec['features_sha256'])
        prepared = False
        def run(config, venue, **kwargs):
            nonlocal prepared
            from decimal import Decimal
            if account.KIND == 'spot':
                from research.session_account import HistoricalVenue
                expected = HistoricalVenue
            else:
                from research.complete_perp import ResearchExchange
                expected = ResearchExchange
            if not isinstance(venue, expected):
                raise ValueError('finite historical venue required before recovery')
            venue.offline = True
            if not prepared:
                if scenario == 'fees-x1.5':
                    venue.fee *= Decimal('1.5')
                prepared = True
            if expression == 'baseline':
                context = old_runtime(expression, book)
            elif account.KIND == 'spot':
                from research.participation import configured
                context = configured(expression, venue=venue, features=features, binding=binding, journal=journal)
            elif expression.startswith('downside-'):
                from research.downside_budget import configured
                context = configured(expression, binding=binding, journal=journal)
            else:
                from research.return_core import configured
                context = configured(book, binding=binding, journal=journal)
            with context as selected:
                result = selected.run(config, venue, **kwargs)
                invalid = [error for error in result.get('errors', [])
                           if error.get('error_type') in ('TypeError', 'KeyError', 'ValueError', 'ArithmeticError')]
                if invalid:
                    raise ValueError('candidate integration failed: ' + json.dumps(invalid))
                return result
        yield SimpleNamespace(run=run)

    account.signal_book = book_for
    account.policy_runtime = runtime_for
    try:
        account.main()
        with Path(str(out) + '.journal.json').open('x') as stream:
            json.dump(account.serial(dict(binding=binding, policy=policy, scenario=scenario,
                account_sha256=hashlib.sha256(out.read_bytes()).hexdigest(), events=journal)), stream, indent=2)
            stream.write('\n')
    finally:
        account.signal_book, account.policy_runtime = old_book, old_runtime


if __name__ == '__main__':
    main()
