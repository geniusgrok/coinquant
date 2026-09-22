from dataclasses import asdict
from decimal import Decimal as D
import json
from pathlib import Path
import unittest
from research.linear_replay import Account, FEE
from research.volatility_target import funded_target, target_fraction

class TargetTests(unittest.TestCase):
    def test_liquidity_cap_is_not_labeled_target(self):
        a=Account(D(1000))
        r=funded_target(a,1,D(1),D(100),D(100),D(80),D(200),D('.5'),None)
        self.assertEqual(r['reason'],'liquidity_cap')
        self.assertEqual(r['requested'],'10')
        self.assertEqual(a.q,D('.5'))

    def test_long_short_add_reduce_funds_and_protection(self):
        for side in (1,-1):
            a=Account(D(1000));sl,tp=(D(80),D(180)) if side==1 else (D(120),D(40))
            r=funded_target(a,side,D('.5'),D(100),D(100),sl,tp,D(100),None)
            self.assertEqual(r['event'],'entry')
            margin=a.margin;before=a.equity(D(105));fees=a.fees;old=abs(a.q);entry=a.entry
            r=funded_target(a,side,D('1.0'),D(105),D(105),sl,tp,D(100),None)
            self.assertEqual(r['event'],'rebalance_add')
            self.assertGreaterEqual(a.margin,margin)
            self.assertEqual(a.entry,(old*entry+r['amount']*105)/abs(a.q))
            self.assertLess(abs(a.equity(D(105))-(before-(a.fees-fees))),D('1e-20'))
            self.assertLessEqual(a.margin,a.wallet)
            self.assertTrue(a.liquidation()<a.sl if side==1 else a.liquidation()>a.sl)
            before=a.equity(D(105));fees=a.fees
            r=funded_target(a,side,D('.2'),D(105),D(105),sl,tp,D(100),None)
            self.assertEqual(r['event'],'rebalance_reduce')
            self.assertLess(abs(a.equity(D(105))-(before-(a.fees-fees))),D('1e-20'))

    def test_capped_add_and_no_upward_minimum_rounding(self):
        instrument=json.loads(Path('evidence/binance-boundary-20260921/current-instrument.json').read_text())['instrument']
        a=Account(D(10));before=asdict(a)
        r=funded_target(a,1,D(1),D(10000),D(10000),D(9000),D(20000),D(100),instrument)
        self.assertEqual(asdict(a),before)
        self.assertEqual(r['accepted'],'0')
        a=Account(D(1000))
        r=funded_target(a,1,D(20),D(100),D(100),D(80),D(200),D(1000),None)
        self.assertEqual(r['reason'],'funding_cap')
        self.assertLess(a.margin,a.wallet)
        self.assertLess(a.q,D(200))

    def test_no_mutation_when_protection_invalid(self):
        a=Account(D(1000));before=asdict(a)
        funded_target(a,1,D(1),D(100),D(100),D(101),D(200),D(100),None)
        self.assertEqual(asdict(a),before)

    def test_volatility_absence_and_warmup(self):
        self.assertEqual(target_fraction([D('.02')]*19,D('.0011')),0)
        low=target_fraction([D('.02')]*20,D('.0011'))
        self.assertGreater(low,target_fraction([D('.04')]*20,D('.0011')))
        self.assertGreater(low,target_fraction([D('.02')]*20,D('.0011'),21))
        self.assertEqual(low,target_fraction([D('99')]+[D('.02')]*20,D('.0011')))

    def test_quote_side_change_rejects_without_mutation(self):
        a=Account(D(1000));before=asdict(a)
        r=funded_target(a,1,D(1),D(100),D(100),D(80),D(200),D(100),None,intended_add=False)
        self.assertEqual(r['reason'],'quote_side_changed');self.assertEqual(asdict(a),before)

    def test_channel_position_has_no_state_latch_or_lookahead(self):
        from research.volatility_target import channel_position
        prior=[(D(110),D(90),D(100))]*20
        self.assertEqual(channel_position(prior+[(D(500),D(1),D(110))]),(1,D(1)))
        self.assertEqual(channel_position(prior+[(D(500),D(1),D(95))]),(-1,D('.5')))
        self.assertEqual(channel_position(prior+[(D(500),D(1),D(100))]),(0,D(0)))
        self.assertEqual(channel_position(prior),(0,D(0)))
