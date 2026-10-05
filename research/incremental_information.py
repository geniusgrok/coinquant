"""Fixed incremental BTC information screen and finite research proposals.

No requests, fitted trading model, account state, orders or default promotion.
Historical prices/features retain modeled availability and development status.
Cross-venue input is source-bound normalized research, not authenticated funds.
"""
from bisect import bisect_right
from decimal import Decimal as D
import hashlib
import json
import math

from research.continuous_routes import solve
from research.edge_features import DAY, FUNDING_LAG, BASIS_LAG
from research.tradeoff_routes import cross_demand

RULE = 'btc-incremental-information-20261005-v1'
EXPRESSIONS = ('release-new-primary', 'release-full-otherwise-half')
CONTROLS = ('momentum5', 'momentum20', 'rms20', 'funding_level', 'basis_level')


def serial(value):
    if isinstance(value, D):
        return str(value)
    if isinstance(value, dict):
        return {str(k): serial(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [serial(v) for v in value]
    return value


def digest(value):
    return hashlib.sha256(json.dumps(serial(value), sort_keys=True).encode()).hexdigest()


class ReleaseBook:
    """Three already-settled days against preceding three, no threshold grid."""
    def __init__(self, bars, features):
        bars = list(bars)
        if any(type(row[0]) is not int for row in bars):
            raise ValueError('integer daily bar times required')
        self.bars = {t: tuple(D(str(v)) for v in row) for t, *row in bars}
        if len(self.bars) != len(bars):
            raise ValueError('duplicate daily bar')
        if any(t % DAY or len(row) != 4 or any(not v.is_finite() or v <= 0 for v in row)
               or not row[2] <= min(row[0], row[3]) <= max(row[0], row[3]) <= row[1]
               for t, row in self.bars.items()):
            raise ValueError('completed positive daily OHLC required')
        self.features = features
        self.funding = {row[0]//FUNDING_LAG: row for row in features.records['funding']}
        if len(self.funding) != len(features.records['funding']):
            raise ValueError('duplicate funding settlement slot')
        self.basis = {row[0]: row for row in features.records['basis']}
        self.input_sha256 = digest(dict(bars=self.bars, features=features.sha256))

    def at(self, now):
        if type(now) is not int or now < 0:
            raise ValueError('integer decision milliseconds required')
        funding = self.features.value('funding', now)
        funding_receipt = dict(self.features.last_lookup)
        basis = self.features.value('basis', now)
        basis_receipt = dict(self.features.last_lookup)
        if funding is None or basis is None:
            return dict(status='PENDING', reason='qualified_current_funding_or_basis_missing',
                        funding=funding_receipt, basis=basis_receipt)
        slot = funding_receipt['observation_ms']//FUNDING_LAG
        settled = [self.funding.get(i) for i in range(slot-17, slot+1)]
        end = basis_receipt['observation_ms']
        basis_rows = [self.basis.get(end-i*DAY) for i in range(4)]
        if any(row is None or row[2] is None or row[3] is not None or row[1] > now
               for row in settled+basis_rows):
            return dict(status='PENDING', reason='six_settled_funding_days_or_completed_basis_missing')
        day = (now-BASIS_LAG)//DAY*DAY-DAY
        keys = list(range(day-20*DAY, day+DAY, DAY))
        if not all(t in self.bars for t in keys):
            return dict(status='PENDING', reason='completed_price_controls_missing')
        closes = [self.bars[t][3] for t in keys]
        returns = [b/a-1 for a, b in zip(closes, closes[1:])]
        recent = sum((row[2] for row in settled[9:]), D(0))/9
        previous = sum((row[2] for row in settled[:9]), D(0))/9
        funding_change, basis_change = recent-previous, basis_rows[0][2]-basis_rows[3][2]
        release = previous > 0 and basis_rows[3][2] > 0 and funding_change < 0 and basis_change < 0
        return dict(status='FEATURE_READY', day_ms=day, available_ms=now,
                    release=release, funding_change=funding_change, basis_change=basis_change,
                    funding_level=recent, basis_level=basis,
                    momentum5=closes[-1]/closes[-6]-1, momentum20=closes[-1]/closes[0]-1,
                    rms20=(sum((r*r for r in returns), D(0))/20).sqrt(),
                    input_sha256=self.input_sha256, latest_input_available_ms=max(
                        row[1] for row in settled+basis_rows),
                    availability='Modeled completed bars+60s and actual settlement+8h; not observed historical receipt vintage')

    def label(self, day, kind, stress=False):
        """Delayed open-to-open cash proxy; all 21 funding marks must mature."""
        if kind not in ('coin', 'spot'):
            raise ValueError('BTC coin/spot research kind required')
        entry, exit_ = day+2*DAY, day+9*DAY
        if entry not in self.bars or exit_ not in self.bars:
            return None
        fee = D('.00075') if kind == 'coin' else D('.001')
        slip = D('.0005')
        if stress:
            fee *= 2
            slip *= 2
        opened, closed = self.bars[entry][0]*(1+slip), self.bars[exit_][0]*(1-slip)
        price_gain = closed/opened-1
        costs = fee*(opened+closed)/opened
        funding, available = D(0), exit_+BASIS_LAG
        if kind == 'coin':
            rows = [self.funding.get(i) for i in range(entry//FUNDING_LAG+1, exit_//FUNDING_LAG+1)]
            if any(row is None or row[2] is None or row[3] is not None or row[0]//DAY*DAY not in self.bars
                   for row in rows):
                return None
            funding = sum((row[2]*self.bars[row[0]//DAY*DAY][0]/opened for row in rows), D(0))
            available = max(available, max(row[1] for row in rows))
        return dict(entry_ms=entry+BASIS_LAG, exit_ms=exit_+BASIS_LAG, available_ms=available,
                    gross_return=price_gain, fees=costs, funding=funding,
                    net_return=price_gain-costs-funding)


def fit(rows, controls=CONTROLS):
    """Descriptive OLS with pre-outcome price AND existing level controls."""
    names = ('release', *controls)
    width = len(names)+1
    if len(rows) <= width or len({row['release'] for row in rows}) != 2:
        return dict(identifiable=False, count=len(rows), coefficient=None)
    xs = [[1.0, *[float(row[k]) for k in names]] for row in rows]
    ys = [float(row['net_return']) for row in rows]
    gram = [[sum(x[i]*x[j] for x in xs) for j in range(width)] for i in range(width)]
    rhs = [sum(x[i]*y for x, y in zip(xs, ys)) for i in range(width)]
    try:
        coefficients = solve(gram, rhs)
        influence = solve(gram, [0, 1, *[0]*(width-2)])
    except ValueError:
        return dict(identifiable=False, count=len(rows), coefficient=None)
    residuals = [y-sum(v*c for v, c in zip(x, coefficients)) for x, y in zip(xs, ys)]
    variance = sum((error*sum(v*c for v, c in zip(x, influence)))**2
                   for x, error in zip(xs, residuals))*len(xs)/(len(xs)-width)
    return dict(identifiable=True, count=len(rows), coefficient=coefficients[1],
                hc1_standard_error=math.sqrt(variance), columns=('intercept', *names),
                coefficients=coefficients,
                uncertainty='Descriptive HC1; reused development history/multiple trials, no prospective significance claim')


def assess(rows, eligible, controls=CONTROLS):
    half = len(rows)//2
    halves = [rows[:half], rows[half:]]
    selected = [row for row in rows if row['release']]
    overall, split_fits = fit(rows, controls), [fit(part, controls) for part in halves]
    means = [sum((r['net_return'] for r in part if r['release']), D(0))/
             sum(r['release'] for r in part) if any(r['release'] for r in part) else None for part in halves]
    stress_means = [sum((r['stress_net_return'] for r in part if r['release']), D(0))/
                    sum(r['release'] for r in part) if any(r['release'] for r in part) else None for part in halves]
    gates = dict(coverage=len(rows) >= .9*eligible if eligible else False,
                 events=len(selected) >= 10, each_half=all(sum(r['release'] for r in part) >= 3 for part in halves),
                 identifiable=overall['identifiable'] and all(f['identifiable'] for f in split_fits),
                 overall_increment=overall['identifiable'] and overall['coefficient'] >= .005,
                 both_halves=all(f['identifiable'] and f['coefficient'] > 0 for f in split_fits),
                 net_positive=all(v is not None and v > 0 for v in means),
                 stress_positive=all(v is not None and v > 0 for v in stress_means))
    support = all(gates[k] for k in ('coverage', 'events', 'each_half', 'identifiable'))
    admitted = all(gates.values())
    return dict(status='ELIGIBLE_FINITE_ACCOUNT_PROPOSAL' if admitted else 'NO_SUPPORT' if support else 'PENDING',
                gates=gates, eligible=eligible, matured=len(rows), selected=len(selected), overall=overall,
                half_fits=split_fits, selected_net_means=means, selected_stress_means=stress_means,
                account_entrant=admitted, account_measured=False, default_adopted=False,
                independent_alpha_proven=False, historical_development_only=True)


def proposal(book, assessment, now, expression, *, offline, legal_new_buy=False,
             confirmed_flat=False, protected=False, pending=True, price_priority=True,
             causal_macro=False):
    """Interface for an actual wallet wrapper; never bypass original funds gates."""
    if expression not in EXPRESSIONS or type(now) is not int:
        raise ValueError('registered expression and decision clock required')
    if offline is not True:
        return dict(status='BLOCK_NOT_OFFLINE', orders=0)
    if assessment.get('status') != 'ELIGIBLE_FINITE_ACCOUNT_PROPOSAL':
        return dict(status='NOT_ADMITTED', reason=assessment.get('status'), orders=0)
    feature = book.at(now)
    if feature['status'] != 'FEATURE_READY':
        return dict(status='PENDING', reason=feature['reason'], orders=0)
    if pending is not False or protected is not True:
        return dict(status='BLOCK_ACCOUNT_CONTEXT', orders=0)
    if expression == EXPRESSIONS[0]:
        if not (confirmed_flat is True and price_priority is False and causal_macro is True and feature['release']):
            return dict(status='NO_NEW_OPPORTUNITY', orders=0)
        return dict(status='PROPOSE_NEW_PRIMARY_RESEARCH', gross_equity_cap='1',
                    fresh_only=True, topup=False, source_sha256=book.input_sha256,
                    consumed_identity=digest(dict(rule=RULE, day=feature['day_ms'], input=book.input_sha256)), orders=0)
    if legal_new_buy is not True:
        return dict(status='BLOCK_ORIGINAL_NEW_BUY', orders=0)
    return dict(status='PROPOSE_NEW_BUDGET_RESEARCH', factor='1' if feature['release'] else '.5',
                held_changes=False, topup=False, source_sha256=book.input_sha256, orders=0)


def qualify_cross(packet, now):
    """Strict normalized public-window admission; retain all missing causes.

    A complete_window flag alone is insufficient. Both venue prefixes and tails
    require causal boundary receipts; each sequence must have zero known gaps.
    Normalization/source-document proofs remain explicit research assumptions.
    """
    if packet is None:
        return dict(status='PENDING', reasons=['no_complete_paired_public_window'], account_entrant=False)
    reasons = []
    for key in ('start_ms', 'end_ms', 'available_ms'):
        if type(packet.get(key)) is not int:
            raise ValueError('integer cross-window clocks required')
    if type(now) is not int or not packet['start_ms'] < packet['end_ms'] <= packet['available_ms'] <= now:
        raise ValueError('future or reversed cross-window availability')
    legs = packet.get('boundary_proofs', [])
    if len(legs) != 2 or len({leg.get('venue') for leg in legs}) != 2:
        reasons.append('two_venue_boundary_proofs_missing')
    hashes = set(packet.get('source_sha256', []))
    for leg in legs:
        prefix, tail = leg.get('prefix'), leg.get('tail')
        semantics = leg.get('semantics_sha256')
        if semantics not in hashes or leg.get('unit') != 'BTC' or leg.get('side_role') != 'taker':
            reasons.append('qualified_units_and_aggressor_semantics_missing')
        if leg.get('gaps') != [] or leg.get('conflicts') != [] or leg.get('reconnects') != 0:
            reasons.append('sequence_gap_or_conflict_not_closed')
        if prefix is None or tail is None:
            reasons.append('prefix_or_tail_receipt_missing')
            continue
        for proof in (prefix, tail):
            if (type(proof.get('event_ms')) is not int or type(proof.get('available_ms')) is not int
                    or not proof['event_ms'] <= proof['available_ms'] <= packet['available_ms']
                    or proof.get('raw_sha256') not in hashes or proof.get('sequence_complete') is not True):
                reasons.append('causal_raw_boundary_sequence_proof_missing')
        if prefix.get('event_ms', now) > packet['start_ms'] or tail.get('event_ms', -1) < packet['end_ms']:
            reasons.append('event_time_window_not_bracketed')
    if reasons:
        return dict(status='PENDING', reasons=sorted(set(reasons)), account_entrant=False)
    event = cross_demand(packet, now)
    if event['status'] not in ('DEMAND_CANDIDATE', 'NO_EVENT'):
        return dict(status='PENDING', reasons=[event['status']], account_entrant=False)
    return dict(status='QUALIFIED_RESEARCH_FEATURE', event=event, account_entrant=False,
                input_sha256=digest(packet), available_ms=packet['available_ms'],
                outcome_status='PENDING_MATURE_NET_OUTCOME_AND_PRICE_SINGLE_VENUE_CONTROLS',
                authenticated_market_or_account=False)


def mature_cross(features, labels, now):
    """No receipt-day sample inflation; require complete nonoverlapping labels.

    Labels are independently produced net-return/control records; this function
    checks qualification and maturity, never invents future prices or funding.
    """
    rows, pending, through = [], 0, -1
    for feature in sorted(features, key=lambda r: r['available_ms']):
        if feature.get('status') != 'QUALIFIED_RESEARCH_FEATURE':
            pending += 1
            continue
        label = labels.get(feature['input_sha256'])
        if label is None or label.get('available_ms', now+1) > now:
            pending += 1
            continue
        begin, end = label['entry_ms'], label['exit_ms']
        if (type(begin) is not int or type(end) is not int or begin < feature['available_ms']
                or end-begin != 7*DAY or not end <= label['available_ms'] <= now
                or label.get('feature_sha256') != feature['input_sha256']):
            raise ValueError('label must follow exact qualified feature and mature seven-day interval')
        if any(k not in label for k in ('net_return', 'stress_net_return', *CONTROLS, 'single_venue_imbalance')):
            raise ValueError('price, level and single-venue net outcome controls required')
        if begin < through:
            continue
        through = end
        rows.append(dict(label, release=feature['event']['positive']))
    result = assess(rows, len(features), (*CONTROLS, 'single_venue_imbalance'))
    return dict(result, matured_nonoverlapping=len(rows), pending=pending, rows=rows,
                reason='Source/maturity qualification precedes incremental net outcome evaluation; no automatic adoption')
