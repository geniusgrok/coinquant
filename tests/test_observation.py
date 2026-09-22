"""Regression tests for stale observations and account-mode authority."""
from dataclasses import replace
import tempfile
import unittest

from coinquant.config import Config
from coinquant.execution import run_once
from coinquant.types import D, Position, Unknown
from test_execution import FakeVenue


class ObservationTests(unittest.TestCase):
    def config(self, directory):
        return Config(account_uid='12345', max_position_usd=D(100000), state_dir=directory)

    def test_post_write_read_failure_never_reports_previous_flat_account_as_safe(self):
        venue = FakeVenue()
        def snapshot():
            if venue.writes:
                raise Unknown('injected post-write read failure')
            return venue.s
        venue.snapshot = snapshot
        with tempfile.TemporaryDirectory() as path:
            result = run_once(venue, self.config(path), execute=True)
        self.assertNotEqual(venue.s.position.quantity, 0)
        self.assertEqual(result['status'], 'unknown')
        self.assertIsNone(result['actual'])
        self.assertFalse(result['account_observation_current'])
        self.assertFalse(result['offline_safe_at_observation'])
        self.assertFalse(result['protection_verified_at_observation'])
        self.assertEqual(sum(w[0] == 'place' for w in venue.writes), 1)

    def test_mismatched_margin_mode_does_not_authorize_emergency_flatten(self):
        venue = FakeVenue()
        venue.s = replace(venue.s, margin_mode='REGULAR_MARGIN',
                          position=Position(D(100), D(30745), D('.01'), D(29500)))
        with tempfile.TemporaryDirectory() as path:
            result = run_once(venue, self.config(path), execute=True)
        self.assertEqual(result['status'], 'blocked')
        self.assertEqual(venue.writes, [])
        self.assertIsNone(result['actual'])

    def test_flat_derivative_report_keeps_collateral_fiat_delta(self):
        venue = FakeVenue()
        with tempfile.TemporaryDirectory() as path:
            result = run_once(venue, self.config(path))
        self.assertEqual(D(result['effective_derivative_leverage']), 0)
        self.assertEqual(D(result['effective_fiat_delta_leverage']), 1)
        self.assertEqual(D(result['net_btc_delta']), venue.s.wallet_btc)
