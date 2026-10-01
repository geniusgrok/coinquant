"""Registered research variants through the real finite session and Lifecycle.

All overrides are process-local and research-only. Old measurement identities
and production defaults remain intact; economic selection never enables trading.
"""
import argparse
import bisect
from collections import Counter, deque
from contextlib import contextmanager
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
import tempfile

from coinquant import campaign, linear_preview
from coinquant.config import Config
from coinquant.linear_account import FEE
from coinquant.linear_sizing import GAP, FUNDING_RESERVE
from coinquant.opportunities import Opportunity
from coinquant.session import run
from coinquant.types import Blocked, Unknown
from research import rebuild, session_schedule
from research.comparison_report import audit
from research.rolling_prints import RollingPrints
from research.session_exchange import SessionExchange
from research.session_market import load_base, TradePrints
from research.unified_perp import PriorFX

DAY, EIGHT_HOURS = 86400000, 28800000
CANDIDATES = ('incumbent', 'tail-sizing', 'no-macro', 'slow-trend',
              'funding-filter', 'basis-filter', 'conditional-short')
SCENARIOS = {'base': {}, 'fees-x1.5': {'fee': D('.001125')},
             'read-400ms': {'read_latency_ms': 400},
             'trigger-slip': {'trigger_slippage': D('.0015')}}
BaseCampaign = campaign.Campaign


def checksum(body):
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


class Crowding:
    def __init__(self, path):
        raw = Path(path).read_bytes()
        self.sha256 = hashlib.sha256(raw).hexdigest()
        body = json.loads(raw)
        self.source = body['source']
        self.rows = {}
        self.times = {}
        self.coverage = Counter()
        for feature in ('funding', 'basis'):
            rows = [(stamp, D(str(value))) for stamp, value in body[feature]]
            if any(type(t) is not int or not v.is_finite() for t, v in rows) or any(
                    a[0] >= b[0] for a, b in zip(rows, rows[1:])):
                raise ValueError('invalid feature time series')
            self.rows[feature] = rows
            self.times[feature] = [t for t, _ in rows]

    def value(self, feature, now):
        known = now - EIGHT_HOURS if feature == 'funding' else now
        age_limit = EIGHT_HOURS if feature == 'funding' else DAY
        index = bisect.bisect_right(self.times[feature], known) - 1
        if index < 0 or known - self.rows[feature][index][0] >= age_limit:
            self.coverage[feature + '_missing_or_stale'] += 1
            return None
        self.coverage[feature + '_known'] += 1
        return self.rows[feature][index][1]


