"""Read-only attribution of the already published 795-session simulation.

Pass the archived account, reports, input qualification metadata, and ten original
Binance 4h monthly ZIPs. No adapter, account, or exchange calls are made.
"""
import argparse
import bisect
import csv
import gzip
import hashlib
import json
import statistics
import zipfile
from collections import Counter, defaultdict
from decimal import Decimal as D, ROUND_CEILING, ROUND_FLOOR
from pathlib import Path

FOUR = 14_400_000
DAY = 86_400_000
MONTHS = ('2020-03','2020-04','2022-07','2022-08','2023-04',
          '2024-05','2024-08','2025-01','2025-02','2025-04')


def load_bars(h4_dir, qualification_path):
    qualified = json.loads(Path(qualification_path).read_text())['qualification_maps']['files']
    bars = {}
    for month in MONTHS:
        name = f'BTCUSDT-4h-{month}.zip'
        path = Path(h4_dir) / name
        original = [row['original_content_sha256'] for key,row in qualified.items()
                    if key.endswith('/klines/4h/' + name)]
        if len(original) != 1 or hashlib.sha256(path.read_bytes()).hexdigest() != original[0]:
            raise ValueError('4h archive differs from the registered original: ' + name)
        with zipfile.ZipFile(path) as source:
            for row in csv.reader(source.read(source.namelist()[0]).decode().splitlines()):
                if row[0].isdigit():
                    bars[int(row[0]) + FOUR] = (D(row[2]), D(row[3]), D(row[4]))
    return bars


def matching_primary(bars, first_fill_ms, target_take):
    complete = []
    matches = []
    for end in sorted(t for t in bars if first_fill_ms - 7 * DAY <= t <= first_fill_ms):
        if any(end - k * FOUR not in bars for k in range(16)):
            continue
        complete.append(end)
        prior = bars[end - FOUR][2]
        close = bars[end][2]
        atr = sum((max(bars[end - k * FOUR][0] - bars[end - k * FOUR][1],
                       abs(bars[end - k * FOUR][0] - bars[end - (k + 1) * FOUR][2]),
                       abs(bars[end - k * FOUR][1] - bars[end - (k + 1) * FOUR][2]))
                   for k in range(1, 15)), D(0)) / 14
        if close - prior > 3 * atr:
            stop = (prior + close) / 2
            take = close * (close / stop) ** 20
            if take.quantize(D('.1'), rounding=ROUND_CEILING) == target_take:
                matches.append((end, stop))
    return len(complete), matches


