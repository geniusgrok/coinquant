from dataclasses import replace
from unittest import TestCase

from coinquant.config import Config
from coinquant.snapshot import export
from coinquant.types import Unknown


class SnapshotExportTests(TestCase):
    def fixture(self):
        now = 1700000000000
        return {'account_uid': '1', 'wallet_observed_from_ms': now - 1000,
                'wallet_observed_until_ms': now, 'observed_at_ms': now,
                'quantity_btc': '-2', 'wallet_usdt': '1000', 'entry': '100',
                'mark_price': '95', 'mark_time': now, 'native_liquidation_price': '150',
                'available_usdt': '500', 'native_full_position_protected': True,
                'possible_entry_remainders': False}

    def test_short_export_includes_unrealized_pnl_once(self):
        row = export(self.fixture(), Config('1', '/tmp/unused'))
        self.assertEqual(row['equity_usdt'], '1010')
        self.assertEqual(row['available_usdt'], '500')
        self.assertEqual(row['btc_position'], '-2')
        self.assertEqual(row['btc_direction'],'short')
        self.assertEqual(row['btc_notional_usdt'],'190')
        self.assertEqual(row['unprotected_notional_usdt'],'0')
        self.assertFalse(row['write_attempted'])
        self.assertFalse(row['native_execution_verified'])

    def test_uid_stale_mark_and_slow_collection_are_unknown(self):
        actual = self.fixture()
        for fields in ({'account_uid': '2'}, {'mark_time': actual['mark_time'] - 5001},
                       {'wallet_observed_from_ms': actual['observed_at_ms'] - 5001}):
            with self.subTest(fields=fields), self.assertRaises(Unknown):
                export(dict(actual, **fields), Config('1', '/tmp/unused'))

    def test_flat_account_has_no_liquidation_buffer_or_extra_collateral(self):
        actual = dict(self.fixture(), quantity_btc='0', entry='0', native_liquidation_price='0')
        row = export(actual, replace(Config('1', '/tmp/unused'), environment='demo'))
        self.assertEqual(row['equity_usdt'], '1000')
        self.assertEqual(row['environment'], 'demo')
        self.assertIsNone(row['liquidation_buffer_fraction'])

    def test_stop_distance_and_unprotected_notional_are_reported_separately(self):
        actual=dict(self.fixture(),native_full_position_protected=False,
                    protective_algos=[dict(type='STOP_MARKET',trigger='110')])
        row=export(actual,Config('1','/tmp/unused'))
        self.assertEqual(row['stop_distance_loss_usdt'],'20')
        self.assertEqual(row['unprotected_notional_usdt'],'190')

    def test_reversed_collection_clock_is_unknown(self):
        actual = self.fixture()
        actual['wallet_observed_from_ms'] = actual['wallet_observed_until_ms'] + 1
        with self.assertRaises(Unknown):
            export(actual, Config('1', '/tmp/unused'))
