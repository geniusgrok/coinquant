from dataclasses import replace
from decimal import Decimal as D
import tempfile
import unittest

from pancakequant.config import Config
from pancakequant.execution import coverage, run_once
from pancakequant.model import decide, liquidation_price, repair_target
from pancakequant.types import Position, Unknown, ModelConfig
from test_model import sample, history


def protectors(p):
    if not p.quantity:
        return ()
    common = dict(symbol='BTCUSD', positionIdx=0, side='Sell' if p.quantity > 0 else 'Buy',
                  orderStatus='Untriggered', orderType='Market', tpslMode='Full',
                  closeOnTrigger=True, reduceOnly=True, triggerBy='MarkPrice', qty=str(abs(p.quantity)))
    return tuple(dict(common, orderId=k, stopOrderType=k, triggerPrice=str(price))
                 for k, price in (('TakeProfit', p.take_profit), ('StopLoss', p.stop_loss)))


class FakeVenue:
    def __init__(self, snapshot=None):
        self.s = snapshot or sample()
        self.records = {}
        self.writes = []
        self.failure = ''
        self.fill_limit = None
        self.cancel_race = False

    def identity(self):
        return '12345'

    def snapshot(self):
        if self.failure == 'snapshot':
            raise Unknown('conditional order query unavailable')
        return self.s

    def candles(self, now):
        if self.failure == 'candles':
            raise Unknown('market data missing')
        return history()

    def lookup(self, link):
        return self.records.get(link)

    def _fill(self, delta, target, reduce_only):
        p, price = self.s.position, target.entry
        if reduce_only:
            assert delta * p.quantity < 0 and abs(delta) <= abs(p.quantity)
            new_qty = p.quantity + delta
            wallet = self.s.wallet_btc + (-delta) * (1 / p.entry - 1 / price)
            entry = p.entry
        else:
            new_qty = p.quantity + delta
            wallet = self.s.wallet_btc
            entry = new_qty / (p.quantity / p.entry + delta / price) if p.quantity else price
        wallet -= abs(delta) * self.s.rules.taker_fee / price
        if new_qty:
            margin = abs(new_qty) / entry / 20
            liq = liquidation_price(new_qty, entry, margin, self.s.rules.maintenance_rate, self.s.rules.taker_fee)
            p = Position(new_qty, entry, margin, liq,
                         p.take_profit if reduce_only else target.take_profit,
                         p.stop_loss if reduce_only else target.stop_loss)
        else:
            p = Position()
        self.s = replace(self.s, wallet_btc=wallet, position=p,
                         available_btc=wallet - p.margin_btc, orders=protectors(p))

    def place(self, link, delta, target, *, reduce_only=False):
        self.writes.append(('place', link, delta, reduce_only))
        if self.failure == 'missing':
            raise Unknown('request timed out; receipt unavailable')
        fill = delta if self.fill_limit is None else (1 if delta > 0 else -1) * min(abs(delta), self.fill_limit)
        self._fill(fill, target, reduce_only)
        status = 'Filled' if fill == delta else 'PartiallyFilledCanceled'
        if self.cancel_race:
            status = 'PartiallyFilled'
            order = dict(symbol='BTCUSD', orderLinkId=link, orderStatus=status, reduceOnly=False, qty=str(abs(delta)), cumExecQty=str(abs(fill)))
            self.s = replace(self.s, orders=self.s.orders + (order,))
        self.records[link] = dict(symbol='BTCUSD', orderLinkId=link, orderStatus=status, cumExecQty=str(abs(fill)))
        if self.failure == 'ack':
            raise Unknown('acknowledgment lost after exchange filled')
        return {'orderLinkId': link}

    def cancel(self, link):
        self.writes.append(('cancel', link))
        self.records[link]['orderStatus'] = 'Cancelled'
        self.s = replace(self.s, orders=protectors(self.s.position))
        return {'orderLinkId': link}

    def protect(self, target):
        self.writes.append(('protect',))
        if self.failure == 'protection':
            raise Unknown('protection service unavailable')
        p = replace(self.s.position, take_profit=target.take_profit, stop_loss=target.stop_loss)
        self.s = replace(self.s, position=p, orders=protectors(p))
        return {}


