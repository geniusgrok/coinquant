"""One-shot Spot-only training and actual risk replay; no partial final assessment."""
import gc
import sys
from pathlib import Path

REVIEW = Path('/workspace/btc-alpha-beta-next/review')
sys.path.insert(0, str(REVIEW))
import run_registered_followthrough_project_calibration as queue

def main():
    import time
    while not queue.SINGLES['spot'].exists() or Path('/proc/21624').exists():
        time.sleep(10)
    queue.source(queue.ANALYSIS)
    sys.path.insert(0, str(queue.ANALYSIS))
    from research import alpha_assessment as a
    current = a.source_identity()
    schedule = queue.ROOT/'coinquant/research/session_schedule.json'
    fx_path = queue.ROOT/'starquant/data/usdcny_frankfurter.json'
    market = Path('/tmp/spotquant-market/klines')
    env = a.environment(schedule, fx_path, market)
    bars = a.load_daily(market, a.END_MS, require_through=a.END_MS)
    fx = a.PriorFX(fx_path)
    usd, cny = a.market_returns_for(bars, fx)
    expected = {n+'/'+s for n in a.SPEC['spot_candidates'] for s in a.SPEC['spot_scenarios']}
    bundle = a.consume(queue.SINGLES['spot'], 'spot', env, bars, fx, usd, cny, expected=expected)
    equivalence = a.verify_execution_equivalence(bundle['metadata']['source'], current, 'spot',
                     env['spec_sha256'], env['protocol_sha256'])
    baseline = a.original_baseline(queue.ROOT/'spotquant/evidence/complete-delivery-20261001/spot-consensus-corrected.json',
                                   'spot', bundle, env)
    a.require(baseline['passed'], 'Original baseline mismatch; no early actual risk replay')
    document, training = a.calibration_document({'spot': bundle}, usd, fx)
    a.write_new(queue.SPOT_CAL, document)
    queue.write(queue.OUT/'spot-project-calibration-proof.json', {
        'scope': 'Spot only; full48 final assessment remains pending',
        'analysis_source': current, 'analysis_execution_equivalence_sha256': equivalence,
        'inputs': {k:v for k,v in bundle.items() if k!='accounts'},
        'original_baseline_verification': baseline, 'training': training,
        'calibration_sha256': queue.sha(queue.SPOT_CAL), 'profiles': sorted(document['profiles']),
        'native_cases': 0, 'actual_account_days': 0,
        'source_rule': 'Final unified assessment must independently verify this exact deterministic project subset.'})
    del bundle, bars, usd, cny
    gc.collect()
    queue.source(queue.ANALYSIS)
    path = queue.risk('spot', calibration=queue.SPOT_CAL, label_prefix='risk-spot-project-early')
    queue.write(queue.EARLY_SPOT_DONE, {'actual_risk_path': str(path) if path else None,
        'actual_risk_sha256': queue.sha(path) if path else None,
        'actual_calibration_path': str(queue.SPOT_CAL), 'actual_calibration_sha256': queue.sha(queue.SPOT_CAL),
        'scope': 'Actual Spot risk replays only; unified final assessment and independent review pending'})

if __name__ == '__main__':
    main()
