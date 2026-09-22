import copy
import unittest
import numpy as np
from research.spot_flow import features, normalize, valid_flow, fit, sequential, HOUR, DAY

class SpotFlowTests(unittest.TestCase):
    def test_lag_missing_and_timestamp_units(self):
        rows={t:[str(t),'100','102','98','100','10',str(t+HOUR-1),'1000','5','5','500','0'] for t in range(250*HOUR)[::HOUR]}
        t=200*HOUR
        expected=features(t,rows,rows,{})
        changed=copy.deepcopy(rows)
        for s in changed:
            if s>=t-HOUR: changed[s][10]='1000'
        self.assertEqual(expected,features(t,changed,changed,{}))
        del changed[t-10*HOUR]
        self.assertIsNone(features(t,changed,rows,{}))
        r=rows[0].copy();r[0]='1735689600000000';r[6]='1735693199999999'
        self.assertTrue(valid_flow(normalize(r)))
        r=rows[0].copy();r[10]='1001';self.assertFalse(valid_flow(r))
        r[10]='NaN';self.assertFalse(valid_flow(r))
    def test_prediction_ignores_test_labels_and_continuation_constraint(self):
        rng=np.random.default_rng(19)
        train=[dict(x=rng.normal(size=8).tolist()) for _ in range(80)]
        for r in train:r['gross']=-r['x'][6]-.5*r['x'][7]
        test=copy.deepcopy(train[:5]);first=fit(train,test)
        for r in test:r['gross']=1e9
        second=fit(train,test)
        np.testing.assert_array_equal(first[1],second[1])
        self.assertTrue(all(v>=0 for v in first[2]['expanded_beta'][7:]))
        self.assertTrue(all(abs(v)<1e-10 for v in first[2]['expanded_beta'][7:]))
    def test_unmatured_training_labels_do_not_change_decision(self):
        from coinquant.research import timestamp
        boundary=timestamp('2022-01-01T00:00:00Z');rng=np.random.default_rng(8)
        samples=[dict(t=boundary-(50-i)*10*DAY,u=boundary-(50-i)*10*DAY+7*DAY,month='2021-01',primary=True,x=rng.normal(size=8).tolist(),gross=.01,long=.01,short=-.02,L_side=0) for i in range(40)]
        samples += [dict(samples[0],t=boundary-2*DAY,u=boundary+9*DAY,month='2021-12',gross=1e9)]
        samples += [dict(samples[0],t=boundary+DAY,u=boundary+9*DAY,month='2022-01')]
        first,_=sequential(samples);samples[-2]['gross']=-1e9;second,fits=sequential(samples)
        self.assertEqual(first[-1],second[-1])
        self.assertLess(fits[-1]['max_training_exit'],boundary-7*DAY)

    def test_positive_increment_is_not_accidentally_disabled(self):
        rng=np.random.default_rng(42)
        train=[dict(x=rng.normal(size=8).tolist()) for _ in range(100)]
        for r in train:r['gross']=.03*r['x'][6]+.02*r['x'][7]
        base,expanded,details=fit(train,train[:10])
        self.assertTrue(all(v>0 for v in details['expanded_beta'][7:]))
        self.assertGreater(float(np.max(abs(expanded-base))),.001)