def main(account_path, reports_path, qualification_path, h4_dir, detail_output=None):
    account = json.loads(gzip.decompress(Path(account_path).read_bytes()))
    financial = account['financial']
    reports = [json.loads(line) for line in Path(reports_path).open()]
    assert account['no_live_account'] and not account['native_verified']
    assert financial['audit']['passed'] and len(reports) == account['session_count'] == 795
    starts = [row['start_ms'] for row in reports]
    assert starts == account['inputs']['starts_ms']
    id_to_client = {v['orderId']:k for k,v in financial['orders'].items() if 'orderId' in v}
    sent = financial['sent']
    sent_index = {v.get('newClientOrderId'):i for i,(method,path,v) in enumerate(sent)
                  if (method,path) == ('POST','/fapi/v1/order')}
    triggered = {int(v['actualOrderId']):v['orderType'] for v in financial['algos'].values()
                 if v.get('algoStatus') == 'FINISHED' and int(v.get('actualOrderId') or 0) > 0}
    bars = load_bars(h4_dir, qualification_path)

    position = D(0)
    rows = []
    for trade in sorted(financial['trades'], key=lambda r:(r['time'],r['id'])):
        if position == 0 and trade['side'] == 'BUY':
            rows.append({'first':trade, 'client':id_to_client[trade['orderId']]})
        position += D(trade['qty']) if trade['side'] == 'BUY' else -D(trade['qty'])
        if position == 0:
            rows[-1]['last'] = trade
    assert len(rows) == 50 and position == 0
    for number,row in enumerate(rows,1):
        first,last,client = row['first'],row['last'],row['client']
        session_index = bisect.bisect_right(starts,first['time']) - 1
        entry_report = reports[session_index]
        assert entry_report['entry_timing']['entry_id'] == client
        sent_at = entry_report['entry_timing']['entry_send_attempt_at_ms']
        assert 0 <= first['time'] - sent_at <= 5000, (number,first['time']-sent_at)
        context = [(k,report) for k,report in enumerate(reports[session_index:],session_index)
                   if (report.get('entry_timing') or {}).get('entry_id') == client
                   and report['start_ms'] <= last['time']]
        holds = [(k,report['model_preview']) for k,report in context
                 if (report.get('model_preview') or {}).get('action') == 'hold'
                 and report['model_preview']['position_campaign'] ==
                 (report['model_preview'].get('opportunity') or {}).get('identity')]
        assert len({m['position_campaign'] for _,m in holds}) <= 1

        stop_prices = []
        take_prices = []
        for method,path,payload in sent[sent_index[client]+1:]:
            if (method,path) == ('POST','/fapi/v1/order'):
                break
            if (method,path) == ('POST','/fapi/v1/algoOrder'):
                if payload.get('type') == 'STOP_MARKET':
                    stop_prices.append(D(payload['triggerPrice']))
                if payload.get('type') == 'TAKE_PROFIT_MARKET':
                    take_prices.append(D(payload['triggerPrice']))
        assert stop_prices and take_prices and len(set(take_prices)) == 1, (number,stop_prices,take_prices)
        if holds:
            identity = holds[0][1]['position_campaign']
            kind = 'primary' if identity > 0 else 'macro'
            model_stop = D(holds[0][1]['opportunity']['stop'])
            assert model_stop.quantize(D('.1'),rounding=ROUND_FLOOR) == stop_prices[-1]
            complete,matches = matching_primary(bars, first['time'],take_prices[0])
            if complete == 42:
                assert matches == ([(identity,model_stop)] if kind == 'primary' else [])
            provenance = 'same-entry-held-preview' if holds[0][0] == session_index else 'later-held-preview'
        else:
            complete,matches = matching_primary(bars, first['time'],take_prices[0])
            assert complete == 42 and len(matches) <= 1
            if matches:
                identity,model_stop = matches[0]
                assert model_stop.quantize(D('.1'),rounding=ROUND_FLOOR) == stop_prices[-1]
                kind = 'primary'
                provenance = 'qualified-h4-geometry'
            else:
                identity = None
                model_stop = None
                kind = 'macro'
                provenance = 'macro-type-only-no-durable-epoch'
        amounts = defaultdict(lambda:D(0))
        for event in financial['funding_ledger']:
            if first['time'] <= event['time'] <= last['time']:
                amounts[event['incomeType']] += D(event['income'])
        net = sum(amounts.values(),D(0))
        following = [k for k,start in enumerate(starts) if first['time'] < start < last['time']]
        next_index = following[0] if following else None
        proven_next = bool(next_index is not None and any(k == next_index for k,_ in holds))
        expire = identity + 7*DAY if kind == 'primary' else None
        rows[number-1] = {
            'n':number,'first_ms':first['time'],'last_ms':last['time'],
            'entry_session_index':session_index,'entry_session_start_ms':starts[session_index],
            'entry_report_preview':entry_report.get('model_preview') is not None,
            'kind':kind,'identity_ms':identity,'identity_provenance':provenance,
            'signal_age_hours':round((first['time']-identity)/3_600_000,3) if identity is not None and identity>0 else None,
            'model_stop':str(model_stop) if model_stop is not None else None,
            'first_native_stop':str(stop_prices[0]),'last_native_stop':str(stop_prices[-1]),
            'first_entry_price':first['price'],
            'original_stop_distance_pct':str((D(first['price'])-model_stop)/D(first['price'])*100)
                if model_stop is not None else None,
            'request_to_first_fill_ms':first['time']-sent_at,
            'fees_usdt':str(amounts['COMMISSION']),'funding_usdt':str(amounts['FUNDING_FEE']),
            'realized_usdt':str(amounts['REALIZED_PNL']),'net_usdt':str(net),
            'duration_hours':round((last['time']-first['time'])/3_600_000,3),
            'exit_reason':triggered.get(last['orderId'],'ORDINARY'),
            'next_session_index':next_index,'next_session_start_ms':starts[next_index] if next_index is not None else None,
            'next_session_proven_active':proven_next,
            'primary_expiry_ms':expire,
            'next_session_before_expiry':next_index is not None and expire is not None and starts[next_index] < expire,
        }
    assert sum((D(row['net_usdt']) for row in rows),D(0)) == D(financial['wallet_usdt'])-D(account['initial_usdt'])
    if detail_output:
        Path(detail_output).write_text(json.dumps(rows,indent=2))
    primary = [row for row in rows if row['kind'] == 'primary']
    short = [row for row in rows if row['duration_hours'] < 24]
    print(json.dumps({'campaigns':len(rows),'kind':dict(Counter(r['kind'] for r in rows)),
                      'provenance':dict(Counter(r['identity_provenance'] for r in rows)),
                      'exit':dict(Counter(r['exit_reason'] for r in rows)),
                      'primary_age_at_least_4h':sum(row['signal_age_hours'] >= 4 for row in primary),
                      'primary_age_median_h':statistics.median(row['signal_age_hours'] for row in primary),
                      'short_count':len(short),
                      'short_all_net_losers':all(D(row['net_usdt']) < 0 for row in short),
                      'short_no_next_manual_session':sum(row['next_session_index'] is None for row in short),
                      'request_fill_ms_range':[min(row['request_to_first_fill_ms'] for row in rows),
                                               max(row['request_to_first_fill_ms'] for row in rows)],
                      'wallet_reconciled':True},indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('account_gz')
    parser.add_argument('reports_jsonl')
    parser.add_argument('qualification_json')
    parser.add_argument('h4_dir')
    parser.add_argument('--detail-output',help='optional local anonymized campaign rows')
    args = parser.parse_args()
    main(args.account_gz,args.reports_jsonl,args.qualification_json,args.h4_dir,args.detail_output)
