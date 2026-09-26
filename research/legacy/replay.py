"""Sparse account replay using the SAME production target model.

The manifest selects a supported aligned base interval (one minute or one hour).
Whole-account extrema include BTC collateral. Intrabar path uncertainty is handled
conservatively; it is never resolved by assuming the most favorable fill order.
"""
from collections import deque
from dataclasses import replace
import csv
from decimal import Decimal as D
import gzip
import json
from pathlib import Path

from coinquant.data import Dataset, MINUTE
from .model import bankruptcy_price, decide, liquidation_price, validate_risk_increase
from .pending import validate_target
from coinquant.research import economic_limits, digest, invocations, iso, source_identity, spec, timestamp
from coinquant.types import Bar, Blocked, INTERVAL_MS, Position, Snapshot, ZERO, floor_step, serial


class Account:
    def __init__(self, wallet):
        self.wallet = wallet
        self.position = Position()
        self.fees = ZERO
        self.funding = ZERO
        self.liquidations = 0
        self.exit_pending = ''
        self.entry_pending = None

    def equity(self, mark):
        return (self.wallet + self.position.pnl(mark)) * mark

    def fill(self, delta, price, rules, tp=ZERO, sl=ZERO):
        p = self.position
        if not delta:
            return
        if delta * p.quantity < 0:
            if abs(delta) > abs(p.quantity):
                raise Blocked('replay must close before reversing')
            self.wallet += (-delta) * (1 / p.entry - 1 / price)
            q, entry = p.quantity + delta, p.entry
        else:
            q = p.quantity + delta
            entry = q / (p.quantity / p.entry + delta / price) if p.quantity else price
        fee = abs(delta) * rules.taker_fee / price
        self.wallet -= fee
        self.fees += fee
        if not q:
            self.position, self.exit_pending = Position(), ''
            return
        if delta * p.quantity < 0:
            margin = p.margin_btc * abs(q / p.quantity)
            tp, sl = p.take_profit, p.stop_loss
        else:
            margin = p.margin_btc + abs(delta) / price / 20
        liq = liquidation_price(q, entry, margin, rules.maintenance_rate, rules.taker_fee)
        self.position = Position(q, entry, margin, liq, tp, sl)

    def pay_funding(self, rate, mark, rules):
        cost = self.position.quantity / mark * rate
        self.wallet -= cost
        self.funding += cost
        p = self.position
        # Funding first consumes available BTC; a shortfall reduces isolated
        # collateral, never invents a free top-up from outside the account.
        if p.quantity and self.wallet < p.margin_btc:
            margin = max(D('0.00000001'), self.wallet)
            self.position = replace(p, margin_btc=margin, liquidation=liquidation_price(
                p.quantity, p.entry, margin, rules.maintenance_rate, rules.taker_fee))


class Equity:
    def __init__(self, initial, start, writer):
        self.peak = initial
        self.peak_time = start
        self.mdd = ZERO
        self.drawdown_start = start
        self.drawdown_end = start
        self.writer = writer
        self.last = initial
        self.year_initial = initial
        self.year = iso(start)[:4]
        self.year_low = initial
        self.year_peak = initial
        self.year_mdd = ZERO
        self.years = []

    def observe(self, time, event, usd, btc, fx):
        if usd > self.peak:
            self.peak, self.peak_time = usd, time
        dd = max(ZERO, 1 - usd / self.peak)
        if dd > self.mdd:
            self.mdd = dd
            self.drawdown_start, self.drawdown_end = self.peak_time, time
        year = iso(time - 1 if event == 'close' else time)[:4]
        if year != self.year:
            self.close_year()
            self.year, self.year_initial = year, self.last
            self.year_peak, self.year_mdd = self.last, ZERO
        self.year_peak = max(self.year_peak, usd)
        self.year_mdd = max(self.year_mdd, 1 - usd / self.year_peak)
        self.last = usd
        self.writer.writerow([time, iso(time), event, str(btc), str(usd), str(usd * fx), str(dd)])

    def close_year(self):
        self.years.append({'year': self.year, 'return': str(self.last / self.year_initial - 1),
                           'mdd': str(self.year_mdd), 'ending_usd': str(self.last)})


