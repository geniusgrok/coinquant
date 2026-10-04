"""Frozen BTC information expressions and causal joint new-risk decisions.

Research only. Accounts remain separately funded; no orders or transfers here.
"""
from decimal import Decimal as D
from pathlib import Path
import hashlib
import json
import math

DAY = 86400000
SPEC = Path(__file__).with_name('nine-spec.json')
FAMILIES = ('etf-demand', 'oi-deleveraging', 'option-insurance',
            'old-coin-supply', 'dollar-financing')
RULES = ('gross-entry-cap', 'stress-entry-cap', 'state-exposure', 'risk-capacity')


def number(value, *, nonnegative=False):
    if isinstance(value, bool):
        raise ValueError('boolean is not a financial amount')
    result = D(str(value))
    if not result.is_finite() or (nonnegative and result < 0):
        raise ValueError('invalid financial amount')
    return result


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def serial(value):
    if isinstance(value, D):
        return str(value)
    if isinstance(value, dict):
        return {str(k): serial(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [serial(v) for v in value]
    return value


def context_at(context, now):
    """Only completed daily observations, actually available before the call."""
    if (not context or type(context.get('completed_through_ms')) is not int
            or context['completed_through_ms'] % DAY
            or not 0 <= now-context['completed_through_ms'] < 2*DAY
            or type(context.get('available_ms')) is not int
            or not context['completed_through_ms'] <= context['available_ms'] <= now
            or not isinstance(context.get('source_sha256'), str)
            or len(context['source_sha256']) != 64
            or any(c not in '0123456789abcdef' for c in context['source_sha256'])):
        raise ValueError('fresh causal completed market context required')
    returns = list(map(number, context['returns20']))
    if len(returns) != 20:
        raise ValueError('twenty completed returns required')
    return returns


def admission(accounts, proposal, now, rule, context=None, competitor=None):
    """Includes real still-committed entry capacity, not just filled exposure."""
    if rule not in RULES:
        raise ValueError('unregistered joint rule')
    try:
        if type(now) is not int or len(accounts) != 2 or {a['kind'] for a in accounts} != {'spot', 'coin'}:
            raise ValueError('two separate BTC accounts required')
        equity = gross = risk = D(0)
        for account in accounts:
            if (account['symbol'] != 'BTCUSDT' or type(account['receipt_ms']) is not int
                    or not 0 <= now-account['receipt_ms'] <= 60000
                    or account['owned'] is not True or account['protected'] is not True
                    or account['pending'] is not False):
                raise ValueError('unknown/stale ownership, protection or pending state')
            e = number(account['equity_usdt'])
            if e <= 0:
                raise ValueError('nonpositive independent equity')
            equity += e
            gross += number(account['gross_notional_usdt'], nonnegative=True)
            gross += number(account.get('reserved_notional_usdt', '0'), nonnegative=True)
            risk += number(account['stop_risk_usdt'], nonnegative=True)
            risk += number(account.get('reserved_stop_risk_usdt', '0'), nonnegative=True)
        kind = proposal['kind']
        if (kind not in ('spot', 'coin') or proposal['symbol'] != 'BTCUSDT'
                or proposal['side'] != 'BUY' or type(proposal['at_ms']) is not int
                or not 0 <= now-proposal['at_ms'] <= 15000):
            raise ValueError('known fresh new BUY proposal required')
        amount = number(proposal['gross_notional_usdt'], nonnegative=True)
        extra = number(proposal['stop_risk_usdt'], nonnegative=True)
        cap = D(4)
        returns = None
        if rule in ('stress-entry-cap', 'state-exposure'):
            returns = context_at(context, now)
        if rule == 'state-exposure':
            for a in accounts:
                if type(a['momentum_available_ms']) is not int or a['momentum_available_ms'] > now:
                    raise ValueError('future account direction')
                number(a['momentum20'])
            if all(number(a['momentum20']) < 0 for a in accounts):cap=D(2)
        admitted = gross+amount <= cap*equity
        reason = 'gross-cap'
        competition = False
        if rule == 'stress-entry-cap':
            shock = max(D(0), -min(returns))
            admitted &= shock*(gross+amount)+risk+extra <= D('.20')*equity
            reason = 'gross-and-confirmed-stress'
        if rule == 'risk-capacity' and competitor is not None:
            if (competitor['kind'] == kind or competitor['symbol'] != 'BTCUSDT'
                    or competitor['side'] != 'BUY' or type(competitor['at_ms']) is not int
                    or not 0 <= now-competitor['at_ms'] <= 15000
                    or competitor.get('feasible') is not True):
                raise ValueError('competitor is not a fresh independent feasible preflight')
            other = number(competitor['gross_notional_usdt'], nonnegative=True)
            other_risk = number(competitor['stop_risk_usdt'], nonnegative=True)
            competition = amount > 0 and other > 0 and gross+amount+other > cap*equity
            if competition:
                # No outcome-trained ranking, held eviction or account cash movement.
                cost = (extra/amount, kind != 'spot')
                other_cost = (other_risk/other, competitor['kind'] != 'spot')
                admitted &= cost <= other_cost
                reason = 'lower-confirmed-risk-cost-first'
        return serial(dict(status='ADMIT_RESEARCH_PROPOSAL' if admitted else 'BLOCK_NEW_RISK',
                           rule=rule, gross_over_equity=(gross+amount)/equity,
                           competition=competition, reason=reason, orders=0, transfers=0))
    except (KeyError, TypeError, ValueError, ArithmeticError) as error:
        return dict(status='BLOCK_UNKNOWN', rule=rule, reason=str(error), orders=0, transfers=0)


def alpha_expression(family, expression, feature, proposal, *, owned=False, context=None):
    """Concrete new-order expression. Never expands an incumbent budget."""
    if family not in FAMILIES or expression not in (0, 1):
        raise ValueError('unregistered information expression')
    if proposal.get('symbol') != 'BTCUSDT' or proposal.get('side') != 'BUY':
        raise ValueError('only genuine BTC new BUY is eligible')
    if feature.get('status') != 'FEATURE_READY':
        return dict(status='WAIT_QUALIFIED_DATA', factor=None, action=None)
    weak, release = feature.get('weak'), feature.get('release')
    if type(weak) is not bool or type(release) is not bool:
        raise ValueError('known frozen feature predicates required')
    if family == 'oi-deleveraging' and expression == 0:
        return dict(status='PROPOSE_NEW_PRIMARY_RESEARCH' if release and not owned else 'NO_ACTION',
                    factor='1', action='new-primary' if release and not owned else None)
    if expression == 1 and family in ('option-insurance', 'dollar-financing'):
        factor = D(1) if release else D(0)
    elif expression == 0 or family == 'oi-deleveraging':
        factor = D('.75') if weak else D(1)
    else:
        factor = D(0) if weak else D(1)
    return dict(status='CHANGE_NEW_BUDGET' if factor != 1 else 'NO_ACTION',
                factor=str(factor), action='new-budget', held_changed=False)


def failure_route(status, *, information_valid=None, expressions_used=0):
    if status in ('WAIT_QUALIFIED_DATA', 'WAIT_NEW_INTERVAL', 'SOURCE_UNAVAILABLE'):
        return 'WAIT_NEW_EVIDENCE_AND_ADVANCE_NEXT_FAMILY'
    if status in ('NO_ACTION', 'SUPPORT_PENDING'):
        return 'FREEZE_SUPPORT_PENDING_AND_ADVANCE_NEXT_MECHANISM'
    if status == 'REJECT_INFORMATION' or information_valid is False:
        return 'CLOSE_FAMILY_ADVANCE_NEXT_SOURCE'
    if status == 'REJECT_COST' and expressions_used < 2:
        return 'TRY_ONE_REGISTERED_DISTINCT_EXPRESSION'
    if status == 'ONLY_LOWER_EXPOSURE':
        return 'COMPARE_SIMPLE_CONTROL_CLASSIFY_BETA'
    return 'ADVANCE_NEXT_MECHANISM'


def portfolio_metrics(curve, btc_closes):
    """Descriptive actual daily wallet metrics, never curve-scaled or CAGR."""
    pairs = []
    days = sorted(curve)
    for a, b in zip(days, days[1:]):
        if b-a != DAY or a not in btc_closes or b not in btc_closes:
            continue
        wealth_a, wealth_b = number(curve[a]['equity_usdt']), number(curve[b]['equity_usdt'])
        if wealth_a <= 0:
            raise ValueError('nonpositive wallet curve')
        pairs.append((float(number(btc_closes[b])/number(btc_closes[a])-1),
                      float(wealth_b/wealth_a-1)))
    if len(pairs) < 3:
        return dict(status='INSUFFICIENT_DAILY_SUPPORT', days=len(pairs), beta=None,
                    upside_capture=None, downside_capture=None, prospective_alpha_proven=False)
    x, y = zip(*pairs)
    mx, my = sum(x)/len(x), sum(y)/len(y)
    variance = sum((v-mx)**2 for v in x)
    def capture(sign):
        rows = [(a,b) for a,b in pairs if (a > 0 if sign > 0 else a < 0)]
        denom = sum(a for a,b in rows)
        return sum(b for a,b in rows)/denom if denom else None
    return dict(status='DESCRIPTIVE', days=len(pairs),
                beta=sum((a-mx)*(b-my) for a,b in pairs)/variance if variance else None,
                upside_capture=capture(1), downside_capture=capture(-1),
                daily_volatility=math.sqrt(sum((v-my)**2 for v in y)/(len(y)-1)*365.25),
                prospective_alpha_proven=False)


def pair_gate(candidate, baseline, uniform):
    """A finite window can admit further measurement, never promote a default."""
    c, b, u = (number(r['final_cny']) for r in (candidate, baseline, uniform))
    cm, bm, um = (number(r['synchronized_observed_mdd']) for r in (candidate, baseline, uniform))
    risk_wealth = (c >= b and cm <= bm+D('.01')) or (cm <= bm*D('.8') and c >= b*D('.95'))
    return dict(audits=all(r['finished'] for r in (candidate,baseline,uniform)),
                actual_action=candidate['changed_commitments'] > 0,
                risk_wealth=risk_wealth,
                beats_simple=c >= u and cm <= um+D('.01') and (c > u or cm < um),
                meaning='Finite research pair. Observed synchronized MDD is not continuous/native joint MDD.')