class ResearchCampaign(BaseCampaign):
    variant = 'incumbent'
    crowding = None

    def __init__(self):
        super().__init__()
        self.daily_closes = deque(maxlen=65)
        self.decision_ms = None

    def update(self, end, high, low, close):
        result = super().update(end, high, low, close)
        if end % DAY == 0:
            self.daily_closes.append(D(close))
        return result

    def trend(self, direction):
        if len(self.daily_closes) < 65:
            return False
        closes = list(self.daily_closes)
        sma = sum(closes[-60:]) / 60
        old = sum(closes[-65:-5]) / 60
        return (closes[-1] > sma and sma > old if direction > 0
                else closes[-1] < sma and sma < old)

    def short_active(self):
        primary = self.model.active
        return self.variant == 'conditional-short' and primary is not None and (
            primary.direction < 0 and self.trend(-1) and
            (self.position_campaign == primary.identity or primary.identity != self.primary_consumed))

    @property
    def active(self):
        if self.position_campaign is not None and self.position_campaign < 0:
            return self.macro_opportunity
        if self.short_active():
            return self.model.active
        return super().active

    def macro_relevant(self):
        if self.variant in ('no-macro', 'slow-trend') or (self.short_active() and
                (self.position_campaign is None or self.position_campaign >= 0)):
            return False
        return super().macro_relevant()

    def select_macro(self, row, mark, call, *, bootstrap=False):
        if type(call) is not int or not self.last <= call < self.last + self.model.interval:
            raise Blocked('decision precedes completed market')
        self.decision_ms = call
        if self.variant == 'no-macro' or (self.short_active() and (
                self.position_campaign is None or self.position_campaign >= 0)):
            self.macro_epoch = self.macro_opportunity = None
            self.macro_observation = None
            return
        if self.variant != 'slow-trend':
            return super().select_macro(row, mark, call, bootstrap=bootstrap)
        self.macro_observation = {'research': 'completed-SMA60-rising-five-days', 'call_ms': call}
        primary = self.model.active
        if (not self.trend(1) or (self.position_campaign is not None and self.position_campaign >= 0)
                or (self.position_campaign is None and primary is not None and primary.direction > 0
                    and primary.identity != self.primary_consumed)):
            self.macro_epoch = self.macro_opportunity = None
            return
        if self.position_campaign is not None:
            if self.macro_opportunity is None or self.macro_opportunity.identity != self.position_campaign:
                raise Blocked('owned slow trend geometry unavailable')
            return
        if self.macro_epoch is None:
            self.macro_epoch = -call
        if bootstrap:
            self.macro_consumed = self.macro_epoch
        if self.macro_opportunity is None and len(self.daily_lows) == 10:
            stop, price = min(self.daily_lows), D(mark)
            if 0 < stop < price:
                self.macro_opportunity = Opportunity(self.macro_epoch, 1, stop, price * (price / stop) ** 20, None)

    def fraction(self, risk, friction):
        if self.variant != 'tail-sizing':
            return super().fraction(risk, friction)
        if len(self.returns) < 20:
            return D(0)
        returns = list(self.returns)
        rms = max((sum((v*v for v in returns[-n:]), D(0)) / n).sqrt() for n in (20, 5))
        return D(risk)*D('.20')/(D('2.33')*rms*D(7).sqrt()+GAP+FUNDING_RESERVE+2*(FEE+D(friction)))

    def action(self, quantity):
        action = super().action(quantity)
        if action == 'enter' and self.active.direction > 0 and self.variant in ('funding-filter', 'basis-filter'):
            feature = 'funding' if self.variant == 'funding-filter' else 'basis'
            value = self.crowding.value(feature, self.decision_ms) if self.crowding is not None else None
            if value is None or value > (D('.0003') if feature == 'funding' else D('.01')):
                return 'flat'
        return action

    def checkpoint(self):
        saved = super().checkpoint()
        saved['body']['research'] = {'variant': self.variant, 'daily_closes': list(map(str, self.daily_closes)),
                                     'decision_ms': self.decision_ms}
        saved['sha256'] = checksum(saved['body'])
        return saved

    @classmethod
    def restore(cls, saved):
        if saved.get('sha256') != checksum(saved['body']):
            raise Blocked('invalid research checkpoint digest')
        body = dict(saved['body'])
        extra = body.pop('research')
        if extra['variant'] != cls.variant:
            raise Blocked('candidate checkpoint mismatch')
        result = BaseCampaign.restore.__func__(cls, {'body': body, 'sha256': checksum(body)})
        closes = [D(v) for v in extra['daily_closes']]
        if len(closes) > 65 or any(not v.is_finite() or v <= 0 for v in closes):
            raise Blocked('invalid research daily closes')
        result.daily_closes = deque(closes, maxlen=65)
        result.decision_ms = extra['decision_ms']
        return result


@contextmanager
def variant(name, crowding):
    old = campaign.Campaign, linear_preview.Campaign, ResearchCampaign.variant, ResearchCampaign.crowding
    campaign.Campaign = linear_preview.Campaign = ResearchCampaign
    ResearchCampaign.variant, ResearchCampaign.crowding = name, crowding
    try:
        yield
    finally:
        campaign.Campaign, linear_preview.Campaign, ResearchCampaign.variant, ResearchCampaign.crowding = old


class ResearchExchange(SessionExchange):
    def __init__(self, *args, fx, **kwargs):
        # Initial metric point must use the same prior FX and exit conversion.
        self.fx, self.exit_conversion = fx, D('.001')
        self.daily = {}
        super().__init__(*args, **kwargs)

    def capture(self, stamp, price=None):
        if self.q and price is None:
            return
        price = D(price or 0)
        equity = self.wallet + (self.q*(price-self.entry) if self.q else D(0))
        # Closing boundary belongs to the day that just finished.
        day = (stamp-1)//DAY if stamp % DAY == 0 else stamp//DAY
        self.daily[day] = {'date': rebuild.iso(day*DAY)[:10], 'stamp_ms': stamp,
            'equity_usdt': str(equity), 'equity_cny': str(equity*self.fx(stamp)*(1-self.exit_conversion)),
            'wallet_usdt': str(self.wallet), 'quantity_btc': str(self.q), 'mark_usdt': str(price),
            'net_btc_exposure_usdt': str(self.q*price), 'gross_btc_exposure_usdt': str(abs(self.q)*price),
            'fees_usdt': str(self.fees), 'funding_paid_usdt': str(self.funding_paid)}

    def _note_cash(self):
        super()._note_cash()
        if not self.q:
            self.capture(self.now_ms)

    def _on_minute(self, open_ms):
        super()._on_minute(open_ms)
        if (open_ms+60000) % DAY == 0:
            row = self.market.minute('mark', open_ms) or self.market.minute('trade', open_ms)
            if row is not None:
                self.capture(open_ms+60000, row[3])

    def _partial(self, open_ms, at_boundary):
        super()._partial(open_ms, at_boundary)
        if at_boundary and (open_ms+60000) % DAY == 0:
            row = self.market.minute('mark', open_ms) or self.market.minute('trade', open_ms)
            if row is not None:
                self.capture(open_ms+60000, row[3])

    def _pay_funding(self, start_ms, end_ms):
        super()._pay_funding(start_ms, end_ms)
        if self.q and end_ms % DAY == 0 and self.now_ms == end_ms:
            row = self.market.minute('mark', end_ms-60000)
            if row is not None:
                self.capture(end_ms, row[3])