def aggregate(chunk):
    return Bar(chunk[0].time, chunk[0].open, max(b.high for b in chunk),
               min(b.low for b in chunk), chunk[-1].close, sum((b.volume for b in chunk), ZERO))


def hosted_exit_price(position, trigger_price, trade_open, slip, *, adverse_gap):
    """Conservative market-exit estimate without borrowing a later bar extreme.

    Stop/liquidation exits honor an adverse gap already visible at the bar open.
    Take-profit exits receive no favorable gap improvement. High/low remain
    available separately for trigger detection and complete-account MDD.
    """
    if not position.quantity or min(trigger_price, trade_open) <= 0:
        raise Blocked('invalid hosted exit pricing inputs')
    if position.quantity > 0:
        reference = min(trigger_price, trade_open) if adverse_gap else trigger_price
        return reference * (1 - slip)
    reference = max(trigger_price, trade_open) if adverse_gap else trigger_price
    return reference * (1 + slip)


LIQUIDATION_REASON = 'liquidation takeover at bankruptcy price'
STOP_REASON = 'hosted_stop'
TAKE_REASON = 'hosted_take_profit'


def _pending_exit_terms(position, reason):
    """Recover a previously triggered native exit without losing its price.

    A full-position TP/SL is a market exit once triggered. If the conservative
    replay cannot fill it fully in one base bar, later bars must keep the same
    protector identity while allowing newly known adverse gaps. Liquidation is
    an exchange takeover, not a user market order.
    """
    if not position.quantity:
        raise Blocked('pending native exit requires an open position')
    if reason == LIQUIDATION_REASON:
        return ZERO, False, True
    if reason == STOP_REASON:
        return position.stop_loss, True, False
    if reason == TAKE_REASON:
        return position.take_profit, True, False
    raise Blocked('unknown pending native exit state')


def _open_exit_terms(position, mark_open):
    """Return an already-crossed native exit at the known bar open.

    Known open information wins before the manual invocation and before later
    high/low extrema. This prevents a later intrabar low/high from rewriting a
    stop that was already executable at the open into a liquidation.
    """
    if not position.quantity:
        return None
    if min(position.liquidation, position.stop_loss, position.take_profit, mark_open) <= 0:
        raise Blocked('open position lacks valid native protection geometry')
    long = position.quantity > 0
    if (long and mark_open <= position.liquidation) or (not long and mark_open >= position.liquidation):
        return LIQUIDATION_REASON, ZERO, False, True
    if (long and mark_open <= position.stop_loss) or (not long and mark_open >= position.stop_loss):
        return STOP_REASON, position.stop_loss, True, False
    if (long and mark_open >= position.take_profit) or (not long and mark_open <= position.take_profit):
        return TAKE_REASON, position.take_profit, False, False
    return None


def liquidation_takeover(account, rules):
    """Fully transfer the isolated position at bankruptcy, independent of book capacity."""
    p = account.position
    if not p.quantity:
        raise Blocked('liquidation takeover requires an open position')
    price = bankruptcy_price(p.quantity, p.entry, p.margin_btc, rules.taker_fee)
    delta = -p.quantity
    fee_before = account.fees
    account.fill(delta, price, rules)
    if account.position.quantity:
        raise Blocked('liquidation takeover must close the full isolated position')
    return delta, price, account.fees - fee_before


