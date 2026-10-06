"""Demo environment isolation and the optional sizing capital limit."""
import io
import json
import tempfile
from decimal import Decimal as D
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch

from coinquant.binance import Binance
from coinquant.cli import main, observe, source_digest, trial_gate
from coinquant.config import Config
from coinquant.session import run
from coinquant.state import State
from coinquant.types import Blocked
from coinquant.types import Unknown
from coinquant.demo_evidence import verify


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
            with patch.dict('os.environ', demo, clear=True), patch('coinquant.cli.Binance') as venue,patch('coinquant.cli.Lifecycle.instrument'):
                venue.return_value.snapshot.return_value = {'equity_usdt': '100'}
                venue.return_value.recover_pending.return_value={'resolved':0,'pending':0}
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

    def test_demo_execute_without_trial_flags_stays_blocked_before_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = self._config(tmp, environment='demo')
            with patch('coinquant.cli.Binance') as venue, patch('sys.stdout', io.StringIO()), \
                    patch('sys.stderr', io.StringIO()):
                self.assertEqual(main(['run', '--execute', '--config', str(config)]), 2)
                venue.assert_not_called()

    def test_controlled_demo_writes_use_the_same_session_and_adapter(self):
        with tempfile.TemporaryDirectory() as tmp:
            config=self._config(tmp,environment='demo',capital_limit_usdt='100')
            keys={'COINQUANT_BINANCE_DEMO_KEY':'d','COINQUANT_BINANCE_DEMO_SECRET':'s',
                  'COINQUANT_BINANCE_KEY':'live','COINQUANT_BINANCE_SECRET':'live'}
            with patch.dict('os.environ',keys,clear=True),patch('coinquant.cli.Binance') as venue, \
                    patch('coinquant.session.run',return_value={'status':'no_action'}) as session, \
                    patch('sys.stdout',io.StringIO()),patch('sys.stderr',io.StringIO()):
                self.assertEqual(main(['run','--config',str(config),'--execute','--trial','demo',
                                       '--authorize-uid','123']),0)
                self.assertEqual(venue.call_args.kwargs['key'],'d')
                self.assertTrue(venue.call_args.kwargs['authorize_writes'])
                self.assertTrue(session.call_args.kwargs['execute'])
                session.assert_called_once()

    def test_live_trial_needs_reviewed_matching_demo_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            config=self._config(tmp,environment='live',capital_limit_usdt='100',
                                max_stop_loss_fraction='.02',stop_slippage_fraction='.01')
            live=Config('123',str(Path(tmp)/'state'),environment='live',capital_limit_usdt='100',
                        max_stop_loss_fraction='.02',stop_slippage_fraction='.01')
            with self.assertRaises(Blocked):trial_gate(config,live,mode='live',uid='123')
            evidence=Path(tmp)/'evidence.json'
            proof=dict(source_digest='wrong',demo_uid='456',demo_state_dir=str(Path(tmp)/'demo-state'),
                       demo_capital_limit_usdt='100',entry_order_id='1',stop_algo_id='2',
                       take_algo_id='3',reduction_order_id='4',offline_trigger_order_id='5')
            evidence.write_text(json.dumps(proof))
            with self.assertRaises(Blocked):trial_gate(config,live,mode='live',uid='123',evidence=evidence)
            proof['source_digest']=source_digest();evidence.write_text(json.dumps(proof))
            with patch('coinquant.cli.connect') as connect,patch('coinquant.cli.verify_demo_evidence') as verify:
                trial_gate(config,live,mode='live',uid='123',evidence=evidence)
                self.assertEqual(connect.call_args.args[0].environment,'demo')
                self.assertEqual(verify.call_args.args[0],proof)

    def test_supplied_demo_ids_alone_do_not_attest_native_orders(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp)/'demo-state'
            with State(directory,'binance:BTCUSDT:demo:456'):
                pass
            proof=dict(source_digest='digest',demo_uid='456',demo_state_dir=str(directory),
                       demo_capital_limit_usdt='100',entry_order_id='made-up-entry',
                       stop_algo_id='made-up-stop',take_algo_id='made-up-take',
                       reduction_order_id='made-up-reduction',
                       offline_trigger_order_id='made-up-trigger')
            reader=Mock(environment='demo',authorize_writes=False)
            reader.account_identity.return_value='456'
            reader.query_intent.side_effect=Unknown('native identity absent')
            with self.assertRaises(Unknown):
                verify(proof,'digest',D(100),reader)

    def test_demo_evidence_requires_native_fill_and_session_chronology(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp)/'demo-state';scope='binance:BTCUSDT:demo:456'
            proof=dict(source_digest='digest',demo_uid='456',demo_state_dir=str(directory),
                       demo_capital_limit_usdt='100',entry_order_id='entry',stop_algo_id='stop',
                       take_algo_id='take',reduction_order_id='reduce',offline_trigger_order_id='offline')
            orders={}
            with State(directory,scope) as state:
                def ordinary(identity,side,kind,requested,filled,status,reduce=False):
                    payload=dict(symbol='BTCUSDT',positionSide='BOTH',side=side,type=kind,
                                 quantity=str(requested),reduceOnly='true' if reduce else 'false')
                    state.prepare(identity,'binance_order',payload)
                    state.finish(identity,'confirmed',{})
                    parent=dict(payload,reduceOnly=reduce,orderId=len(orders)+1,
                                origQty=str(requested),executedQty=str(filled),status=status)
                    orders[identity]=dict(parent=parent,child=None)
                def conditional(identity,kind,finished=False):
                    payload=dict(symbol='BTCUSDT',positionSide='BOTH',side='SELL',type=kind,
                                 triggerPrice='90',workingType='MARK_PRICE',
                                 closePosition='true',priceProtect='false')
                    state.prepare(identity,'binance_algo',payload)
                    state.finish(identity,'confirmed',{'status':'NEW'})
                    parent=dict(payload,orderType=kind,closePosition=True,priceProtect=False,
                                algoStatus='FINISHED' if finished else 'NEW')
                    child=(dict(symbol='BTCUSDT',positionSide='BOTH',side='SELL',orderId=40,
                                origQty='2',executedQty='2',status='FILLED') if finished else None)
                    orders[identity]=dict(parent=parent,child=child)
                ordinary('entry','BUY','LIMIT',3,3,'FILLED')
                conditional('stop','STOP_MARKET');conditional('take','TAKE_PROFIT_MARKET')
                ordinary('reduce','SELL','MARKET',2,1,'EXPIRED',True)
                conditional('offline','STOP_MARKET',True)
                base=dict(trial_mode='demo',source_digest='digest',cleanup='verified',pending_intents=0,
                          sizing_capital_usdt='100',
                          elapsed_seconds=3)
                state.report(dict(base,session_started_at_ms=1000000,
                                  actual=dict(quantity_btc='2',native_full_position_protected=True)))
                state.report(dict(base,session_started_at_ms=1020000,
                                  actual=dict(quantity_btc='0',native_full_position_protected=False)))
            reader=Mock(environment='demo',authorize_writes=False)
            reader.account_identity.return_value='456';reader.clock.return_value=1030
            reader.query_intent.side_effect=lambda identity,conditional=False:orders[identity]
            reader.get.return_value=[dict(id=1,time=1010000,orderId=40,qty='2',price='89',
                                          symbol='BTCUSDT',positionSide='BOTH',side='SELL')]
            self.assertTrue(verify(proof,'digest',D(100),reader))
            orders['offline']['child']['status']='NEW'
            with self.assertRaises(Unknown):
                verify(proof,'digest',D(100),reader)

    def test_session_refuses_an_adapter_for_another_environment_or_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            for fields in (dict(environment='demo'), dict(capital_limit_usdt='100')):
                with self.assertRaisesRegex(Blocked, 'environment or risk limits'):
                    run(Config('123', tmp, **fields), Binance())

    def test_capital_limit_must_be_a_positive_decimal_string(self):
        for value in ('0', '-1', 'NaN', 'Infinity', 'abc', 100):
            with self.assertRaises(Blocked):
                Config('123', '/tmp/x', capital_limit_usdt=value)
        self.assertEqual(Config('123', '/tmp/x', capital_limit_usdt='250.5').capital_limit, D('250.5'))
