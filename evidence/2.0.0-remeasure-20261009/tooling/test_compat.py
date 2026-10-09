"""Small offline integration checks for the recovered research adapter.

Synthetic inputs use the real Market, TradePrints ZIP parser and PriorFX. The
production coordinator, writer, ownership decoder, fees and matching run
unchanged. These are compatibility checks, not historical economic evidence.
State cases run in a child process with normal HOME and locks, using synthetic
UID 12017 and a separate temporary state directory; no account CLI is invoked.
"""
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

from coinquant.campaign import Campaign
from coinquant.config import Config
from coinquant.opportunities import Opportunity
from coinquant.ownership import owned_observation
from coinquant.session import run
from coinquant.state import State
from coinquant.types import Blocked
from research.complete_perp import ResearchExchange
from research.replay_checkpoint import (
    FIELDS, digest, restore_venue, snapshot_venue, source_fingerprint,
)
from research.session_market import Market, TradePrints
from research.unified_perp import PriorFX


FOUR = 14_400_000
MINUTE = 60_000
BOUNDARY = 1770004800000 // FOUR * FOUR
START = BOUNDARY + 1000
UID = 12017
INITIAL = D(1000)


class Inputs:
    def __init__(self, root, *, print_quantity='.006', trigger=None):
        self.root = Path(root)
        self.prints = self.root / 'prints'
        self.prints.mkdir()
        self.fx = self.root / 'fx.json'
        self.fx.write_text(json.dumps({'rates': {'2020-01-01': {'CNY': '7'}}}))
        self.minutes = {}
        rows = []
        identity = 1
        for minute in range(BOUNDARY - MINUTE, BOUNDARY + 15 * MINUTE, MINUTE):
            prices = []
            for stamp in range(minute, minute + MINUTE, 250):
                price = D(trigger[1]) if trigger and stamp >= trigger[0] else D(100000)
                prices.append(price)
                rows.append(f'{identity},{price},{print_quantity},{identity},{identity},{stamp},false\n')
                identity += 1
            self.minutes[minute] = (prices[0], max(prices), min(prices), prices[-1], D(10))
        date = datetime.fromtimestamp(BOUNDARY / 1000, timezone.utc).strftime('%Y-%m-%d')
        archive = self.prints / f'BTCUSDT-aggTrades-{date}.zip'
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as target:
            target.writestr(archive.stem + '.csv', ''.join(rows))
        sha = hashlib.sha256(archive.read_bytes()).hexdigest()
        Path(str(archive) + '.CHECKSUM').write_text(f'{sha}  {archive.name}\n')

    def venue(self, config=None):
        market = Market({}, (), identity={
            'trade': dict(self.minutes), 'mark': dict(self.minutes),
        })
        venue = ResearchExchange(
            market, START, INITIAL, fx=PriorFX(self.fx), initial_cny=INITIAL * 7,
            matcher='trade_print', prints=TradePrints(self.prints), uid=UID,
        )
        venue.read_latency_ms = 200
        venue.latency_ms = 1000
        venue.mark_gap = 'bound'
        venue.offline = True
        config = config or Config(str(UID), str(self.root / 'state'), 60, 5)
        venue.loss_fraction = config.loss_fraction
        venue.slip_fraction = config.slip_fraction
        return venue


def order(venue, name, side, quantity, *, price='100000', reduce=False):
    params = dict(symbol='BTCUSDT', positionSide='BOTH', side=side,
                  newClientOrderId='cq-' + name, quantity=str(quantity))
    if reduce:
        params.update(type='MARKET', reduceOnly='true')
    else:
        params.update(type='LIMIT', timeInForce='IOC', price=str(price))
    return venue.send('POST', '/fapi/v1/order', params)


