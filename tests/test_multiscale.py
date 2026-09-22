import copy
import hashlib
import json
import unittest
from decimal import Decimal as D

from coinquant.multiscale import DAY, PUBLICATION_LAG, MultiscaleCampaign, direction_score, daily_snapshots, published_daily_key
from coinquant.types import Blocked
from research.bounded_execution import ExecutionStudy
from research.persistent_hold_replay import run

START = 1572566400000


def feed(model, closes, start=START):
    for i, close in enumerate(closes):
        c = D(close)
        model.update(start+(i+1)*DAY, c*D('1.01'), c*D('.99'), c, D('.0011'))
    return model


class MultiscaleTests(unittest.TestCase):
    def test_normalized_monotone_and_zero(self):
        score, parts = direction_score([D(100)*D('1.01')**i for i in range(85)])
        self.assertEqual((score, parts), (D(1), (D(1),)*3))
        self.assertEqual(direction_score([D(100)]*85), (D(0), (D(0),)*3))
        self.assertEqual(direction_score([D(100)*D('.99')**i for i in range(85)])[0], -1)

    def test_formula_uses_each_return_square_not_volatility_of_centered_returns(self):
        closes = [D(100)*(D('1.012') if i%3 else D('.986'))**i for i in range(85)]
        score, components = direction_score(closes)
        expected = []
        for h in (7,28,84):
            rs=[(closes[i]/closes[i-1]).ln() for i in range(85-h,85)]
            value=(closes[-1]/closes[-1-h]).ln()/sum(r*r for r in rs).sqrt()
            expected.append(max(D(-1), min(D(1), value)))
        self.assertEqual(components, tuple(expected));self.assertEqual(score, sum(expected)/3)

    def test_all_scales_required(self):
        model=feed(MultiscaleCampaign(), [100]*84)
        self.assertIsNone(model.snapshot.score);self.assertIsNone(model.active_since)
        self.assertEqual(model.snapshot.fraction, 0)

    def test_publication_boundary(self):
        model=feed(MultiscaleCampaign(), range(100,185))
        self.assertEqual(model.active_since, model.snapshot.bar_end+PUBLICATION_LAG)
        with self.assertRaises(Blocked):model.visible(model.snapshot.available_at-1)
        self.assertEqual(model.action(0, model.snapshot.available_at), 'enter')

    def test_bad_data_does_not_create_reversal_or_mutate_state(self):
        model=feed(MultiscaleCampaign(), range(100,185));before=model.checkpoint()
        for high,low,close in [(D('NaN'),100,100),(100,0,100),(100,99,D('Infinity'))]:
            with self.assertRaises(ValueError):model.update(model.snapshot.bar_end+DAY,high,low,close)
            self.assertEqual(before,model.checkpoint())
        with self.assertRaises(ValueError):model.update(model.snapshot.bar_end+2*DAY,200,190,195)
        self.assertEqual(before,model.checkpoint())

    def test_stop_consumes_and_restart_does_not_reenter(self):
        model=feed(MultiscaleCampaign(), range(100,185));identity=model.active_since
        # A rejected attempt makes no call to filled, so the opportunity remains.
        self.assertEqual(model.action(0,model.snapshot.available_at),'enter')
        model.filled(identity);model.closed()
        model=MultiscaleCampaign.restore(model.checkpoint())
        self.assertEqual(model.action(0,model.snapshot.available_at),'consumed')
        model.update(model.snapshot.bar_end+DAY,190,180,189,D('.0011'))
        self.assertEqual(model.active_since,identity)
        self.assertEqual(model.action(0,model.snapshot.available_at),'consumed')

    def test_offline_negative_then_positive_is_not_old_position(self):
        model=feed(MultiscaleCampaign(), range(100,185));old=model.active_since;model.filled(old)
        t=model.snapshot.bar_end
        for i,c in enumerate([10,11,12,13,14,15,16,17,18,19,20,25,30,40,55,70,100,150,230,350,550,900,1500,2500,4000,8000,15000,30000,60000]):
            model.update(t+(i+1)*DAY,D(c)*D('1.01'),D(c)*D('.99'),c)
        self.assertIsNotNone(model.active_since);self.assertNotEqual(old,model.active_since)
        self.assertEqual(model.action(D('.1'),model.snapshot.available_at),'exit')

    def test_state_cannot_supply_missing_account_ownership(self):
        model=feed(MultiscaleCampaign(),range(100,185))
        with self.assertRaises(Blocked):model.action(D('.1'),model.snapshot.available_at)

    def test_campaign_identity_older_than_rolling_window_survives(self):
        model=feed(MultiscaleCampaign(),range(100,300));model.filled(model.active_since)
        restored=MultiscaleCampaign.restore(model.checkpoint())
        self.assertEqual(restored.checkpoint(),model.checkpoint())
        self.assertEqual(restored.action(D('.1'),restored.snapshot.available_at),'hold')

    def test_checkpoint_rejects_old_model_and_mutation(self):
        model=feed(MultiscaleCampaign(),range(100,185));saved=model.checkpoint()
        broken=copy.deepcopy(saved);broken['body']['model']='impulse_hold'
        broken['sha256']=hashlib.sha256(json.dumps(broken['body'],sort_keys=True).encode()).hexdigest()
        with self.assertRaises(Blocked):MultiscaleCampaign.restore(broken)
        broken=copy.deepcopy(saved);broken['body']['consumed']=1
        with self.assertRaises(Blocked):MultiscaleCampaign.restore(broken)

    def test_future_append_does_not_change_saved_prefix(self):
        model=feed(MultiscaleCampaign(),range(100,190));prefix=model.checkpoint()
        future=MultiscaleCampaign.restore(prefix)
        future.update(future.snapshot.bar_end+DAY,300,1,2)
        self.assertEqual(model.checkpoint(),prefix)

    def test_daily_key_excludes_the_unpublished_midnight_close(self):
        t=START+DAY
        self.assertEqual(published_daily_key(t),START+PUBLICATION_LAG)
        self.assertEqual(published_daily_key(t+PUBLICATION_LAG-1),START+PUBLICATION_LAG)
        self.assertEqual(published_daily_key(t+PUBLICATION_LAG),t+PUBLICATION_LAG)

    def test_hourly_rebuild_future_perturbation_preserves_every_past_snapshot(self):
        hour=3_600_000; rows={}
        for i in range(92*24):
            t=START+i*hour;price=D(100)+D(i)/24
            rows[t]=[t,str(price),str(price+1),str(price-1),str(price),'1',t+hour-1,'100',1]
        start=START+31*DAY;end=START+92*DAY;boundary=START+88*DAY
        warm={t:r for t,r in rows.items() if t<start};trade={t:r for t,r in rows.items() if t>=start}
        original=daily_snapshots(warm,trade,start,end,D('.0011'))
        changed=copy.deepcopy(trade)
        for t,r in changed.items():
            if t>=boundary:
                r[1:5]=[str(D(x)/10) for x in r[1:5]]
        alternate=daily_snapshots(warm,changed,start,end,D('.0011'))
        self.assertEqual({t:s.record() for t,s in original.items() if t<=boundary+PUBLICATION_LAG},
                         {t:s.record() for t,s in alternate.items() if t<=boundary+PUBLICATION_LAG})
        self.assertNotEqual(original[end+PUBLICATION_LAG].score,alternate[end+PUBLICATION_LAG].score)

    def test_unsafe_replay_combinations_still_rejected_before_loading_inputs(self):
        from pathlib import Path
        for extra in ({}, {'risk_scale':D(6),'short_risk_scale':D(0)},
                      {'risk_scale':D(6),'short_risk_scale':D(0),'execution':ExecutionStudy(True,False,frozenset(),{},D(6),False,'instant')}):
            with self.assertRaises(ValueError):run(*(Path('unread') for _ in range(4)),reference='multiscale',**extra)


if __name__=='__main__':unittest.main()
