"""One small fixed campaign screen; no new history/account/network calls."""
import argparse
from decimal import Decimal as D
import gzip
import hashlib
import json
from pathlib import Path
import time

from research.lifecycle import SPEC, coin_campaigns, spot_campaigns, debt_screen, serial


def bound(path, sha):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != sha:
        raise ValueError('immutable lifecycle input changed')
    return raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('preserve prior lifecycle screen')
    began = time.monotonic()
    spec = json.loads(SPEC.read_text())
    packet = json.loads(bound(spec['daily_packet'], spec['daily_sha256']))
    bars = [(int(t)+86400000+60000, D(v['close'])) for t, v in
            sorted(packet['bars'].items(), key=lambda item: int(item[0]))]
    results = {}
    for kind, selector in (('coin', coin_campaigns), ('spot', spot_campaigns)):
        source = spec['projections'][kind]
        ledger = json.loads(gzip.decompress(bound(source['path'], source['sha256'])))
        if ledger['audit']['passed'] is not True:
            raise ValueError('owned ledger audit failed')
        campaigns = selector(ledger, bars)
        results[kind] = dict(original_strategy=ledger['parent_binding'],
            campaign_debt=debt_screen(campaigns, bars, spec['cutoff_ms']),
            earned_profit_giveback=dict(status='BLOCKED_INPUT', account_entrant=False,
                reason='Pinned projection does not export causal accepted initial protective installation receipt. Do not use write_attempt or ATR reconstruction as installed R.',
                policies=['giveback-half', 'giveback-full']),
            actual_cohorts=len(campaigns), actual_closed_cohorts=sum(c['fully_closed'] for c in campaigns),
            fully_settled_cash=sum((c['gain'] for c in campaigns if c['fully_closed']), D(0)))
    out = dict(format='btc-owned-lifecycle-screen-v1',
        registered_spec_sha256=hashlib.sha256(SPEC.read_bytes()).hexdigest(),
        screening_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        mechanism_source_sha256=hashlib.sha256(SPEC.with_name('lifecycle.py').read_bytes()).hexdigest(),
        daily_sha256=spec['daily_sha256'], projection_bindings=spec['projections'],
        price_time_rule='Completed UTC daily close becomes causally available at end+60sec; neither current day nor fill partial day enters owned-close peak.',
        results=results, elapsed_seconds=time.monotonic()-began, original795_replays=0,
        independently_financed_new_wallets=0, prospective_alpha_proven=False,
        default_changed=False, qualification='NOT_QUALIFIED')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x') as stream:
        stream.write(json.dumps(serial(out), indent=2)+'\n')
    print(json.dumps(serial(dict(elapsed_seconds=out['elapsed_seconds'], results={
        k:{p:dict(status=v['status'], eras=v['eras']) for p,v in r['campaign_debt'].items()}
        for k,r in results.items()})), indent=2))


if __name__ == '__main__':
    main()