def protection(venue, name, side, kind, price, state=None):
    params = dict(symbol='BTCUSDT', positionSide='BOTH', side=side,
                  clientAlgoId='cq-' + name, type=kind, triggerPrice=str(price),
                  workingType='MARK_PRICE', closePosition='true', priceProtect='false')
    if state is not None:
        state.prepare(params['clientAlgoId'], 'binance_algo', params)
    return venue.send('POST', '/fapi/v1/algoOrder', params)


def seed(config):
    model = Campaign()
    model.last = model.model.last = BOUNDARY
    model.returns.extend([D('.02')] * 20)
    model.model.active = Opportunity(BOUNDARY, 1, D(95000), D(110000), BOUNDARY + FOUR)
    with State(config.state_dir, config.scope) as state:
        state.set('linear_campaign', model.checkpoint())


def session_fixture(check, root):
    config = Config(str(UID), str(Path(root) / 'state'), 60, 5)
    inputs = Inputs(root, print_quantity='1')
    venue = inputs.venue(config)
    seed(config)
    report = run(config, venue, execute=True, monotonic=venue.monotonic, wait=venue.wait)
    check.assertEqual(report['cleanup'], 'verified', report)
    check.assertFalse(report['execution_unresolved'], report)
    check.assertEqual(report['pending_intents'], 0, report)
    check.assertGreater(venue.q, 0, report)
    check.assertTrue(report['actual']['native_full_position_protected'], report)
    check.assertTrue(report['actual']['stop_before_liquidation'], report)
    check.assertNotEqual(report.get('income_audit', {}).get('status'), 'unresolved', report)
    return config, inputs, venue, report


def binding_for(config, venue):
    return dict(source_sha256=source_fingerprint(),
                strategy_sha256=digest(asdict(config)),
                input_sha256=digest((venue.market.identity, venue.prints.loaded, venue.fx.sha256)),
                schedule_sha256=digest([START, START + 2 * MINUTE]))


