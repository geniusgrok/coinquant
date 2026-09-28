import hashlib
import tempfile
import zipfile
from datetime import datetime, timezone
from decimal import Decimal as D
from pathlib import Path
from unittest import TestCase

from coinquant.campaign import ORIGIN
from coinquant.config import Config
from coinquant.session import run
from research.session_exchange import SessionExchange
from research.session_market import FOUR, Market, TradePrints, four_hour_from_hours, WARMUP_TRADE, WARMUP_TRADE_SHA, _require
import json


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
        filled = exchange._fill_from_prints('BUY', D('100'), D('0.01'))
        self.assertEqual(filled, D('0.007'))
        self.assertEqual(exchange.funnel['ioc_filled'], 1)
        self.assertTrue(exchange.known_path)
        exchange.funnel['ioc_filled'] = 0
        missed = exchange._fill_from_prints('BUY', D('99'), D('0.01'))
        self.assertEqual(missed, 0)
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

    def test_ioc_fill_is_registered_at_arrival_and_answered_after_the_window(self):
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
        self.assertEqual(exchange.trades[-1]['time'], sent_at + 1000)
        self.assertEqual(exchange.now_ms, sent_at + 2000)

    def test_chase_bound_skips_an_extended_long_and_allows_the_signal_price(self):
        from coinquant.state import State

        def run_at(entry_price):
            bars, trade, mark = {}, {}, {}
            price = D(10000)
            cursor = ORIGIN
            for _ in range(40 * 6):
                bars[cursor] = (price, price + 2, price - 2, price, D(1000))
                cursor += FOUR_H
            shock = ORIGIN + 30 * DAY
            prior = bars[shock - FOUR_H][3]
            jumped = prior + 400
            bars[shock] = (prior, jumped + 2, prior - 2, jumped, D(1000))
            start = shock + FOUR_H
            _plant(trade, start - 60_000, entry_price)
            _plant(mark, start - 60_000, entry_price)
            _plant(trade, start, entry_price, high=entry_price)
            _plant(mark, start, entry_price)
            exchange = SessionExchange(Market(bars, (), identity={'trade': trade, 'mark': mark}), start,
                                       (D(10000) / D('6.9762')) * (D(1) - D('0.001')), matcher='unresolved')
            directory = tempfile.mkdtemp()
            with State(directory, 'binance:BTCUSDT:live:1') as state:
                state.set('enter_unconsumed_bootstrap', True)
                state.set('research_side', 'long')
                state.set('research_chase_bound', True)
            run(Config('1', directory, 10, 5), exchange, execute=True, monotonic=exchange.monotonic, wait=exchange.wait)
            return exchange

        self.assertEqual(run_at(D(10800)).funnel['ioc_submitted'], 0)
        self.assertGreaterEqual(run_at(D(10400)).funnel['ioc_submitted'], 1)

    def test_research_side_blocks_the_opposite_impulse(self):
        exchange, _start, _price = self._exchange('unresolved')
        directory = tempfile.mkdtemp()
        from coinquant.state import State
        with State(directory, 'binance:BTCUSDT:live:1') as state:
            state.set('enter_unconsumed_bootstrap', True)
            state.set('research_side', 'short')
        run(Config('1', directory, 10, 5), exchange, execute=True, monotonic=exchange.monotonic, wait=exchange.wait)
        self.assertEqual(exchange.funnel['ioc_submitted'], 0)
        self.assertEqual(exchange.q, 0)

    def test_bootstrap_flag_lets_the_first_active_impulse_enter(self):
        exchange, start, _price = self._exchange('unresolved')
        directory = tempfile.mkdtemp()
        from coinquant.state import State
        with State(directory, 'binance:BTCUSDT:live:1') as state:
            state.set('enter_unconsumed_bootstrap', True)
        run(Config('1', directory, 10, 5), exchange, execute=True, monotonic=exchange.monotonic, wait=exchange.wait)
        self.assertGreaterEqual(exchange.funnel['ioc_submitted'], 1)

    def test_schedule_module_does_not_hand_future_starts_to_the_exchange(self):
        source = Path('research/session_exchange.py').read_text(encoding='utf-8')
        self.assertNotIn('invocation_draws', source)
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
