"""Offline checkpoint money/identity boundaries; no historical wallet replay."""
from collections import deque
from datetime import date
from decimal import Decimal as D
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from coinquant.config import Config
from research.complete_perp import ResearchExchange
from research.replay_checkpoint import (ReplayTimings, decode, digest, encode,
                                       restore_venue, snapshot_venue, source_fingerprint)
from research.session_market import Market, TradePrints
from research.unified_perp import PriorFX


class MockLockedState:
    """A pure SQLite boundary fixture, never a real account or OS lock."""
    def __init__(self, identity):
        self.identity = identity
        self.lock, self.account_lock = object(), object()
        self.db = sqlite3.connect(':memory:')
        self.db.execute('CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        self.db.execute('CREATE TABLE intents (id TEXT PRIMARY KEY, status TEXT NOT NULL)')
        self.put('identity', identity)
        self.put('campaign', {'last': 1000, 'primary_consumed': 123})

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def put(self, key, value):
        self.db.execute('INSERT OR REPLACE INTO meta VALUES (?,?)', (key, json.dumps(value)))

    def get(self, key):
        row = self.db.execute('SELECT value FROM meta WHERE key=?', (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def pending(self):
        return list(self.db.execute("SELECT id FROM intents WHERE status IN ('unknown','partial')"))


class CheckpointTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        fx_file = self.root/'fx.json'
        fx_file.write_text(json.dumps({'rates': {'2019-12-31': {'CNY': '7'}}}))
        self.fx = PriorFX(fx_file)
        self.config = Config('12000', str(self.root/'state'), 300, 5)
        self.binding = dict(source_sha256=source_fingerprint(), strategy_sha256='1'*64,
                            input_sha256='2'*64, schedule_sha256='3'*64)
        self.state = MockLockedState(self.config.scope)
        self.addCleanup(self.state.db.close)
        self.state_patch = patch('research.replay_checkpoint.State', return_value=self.state)
        self.state_patch.start()
        self.addCleanup(self.state_patch.stop)
        self.report = dict(cleanup='verified', pending_intents=0,
                           execution_unresolved=False, protection_replacement_pending=False)

    def venue(self):
        venue = ResearchExchange(Market({}, ()), 1577836800000, D(1000),
            fx=self.fx, matcher='trade_print', prints=TradePrints(self.root/'prints'), uid=12000)
        venue.offline = True
        venue.read_latency_ms, venue.latency_ms, venue.mark_gap = 200, 1000, 'bound'
        return venue

    def snapshot(self, venue):
        return snapshot_venue(venue, binding=self.binding, config=self.config, session_report=self.report)

    def restore(self, venue, checkpoint, **kwargs):
        return restore_venue(venue, checkpoint, binding=kwargs.get('binding', self.binding),
                             config=kwargs.get('config', self.config))

    def test_lossless_money_clocks_cursors_aliases_and_unknown_path(self):
        venue = self.venue()
        venue.wallet, venue.fees, venue.funding_paid = D('999.001'), D('.999'), D('.000')
        venue.now_ms += 777
        venue._scanned, venue.held_from = venue.now_ms - 77, venue.now_ms - 700
        venue.request_weights = deque([(venue.monotonic()-.2, 40)])
        venue._commission = (venue.monotonic()-.1, D('.00075'))
        venue.known_path, venue.unknown_from = False, venue.now_ms - 1
        venue.bounded_minutes = [venue.now_ms - 60000]
        order = dict(orderId=42, clientOrderId='cq-filled', status='FILLED')
        venue.orders[order['clientOrderId']] = venue.by_order_id[42] = order
        venue._seq, venue._tran = 42, 9
        original = self.snapshot(venue)
        # Real State refreshes the lock lease when reopened; it is not copied.
        self.state.put('writer_host', {'at': 999, 'pid': 123})
        fresh = self.restore(self.venue(), original)
        self.assertEqual(self.snapshot(fresh), original)
        self.assertIs(fresh.orders['cq-filled'], fresh.by_order_id[42])
        self.assertEqual(fresh.now_ms, venue.now_ms)
        self.assertEqual(fresh._scanned, venue._scanned)
        self.assertFalse(fresh.known_path)
        self.assertEqual(fresh.request_weights, venue.request_weights)
        self.assertEqual(fresh._commission, venue._commission)

    def test_pending_protection_replacement_and_unverified_cleanup_refused(self):
        for field, value in (('cleanup', 'unresolved'), ('pending_intents', 1),
                             ('execution_unresolved', True), ('protection_replacement_pending', True)):
            with self.subTest(field=field):
                report = dict(self.report, **{field: value})
                with self.assertRaises(ValueError):
                    snapshot_venue(self.venue(), binding=self.binding, config=self.config, session_report=report)
        self.state.db.execute("INSERT INTO intents VALUES ('cq-unknown','unknown')")
        with self.assertRaisesRegex(ValueError, 'unresolved'):
            self.snapshot(self.venue())

    def test_held_position_requires_verified_native_protection(self):
        venue = self.venue()
        venue.q, venue.entry, venue.margin = D('.01'), D(10000), D(5)
        with self.assertRaisesRegex(ValueError, 'protected owned exposure'):
            self.snapshot(venue)
        self.report['actual'] = dict(quantity_btc='.01', native_full_position_protected=True,
                                     stop_before_liquidation=True)
        with self.assertRaisesRegex(ValueError, 'protected owned exposure'):
            self.snapshot(venue)
        for kind, trigger in (('STOP_MARKET', '9700'), ('TAKE_PROFIT_MARKET', '11000')):
            identity = 'cq-' + kind
            venue.algos[identity] = dict(clientAlgoId=identity, symbol='BTCUSDT',
                side='SELL', positionSide='BOTH', algoStatus='NEW', orderType=kind,
                closePosition=True, workingType='MARK_PRICE', priceProtect=False,
                triggerPrice=trigger)
        checkpoint = self.snapshot(venue)
        fresh = self.restore(self.venue(), checkpoint)
        self.assertEqual((fresh.q, fresh.entry, fresh.margin), (D('.01'), D(10000), D(5)))

    def test_changed_account_model_or_config_never_mutates_fresh_venue(self):
        checkpoint = self.snapshot(self.venue())
        fresh = self.venue()
        self.state.put('campaign', {'last': 2000, 'primary_consumed': 456})
        with self.assertRaisesRegex(ValueError, 'SQLite was changed'):
            self.restore(fresh, checkpoint)
        self.assertEqual(fresh.now_ms, 1577836800000)
        self.assertEqual(fresh.wallet, D(1000))
        self.state.put('campaign', {'last': 1000, 'primary_consumed': 123})
        with self.assertRaisesRegex(ValueError, 'dependencies'):
            self.restore(fresh, checkpoint, config=Config('12000', str(self.root/'different-state'), 300, 5))
        with self.assertRaisesRegex(ValueError, 'strategy'):
            self.restore(fresh, checkpoint, binding=dict(self.binding, strategy_sha256='4'*64))

    def test_digest_corruption_active_venue_new_state_and_wrong_uid_refused(self):
        venue = self.venue()
        checkpoint = self.snapshot(venue)
        with self.assertRaisesRegex(ValueError, 'digest'):
            self.restore(self.venue(), dict(checkpoint, sha256='0'*64))
        venue.request_weights.append((venue.monotonic(), 1))
        with self.assertRaisesRegex(ValueError, 'fresh venue'):
            self.restore(venue, checkpoint)
        unknown = self.venue()
        unknown.new_matching_cursor = 1
        with self.assertRaisesRegex(ValueError, 'explicit checkpoint version'):
            self.snapshot(unknown)
        with self.assertRaisesRegex(ValueError, 'account'):
            self.restore(self.venue(), checkpoint, config=Config('12001', self.config.state_dir, 300, 5))
        self.state.account_lock = None
        with self.assertRaisesRegex(ValueError, 'normal state and account locks'):
            self.snapshot(self.venue())

    def test_json_codec_never_loads_arbitrary_objects_or_nonfinite_money(self):
        values = {123: D('1.000000000000001'), ('time', 4): deque([(1.2, 40)]),
                  'dates': (date(2020, 1, 1), {'missing-day'})}
        self.assertEqual(decode(json.loads(json.dumps(encode(values)))), values)
        for invalid in (D('NaN'), float('inf'), object()):
            with self.assertRaises(ValueError):
                encode(invalid)
        with self.assertRaises(ValueError):
            decode({'type': 'arbitrary-object', 'value': 'payload'})
        self.assertEqual(digest(values), digest(decode(encode(values))))

    def test_small_profile_counts_sessions_and_preserves_failed_phase_time(self):
        profile = ReplayTimings(max_sessions=2)
        with profile.session():
            pass
        with self.assertRaises(RuntimeError):
            with profile.session():
                raise RuntimeError('retain failed sample time')
        with self.assertRaisesRegex(ValueError, 'budget'):
            profile.session()
        result = profile.result()
        self.assertEqual(result['sessions'], 2)
        self.assertEqual(result['sections']['session']['calls'], 2)
        self.assertTrue(result['nested_sections_may_overlap'])
        with self.assertRaises(ValueError):
            ReplayTimings(max_sessions=795)


if __name__ == '__main__':
    unittest.main()