def isolated_case(case):
    check = unittest.TestCase()
    with tempfile.TemporaryDirectory(prefix='coinquant-replay-compat-') as temporary:
        if case == 'owned-trigger':
            for direction in (1, -1):
                root = Path(temporary) / str(direction)
                root.mkdir()
                trigger_at = BOUNDARY + MINUTE + 5000
                trigger_price = D(99400 if direction > 0 else 100600)
                inputs = Inputs(root, trigger=(trigger_at, trigger_price))
                venue = inputs.venue()
                side = 'BUY' if direction > 0 else 'SELL'
                exit_side = 'SELL' if direction > 0 else 'BUY'
                order(venue, 'trigger-entry', side, '.010')
                config = Config(str(UID), str(root / 'state'))
                with State(config.state_dir, config.scope) as state:
                    parent = protection(venue, 'stop', exit_side, 'STOP_MARKET',
                                        99500 if direction > 0 else 100500, state)
                    accepted_at = parent['createTime']
                    check.assertEqual(parent['algoType'], 'CONDITIONAL')
                    check.assertEqual(accepted_at, venue.now_ms)
                    protection(venue, 'take', exit_side, 'TAKE_PROFIT_MARKET',
                               110000 if direction > 0 else 90000, state)
                    observed = owned_observation(state, venue, 'cq-stop', conditional=True)
                    check.assertFalse(venue.conditional_terminal('cq-stop'))
                    check.assertIsNone(observed['child'])
                    check.assertEqual(observed['parent']['createTime'], accepted_at)
                    venue.advance_unattended(trigger_at + 1)
                    observed = owned_observation(state, venue, 'cq-stop', conditional=True)
                    check.assertTrue(venue.conditional_terminal('cq-stop'))
                    child = observed['child']
                    check.assertEqual(str(child['orderId']), observed['parent']['actualOrderId'])
                    check.assertEqual(observed['parent']['createTime'], accepted_at)
                    check.assertEqual(child['side'], exit_side)
                    check.assertTrue(child['reduceOnly'])
                    fills = [t for t in venue.trades if t['orderId'] == child['orderId']]
                    check.assertEqual(len(fills), 1)
                    fill = fills[0]
                    check.assertEqual(fill['time'], trigger_at)
                    check.assertEqual(D(fill['price']), trigger_price)
                    check.assertEqual(D(fill['realizedPnl']), D(-6))
                    check.assertEqual(D(fill['commission']), D('.010') * trigger_price * venue.fee)
                    check.assertEqual(fill['commissionAsset'], 'USDT')
                    check.assertEqual(venue.q, 0)
                    check.assertEqual(venue.wallet, INITIAL - D(6) - venue.fees)
                    check.assertEqual(venue.algos['cq-take']['algoStatus'], 'CANCELED')
                    check.assertIn('cq-stop', state.get('terminal_native_orders'))
            return

        config, inputs, venue, report = session_fixture(check, temporary)
        if case == 'session-risk':
            expected = dict(max_stop_loss_fraction=config.max_stop_loss_fraction,
                            stop_slippage_fraction=config.stop_slippage_fraction)
            check.assertEqual(venue.loss_fraction, D(expected['max_stop_loss_fraction']))
            check.assertEqual(venue.slip_fraction, D(expected['stop_slippage_fraction']))
            if 'risk_limits' in report:  # added to the current runtime's report
                check.assertEqual(report['risk_limits'], expected)
            # The entry cycle's preview may describe its pre-fill ownership.
            # Verify the native fills actually accepted into the durable ledger.
            with State(config.state_dir, config.scope) as state:
                fills = [json.loads(row[0]) for row in state.db.execute('SELECT payload FROM native_fills')]
            check.assertTrue(fills, report)
            check.assertTrue(all(row['commissionAsset'] == 'USDT' for row in fills))
            check.assertEqual(sum((D(row['commission']) for row in fills), D(0)), venue.fees)
            check.assertEqual(sum((D(row['realizedPnl']) for row in fills), D(0)), 0)
            before = (venue.now_ms, len(venue.sent), venue.wallet, venue.q)
            venue.loss_fraction = D('.11')
            with check.assertRaisesRegex(Blocked, 'configuration differ'):
                run(config, venue, execute=True, monotonic=venue.monotonic, wait=venue.wait)
            check.assertEqual((venue.now_ms, len(venue.sent), venue.wallet, venue.q), before)
            return

        binding = binding_for(config, venue)
        saved = snapshot_venue(venue, binding=binding, config=config, session_report=report)
        # Exercise the JSON codec exactly as a file checkpoint does.
        saved = json.loads(json.dumps(saved, allow_nan=False))
        if case == 'restore':
            resumed = inputs.venue(config)
            restore_venue(resumed, saved, binding=binding, config=config)
            check.assertEqual(snapshot_venue(resumed, binding=binding, config=config, session_report=report), saved)
            for native in resumed.orders.values():
                check.assertIs(resumed.by_order_id[native['orderId']], native)
            until = venue.now_ms + 2 * MINUTE
            venue.advance_unattended(until)
            resumed.advance_unattended(until)
            for key in FIELDS:
                check.assertEqual(getattr(resumed, key, None), getattr(venue, key, None), key)
            check.assertEqual(resumed.prints.loaded, venue.prints.loaded)
            return
        if case == 'tamper':
            broken = deepcopy(saved)
            broken['sha256'] = '0' * 64
            with check.assertRaisesRegex(ValueError, 'digest mismatch'):
                restore_venue(inputs.venue(config), broken, binding=binding, config=config)
            changed = dict(binding, schedule_sha256=digest([START, START + 3 * MINUTE]))
            with check.assertRaisesRegex(ValueError, 'dependencies'):
                restore_venue(inputs.venue(config), saved, binding=changed, config=config)
            # The same SQLite bytes cannot stand in for a different archived prefix.
            archive = Path(config.state_dir) / 'observations-archive.jsonl'
            archive.write_text('{"test_fixture":"unexpected archive"}\n')
            with check.assertRaisesRegex(ValueError, 'SQLite was changed or replaced'):
                restore_venue(inputs.venue(config), saved, binding=binding, config=config)
            archive.unlink()
            with State(config.state_dir, config.scope) as state:
                state.set('linear_campaign', {'test_fixture': 'changed durable model'})
            with check.assertRaisesRegex(ValueError, 'SQLite was changed or replaced'):
                restore_venue(inputs.venue(config), saved, binding=binding, config=config)
            return
        raise AssertionError('unknown isolated case: ' + case)


