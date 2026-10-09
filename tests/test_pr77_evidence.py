"""Native trial evidence must prove the events the live gate promises."""
from copy import deepcopy
from decimal import Decimal as D
import json
from pathlib import Path
import tempfile
from unittest import TestCase
from unittest.mock import Mock, patch

from coinquant.cli import source_digest, trial_gate
from coinquant.config import Config
from coinquant.demo_evidence import verify
from coinquant.state import State
from coinquant.types import Blocked, Unknown

SCOPE='binance:BTCUSDT:demo:456'
RISK=dict(max_stop_loss_fraction='.10',stop_slippage_fraction='.01')


def demo_fixture(directory):
    proof=dict(source_digest='digest',demo_uid='456',demo_state_dir=str(directory),
               demo_capital_limit_usdt='100',entry_order_id='entry',stop_algo_id='stop',
               take_algo_id='take',reduction_order_id='reduce',offline_trigger_order_id='offline',**RISK)
    orders={}
    with State(directory,SCOPE) as state:
        for identity,side,kind,qty,oid in (('entry','BUY','LIMIT','3',1),('reduce','SELL','MARKET','1',4)):
            payload=dict(symbol='BTCUSDT',positionSide='BOTH',side=side,type=kind,
                         quantity=qty,reduceOnly='true' if identity=='reduce' else 'false')
            state.prepare(identity,'binance_order',payload)
            state.finish(identity,'confirmed',{})
            orders[identity]=dict(parent=dict(payload,reduceOnly=identity=='reduce',orderId=oid,
                                             origQty=qty,executedQty=qty,status='FILLED'),child=None)
        for identity,kind,oid,qty in (('stop','STOP_MARKET',20,'1'),
                                     ('take','TAKE_PROFIT_MARKET',30,'1'),
                                     ('offline','STOP_MARKET',40,'2')):
            payload=dict(symbol='BTCUSDT',positionSide='BOTH',side='SELL',type=kind,
                         triggerPrice='110' if identity=='take' else '90',workingType='MARK_PRICE',
                         closePosition='true',priceProtect='false')
            state.prepare(identity,'binance_algo',payload)
            state.finish(identity,'confirmed',{'status':'NEW'})
            orders[identity]=dict(parent=dict(payload,orderType=kind,closePosition=True,
                                             priceProtect=False,algoStatus='FINISHED',clientAlgoId=identity),
                                 child=dict(symbol='BTCUSDT',positionSide='BOTH',side='SELL',
                                            orderId=oid,origQty=qty,executedQty=qty,status='FILLED'))
        actions=[dict(id=identity,method='POST',path=path,at_ms=stamp)
                 for identity,path,stamp in (('stop','/fapi/v1/algoOrder',900100),
                     ('take','/fapi/v1/algoOrder',950100),('entry','/fapi/v1/order',1000100),
                     ('reduce','/fapi/v1/order',1000101),('offline','/fapi/v1/algoOrder',1000102))]
        actions[3]['position_before_btc']='3'
        actual=dict(quantity_btc='2',native_full_position_protected=True,stop_before_liquidation=True,
                    open_algos=[dict(clientAlgoId='offline',algoStatus='NEW',closePosition=True)])
        base=dict(trial_mode='demo',source_digest='digest',risk_limits=RISK,cleanup='verified',
                  pending_intents=0,sizing_capital_usdt='100',status='executed',elapsed_seconds=103)
        state.report(dict(base,session_started_at_ms=900000,write_attempted=True,actions=actions,actual=actual))
        state.report(dict(base,session_started_at_ms=900000,actual=actual))
        state.report(dict(base,session_started_at_ms=1020000,elapsed_seconds=3,
                          actual=dict(quantity_btc='0',native_full_position_protected=False)))
    reader=Mock(environment='demo',authorize_writes=False,loss_fraction=D('.10'),slip_fraction=D('.01'))
    reader.account_identity.return_value='456';reader.clock.return_value=1030
    reader.query_intent.side_effect=lambda identity,conditional=False:deepcopy(orders[identity])
    reader.get.return_value=[dict(id=i+1,time=stamp,orderId=oid,qty=qty,price=price,
                                 symbol='BTCUSDT',positionSide='BOTH',side=side)
                             for i,(stamp,oid,qty,price,side) in enumerate((
                                 (910000,20,'1','89','SELL'),(960000,30,'1','111','SELL'),
                                 (1000150,1,'3','100','BUY'),(1001000,4,'1','100','SELL'),
                                 (1010000,40,'2','89','SELL')))]
    return proof,reader,orders


