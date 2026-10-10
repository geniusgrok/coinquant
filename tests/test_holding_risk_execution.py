"""Owned, native-shape execution of continuous campaign risk limits."""
from decimal import Decimal as D
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from coinquant.config import Config
from coinquant.lifecycle import Lifecycle
from coinquant.session import run
from coinquant.state import State
from coinquant.types import Rejected, Unknown
from tests.session_venue import Venue

SCOPE='binance:BTCUSDT:live:123'


class HoldingRiskExecution(TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.directory=self.tmp.name
        self.venue=Venue();self.venue.seed(self.directory)

    def session(self, **limits):
        config=Config('123',self.directory,1,1,**limits)
        self.venue.capital_limit=config.capital_limit
        self.venue.loss_fraction=config.loss_fraction
        self.venue.slip_fraction=config.slip_fraction
        return run(config,self.venue,execute=True,monotonic=self.venue.monotonic,wait=self.venue.wait)

    def protection(self):
        with State(self.directory,SCOPE) as state:
            return state.get('position_protection')

    def test_observed_profit_and_later_funding_tighten_native_stop_without_relaxing_it(self):
        self.assertEqual(self.session()['cleanup'],'verified')
        original=self.protection();quantity=self.venue.q
        self.venue.mark=D(108000);self.venue.wait(1)
        first=self.session()
        locked=self.protection()
        self.assertEqual(locked['stop'],original['stop'])
        self.assertGreater(D(locked['loss_ceiling_usdt']),0)
        self.assertEqual(locked['buffer_distance'],original['buffer_distance'])
        self.assertEqual(self.venue.q,quantity)
        self.venue.wallet-=D('.5');self.venue.pay('FUNDING_FEE',D('-.5'));self.venue.wait(1)
        second=self.session();funded=self.protection()
        self.assertEqual(funded['stop'],original['stop'])
        self.assertEqual(funded['loss_ceiling_usdt'],locked['loss_ceiling_usdt'])
        self.assertEqual(self.venue.q,quantity)
        self.venue.mark=D(104000);self.venue.wait(1)
        self.session(max_stop_loss_fraction='.49')
        self.assertEqual(self.protection()['stop'],original['stop'])
        self.assertEqual(second['holding_risk']['status'],'observed')
        self.assertEqual(first['holding_risk']['status'],'observed')

    def test_lowered_cap_exits_owned_position_even_when_income_is_unavailable(self):
        self.assertEqual(self.session()['cleanup'],'verified')
        before=len(self.venue.sent);get=self.venue.get
        def unavailable(path,parameters=None):
            if path.endswith('/income'):raise Unknown('fixture income unavailable')
            return get(path,parameters)
        self.venue.get=unavailable;self.venue.wait(1)
        result=self.session(capital_limit_usdt='100')
        self.assertGreater(self.venue.q,0,result)
        self.assertEqual(result['cleanup'],'verified')
        self.assertFalse(any(p.get('reduceOnly')=='true' for _,_,p in self.venue.sent[before:]))
        self.assertFalse(any(p.get('timeInForce')=='IOC' for _,_,p in self.venue.sent[before:]))

    def test_missing_cost_audit_keeps_native_protection_and_reports_unverified_risk(self):
        self.venue.fraction=D('.5')
        self.assertEqual(self.session()['cleanup'],'verified')
        quantity=self.venue.q;before=len(self.venue.sent);get=self.venue.get
        def unavailable(path,parameters=None):
            if path.endswith('/income'):raise Unknown('fixture income unavailable')
            return get(path,parameters)
        self.venue.get=unavailable;self.venue.wait(1)
        result=self.session()
        self.assertEqual(self.venue.q,quantity)
        self.assertTrue(result['actual']['native_full_position_protected'])
        self.assertEqual(result['holding_risk']['status'],'unverified')
        self.assertTrue(result['holding_risk_review_required'])
        self.assertTrue(result['manual_takeover_required'])
        self.assertEqual(self.venue.sent[before:],[])

    def test_manage_only_still_tightens_the_frozen_budget(self):
        self.assertEqual(self.session()['cleanup'],'verified')
        original=self.protection();quantity=self.venue.q
        self.venue.mark=D(108000);self.venue.wait(1)
        result=self.session(max_stop_loss_fraction=None,stop_slippage_fraction=None)
        self.assertEqual(result['holding_risk']['status'],'observed')
        self.assertEqual(self.protection()['stop'],original['stop'])
        self.assertEqual(self.venue.q,quantity)
        self.assertEqual(len([p for _,_,p in self.venue.sent if p.get('timeInForce')=='IOC']),1)

    def test_read_only_cannot_relabel_previous_risk_check_as_current(self):
        self.assertEqual(self.session()['cleanup'],'verified')
        self.venue.mark=D(108000);self.venue.wait(1);before=len(self.venue.sent)
        result=run(Config('123',self.directory,1,1),self.venue,execute=False,
                   monotonic=self.venue.monotonic,wait=self.venue.wait)
        self.assertEqual(result['holding_risk']['status'],'last_observed')
        self.assertTrue(result['holding_risk_review_required'])
        self.assertLess(result['holding_risk']['observed_at_ms'],result['session_started_at_ms'])
        self.assertEqual(self.venue.sent[before:],[])

    def test_refused_required_risk_stop_exits_even_while_old_pair_survives(self):
        self.assertEqual(self.session()['cleanup'],'verified')
        self.venue.mark=D(108000);self.venue.wait(1);send=self.venue.send
        def reject_new_stop(method,path,payload):
            if method=='POST' and payload.get('type')=='STOP_MARKET':
                raise Rejected('fixture risk stop refused',native_code=-2021)
            return send(method,path,payload)
        self.venue.send=reject_new_stop
        result=self.session()
        self.assertGreater(self.venue.q,0,result)
        self.assertEqual(result['cleanup'],'verified')
        self.assertEqual(self.protection()['stop'],self.protection()['stop'])

    def test_pending_strategy_amendment_cannot_hide_known_margin_breach(self):
        self.assertEqual(self.session()['cleanup'],'verified')
        with State(self.directory,SCOPE) as state:
            protection=state.get('position_protection')
            state.set('session_replacement',dict(old_epoch=protection['epoch'],epoch=self.venue.now,
                stop=protection['stop'],take='1',campaign=protection['campaign'],started_at_ms=self.venue.now))
        result=self.session(capital_limit_usdt='100')
        self.assertGreater(self.venue.q,0,result)
        self.assertEqual(result['cleanup'],'verified')

    def test_cleanup_checks_risk_even_when_market_catchup_fails(self):
        self.assertEqual(self.session()['cleanup'],'verified')
        original=self.protection();self.venue.mark=D(108000);self.venue.wait(1)
        with patch('coinquant.session.advance',side_effect=Unknown('fixture candle outage')):
            result=self.session()
        self.assertEqual(result['cleanup'],'verified',result)
        self.assertEqual(self.protection()['stop'],original['stop'])
        self.assertEqual(result['holding_risk']['status'],'observed')
        self.assertTrue(result['strategy_review_required'])

    def test_interrupted_tightening_restarts_the_same_durable_target(self):
        self.assertEqual(self.session()['cleanup'],'verified')
        original=self.protection();self.venue.mark=D(108000);self.venue.wait(1)
        with State(self.directory,SCOPE) as state:
            engine=Lifecycle(self.venue,state,'123',authorized=True)
            snapshot=engine.recover_exposure(engine.settle())
            engine.enforce_holding_risk(snapshot)
            self.assertIsNone(state.get('session_replacement'))
            self.assertEqual(state.get('position_protection')['stop'],original['stop'])
            self.assertGreater(D(state.get('position_protection')['loss_ceiling_usdt']),0)
        self.venue.mark=D(104000);self.venue.wait(1)
        result=self.session()
        final=self.protection()
        self.assertEqual(result['cleanup'],'verified',result)
        self.assertEqual(final['stop'],original['stop'])
        self.assertGreater(self.venue.q,0)

    def test_interrupted_tightening_crossed_before_restart_exits_under_owned_identity(self):
        self.assertEqual(self.session()['cleanup'],'verified')
        original=self.protection();self.venue.mark=D(108000);self.venue.wait(1)
        with State(self.directory,SCOPE) as state:
            engine=Lifecycle(self.venue,state,'123',authorized=True)
            snapshot=engine.recover_exposure(engine.settle())
            engine.enforce_holding_risk(snapshot)
            self.assertEqual(state.get('position_protection')['stop'],original['stop'])
        self.venue.mark=D(original['stop'])-D(1)
        self.venue.wait(1);before=len(self.venue.sent)
        result=self.session()
        self.assertEqual(self.venue.q,0,result)
        self.assertEqual(result['cleanup'],'verified')
        self.assertTrue(any(p.get('reduceOnly')=='true' for _,_,p in self.venue.sent[before:]))