class AdapterCompatibilityTests(unittest.TestCase):
    def isolated(self, case):
        # The environment, HOME and normal account lock behavior are inherited.
        result = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--case', case],
                                capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout[-10000:] + result.stderr[-18000:])

    def test_ioc_add_partial_and_full_close_cash(self):
        for direction in (1, -1):
            with self.subTest(direction=direction), tempfile.TemporaryDirectory(prefix='coinquant-fill-compat-') as root:
                venue = Inputs(root).venue()
                side = 'BUY' if direction > 0 else 'SELL'
                exit_side = 'SELL' if direction > 0 else 'BUY'
                add_price = D(102000 if direction > 0 else 98000)
                first = order(venue, 'first', side, '.010')
                self.assertEqual(first['status'], 'FILLED')
                self.assertEqual(venue.q, D('.010') * direction)
                second = order(venue, 'add', side, '.010', price=add_price)
                self.assertEqual(second['status'], 'FILLED')
                self.assertEqual(venue.q, D('.020') * direction)
                self.assertEqual(venue.entry, (D(100000) + add_price) / 2)
                self.assertEqual(len(venue.trades), 4)  # .006 + .004 in each IOC window
                self.assertTrue(all(D(t['realizedPnl']) == 0 for t in venue.trades))
                self.assertEqual(venue.wallet, INITIAL - venue.fees)
                partial = order(venue, 'partial', exit_side, '.005', reduce=True)
                self.assertEqual(partial['status'], 'FILLED')
                self.assertEqual(venue.q, D('.015') * direction)
                self.assertEqual(D(venue.trades[-1]['realizedPnl']), D(-5))
                self.assertEqual(venue.wallet, INITIAL - D(5) - venue.fees)
                final = order(venue, 'final', exit_side, '.015', reduce=True)
                self.assertEqual(final['status'], 'FILLED')
                self.assertEqual(venue.q, 0)
                self.assertEqual(venue.entry, 0)
                self.assertEqual(venue.margin, 0)
                self.assertEqual(D(venue.trades[-1]['realizedPnl']), D(-15))
                self.assertEqual(venue.wallet, INITIAL - D(20) - venue.fees)
                for trade in venue.trades:
                    self.assertEqual(trade['commissionAsset'], 'USDT')
                    self.assertEqual(D(trade['commission']), D(trade['qty']) * D(trade['price']) * venue.fee)
                    self.assertIn(trade['orderId'], venue.by_order_id)
                self.assertEqual(sum((D(t['commission']) for t in venue.trades), D(0)), venue.fees)
                self.assertEqual(sum((D(t['realizedPnl']) for t in venue.trades), D(0)), D(-20))
                self.assertEqual(sum((D(i['income']) for i in venue.income), D(0)), venue.wallet - INITIAL)
                self.assertEqual(venue.funnel['ioc_submitted'], 2)
                self.assertEqual(venue.funnel['liquidations'], 0)

    def test_trigger_child_is_owned_and_costed(self):
        self.isolated('owned-trigger')

    def test_production_session_accepts_default_and_refuses_mismatched_risk(self):
        self.isolated('session-risk')

    def test_checkpoint_restores_state_and_native_order_identity(self):
        self.isolated('restore')

    def test_checkpoint_refuses_changed_payload_dependencies_or_durable_prefix(self):
        self.isolated('tamper')


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--case':
        isolated_case(sys.argv[2])
    else:
        unittest.main()
