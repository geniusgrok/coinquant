import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from pancakequant.cli import observe
from pancakequant.types import Blocked


class BinanceCLI(unittest.TestCase):
    def test_execution_blocked_before_credentials_or_network(self):
        with patch('pancakequant.cli.BinanceReadOnly') as venue:
            with self.assertRaises(Blocked):observe('/nonexistent',execute=True)
            venue.assert_not_called()

    def test_observation_saves_bound_account_report_without_decision(self):
        with tempfile.TemporaryDirectory() as tmp:
            config=Path(tmp)/'config.json'
            config.write_text(json.dumps(dict(account_uid='123',state_dir=str(Path(tmp)/'state'))))
            with patch.dict('os.environ',{'PANCAKEQUANT_BINANCE_KEY':'fake','PANCAKEQUANT_BINANCE_SECRET':'fake'}),patch('pancakequant.cli.BinanceReadOnly') as venue:
                venue.return_value.snapshot.return_value={'equity_usdt':'100'}
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
