import tempfile
from decimal import Decimal as D
from unittest import TestCase

from coinquant.campaign import ORIGIN
from coinquant.config import Config
from coinquant.session import run
from coinquant.state import State
from research.session_exchange import SessionExchange
from research.session_market import Market


FOUR_H = 14_400_000
DAY = 86_400_000


def _plant(table, open_ms, close):
    close = D(close)
    table[open_ms] = (close, close + D('0.1'), close - D('0.1'), close, D(1000))


def _run(close, funding_rate):
    bars, trade, mark = {}, {}, {}
    price = D(10000)
    cursor = ORIGIN
    for _ in range(40 * 6):
        bars[cursor] = (price, price + 2, price - 2, price, D(1000))
        cursor += FOUR_H
    shock = ORIGIN + 30 * DAY
    # The bar must contain both the previous close and the new close.
    if close >= price:
        bars[shock] = (price, close + 2, price - 2, close, D(1000))
    else:
        bars[shock] = (price, price + 2, close - 2, close, D(1000))
    start = shock + FOUR_H
    _plant(trade, start - 60_000, close)
    _plant(mark, start - 60_000, close)
    _plant(trade, start, close)
    _plant(mark, start, close)
    funding = ((shock, D(funding_rate)),)
    wallet = (D(10000) / D('6.9762')) * (D(1) - D('0.001'))
    exchange = SessionExchange(Market(bars, funding, identity={'trade': trade, 'mark': mark}),
                               start, wallet, matcher='unresolved')
    directory = tempfile.mkdtemp()
    with State(directory, 'binance:BTCUSDT:live:1') as state:
        state.set('enter_unconsumed_bootstrap', True)
        state.set('research_funding_gate', True)
    run(Config('1', directory, 10, 5), exchange, execute=True, monotonic=exchange.monotonic, wait=exchange.wait)
    return exchange


class FundingGateTests(TestCase):
    def test_ordinary_funding_allows_a_long_and_a_crowded_long_does_not_send(self):
        allowed = _run(D(10400), '0.0001')
        crowded = _run(D(10400), '0.0003')
        self.assertGreaterEqual(allowed.funnel['ioc_submitted'], 1)
        self.assertEqual(crowded.funnel['ioc_submitted'], 0)

    def test_ordinary_funding_allows_a_short_and_a_crowded_short_is_skipped(self):
        from coinquant.lifecycle import Lifecycle

        class Reader:
            def __init__(self, rate):
                self.rate = rate

            def clock(self):
                return 0

            def last_settled_funding(self, _now):
                return self.rate

        def allows(rate):
            engine = Lifecycle.__new__(Lifecycle)
            engine.reader = Reader(D(rate))
            return engine._funding_allows({'side': 'SELL'})

        self.assertTrue(allows('0'))
        self.assertTrue(allows('-0.0001'))
        self.assertFalse(allows('-0.0003'))

    def test_long_only_default_sends_nothing_on_a_negative_impulse(self):
        self.assertEqual(_run(D(9600), '0').funnel['ioc_submitted'], 0)
