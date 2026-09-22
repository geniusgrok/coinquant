"""Focused budget-routing and selection-identity checks; no historical optimization."""
import contextlib
from decimal import Decimal as D
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research.bounded_execution import BoundedEntry, ExecutionStudy, risk_scale, MINUTE
from research.bounded_execution_replay import digest, source_identity, verify_selection
from research.persistent_hold_replay import run
from coinquant.linear_account import Account
import test_bounded_execution as fixtures
T = fixtures.T


class BudgetRoutingTests(unittest.TestCase):
    def test_finite_registered_values_only(self):
        for value in ('3.6', '4.8', '6.0', D('6')):
            self.assertEqual(risk_scale(value), D(value))
        for value in ('NaN','Infinity','-1','0','5.4','6.01','bad',True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                risk_scale(value)
        with self.assertRaises(ValueError): ExecutionStudy(True, False, frozenset(), {}, D(7))

    def test_budget_reaches_independent_parent_and_cannot_expand_after_freeze(self):
        filled=[]; maximum=[]
        for budget in (D('3.6'),D('4.8'),D('6.0')):
            a=Account(D(10000))
            p=BoundedEntry.freeze(a,T,T-14400000,D('.5')*budget,D(10000),D(10000),
                                 D(9500),D(20000),D(60000000),None,D('.001'),D('.0002'),budget=budget)
            maximum.append(p.maximum)
            self.assertEqual(BoundedEntry.restore(p.record()).identity,p.identity)
            a.wallet*=2
            for t in range(p.start,p.deadline,MINUTE):
                p.attempt(t,a,D(10000),D(10000),{t-2*MINUTE:D(1000000)},None)
                self.assertLessEqual(a.q,p.maximum)
                self.assertLessEqual(p.loss_at_stop(a),p.risk_budget)
            filled.append(a.q)
        self.assertTrue(maximum[0]<maximum[1]<maximum[2])
        self.assertTrue(filled[0]<filled[1]<filled[2])

    def test_full_call_path_records_budget_and_rejects_mismatch(self):
        frozen,model,cached,minutes=fixtures.TimelineTests().fixture()
        cfg=ExecutionStudy(True,False,frozenset([T]),{t:D(10000) for t in range(T-MINUTE,T+3600000,MINUTE)},D('4.8'))
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)/'measured'
            with patch('research.persistent_hold_replay.spec',return_value=frozen),patch('research.persistent_hold_replay.decision_times',return_value=[T]),patch('coinquant.campaign.Campaign',model),contextlib.redirect_stdout(io.StringIO()):
                r=run(Path('.'),Path('.'),Path('.'),out,allocation='volatility',reference='impulse_hold',lifecycle='one_campaign',entry_side='long',risk_scale=D('4.8'),cached_inputs=cached,cached_minutes=(minutes,[]),execution=cfg)
            parent=json.loads((out/'execution_summary.json').read_text())['parents'][0]
            self.assertEqual(parent['risk_scale'],'4.8');self.assertEqual(r['risk_scale'],'4.8')
            self.assertEqual(r['execution']['risk_scale'],'4.8')
            with self.assertRaisesRegex(ValueError,'does not match'):
                run(Path('.'),Path('.'),Path('.'),out,risk_scale=D('6.0'),execution=cfg,allocation='volatility',reference='impulse_hold',lifecycle='one_campaign',entry_side='long')

    def test_selection_fails_changed_source_evidence_budget_and_performance(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            base=dict(cagr=1,final_cny='100',schedule_sha256='same')
            main=dict(cagr=1.2,final_cny='120',schedule_sha256='same',risk_scale='4.8',validation_used=False,mdd_conservative_envelope='.4',counts={},execution=dict(mode='five_minute',cost_multiplier=1))
            stress={**main,'execution':dict(mode='five_minute',cost_multiplier=2)}
            values={'base':base,'main':main,'stress':stress}
            for name,value in values.items():(root/name).write_text(json.dumps(value))
            selected=dict(source_identity=source_identity(),selected_risk_scale='4.8',baseline_main='base',baseline_stress='base',selected_main='main',selected_stress='stress',files={n:digest(root/n) for n in values})
            path=root/'SELECTION.json';path.write_text(json.dumps(selected))
            verify_selection(path,D('4.8'))
            with self.assertRaises(ValueError):verify_selection(path,D('6.0'))
            (root/'main').write_text('{}')
            with self.assertRaisesRegex(ValueError,'evidence changed'):verify_selection(path,D('4.8'))
            (root/'main').write_text(json.dumps(main))
            selected['source_identity']={};path.write_text(json.dumps(selected))
            with self.assertRaisesRegex(ValueError,'another economic source'):verify_selection(path,D('4.8'))


class BufferAuditTests(unittest.TestCase):
    def test_funding_draw_does_not_retain_original_gap_certificate(self):
        from research.execution_risk_audit import buffer_audit
        from unittest.mock import patch
        a,p,v = fixtures.BoundedTests().parent()
        child=p.attempt(p.start,a,D(10000),D(10000),v,None)
        def snapshot(time):
            return dict(time=str(time),event='close',quantity=str(a.q),wallet=str(a.wallet),
                        margin=str(a.margin),equity_usdt=str(a.equity(D(10000))),
                        average_entry=str(a.entry),sl=str(a.sl),funding=str(a.funding))
        first=snapshot(p.start)
        # Preserve positive isolated equity at the stop, but exhaust free cash
        # and consume one USDT of the original gap collateral through funding.
        cost=a.wallet-a.margin+D(1)
        a.wallet-=cost;a.funding+=cost;a.margin=a.wallet
        second=snapshot(p.start+60000)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'execution_summary.json').write_text(json.dumps({'parents':[p.record()]}))
            (root/'execution.jsonl').write_text(json.dumps(dict(kind='child',**child))+'\n')
            with patch('research.execution_risk_audit.rows',return_value=[first,second]):
                result=buffer_audit(root)
        self.assertFalse(result['original_gap_maintained'])
        self.assertEqual(result['affected_parents'],1)
        self.assertEqual(D(result['total_funding_taken_from_margin']),D(1))
