"""Money and availability checks for the new fixed research screen."""
from decimal import Decimal as D
import json
import unittest

from research.flow_risk import DAY, FOUR, START, aggregate, coin_screen, flow_at, gate, kline, spot_screen


class FlowRiskChecks(unittest.TestCase):
    def test_quote_weighted_complete_day_and_availability(self):
        bars = {START+i*FOUR: (D(100), D(101), D(99), D(100), D(10), D(2)) for i in range(6)}
        bars[START+5*FOUR] = (D(100), D(101), D(99), D(100), D(100), D(90))
        daily = aggregate(bars, FOUR)
        spot = {START: (D(100), D(101), D(99), D(100), D(150), D(60))}
        self.assertFalse(flow_at(spot, daily, START+DAY+59999)['available'])
        event = flow_at(spot, daily, START+DAY+60000)
        self.assertLess(abs(event['perp_imbalance']-D(1)/3), D('1e-26'))
        self.assertTrue(event['veto'])
        # Dropping one 4h slot must not turn a partial day into a feature.
        del bars[START]
        self.assertNotIn(START, aggregate(bars, FOUR))

    def test_no_forming_day_and_microsecond_volume_validation(self):
        values = (D(100), D(101), D(99), D(100), D(10), D(5))
        spot, coin = {START: values}, {START: values}
        old = flow_at(spot, coin, START+DAY+60000)
        coin[START+DAY] = (*values[:4], D(10), D(10))
        self.assertEqual(old, flow_at(spot, coin, START+DAY+60000))
        row = [str(START*1000), '100', '101', '99', '100', '1', str((START+DAY)*1000-1), '10', '1', '1', '5', '0']
        self.assertEqual(kline(row, DAY)[0], START)
        row[10] = '11'
        with self.assertRaises(ValueError):
            kline(row, DAY)

    def test_spot_split_ownership_fees_and_remaining_trim_closure(self):
        # Two sleeves belong to ONE paid entry. A rise in ATR stress risk creates
        # one legal trim; subsequent real SELL settles both sleeve quantities.
        bars = {START+i*DAY: (D(100), D(100), D(100), D(100), D(10), D(5)) for i in range(-14, 4)}
        bars[START] = (D(100), D(200), D(100), D(100), D(10), D(5))
        buy_time, hold_time, sell_time = START+3600000, START+DAY+3600000, START+2*DAY+3600000
        buy = dict(id=1, order_id=1, time=buy_time, qty='1', quote='100', price='100', buyer=True, commission='.01', commission_asset='BTC')
        sell = dict(id=2, order_id=2, time=sell_time, qty='.99', quote='108.9', price='110', buyer=False, commission='.1089', commission_asset='USDT')
        allocations = [[str(i), json.dumps(dict(weights={'30':'1','40':'1'}, sleeves=[30,40])), 'settled', json.dumps(dict(orderId=i))] for i in (1,2)]
        row = dict(daily={'initial':dict(cash_usdt='1000')}, fills=[buy,sell], allocations=allocations,
                   opportunity_ledger=[dict(event='fill',id=1,decision_ms=buy_time-1000,signal_ms=START-DAY),
                                       dict(event='decision',decision_ms=hold_time,completed_bar_ms=START,
                                            sleeves={'30':dict(action='hold'),'40':dict(action='hold')})])
        result = spot_screen(row, bars, bars)
        self.assertEqual(result['actual_buy_cohorts'], 1)
        self.assertEqual(result['alpha_events'][0]['gain'], D('-8.7911'))
        trim = result['beta_events'][0]
        self.assertTrue(trim['closed'])  # string decision sleeve vs integer allocation regression
        self.assertEqual(result['beta']['closed']['count'], 1)
        self.assertEqual(trim['gain'], trim['removed']*(D('99.85005')-D('109.89')))

    def test_coin_campaign_costs_funding_and_fragment_independence(self):
        stamp = START+2*DAY+3600000
        identity = START+DAY
        # Two IOC fragments remain one campaign; entry/exit fees and funding
        # have distinct ledger identities and may not be lost or double-counted.
        trades = [dict(id=1,time=stamp,qty='.4',price='100',side='BUY'),
                  dict(id=2,time=stamp+1,qty='.6',price='100',side='BUY'),
                  dict(id=3,time=stamp+DAY,qty='1',price='101',side='SELL')]
        decision = dict(event='decision',at_ms=stamp-4000,opportunity=identity,action='enter')
        write = dict(event='write_attempt',at_ms=stamp-2000,identity='entry',opportunity=identity,
                     method='POST',payload=dict(side='BUY'))
        fills = [dict(event='fill',trade=t,client_order_id='entry' if t['side']=='BUY' else 'exit') for t in trades]
        income = [dict(time=stamp,incomeType='COMMISSION',income='-.03'),
                  dict(time=stamp+1,incomeType='COMMISSION',income='-.045'),
                  dict(time=stamp+1000,incomeType='FUNDING_FEE',income='-.2'),
                  dict(time=stamp+DAY,incomeType='COMMISSION',income='-.07575'),
                  dict(time=stamp+DAY,incomeType='REALIZED_PNL',income='1')]
        values = (D(100), D(101), D(99), D(100), D(10), D(6))
        market = {START+DAY:values}
        row = dict(trades=trades,funding_ledger=income,sessions=[dict(start_ms=stamp-10000)],
                   opportunity_ledger=[decision,write,*fills])
        result = coin_screen(row, market, market)
        self.assertEqual(result['actual_campaigns'], 1)
        self.assertEqual(result['actual_fills'], 3)
        self.assertEqual(result['alpha_events'][0]['gain'], D('-.64925'))

    def test_profitable_veto_and_insufficient_episodes_never_promote(self):
        rows = [dict(time_ms=START,notional=D(100),gain=D(-2),closed=True)]
        outcome = gate(rows, rows, 1, D(1))
        self.assertEqual(outcome['decision'], 'REJECT_FIXED_RULE')
        self.assertFalse(outcome['gates']['positive_net'])
        self.assertFalse(outcome['gates']['count'])


if __name__ == '__main__':
    unittest.main()
