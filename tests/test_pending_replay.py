"""Short, synthetic FOK replay checks—not a strategy qualification run."""
from dataclasses import replace
from pathlib import Path
import csv
import gzip
import tempfile
import unittest
from unittest.mock import patch

from pancakequant.data import Dataset
from pancakequant.replay import Account, activate_entry, _replay
from pancakequant.research import invocations
from pancakequant.types import Bar, D, ModelConfig
from test_pending import target
from test_model import sample
from test_replay import dataset_fixture


class PendingReplayTests(unittest.TestCase):
    def test_trigger_consumes_parent_and_never_partial_fills(self):
        account = Account(D('.1')); account.entry_pending = target()
        mark = Bar(0, D(30745), D(31010), D(30740), D(31000))
        trade = Bar(0, D(30745), D(31020), D(30740), D(31000), D(1000))
        event = activate_entry(account, mark, trade, sample().rules, D(99), D('.0002'), D('.0001'))
        self.assertIsNotNone(event)
        self.assertIsNone(event[1])
        self.assertIsNone(account.entry_pending)
        self.assertEqual(account.position.quantity, 0)
        # Recovery of liquidity in a later bar cannot revive a cancelled FOK.
        self.assertIsNone(activate_entry(account, mark, trade, sample().rules, D(1000), D('.0002'), D('.0001')))

    def test_fill_price_stays_within_limit_and_native_stop_has_no_parent_remainder(self):
        account = Account(D('.1')); account.entry_pending = target()
        mark = Bar(0, D(30745), D(31010), D(30740), D(31000))
        trade = Bar(0, D(30745), D(31020), D(30740), D(31000), D(1000))
        event = activate_entry(account, mark, trade, sample().rules, D(100), D('.0002'), D('.0001'))
        parent, price, _ = event
        self.assertLessEqual(price, parent.entry)
        account.fill(parent.quantity, price, sample().rules, parent.take_profit, parent.stop_loss)
        self.assertEqual(account.position.quantity, parent.quantity)
        self.assertIsNone(account.entry_pending)
        account.fill(-parent.quantity, D(30750), sample().rules)
        self.assertEqual(account.position.quantity, 0)
        self.assertIsNone(account.entry_pending)

    def test_pending_only_fires_between_fixed_invocations_no_extra_decision(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            manifest, frozen = dataset_fixture(path)
            dataset = Dataset(manifest, frozen, warmup_bars=3)
            start = dataset.start
            # At start the synthetic mark is 20144. This crossing is later,
            # while no manual invocation is allowed to evaluate a new signal.
            t = replace(target(start - 14_400_000), quantity=D(10), trigger_price=D(20160),
                        entry=D(20200), take_profit=D(20500), stop_loss=D(19900))
            flat = replace(t, quantity=D(0), trigger_price=D(0))
            output = path / 'output'; output.mkdir()
            def decision(bars, snapshot, cfg, **kwargs):
                return t if snapshot.time == start else flat
            with patch('pancakequant.replay.decide', side_effect=decision) as model:
                result = _replay(dataset, ModelConfig(), frozen, output)
            allowed = set(invocations(frozen))
            self.assertEqual({call.args[1].time for call in model.call_args_list}, allowed)
            self.assertEqual(result['decisions'], len(allowed))
            with gzip.open(output / 'orders.csv.gz', 'rt') as stream:
                rows = list(csv.DictReader(stream))
            native = [r for r in rows if r['event'] == 'native_entry']
            self.assertEqual(len(native), 1)
            self.assertNotIn(int(native[0]['time']), allowed)
            self.assertEqual(D(native[0]['delta_usd_contracts']), 10)
            self.assertTrue(all(int(r['time']) in allowed for r in rows if r['event'].startswith('manual_')))
            self.assertEqual(result['qualification'], 'NOT_QUALIFIED')
