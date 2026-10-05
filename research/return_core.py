"""Causal, strongly shrunk net-return core; explicit offline research only.

Daily open quotes and funding marks are disclosed research proxies. They are not
executable perpetual quotes, native financing history or new out-of-sample proof.
Statistical fitting uses floats; account sizing and protection remain Decimal.
"""
from bisect import bisect_left, bisect_right
from collections import deque
from contextlib import contextmanager
from decimal import Decimal as D
import hashlib
import json
import math
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

DAY = 86400000
FUNDING_INTERVAL = 28800000
RULE = 'btc-net-return-core-20261005-v1'
MODES = ('positive', 'low-turnover')
PARAMETERS = dict(horizon_days=7, entry_delay_days=2, feature_days=[5, 20],
                  min_samples=26, max_samples=156, ridge=100,
                  fee='.00075', slip='.0005', target='1', stop_fraction='.25',
                  low_turnover_owned_days=7, low_turnover_negative_days=2)


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


def ridge_predict(training, current):
    """Train-only scaling; sum squared errors + 100 * all coefficients squared."""
    count = len(training)
    means = [sum(x[j] for x, _ in training)/count for j in range(3)]
    scales = [math.sqrt(sum((x[j]-means[j])**2 for x, _ in training)/count)
              or 1.0 for j in range(3)]
    design = [[1.0, *((x[j]-means[j])/scales[j] for j in range(3))]
              for x, _ in training]
    matrix = [[sum(x[i]*x[j] for x in design)+(100.0 if i == j else 0.0)
               for j in range(4)] for i in range(4)]
    rhs = [sum(x[i]*y for x, (_, y) in zip(design, training)) for i in range(4)]
    for i in range(4):
        divisor = matrix[i][i]
        for j in range(i, 4):
            matrix[i][j] /= divisor
        rhs[i] /= divisor
        for k in range(4):
            if k != i:
                amount = matrix[k][i]
                for j in range(i, 4):
                    matrix[k][j] -= amount*matrix[i][j]
                rhs[k] -= amount*rhs[i]
    prediction = rhs[0]+sum(rhs[j+1]*(current[j]-means[j])/scales[j] for j in range(3))
    if not math.isfinite(prediction):
        raise ValueError('nonfinite fitted forecast')
    return D(str(prediction))


