import unittest
from research.tradeoff_routes import evaluate, owned_reduction


class TradeoffRoutes(unittest.TestCase):
    def test_reduction_requires_fresh_protected_owned_capacity(self):
        account=dict(symbol='BTCUSDT',owned=True,protected=True,pending=False,available_ms=100,
                     kind='coin',owned_btc='1',confirmed_reducible_btc='.4')
        self.assertEqual(owned_reduction(account,100,'.5')['status'],'BLOCK_REDUCTION_CAPACITY')
        account['confirmed_reducible_btc']='1'
        plan=owned_reduction(account,100,'.5')
        self.assertEqual(plan['quantity_btc'],'0.5');self.assertTrue(plan['reduce_only'])
        self.assertEqual(plan['orders'],0)
        self.assertEqual(owned_reduction(account,60101,'.5')['status'],'BLOCK_UNKNOWN_ACCOUNT')

    def test_missing_future_and_incomplete_data_cannot_enter_accounts(self):
        packet=dict(decision_ms=100)
        result=evaluate(packet)
        self.assertEqual(result['account_entrants'],0)
        packet['cross-venue']=dict(end_ms=101,available_ms=101,source_sha256=['a'*64],base='BTC',quote='USDT')
        self.assertEqual(evaluate(packet)['observations']['cross-venue']['status'],'BLOCK_INFORMATION')

    def test_exit_never_infers_an_event_from_an_unowned_clock(self):
        result=evaluate(dict(decision_ms=100,owned_event=dict(confirmed_fill_ms=101,family='absorption',source_sha256='a'*64)))
        self.assertEqual(result['expressions']['absorption-decay-exit']['status'],'BLOCK_EVENT_OWNERSHIP')
