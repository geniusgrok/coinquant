"""Task6 review: synthetic pure probes only; no network/native/accounts/producers.
Run with the relevant repository on PYTHONPATH, argument spot or perp.
Test fixture initialization mocks clock, HTTP acquisition and final-export trust.
"""
import sys
from tests.test_edge_forward import ForwardTests
from research import edge_forward as f


def fixture():
    case = ForwardTests('test_proposal_modeled_fill_fee_net_conservation_and_checkpoint')
    case.setUp()
    return case


def next_print(case, stamp, close):
    receipts = case.observations(stamp, [close])
    receipt = next(r for r in receipts if r['category'] == 'trades')
    raw = f.dump([dict(a=101, p=close, q='100', T=stamp-120)])
    f.Path(receipt['path']).write_bytes(raw)
    receipt['sha256'] = f.sha(raw)
    return receipts


if sys.argv[1] == 'spot':
    case = fixture()
    try:
        state = case.enter()
        state = case.observe(case.initial + 3*f.INTERVAL, ['112'])
        print('T6-F1 before:', state['unresolved'], 'btc=', state['btc'])
        stamp = case.initial + 4*f.INTERVAL
        result = f.apply_observation(state, next_print(case, stamp, '80'), stamp, stamp+1, False, {})
        print('T6-F1 after:', result['unresolved'], 'btc=', result['btc'],
              'fills=', [(m['qty'], m['price'], m['time']) for m in result['events'][-1]['money']],
              'audit=', f.audit(result))
    finally:
        case.doCleanups()
    case = fixture()
    try:
        from spotquant.follow import _high_counts
        case.initial += 120000
        state = case.enter()
        w = next(iter(state['engine']['positions']))
        position = state['engine']['positions'][w]
        stamp = case.initial + 3*f.INTERVAL
        start = stamp//f.INTERVAL*f.INTERVAL-f.INTERVAL
        print('T6-F3 before:', 'entry_day_ms=', position['first_ms']%f.INTERVAL,
              'peak=', position['peak'], 'canonical_high_counts=', _high_counts(start, position['first_ms']))
        f.advance(state['engine'], [dict(start=start, end=start+f.INTERVAL,
                                       open='112', high='200', low='111', close='112')])
        print('T6-F3 after:', 'peak=', state['engine']['positions'][w]['peak'])
    finally:
        case.doCleanups()
    case = fixture()
    try:
        history = f.strict(case.history.read_bytes()); receipt = history[0]
        rows = f.strict(f.payload(receipt))
        for row in rows[-20:]:
            row[2] = '130'; row[3] = '70'
        raw = f.dump(rows); f.Path(receipt['path']).write_bytes(raw)
        receipt['sha256'] = f.sha(raw); case.history.write_bytes(f.dump(history))
        state = case.enter()
        print('T6-F4 stops:', [p['stop'] for p in state['engine']['positions'].values()])
        stamp = case.initial + 3*f.INTERVAL
        result = f.apply_observation(state, next_print(case, stamp, '100'), stamp, stamp+1, False, {})
        print('T6-F4 transition:', 'unresolved=', result['unresolved'],
              'money=', [(m['kind'], m['qty'], m.get('passive', False)) for m in result['events'][-1]['money']])
        try:
            print('T6-F4 audit:', f.audit(result))
        except Exception as error:
            print('T6-F4 audit rejection:', type(error).__name__, str(error))
    finally:
        case.doCleanups()
else:
    case = fixture()
    try:
        state = case.initialize(); stamp = case.initial+f.INTERVAL
        receipts = case.observations(stamp, ['100'])
        bars = f.bars_from([r for r in receipts if r['category']=='bars'], stamp)
        f.advance(state['engine'], bars)
        # Direct sizing-adapter probe after bootstrap. This is not a valid full
        # ledger/public-provenance fixture and makes no such claim.
        state['events'] = [{}]
        book = f.book_from(case.observations(stamp, ['112']), stamp)
        today = f.datetime.fromtimestamp(stamp/1000, f.timezone.utc).date()
        book['dfii10'] = dict(missing_reason=None,
            latest_observation_date=str(today-f.timedelta(days=3)),
            prior20_observation_date=str(today-f.timedelta(days=30)),
            latest_value='1.5', prior20_value='2', latest_value_available_ms=stamp-f.DAY,
            prior20_value_available_ms=stamp-f.DAY, asof_vintage_date=str(today-f.timedelta(days=3)),
            response_sha256='synthetic')
        proposal, money, simulation = f.coin_decide(state, bars, book, stamp, True)
        a = state['engine']['account']
        loss = f.number(a['q'])*(f.number(a['entry'])-f.number(a['sl']))
        budget = f.number(state['initial_wallet'])*f.D('.03')
        print('T6-F2:', 'action=', proposal['action'], 'macro_identity=', proposal['opportunity']['identity'],
              'qty=', a['q'], 'entry=', a['entry'], 'stop=', a['sl'],
              'stop_loss=', loss, 'canonical_3pct_budget=', budget, 'ratio=', loss/budget)
        print('T6-F2 target:', state['engine']['committed_target'], 'sizing=', simulation)
    finally:
        case.doCleanups()
