"""Demo environment isolation and the optional sizing capital limit."""
import io
import json
import tempfile
from decimal import Decimal as D
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from coinquant.binance import Binance
from coinquant.cli import main, observe
from coinquant.config import Config
from coinquant.session import run
from coinquant.state import State
from coinquant.types import Blocked


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class EnvironmentTests(TestCase):
    def _config(self, tmp, **fields):
        path = Path(tmp) / 'config.json'
        path.write_text(json.dumps(dict(account_uid='123', state_dir=str(Path(tmp) / 'state'), **fields)))
        return path

    def test_demo_reads_only_demo_hosts(self):
        urls = []

        class Capture:
            def open(self, request, timeout):
                urls.append(request.full_url)
                body = {'serverTime': 1} if '/fapi/v1/time' in request.full_url else {'uid': 7}
                return Response(json.dumps(body).encode())

        venue = Binance(key='k', secret='s', opener=Capture(), environment='demo')
        venue.get('/fapi/v1/time')
        venue.account_identity()
        self.assertTrue(urls[0].startswith('https://demo-fapi.binance.com/fapi/v1/time'))
        self.assertTrue(urls[1].startswith('https://demo-api.binance.com/api/v3/account'))
        with self.assertRaises(Blocked):
            Binance(environment='testnet')

    def test_demo_uses_its_own_credentials_and_state_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = self._config(tmp, environment='demo')
            live = {'COINQUANT_BINANCE_KEY': 'live', 'COINQUANT_BINANCE_SECRET': 'live'}
            with patch.dict('os.environ', live, clear=True), patch('coinquant.cli.Binance') as venue:
                with self.assertRaisesRegex(Blocked, 'COINQUANT_BINANCE_DEMO_KEY'):
                    observe(config)
                venue.assert_not_called()
            demo = {'COINQUANT_BINANCE_DEMO_KEY': 'demo', 'COINQUANT_BINANCE_DEMO_SECRET': 'demo'}
            with patch.dict('os.environ', demo, clear=True), patch('coinquant.cli.Binance') as venue:
                venue.return_value.snapshot.return_value = {'equity_usdt': '100'}
                result = observe(config)
                self.assertEqual(result['environment'], 'demo')
                self.assertEqual(venue.call_args.kwargs['environment'], 'demo')
                self.assertEqual(venue.call_args.kwargs['key'], 'demo')
            with State(Path(tmp) / 'state', 'binance:BTCUSDT:demo:123') as state:
                self.assertEqual(state.identity, 'binance:BTCUSDT:demo:123')

    def test_live_state_directory_refuses_a_demo_configuration(self):
        with tempfile.TemporaryDirectory() as tmp:
            with State(Path(tmp) / 'state', 'binance:BTCUSDT:live:123'):
                pass
            config = self._config(tmp, environment='demo')
            demo = {'COINQUANT_BINANCE_DEMO_KEY': 'demo', 'COINQUANT_BINANCE_DEMO_SECRET': 'demo'}
            with patch.dict('os.environ', demo, clear=True), patch('coinquant.cli.Binance'):
                with self.assertRaises(Blocked):
                    observe(config)

    def test_demo_execute_stays_blocked_before_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = self._config(tmp, environment='demo')
            with patch('coinquant.cli.Binance') as venue, patch('sys.stdout', io.StringIO()), \
                    patch('sys.stderr', io.StringIO()):
                self.assertEqual(main(['run', '--execute', '--config', str(config)]), 2)
                venue.assert_not_called()

    def test_session_refuses_an_adapter_for_another_environment_or_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            for fields in (dict(environment='demo'), dict(capital_limit_usdt='100')):
                with self.assertRaisesRegex(Blocked, 'environment or capital limit'):
                    run(Config('123', tmp, **fields), Binance())

    def test_capital_limit_must_be_a_positive_decimal_string(self):
        for value in ('0', '-1', 'NaN', 'Infinity', 'abc', 100):
            with self.assertRaises(Blocked):
                Config('123', '/tmp/x', capital_limit_usdt=value)
        self.assertEqual(Config('123', '/tmp/x', capital_limit_usdt='250.5').capital_limit, D('250.5'))