class ExecutionTests(unittest.TestCase):
    def config(self, directory):
        return Config(account_uid='12345', max_position_usd=D(100000), state_dir=directory)

    def test_read_only_is_default_and_keys_do_not_enable_writes(self):
        venue = FakeVenue()
        with tempfile.TemporaryDirectory() as path:
            r = run_once(venue, self.config(path))
        self.assertEqual(r['status'], 'read_only')
        self.assertEqual(venue.writes, [])
        self.assertEqual(venue.s.position.quantity, 0)

    def test_real_account_match_required(self):
        venue = FakeVenue()
        with tempfile.TemporaryDirectory() as path:
            r = run_once(venue, replace(self.config(path), account_uid='999'), execute=True)
        self.assertEqual(r['status'], 'blocked')
        self.assertEqual(venue.writes, [])

    def test_unknown_ack_reconciles_without_duplicate_and_same_candle_skips_entry(self):
        venue = FakeVenue(); venue.failure = 'ack'
        with tempfile.TemporaryDirectory() as path:
            config = self.config(path)
            a = run_once(venue, config, execute=True)
            b = run_once(venue, config, execute=True)
        self.assertEqual(a['status'], 'executed')
        self.assertEqual(b['status'], 'no_action')
        self.assertEqual(sum(w[0] == 'place' for w in venue.writes), 1)
        self.assertTrue(coverage(venue.s))

    def test_absent_unknown_order_stays_pending_and_is_not_resent(self):
        venue = FakeVenue(); venue.failure = 'missing'
        with tempfile.TemporaryDirectory() as path:
            config = self.config(path)
            a = run_once(venue, config, execute=True)
            b = run_once(venue, config, execute=True)
        self.assertEqual(a['status'], 'unknown')
        self.assertEqual(b['status'], 'unknown')
        self.assertTrue(b['pending_intents'])
        self.assertEqual(sum(w[0] == 'place' for w in venue.writes), 1)

    def test_local_state_loss_uses_exchange_client_identifier(self):
        venue = FakeVenue()
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as lost:
            run_once(venue, self.config(first), execute=True)
            # Stop hit while offline. The filled parent receipt remains at venue.
            venue.s = replace(venue.s, position=Position(), orders=())
            r = run_once(venue, self.config(lost), execute=True)
        self.assertEqual(sum(w[0] == 'place' for w in venue.writes), 1)
        self.assertEqual(venue.s.position.quantity, 0)
        self.assertEqual(r['status'], 'no_action')

    def test_partial_fill_has_full_actual_coverage_and_remainder_is_cancelled(self):
        venue = FakeVenue(); venue.fill_limit = D(2); venue.cancel_race = True
        with tempfile.TemporaryDirectory() as path:
            r = run_once(venue, self.config(path), execute=True)
        self.assertEqual(r['status'], 'partial')
        self.assertEqual(venue.s.position.quantity, 2)
        self.assertTrue(coverage(venue.s))
        self.assertEqual(sum(w[0] == 'cancel' for w in venue.writes), 1)
        self.assertFalse(r['pending_intents'])

    def test_position_above_single_order_cap_can_still_be_fully_protected(self):
        venue = FakeVenue(replace(
            sample(), rules=replace(sample().rules, maximum=D(5))))
        for quantity in (D(10), D(31)):
            p = Position(quantity, D(30745), D('0.0002'), D(29000),
                         D(33000), D(30000))
            snapshot = replace(
                venue.s, position=p,
                available_btc=venue.s.wallet_btc - p.margin_btc,
                orders=protectors(p))
            self.assertTrue(coverage(snapshot))

    def test_immediate_target_is_chunked_to_single_order_max(self):
        snapshot = replace(sample(), rules=replace(sample().rules, maximum=D(5)))
        venue = FakeVenue(snapshot)
        with tempfile.TemporaryDirectory() as path:
            r = run_once(venue, self.config(path), execute=True)
        self.assertEqual(r['status'], 'partial')
        places = [w for w in venue.writes if w[0] == 'place']
        self.assertEqual(len(places), 1)
        self.assertEqual(abs(places[0][2]), D(5))
        self.assertEqual(abs(venue.s.position.quantity), D(5))
        self.assertTrue(coverage(venue.s))

    def test_position_fields_without_native_orders_are_not_protection(self):
        venue = FakeVenue()
        with tempfile.TemporaryDirectory() as path:
            run_once(venue, self.config(path), execute=True)
        self.assertTrue(coverage(venue.s))
        self.assertFalse(coverage(replace(venue.s, orders=())))
        bad = tuple(dict(o, qty='0.1') for o in venue.s.orders)
        self.assertFalse(coverage(replace(venue.s, orders=bad)))

    def test_same_candle_and_missing_data_still_repair_protection(self):
        venue = FakeVenue()
        with tempfile.TemporaryDirectory() as path:
            config = self.config(path)
            run_once(venue, config, execute=True)
            venue.s = replace(venue.s, orders=())
            venue.failure = 'candles'
            r = run_once(venue, config, execute=True)
        self.assertEqual(r['status'], 'unknown')
        self.assertTrue(coverage(venue.s))
        self.assertEqual(sum(w[0] == 'place' for w in venue.writes), 1)
        self.assertTrue(any(w[0] == 'protect' for w in venue.writes))
        self.assertEqual(sum(w[0] == 'cancel' for w in venue.writes), 0)

    def test_protection_failure_attempts_reduce_only_not_increase(self):
        venue = FakeVenue()
        with tempfile.TemporaryDirectory() as path:
            config = self.config(path)
            run_once(venue, config, execute=True)
            venue.s = replace(venue.s, orders=())
            venue.failure = 'protection'
            r = run_once(venue, config, execute=True)
        self.assertEqual(venue.s.position.quantity, 0)
        self.assertTrue(venue.writes[-1][3])
        self.assertEqual(r['emergency'], 'flat_verified')

    def test_forged_risk_target_is_blocked_before_exchange_write(self):
        venue = FakeVenue()
        unsafe = replace(decide(history(), venue.s, ModelConfig()), quantity=D(5000))
        with tempfile.TemporaryDirectory() as path:
            from unittest.mock import patch
            with patch('pancakequant.execution.decide', return_value=unsafe):
                r = run_once(venue, self.config(path), execute=True)
        self.assertEqual(r['status'], 'blocked')
        self.assertEqual(venue.writes, [])
        self.assertIn('risk-increasing target', r['reason'])

    def test_prewrite_block_does_not_consume_signal_candle(self):
        venue = FakeVenue()
        unsafe = replace(decide(history(), venue.s, ModelConfig()), quantity=D(5000))
        with tempfile.TemporaryDirectory() as path:
            config = self.config(path)
            from unittest.mock import patch
            with patch('pancakequant.execution.decide', return_value=unsafe):
                first = run_once(venue, config, execute=True)
            second = run_once(venue, config, execute=True)
        self.assertEqual(first['status'], 'blocked')
        self.assertIn(second['status'], ('executed', 'partial'))
        self.assertEqual(sum(w[0] == 'place' for w in venue.writes), 1)

    def test_failed_order_read_is_not_empty_account(self):
        venue = FakeVenue(); venue.failure = 'snapshot'
        with tempfile.TemporaryDirectory() as path:
            r = run_once(venue, self.config(path), execute=True)
        self.assertEqual(r['status'], 'unknown')
        self.assertEqual(venue.writes, [])


if __name__ == '__main__':
    unittest.main()