def activate_entry(account, mark, trade, rules, capacity, spread, slip, *, at_open=False):
    """Return (target, execution_price, reason) without any signal evaluation.

    The limit must cover the adverse traded extreme in an unresolved base bar.
    Base-bar volume is only a disclosed liquidity proxy; it is not FOK book proof.
    At trigger, the parent is consumed whether it fills or is cancelled.
    """
    target = account.entry_pending
    if target is None:
        return None
    long = target.quantity > 0
    trigger_mark = mark.open if at_open else mark.high if long else mark.low
    hit = trigger_mark >= target.trigger_price if long else trigger_mark <= target.trigger_price
    if not hit:
        return None
    account.entry_pending = None
    if account.position.quantity:
        raise Blocked('pending parent cannot coexist with an existing replay position')
    # At the bar open, an already-crossed parent can execute from the known
    # traded open. For an intrabar crossing, do not use a later high/low as if
    # it were the trigger-time quote: price from the trigger plus frozen costs.
    quote = trade.open if at_open else target.trigger_price
    price = quote * (1 + spread / 2 + slip if long else 1 - spread / 2 - slip)
    q = abs(target.quantity)
    affordable = account.wallet >= q / price * (D('.05') + 2 * rules.taker_fee)
    cap = min(capacity, rules.maximum, rules.risk_limit_usd)
    within_limit = price <= target.entry if long else price >= target.entry
    protective = target.stop_loss < mark.open < target.take_profit if long else target.take_profit < mark.open < target.stop_loss
    # Before an intrabar crossing the open can be below the entry stop; do
    # not use that path favorably. Its account excursion is still marked below.
    if not at_open:
        protective = target.stop_loss < target.trigger_price < target.take_profit if long else target.take_profit < target.trigger_price < target.stop_loss
    if q > cap or not affordable or not within_limit or not protective:
        return target, None, 'FOK cancelled: liquidity/margin/price or protection precondition'
    return target, price, 'previously hosted conditional FOK; full fill only'


