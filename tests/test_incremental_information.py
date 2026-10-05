from decimal import Decimal as D
from types import SimpleNamespace
import unittest

from research.incremental_information import (DAY, FUNDING_LAG, ReleaseBook, assess,
                                              mature_cross, proposal, qualify_cross)


class IncrementalInformationTests(unittest.TestCase):
    def book(self):
        bars = [(i*DAY, '100', '120', '90', str(100+i)) for i in range(41)]
        # Repair OHLC high for the later controls without using future prices.
        bars = [(t, o, '150', l, c) for t, o, _, l, c in bars]
        funding = [(i*FUNDING_LAG, (i+1)*FUNDING_LAG,
                    D('.0002') if i < 88 else D('.0001'), None) for i in range(125)]
        basis = [(i*DAY, i*DAY+60000, D('.02')-D(i)/10000, None) for i in range(1, 42)]

        class Features:
            sha256 = 'a'*64
            records = dict(funding=funding, basis=basis)

            def value(self, name, now):
                rows = [r for r in self.records[name] if r[1] <= now]
                row = rows[-1] if rows else (None, None, None, 'missing')
                self.last_lookup = dict(observation_ms=row[0], available_ms=row[1])
                return row[2]

        return ReleaseBook(bars, Features())

    def test_feature_uses_completed_settlements_and_price_controls(self):
        book = self.book()
        now = 31*DAY+60000
        event = book.at(now)
        self.assertEqual(event['status'], 'FEATURE_READY')
        self.assertTrue(event['release'])
        self.assertLessEqual(event['latest_input_available_ms'], now)
        self.assertEqual(event['day_ms'], 30*DAY)
        self.assertEqual(event['momentum20'], D(130)/110-1)

    def test_missing_funding_is_not_zero_and_label_is_fully_mature(self):
        book = self.book()
        label = book.label(22*DAY, 'coin')
        self.assertGreaterEqual(label['available_ms'], label['exit_ms'])
        book.funding.pop((24*DAY)//FUNDING_LAG+1)
        self.assertIsNone(book.label(22*DAY, 'coin'))
        self.assertIsNotNone(book.label(22*DAY, 'spot'))

    def test_future_settlement_cannot_change_current_feature(self):
        book = self.book()
        now = 31*DAY+60000
        expected = book.at(now)
        slot = now//FUNDING_LAG+1
        book.funding[slot] = (slot*FUNDING_LAG, (slot+1)*FUNDING_LAG, D('999'), None)
        self.assertEqual(book.at(now), expected)

    def test_rejected_information_and_account_context_do_not_propose_money(self):
        book = self.book()
        result = proposal(book, {'status': 'NO_SUPPORT'}, 31*DAY+60000,
                          'release-new-primary', offline=True)
        self.assertEqual(result['status'], 'NOT_ADMITTED')
        result = proposal(book, {'status': 'ELIGIBLE_FINITE_ACCOUNT_PROPOSAL'}, 31*DAY+60000,
                          'release-full-otherwise-half', offline=True,
                          legal_new_buy=True, protected=True, pending=True)
        self.assertEqual(result['status'], 'BLOCK_ACCOUNT_CONTEXT')

    def test_flat_primary_keeps_original_priority_and_macro_requirement(self):
        book = self.book()
        ready = {'status': 'ELIGIBLE_FINITE_ACCOUNT_PROPOSAL'}
        args = dict(offline=True, confirmed_flat=True, protected=True, pending=False, causal_macro=True)
        blocked = proposal(book, ready, 31*DAY+60000, 'release-new-primary', price_priority=True, **args)
        allowed = proposal(book, ready, 31*DAY+60000, 'release-new-primary', price_priority=False, **args)
        self.assertEqual(blocked['status'], 'NO_NEW_OPPORTUNITY')
        self.assertEqual(allowed['status'], 'PROPOSE_NEW_PRIMARY_RESEARCH')
        self.assertEqual(allowed['gross_equity_cap'], '1')
        self.assertEqual(allowed['orders'], 0)

    def packet(self):
        hashes = ['a'*64, 'b'*64, 'c'*64]
        return dict(start_ms=1000, end_ms=2000, available_ms=2100, base='BTC', quote='USDT',
                    venues=['a', 'b'], source_sha256=hashes, complete_window=True,
                    conversion_qualified=True, fx_pair='USDT/USD', fx_book_ms=1950,
                    fx_available_ms=2000, fx_bid='.999', fx_ask='1.001', fx_source_sha256=hashes[2],
                    observation_ms=2000,
                    flows=[dict(venue=v, buy_btc='2', sell_btc='1') for v in ('a', 'b')],
                    boundary_proofs=[dict(venue=v, unit='BTC', side_role='taker',
                        semantics_sha256=hashes[0], gaps=[], conflicts=[], reconnects=0,
                        prefix=dict(event_ms=900, available_ms=950, raw_sha256=hashes[0], sequence_complete=True),
                        tail=dict(event_ms=2050, available_ms=2100, raw_sha256=hashes[1], sequence_complete=True)) for v in ('a', 'b')])

    def test_complete_flag_cannot_replace_boundary_proofs_or_fresh_fx(self):
        packet = self.packet()
        packet['boundary_proofs'][0]['tail'] = None
        self.assertEqual(qualify_cross(packet, 2100)['status'], 'PENDING')
        packet = self.packet()
        packet['fx_book_ms'] = 1
        with self.assertRaises(ValueError):
            qualify_cross(packet, 2100)
        with self.assertRaises(ValueError):
            qualify_cross(self.packet(), 2099)

    def test_qualified_window_still_needs_real_mature_outcomes(self):
        window = qualify_cross(self.packet(), 2100)
        self.assertEqual(window['status'], 'QUALIFIED_RESEARCH_FEATURE')
        result = mature_cross([window], {}, 2100)
        self.assertEqual(result['status'], 'PENDING')
        self.assertFalse(result['account_entrant'])
        self.assertFalse(result['independent_alpha_proven'])
        self.assertEqual(result['matured_nonoverlapping'], 0)

    def test_no_events_remain_support_pending(self):
        self.assertEqual(assess([], 0)['status'], 'PENDING')


if __name__ == '__main__':
    unittest.main()
