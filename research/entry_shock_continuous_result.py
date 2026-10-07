"""Read-only aggregate check of the frozen original/defer wallet pair.

Receipts and private journals are local arguments. Output contains no order
identifiers, account paths, exact session times, or raw wallet balances.
"""
import argparse
from collections import Counter, defaultdict
from datetime import date
import gzip
import json
import math


def read(path):
    opener = gzip.open if str(path).endswith('.gz') else open
    with opener(path, 'rt') as stream:
        return json.load(stream)


def journal(receipt):
    with open(receipt['reports']['path']) as stream:
        return [json.loads(line) for line in stream]


def percent(number):
    return round(number * 100, 4)


def metrics(financial):
    daily = financial['daily']
    cny = [float(row['equity_cny']) for row in daily]
    usdt = [float(row['equity_usdt']) for row in daily]
    if min(cny + usdt) <= 0 or len(daily) != 2455:
        raise ValueError('finite complete daily equity path required')

    def es5(values):
        returns = sorted(after / before - 1 for before, after in zip(values, values[1:]))
        count = math.ceil(len(returns) * .05)
        return -sum(returns[:count]) / count

    year_rows = defaultdict(list)
    for row in daily:
        year_rows[row['date'][:4]].append(row)
    previous = float(year_rows['2019'][-1]['equity_cny'])
    annual = {}
    for year, rows in sorted(year_rows.items()):
        if year == '2019':
            continue
        last = float(rows[-1]['equity_cny'])
        annual[year] = percent(last / previous - 1)
        previous = last

    exposure = [float(row['gross_btc_exposure_usdt']) / float(row['equity_usdt'])
                for row in daily]
    held = [value for value in exposure if value > 0]
    turnover = sum(float(trade['qty']) * float(trade['price'])
                   for trade in financial['trades'])
    years = (date(2026, 9, 20) - date(2020, 1, 1)).days / 365.25
    return dict(cagr_pct=percent((float(financial['final_cny']) / 10000) ** (1 / years) - 1),
                mdd_pct=percent(float(financial['mdd'])),
                daily_es5_cny_pct=percent(es5(cny)),
                daily_es5_usdt_pct=percent(es5(usdt)),
                terminal_cny=float(financial['final_cny']),
                fees=float(financial['fees']), funding=float(financial['funding']),
                trades=len(financial['trades']), turnover=turnover,
                held_days=len(held),
                mean_gross_exposure_to_equity=round(sum(exposure) / len(exposure), 4),
                max_gross_exposure_to_equity=round(max(exposure), 4),
                annual_cny_return_pct=annual)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--original', required=True)
    parser.add_argument('--baseline', required=True)
    parser.add_argument('--candidate', required=True)
    args = parser.parse_args()
    old, base, candidate = map(read, (args.original, args.baseline, args.candidate))
    if not all(row['complete'] and row['session_count'] == 795 and row['no_live_account'] and
               row['financial']['audit']['passed'] and row['financial']['known_path'] and
               not row['native_verified'] for row in (old, base, candidate)):
        raise ValueError('complete audited offline receipts required')
    financial_fields = ('wallet_usdt', 'quantity_btc', 'position', 'entry', 'margin',
                        'fees', 'funding', 'final_mark', 'final_usdt', 'final_cny',
                        'mdd', 'mdd_close', 'peak_cny', 'peak_envelope_cny',
                        'known_path', 'unknown_from', 'hindsight_bounded', 'funnel',
                        'trades', 'funding_ledger', 'daily', 'daily_cny',
                        'loaded_minute_files', 'loaded_print_files', 'audit')
    if any(old['financial'][key] != base['financial'][key] for key in financial_fields):
        raise ValueError('fresh baseline does not reproduce archived full account')
    bound = ('schedule_sha256', 'fx_sha256', 'market_identity_sha256',
             'market_values_sha256', 'macro_sha256', 'parser_sha256',
             'qualified_metadata_sha256')
    if (any(base['inputs'][key] != candidate['inputs'][key] for key in bound) or
        any(base['financial'][key] != candidate['financial'][key]
            for key in ('loaded_minute_files', 'loaded_print_files'))):
        raise ValueError('paired inputs or actually used market file versions differ')
    left, right = journal(base), journal(candidate)
    if len(left) != 795 or len(right) != 795 or left[:26] != right[:26]:
        raise ValueError('pre-decision prefix or journal count changed')
    first_difference = next((index + 1 for index, pair in enumerate(zip(left, right))
                             if pair[0] != pair[1]), None)
    if first_difference != 27:
        raise ValueError('unexpected first decision divergence')
    baseline, proposed = metrics(base['financial']), metrics(candidate['financial'])
    if (baseline['cagr_pct'] >= 150 or baseline['mdd_pct'] >= 50):
        raise ValueError('archived economic reference changed')
    status = Counter((a['status'], b['status']) for a, b in zip(left, right))
    outcome = dict(
        full_baseline_reproduced=True, verified_financial_fields=len(financial_fields),
        paired_input_versions_equal=True, shared_report_prefix=26,
        first_changed_session_ordinal=first_difference,
        executed_only_by_baseline=status['executed', 'no_action'],
        executed_only_by_candidate=status['no_action', 'executed'],
        baseline={key: value for key, value in baseline.items()
                  if key not in ('terminal_cny', 'fees', 'funding', 'turnover')},
        candidate={key: value for key, value in proposed.items()
                   if key not in ('terminal_cny', 'fees', 'funding', 'turnover')},
        paired_delta=dict(
            terminal_wealth_pct=percent(proposed['terminal_cny'] / baseline['terminal_cny'] - 1),
            cagr_pp=round(proposed['cagr_pct'] - baseline['cagr_pct'], 4),
            mdd_pp=percent(float(candidate['financial']['mdd']) -
                           float(base['financial']['mdd'])),
            daily_es5_cny_pp=round(proposed['daily_es5_cny_pct'] - baseline['daily_es5_cny_pct'], 4),
            trades=proposed['trades'] - baseline['trades'],
            turnover_pct=percent(proposed['turnover'] / baseline['turnover'] - 1),
            fees_pct=percent(proposed['fees'] / baseline['fees'] - 1),
            funding_pct=percent(proposed['funding'] / baseline['funding'] - 1),
            held_days=proposed['held_days'] - baseline['held_days']),
        replacement_route_one=bool(proposed['cagr_pct'] >= 1.10 * baseline['cagr_pct']
                                   and proposed['mdd_pct'] <= baseline['mdd_pct']),
        replacement_route_two=bool(proposed['cagr_pct'] >= .95 * baseline['cagr_pct']
                                   and proposed['mdd_pct'] <= .80 * baseline['mdd_pct']),
        original_150_50_target=bool(proposed['cagr_pct'] >= 150 and proposed['mdd_pct'] < 50),
        native_verified=False)
    print(json.dumps(outcome, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
