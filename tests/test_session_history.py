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
        exchange.now_ms = base
        filled = exchange._fill_from_prints('BUY', D('100'), D('0.01'))
        self.assertEqual(filled, D('0.007'))
        self.assertEqual(exchange.funnel['ioc_filled'], 1)
        self.assertTrue(exchange.known_path)
        exchange.funnel['ioc_filled'] = 0
        missed = exchange._fill_from_prints('BUY', D('99'), D('0.01'))
        self.assertEqual(missed, 0)
        self.assertIsNone(TradePrints(directory).window(base + 86_400_000 + 1000, base + 86_400_000 + 2000))

    def test_missing_print_reject_does_not_leave_an_unknown_intent(self):
        exchange, _start, _price = self._exchange('trade_print')
        exchange.prints = TradePrints(Path(tempfile.mkdtemp()))
        directory = tempfile.mkdtemp()
        from coinquant.state import State
        with State(directory, 'binance:BTCUSDT:live:1') as state:
            state.set('enter_unconsumed_bootstrap', True)
        run(Config('1', directory, 10, 5), exchange, execute=True, monotonic=exchange.monotonic, wait=exchange.wait)
        exchange.advance_unattended(exchange.now_ms + 86_400_000)
        minute = exchange.now_ms // 60_000 * 60_000 - 60_000
        _plant(exchange.market.identity['trade'], minute, _price)
        _plant(exchange.market.identity['mark'], minute, _price)
        run(Config('1', directory, 10, 5), exchange, execute=True, monotonic=exchange.monotonic, wait=exchange.wait)
        import sqlite3
        rows = sqlite3.connect(str(Path(directory) / 'intents.sqlite')).execute(
            "SELECT status FROM intents WHERE kind='binance_order'").fetchall()
        self.assertGreaterEqual(len(rows), 2)
        self.assertTrue(all(status == 'confirmed' for status, in rows))
        self.assertFalse(exchange.known_path)
        self.assertTrue(exchange.print_miss_days)

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
