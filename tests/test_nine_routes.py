import json
import tempfile
import unittest
from pathlib import Path

from research import nine_routes as r, nine_data as data


class NineRouteTests(unittest.TestCase):
    def inputs(self):
        at=30*r.DAY+60000
        accounts=[dict(kind=kind,symbol='BTCUSDT',receipt_ms=at,owned=True,protected=True,pending=False,
            equity_usdt='100',gross_notional_usdt='100',stop_risk_usdt='1',reserved_notional_usdt='0',
            momentum20='.1',momentum_available_ms=at) for kind in ('spot','coin')]
        proposal=dict(kind='spot',symbol='BTCUSDT',side='BUY',at_ms=at,
            gross_notional_usdt='100',stop_risk_usdt='1',feasible=True)
        context=dict(completed_through_ms=30*r.DAY,available_ms=at,source_sha256='a'*64,returns20=['-.01']*20)
        return at,accounts,proposal,context

    def test_committed_unfilled_budget_is_not_free_capacity(self):
        at,accounts,proposal,context=self.inputs()
        self.assertEqual(r.admission(accounts,proposal,at,'gross-entry-cap')['status'],'ADMIT_RESEARCH_PROPOSAL')
        accounts[1]['reserved_notional_usdt']='600'
        self.assertEqual(r.admission(accounts,proposal,at,'gross-entry-cap')['status'],'BLOCK_NEW_RISK')
        accounts[1]['pending']=True
        self.assertEqual(r.admission(accounts,proposal,at,'gross-entry-cap')['status'],'BLOCK_UNKNOWN')

    def test_future_positive_direction_cannot_bypass_state_guard(self):
        at,accounts,proposal,context=self.inputs();accounts[1]['momentum_available_ms']=at+1
        self.assertEqual(r.admission(accounts,proposal,at,'state-exposure',context)['status'],'BLOCK_UNKNOWN')
        accounts[1]['momentum_available_ms']=at;context['available_ms']=at+1
        self.assertEqual(r.admission(accounts,proposal,at,'stress-entry-cap',context)['status'],'BLOCK_UNKNOWN')

    def test_competitor_must_be_independent_fresh_actual_preflight(self):
        at,accounts,proposal,context=self.inputs();proposal['gross_notional_usdt']='400'
        competitor=dict(proposal,kind='coin',stop_risk_usdt='40')
        verdict=r.admission(accounts,proposal,at,'risk-capacity',competitor=competitor)
        self.assertTrue(verdict['competition']);self.assertEqual(verdict['status'],'ADMIT_RESEARCH_PROPOSAL')
        competitor['at_ms']=at+1
        self.assertEqual(r.admission(accounts,proposal,at,'risk-capacity',competitor=competitor)['status'],'BLOCK_UNKNOWN')

    def test_received_revisions_never_become_old_available_data(self):
        raw=b'observation_date,SOFR\n2026-09-01,4.25\n2026-09-02,4.26\n'
        receipt=data.date_ms('2026-10-04')
        rows=data.points('sofr',raw,receipt)
        self.assertTrue(all(row['available_ms']==receipt and not row['historical_vintage_proven'] for row in rows))
        sources=[{'sofr':{'points':rows}}]
        self.assertEqual(data.known_rows(sources,'sofr',receipt-1),[])
        revised=dict(rows[0],rate_fraction='.99',available_ms=receipt+r.DAY)
        sources.append({'sofr':{'points':[revised]}})
        self.assertEqual(data.known_rows(sources,'sofr',receipt+2*r.DAY)[0]['rate_fraction'],rows[0]['rate_fraction'])

    def test_hash_tamper_and_active_supply_substitution_reject(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);raw=b'observation_date,SOFR\n2026-09-01,4.25\n';(folder/'source').write_bytes(raw)
            receipt=dict(status=200,raw_file='source',sha256=r.sha(raw),receipt_ms=data.date_ms('2026-10-04'))
            (folder/'source').write_bytes(raw+b'changed')
            with self.assertRaises(ValueError):data.read_source(folder,receipt,'sofr')
        with self.assertRaises(ValueError):data.points('old-coin-supply',json.dumps({'data':[{'asset':'btc','SplyAct1yr':'100'}]}).encode(),data.date_ms('2026-10-04'))

    def test_uncertain_data_cannot_generate_primary_or_expand_budget(self):
        proposal=dict(symbol='BTCUSDT',side='BUY');feature=dict(status='WAIT_NEW_INTERVAL',weak=None,release=None)
        self.assertIsNone(r.alpha_expression('oi-deleveraging',0,feature,proposal)['factor'])
        ready=dict(status='FEATURE_READY',weak=True,release=False)
        self.assertEqual(r.alpha_expression('etf-demand',0,ready,proposal)['factor'],'0.75')
        self.assertEqual(r.alpha_expression('etf-demand',1,ready,proposal)['factor'],'0')
        self.assertEqual(r.alpha_expression('oi-deleveraging',0,dict(ready,release=True),proposal,owned=True)['status'],'NO_ACTION')


if __name__=='__main__':unittest.main()
