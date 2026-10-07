"""Read-only check of later manual starts for the frozen entry-shock deferral.

Inputs are the already attributed original offline wallet, its terminal reports,
SHA-qualified original UM 4h and mark ZIPs. Output omits session/order identities.
No counterfactual wallet, quote, fill or account action is produced.
"""
import argparse
import csv
from datetime import datetime, timezone
from decimal import Decimal as D
import gzip
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import zipfile

from coinquant.dfii10 import eligible
from coinquant.opportunities import Opportunities
from entry_shock_consistency import shock
from held_shock_support import DAY, daily_closes

ARCHIVE = 'c6223a5d1bd6ae46fd192668335cee31630ff33e'
FOUR = 14_400_000
FEE = D('.00075')


def source_digests():
    raw = subprocess.check_output([
        'git', 'show', f'{ARCHIVE}:backtest-source/data/qualified-market-metadata.json'])
    files = json.loads(raw)['qualification_maps']['files']
    return {key.rsplit('/', 1)[-1]: row['original_content_sha256']
            for key, row in files.items() if '/klines/4h/' in key or '/mark/1m/' in key}


def checked_rows(path, digests, original_name=None):
    if sha256(path.read_bytes()).hexdigest() != digests[original_name or path.name]:
        raise ValueError(f'original source digest mismatch: {path.name}')
    with zipfile.ZipFile(path) as source:
        for row in csv.reader(source.read(source.namelist()[0]).decode().splitlines()):
            if row and row[0].isdigit():
                yield row


def primary_at_starts(h4_dir, starts, digests):
    model = Opportunities()
    active = {}
    for path in sorted(h4_dir.glob('BTCUSDT-4h-*.zip')):
        for row in checked_rows(path, digests):
            end = int(row[0]) + FOUR
            opportunity = model.update(end, D(row[2]), D(row[3]), D(row[4]))
            if end in starts:
                active[end] = bool(opportunity and opportunity.direction > 0)
    if set(active) != starts:
        raise ValueError('later start missing completed 4h source')
    return active


def prior_mark(mark_dir, start, digests):
    month = datetime.fromtimestamp(start / 1000, timezone.utc).strftime('%Y-%m')
    name = f'BTCUSDT-1m-{month}.zip'
    path = mark_dir / f'coinquant-mark-1m-{month}.zip'
    rows = (row for row in checked_rows(path, digests, name) if int(row[6]) < start)
    last = None
    for row in rows:
        last = D(row[4])
    if last is None:
        raise ValueError('no completed mark before manual start')
    return last


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('intervals', type=Path)
    parser.add_argument('account_gz', type=Path)
    parser.add_argument('reports_jsonl', type=Path)
    parser.add_argument('h4_dir', type=Path)
    parser.add_argument('mark_dir', type=Path)
    args = parser.parse_args()
    intervals = json.loads(args.intervals.read_text())
    account = json.load(gzip.open(args.account_gz, 'rt'))
    reports = [json.loads(row) for row in args.reports_jsonl.open()]
    if not (len(intervals) == 50 and len(reports) == account['session_count'] == 795
            and account['no_live_account'] and not account['native_verified']
            and account['financial']['audit']['passed']
            and [r['start_ms'] for r in reports] == account['inputs']['starts_ms']):
        raise ValueError('original offline wallet identity or audit mismatch')
    closes = daily_closes(args.h4_dir)
    digests = source_digests()
    affected = [row for row in intervals if row['kind'] == 'macro'
                and shock(closes, row['entry_session_start_ms'] // DAY * DAY)]
    if len(affected) != 4:
        raise ValueError('expected four shocked original macro first fills')
    later = {r['market_through'] for row in affected for r in reports
             if row['first_ms'] < r['start_ms'] < row['last_ms']
             and r['start_ms'] - row['entry_session_start_ms'] < 7 * DAY}
    primary = primary_at_starts(args.h4_dir, later, digests)
    result = []
    for row in affected:
        sessions = [r for r in reports if row['first_ms'] < r['start_ms'] < row['last_ms']
                    and r['start_ms'] - row['entry_session_start_ms'] < 7 * DAY]
        statuses = []
        for r in sessions:
            preview = r.get('model_preview') or {}
            owned = (preview.get('action') == 'hold'
                     and preview.get('position_campaign') == row['identity_ms']
                     and D(str((r.get('actual') or {}).get('quantity_btc', 0))) > 0
                     and (r.get('actual') or {}).get('native_full_position_protected'))
            macro = preview.get('macro_observation')
            statuses.append((r, shock(closes, r['market_through'] // DAY * DAY),
                             bool(owned), bool(macro and eligible(macro, r['start_ms'])),
                             primary[r['market_through']]))
        first = next((r for r, label, owned, macro, competing in statuses
                      if label is False and owned and macro and not competing), None)
        entry = row['first_ms']
        date = datetime.fromtimestamp(entry / 1000, timezone.utc)
        summary = {
            'quarter': f'{date.year}Q{(date.month - 1) // 3 + 1}',
            'original_net_usdt': str(D(row['net_usdt']).quantize(D('.01'))),
            'later_manual_starts': len(statuses),
            'later_shock_labels': [label for _, label, _, _, _ in statuses],
            'all_owned_protected': all(owned for _, _, owned, _, _ in statuses) if statuses else None,
            'all_macro_eligible': all(macro for _, _, _, macro, _ in statuses) if statuses else None,
            'any_competing_primary': any(competing for _, _, _, _, competing in statuses),
        }
        if first:
            mark = prior_mark(args.mark_dir, first['start_ms'], digests)
            trades = account['financial']['trades']
            sells = [t for t in trades if first['start_ms'] <= t['time'] <= row['last_ms']
                     and t['side'] == 'SELL']
            buys = [t for t in trades if first['start_ms'] <= t['time'] <= row['last_ms']
                    and t['side'] == 'BUY']
            quantity = sum((D(t['qty']) for t in sells), D(0))
            sell_cash = sum((D(t['qty']) * D(t['price']) for t in sells), D(0))
            funding = sum((D(f['income']) for f in account['financial']['funding_ledger']
                           if f['incomeType'] == 'FUNDING_FEE'
                           and first['start_ms'] <= f['time'] <= row['last_ms']), D(0))
            if not quantity or buys or quantity != D(str(first['actual']['quantity_btc'])):
                raise ValueError('later original inventory cannot support conditional calculation')
            break_even = (sell_cash * (1 - FEE) + funding) / (quantity * (1 + FEE))
            conditional = sell_cash * (1 - FEE) + funding - quantity * mark * (1 + FEE)
            summary.update({
                'first_possible_reentry_delay_h': round((first['start_ms'] - entry) / 3_600_000, 2),
                'hours_to_original_exit': round((row['last_ms'] - first['start_ms']) / 3_600_000, 2),
                'prior_completed_mark': str(mark),
                'original_later_sell_vwap': str(sell_cash / quantity),
                'original_later_funding_usdt': str(funding.quantize(D('.01'))),
                'conditional_break_even_buy': str(break_even.quantize(D('.01'))),
                'required_buy_improvement_vs_mark_pct': str(((mark / break_even - 1) * 100).quantize(D('.001'))),
                'conditional_mark_buy_pnl_usdt': str(conditional.quantize(D('.01'))),
                'original_final_native_stop': row['last_native_stop'],
            })
        result.append(summary)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
