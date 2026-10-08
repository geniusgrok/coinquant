"""A refused or never-sent safety intent leaves nothing at the exchange and may be tried again."""
import tempfile
import unittest

from coinquant.binance_safety import _once, protect_existing, settled_protection
from coinquant.state import State
from coinquant.types import Blocked, NotSent, Rejected, Unknown
from tests.test_binance_safety import Native, rules


class RejectedIntentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = State(self.tmp.name, 'binance:BTCUSDT:live:123').__enter__()
        self.native = Native()

    def tearDown(self):
        self.state.__exit__()
        self.tmp.cleanup()

    def protect(self, send):
        return protect_existing(self.native, self.state, send, '123', 100, '95000', '110000',
                                instrument=rules(), authorized=True)

    def test_locally_refused_protection_is_retried_under_the_same_identity(self):
        def refuse(*args):
            raise NotSent('local request-weight reserve unavailable')
        with self.assertRaises(Blocked):
            self.protect(refuse)
        self.assertEqual(self.native.sent, [])
        stop = next(iter(self.state.db.execute("SELECT id,status FROM intents")))
        self.assertEqual(stop[1], 'rejected')
        self.assertTrue(settled_protection(self.native, self.state, stop[0]))
        after = self.protect(self.native.send)
        self.assertTrue(after['native_full_position_protected'])
        self.assertEqual(len(self.native.sent), 2)
        self.assertEqual(self.state.pending(), [])
        row = self.state.db.execute('SELECT status FROM intents WHERE id=?', (stop[0],)).fetchone()
        self.assertEqual(row[0], 'confirmed')

    def test_rejected_entry_is_never_prepared_again(self):
        payload = dict(symbol='BTCUSDT', side='BUY', type='LIMIT', quantity='1')
        self.state.prepare('cq-entry', 'binance_order', payload)
        self.state.finish('cq-entry', 'rejected', {'not_sent': 'deadline'})
        with self.assertRaises(Unknown):
            self.state.prepare('cq-entry', 'binance_order', payload)

    def test_refused_cancel_is_left_to_the_target_state(self):
        def refuse(*args):
            raise Rejected('Binance rejected the request with code -2011')
        _once(self.state, 'cq-cancel', 'binance_algo_cancel', {'clientAlgoId': 'cq-x'}, refuse,
              'DELETE', '/fapi/v1/algoOrder', at_ms=0)
        status = self.state.db.execute("SELECT status FROM intents WHERE id='cq-cancel'").fetchone()[0]
        self.assertEqual(status, 'rejected')
        sent = []
        _once(self.state, 'cq-cancel', 'binance_algo_cancel', {'clientAlgoId': 'cq-x'},
              lambda *args: sent.append(args), 'DELETE', '/fapi/v1/algoOrder', at_ms=0)
        self.assertEqual(len(sent), 1)
