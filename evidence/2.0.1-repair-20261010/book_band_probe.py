"""Read-only market/predicate probe; not an account replay or return estimate."""
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal as D, ROUND_CEILING
from pathlib import Path
from types import SimpleNamespace
import gzip
import hashlib
import json
import shutil
import sys

BASE = Path(__file__).resolve().parents[1]
TOOLING = BASE / 'coinquant-remeasure-tooling-v2'
sys.path[:0] = [str(BASE / 'coinquant'), str(TOOLING)]
from coinquant.types import floor_step
from research.session_exchange import SessionExchange
from research.session_market import Market, TradePrints


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def limit(book, side, tick):
    raw = book['ask'] * D('1.001') if side > 0 else book['bid'] * D('.999')
    return floor_step(raw, tick) if side > 0 else (raw / tick).to_integral_value(rounding=ROUND_CEILING) * tick


def comparison(before, after, side, tick):
    old_limit, new_limit = limit(before, side, tick), limit(after, side, tick)
    capacity = after['depth'] * D('.25') if (after['ask'] <= old_limit if side > 0 else after['bid'] >= old_limit) else D(0)
    band_ok = old_limit <= new_limit if side > 0 else old_limit >= new_limit
    return dict(original_limit=old_limit, fresh_band_limit=new_limit,
                exact_limit_accepts=old_limit == new_limit and capacity > 0,
                band_and_depth_accepts=band_ok and capacity > 0,
                capacity_inside_original_limit_btc=capacity,
                reason='outside_current_band' if not band_ok else 'no_depth_inside_original_limit' if not capacity else 'available')


spec = json.loads((BASE / 'coinquant-remeasure-2.0.0-v2/spec.json').read_text())
details_path = BASE / 'diagnosis/trade-path-details.json'
details = json.loads(details_path.read_text())
scratch = BASE / 'diagnosis/book-band-market-probe'
selected = scratch / 'selected'
selected.mkdir(parents=True, exist_ok=True)
cache = scratch / 'selected-cache'
cache.mkdir(exist_ok=True)
market = Market({}, [], root=spec['market'])
rules_path = TOOLING / 'evidence/bounded-session-20260926/public/rules.json'
rules = json.loads(rules_path.read_text())['instrument']
tick = D(next(rule['tickSize'] for rule in rules['filters'] if rule['filterType'] == 'PRICE_FILTER'))
exchange = object.__new__(SessionExchange)
exchange.market, exchange.rules = market, rules
results = []
inputs = {}

for case in details['delayed_same_campaign_entries']:
    start = case['original_session_current_terminal_report']['start_ms']
    date = datetime.fromtimestamp(start / 1000, timezone.utc).strftime('%Y-%m-%d')
    name = f'BTCUSDT-aggTrades-{date}.zip'
    raw = Path(spec['prints']) / name
    expected = Path(str(raw) + '.CHECKSUM').read_text().split()[0]
    assert sha(raw) == expected
    inputs[str(raw)] = expected
    for suffix in ('', '.CHECKSUM'):
        target = selected / (name + suffix)
        if not target.exists():
            target.symlink_to(Path(str(raw) + suffix))
    binary = cache / f'{name}.{expected}.bin'
    packed = Path(spec['shared_parsed_cache']) / spec['parser_sha256'] / (binary.name + '.gz')
    if not binary.exists() and packed.exists():
        with gzip.open(packed, 'rb') as source, binary.open('xb') as destination:
            shutil.copyfileobj(source, destination)
    exchange.prints = TradePrints(selected)

    def book(at):
        exchange.now_ms = at
        stamp, bid, ask, depth = exchange._book()
        return dict(request_at_ms=at, observed_at_ms=stamp, bid=bid, ask=ask, depth=depth)

    rows = []
    for offset in range(3800, 296000, 5000):
        before, after = book(start + offset), book(start + offset + 4200)
        fresh = abs(after['request_at_ms'] - after['observed_at_ms']) <= 15000
        same_bar = before['request_at_ms'] // 14400000 == after['observed_at_ms'] // 14400000
        rows.append(dict(before=before, after=after, fresh=fresh, same_bar=same_bar,
                         buy=comparison(before, after, 1, tick), sell=comparison(before, after, -1, tick)))
    summary = {}
    for key in ('buy', 'sell'):
        counts = Counter()
        for row in rows:
            if row['fresh'] and row['same_bar']:
                counts['fresh_same_bar_pairs'] += 1
                counts['exact_limit_accepts'] += row[key]['exact_limit_accepts']
                counts['band_and_depth_accepts'] += row[key]['band_and_depth_accepts']
                counts['only_band_accepts'] += row[key]['band_and_depth_accepts'] and not row[key]['exact_limit_accepts']
                counts[row[key]['reason']] += 1
        summary[key] = dict(counts)
    results.append(dict(campaign=case['campaign'], start_ms=start, date=date, summary=summary, pairs=rows))
    print(json.dumps(dict(date=date, summary=summary)), flush=True)
    # This probe's parser cache is disposable; no live/account state is opened.
    binary.unlink(missing_ok=True)

for relative, digest in market.loaded.items():
    inputs[str(Path(spec['market']) / relative)] = digest
proof = dict(kind='fixed-limit-fresh-band-market-predicate-probe',
    no_account_requests=True, no_account_state=True, no_orders=True,
    source_hashes={str(path):sha(path) for path in (Path(__file__), details_path,
        TOOLING / 'research/session_exchange.py', TOOLING / 'research/session_market.py', rules_path)},
    input_hashes=inputs, tick=str(tick), cases=results,
    selection='The same three sessions previously selected by original archived missing entry reports; no return based selection.',
    sampling='Pairs every 5 seconds within the original 300-second session. First quote at +3.8s, second +4.2s later, matching two ordinary ten-read account snapshots plus one final book read at 200ms/read.',
    limitations=['These are deterministic market observation pairs, not recovered actual failed request timestamps or account replays.',
        'The archived errors alone do not identify which internal book condition rejected each attempt.',
        'No planned quantity is invented: report maximum allowable quantity inside the unchanged original limit.',
        'No changed order price, quantity, risk budget, outcome, or CAGR is inferred from this predicate probe.'])
destination = BASE / 'diagnosis/book-band-probe.json'
destination.write_text(json.dumps(proof, default=str, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(dict(path=str(destination), sha256=sha(destination))))
