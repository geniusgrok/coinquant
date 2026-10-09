from decimal import Decimal as D
from datetime import datetime, timezone
from unittest import TestCase
from unittest.mock import Mock
from coinquant.campaign import Campaign, ORIGIN
from coinquant.config import Config
from coinquant.opportunities import Opportunity
from coinquant.native_preview import entry_preview, topup_preview
from coinquant.types import Blocked, Unknown
from tests.test_binance_quantity import instrument as quantity_rules


class NativePreviewTests(TestCase):
    def fixture(self):
        model=Campaign();model.last=ORIGIN+30*86400000;model.model.last=model.last
        model.returns.extend([D('.02')]*20)
        model.model.active=Opportunity(model.last,1,D(90),D(200),model.last+14400000)
        now=model.last+1000
        snapshot=dict(account_uid='123',quantity_btc='0',entry='0',wallet_usdt='1000',equity_usdt='1000',available_usdt='1000',
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
        config=Config('123','/tmp/coinquant-preview-test')
        reader.loss_fraction=config.loss_fraction;reader.slip_fraction=config.slip_fraction
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
        for field in ('collateral','book','account','equity','missing_equity','fill_cursor'):
            m,r,s,values,_=self.fixture()
            if field=='collateral':r.snapshot.return_value['available_usdt']='900'
            elif field=='book':values['/fapi/v1/depth']['E']-=20000
            else:r.snapshot.return_value['quantity_btc']='1'
            if field=='equity':r.snapshot.return_value=dict(s,equity_usdt='999')
            elif field=='missing_equity':r.snapshot.return_value=dict(s);r.snapshot.return_value.pop('equity_usdt')
            elif field=='fill_cursor':s['last_fill_id']=1;r.snapshot.return_value=dict(s,last_fill_id=2)
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
        held=dict(s,quantity_btc='1',entry='100',isolated_wallet_usdt='10',mark_price='110',equity_usdt='1010')
        r.snapshot.return_value=dict(held)
        with self.assertRaises(Blocked):topup_preview(r,m,held,'5','90','200.1')
        costs=dict(paid_commission_usdt='.05',realized_pnl_usdt='0')
        plan=topup_preview(r,m,held,'5','90','200.1','30',stop_slippage_fraction='.01',**costs)
        add=D(plan['quantity_btc'])
        self.assertGreater(add,0)
        self.assertLessEqual(1*(100-90)+add*(D(plan['entry_estimate'])-90),30)
        spent=topup_preview(r,m,held,'5','90','200.1','10',stop_slippage_fraction='.01',**costs)
        self.assertEqual(spent['quantity_btc'],'0');self.assertEqual(spent['constraint'],'stop_budget')

    def test_explicit_loss_budget_includes_both_fees_and_adverse_stop_slippage(self):
        m,r,s,_,_=self.fixture()
        r.loss_fraction=D('.02');r.slip_fraction=D('.01')
        plan=entry_preview(r,m,s)
        quantity=D(plan['quantity_btc']);price=D(plan['entry_estimate']);stop=D(plan['stop'])
        per_btc=price-stop+price*D(plan['fee'])+stop*(D('.01')+D('1.01')*D(plan['fee']))
        self.assertLessEqual(quantity*per_btc,D(plan['stop_budget_usdt']))
        self.assertEqual(D(plan['stop_budget_usdt']),D('20'))
        held=dict(s,quantity_btc=str(quantity),entry=str(price),isolated_wallet_usdt=plan['allocated_margin_usdt'],
                  equity_usdt=str(D(s['wallet_usdt'])+quantity*(D(s['mark_price'])-price)))
        r.snapshot.return_value=dict(held)
        add=topup_preview(r,m,held,'100',str(stop),plan['take'],plan['stop_budget_usdt'],
                          plan['sizing_capital_usdt'],plan['stop_slippage_fraction'],
                          paid_commission_usdt=quantity*price*D('.0005'),realized_pnl_usdt='0')
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

    def test_real_default_signal_has_a_cost_included_loss_ceiling(self):
        _,r,s,values,_=self.fixture()
        m=Campaign()
        for i in range(30*6):
            m.update(ORIGIN+(i+1)*14400000,D(38500),D(37500),D(38000))
        m.update(m.last+14400000,D(50500),D(38000),D(50000))
        now=m.last+1000
        s.update(mark_price='50000',mark_time=now)
        r.clock.return_value=now/1000;r.snapshot.return_value=dict(s)
        values['/fapi/v1/depth']=dict(E=now,bids=[['49999.9','1000']],asks=[['50000','1000']])
        plan=entry_preview(r,m,s)
        q,price,stop,fee=(D(plan[k]) for k in ('quantity_btc','entry_estimate','stop','fee'))
        loss=q*(price-stop+price*fee+stop*(D('.01')+D('1.01')*fee))
        self.assertEqual(stop,D(44000))
        self.assertGreater(q,0)
        self.assertLessEqual(loss,D(490))
        self.assertEqual(plan['stop_budget_capital_usdt'],'1000')
        self.assertEqual(plan['account_equity_usdt'],'1000')
        r.loss_fraction=r.slip_fraction=None
        with self.assertRaises(Blocked):entry_preview(r,m,s)

    def test_topup_uses_the_smaller_frozen_or_current_equity_budget(self):
        m,r,s,values,_=self.fixture()
        now=m.last+1000
        values['/fapi/v1/depth']=dict(E=now,bids=[['109.9','1000']],asks=[['110','1000']])
        held=dict(s,quantity_btc='1',entry='100',isolated_wallet_usdt='10',mark_price='110',equity_usdt='1010')
        r.snapshot.return_value=dict(held)
        costs=dict(paid_commission_usdt='.05',realized_pnl_usdt='0')
        frozen=topup_preview(r,m,held,'100','90','200.1','30','1000','.01',**costs)
        self.assertEqual(D(frozen['stop_budget_usdt']),30)
        # Unrealized profit does not increase trial cash capital or the frozen budget.
        self.assertEqual(D(frozen['stop_budget_capital_usdt']),1000)
        r.loss_fraction=D('.01')
        lowered=topup_preview(r,m,held,'100','90','200.1','30','1000','.01',**costs)
        self.assertEqual(D(lowered['stop_budget_usdt']),30)
        self.assertEqual(D(lowered['current_equity_stop_budget_usdt']),10)
        self.assertEqual(lowered['quantity_btc'],'0')
        # A loss shrinks the fresh equity basis; the whole existing position is counted.
        r.loss_fraction=D('.03')
        held.update(mark_price='95',equity_usdt='995')
        r.snapshot.return_value=dict(held)
        values['/fapi/v1/depth']=dict(E=now,bids=[['94.9','1000']],asks=[['95','1000']])
        fallen=topup_preview(r,m,held,'100','90','200.1','30','1000','.01',**costs)
        self.assertEqual(D(fallen['current_equity_stop_budget_usdt']),D('29.85'))
        self.assertEqual(D(fallen['stop_budget_capital_usdt']),995)

    def test_current_equity_budget_counts_giving_back_unrealized_profit(self):
        m,r,s,values,_=self.fixture()
        now=m.last+1000
        held=dict(s,quantity_btc='1',entry='100',isolated_wallet_usdt='100',mark_price='400',equity_usdt='1300')
        r.snapshot.return_value=dict(held)
        values['/fapi/v1/depth']=dict(E=now,bids=[['399.9','1000']],asks=[['400','1000']])
        r.loss_fraction=D('.3')
        plan=topup_preview(r,m,held,'100','90','1000','490','1000','.01',
                           paid_commission_usdt='.05',realized_pnl_usdt='0')
        # Entry-to-stop loss fits 490; mark-to-stop giveback already exceeds
        # the fresh 300 budget. The add is refused, without reducing this position.
        self.assertEqual(plan['quantity_btc'],'0')
        self.assertEqual(D(plan['current_equity_stop_budget_usdt']),300)

    def test_lower_current_fee_does_not_discount_the_already_paid_entry_fee(self):
        m,r,s,values,_=self.fixture()
        now=m.last+1000
        values['/fapi/v1/depth']=dict(E=now,bids=[['109.9','1000']],asks=[['110','1000']])
        values['/fapi/v1/commissionRate']['takerCommissionRate']='.0001'
        held=dict(s,quantity_btc='1',entry='100',isolated_wallet_usdt='10',mark_price='110',equity_usdt='1010')
        r.snapshot.return_value=dict(held)
        plan=topup_preview(r,m,held,'5','90','200.1','30',stop_slippage_fraction='.01',
                           paid_commission_usdt='.05',realized_pnl_usdt='0')
        add=D(plan['quantity_btc']);price=D(plan['entry_estimate'])
        # The native entry paid .05 at the old rate. Only this new add and the
        # future exit use the lower current rate; their cost stays inside 30.
        loss=D('.05')+(1+add)*(D(100)-90)+add*(price-100)+add*price*D('.0001')
        loss+=(1+add)*90*(D('.01')+D('1.01')*D('.0001'))
        self.assertGreater(add,0)
        self.assertLessEqual(loss,30)
        self.assertEqual(add,D('.905'))

    def test_partial_reduction_retains_all_paid_fees_and_realized_losses(self):
        m,r,s,values,_=self.fixture()
        now=m.last+1000
        values['/fapi/v1/depth']=dict(E=now,bids=[['109.9','1000']],asks=[['110','1000']])
        held=dict(s,quantity_btc='.5',entry='100',isolated_wallet_usdt='10',mark_price='110',
                  wallet_usdt='979.85',available_usdt='979.85',equity_usdt='984.85')
        r.snapshot.return_value=dict(held)
        plan=topup_preview(r,m,held,'5','90','200.1','30',stop_slippage_fraction='.01',
                           paid_commission_usdt='.15',realized_pnl_usdt='-20')
        add=D(plan['quantity_btc']);price=D(plan['entry_estimate'])
        loss=D('.15')+20+D('.5')*(100-90)+add*(price-90)+add*price*D('.0005')
        loss+=(D('.5')+add)*90*(D('.01')+D('1.01')*D('.0005'))
        self.assertGreater(add,0)
        self.assertLessEqual(loss,30)
        # Cumulative realized losses can exhaust the campaign without changing
        # its residual entry price or making present equity nonpositive.
        spent=topup_preview(r,m,held,'5','90','200.1','30',stop_slippage_fraction='.01',
                            paid_commission_usdt='.15',realized_pnl_usdt='-30')
        self.assertEqual(spent['quantity_btc'],'0')
        for fee,pnl in ((None,'0'),('.15',None),('-1','0'),('NaN','0'),('.15','NaN')):
            with self.subTest(fee=fee,pnl=pnl),self.assertRaises((Blocked,Unknown)):
                topup_preview(r,m,held,'5','90','200.1','30',stop_slippage_fraction='.01',
                              paid_commission_usdt=fee,realized_pnl_usdt=pnl)
