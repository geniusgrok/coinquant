"""Registered three-candidate comparison. Refuses to rank mismatched accounts."""
import argparse
import hashlib
import json
from pathlib import Path

from research.rebuild import ROOT, source_identity


def compare(coin, star):
    if not coin.get('complete') or coin['source']['dirty'] or not star.get('baseline_reproduced'):
        raise ValueError('incomplete or dirty original account')
    cfg = star['candidate_configs']['baseline']
    dimensions = {
        'operation_schedule': ['795 frozen finite manual sessions', 'continuous minute replay'],
        'valuation': ['official mark with owner-accepted 29-minute bound', 'trade OHLC mark proxy'],
        'fills': ['IOC print-quantity upper bound', 'next-minute OHLC causal kernel'],
        'fees': [coin['fee'], str(cfg['taker'])],
        'slippage': [f"entry {coin['market_slippage']}, stop {coin['trigger_slippage']}",
                     f"base {cfg['slip_base']} plus impact {cfg['impact_y']}"],
        'latency': [f"read {coin['read_latency_ms']}ms/write {coin['latency_ms']}ms", 'next-minute fills; no REST latency'],
        'funding': ['official recorded calendar', '7305 official / 56 proxy / 1 zero'],
        'fx_conversion': [coin['fx'] + '; ' + coin['conversion'], 'prior published Frankfurter; 0.0035 each way'],
        'missing_input_policy': ['owner-accepted bounded mark gap', 'funding proxy/zero and OHLC mark proxy'],
    }
    rows = {'Coinquant-default': {'cagr': coin['cagr'], 'mdd': coin['mdd_envelope'],
                                  'config': {'primary_risk': coin['primary_risk'], 'schedule_sha256': coin['schedule_sha256']}}}
    for candidate in ('baseline', 'half-risk'):
        row = star['results'][candidate]['base']
        rows['Starquant-' + candidate] = {'cagr': row['cagr'], 'mdd': 1 - row['min_equity_over_peak'],
                                          'config': star['candidate_configs'][candidate]}
    blockers = [key for key, values in dimensions.items() if values[0] != values[1]]
    return {'candidates': rows, 'dimensions': dimensions, 'blockers': blockers,
            'comparable': not blockers, 'selected': None, 'ranking_permitted': not blockers,
            'target': {'cagr': 1.5, 'mdd_strictly_less_than': .5},
            'reference_schedule_sha256': coin['schedule_sha256'],
            'native_execution_verified': False, 'out_of_sample': False,
            'next_action': 'align each blocker, rerun full comparable accounts, then evaluate execution/maintenance'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--star', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.out.exists():
        parser.error('refusing to overwrite an existing comparison')
    coin_path = ROOT / 'evidence/remeasure-20260929-m10/M10-r75.json'
    blobs = [path.read_bytes() for path in (coin_path, args.star)]
    report = compare(*(json.loads(blob) for blob in blobs))
    report['originals'] = [{'name': path.name, 'sha256': hashlib.sha256(blob).hexdigest()}
                           for path, blob in zip((coin_path, args.star), blobs)]
    report['source'] = source_identity()
    if report['source']['dirty']:
        parser.error('commit source before saving evidence')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'comparable': report['comparable'], 'blockers': report['blockers']}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
