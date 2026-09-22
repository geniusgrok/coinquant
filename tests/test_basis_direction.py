import copy
import unittest
import numpy as np
from research.basis_direction import HOUR, DAY, features, direction_label, fit_predict, valid

class BasisDirectionTests(unittest.TestCase):
    def setUp(self):
        self.rows={t:[t,'100','102','98','100','10',t+HOUR-1,'1000'] for t in range(0,250*HOUR,HOUR)}
    def test_future_prices_and_quotes_cannot_change_feature(self):
        t=200*HOUR;before=features(t,self.rows,self.rows,{})
        future=copy.deepcopy(self.rows)
        for s in future:
            if s>=t-HOUR:future[s][1:6]=['200','204','196','200','50'];future[s][7]='10000'
        self.assertEqual(before,features(t,future,future,{}))
        missing=dict(self.rows);del missing[t-10*HOUR]
        self.assertIsNone(features(t,missing,self.rows,{}))
    def test_bad_close_and_quote_rejected(self):
        row=self.rows[0].copy();row[6]=HOUR
        self.assertFalse(valid(row));row[6]=HOUR-1;row[7]='2000'
        self.assertFalse(valid(row))
    def test_funding_boundary_direction_and_cost(self):
        t=HOUR;u=10*HOUR
        f={t:.01,t+HOUR:.01,u:.01,u+HOUR:.9}
        a=direction_label(t,u,1,self.rows,self.rows,f)
        b=direction_label(t,u,-1,self.rows,self.rows,f)
        self.assertLess(a[0],-.02);self.assertGreater(b[0],0)
        self.assertLessEqual(a[0],a[1]);self.assertLessEqual(b[0],b[1])
        self.assertEqual(a,direction_label(t,u,1,self.rows,self.rows,{t:.01,t+HOUR:.01,u:.01}))
        self.assertLess(a[0],direction_label(t,u,1,self.rows,self.rows,{t+HOUR:.01})[0])
    def test_prediction_does_not_read_test_labels(self):
        rng=np.random.default_rng(7)
        train=[{'x':rng.normal(size=6).tolist(),'gross':float(rng.normal())} for _ in range(80)]
        test=[{'x':rng.normal(size=6).tolist(),'gross':0} for _ in range(5)]
        first=fit_predict(train,test)
        for r in test:r['gross']=1e8
        second=fit_predict(train,test)
        for a,b in zip(first[:3],second[:3]):np.testing.assert_array_equal(a,b)

if __name__=='__main__':unittest.main()