class DemoEvidenceTests(TestCase):
    def test_filled_partial_position_and_both_native_triggers_are_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            proof,reader,_=demo_fixture(Path(tmp))
            self.assertTrue(verify(proof,'digest',D(100),reader))

    def test_untriggered_take_profit_or_missing_native_fill_cannot_pass(self):
        for missing in ('trigger','fill'):
            with self.subTest(missing=missing),tempfile.TemporaryDirectory() as tmp:
                proof,reader,orders=demo_fixture(Path(tmp))
                if missing=='trigger':
                    orders['take']['parent']['algoStatus']='NEW';orders['take']['child']=None
                else:reader.get.return_value=[t for t in reader.get.return_value if t['orderId']!=30]
                with self.assertRaises(Blocked):verify(proof,'digest',D(100),reader)

    def test_full_position_exit_is_not_partial_reduction_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            proof,reader,_=demo_fixture(Path(tmp))
            with State(tmp,SCOPE) as state:
                seq,payload=state.db.execute('SELECT sequence,payload FROM observations ORDER BY sequence LIMIT 1').fetchone()
                report=json.loads(payload);report['actions'][3]['position_before_btc']='1'
                with state.db:state.db.execute('UPDATE observations SET payload=? WHERE sequence=?',(json.dumps(report),seq))
            with self.assertRaisesRegex(Blocked,'partial position'):verify(proof,'digest',D(100),reader)

    def test_same_source_with_different_risk_configuration_is_not_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            proof,reader,_=demo_fixture(Path(tmp))
            proof['max_stop_loss_fraction']='.02';reader.loss_fraction=D('.02')
            with self.assertRaisesRegex(Blocked,'current-source'):verify(proof,'digest',D(100),reader)

    def test_later_larger_cap_report_cannot_upgrade_earlier_small_cap_orders(self):
        with tempfile.TemporaryDirectory() as tmp:
            proof,reader,_=demo_fixture(Path(tmp))
            with State(tmp,SCOPE) as state:
                seq,payload=state.db.execute('SELECT sequence,payload FROM observations ORDER BY sequence LIMIT 1').fetchone()
                report=json.loads(payload);report['sizing_capital_usdt']='10'
                with state.db:state.db.execute('UPDATE observations SET payload=? WHERE sequence=?',(json.dumps(report),seq))
            with self.assertRaisesRegex(Blocked,'current-source'):verify(proof,'digest',D(100),reader)

    def test_read_only_session_during_trigger_is_not_offline(self):
        with tempfile.TemporaryDirectory() as tmp:
            proof,reader,_=demo_fixture(Path(tmp))
            with State(tmp,SCOPE) as state:state.report(dict(session_started_at_ms=1009000,status='read_only'))
            with self.assertRaisesRegex(Blocked,'between completed sessions'):verify(proof,'digest',D(100),reader)

    def test_first_partial_trigger_fill_must_also_be_outside_every_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            proof,reader,_=demo_fixture(Path(tmp))
            fills=reader.get.return_value;last=fills.pop()
            fills.extend((dict(last,qty='1'),dict(last,id=6,time=1015000,qty='1')))
            with State(tmp,SCOPE) as state:
                report=json.loads(state.db.execute('SELECT payload FROM observations ORDER BY sequence LIMIT 1').fetchone()[0])
                report.update(session_started_at_ms=1009000,elapsed_seconds=3,actions=[],write_attempted=False)
                report['actual']['observed_at_ms']=1009999
                state.report(report)
            with self.assertRaisesRegex(Blocked,'between completed sessions'):verify(proof,'digest',D(100),reader)

    def test_terminal_child_survives_parent_finishing_but_not_changed_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            proof,reader,orders=demo_fixture(Path(tmp))
            archived=deepcopy(orders['offline']);archived['parent']['algoStatus']='TRIGGERED'
            with State(tmp,SCOPE) as state:state.set('terminal_native_orders',{'offline':archived})
            orders['offline']['parent']['updateTime']=1010100
            self.assertTrue(verify(proof,'digest',D(100),reader))
            orders['offline']['child']['executedQty']='1'
            with self.assertRaises(Unknown):verify(proof,'digest',D(100),reader)

    def test_live_gate_rejects_configuration_mismatch_before_demo_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp);config=Config('123',str(directory/'live'),capital_limit_usdt='100')
            config_path=directory/'config.json';config_path.write_text(json.dumps(dict(environment='live')))
            proof,_,_=demo_fixture(directory/'demo');proof['source_digest']=source_digest()
            proof['stop_slippage_fraction']='.02'
            evidence=directory/'proof.json';evidence.write_text(json.dumps(proof))
            with patch('coinquant.cli.connect') as connect:
                with self.assertRaisesRegex(Blocked,'configurations differ'):
                    trial_gate(config_path,config,mode='live',uid='123',evidence=evidence)
                connect.assert_not_called()

    def test_disabling_new_risk_preserves_matching_source_demo_management_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp)
            config=Config('123',str(directory/'live'),capital_limit_usdt='100',
                          max_stop_loss_fraction=None,stop_slippage_fraction=None)
            config_path=directory/'config.json';config_path.write_text(json.dumps(dict(environment='live')))
            proof,_,_=demo_fixture(directory/'demo');proof['source_digest']=source_digest()
            evidence=directory/'proof.json';evidence.write_text(json.dumps(proof))
            with patch('coinquant.cli.connect') as connect,patch('coinquant.cli.verify_demo_evidence') as check:
                trial_gate(config_path,config,mode='live',uid='123',evidence=evidence)
                self.assertEqual(connect.call_args.args[0].loss_fraction,D('.10'))
                check.assert_called_once()
