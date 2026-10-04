import hashlib
import tempfile
import zipfile
from datetime import datetime, timezone
from decimal import Decimal as D
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from coinquant.campaign import ORIGIN
from coinquant.config import Config
from coinquant.session import run
from coinquant.types import Unknown
from research.session_exchange import SessionExchange
from research.session_market import FOUR, Market, TradePrints, four_hour_from_hours, WARMUP_TRADE, WARMUP_TRADE_SHA, _require
import json
from urllib.error import HTTPError


FOUR_H = 14_400_000
DAY = 86_400_000


def _market():
    trade, mark, bars = {}, {}, {}
    price = D(10000)
    cursor = ORIGIN
    # Forty days of calm four-hour bars, with a one-percent step at each UTC midnight.
    for _day in range(40):
        for slot in range(6):
            close = price
            bars[cursor] = (close, close + 2, close - 2, close, D(1000))
            cursor += FOUR_H
        price = (price * D('1.01')).quantize(D('0.1'))
    return bars, trade, mark, cursor


def _plant(table, open_ms, close, low=None, high=None):
    close = D(close)
    table[open_ms] = (close, high if high is not None else close + D('0.1'),
                      low if low is not None else close - D('0.1'), close, D(1000))


class SessionHistoryTests(TestCase):
    def test_warmup_hours_make_aligned_four_hour_bars(self):
        _require(WARMUP_TRADE, WARMUP_TRADE_SHA)
        bars = four_hour_from_hours(json.loads(WARMUP_TRADE.read_text(encoding='utf-8')))
        self.assertEqual(min(bars), ORIGIN)
        self.assertEqual(len(bars), 186)
        self.assertEqual(max(bars) + FOUR, int(datetime(2020, 1, 1, tzinfo=timezone.utc).timestamp() * 1000))

    def _exchange(self, matcher):
        bars, trade, mark, _cursor = _market()
        # First shock on day 25. Close jumps far enough to clear three ATRs.
        shock = ORIGIN + 25 * DAY
        prior = bars[shock - FOUR_H][3]
        jumped = prior + 400
        bars[shock] = (prior, jumped + 2, prior - 2, jumped, D(1000))
        start = shock + FOUR_H
        _plant(trade, start - 60_000, jumped)
        _plant(mark, start - 60_000, jumped)
        _plant(trade, start, jumped, high=jumped)
        _plant(mark, start, jumped)
        market = Market(bars, (), identity={'trade': trade, 'mark': mark})
        wallet = (D(10000) / D('6.9762')) * (D(1) - D('0.001'))
        return SessionExchange(market, start, wallet, matcher=matcher), start, jumped

    def test_unresolved_ioc_retries_without_a_fill(self):
        exchange, start, _price = self._exchange('unresolved')
        directory = tempfile.mkdtemp()
        # Cold start consumes the shock. A later shock is a new opportunity.
        run(Config('1', directory, 5, 5), exchange, execute=True, monotonic=exchange.monotonic, wait=exchange.wait)
        self.assertEqual(exchange.q, 0)
        second = start + 10 * DAY
        flat = exchange.market.bar4(start - FOUR_H)[3]
        cursor = start
        while cursor < second:
            exchange.market.h4[cursor] = (flat, flat + 2, flat - 2, flat, D(1000))
            cursor += FOUR_H
        jumped = flat + 400
        exchange.market.h4[second] = (flat, jumped + 2, flat - 2, jumped, D(1000))
        begin = second + FOUR_H
        _plant(exchange.market.identity['trade'], begin - 60_000, jumped)
        _plant(exchange.market.identity['mark'], begin - 60_000, jumped)
        exchange.advance_unattended(begin)
        sent = len(exchange.sent)
        run(Config('1', directory, 10, 5), exchange, execute=True, monotonic=exchange.monotonic, wait=exchange.wait)
        self.assertEqual(exchange.q, 0)
        self.assertGreaterEqual(exchange.funnel['ioc_submitted'], 1)
        self.assertEqual(exchange.funnel['ioc_filled'], 0)
        self.assertGreater(len(exchange.sent), sent)
        self.assertTrue(all(order['status'] == 'EXPIRED' and D(order['executedQty']) == 0
                            for order in exchange.orders.values() if order['type'] == 'LIMIT'))

    def test_exchange_stop_between_sessions_is_not_a_client_order(self):
        exchange, start, _price = self._exchange('bar_through')
        initial = exchange.wallet
        directory = tempfile.mkdtemp()
        run(Config('1', directory, 5, 5), exchange, execute=True, monotonic=exchange.monotonic, wait=exchange.wait)
        second = start + 10 * DAY
        flat = exchange.market.bar4(start - FOUR_H)[3]
        cursor = start
        while cursor < second:
            exchange.market.h4[cursor] = (flat, flat + 2, flat - 2, flat, D(1000))
            cursor += FOUR_H
        jumped = flat + 400
        exchange.market.h4[second] = (flat, jumped + 2, flat - 2, jumped, D(1000))
        begin = second + FOUR_H
        _plant(exchange.market.identity['trade'], begin - 60_000, jumped)
        _plant(exchange.market.identity['mark'], begin - 60_000, jumped)
        _plant(exchange.market.identity['trade'], begin, jumped, high=jumped)
        _plant(exchange.market.identity['mark'], begin, jumped)
        exchange.advance_unattended(begin)
        result = run(Config('1', directory, 10, 5), exchange, execute=True,
                     monotonic=exchange.monotonic, wait=exchange.wait)
        self.assertGreater(exchange.q, 0, result)
        self.assertGreaterEqual(exchange.funnel['protections'], 2)
        stop = next(D(algo['triggerPrice']) for algo in exchange.algos.values()
                    if algo['orderType'] == 'STOP_MARKET' and algo['algoStatus'] == 'NEW')
        sent = len(exchange.sent)
        # One quiet minute, then a minute that trades through the stop and not liquidation.
        quiet = (exchange.now_ms // 60_000 + 1) * 60_000
        _plant(exchange.market.identity['mark'], quiet, jumped)
        _plant(exchange.market.identity['mark'], quiet + 60_000, jumped, low=stop, high=jumped)
        exchange.advance_unattended(quiet + 120_000)
        self.assertEqual(exchange.q, 0)
        self.assertEqual(len(exchange.sent), sent)
        self.assertGreaterEqual(exchange.funnel['triggers'], 1)
        self.assertTrue(exchange.known_path)
        # Funds identity on a flat account: the wallet moved only by native income rows.
        self.assertEqual(exchange.wallet - initial, sum(D(row['income']) for row in exchange.income))
        commissions = [D(row['income']) for row in exchange.income if row['incomeType'] == 'COMMISSION']
        self.assertTrue(commissions and all(value < 0 for value in commissions))
        self.assertEqual(-sum(commissions), exchange.fees)
        self.assertEqual(exchange.margin, 0)

    def test_trade_print_window_fills_at_the_limit(self):
        directory = Path(tempfile.mkdtemp())
        day = datetime(2020, 1, 3, tzinfo=timezone.utc)
        base = int(day.timestamp() * 1000) + 60_000
        # Columns match vision aggTrades: id, price, qty, first, last, time, maker flag.
        lines = [
            f'1,100,1,1,1,{base + 999},false',
            f'2,99.5,0.003,2,2,{base + 1000},false',
            f'3,101,5,3,3,{base + 1200},true',
            f'4,100,0.004,4,4,{base + 1999},false',
            f'5,90,9,5,5,{base + 2000},false',
        ]
        payload = ('\n'.join(lines) + '\n').encode()
        path = directory / 'BTCUSDT-aggTrades-2020-01-03.zip'
        with zipfile.ZipFile(path, 'w') as archive:
            archive.writestr('BTCUSDT-aggTrades-2020-01-03.csv', payload)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        Path(str(path) + '.CHECKSUM').write_text(digest + '  BTCUSDT-aggTrades-2020-01-03.zip\n', encoding='utf-8')
        prints = TradePrints(directory)
        window = prints.window(base + 1000, base + 2000)
        self.assertEqual(window, [(D('99.5'), D('0.003')), (D('101'), D('5')), (D('100'), D('0.004'))])
        exchange, _start, _price = self._exchange('trade_print')
        exchange.prints = prints
        exchange.now_ms = base + 1000  # arrival after the request latency
        filled = sum(part for _stamp, part in exchange._fill_from_prints('BUY', D('100'), D('0.01')))
        self.assertEqual(filled, D('0.007'))
        self.assertEqual(exchange.funnel['ioc_filled'], 1)
        self.assertTrue(exchange.known_path)
        exchange.funnel['ioc_filled'] = 0
        missed = exchange._fill_from_prints('BUY', D('99'), D('0.01'))
        self.assertEqual(missed, [])
        self.assertIsNone(TradePrints(directory).window(base + 86_400_000 + 1000, base + 86_400_000 + 2000))

    def test_missing_prints_block_observation_before_any_order(self):
        exchange, _start, _price = self._exchange('trade_print')
        exchange.prints = TradePrints(Path(tempfile.mkdtemp()))
        directory = tempfile.mkdtemp()
        from coinquant.state import State
        with State(directory, 'binance:BTCUSDT:live:1') as state:
            state.set('enter_unconsumed_bootstrap', True)
        report = run(Config('1', directory, 10, 5), exchange, execute=True, monotonic=exchange.monotonic, wait=exchange.wait)
        self.assertEqual(report['status'], 'unknown')
        self.assertTrue(any('trade print' in e['reason'] for e in report['errors']), report['errors'])
        self.assertEqual(exchange.sent, [])
        self.assertEqual(exchange.q, 0)

    def test_ioc_fill_is_booked_at_its_print_and_answered_after_the_window(self):
        directory = Path(tempfile.mkdtemp())
        exchange, start, price = self._exchange('trade_print')
        day = datetime.fromtimestamp(start / 1000, timezone.utc)
        lines = [f'1,{price},5,1,1,{start - 500},false', f'2,{price},5,2,2,{start + 1500},false']
        path = directory / f'BTCUSDT-aggTrades-{day:%Y-%m-%d}.zip'
        with zipfile.ZipFile(path, 'w') as archive:
            archive.writestr(path.stem + '.csv', ('\n'.join(lines) + '\n').encode())
        Path(str(path) + '.CHECKSUM').write_text(hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + path.name + '\n', encoding='utf-8')
        exchange.prints = TradePrints(directory)
        stamp, _mark = exchange._mark_state()
        self.assertEqual(stamp, start - 500)
        sent_at = exchange.now_ms
        exchange._inflight = ('POST', '/fapi/v1/order', dict(
            symbol='BTCUSDT', side='BUY', type='LIMIT', timeInForce='IOC',
            quantity='0.01', price=str(price + 10), newClientOrderId='cq-t'))
        order = exchange._transport(None, 1)
        self.assertEqual(order['status'], 'FILLED')
        self.assertEqual(sent_at + 1000, start + 1000)
        self.assertEqual(exchange.trades[-1]['time'], start + 1500)
        self.assertEqual(exchange.now_ms, sent_at + 2000)

    def test_cold_start_consumes_the_already_active_impulse(self):
        exchange, _start, _price = self._exchange('unresolved')
        run(Config('1', tempfile.mkdtemp(), 10, 5), exchange, execute=True, monotonic=exchange.monotonic, wait=exchange.wait)
        self.assertEqual(exchange.funnel['ioc_submitted'], 0)
        self.assertEqual(exchange.q, 0)

    def test_schedule_module_does_not_hand_future_starts_to_the_exchange(self):
        source = Path('research/session_exchange.py').read_text(encoding='utf-8')
        self.assertNotIn('starts_ms', source)


class EnvelopePeakTests(TestCase):
    def test_intraminute_high_before_a_fall_is_a_peak(self):
        minute = ORIGIN + 30 * DAY
        mark = {minute: (D(100), D(110), D(100), D(100), D(1))}
        market = Market({}, (), identity={'trade': {}, 'mark': mark})
        exchange = SessionExchange(market, minute, D(2000))
        exchange.q, exchange.entry, exchange.margin = D(10), D(100), D(1000)
        exchange._on_minute(minute)
        self.assertEqual(exchange.mdd_envelope, 1 - D(2000) / D(2100))
        self.assertEqual(exchange.mdd_close, 0)

    def test_missing_mark_minute_forfeits_the_isolated_wallet_or_flags_hindsight(self):
        minute = ORIGIN + 30 * DAY
        trade = {minute: (D(100), D(101), D(99), D(100), D(1))}
        for policy in ('forfeit', 'bound'):
            market = Market({}, (), identity={'trade': dict(trade), 'mark': {}})
            exchange = SessionExchange(market, minute, D(2000))
            exchange.mark_gap = policy
            exchange.q, exchange.entry, exchange.margin = D(1), D(100), D(20)
            exchange.algos['s'] = dict(algoStatus='NEW', orderType='STOP_MARKET', triggerPrice='90',
                                       clientAlgoId='s', algoId=1)
            exchange._on_minute(minute)
            if policy == 'forfeit':
                self.assertEqual(exchange.q, 0)
                self.assertEqual(exchange.wallet, D(1980))
                self.assertFalse(exchange.hindsight_bounded)
            else:
                self.assertTrue(exchange.hindsight_bounded)


class IntraminuteEventTests(TestCase):
    MINUTE = 60_000

    def _venue(self, prints, funding=()):
        day = datetime(2020, 1, 3, tzinfo=timezone.utc)
        self.m = int(day.timestamp() * 1000) + 10 * self.MINUTE
        trade, mark = {}, {}
        _plant(trade, self.m - self.MINUTE, 10000)
        _plant(mark, self.m - self.MINUTE, 10000)
        _plant(trade, self.m, 10000, low=D(8500), high=D(10000))
        _plant(mark, self.m, 10000, low=D(8500), high=D(10000))
        market = Market({}, [(self.m + at, rate) for at, rate in funding], identity={'trade': trade, 'mark': mark})
        path = None
        if prints is not None:
            directory = Path(tempfile.mkdtemp())
            path = directory / f'BTCUSDT-aggTrades-{day:%Y-%m-%d}.zip'
            lines = [f'{i},{price},{qty},{i},{i},{self.m + at},false' for i, (at, price, qty) in enumerate(prints, 1)]
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr(path.stem + '.csv', ('\n'.join(lines) + '\n').encode())
            Path(str(path) + '.CHECKSUM').write_text(hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + path.name + '\n', encoding='utf-8')
        return SessionExchange(market, self.m + 1000, D(10000), matcher='trade_print',
                               prints=TradePrints(path.parent) if path else None)

    def _hold(self, exchange):
        exchange.q, exchange.entry, exchange.margin = D(1), D(10000), D(2000)
        exchange.held_from = exchange.now_ms
        exchange.algos['cq-stop'] = dict(algoStatus='NEW', orderType='STOP_MARKET', triggerPrice='9000')

    def _close_at(self, exchange, arrival):
        exchange.wait((arrival - exchange.latency_ms - exchange.now_ms) / 1000)
        exchange._inflight = ('POST', '/fapi/v1/order', dict(
            symbol='BTCUSDT', side='SELL', type='MARKET', quantity='1', reduceOnly='true', newClientOrderId='cq-x'))
        return exchange._transport(None, 1)

    def _close_refused(self, exchange, arrival):
        """The stop closed the position first: Binance refuses a reduce-only order with -2022."""
        with self.assertRaises(HTTPError) as caught:
            self._close_at(exchange, arrival)
        self.assertEqual(caught.exception.code, 400)
        self.assertEqual(json.loads(caught.exception.read())['code'], -2022)

    def test_stop_inside_the_minute_precedes_a_later_client_close(self):
        exchange = self._venue([(1000, 10000, 1), (10_000, 8500, 1), (20_000, 10000, 1)])
        self._hold(exchange)
        self._close_refused(exchange, self.m + 20_000)
        self.assertEqual(exchange.funnel['triggers'], 1)
        self.assertEqual(exchange.trades[-1]['time'], self.m + 10_000)
        self.assertEqual(D(exchange.trades[-1]['price']), 8500)  # the print gapped through the stop
        self.assertGreater(exchange.mdd_envelope, D('.09'))
        self.assertEqual(exchange.q, 0)

    def test_unordered_official_minute_applies_the_adverse_stop_before_a_close(self):
        exchange = self._venue(None)
        self._hold(exchange)
        self._close_refused(exchange, self.m + 20_000)
        self.assertEqual(exchange.funnel['partial_adverse'], 1)
        self.assertEqual(D(exchange.trades[-1]['price']), 9000)

    def test_overlapping_replacement_stops_fire_the_more_protective_leg(self):
        exchange = self._venue([(1000, 10000, 1), (10_000, 9400, 1), (20_000, 10000, 1)])
        self._hold(exchange)
        exchange.algos['cq-old'] = dict(algoStatus='NEW', orderType='STOP_MARKET', triggerPrice='9500')
        exchange.algos['cq-take'] = dict(algoStatus='NEW', orderType='TAKE_PROFIT_MARKET', triggerPrice='12000')
        self.assertEqual(exchange._triggers(), (D(9500), D(12000)))
        exchange.wait(30)
        self.assertEqual(exchange.q, 0)
        self.assertEqual(exchange.algos['cq-old']['algoStatus'], 'FINISHED')
        self.assertEqual(exchange.algos['cq-stop']['algoStatus'], 'CANCELED')

    def _write(self, exchange, path, params):
        exchange._inflight = ('POST', path, params)
        return exchange._transport(None, 1)

    def test_protection_that_would_trigger_immediately_and_bad_margin_are_refused_natively(self):
        exchange = self._venue([(1000, 10000, 1)])
        self._hold(exchange)
        exchange.algos.clear()
        stop = dict(symbol='BTCUSDT', side='SELL', type='STOP_MARKET', closePosition='true',
                    clientAlgoId='cq-late')
        with self.assertRaises(HTTPError) as caught:
            self._write(exchange, '/fapi/v1/algoOrder', {**stop, 'triggerPrice': '20000'})
        self.assertEqual(json.loads(caught.exception.read())['code'], -2021)
        self.assertNotIn('cq-late', exchange.algos)
        ok = self._write(exchange, '/fapi/v1/algoOrder', {**stop, 'triggerPrice': '8000'})
        self.assertEqual(ok['algoStatus'], 'NEW')
        for params in (dict(symbol='BTCUSDT', type=1, amount='999999'), dict(symbol='BTCUSDT', type=2, amount='1')):
            with self.assertRaises(HTTPError):
                self._write(exchange, '/fapi/v1/positionMargin', params)
        self.assertEqual(exchange.margin, D(2000))

    def test_funding_without_its_official_mark_is_unknown_not_the_entry_price(self):
        exchange = self._venue([(700, 10000, 5)], funding=[(500, D('0.001'))])
        self._hold(exchange)
        with patch.object(type(exchange.market), 'minute', return_value=None):
            with self.assertRaises(Unknown):
                exchange._pay_funding(self.m, self.m + 10_000)

    def test_fill_after_funding_settlement_pays_no_funding(self):
        exchange = self._venue([(700, 10000, 5)], funding=[(500, D('0.001'))])
        exchange.now_ms = self.m - 1000
        exchange._inflight = ('POST', '/fapi/v1/order', dict(
            symbol='BTCUSDT', side='BUY', type='LIMIT', timeInForce='IOC',
            quantity='0.1', price='10010', newClientOrderId='cq-e'))
        order = exchange._transport(None, 1)
        self.assertEqual(order['status'], 'FILLED')
        self.assertEqual(exchange.trades[-1]['time'], self.m + 700)
        self.assertEqual(exchange.funnel['funding'], 0)
        self.assertEqual(exchange.funding_paid, 0)

    def test_print_path_peak_counts_before_the_stop(self):
        exchange = self._venue([(1000, 10000, 1), (5000, 12000, 1), (10_000, 8500, 1), (20_000, 10000, 1)])
        self._hold(exchange)
        self._close_refused(exchange, self.m + 20_000)
        self.assertEqual(exchange.funnel['triggers'], 1)
        self.assertGreater(exchange.mdd_envelope, D('.29'))

    def test_stop_found_while_settling_an_add_drops_the_rest(self):
        exchange = self._venue([(1000, 10000, 1), (20_500, 10000, 5)])
        self._hold(exchange)
        exchange.wait(18)
        exchange._inflight = ('POST', '/fapi/v1/order', dict(
            symbol='BTCUSDT', side='BUY', type='LIMIT', timeInForce='IOC',
            quantity='0.1', price='10010', newClientOrderId='cq-a'))
        order = exchange._transport(None, 1)
        self.assertEqual(exchange.funnel['partial_adverse'], 1)
        self.assertEqual(order['status'], 'EXPIRED')
        self.assertEqual(D(order['executedQty']), 0)
        self.assertEqual(exchange.q, 0)

    def test_print_path_drawdown_does_not_depend_on_polling_steps(self):
        for sign in (1, -1):
            path = [(1000, 10000, 1), (6000, 10000 - sign * 1000, 1), (11_000, 10000 + sign * 2000, 1)]
            results = []
            for steps in ((20,), (5, 5, 5, 5)):
                exchange = self._venue(path)
                exchange.q, exchange.entry, exchange.margin = D(sign), D(10000), D(2000)
                exchange.held_from = exchange.now_ms
                exchange.algos['cq-take'] = dict(algoStatus='NEW', orderType='TAKE_PROFIT_MARKET',
                                                 triggerPrice=str(10000 + sign * 1200))
                for seconds in steps:
                    exchange.wait(seconds)
                self.assertEqual(exchange.q, 0)
                results.append((exchange.mdd_envelope, exchange.wallet, exchange.trades[-1]['time']))
            self.assertEqual(results[0], results[1])
            self.assertAlmostEqual(float(results[0][0]), 0.10, places=3)
