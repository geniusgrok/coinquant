from decimal import Decimal as D
from datetime import datetime, timezone
import json
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock
from coinquant.campaign import Campaign, ORIGIN
from coinquant.opportunities import Opportunity
from coinquant.native_preview import entry_preview
from coinquant.linear_account import Account
from coinquant.linear_sizing import funded_target
from coinquant.types import Unknown


class NativePreviewTests(TestCase):
    def fixture(self):
        model=Campaign();model.last=ORIGIN+30*86400000;model.model.last=model.last
        model.returns.extend([D('.02')]*20)
        model.model.active=Opportunity(model.last,1,D(90),D(200),model.last+14400000)
        now=model.last+1000
        snapshot=dict(account_uid='123',quantity_btc='0',wallet_usdt='1000',available_usdt='1000',
                      possible_entry_remainders=0,mark_price='100',mark_time=now)
        instrument=json.loads(Path('evidence/binance-boundary-20260921/current-instrument.json').read_text())['instrument']
        instrument.update(status='TRADING',contractType='PERPETUAL',marginAsset='USDT')
        instrument['filters']=[f for f in instrument['filters'] if f['filterType']!='PRICE_FILTER']+[
            dict(filterType='PRICE_FILTER',tickSize='.1',minPrice='.1',maxPrice='1000000')]
        values={
            '/fapi/v1/exchangeInfo':{'symbols':[instrument]},
            '/fapi/v1/commissionRate':dict(symbol='BTCUSDT',takerCommissionRate='.0005'),
            '/fapi/v1/leverageBracket':dict(symbol='BTCUSDT',brackets=[dict(notionalFloor='0',notionalCap='100000',maintMarginRatio='.005',cum='0',initialLeverage=20)]),
            '/fapi/v1/depth':dict(E=now,bids=[['99.9','1000']],asks=[['100','1000']])}
        reader=Mock();reader.clock.return_value=now/1000;reader.get.side_effect=lambda path,params=None:values[path]
        reader.snapshot.return_value=snapshot.copy()
        return model,reader,snapshot,values,instrument

    def test_native_inputs_use_identical_funding_function_without_consumption(self):
        m,r,s,values,instrument=self.fixture();before=m.checkpoint()
        p=entry_preview(r,m,s);a=Account(D(1000))
        expected=funded_target(a,1,m.entry_fraction('.0011'),D('100.1'),D(100),D(90),D('200.1'),D(10),instrument,fee=D('.0005'),maintenance=D('.005'),notional_limit=D(100000))
        self.assertEqual(p['quantity_btc'],str(a.q));self.assertGreater(a.q,0)
        self.assertEqual(p['allocated_margin_usdt'],str(a.margin));self.assertEqual(p['constraint'],expected['reason'])
        self.assertEqual(m.checkpoint(),before)

    def test_unknown_collateral_book_or_account_blocks(self):
        for field in ('collateral','book','account'):
            m,r,s,values,_=self.fixture()
            if field=='collateral':r.snapshot.return_value['available_usdt']='900'
            elif field=='book':values['/fapi/v1/depth']['E']-=20000
            else:r.snapshot.return_value['quantity_btc']='1'
            with self.assertRaises(Unknown):entry_preview(r,m,s)

    def test_macro_parent_quantity_respects_three_percent_stop_budget(self):
        m,r,s,_,_=self.fixture()
        m.model.active=None;m.daily_lows.extend([D(90)]*10)
        now=m.last+1000
        row=dict(missing_reason=None,latest_value='1',prior20_value='1.3',
                 latest_observation_date=datetime.fromtimestamp(m.last/1000,timezone.utc).date().isoformat(),
                 latest_value_available_ms=m.last-1,prior20_value_available_ms=m.last-1)
        m.select_macro(row,'100',now)
        plan=entry_preview(r,m,s,side='long')
        self.assertLess(plan['campaign'],0)
        self.assertLessEqual(D(plan['quantity_btc'])*(D(plan['entry_estimate'])-D(plan['stop'])),D(30))

    def test_liquidation_uses_supplied_closing_fee(self):
        a=Account(D(1000),q=D(1),entry=D(100),margin=D(20))
        self.assertGreater(a.liquidation(D('.005'),D('.002')),a.liquidation(D('.005'),D('.0005')))
        self.assertEqual(a.liquidation(D('.005'),D('.002')),D(80)/(1-D('.007')))
