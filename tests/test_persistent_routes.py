import json
from decimal import Decimal as D
from pathlib import Path
import tempfile
import unittest

from research import persistent_routes as r, persistent_data as data


class PersistentMoneyTests(unittest.TestCase):
    def test_fee_owned_sale_fraction(self):
        def allocation(oid,buyer):
            payload=dict(weights={'30':'1'},signal_ms=0,repair={'30':False})
            return [str(oid),json.dumps(payload),'settled',json.dumps({'orderId':oid})]
        ledger=dict(allocations=[allocation(1,True),allocation(2,False)],
                    opportunity_ledger=[dict(event='fill',id=1)],fills=[
            dict(id=1,order_id=1,time=1,qty='1',quote='100',commission='.001',commission_asset='BTC',buyer=True,price='100'),
            dict(id=2,order_id=2,time=2,qty='.5',quote='60',commission='.06',commission_asset='USDT',buyer=False,price='120')])
        lot=r.owned_spot(ledger)[0]
        self.assertEqual(lot['quantity'],D('.999'))
        self.assertEqual(lot['left'],D('.499'))
        self.assertEqual(lot['settlements'][0]['proceeds'],D('59.94'))

    def test_joint_unknown_and_stale_cannot_add_risk(self):
        accounts=[dict(kind=k,symbol='BTCUSDT',receipt_ms=100,owned=True,protected=True,pending=False,
                       equity_usdt='100',gross_notional_usdt='100',stop_risk_usdt='5') for k in ('spot','coin')]
        proposal=dict(symbol='BTCUSDT',side='BUY',gross_notional_usdt='50',stop_risk_usdt='2')
        self.assertEqual(r.joint_admission(accounts,proposal,100,[])['status'],'ADMIT_RESEARCH_PROPOSAL')
        accounts[0]['owned']=False
        self.assertEqual(r.joint_admission(accounts,proposal,100,[])['status'],'BLOCK_UNKNOWN')
        accounts[0]['owned']=True
        self.assertEqual(r.joint_admission(accounts,proposal,60101,[])['status'],'BLOCK_UNKNOWN')

    def test_joint_tail_gate_can_block_gross_admission(self):
        accounts=[dict(kind=k,symbol='BTCUSDT',receipt_ms=1,owned=True,protected=True,pending=False,
                       equity_usdt='100',gross_notional_usdt='100',stop_risk_usdt='5') for k in ('spot','coin')]
        proposal=dict(symbol='BTCUSDT',side='BUY',gross_notional_usdt='200',stop_risk_usdt='2')
        self.assertEqual(r.joint_admission(accounts,proposal,1,[])['status'],'ADMIT_RESEARCH_PROPOSAL')
        result=r.joint_admission(accounts,proposal,1,['-.1']+['0']*19,'stress-entry-cap')
        self.assertEqual(result['status'],'BLOCK_NEW_RISK')
        self.assertEqual(result['orders'],0)

    def test_future_bar_cannot_change_completed_signal(self):
        bars={i*r.f.DAY:(D(i+100),D(i+101),D(i+99),D(i+100),D(100),D(50)) for i in range(25)}
        past=r.signal(bars,24*r.f.DAY,'state-trend','spot')
        bars[25*r.f.DAY]=(D(1),D(10000),D(1),D(10000),D(100000),D(1))
        self.assertEqual(past,r.signal(bars,24*r.f.DAY,'state-trend','spot'))


class PersistentReceiptTests(unittest.TestCase):
    def test_future_receipt_and_duplicate_day_do_not_become_samples(self):
        at=10*data.DAY
        packet=dict(oi=None,option_features=dict(available_ms=at+1,rr_near30='-.02',term_ratio='.9'))
        self.assertEqual(data.features([packet],at)['status'],'WAIT_NEW_INTERVAL')
        packet['option_features']['available_ms']=at
        result=data.features([packet,packet],at)
        self.assertEqual(result['independent_receipt_days'],1)
        self.assertIsNone(result['option_skew'])
        self.assertEqual(result['account_days'],0)

    def test_tampered_receipt_is_rejected_before_parsing(self):
        with tempfile.TemporaryDirectory() as name:
            path=Path(name)/'raw.json';path.write_text('{}')
            receipt=dict(status=200,raw_file='raw.json',sha256='0'*64,name='btc-oi',request_ms=0,receipt_ms=1)
            with self.assertRaisesRegex(ValueError,'bytes changed'):data.parse_receipt(receipt,Path(name))

    def test_dvol_and_missing_delta_do_not_qualify_as_skew(self):
        with tempfile.TemporaryDirectory() as name:
            raw=json.dumps(dict(result=dict(mark_iv=50,timestamp=1,instrument_name='BTC-30OCT26-100000-C'))).encode()
            (Path(name)/'raw.json').write_bytes(raw)
            receipt=dict(status=200,raw_file='raw.json',sha256=data.digest(raw),name='option-30-C',request_ms=0,receipt_ms=1)
            with self.assertRaises(KeyError):data.parse_receipt(receipt,Path(name))
