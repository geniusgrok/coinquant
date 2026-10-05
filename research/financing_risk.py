"""Causal isolated-financing proposals; no adapter, orders or authentication.

The caller persists ``next_state`` before any separately authorized action.
Hash bindings and provenance labels constrain research inputs; they do not
authenticate a native account or prove a margin-release bound. Historical
SessionExchange brackets are synthetic and cannot qualify this candidate.
"""
from copy import deepcopy
from decimal import Decimal as D

from research.replacement_routes import number

RULE = 'isolated-financing-buffer-v1'
EIGHT_HOURS = 8 * 3600000
SHOCK = D('.10')


def _observation(row, now, age, origin):
    if (row['origin'] != origin or row['symbol'] != 'BTCUSDT'
            or type(row['observed_ms']) is not int
            or type(row['available_ms']) is not int
            or not 0 <= row['observed_ms'] <= row['available_ms'] <= now
            or now-row['observed_ms'] > age):
        raise ValueError('missing causal native-origin observation')
    hashes = row['source_sha256']
    if (not isinstance(hashes, list) or not hashes
            or any(not isinstance(s, str) or len(s) != 64
                   or any(c not in '0123456789abcdef' for c in s) for s in hashes)):
        raise ValueError('raw receipt bindings required')


def _maintenance(brackets, notional):
    previous, previous_rate, previous_cum = D(0), D(0), D(0)
    answer = None
    for tier in brackets['tiers']:
        floor = number(tier['notionalFloor'], nonnegative=True)
        cap = number(tier['notionalCap'], positive=True)
        rate = number(tier['maintMarginRatio'], nonnegative=True)
        deduction = number(tier['cum'], nonnegative=True)
        if (floor != previous or cap <= floor or not previous_rate <= rate < D('.05')
                or deduction > floor*rate
                or floor and deduction != previous_cum+floor*(rate-previous_rate)
                or not floor and deduction):
            raise ValueError('incomplete or inconsistent dated maintenance tiers')
        if floor <= notional < cap:
            answer = max(D(0), notional*rate-deduction)
        previous, previous_rate, previous_cum = cap, rate, deduction
    if answer is None:
        raise ValueError('position outside verified maintenance tiers')
    return answer


def _saved(state, account, now):
    if state is None:
        return None
    state = deepcopy(state)
    if (state['rule'] != RULE or state['account_uid'] != account['account_uid']
            or state['campaign'] != account['owned_campaign']
            or type(state['triggered_ms']) is not int
            or type(state['last_observed_ms']) is not int
            or not 0 <= state['triggered_ms'] <= state['last_observed_ms'] <= now
            or type(state['direction']) is not int or state['direction'] not in (-1, 1)):
        raise ValueError('persistent cap ownership/clock mismatch')
    number(state['cap_btc'], nonnegative=True)
    return state