def select(results):
    eligible, decisions = [], {}
    incumbent_complete = all(r['complete'] and r['audit']['passed'] and r['known_path'] and
        not r['execution_unresolved'] for r in results['incumbent'].values())
    for name in CANDIDATES:
        rows = [results[name][s] for s in SCENARIOS]
        complete = all(r['complete'] and r['audit']['passed'] and r['known_path'] and
                       not r['execution_unresolved'] for r in rows)
        incumbent = results['incumbent']
        matched = complete and incumbent_complete and all(D(r['mdd']) < D('.5') and r['cagr'] >= incumbent[s]['cagr']-.01
            for s, r in zip(SCENARIOS, rows))
        base, reference = results[name]['base'], incumbent['base']
        improvement = complete and incumbent_complete and (base['cagr'] >= reference['cagr']+.01 or
            (D(base['mdd']) <= D(reference['mdd'])-D('.01') and base['cagr'] >= reference['cagr']-.03))
        accepted = name not in ('incumbent', 'no-macro') and matched and improvement
        decisions[name] = {'complete_audited': complete, 'matched_constraints': matched,
                          'improvement': improvement, 'eligible': accepted,
                          'worst_cagr': min(r['cagr'] for r in rows) if complete else None}
        if accepted:
            eligible.append(name)
    all_incumbent = decisions['incumbent']['complete_audited']
    selected = max(eligible, key=lambda n: (decisions[n]['worst_cagr'], -CANDIDATES.index(n))) if eligible and all_incumbent else 'incumbent'
    return {'selected_research_candidate': selected, 'decisions': decisions,
            'production_promoted': False, 'native_execution_verified': False}


