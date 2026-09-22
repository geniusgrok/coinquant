import unittest
from research.attention_screen import weeks, features, predict, DAY, timestamp


class AttentionCausality(unittest.TestCase):
    def setUp(self):
        self.start=timestamp('2019-11-04T00:00:00Z')
        self.daily={self.start+i*DAY:100+i for i in range(70)}

    def test_publication_and_future_prefix(self):
        rows=weeks(self.daily);t=rows[4]['assumed_available_at']
        self.assertNotIn(t-1,features(rows,[t-1])[0])
        got=features(rows,[t])[0][t]
        self.assertIsNone(got['available_at'])
        changed={k:(v*1000 if k>=rows[4]['period_end'] else v) for k,v in self.daily.items()}
        self.assertEqual(features(weeks(changed),[t])[0][t],got)

    def test_missing_week_not_zero_or_stale_fallback(self):
        rows=weeks(self.daily);t=rows[5]['assumed_available_at']
        missing=dict(self.daily);del missing[self.start+35*DAY]
        self.assertNotIn(t,features(weeks(missing),[t])[0])
        zero=dict(self.daily);zero[self.start+35*DAY]=0
        self.assertIn(t,features(weeks(zero),[t])[0])
        last=rows[-1]['assumed_available_at']
        self.assertNotIn(last+7*DAY,features(rows,[last+7*DAY])[0])

    def test_constant_rescaling_not_full_history_normalization(self):
        a=weeks(self.daily);b=weeks({k:3*v for k,v in self.daily.items()})
        for x,y in zip(a,b):
            if x['attention'] is not None:self.assertEqual(3*x['attention'],y['attention'])


if __name__=='__main__':unittest.main()
