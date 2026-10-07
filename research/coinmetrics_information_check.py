"""Single conditional information/cost screen after the frozen support gate.

Outputs aggregates only. Four-hour close and funding are diagnostic proxies;
native stops, executable fills, wallet interactions and PIT are not claimed.
"""
import argparse
from decimal import Decimal as D
import json
from pathlib import Path
from statistics import median

from research.coinmetrics_source_check import coinmetrics
from research.coinmetrics_supply_screen import (
    DAY, FOUR_HOURS, LATER_PERIOD, SEVEN_DAYS, candidates, completed_price, original_macro)


ROUND_TRIP_FEE = D('0.0015')  # original 7.5 bp each side


def outcome(item, closes, funding):
    start = item['start']
    first = closes[(start // FOUR_HOURS) * FOUR_HOURS]
    final = closes[((start + SEVEN_DAYS) // FOUR_HOURS) * FOUR_HOURS]
    # The archived feature's observation_ms is the venue settlement clock;
    # available_ms is an eight-hour research publication delay, not cashflow time.
    rates = [D(row['value']) for row in funding if start < row['observation_ms'] <= start + SEVEN_DAYS]
    if len(rates) < 19 or len(rates) > 22:
        raise ValueError('incomplete original seven-day funding interval')
    gross = final / first - 1
    paid = sum(rates, D(0))
    return dict(gross=gross, signed_funding=paid, funding_events=len(rates),
                net=gross - paid - ROUND_TRIP_FEE,
                doubled_fee_net=gross - paid - 2 * ROUND_TRIP_FEE)


def mean(values):
    return sum(values, D(0)) / len(values)


def es5(values):
    return mean(sorted(values)[:max(1, (len(values) + 19) // 20)])


def aggregate(pairs, closes, funding, intervals):
    result = {}
    for label, cohort in [('all', pairs),
                          ('development', [p for p in pairs if p[0]['start'] < LATER_PERIOD]),
                          ('later', [p for p in pairs if p[0]['start'] >= LATER_PERIOD])]:
        if not cohort:
            raise ValueError('empty chronological period')
        events = [outcome(event, closes, funding) for event, _ in cohort]
        controls = [outcome(control, closes, funding) for _, control in cohort]
        e = [x['doubled_fee_net'] for x in events]
        c = [x['doubled_fee_net'] for x in controls]
        delta = [a - b for a, b in zip(e, c)]
        next_entries = [r for event, _ in cohort for r in intervals
                        if event['start'] < r['first_ms'] < event['start'] + SEVEN_DAYS]
        balance = dict(paired_median_abs_btc_3d_gap_pp=str(
                           median(abs(a['btc_3d_return'] - b['btc_3d_return']) for a, b in cohort) * 100),
                       paired_median_abs_btc_20d_rms_gap_pp=str(
                           median(abs(a['btc_20d_rms'] - b['btc_20d_rms']) for a, b in cohort) * 100),
                       paired_median_abs_usdt_price_gap_bp=str(
                           median(abs(a['source_price'] - b['source_price']) for a, b in cohort) * 10000))
        result[label] = dict(pairs=len(cohort),
                             pre_start_match_balance=balance,
                             event_mean_gross_pct=str(mean([x['gross'] for x in events]) * 100),
                             event_mean_signed_funding_pct=str(mean([x['signed_funding'] for x in events]) * 100),
                             event_mean_original_fee_net_pct=str(mean([x['net'] for x in events]) * 100),
                             event_mean_doubled_fee_net_pct=str(mean(e) * 100),
                             event_median_doubled_fee_net_pct=str(median(e) * 100),
                             control_mean_doubled_fee_net_pct=str(mean(c) * 100),
                             control_median_doubled_fee_net_pct=str(median(c) * 100),
                             paired_mean_doubled_fee_delta_pp=str(mean(delta) * 100),
                             event_es5_doubled_fee_pct=str(es5(e) * 100),
                             control_es5_doubled_fee_pct=str(es5(c) * 100),
                             event_profitable_after_doubled_fee=sum(x > 0 for x in e),
                             funding_events_min=min(x['funding_events'] for x in events + controls),
                             funding_events_max=max(x['funding_events'] for x in events + controls),
                             next_original_entries_within_seven_days=len(next_entries),
                             next_original_winning_entries_within_seven_days=sum(D(r['net_usdt']) > 0
                                                                                  for r in next_entries))
    result['frozen_information_gate_pass'] = all(
        D(result[period]['event_mean_doubled_fee_net_pct']) > 0 and
        D(result[period]['event_median_doubled_fee_net_pct']) > 0 and
        D(result[period]['paired_mean_doubled_fee_delta_pp']) > 0 and
        D(result[period]['event_es5_doubled_fee_pct']) >= D(result[period]['control_es5_doubled_fee_pct'])
        for period in ('development', 'later'))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('coinmetrics_raw')
    parser.add_argument('coinmetrics_receipt')
    parser.add_argument('original_schedule')
    parser.add_argument('verified_first_fills')
    parser.add_argument('terminal_reports')
    parser.add_argument('original_um_four_hour_directory')
    parser.add_argument('original_dfii_history_loader')
    parser.add_argument('original_alfred_archive_root')
    parser.add_argument('original_market_features')
    args = parser.parse_args()
    cm = coinmetrics(Path(args.coinmetrics_raw).read_bytes(),
                     json.loads(Path(args.coinmetrics_receipt).read_text()))
    starts = json.loads(Path(args.original_schedule).read_text())['primary']['starts_ms']
    intervals = json.loads(Path(args.verified_first_fills).read_text())
    reports = [json.loads(line) for line in open(args.terminal_reports, encoding='utf-8')]
    if len(starts) != 795 or len(intervals) != 50 or [r['start_ms'] for r in reports] != starts:
        raise ValueError('wrong original account path')
    price, closes = completed_price(args.original_um_four_hour_directory, starts)
    macro = original_macro(args.original_dfii_history_loader, args.original_alfred_archive_root, starts)
    support, _, _, pairs = candidates(cm, starts, reports, intervals, price, macro)
    if not support['support_gate_pass']:
        raise ValueError('frozen pre-outcome support gate did not pass')
    funding = json.loads(Path(args.original_market_features).read_text())['funding']
    answer = aggregate(pairs, closes, funding, intervals)
    print(json.dumps(dict(source_id='coinmetrics_community_usdt_capest_price_v1',
                          historical_pit=False, support=support, information=answer), sort_keys=True))


if __name__ == '__main__':
    main()
