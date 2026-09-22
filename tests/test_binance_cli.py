import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from coinquant.cli import observe
from coinquant.types import Blocked
from coinquant.state import State


class BinanceCLI(unittest.TestCase):
    def test_execution_blocked_before_credentials_or_network(self):
        with patch('coinquant.cli.BinanceReadOnly') as venue:
            with self.assertRaises(Blocked):observe('/nonexistent',execute=True)
            venue.assert_not_called()

    def test_observation_saves_bound_account_report_without_decision(self):
        with tempfile.TemporaryDirectory() as tmp:
            config=Path(tmp)/'config.json'
            config.write_text(json.dumps(dict(account_uid='123',state_dir=str(Path(tmp)/'state'))))
            with patch.dict('os.environ',{'COINQUANT_BINANCE_KEY':'fake','COINQUANT_BINANCE_SECRET':'fake'}),patch('coinquant.cli.BinanceReadOnly') as venue:
                venue.return_value.snapshot.return_value={'equity_usdt':'100'}
                venue.return_value.completed_market.return_value={'candles':[]}
                result=observe(config)
                self.assertEqual(result['status'],'read_only')
                self.assertFalse(result['write_attempted'])
                self.assertEqual(json.loads((Path(tmp)/'state/latest.json').read_text()),result)
                self.assertEqual(observe(config,decision=True)['status'],'blocked')
                venue.return_value.snapshot.assert_called_with('123')

    def test_legacy_configuration_never_selects_old_exchange(self):
        with tempfile.TemporaryDirectory() as tmp:
            config=Path(tmp)/'config.json';config.write_text('{"environment":"live","api_host":"api.bybit.com"}')
            with self.assertRaises(Blocked):observe(config)

    def test_pending_recovery_refreshes_account_and_keeps_unknown_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            config=Path(tmp)/'config.json';directory=Path(tmp)/'state'
            config.write_text(json.dumps(dict(account_uid='123',state_dir=str(directory))))
            with State(directory,'binance:BTCUSDT:live:123') as state:
                state.prepare('cq-unknown','binance_order',{})
            with patch.dict('os.environ',{'COINQUANT_BINANCE_KEY':'fake','COINQUANT_BINANCE_SECRET':'fake'}),patch('coinquant.cli.BinanceReadOnly') as venue:
                calls=[]
                venue.return_value.snapshot.side_effect=lambda uid:(calls.append('snapshot') or {'equity_usdt':'100'})
                venue.return_value.recover_pending.side_effect=lambda state:(calls.append('recover') or {'resolved':0,'pending':1})
                result=observe(config)
                self.assertEqual(calls,['snapshot','recover','snapshot'])
                self.assertEqual(result['status'],'unknown')
                self.assertFalse(result['write_attempted'])
                self.assertEqual(result['pending_intents'],1)
    def test_incomplete_replacement_is_visible_without_pending_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp)/'state';config=Path(tmp)/'config.json'
            config.write_text(json.dumps(dict(account_uid='123',state_dir=str(directory))))
            with State(directory,'binance:BTCUSDT:live:123') as state:
                state.set('binance_protection_replacement',dict(done=False,request={'old_ids':['cq-old']}))
            with patch.dict('os.environ',{'COINQUANT_BINANCE_KEY':'fake','COINQUANT_BINANCE_SECRET':'fake'}),patch('coinquant.cli.BinanceReadOnly') as venue:
                venue.return_value.snapshot.return_value={'equity_usdt':'100'}
                result=observe(config)
                self.assertEqual(result['status'],'unknown');self.assertEqual(result['pending_intents'],0)
                self.assertFalse(result['protection_replacement']['done']);self.assertFalse(result['write_attempted'])


    def test_missing_named_credentials_blocks_before_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / 'config.json'
            config.write_text(json.dumps(dict(account_uid='123', state_dir=str(Path(tmp)/'state'))))
            with patch.dict('os.environ', {}, clear=True), patch('coinquant.cli.BinanceReadOnly') as venue:
                with self.assertRaisesRegex(Blocked, 'read credentials required'):
                    observe(config)
                venue.assert_not_called()