def evaluate(packet, state=None, *, expression='half'):
    """Return a bounded proposal and an external same-campaign checkpoint.

    ``half`` needs a separately justified native margin-release lower bound
    that actually covers the remaining stressed position. A pro-rata margin
    release does not improve the liquidation buffer ratio and is not enough.
    ``flat`` has no hypothetical remaining collateral. Both remain proposals.
    Missing/invalid inputs preserve any cap and block added exposure.
    """
    out = dict(status='BLOCK_FINANCING_INPUT', orders=0, account_entrants=0,
               qualification='RESEARCH_ONLY', native_authenticated=False,
               next_state=deepcopy(state), proposed_reduction_btc='0',
               new_exposure_cap_btc=None, capped_target_btc='0',
               new_risk_blocked=True, tail_safety_proven=False,
               meaning='Caller-supplied receipt bindings are not authenticated funds or economic evidence.')
    try:
        now = packet['decision_ms']
        if type(now) is not int or now < 0 or expression not in ('half', 'flat'):
            raise ValueError('explicit decision clock and fixed expression required')
        account = packet['account']
        _observation(account, now, 60000, 'native-account-observation')
        uid = account['account_uid']
        if (not isinstance(uid, str) or not uid.isascii() or not uid.isdigit()
                or int(uid) <= 0 or uid != packet['expected_account_uid']
                or not isinstance(account['owned_campaign'], str) or not account['owned_campaign']
                or account['owned'] is not True
                or account['one_way'] is not True or account['isolated'] is not True
                or account['auto_add_margin_off'] is not True
                or account['exchange_leverage'] != 20 or account['pending'] is not False):
            raise ValueError('unknown ownership, isolated configuration or pending intents')
        quantity = number(account['quantity_btc'])
        if number(account['owned_quantity_btc']) != quantity:
            raise ValueError('signed position is not wholly owned by this campaign')
        saved = _saved(state, account, now)
        if not quantity:
            if saved is not None:
                flat = account['flat_confirmed_ms']
                if type(flat) is not int or not saved['last_observed_ms'] <= flat <= account['observed_ms']:
                    raise ValueError('fresh owned flat confirmation required to release cap')
            out.update(status='CONFIRMED_FLAT', next_state=None)
            return out
        direction = 1 if quantity > 0 else -1
        if saved is not None and saved['direction'] != direction:
            raise ValueError('position direction changed without confirmed flat')
        if account['protected'] is not True or account['stop_before_liquidation'] is not True:
            raise ValueError('known owned full-position protection required')
        reducible = number(account['confirmed_reducible_btc'], nonnegative=True)
        if reducible > abs(quantity):
            raise ValueError('reducible quantity exceeds actual owned position')
        mark = packet['mark']
        _observation(mark, now, 15000, 'native-mark-observation')
        price = number(mark['mark_price'], positive=True)
        entry = number(account['entry_price'], positive=True)
        pnl = quantity*(price-entry)
        if abs(number(account['unrealized_usdt'])-pnl) > D('.00000001'):
            raise ValueError('mark and actual position PnL disagree')
        isolated = number(account['isolated_wallet_usdt'], nonnegative=True)
        liq = number(account['native_liquidation_price'], nonnegative=True)
        stop = number(account['stop_price'], positive=True)
        if not (liq < stop < price if direction > 0 else price < stop < liq):
            raise ValueError('owned stop/mark/native liquidation geometry is unsafe')
        brackets = packet['brackets']
        _observation(brackets, now, 86400000, 'native-dated-maintenance-brackets')
        if (type(brackets['effective_from_ms']) is not int
                or type(brackets['effective_until_ms']) is not int
                or not brackets['effective_from_ms'] <= now < brackets['effective_until_ms']
                or number(brackets.get('notionalCoef', '1')) != 1):
            raise ValueError('current or synthetic brackets cannot substitute for dated native evidence')
        commission = packet['commission']
        _observation(commission, now, 60000, 'native-account-commission')
        fee = number(commission['taker_fee'], nonnegative=True)
        if fee >= D('.05'):
            raise ValueError('unsupported account commission')
        funding = packet['funding']
        _observation(funding, now, EIGHT_HOURS, 'native-settled-funding')
        rows = funding['settlements']
        last = now//EIGHT_HOURS*EIGHT_HOURS
        if (len(rows) != 3 or [r['time_ms'] for r in rows] !=
                [last-2*EIGHT_HOURS, last-EIGHT_HOURS, last]
                or any(type(r['time_ms']) is not int or r['time_ms'] < 0
                       or r['time_ms'] > funding['observed_ms'] for r in rows)):
            raise ValueError('last three consecutive already-settled receipts required')
        rates = [number(r['rate']) for r in rows]
        if any(abs(r) >= 1 for r in rates):
            raise ValueError('invalid settled funding rate')
        payer = max(D(0), *(direction*r for r in rates))
        stress_price = price*(1-direction*SHOCK)
        notional = abs(quantity)*price
        reserve = 3*notional*payer
        maintenance = _maintenance(brackets, abs(quantity)*stress_price)
        surplus = isolated+quantity*(stress_price-entry)-maintenance-reserve-abs(quantity)*stress_price*fee
        out['diagnostics'] = dict(isolated_equity_usdt=str(isolated+pnl),
            current_maintenance_usdt=str(_maintenance(brackets, notional)),
            stressed_mark=str(stress_price), stressed_maintenance_usdt=str(maintenance),
            funding_stress_reserve_usdt=str(reserve), stress_surplus_usdt=str(surplus),
            funding_means='Three settlements at worst past-three payer rate: scenario, not forecast.',
            pro_rata_reduction_means='Lower dollar exposure; no improvement of liquidation buffer ratio.')
        if saved is None and surplus < 0:
            saved = dict(rule=RULE, account_uid=uid, campaign=account['owned_campaign'],
                direction=direction, cap_btc=str(abs(quantity)*(D('.5') if expression == 'half' else 0)),
                expression=expression, triggered_ms=now, last_observed_ms=now)
        if saved is not None:
            if saved['expression'] != expression:
                raise ValueError('cannot change expression in a persistent campaign')
            saved['last_observed_ms'] = now
        cap = number(saved['cap_btc'], nonnegative=True) if saved else abs(quantity)
        target = number(packet['target_btc'], nonnegative=True)
        reduction = max(D(0), abs(quantity)-cap)
        out.update(next_state=saved, new_exposure_cap_btc=str(cap) if saved else None,
                   capped_target_btc=str(min(target, cap)) if saved else str(target),
                   new_risk_blocked=saved is not None,
                   status='CAP_ACTIVE' if saved else 'NO_FINANCING_BREACH')
        if not reduction:
            return out
        if reduction > reducible:
            out['status'] = 'BLOCK_REDUCTION_CAPACITY'
            return out
        if expression == 'half':
            preview = packet.get('reduction_preview')
            if preview is None:
                out['status'] = 'WAIT_REDUCTION_PREVIEW'
                return out
            _observation(preview, now, 15000, 'verified-native-margin-release-bound')
            if (preview['account_uid'] != uid or preview['campaign'] != account['owned_campaign']
                    or number(preview['remaining_btc'], nonnegative=True) != cap):
                raise ValueError('margin-release bound does not match owned reduction')
            remaining_margin = number(preview['remaining_isolated_wallet_lower_usdt'], nonnegative=True)
            # Native-rule lower bound AFTER settled reduction fees/realised PnL;
            # never assume realised cash stays isolated or remaining entry resets.
            remaining = direction*cap
            after = (remaining_margin+remaining*(stress_price-entry)
                -_maintenance(brackets, cap*stress_price)-3*cap*price*payer-cap*stress_price*fee)
            out['diagnostics']['remaining_stress_surplus_lower_usdt'] = str(after)
            if after < 0:
                out['status'] = 'NO_SUPPORTED_MARGIN_BUFFER_IMPROVEMENT'
                return out
        out.update(status='RESEARCH_OWNED_REDUCTION', proposed_reduction_btc=str(reduction),
                   reduce_only=True, side='SELL' if direction > 0 else 'BUY',
                   execution='Persist cap, use original authorized Lifecycle; reconcile fill/margin/protection before any next action.')
    except (KeyError, ValueError, TypeError, ArithmeticError) as exc:
        out.update(status='BLOCK_FINANCING_INPUT', reason=str(exc),
                   proposed_reduction_btc='0', capped_target_btc='0', new_risk_blocked=True)
    return out
