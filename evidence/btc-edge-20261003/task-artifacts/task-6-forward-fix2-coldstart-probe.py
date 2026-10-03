"""Pure synthetic F6 cold-start probe. No network/private/native/account work.
Mocks only clock, final export trust and acquisition; actual retained raw adapters,
Coin campaign, paper sizing/accounting, append and audit run unchanged.
"""
import io
from zipfile import ZipFile
from tests.test_edge_forward import ForwardTests
from research import edge_forward as f
from coinquant.campaign import Campaign

case = ForwardTests('test_deferred_first_observation_is_only_warmup_then_native_fresh_cross')
case.setUp()
try:
    pending = case.initialize_deferred()
    stamp = case.initial + 1000
    rows = f.strict(f.payload(f.strict(case.history.read_bytes())[0]))
    case.append_receipts(stamp, [case.receipt('klines?symbol=BTCUSDT&interval=4h', rows, stamp-100)])
    blocked = case.observe(case.initial+f.INTERVAL, ['100'])
    print('FIRST_DECISION', blocked['events'][-1]['proposal'], 'BTC', blocked['btc'])
    stamp = case.initial + 2*f.INTERVAL
    receipts = case.observations(stamp, ['112'])
    bar_receipt = next(r for r in receipts if r['category'] == 'bars')
    raw = f.dump([case.bar(stamp//f.INTERVAL*f.INTERVAL-f.INTERVAL, '100')])
    f.Path(bar_receipt['path']).write_bytes(raw); bar_receipt['sha256'] = f.sha(raw)
    today = f.datetime.fromtimestamp(stamp/1000, f.timezone.utc).date()
    vintage = today-f.timedelta(days=4)
    dates = [vintage-f.timedelta(days=20-i) for i in range(21)]
    form = ('<select id="form_selected_vintage_dates">' + ''.join('<option value="'+str(v)+'">' for v in dates) + '</select>').encode()
    form_path = case.root/'form.html'; form_path.write_bytes(form)
    csv = io.StringIO(); writer = f.csv.writer(csv)
    writer.writerow(['observation_date'] + [v.strftime('DFII10_%Y%m%d') for v in dates])
    for i in range(21):
        observed = today-f.timedelta(days=26-i)
        writer.writerow([str(observed)] + ['']*20 + [str(f.D('2')-f.D(i)/40)])
    archive = io.BytesIO()
    with ZipFile(archive, 'w') as z: z.writestr('DFII10.csv', csv.getvalue())
    receipt = case.receipt(f.DFII_URL, archive.getvalue(), stamp-100, raw=True)
    receipt.update(form_path=str(form_path), form_sha256=f.sha(form), vintages=[str(v) for v in dates])
    receipts.append(receipt)
    row = f.dfii_from(receipt, stamp)
    print('KNOWN_BEFORE_INIT', row['latest_value_available_ms'] < pending['initialized_ms'], 'LATEST_OBSERVATION', row['latest_observation_date'], 'VINTAGE', row['asof_vintage_date'])
    expected = Campaign.restore(blocked['engine']['campaign'])
    bars = f.bars_from([bar_receipt], stamp)
    for bar in bars: expected.update(bar['end'], bar['high'], bar['low'], bar['close'])
    expected.select_macro(row, '112', stamp, bootstrap=True)
    print('NATIVE_FIRST_VALID_MACRO_ACTION', expected.action(f.D(0)))
    result = case.append_receipts(stamp, receipts)
    print('EVENT_KINDS', [e['kind'] for e in result['events']])
    print('FIRST_VALID_MACRO_ACTION', result['events'][-1]['proposal']['action'], 'BTC', result['btc'])
    print('APPENDED_AND_RELOADED_AUDIT', f.audit(f.strict(case.diary.read_bytes())))
finally:
    case.doCleanups()
