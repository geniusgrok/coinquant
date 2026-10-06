from decimal import Decimal as D
from datetime import datetime, timezone
from unittest import TestCase
from unittest.mock import Mock
from coinquant.campaign import Campaign, ORIGIN
from coinquant.opportunities import Opportunity
from coinquant.native_preview import entry_preview, topup_preview
from coinquant.types import Unknown
from tests.test_binance_quantity import instrument as quantity_rules


class NativePreviewTests(TestCase):
    def fixture(self):
        model=Campaign();model.last=ORIGIN+30*86400000;model.model.last=model.last
        model.returns.extend([D('.02')]*20)
        model.model.active=Opportunity(model.last,1,D(90),D(200),model.last+14400000)
        now=model.last+1000
        snapshot=dict(account_uid='123',quantity_btc='0',wallet_usdt='1000',available_usdt='1000',
                      possible_entry_remainders=0,mark_price='100',mark_time=now)
        instrument=quantity_rules()
        instrument['filters'][2]['notional']='5'
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
        reader.capital_limit=None
        reader.loss_fraction=None;reader.slip_fraction=None
        return model,reader,snapshot,values,instrument

    def test_capital_limit_sizes_from_the_trial_capital_only(self):
        m,r,s,_,instrument=self.fixture()
        r.capital_limit=D(100)
        p=entry_preview(r,m,s)
        self.assertEqual(p['sizing_capital_usdt'],'100')
        quantity=D(p['quantity_btc'])
        self.assertGreater(quantity,0)
        self.assertLessEqual(D(p['allocated_margin_usdt']),100)
        # Entry fee, ongoing funding reserve and closing fee remain cash funded.
        self.assertLessEqual(D(p['allocated_margin_usdt'])+quantity*D(p['entry_estimate'])*D('.011'),100)
        m,r,s,_,_=self.fixture()
        self.assertGreater(D(entry_preview(r,m,s)['quantity_btc']),quantity)

    def test_preview_rounds_funded_quantity_without_consuming_campaign(self):
        m,r,s,values,instrument=self.fixture();before=m.checkpoint()
        p=entry_preview(r,m,s);quantity=D(p['quantity_btc'])
        self.assertGreater(quantity,0)
        self.assertEqual(quantity % D('.001'),0)
        self.assertLessEqual(quantity*D(p['entry_estimate']),D(p['notional_cap']))
        liquidation=(quantity*D(p['entry_estimate'])-D(p['allocated_margin_usdt']))/(quantity*(1-D(p['maintenance_bound'])-D(p['fee'])))
        self.assertLess(liquidation,D(p['stop']))
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
        plan=entry_preview(r,m,s)
        self.assertLess(plan['campaign'],0)
        self.assertLessEqual(D(plan['quantity_btc'])*(D(plan['entry_estimate'])-D(plan['stop'])),D(30))

    def test_top_up_keeps_whole_position_inside_the_stop_budget(self):
        m,r,s,values,_=self.fixture()
        now=m.last+1000
        values['/fapi/v1/depth']=dict(E=now,bids=[['109.9','1000']],asks=[['110','1000']])
        held=dict(s,quantity_btc='1',entry='100',isolated_wallet_usdt='10',mark_price='110')
        r.snapshot.return_value=dict(held)
        free=topup_preview(r,m,held,'5','90','200.1')
        self.assertGreater(D(free['quantity_btc']),1)
        plan=topup_preview(r,m,held,'5','90','200.1','30')
        add=D(plan['quantity_btc'])
        self.assertGreater(add,0)
        self.assertLessEqual(1*(100-90)+add*(D(plan['entry_estimate'])-90),30)
        spent=topup_preview(r,m,held,'5','90','200.1','10')
        self.assertEqual(spent['quantity_btc'],'0');self.assertEqual(spent['constraint'],'stop_budget')

    def test_explicit_loss_budget_includes_both_fees_and_adverse_stop_slippage(self):
        m,r,s,_,_=self.fixture()
        r.loss_fraction=D('.02');r.slip_fraction=D('.01')
        plan=entry_preview(r,m,s)
        quantity=D(plan['quantity_btc']);price=D(plan['entry_estimate']);stop=D(plan['stop'])
        per_btc=price-stop+price*D(plan['fee'])+stop*(D('.01')+D('1.01')*D(plan['fee']))
        self.assertLessEqual(quantity*per_btc,D(plan['stop_budget_usdt']))
        self.assertEqual(D(plan['stop_budget_usdt']),D('20'))
        held=dict(s,quantity_btc=str(quantity),entry=str(price),isolated_wallet_usdt=plan['allocated_margin_usdt'])
        r.snapshot.return_value=dict(held)
        add=topup_preview(r,m,held,'100',str(stop),plan['take'],plan['stop_budget_usdt'],
                          plan['sizing_capital_usdt'],plan['stop_slippage_fraction'])
        self.assertEqual(add['quantity_btc'],'0')

    def test_explicit_budget_also_caps_macro_campaign(self):
        m,r,s,_,_=self.fixture()
        m.model.active=None;m.daily_lows.extend([D(90)]*10)
        row=dict(missing_reason=None,latest_value='1',prior20_value='1.3',
                 latest_observation_date=datetime.fromtimestamp(m.last/1000,timezone.utc).date().isoformat(),
                 latest_value_available_ms=m.last-1,prior20_value_available_ms=m.last-1)
        m.select_macro(row,'100',m.last+1000)
        r.loss_fraction=D('.01');r.slip_fraction=D('.01')
        plan=entry_preview(r,m,s)
        self.assertLess(plan['campaign'],0)
        self.assertEqual(plan['stop_budget_usdt'],'10.00')
