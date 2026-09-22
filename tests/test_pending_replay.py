"""Short, synthetic FOK replay checks—not a strategy qualification run."""
from dataclasses import replace
from pathlib import Path
import csv
import gzip
import tempfile
import unittest
from unittest.mock import patch

from coinquant.data import Dataset
from coinquant.replay import Account, activate_entry, hosted_exit_price, _replay
from coinquant.research import invocations
from coinquant.types import Bar, D, ModelConfig
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

    def test_intrabar_future_extreme_does_not_change_trigger_fill_price(self):
        rules = sample().rules
        first = Account(D('.1')); first.entry_pending = target()
        second = Account(D('.1')); second.entry_pending = target()
        mark = Bar(0, D(30745), D(40000), D(30740), D(31000))
        normal = Bar(0, D(30745), D(31020), D(30740), D(31000), D(1000))
        future_spike = Bar(0, D(30745), D(40000), D(30740), D(31000), D(1000))
        a = activate_entry(first, mark, normal, rules, D(100), D('.0002'), D('.0001'))
        b = activate_entry(second, mark, future_spike, rules, D(100), D('.0002'), D('.0001'))
        self.assertIsNotNone(a[1])
        self.assertEqual(a[1], b[1])
        self.assertEqual(a[1], target().trigger_price * D('1.0002'))

    def test_hosted_exit_uses_threshold_or_known_adverse_open_not_future_extreme(self):
        p = replace(sample().position, quantity=D(100), stop_loss=D(30000),
                    take_profit=D(32000), liquidation=D(29000))
        # Intrabar stop: fill from stop threshold, not a later low.
        self.assertEqual(
            hosted_exit_price(p, p.stop_loss, D(31000), D('.001'), adverse_gap=True),
            D(30000) * D('.999'))
        # Gap through stop: the already-worse open is known and must be honored.
        self.assertEqual(
            hosted_exit_price(p, p.stop_loss, D(29500), D('.001'), adverse_gap=True),
            D(29500) * D('.999'))
        # Take profit receives no optimistic favorable-gap improvement.
        self.assertEqual(
            hosted_exit_price(p, p.take_profit, D(33000), D('.001'), adverse_gap=False),
            D(32000) * D('.999'))

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
            with patch('coinquant.replay.decide', side_effect=decision) as model:
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
