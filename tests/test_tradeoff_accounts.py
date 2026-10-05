import unittest
from decimal import Decimal as D
from types import SimpleNamespace
from research.tradeoff_accounts import policy_runtime, signal_book


class TradeoffAccounts(unittest.TestCase):
    def test_short_only_keeps_causal_clock_and_checkpoint_mode(self):
        packet = {'bars':{str(i*86400000):dict(open='100', high='101', low='99', close=str(100+i))
                          for i in range(120)}}
        book, _ = signal_book(packet, 'channel-short', 'a'*64)
        self.assertEqual(book.mode, 'channel-short')
        self.assertTrue(all(r['direction'] <= 0 for r in book.rows))
        self.assertIsNone(book.at(86459999))
        self.assertEqual(book.at(86460000)['day_ms'], 0)

    def test_budget_restore_and_offline_guard(self):
        from coinquant import campaign
        before = campaign.PRIMARY_RISK, campaign.MACRO_RISK
        with self.assertRaisesRegex(ValueError, 'offline'):
            with policy_runtime('uniform75', None) as runtime:
                self.assertEqual(D(campaign.PRIMARY_RISK), D(before[0])*D('.75'))
                runtime.run(None, SimpleNamespace(offline=False), execute=True)
        self.assertEqual((campaign.PRIMARY_RISK, campaign.MACRO_RISK), before)
