"""Synthetic protocol fixtures only; no market observations or economic proof."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research.information_next import SECOND, compile_window


def iso(ns):
    return (datetime(1970, 1, 1, tzinfo=timezone.utc)
            + timedelta(microseconds=ns // 1000)).isoformat().replace('+00:00', 'Z')


class InformationNext(unittest.TestCase):
    def fixture(self, directory, *, missing=False, future=False):
        start, end, decision = 100 * SECOND, 102 * SECOND, 102_200_000_000
        coin = [(99 * SECOND, dict(type='subscriptions', channels=[
            dict(name='level2_50', product_ids=['USDT-USD'])])),
            (99_100_000_000, dict(type='snapshot', product_id='USDT-USD',
                bids=[['.999', '10']], asks=[['1.001', '10']]))]
        for stamp in (99_900_000_000, 100_400_000_000, 100_900_000_000,
                      101_400_000_000, 101_900_000_000, 102_100_000_000):
            coin.append((stamp + 10_000_000, dict(type='l2update', product_id='USDT-USD',
                time=iso(stamp), changes=[['buy', '.999', '10']])))
        for stamp, last in ((99_800_000_000, 10), (102_050_000_000, 12)):
            coin.append((stamp + 10_000_000, dict(type='heartbeat', product_id='BTC-USD',
                time=iso(stamp), last_trade_id=last)))
        for identity, stamp, maker, qty in ((11, 100_300_000_000, 'sell', '2'),
                                            (12, 101_100_000_000, 'buy', '1')):
            coin.append((stamp + 10_000_000, dict(type='match', product_id='BTC-USD',
                trade_id=identity, time=iso(decision + SECOND if future and identity == 11 else stamp),
                side=maker, size=qty, price='100')))
        kraken = []
        for identity, stamp, side, qty in ((20, 99_800_000_000, 'buy', '3'),
                (21, 100_400_000_000, 'buy', '2'), (22, 101_300_000_000, 'sell', '1'),
                (23, 102_020_000_000, 'buy', '1')):
            if not (missing and identity == 22):
                kraken.append((stamp + 10_000_000, dict(channel='trade', type='update', data=[
                    dict(symbol='BTC/USD', trade_id=identity, timestamp=iso(stamp),
                         side=side, qty=qty, price='100')])))
        docs, streams, semantics = {}, [], {}
        for venue, messages in (('coinbase', coin), ('kraken', kraken)):
            doc = directory / (venue + '-synthetic-doc')
            doc.write_text('Synthetic ' + venue + ' protocol fixture, not a captured document.')
            docs[venue] = hashlib.sha256(doc.read_bytes()).hexdigest()
            semantics[venue] = dict(path=str(doc), sha256=docs[venue])
            rows = []
            for received, msg in sorted(messages):
                raw = json.dumps(msg, separators=(',', ':'))
                rows.append(json.dumps(dict(receipt_ns=received, opcode=1, raw_text=raw,
                    raw_sha256=hashlib.sha256(raw.encode()).hexdigest())))
            path = directory / (venue + '-messages.ndjson')
            path.write_text('\n'.join(rows) + '\n')
            receipt = dict(venue=venue, TLS_verified=True, websocket_http_status=101,
                url='wss://ws-feed.exchange.coinbase.com' if venue == 'coinbase' else 'wss://ws.kraken.com/v2',
                connection_attempts=1, reconnects=0, private_request=False, failures=[],
                status='FIXED_WINDOW_STOP', raw_messages_file=path.name,
                raw_messages_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), raw_bytes=path.stat().st_size)
            recpath = directory / (venue + '-receipt.json')
            recpath.write_text(json.dumps(receipt))
            streams.append(dict(venue=venue, receipt_path=str(recpath),
                receipt_sha256=hashlib.sha256(recpath.read_bytes()).hexdigest()))
        return dict(start_ns=start, end_ns=end, decision_ns=decision, registered_ns=98 * SECOND,
                    semantics=semantics, streams=streams), docs

    def test_closed_raw_window_maps_maker_side_and_stays_research_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan, docs = self.fixture(Path(tmp))
            with patch('research.information_next.DOCS', docs):
                result = compile_window(plan)
        self.assertEqual(result['status'], 'CLOSED_RESEARCH_WINDOW')
        self.assertEqual(result['observation']['status'], 'DEMAND_CANDIDATE')
        for flow in result['packet']['cross-venue']['flows']:
            self.assertEqual((flow['buy_btc'], flow['sell_btc']), ('2', '1'))
        self.assertEqual(result['account_entrants'], 0)
        self.assertEqual(result['orders'], 0)
        self.assertFalse(result['predictive_alpha_proven'])

    def test_missing_fenced_trade_cannot_claim_completeness(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan, docs = self.fixture(Path(tmp), missing=True)
            with patch('research.information_next.DOCS', docs):
                result = compile_window(plan)
        self.assertIn('kraken incomplete fenced trade-ID coverage', result['blockers'])
        self.assertEqual(result['status'], 'WAIT_COMPLETE_WINDOW')
        self.assertNotIn('packet', result)

    def test_future_exchange_event_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan, docs = self.fixture(Path(tmp), future=True)
            with patch('research.information_next.DOCS', docs):
                with self.assertRaisesRegex(ValueError, 'future Coinbase exchange event'):
                    compile_window(plan)
