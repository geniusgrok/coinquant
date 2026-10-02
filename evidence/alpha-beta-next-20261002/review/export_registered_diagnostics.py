"""Export the complete64 identities from an accepted final report, without recomputation.

Financial/adoption review is external. This tool only preserves reported values;
it does not create an account, change selection, or establish native evidence.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assessment', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--spot-calibration', required=True, type=Path)
    parser.add_argument('--perp-calibration', required=True, type=Path)
    args = parser.parse_args()
    original = args.assessment.read_bytes()
    report = json.loads(original)
    if not (report['all_measured_accounts_valid'] is True and report['rules_freeze_ready'] is True
            and report['pending'] == [] and report['sensitivity_missing'] == []
            and report['registered_work_pending'] is False and report['risk_accounts_pending'] is False
            and report['native_cases'] == report['actual_account_days'] == 0
            and len(report['accounts']) == 60 and len(report['sensitivity']) == 4):
        raise ValueError('Complete accepted64 inventory with disclosed native-zero scope required')
    provenance = args.out.with_suffix('.provenance.json')
    for path in (args.out, provenance):
        if path.exists() or path.is_symlink() or path.resolve() != path.absolute():
            raise ValueError('New ordinary output path required: ' + str(path))
    calibration_inputs = {'spot': args.spot_calibration, 'perp': args.perp_calibration}
    calibration_bytes, calibrations = {}, {}
    for kind, path in calibration_inputs.items():
        calibration_bytes[kind] = path.read_bytes()
        if hashlib.sha256(calibration_bytes[kind]).hexdigest() != report['risk_calibrations'][kind]['raw_sha256']:
            raise ValueError('Actual calibration raw differs from final report: ' + kind)
        calibrations[kind] = json.loads(calibration_bytes[kind])
    rows = []

    def append(identity, account, capital, offset, kind, risk=False):
        if account['valid'] is not True or account['rejections']:
            raise ValueError('Invalid account cannot be exported: ' + identity)
        summary = account['financial']
        validation = summary['validation_2022_plus']
        matching = report['risk'][kind].get(account['candidate'], {}) if risk else {}
        profile = calibrations[kind]['profiles'][account['candidate']] if risk else {}
        rows.append([identity, capital, offset, account['cagr'], account['mdd'],
                     summary['metrics']['daily_mdd'], summary.get('fees_usdt'), summary.get('funding_paid_usdt'),
                     validation['regression']['beta_btc'], validation['usdt']['daily_volatility_annualized'],
                     profile.get('scale'), matching.get('achieved_match'), matching.get('validation_total_usdt_return_gain'),
                     account['raw_bundle_sha256'], report['risk_calibrations'][kind]['raw_sha256'] if risk else None])

    for identity, account in report['accounts'].items():
        append(identity, account, '10000', 0, identity.split('/')[0], risk='/risk/' in identity)
    for entry in report['sensitivity']:
        identity = 'perp/sensitivity/' + entry['candidate'] + '/' + entry['initial_cny'] + '/' + str(entry['start_offset_ms'])
        append(identity, entry['account'], entry['initial_cny'], entry['start_offset_ms'], 'perp')
    if len(rows) != 64 or len({row[0] for row in rows}) != 64:
        raise ValueError('Exactly64 unique identities required')
    with args.out.open('x', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['account', 'initial_cny', 'start_offset_ms', 'registered_cny_cagr', 'continuous_proxy_mdd',
                         'daily_closing_mdd', 'fees_usdt', 'funding_paid_usdt', 'validation_2022_plus_btc_beta',
                         'validation_2022_plus_usdt_annualized_volatility', 'fixed_training_new_entry_scale',
                         'achieved_upper_risk_band_match', 'validation_cumulative_usdt_return_difference',
                         'actual_raw_bundle_sha256', 'actual_risk_calibration_sha256'])
        writer.writerows(rows)
    if args.assessment.read_bytes() != original:
        raise ValueError('Assessment changed during export; no provenance published')
    for kind, path in calibration_inputs.items():
        if path.read_bytes() != calibration_bytes[kind]:
            raise ValueError('Calibration changed during export; no provenance published: ' + kind)
    with provenance.open('x') as stream:
        json.dump({'assessment_sha256': hashlib.sha256(original).hexdigest(), 'account_count': 64,
                   'csv_sha256': hashlib.sha256(args.out.read_bytes()).hexdigest(),
                   'tool_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                   'actual_calibration_sha256': {kind: hashlib.sha256(data).hexdigest() for kind, data in calibration_bytes.items()},
                   'interpretation': 'Reported values only. Return/MDD/volatility/differences are fractions, not percentages. Coin registered CAGR uses365.2425days; Spot and descriptive daily annualization365.25. Risk match is an upper band, not exact equality. No prospective-alpha/native/adoption approval.'},
                  stream, indent=2)
        stream.write('\n')


if __name__ == '__main__':
    main()
