import tempfile
import time
from io import BytesIO
from unittest import TestCase
from unittest.mock import Mock
from urllib.error import HTTPError

from coinquant.binance import Binance
from coinquant.config import Config
from coinquant.session import run
from coinquant.types import Unknown
from tests.session_venue import Venue
from research.session_exchange import SessionExchange
from research.session_market import Market
from research.session_replay import Tape
from decimal import Decimal as D


class VirtualClockTests(TestCase):
    def test_positive_submillisecond_wait_advances_virtual_venues(self):
        for venue in (Venue(), SessionExchange(Market({}, ()), 1000, D(100)), Tape([], 1000)):
            before = venue.now if isinstance(venue, (Venue, Tape)) else venue.now_ms
            venue.wait(0.0001)
            self.assertEqual(venue.now if isinstance(venue, (Venue, Tape)) else venue.now_ms, before + 1)

    def test_injected_monotonic_is_not_the_wall_clock(self):
        wall = time.monotonic()
        venue = Binance(monotonic=lambda: 10**9, opener=Mock())
        venue.begin_cycle(10)
        self.assertEqual(venue.deadline, 10**9 + 10)
        self.assertNotEqual(venue.deadline, wall + 10)
        venue.request_weights.append((10**9 - 10, 2190))
        with self.assertRaises(Unknown):
            venue.ensure_capacity(20)
        venue.request_weights.clear()
        venue.request_weights.append((10**9 - 120, 2190))
        venue.ensure_capacity(20)

    def test_entry_budget_uses_the_venue_clock(self):
        tmp = tempfile.TemporaryDirectory()
        venue = Venue()
        venue.seed(tmp.name)
        seen = {}
        original = venue.send

        def send(method, path, payload):
            if method == 'POST' and path.endswith('/order') and payload.get('reduceOnly') != 'true':
                seen['deadline'] = venue.deadline
                seen['clock'] = venue.monotonic()
            return original(method, path, payload)

        venue.send = send
        run(Config('123', tmp.name, 3, 1), venue, execute=True, monotonic=venue.monotonic, wait=venue.wait)
        self.assertEqual(seen['deadline'], seen['clock'] + 120)
        self.assertGreater(seen['clock'], 10**8)
        self.assertLess(time.monotonic(), 10**6)
        self.assertEqual(venue.deadline, venue.monotonic() + 120)
        tmp.cleanup()

    def test_rate_limit_cooldown_stays_on_the_injected_clock(self):
        opener = Mock()
        opener.open.side_effect = HTTPError('https://fapi.binance.com', 429, 'rate', {'Retry-After': '90'}, BytesIO(b''))
        clock = {'now': 1000.0}
        venue = Binance(monotonic=lambda: clock['now'], opener=opener, clock=lambda: 1_700_000_000)
        with self.assertRaises(Unknown):
            venue.get('/fapi/v1/time')
        self.assertEqual(venue.cooldown_until, 1090)
        clock['now'] = 1089
        with self.assertRaises(Unknown):
            venue.get('/fapi/v1/time')
        self.assertEqual(opener.open.call_count, 1)
