"""Fixed pullback-recovery hypothesis, using existing protected long campaigns."""
from collections import deque
from contextlib import contextmanager
from decimal import Decimal as D
from unittest.mock import patch

from coinquant.opportunities import FOUR_HOURS, Opportunity
from coinquant.types import Blocked
from research import alpha_perp as alpha, complete_perp as meter

BASE = alpha.AlphaCampaign


def recovery(closes, lows, prior_atr):
    """Completed-bar-only long recovery; fixed parameters, no threshold search."""
    if len(closes) < 360 or len(lows) < 6 or prior_atr is None or prior_atr <= 0:
        return None
    close, previous = closes[-1], closes[-2]
    # Sixty days of 4h closes, a prior 24h drawdown and a subsequent up close.
    if not (close > sum(closes[-360:])/360 and close > previous and
            max(closes[-7:-2])-previous >= 2*prior_atr):
        return None
    stop = min(lows[-6:])
    if not 0 < stop < close:
        return None
    return stop, close + 2*(close-stop)


class PullbackCampaign(BASE):
    def __init__(self):
        super().__init__()
        self.recovery_closes = deque(maxlen=360)
        self.recovery_lows = deque(maxlen=6)

    def update(self, end, high, low, close):
        atr = sum(self.model.tr)/14 if len(self.model.tr) == 14 else None
        super().update(end, high, low, close)
        self.recovery_closes.append(D(close))
        self.recovery_lows.append(D(low))
        signal = recovery(list(self.recovery_closes), list(self.recovery_lows), atr)
        # Preserve owned campaigns and genuine incumbent primary longs.
        if (signal and self.position_campaign is None and
                (self.model.active is None or self.model.active.direction < 0)):
            stop, take = signal
            self.model.active = Opportunity(end, 1, stop, take, end + 14*FOUR_HOURS)
            self.trigger = dict(identity=end, close=str(close), prior_atr=str(atr),
                                direction=1, kind='impulse', signal_family='pullback-recovery')
            if self.journal is not None:
                self.journal.append(dict(event='opportunity', at_ms=end, **self.trigger))
        return self.model.active

    def entry_fraction(self, friction):
        value = super().entry_fraction(friction)
        if (self.active is not None and self.active.identity > 0 and self.trigger and
                self.trigger.get('signal_family') == 'pullback-recovery'):
            value *= D('.5')
        return value

    def checkpoint(self):
        saved = super().checkpoint()
        saved['body']['recovery'] = dict(closes=list(map(str, self.recovery_closes)),
                                        lows=list(map(str, self.recovery_lows)))
        saved['sha256'] = meter.checksum(saved['body'])
        return saved

    @classmethod
    def restore(cls, saved):
        try:
            body = dict(saved['body'])
            if saved['sha256'] != meter.checksum(body):
                raise ValueError('digest')
            extra = body.pop('recovery')
            result = BASE.restore.__func__(cls, {'body': body, 'sha256': meter.checksum(body)})
            for key, maximum in [('closes', 360), ('lows', 6)]:
                values = [D(v) for v in extra[key]]
                expected = min(maximum, (result.last-alpha.campaign.ORIGIN)//FOUR_HOURS)
                if len(values) != expected or any(not v.is_finite() or v <= 0 for v in values):
                    raise ValueError('recovery chronology')
                setattr(result, 'recovery_'+key, deque(values, maxlen=maximum))
            return result
        except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
            raise Blocked('invalid pullback checkpoint') from exc


@contextmanager
def variant(binding, journal=None):
    with patch.object(alpha, 'AlphaCampaign', PullbackCampaign), alpha.variant(
            'incumbent', binding=binding, journal=journal):
        yield


def screen(market):
    """Standalone event study; reject weak hypotheses without an account replay.

    Next-bar fills are optimistic proxies. Macro competition, finite sessions,
    margin and native execution are absent; positive results require full replay.
    """
    import bisect
    from statistics import mean
    from coinquant.campaign import ORIGIN
    from research.rebuild import timestamp, START, END
    begin, end = timestamp(START), timestamp(END)
    model = PullbackCampaign()
    rows = []
    bars = sorted((stamp, values) for stamp, values in market.h4.items() if ORIGIN <= stamp < end)
    funding_times = [t for t, _ in market.funding]
    for index, (stamp, values) in enumerate(bars):
        open_, high, low, close = values[:4]
        model.update(stamp+FOUR_HOURS, high, low, close)
        trigger = model.trigger
        if (stamp+FOUR_HOURS < begin or not trigger or trigger['identity'] != stamp+FOUR_HOURS
                or trigger.get('signal_family') != 'pullback-recovery' or index+1 >= len(bars)):
            continue
        opportunity = model.model.active
        entered = bars[index+1][0]
        entry = bars[index+1][1][0]*D('1.0005')
        stop, take = opportunity.stop, opportunity.take
        if entry <= stop or entry >= take:
            continue
        exit_, ended, reason = None, None, 'expiry'
        for t, b in bars[index+1:index+15]:
            o, h, l, c = b[:4]
            # Adverse-first ordering when both barriers occur inside one bar.
            if o <= stop or l <= stop:
                exit_, ended, reason = min(o, stop)*D('.999'), t+FOUR_HOURS, 'stop_proxy'
                break
            if h >= take:
                exit_, ended, reason = take*D('.9995'), t+FOUR_HOURS, 'take_proxy'
                break
            exit_, ended = c*D('.9995'), t+FOUR_HOURS
        first = bisect.bisect_right(funding_times, entered)
        last = bisect.bisect_right(funding_times, ended)
        # Actual settled rates, paid on proxy mark notional rather than a fixed entry notional.
        funding = sum((rate*market.h4[t//FOUR_HOURS*FOUR_HOURS][0]/entry
                       for t, rate in market.funding[first:last]
                       if t//FOUR_HOURS*FOUR_HOURS in market.h4), D(0))
        net = exit_/entry*D('.99925')-D('1.00075')-funding
        rows.append(dict(signal_ms=trigger['identity'], entry_ms=entered, exit_ms=ended,
                         entry=str(entry), exit=str(exit_), net_return=str(net),
                         funding_return=str(funding), reason=reason))
    average = mean(float(r['net_return']) for r in rows) if rows else None
    return dict(candidate='pullback-recovery', signals=len(rows),
                mean_cost_and_funding_net_return=average,
                positive_fraction=sum(D(r['net_return']) > 0 for r in rows)/len(rows) if rows else None,
                survives_screen=len(rows) >= 10 and average is not None and average > 0,
                trades=rows, financial_account_complete=False,
                limitations=['Standalone 4h event study, not account CAGR/alpha/beta or acceptance.',
                             'Next-open proxy ignores session timing, macro competition, depth, rounding and margin.',
                             'Intrabar barriers use adverse-first ordering; funding uses proxy open marks.'])


def main(argv=None):
    import argparse
    import json
    from pathlib import Path
    from research.session_market import load_base
    from research.rebuild import source_identity
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screen', action='store_true', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.out.exists():
        parser.error('exclusive output required')
    market = load_base(Path('/tmp/coinquant-market'))
    report = dict(format='btc-pullback-recovery-screen-v1', source=source_identity(),
                  input_receipts=market.identity, screen=screen(market),
                  native_cases=0, prospective_alpha_proven=False)
    with args.out.open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
    result = report['screen']
    print(json.dumps({k:result[k] for k in ('candidate','signals','mean_cost_and_funding_net_return','survives_screen')}))


if __name__ == '__main__':
    main()