class Forecast:
    """Fixed weekly, non-overlapping labels admitted only after full maturity.

Input bars are (UTC day, open, high, low, close). Input funding is the already
validated FeatureBook (observation, available, rate, cause) sequence. Prices use
modeled completion+60000ms. A missing settlement never becomes a zero rate.
"""
    def __init__(self, bars, funding, mode='positive'):
        if mode not in MODES:
            raise ValueError('unregistered return-core expression')
        self.mode = mode
        bars = [(t, *(D(str(v)) for v in row)) for t, *row in bars]
        if (any(type(t) is not int or t % DAY or len(row) != 4 or
                any(not p.is_finite() or p <= 0 for p in row) or
                not row[2] <= min(row[0], row[3]) <= max(row[0], row[3]) <= row[1]
                for t, *row in bars) or any(b[0]-a[0] != DAY for a, b in zip(bars, bars[1:]))):
            raise ValueError('contiguous completed BTC daily OHLC required')
        funding = [(t, a, None if r is None else D(str(r)), cause)
                   for t, a, r, cause in funding]
        if (any(type(t) is not int or type(a) is not int or a != t+FUNDING_INTERVAL or
                t % FUNDING_INTERVAL >= 60000 or
                r is None and not isinstance(cause, str) or
                r is not None and (cause is not None or not r.is_finite())
                for t, a, r, cause in funding) or
                any(b[0] <= a[0] for a, b in zip(funding, funding[1:]))):
            raise ValueError('validated settled funding chronology/lag required')
        self.input_sha256 = digest(dict(bars=bars, funding=funding))
        self.bars, self.funding = bars, funding
        by_day = {row[0]: row for row in bars}
        funds = {t//FUNDING_INTERVAL: (t, a, r, cause) for t, a, r, cause in funding}
        if len(funds) != len(funding):
            raise ValueError('duplicate eight-hour funding settlement slot')
        feature_rows, labels = [], []
        for i, row in enumerate(bars):
            t, _, _, _, close = row
            feature = None
            if i >= 20:
                returns = [float(bars[j][4]/bars[j-1][4]-1) for j in range(i-19, i+1)]
                feature = (float(close/bars[i-5][4]-1), float(close/bars[i-20][4]-1),
                           math.sqrt(sum(min(r, 0.0)**2 for r in returns)/20))
            feature_rows.append((t+DAY+60000, t, feature))
            if feature is None or (t//DAY) % 7:
                continue
            entry, exit_ = t+2*DAY, t+9*DAY
            if entry not in by_day or exit_ not in by_day:
                continue
            slots = range(entry//FUNDING_INTERVAL+1, exit_//FUNDING_INTERVAL+1)
            settled = [funds.get(slot) for slot in slots]
            if any(f is None or f[2] is None or f[3] is not None for f in settled):
                continue
            entry_quote = by_day[entry][1]
            exit_quote = by_day[exit_][1]
            entry_fill = entry_quote*(1+D(PARAMETERS['slip']))
            exit_fill = exit_quote*(1-D(PARAMETERS['slip']))
            price_gain = exit_fill/entry_fill-1
            fees = D(PARAMETERS['fee'])*(entry_fill+exit_fill)/entry_fill
            # Quotes are daily spot-open mark proxies at actual settlement slots.
            funding_cash = sum((rate*by_day[obs//DAY*DAY][1]/entry_fill
                                for obs, _, rate, _ in settled), D(0))
            available = max(exit_+60000, max(f[1] for f in settled))
            labels.append(dict(day_ms=t, entry_ms=entry+60000, exit_ms=exit_+60000,
                               available_ms=available, features=feature,
                               gross_return=price_gain, fees=fees, funding=funding_cash,
                               net_return=price_gain-fees-funding_cash))
        self.labels = labels
        ordered = sorted(labels, key=lambda r: r['available_ms'])
        known, cursor, rows = [], 0, []
        for available, t, feature in feature_rows:
            while cursor < len(ordered) and ordered[cursor]['available_ms'] < available:
                known.append(ordered[cursor]); cursor += 1
            training = known[-PARAMETERS['max_samples']:]
            prediction = None
            if feature is not None and len(training) >= PARAMETERS['min_samples']:
                prediction = ridge_predict([(r['features'], float(r['net_return'])) for r in training], feature)
            rows.append(dict(day_ms=t, available_ms=available, prediction=prediction,
                             training_count=len(training),
                             latest_label_available_ms=max((r['available_ms'] for r in training), default=None)))
        self.rows = rows
        self.times = [r['available_ms'] for r in rows]

    def at(self, call):
        i = bisect_right(self.times, call)-1
        return self.rows[i] if i >= 0 else None


def campaign_class(book):
    from coinquant.campaign import Campaign as Legacy
    from coinquant.opportunities import Opportunity
    from coinquant.types import Blocked

    class ReturnCampaign(Legacy):
        continuous_entry = True
        core_rule = RULE+':'+book.mode

        def __init__(self):
            super().__init__()
            self.core_active = None
            self.target = D(0)
            self.extreme = self.peak_after = self.owned_since = None
            self.signal_call = self.signal_day = self.prediction = None
            self.negative_days = 0
            self.stop_crossed = False

        @property
        def active(self):
            return self.core_active

        def macro_relevant(self):
            return False

        def update(self, end, high, low, close):
            Legacy.update(self, end, high, low, close)
            a = self.core_active
            if a is not None and self.position_campaign == a.identity:
                eligible = self.peak_after is not None and end-self.model.interval >= self.peak_after
                self.extreme = max(self.extreme, D(high) if eligible else D(close))
                self.core_active = Opportunity(a.identity, 1, max(a.stop, self.extreme*D('.75')), a.take, None)
            return self.core_active

        def select_macro(self, row, mark, call, *, bootstrap=False):
            if row is not None or type(call) is not int or not self.last <= call < self.last+self.model.interval:
                raise Blocked('return core requires its causal completed market boundary')
            f = book.at(call)
            if f is None or call-f['available_ms'] >= 2*DAY:
                raise Blocked('causal return forecast unavailable or stale')
            if self.position_campaign is not None and self.owned_since is None:
                # Begins after recovery confirmed ownership, never from price replay.
                self.owned_since = call
            elif self.position_campaign is None:
                self.owned_since = None
            fresh_day = self.signal_day != f['day_ms']
            p = f['prediction']
            if fresh_day:
                self.negative_days = self.negative_days+1 if p is not None and p <= 0 else 0
            desired = p is not None and p > 0
            if (book.mode == 'low-turnover' and self.core_active is not None and
                    self.position_campaign == self.core_active.identity and
                    p is not None and not desired):
                desired = call < self.owned_since+7*DAY or self.negative_days < 2
            self.signal_call, self.signal_day, self.prediction = call, f['day_ms'], p
            self.target = D(1) if desired else D(0)
            if not desired:
                self.core_active = None
            elif self.core_active is None:
                price = D(mark)
                if not price.is_finite() or price <= 0:
                    raise Blocked('causal return-core entry quote required')
                self.extreme, self.peak_after = price, (call//self.model.interval+1)*self.model.interval
                self.core_active = Opportunity(self.last, 1, price*D('.75'), price*4, None)
            self.macro_observation = None
            self.stop_crossed = bool(self.core_active and self.position_campaign is not None and D(mark) <= self.core_active.stop)

        def entry_fraction(self, friction):
            return self.target

        def action(self, quantity):
            if quantity and self.stop_crossed:
                return 'exit'
            return Legacy.action(self, quantity)

        def checkpoint(self):
            saved = Legacy.checkpoint(self)
            a = self.core_active
            saved['body']['core'] = serial(dict(rule=self.core_rule, input_sha256=book.input_sha256,
                signal_call=self.signal_call, signal_day=self.signal_day, prediction=self.prediction,
                target=self.target, negative_days=self.negative_days, owned_since=self.owned_since,
                extreme=self.extreme, peak_after=self.peak_after, stop_crossed=self.stop_crossed,
                active=None if a is None else dict(identity=a.identity, stop=a.stop, take=a.take)))
            saved['sha256'] = digest(saved['body'])
            return saved

        @classmethod
        def restore(cls, saved):
            try:
                if saved['sha256'] != digest(saved['body']):
                    raise ValueError('return checkpoint digest')
                body = dict(saved['body']); core = body.pop('core')
                if core['rule'] != cls.core_rule or core['input_sha256'] != book.input_sha256:
                    raise ValueError('return forecast identity')
                result = Legacy.restore.__func__(cls, dict(body=body, sha256=digest(body)))
                for key in ('signal_call', 'signal_day', 'negative_days', 'owned_since', 'peak_after', 'stop_crossed'):
                    setattr(result, key, core[key])
                for key in ('prediction', 'target', 'extreme'):
                    setattr(result, key, None if core[key] is None else D(core[key]))
                if (result.target not in (D(0), D(1)) or type(result.negative_days) is not int or result.negative_days < 0 or
                        type(result.stop_crossed) is not bool or result.owned_since is not None and
                        (type(result.owned_since) is not int or not 0 < result.owned_since < result.last+result.model.interval)):
                    raise ValueError('return ownership state')
                if result.signal_call is not None:
                    f = book.at(result.signal_call)
                    if (type(result.signal_call) is not int or not 0 < result.signal_call < result.last+result.model.interval or
                            f is None or result.signal_day != f['day_ms'] or result.prediction != f['prediction']):
                        raise ValueError('causal fitted forecast binding')
                elif result.signal_day is not None or result.prediction is not None or result.target:
                    raise ValueError('missing forecast clock')
                a = core['active']
                result.core_active = None if a is None else Opportunity(a['identity'], 1, D(a['stop']), D(a['take']), None)
                if a is not None and (type(a['identity']) is not int or not 1575158400000 < a['identity'] <= result.last or
                        not result.target or not 0 < result.core_active.stop < result.core_active.take or
                        any(not p.is_finite() for p in (result.core_active.stop, result.core_active.take)) or
                        result.extreme is None or not result.extreme.is_finite() or result.extreme <= 0):
                    raise ValueError('funded return campaign geometry')
                if result.peak_after is not None and (type(result.peak_after) is not int or
                        result.peak_after % result.model.interval or result.peak_after > result.last+result.model.interval):
                    raise ValueError('return owned peak clock')
                return result
            except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
                raise Blocked('foreign or invalid return-core checkpoint; no automatic reset') from exc

    return ReturnCampaign


@contextmanager
def configured(book, *, binding, journal=None):
    """Matching cold, independent offline wallets; guard precedes any recovery."""
    from coinquant import linear_preview, session
    from coinquant.lifecycle import Lifecycle
    from coinquant.types import Blocked
    if not isinstance(book, Forecast) or not isinstance(binding, dict) or not binding:
        raise ValueError('bound return forecast required')
    identity = dict(rule=RULE, mode=book.mode, parameters=PARAMETERS, input_sha256=book.input_sha256,
                    source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), binding=binding)
    selected = campaign_class(book)
    original_guard, original_rebalance = session._guard_strategy, Lifecycle.rebalance
    journal = journal if journal is not None else []

    def guard(state):
        stored = state.get('lifecycle_identity')
        occupied = any(state.get(k) is not None for k in ('linear_campaign', 'entry_plan', 'entry_fill',
                       'entry_campaigns', 'settled_entry_campaigns', 'position_protection'))
        if stored != identity and (stored is not None or occupied or state.db.execute('SELECT 1 FROM intents LIMIT 1').fetchone()):
            raise Blocked('return-core account identity mismatch before recovery')
        if stored is None:
            state.set('lifecycle_identity', identity)
        return original_guard(state)

    def rebalance(engine, model, snapshot):
        return snapshot if isinstance(model, selected) and book.mode == 'low-turnover' else original_rebalance(engine, model, snapshot)

    def check(reader):
        if getattr(reader, 'offline', False) is not True:
            raise Blocked('return core refuses account adapters before clock/recovery')

    def run(config, reader, **kwargs):
        check(reader)
        result = session.run(config, reader, **kwargs)
        journal.append(dict(event='return-core-session', mode=book.mode, status=result['status']))
        return result

    def cycle(reader, *args, **kwargs):
        check(reader)
        return session.cycle(reader, *args, **kwargs)

    with patch.object(linear_preview, 'Campaign', selected), patch.object(session, '_LIFECYCLE_IDENTITY', identity), \
            patch.object(session, '_guard_strategy', guard), patch.object(Lifecycle, 'rebalance', rebalance):
        yield SimpleNamespace(run=run, cycle=cycle, identity=identity)
