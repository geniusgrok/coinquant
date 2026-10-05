"""Protection amendments, late income and writer ownership."""
import sqlite3
import tempfile
import unittest
import socket
import time
from decimal import Decimal as D
from pathlib import Path

from coinquant.audit import allows_new_risk, income
from coinquant.campaign import Campaign
from coinquant.config import Config
from coinquant.session import run
from coinquant.state import State
from coinquant.types import Blocked, Unknown
from tests.session_venue import Venue


SCOPE = 'binance:BTCUSDT:live:123'


class IncomeBoundaryTests(unittest.TestCase):
    def test_failed_amendment_preserves_old_pair_but_does_not_block_owned_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            venue = Venue()
            venue.seed(directory)

            def session():
                return run(Config('123', directory, 2, 1), venue, execute=True,
                           monotonic=venue.monotonic, wait=venue.wait)

            self.assertEqual(session()['cleanup'], 'verified')
            self.assertGreater(venue.q, 0)
            for item in venue.rules['filters']:
                if item['filterType'] == 'PRICE_FILTER':
                    item['tickSize'] = '0.01'
            venue.mark = D('110000.08')
            owned_quantity = venue.q
            held = session()
            self.assertEqual(venue.q, owned_quantity)
            self.assertTrue(held['actual']['native_full_position_protected'])
            self.assertTrue(held['protection_replacement_pending'])
            with State(directory, SCOPE) as state:
                model = Campaign.restore(state.get('linear_campaign'))
                model.model.active = None
                state.set('linear_campaign', model.checkpoint())
                self.assertEqual(model.action(venue.q), 'exit')
            before = len(venue.sent)
            exited = session()
            self.assertEqual(venue.q, 0)
            self.assertTrue(any(payload.get('reduceOnly') == 'true'
                                for _, _, payload in venue.sent[before:]))
            self.assertEqual(exited['cleanup'], 'verified')
            self.assertFalse(exited['protection_replacement_pending'])

    def test_preanchor_late_income_is_not_new_income(self):
        venue = Venue()
        with tempfile.TemporaryDirectory() as directory, State(directory, SCOPE) as state:
            baseline = venue.now
            first = income(venue, state, wallet='1000')
            self.assertTrue(allows_new_risk(first, '1000', flat=True))
            venue.wait(61)
            venue.income.append(dict(incomeType='TRANSFER', tranId=99, time=baseline-1000,
                                     asset='USDT', income='1000', symbol='', tradeId=''))
            subsequent = income(venue, state, wallet='1000')
            self.assertEqual(subsequent['wallet_closure'], 'explained')
            self.assertTrue(allows_new_risk(subsequent, '1000', flat=True))
            venue.wait(61)
            venue.income.append(dict(incomeType='TRANSFER', tranId=100, time=venue.now-1000,
                                     asset='USDT', income='10', symbol='', tradeId=''))
            venue.wallet += D(10)
            self.assertEqual(income(venue, state, wallet='1010')['wallet_closure'], 'explained')
            self.assertEqual(income(venue, state, wallet='1010', force=True)['observed_transactions'], 2)

    def test_ambiguous_initial_wallet_boundary_blocks_risk(self):
        venue = Venue()
        with tempfile.TemporaryDirectory() as directory, State(directory, SCOPE) as state:
            baseline = venue.now
            income(venue, state, wallet='1000')
            venue.wait(61)
            venue.income.append(dict(incomeType='TRANSFER', tranId=99, time=baseline,
                                     asset='USDT', income='10', symbol='', tradeId=''))
            with self.assertRaisesRegex(Unknown, 'boundary'):
                income(venue, state, wallet='1010')
            self.assertEqual(state.get('wallet_anchor')['wallet'], '1000')


    def test_foreign_live_writer_refusal_does_not_change_state(self):
        with tempfile.TemporaryDirectory() as directory:
            with State(directory, SCOPE) as state:
                state.set('writer_host', {'host': socket.gethostname() + '-other',
                                          'pid': 42, 'at': float(time.time())})
                before = state.get('writer_host')
            with self.assertRaises(Blocked):
                State(directory, SCOPE).__enter__()
            with sqlite3.connect(Path(directory) / 'intents.sqlite') as db:
                import json
                self.assertEqual(json.loads(db.execute("SELECT value FROM meta WHERE key='writer_host'").fetchone()[0]), before)


if __name__ == '__main__':
    unittest.main()