def _replay(dataset, cfg, frozen, directory, *, stress=False, notional_limit=None):
    step = dataset.interval
    # The activity basis is frozen independently of the bar interval. Hourly
    # price bars preserve extrema but must not multiply executable capacity by
    # aggregating an hour of volume into a one-minute liquidity assumption.
    liquidity_basis = int(frozen['liquidity_activity_basis_ms'])
    if liquidity_basis <= 0 or step % liquidity_basis:
        raise Blocked('frozen liquidity activity basis is incompatible with replay interval')
    liquidity_scale = D(liquidity_basis) / D(step)
    initial = D(frozen['initial_cny']) / D(frozen['cny_per_usd'])
    fx = D(frozen['cny_per_usd'])
    spread, slip = D(frozen['spread_fraction']), D(frozen['slippage_fraction'])
    participation, depth_fraction = D(frozen['volume_participation']), D(frozen['book_proxy_fraction'])
    account, statistics = None, None
    history, chunk = deque(maxlen=501), []
    triggers = set(invocations(frozen, stress=stress))
    actual_triggers, decisions, fills_count, margin_index = [], 0, 0, 0
    previous_volume_per_minute, last_funding = ZERO, ZERO
    chunk_duration = 0
    expected_tick = dataset.warmup_start
    final_mark = None
    observed_start = False
    with gzip.open(directory / 'equity.csv.gz', 'wt', encoding='utf-8', newline='') as eqfile, \
         gzip.open(directory / 'orders.csv.gz', 'wt', encoding='utf-8', newline='') as orderfile:
        equity_writer, orders = csv.writer(eqfile), csv.writer(orderfile)
        equity_writer.writerow(['time', 'utc', 'event', 'equity_btc', 'equity_usd', 'equity_cny', 'drawdown'])
        orders.writerow(['time', 'utc', 'event', 'delta_usd_contracts', 'price', 'fee_btc', 'quantity_after', 'tp', 'sl', 'reason'])
        for tick in dataset.ticks():
            bar, mark, t = tick.trade, tick.mark, tick.trade.time
            step = dataset.interval if tick.interval_ms is None else tick.interval_ms
            if type(step) is not int or step not in (MINUTE, dataset.interval) or t != expected_tick or t % step or mark.time != t:
                raise Blocked('invalid refined execution interval or continuity')
            expected_tick = t + step
            liquidity_scale = D(liquidity_basis) / D(step)
            while margin_index + 1 < len(dataset.tiers) and dataset.tiers[margin_index + 1]['time'] <= t:
                margin_index += 1
            row = dataset.tiers[margin_index]
            rules = dataset.venue_rules(row, mark.open)
            if t >= dataset.start:
                if account is None:
                    if t != dataset.start:
                        raise Blocked('formal account did not start at the frozen timestamp')
                    statistics = Equity(initial, t, equity_writer)
                    statistics.observe(t, 'initial_capital', initial, initial / mark.open, fx)
                    account = Account(initial / mark.open * (1 - D(frozen['initial_conversion_cost'])))
                    observed_start = True
                if t in dataset.funding:
                    last_funding, funding_mark = dataset.funding[t]
                    account.pay_funding(last_funding, funding_mark, rules)
                p = account.position
                if p.quantity:
                    account.position = replace(p, liquidation=liquidation_price(
                        p.quantity, p.entry, p.margin_btc, rules.maintenance_rate, rules.taker_fee))
                statistics.observe(t, 'open', account.equity(mark.open), account.equity(mark.open) / mark.open, fx)
                capacity = floor_step(bar.volume * liquidity_scale * participation, rules.step)

                def execute(delta, price, kind, reason, tp=ZERO, sl=ZERO):
                    nonlocal capacity, fills_count
                    qty = min(abs(delta), capacity, rules.maximum)
                    qty = floor_step(qty, rules.step)
                    if qty < rules.minimum:
                        return ZERO
                    signed = qty if delta > 0 else -qty
                    fee_before = account.fees
                    account.fill(signed, price, rules, tp, sl)
                    capacity -= qty
                    fills_count += 1
                    orders.writerow([t, iso(t), kind, str(signed), str(price), str(account.fees - fee_before),
                                     str(account.position.quantity), str(account.position.take_profit),
                                     str(account.position.stop_loss), reason])
                    statistics.observe(t, 'after_' + kind, account.equity(mark.open), account.equity(mark.open) / mark.open, fx)
                    return signed

                def activate(*, at_open=False):
                    event = activate_entry(account, mark, bar, rules, capacity, spread, slip, at_open=at_open)
                    if event is None:
                        return
                    parent, price, reason = event
                    if price is None:
                        orders.writerow([t, iso(t), 'native_entry_cancel', '0', str(parent.entry), '0',
                                         str(account.position.quantity), str(parent.take_profit), str(parent.stop_loss), reason])
                    else:
                        filled = execute(parent.quantity, price, 'native_entry', reason,
                                         parent.take_profit, parent.stop_loss)
                        if filled != parent.quantity:
                            raise Blocked('FOK replay unexpectedly produced a partial fill')

                # Existing parent may have triggered before this invocation. Its
                # real fill wins; later sizing sees the resulting account.
                activate(at_open=True)
                # Known open crossings execute before a new manual decision and
                # before later base-bar extrema can alter their causal ordering.
                protection_crossed_at_open = False
                p = account.position
                open_exit = _open_exit_terms(p, mark.open) if p.quantity else None
                if open_exit:
                    reason, exit_reference, adverse_gap, liquidation = open_exit
                    if liquidation:
                        delta, price, fee = liquidation_takeover(account, rules)
                        account.liquidations += 1
                        fills_count += 1
                        orders.writerow([t, iso(t), 'native_exit', str(delta), str(price), str(fee),
                                         str(account.position.quantity), '0', '0', reason])
                        statistics.observe(t, 'after_native_exit', account.equity(mark.open),
                                           account.equity(mark.open) / mark.open, fx)
                    else:
                        execute(-p.quantity, hosted_exit_price(
                            p, exit_reference, bar.open, slip, adverse_gap=adverse_gap),
                            'native_exit', reason)
                    protection_crossed_at_open = True
                if t in triggers:
                    actual_triggers.append(t)
                    if not protection_crossed_at_open and not account.exit_pending:
                        snapshot = Snapshot('historical-dedicated-btc', t, account.wallet,
                                            max(ZERO, account.wallet - account.position.margin_btc),
                                            mark.open, bar.open * (1 - spread / 2), bar.open * (1 + spread / 2),
                                            previous_volume_per_minute * depth_fraction,
                                            previous_volume_per_minute * depth_fraction,
                                            account.position, rules, funding_rate=last_funding)
                        try:
                            target = decide(list(history), snapshot, cfg, notional_limit=notional_limit)
                        except Blocked as exc:
                            raise Blocked(f'causal replay decision blocked at {iso(t)}: {exc}') from exc
                        decisions += 1
                        p = account.position
                        if p.quantity and p.quantity * target.quantity <= 0:
                            price = bar.open * (1 - spread / 2 - slip) if p.quantity > 0 else bar.open * (1 + spread / 2 + slip)
                            execute(-p.quantity, price, 'manual_reduce', target.reason)
                            if account.position.quantity:
                                target = replace(target, quantity=account.position.quantity,
                                                 take_profit=account.position.take_profit, stop_loss=account.position.stop_loss)
                            else:
                                # Same production rule: recompute after actual
                                # close, still at this authorized invocation.
                                refreshed = replace(snapshot, wallet_btc=account.wallet,
                                                    available_btc=account.wallet, position=account.position)
                                snapshot = refreshed
                                target = decide(list(history), snapshot, cfg, notional_limit=notional_limit)
                        if target.trigger_price:
                            validate_target(snapshot, target, notional_limit or rules.maximum, cfg)
                            operation = 'manual_amend_entry' if account.entry_pending else 'manual_place_entry'
                            account.entry_pending = target
                            orders.writerow([t, iso(t), operation, '0', str(target.entry), '0',
                                             str(account.position.quantity), str(target.take_profit), str(target.stop_loss), target.reason])
                        elif account.entry_pending:
                            account.entry_pending = None
                            orders.writerow([t, iso(t), 'manual_cancel_entry', '0', '0', '0',
                                             str(account.position.quantity), '0', '0', target.reason])
                        delta = target.quantity - account.position.quantity
                        if not target.trigger_price and delta and not (account.position.quantity * target.quantity < 0):
                            reduction = account.position.quantity * delta < 0
                            price = bar.open * (1 + spread / 2 + slip) if delta > 0 else bar.open * (1 - spread / 2 - slip)
                            # IOC limit only fills at or better than the submitted
                            # limit. Subsequent slippage does not bypass that cap.
                            acceptable = reduction or (delta > 0 and price <= target.entry) or (delta < 0 and price >= target.entry)
                            if acceptable:
                                if not reduction:
                                    validate_risk_increase(snapshot, target, cfg,
                                                           notional_limit=notional_limit)
                                execute(delta, price, 'manual_reduce' if reduction else 'manual_increase',
                                        target.reason, target.take_profit, target.stop_loss)
                        if account.position.quantity and target.quantity * account.position.quantity > 0:
                            account.position = replace(account.position, take_profit=target.take_profit, stop_loss=target.stop_loss)
                # Between invocations only the already installed native parent
                # and exits can fire; never recompute a target from this bar.
                activate()
                p = account.position
                # Conservative intrabar account-extrema envelope: mark the
                # current complete account at both extremes before considering
                # fills. This deliberately does not erase excursions at SL price.
                candidates = [(account.equity(m), m) for m in (mark.high, mark.low)]
                for usd, price in sorted(candidates, reverse=True):
                    statistics.observe(t, 'intraminute_envelope', usd, usd / price, fx)
                if p.quantity:
                    long = p.quantity > 0
                    liq_hit = mark.low <= p.liquidation if long else mark.high >= p.liquidation
                    stop_hit = mark.low <= p.stop_loss if long else mark.high >= p.stop_loss
                    take_hit = mark.high >= p.take_profit if long else mark.low <= p.take_profit
                    pending_before_bar = bool(account.exit_pending)
                    exit_reference = ZERO
                    adverse_gap = False
                    if pending_before_bar:
                        exit_reference, adverse_gap, _ = _pending_exit_terms(
                            p, account.exit_pending)
                    if liq_hit:
                        # Exchange liquidation takes over the whole isolated
                        # position at bankruptcy; it is not constrained by the
                        # user's market-order participation proxy.
                        reason = LIQUIDATION_REASON
                        delta, price, fee = liquidation_takeover(account, rules)
                        account.liquidations += 1
                        fills_count += 1
                        orders.writerow([t, iso(t), 'native_exit', str(delta), str(price), str(fee),
                                         str(account.position.quantity), '0', '0', reason])
                        statistics.observe(t, 'after_native_exit', account.equity(mark.open),
                                           account.equity(mark.open) / mark.open, fx)
                    else:
                        if stop_hit and not pending_before_bar:
                            account.exit_pending = STOP_REASON
                            exit_reference, adverse_gap = p.stop_loss, True
                        elif take_hit and not pending_before_bar:
                            account.exit_pending = TAKE_REASON
                            exit_reference = p.take_profit
                        if account.exit_pending:
                            # A native full-position market protector can remain
                            # partially filled in this conservative liquidity
                            # model. Preserve its trigger identity across bars.
                            price = hosted_exit_price(
                                p, exit_reference, bar.open, slip,
                                adverse_gap=adverse_gap)
                            reason = account.exit_pending
                            execute(-p.quantity, price, 'native_exit', reason)
                final_mark = mark.close
                statistics.observe(t + step, 'close', account.equity(mark.close), account.equity(mark.close) / mark.close, fx)
                if account.wallet <= 0 or account.equity(mark.close) <= 0:
                    raise Blocked('account insolvent in conservative replay; cannot reset or silently truncate')
            chunk.append(bar)
            chunk_duration += step
            if t + step == (chunk[0].time // INTERVAL_MS + 1) * INTERVAL_MS:
                if chunk_duration != INTERVAL_MS:
                    raise Blocked('incomplete signal aggregation')
                history.append(aggregate(chunk)); chunk = []; chunk_duration = 0
            previous_volume_per_minute = bar.volume * liquidity_scale
        if not observed_start or statistics is None or actual_triggers != sorted(triggers) or expected_tick != dataset.end:
            raise Blocked('incomplete account or invocation coverage')
        statistics.close_year()
    final = account.equity(final_mark)
    years = D(dataset.end - dataset.start) / D('31556952000')
    cagr = float(final / initial) ** (1 / float(years)) - 1
    gaps = [b - a for a, b in zip(actual_triggers, actual_triggers[1:])]
    return dict(initial_equity_usd=initial, final_equity_btc=final / final_mark, final_equity_usd=final,
                final_equity_cny=final * fx, cagr=cagr, mdd=statistics.mdd,
                drawdown_start=iso(statistics.drawdown_start), drawdown_end=iso(statistics.drawdown_end),
                yearly=statistics.years, fees_btc=account.fees, net_funding_paid_btc=account.funding,
                liquidation_events=account.liquidations, fills=fills_count, decisions=decisions,
                invocations=len(actual_triggers), longest_interval_hours=max(gaps, default=0) / 3_600_000,
                longest_tail_without_invocation_hours=(dataset.end - actual_triggers[-1]) / 3_600_000,
                economic_numbers_meet_limits=economic_limits(cagr, statistics.mdd, frozen),
                qualification='NOT_QUALIFIED',
                limitations=['Base-bar extrema are a conservative account-drawdown envelope, not a known tick path.',
                             'Liquidity uses previous-base-bar volume normalized to a one-minute activity proxy; spread/slippage/conversion are frozen modeling assumptions.',
                             'Native FOK/partial-fill/offline-order integration and historical source authenticity remain unverified.'])


def run(manifest, output, config, *, stress=False):
    frozen = spec()
    required = max(config.model.trend_bars, config.model.channel_bars + 1, config.model.atr_bars + 1)
    dataset = Dataset(manifest, frozen, warmup_bars=required)
    directory = Path(output).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    if any(directory.iterdir()):
        raise Blocked('evidence output must be empty; refusing to overwrite original results')
    identity = dict(source_sha256=source_identity(), config=serial(config),
                    dataset_manifest_sha256=digest(manifest), dataset=dataset.manifest,
                    research_spec=frozen, research_spec_sha256=digest(Path(__file__).resolve().parent / 'spec.json'),
                    stress=stress)
    (directory / 'identity.json').write_text(json.dumps(identity, indent=2) + '\n')
    with open(directory / 'invocations.csv', 'w', newline='') as stream:
        writer = csv.writer(stream); writer.writerow(['time', 'utc'])
        writer.writerows((t, iso(t)) for t in invocations(frozen, stress=stress))
    try:
        result = _replay(dataset, config.model, frozen, directory, stress=stress,
                         notional_limit=config.max_position_usd if config.max_position_usd > 0 else None)
    except (Blocked, OSError, ValueError, KeyError, ArithmeticError) as exc:
        result = {'status': 'failed', 'qualification': 'NOT_QUALIFIED', 'reason': str(exc)}
        (directory / 'result.json').write_text(json.dumps(serial(result), indent=2) + '\n')
        raise
    result.update(status='measured', provenance=dataset.manifest['provenance'],
                  output_files={p.name: dict(bytes=p.stat().st_size, sha256=digest(p)) for p in directory.iterdir() if p.is_file()})
    (directory / 'result.json').write_text(json.dumps(serial(result), indent=2) + '\n')
    return serial(result)