def measure(args):
    identity = rebuild.source_identity()
    if identity['dirty']:
        raise ValueError('commit research and production sources before measurement')
    protocol = rebuild.ROOT/'research/complete-delivery-PROTOCOL.md'
    inputs = {'source': identity, 'protocol_sha256': hashlib.sha256(protocol.read_bytes()).hexdigest()}
    schedule = session_schedule.load()['primary']
    starts = schedule['starts_ms'][:args.limit]
    fx, crowding = PriorFX(args.fx), Crowding(args.crowding)
    inputs.update(schedule_sha256=schedule['sha256'], fx_sha256=fx.sha256,
                  crowding_sha256=crowding.sha256, crowding_source=crowding.source)
    market = load_base(args.market)
    tape = RollingPrints(args.prints) if args.restore_prints else TradePrints(args.prints)
    initial = D(10000)/fx(rebuild.timestamp(rebuild.START))*D('.999')
    with tempfile.TemporaryDirectory(prefix='complete-perp-') as scratch:
        accounts = {}
        for i, name in enumerate(CANDIDATES):
            for j, (scenario, options) in enumerate(SCENARIOS.items()):
                e = ResearchExchange(market, starts[0], initial, fx=fx, matcher='trade_print', prints=tape, uid=12000+i*4+j)
                e.read_latency_ms, e.latency_ms, e.mark_gap = 200, 1000, 'bound'
                for k, v in options.items():
                    setattr(e, k, v)
                accounts[name, scenario] = {'exchange': e, 'state': Path(scratch)/name/scenario,
                                            'sessions': [], 'failure': None, 'coverage': Counter()}
        for index, start in enumerate(starts):
            for (name, scenario), c in accounts.items():
                if c['failure']:
                    continue
                e = c['exchange']
                try:
                    with variant(name, crowding):
                        if e.now_ms < start:
                            e.advance_unattended(start)
                        before = crowding.coverage.copy()
                        report = run(Config(str(e.uid), str(c['state']), 300, 5), e,
                                     execute=True, monotonic=e.monotonic, wait=e.wait)
                        c['coverage'].update(crowding.coverage-before)
                        c['sessions'].append({'index': index, 'start_ms': start, 'status': report['status'],
                            'execution_unresolved': bool(report.get('execution_unresolved')),
                            'cleanup': report.get('cleanup'), 'cycles': report.get('cycles'),
                            'observations': rebuild._harvest(c['state'])})
                except (Unknown, OSError, ValueError, KeyError, TypeError, ArithmeticError) as exc:
                    c['failure'] = {'type': type(exc).__name__, 'reason': str(exc), 'session': index}
            if index % 10 == 0:
                print(json.dumps({'session': index, 'date': rebuild.iso(start), 'failures': {
                    '/'.join(key): c['failure'] for key, c in accounts.items() if c['failure']}}), flush=True)
            checkpoint = args.out.with_suffix('.progress.json')
            checkpoint.write_text(json.dumps({'source': identity, 'complete': False, 'last_session': index,
                'accounts': {'/'.join(k): {'sessions': len(c['sessions']), 'wallet': str(c['exchange'].wallet),
                  'position': str(c['exchange'].q), 'failure': c['failure']} for k,c in accounts.items()}}, indent=2)+'\n')
        results = {name: {} for name in CANDIDATES}
        end = rebuild.timestamp(rebuild.END) if args.limit is None else starts[-1]+420000
        for (name, scenario), c in accounts.items():
            e, mark, equity = c['exchange'], None, None
            try:
                if not c['failure']:
                    e.advance_unattended(max(e.now_ms, end))
                mark = rebuild._final_mark(e) if e.q else D(0)
                equity = e.wallet+(e.q*(mark-e.entry) if e.q else D(0))
                e.capture(e.now_ms, mark)
            except (Unknown, OSError, ValueError) as exc:
                c['failure'] = {'type': type(exc).__name__, 'reason': str(exc), 'phase': 'finalization'}
            complete = args.limit is None and not c['failure'] and len(c['sessions']) == 795
            cny = equity*e._cny() if equity is not None else None
            row = {'complete': bool(complete), 'final_usdt': str(equity), 'final_cny': str(cny),
                'cagr': (float(cny/10000)**(rebuild.YEAR_MS/(end-rebuild.timestamp(rebuild.START)))-1
                         if cny > 0 else -1) if complete and cny is not None else None,
                'mdd': str(e.mdd_envelope), 'mdd_close': str(e.mdd_close),
                'mdd_envelope_at': e.mdd_envelope_at, 'mdd_close_at': e.mdd_close_at,
                'position': str(e.q), 'fees': str(e.fees), 'funding': str(e.funding_paid),
                'final_mark': str(mark), 'known_path': e.known_path, 'unknown_from': e.unknown_from,
                'hindsight_bounded': e.hindsight_bounded, 'bounded_minutes': e.bounded_minutes,
                'funnel': e.funnel, 'failure': c['failure'], 'trades': e.trades, 'funding_ledger': e.income,
                'sessions': c['sessions'], 'feature_coverage': dict(c['coverage']),
                'execution_unresolved': sum(r['execution_unresolved'] for r in c['sessions']),
                'daily': [v for k,v in sorted(e.daily.items()) if k*DAY >= rebuild.timestamp(rebuild.START)],
                'daily_cny': sorted(e.daily_cny.items())}
            row['audit'] = audit(row, initial, mark) if equity is not None else {'passed': False}
            results[name][scenario] = row
            print(json.dumps({'finished': name+'/'+scenario, 'complete': complete, 'audit': row['audit']['passed'],
                              'cagr': row['cagr'], 'mdd': row['mdd']}), flush=True)
        inputs.update(market_identity=market.identity, loaded_minute_files=market.loaded,
                      loaded_print_files=tape.loaded)
        return {'inputs': inputs, 'results': results, 'selection': select(results),
            'conditions': {'initial_fx_corrected_before_first_metric': True, 'start_cny': 10000,
                'conversion_each_way': '.001', 'read_latency_ms': 200, 'write_latency_ms': 1000,
                'default_fee': '.00075', 'scenarios': SCENARIOS,
                'funding_filter_lag_ms': EIGHT_HOURS, 'funding_stale_age_ms': EIGHT_HOURS,
                'basis_stale_age_ms': DAY, 'daily_metrics': 'daily snapshots; not continuous MDD',
                'venue': 'historical proxy, not native fills or prospective alpha',
                'qualification': 'NOT_QUALIFIED'}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--market', type=Path, default=Path('/tmp/coinquant-market'))
    parser.add_argument('--prints', type=Path, default=Path('/workspace/.btc-third-round-prints'))
    parser.add_argument('--fx', type=Path, default=Path('/workspace/starquant/data/usdcny_frankfurter.json'))
    parser.add_argument('--crowding', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--restore-prints', action='store_true')
    parser.add_argument('--limit', type=int)
    args = parser.parse_args(argv)
    if args.out.exists() or (args.limit is not None and (not 1 <= args.limit <= 795 or
            not str(args.out.resolve()).startswith('/tmp/'))):
        parser.error('never overwrite results; partial smoke output must stay under /tmp')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    result = measure(args)
    with args.out.open('x') as stream:
        json.dump(result, stream, default=str, allow_nan=False)
        stream.write('\n')
    return 2 if any(r['failure'] or not r['audit']['passed'] for rows in result['results'].values() for r in rows.values()) else 0


if __name__ == '__main__':
    raise SystemExit(main())
