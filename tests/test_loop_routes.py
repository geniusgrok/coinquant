import json
import math
from decimal import Decimal as D
from pathlib import Path
import tempfile
import unittest

from research import nine_routes as r, loop_alpha as alpha, loop_risk as risk
from research import loop_admission as admission, loop_accounts as accounts, loop_data as data


class LoopRoutesTests(unittest.TestCase):
    def test_sleeve_fifo_uses_selling_owner_and_actual_btc_commission(self):
        def fill(identity,order,qty,quote,buyer,fee='0'):
            return dict(id=identity,order_id=order,time=identity,qty=str(qty),quote=str(quote),price='100',
                buyer=buyer,commission=fee,commission_asset='BTC')
        def allocation(order,sleeve):return [order,json.dumps(dict(weights={sleeve:'1'})),'settled',json.dumps(dict(orderId=order))]
        rows=alpha.spot_baskets(dict(allocations=[allocation(1,'30'),allocation(2,'50'),allocation(3,'50')],
            fills=[fill(1,1,1,100,True,'.001'),fill(2,2,1,200,True),fill(3,3,1,150,False)]))
        self.assertEqual(rows[0]['residue_btc'],D('.999'));self.assertFalse(rows[0]['closed'])
        self.assertTrue(rows[1]['closed']);self.assertEqual(rows[1]['gain'],D(-50))

    def test_coin_campaign_gain_includes_fee_funding_and_censors_open_campaign(self):
        fills=[dict(id=i,orderId=i,time=i,qty='1',price='100',side=side) for i,side in [(1,'BUY'),(3,'SELL'),(5,'BUY')]]
        income=[dict(time=t,income=value,incomeType=kind) for t,value,kind in
                [(1,'-.1','COMMISSION'),(2,'-.2','FUNDING_FEE'),(3,'10','REALIZED_PNL'),(5,'-.1','COMMISSION')]]
        rows=alpha.coin_baskets(dict(trades=fills,funding_ledger=income))
        self.assertEqual(rows[0]['gain'],D('9.7'));self.assertEqual(rows[1]['residue_btc'],D(1))
        self.assertEqual(len(alpha.nonoverlapping(rows)),1)

    def test_actual_mature_gate_can_admit_without_default_or_curve_claim(self):
        rows=[]
        for i in range(80):
            selected=i%2==0;market=D(str(math.sin(i)));momentum=D(str(math.cos(i*.7)));rms=D(str((i%7+1)/100))
            gain=D(10)-D(30)*selected+market+momentum+rms
            rows.append(dict(id=str(i),at_ms=2*i,settled_ms=2*i+1,closed=True,notional=D(100),gain=gain,
                selected=selected,factor=D('.75') if selected else D(1),market_return=market,prior_momentum=momentum,prior_rms=rms))
        result=alpha.information(rows,80,'spot')
        self.assertTrue(result['account_entrant']);self.assertFalse(result['default_adopted']);self.assertFalse(result['account_measured'])
        self.assertFalse(alpha.information(rows,100,'spot')['account_entrant'])
        with self.assertRaises(KeyError):alpha.information(rows,80,'coin')

    def test_realized_wallet_preserves_coin_income_and_mark_pnl(self):
        pair=dict(accounts=dict(spot=dict(initial_usdt='100',fills=[]),coin=dict(initial_usdt='100',
            trades=[dict(time=1,side='BUY',qty='1',price='100')],
            funding_ledger=[dict(time=1,asset='USDT',symbol='BTCUSDT',income='-1')])) )
        wallet=risk.Wallets(pair);wallet.advance(1)
        self.assertEqual(risk.Wallets.equity(wallet.amounts(),D(100),D(110)),D(209))

    def snapshots(self,now,equity='600',q='1'):
        return [dict(kind=kind,symbol='BTCUSDT',receipt_ms=now,owned=True,protected=True,pending=False,
            equity_usdt=equity,fx='10',quantity_btc=q,mark_usdt='100') for kind in ('spot','coin')]

    def test_brake_hysteresis_rejects_future_peak_and_never_tops_up(self):
        a=self.snapshots(100,equity='450');state=risk.brake_state(None,[],a,100)
        self.assertTrue(state['braking']);plan=risk.brake_plan(state,a[1],requested='.8')
        self.assertEqual(D(plan['target_btc']),D('.5'));self.assertEqual(D(plan['requested_btc']),D('.5'));self.assertEqual(plan['orders'],0)
        middle=risk.brake_state(state,[],self.snapshots(200,equity='470'),200);self.assertTrue(middle['braking'])
        recovered=risk.brake_state(middle,[],self.snapshots(300,equity='490'),300);self.assertFalse(recovered['braking'])
        with self.assertRaises(ValueError):risk.brake_state(None,[dict(at_ms=101,equity_cny='20000')],a,100)
        with self.assertRaises(ValueError):risk.brake_state(state,[],a,99)

    def test_implied_budget_never_increases_and_rejects_future_receipt(self):
        self.assertEqual(risk.implied_factor('.01','.02',100,100),1)
        self.assertLess(risk.implied_factor('1','.02',100,100),1)
        with self.assertRaises(ValueError):risk.implied_factor('1','.02',101,100)

    def test_native_stop_flag_without_price_quantity_does_not_cover_risk(self):
        a=self.snapshots(100);books={kind:dict(available_ms=100,executable_bid_btc='2',confirmed_jump_fraction='.01') for kind in ('spot','coin')}
        self.assertFalse(risk.protection_plan(a,books,100)['new_risk'])
        for row in a:row['confirmed_native_stops']=[dict(confirmed=True,side='SELL',symbol='BTCUSDT',receipt_ms=100,stop_price_usdt='90',quantity_btc='1')]
        self.assertTrue(risk.protection_plan(a,books,100)['new_risk'])
        a[0]['confirmed_native_stops'][0]['stop_price_usdt']='110'
        self.assertFalse(risk.protection_plan(a,books,100)['new_risk'])

    def test_candle_touch_and_missing_queue_never_prove_maker_execution(self):
        packet=dict(session_start_ms=0,deadline_ms=300000,account=self.snapshots(100)[1])
        self.assertEqual(admission.execution_plan(packet,100)['status'],'WAIT_EXECUTION_EVIDENCE')

    def test_no_entrant_does_not_create_account_job(self):
        screen=dict(spec_sha256=r.sha(data.SPEC.read_bytes()),routes={'a':dict(account_entrant=False,status='SUPPORT_PENDING')})
        result=accounts.plan(screen,[])
        self.assertEqual(result['new_accounts'],0);self.assertEqual(result['jobs'],[])

    def test_today_calendar_cannot_backfill_an_old_release(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);raw=b'BEGIN:VCALENDAR\nBEGIN:VEVENT\nDTSTART:20200101T133000Z\nSUMMARY:Consumer Price Index\nEND:VEVENT\nEND:VCALENDAR\n'
            (folder/'cpi.ics').write_bytes(raw)
            (folder/'receipts.json').write_text(json.dumps(dict(receipts=[dict(name='cpi.ics',status=200,raw_file='cpi.ics',sha256=r.sha(raw),receipt_ms=2000000000000)])))
            result=data.calendar(folder)
            self.assertEqual(result['events'],[]);self.assertFalse(result['old_event_availability_proven'])


if __name__=='__main__':unittest.main()
