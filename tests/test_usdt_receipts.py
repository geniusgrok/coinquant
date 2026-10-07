"""Targeted source-clock and revision checks; no exchange or account fixture."""
import json
import tempfile
from pathlib import Path
import unittest

from research.usdt_receipts import DAY, _points, append_response, asof, signal_at


def response(values, *, missing=(), extra=None):
    dates = [i * DAY for i in range(1, len(values) + 1) if i not in missing]
    body = dict(market_caps=[[t, values[t // DAY - 1]] for t in dates],
                prices=[[t, 1] for t in dates])
    if extra is not None:
        body['market_caps'].append(extra)
        body['prices'].append([extra[0], 1])
    return json.dumps(body).encode()


class Receipts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'receipts.jsonl'

    def test_manual_start_uses_only_received_complete_daily_versions(self):
        now = 4 * DAY + 11 * 60_000
        first = append_response(self.path, response([100, 99, 101, 98]), now)
        self.assertIsNone(signal_at(self.path, now - 1))
        self.assertTrue(signal_at(self.path, now)['crossed_negative'])
        self.assertEqual(signal_at(self.path, now)['event_ms'], 4 * DAY)
        self.assertIsNone(signal_at(self.path, now + DAY))  # no fabricated next-day receipt
        self.assertEqual(first['points'][0]['data_era'], 'late_historical_import')
        self.assertEqual(first['points'][-1]['revision_stage'], 'provisional')

    def test_revision_appends_and_preserves_prior_asof_value(self):
        t = 4 * DAY + 11 * 60_000
        first = append_response(self.path, response([100, 99, 101, 98]), t)
        second = append_response(self.path, response([100, 99, 101, 102]), t + 60_000)
        self.assertEqual(asof(self.path, t)[-1]['market_cap_usd'], '98')
        self.assertEqual(asof(self.path, t + 60_000)[-1]['market_cap_usd'], '102')
        self.assertEqual(second['points'][-1]['revises'], first['points'][-1]['version_hash'])
        self.assertFalse(signal_at(self.path, t + 60_000)['crossed_negative'])
        self.assertEqual(len(self.path.read_text().splitlines()), 2)
        with self.assertRaises(ValueError):
            append_response(self.path, response([100, 100, 99, 97]), t)

    def test_missing_future_grid_and_chain_fail_closed(self):
        t = 4 * DAY + 11 * 60_000
        append_response(self.path, response([100, 100, 99, 102], missing=(2,)), t)
        self.assertIsNone(signal_at(self.path, t))
        with self.assertRaises(ValueError):
            _points(response([100], extra=[5 * DAY, 110]), t)
        self.assertEqual(len(_points(response([100], extra=[DAY + 30_000, 110]), t)), 1)
        unpaired = json.loads(response([100]))
        unpaired['prices'] = []
        with self.assertRaises(ValueError):
            _points(json.dumps(unpaired).encode(), t)
        with self.assertRaises(ValueError):
            _points(response([100, -1]), t)
        damaged = self.path.read_text().replace('"market_cap_usd":"100"', '"market_cap_usd":"101"', 1)
        self.path.write_text(damaged)
        with self.assertRaises(ValueError):
            asof(self.path, t)


if __name__ == '__main__':
    unittest.main()
