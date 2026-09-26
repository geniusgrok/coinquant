"""Risk regressions reproduced while checking PR #43 and adjacent call paths."""
from copy import deepcopy
from decimal import Decimal as D
import json
import tempfile
from unittest import TestCase
from unittest.mock import Mock

from coinquant.audit import income
from coinquant.config import Config
from coinquant.ownership import reconcile,fill_history
from coinquant.session import run
from coinquant.state import State
from coinquant.types import Unknown
from tests.session_venue import Venue
from tests import test_ownership as ownership_fixture


class ReviewRegressions(TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.directory=self.tmp.name
        self.venue=Venue();self.venue.seed(self.directory)
    def tearDown(self):self.tmp.cleanup()
    def session(self,seconds=1,**kw):
        return run(Config('123',self.directory,seconds,1),self.venue,execute=True,
                   monotonic=self.venue.monotonic,wait=self.venue.wait,**kw)

    def test_external_protection_cannot_make_cleanup_verified(self):
        self.session();before=len(self.venue.sent)
        for n,algo in enumerate(list(self.venue.algos.values())):
            replacement=deepcopy(algo);algo['algoStatus']='CANCELED'
            replacement.update(clientAlgoId='external-'+str(n),algoId=100+n)
            if replacement['orderType']=='STOP_MARKET':replacement['triggerPrice']='90000'
            self.venue.algos[replacement['clientAlgoId']]=replacement
        r=self.session()
        self.assertEqual(r['status'],'unknown');self.assertEqual(r['cleanup'],'unresolved')
        self.assertEqual(len(self.venue.sent),before)

    def test_changed_owned_protection_does_not_pass_aggregate_geometry(self):
        self.session();before=len(self.venue.sent)
        for algo in self.venue.algos.values():
            if algo['orderType']=='STOP_MARKET':algo['triggerPrice']='90000'
        self.assertTrue(self.venue.snapshot('123')['native_full_position_protected'])
        r=self.session();self.assertEqual(r['cleanup'],'unresolved')
        self.assertEqual(len(self.venue.sent),before)

    def test_full_recent_window_is_a_cursor_not_complete_history(self):
        self.venue.trades=[dict(symbol='BTCUSDT',id=i,time=self.venue.now) for i in range(1000)]
        snapshot=self.venue.snapshot('123')
        self.assertEqual(snapshot['last_fill_id'],999)
        self.assertFalse(snapshot['recent_fill_window_complete'])
        self.assertFalse(snapshot['recovery_history_complete'])

    def test_more_than_1000_same_millisecond_fills_reconcile_and_protect(self):
        original=self.venue.fill
        def fragmented(order,amount):
            original(order,amount)
            if amount:
                trade=self.venue.trades.pop();first=amount/2000
                self.venue.trades=[dict(trade,id=i+1,qty=str(first if i<1000 else amount/2)) for i in range(1001)]
        self.venue.fill=fragmented
        result=self.session();self.assertEqual(result['cleanup'],'verified')
        with State(self.directory,'binance:BTCUSDT:live:123') as state:
            self.assertEqual(state.db.execute('SELECT COUNT(*) FROM native_fills').fetchone()[0],1001)
        pages=[p for method,path,p in self.venue.calls if 'fromId' in p]
        self.assertTrue(any(p['fromId']==1001 for p in pages))
        self.assertTrue(all('startTime' not in p and 'endTime' not in p for p in pages))

    def test_restart_finishes_interrupted_owned_protection_replacement(self):
        from coinquant.campaign import Campaign
        self.session()
        with State(self.directory,'binance:BTCUSDT:live:123') as state:
            from dataclasses import replace
            model=Campaign.restore(state.get('linear_campaign'));model.model.active=replace(model.model.active,stop=D(96000))
            state.set('linear_campaign',model.checkpoint())
        original=self.venue.send
        def interrupted(method,path,p):
            result=original(method,path,p)
            if method=='DELETE':self.venue.fail_reads=True
            return result
        self.venue.send=interrupted
        self.assertEqual(self.session()['cleanup'],'unresolved')
        self.venue.send=original;self.venue.fail_reads=False
        self.assertEqual(self.session()['cleanup'],'verified')
        self.assertEqual(len([a for a in self.venue.algos.values() if a['algoStatus']=='NEW']),2)
        self.assertEqual(len(self.venue.algos),4)

    def test_unknown_observations_are_retained_without_stale_equity(self):
        self.session();self.venue.fail_reads=True
        result=self.session()
        self.assertNotIn('actual',result)
        with State(self.directory,'binance:BTCUSDT:live:123') as state:
            reports=[json.loads(r[0]) for r in state.db.execute('SELECT payload FROM observations ORDER BY sequence')]
        self.assertTrue(any(r.get('observation_current') for r in reports))
        self.assertFalse(reports[-1]['observation_current'])
        self.assertNotIn('actual',reports[-1])

    def test_cashflow_audit_outage_blocks_entry_but_not_verified_exit(self):
        from coinquant.campaign import Campaign
        self.session()
        with State(self.directory,'binance:BTCUSDT:live:123') as state:
            model=Campaign.restore(state.get('linear_campaign'));model.model.active=None
            state.set('linear_campaign',model.checkpoint());state.set('income_coverage',None)
        original=self.venue.get
        def unavailable(path,p=None):
            if path.endswith('/income'):raise Unknown('income unavailable')
            return original(path,p)
        self.venue.get=unavailable
        result=self.session()
        self.assertEqual(self.venue.q,0);self.assertEqual(result['cleanup'],'verified')
        self.assertEqual(result['status'],'unknown')
        self.venue.seed(self.directory)
        before=len(self.venue.sent)
        self.session()
        self.assertEqual(len(self.venue.sent),before)

    def test_disconnect_during_final_wait_clears_previous_observation(self):
        def disconnect(seconds):
            self.venue.wait(seconds);self.venue.fail_reads=True
        result=run(Config('123',self.directory,1,1),self.venue,execute=True,
                   monotonic=self.venue.monotonic,wait=disconnect)
        self.assertEqual(result['cleanup'],'unresolved')
        self.assertFalse(result['observation_current'])
        self.assertNotIn('actual',result);self.assertNotIn('model_preview',result)


class HistoryArchiveTests(TestCase):
    def test_verified_archive_recovers_old_entry_without_expired_native_order(self):
        with tempfile.TemporaryDirectory() as tmp,State(tmp,'binance:BTCUSDT:live:123') as state:
            model,reader,snapshot,trade=ownership_fixture.OwnershipTests().fixture(state)
            reader.query_intent.return_value['parent']['status']='CANCELED'
            state.finish('cq-entry','confirmed',{'executed_quantity':'.003'})
            reconcile(state,reader,model,snapshot)
            reader.clock.return_value+=60*86400;reader.get.return_value=[]
            reconcile(state,reader,model,snapshot)
            reader.clock.return_value+=40*86400
            reader.query_intent.reset_mock();reader.query_intent.side_effect=Unknown('expired order')
            result=reconcile(state,reader,model,snapshot)
            self.assertEqual(result['quantity'],'0.003');reader.query_intent.assert_not_called()

    def test_archive_does_not_hide_unobserved_retention_gap(self):
        with tempfile.TemporaryDirectory() as tmp,State(tmp,'binance:BTCUSDT:live:123') as state:
            model,reader,snapshot,trade=ownership_fixture.OwnershipTests().fixture(state)
            reader.query_intent.return_value['parent']['status']='CANCELED'
            reconcile(state,reader,model,snapshot)
            reader.clock.return_value+=100*86400;reader.get.reset_mock()
            with self.assertRaisesRegex(Unknown,'archive required'):reconcile(state,reader,model,snapshot)
            reader.get.assert_not_called()

    def test_changed_archived_fill_blocks_and_keeps_prior_coverage(self):
        with tempfile.TemporaryDirectory() as tmp,State(tmp,'binance:BTCUSDT:live:123') as state:
            model,reader,snapshot,trade=ownership_fixture.OwnershipTests().fixture(state)
            reconcile(state,reader,model,snapshot);before=state.get('ownership_coverage')
            trade['qty']='.004'
            with self.assertRaisesRegex(Unknown,'changed after'):reconcile(state,reader,model,snapshot)
            self.assertEqual(state.get('ownership_coverage'),before)

    def test_nonadvancing_id_page_is_not_accepted_as_complete(self):
        reader=Mock();page=[dict(id=i,time=100) for i in range(1000)]
        reader.get.return_value=page
        with self.assertRaisesRegex(Unknown,'did not advance'):fill_history(reader,100,100,-1)

    def test_truncated_id_history_cannot_hide_full_time_page(self):
        reader=Mock();page=[dict(id=i,time=100) for i in range(1000)]
        reader.get.side_effect=[page,[]]
        with self.assertRaisesRegex(Unknown,'pages disagree'):fill_history(reader,100,100,-1)


class IncomeAuditTests(TestCase):
    def test_native_signed_funding_fees_and_same_id_types_are_retained(self):
        with tempfile.TemporaryDirectory() as tmp,State(tmp,'test') as state:
            reader=Mock();reader.clock.return_value=100000
            base=dict(tranId=1,time=99999000,asset='USDT',symbol='BTCUSDT',tradeId='')
            reader.get.return_value=[dict(base,incomeType='FUNDING_FEE',income='2.5'),dict(base,incomeType='COMMISSION',income='-.2')]
            first=income(reader,state);self.assertEqual(first['observed_transactions'],2)
            reader.clock.return_value+=61
            self.assertEqual(income(reader,state)['observed_transactions'],2)
            rows=[json.loads(r[0]) for r in state.db.execute('SELECT payload FROM native_income')]
            self.assertEqual(sum(D(r['income']) for r in rows),D('2.3'))
            self.assertFalse(first['continuous_equity_verified'])

    def test_income_pagination_and_duplicate_page_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp,State(tmp,'test') as state:
            reader=Mock();reader.clock.return_value=100000
            rows=[dict(tranId=i,time=99999000,asset='USDT',incomeType='FUNDING_FEE',income='-.01') for i in range(1001)]
            reader.get.side_effect=lambda path,p:rows[(p['page']-1)*1000:p['page']*1000]
            self.assertEqual(income(reader,state)['observed_transactions'],1001)
            reader.clock.return_value+=61;reader.get.side_effect=None;reader.get.return_value=rows[:1000]
            before=state.get('income_coverage')
            with self.assertRaisesRegex(Unknown,'repeated'):income(reader,state)
            self.assertEqual(state.get('income_coverage'),before)

    def test_missing_income_coverage_is_not_filled_with_zero_cashflows(self):
        with tempfile.TemporaryDirectory() as tmp,State(tmp,'test') as state:
            reader=Mock();reader.clock.return_value=100000;reader.get.return_value=[]
            before=income(reader,state);reader.clock.return_value+=100*86400
            with self.assertRaisesRegex(Unknown,'retention gap'):income(reader,state)
            self.assertEqual(state.get('income_coverage'),before)
