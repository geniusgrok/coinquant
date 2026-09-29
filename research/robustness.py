"""Overfitting audit over the frozen session schedule (protocol section O1).

Each candidate is a set of research knobs. Every candidate runs the production session
runner through `research.rebuild.trial` on the whole window and on fresh CNY 10,000 blocks
(one per calendar year). Nothing here reaches a live reader.

    python3 -m research.robustness run [--jobs 4] [--only NAME ...]
    python3 -m research.robustness report
"""
import argparse
import hashlib
import json
import math
import subprocess
import sys
import threading
from datetime import date, timedelta
from pathlib import Path
from queue import Queue
from statistics import NormalDist

from research import rebuild

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'evidence' / 'robustness-20260929'
SCRATCH = Path('/tmp/cq-robust')
BLOCKS = {
    'Y2020': ('2020-01-01T00:00:00Z', '2021-01-01T00:00:00Z'),
    'Y2021': ('2021-01-01T00:00:00Z', '2022-01-01T00:00:00Z'),
    'Y2022': ('2022-01-01T00:00:00Z', '2023-01-01T00:00:00Z'),
    'Y2023': ('2023-01-01T00:00:00Z', '2024-01-01T00:00:00Z'),
    'Y2024': ('2024-01-01T00:00:00Z', '2025-01-01T00:00:00Z'),
    'Y2025': ('2025-01-01T00:00:00Z', '2026-01-01T00:00:00Z'),
    'Y2026': ('2026-01-01T00:00:00Z', rebuild.END),
}
SPLITS = {'A': (('Y2020', 'Y2021', 'Y2022', 'Y2023'), ('Y2024', 'Y2025', 'Y2026')),
          'B': (('Y2020', 'Y2021', 'Y2022'), ('Y2023', 'Y2024', 'Y2025', 'Y2026'))}
MDD_BUFFER = 0.40
ADOPT_RATIO = 1.10
REGISTERED_BEFORE = 66

BASE = {}
NEIGHBOURS = {
    'imp2.5': {'impulse_atr': '2.5'}, 'imp3.5': {'impulse_atr': '3.5'},
    'atr10': {'atr_bars': '10'}, 'atr20': {'atr_bars': '20'},
    'life28': {'life_bars': '28'}, 'life56': {'life_bars': '56'},
    'ret0.4': {'retrace': '0.4'}, 'ret0.6': {'retrace': '0.6'},
    'take10': {'take_power': '10'}, 'take40': {'take_power': '40'},
    'dfii0.15': {'dfii_drop': '0.15'}, 'dfii0.35': {'dfii_drop': '0.35'},
    'macro0': {'macro_risk': '0.001'}, 'macro1.8': {'macro_risk': '1.8'},
    'risk3.6': {'primary_risk': '3.6'}, 'risk5': {'primary_risk': '5'}, 'risk6': {'primary_risk': '6'},
}
EXECUTION = {f'O0-w{limit}': {'weight_limit': str(limit)} for limit in (2000, 2100, 2300, 2400)}
CANDIDATES = {'base': BASE, **NEIGHBOURS}
STRESS = {'fee150': ['--fee', '0.001125'],
          'slip2': ['--trigger-slippage', '0.002', '--market-slippage', '0.001'],
          'part10': ['--participation', '0.1'], 'skip': ['--sequence', 'random_skip'],
          'absence': ['--sequence', 'absence'], 'block': ['--sequence', 'block_21d']}
YEARS = (date(2026, 9, 20) - date(2020, 1, 1)).days / 365.2425
FAMILIES = {'impulse_atr': ('imp2.5', 'imp3.5'), 'atr_bars': ('atr10', 'atr20'), 'life_bars': ('life28', 'life56'),
            'retrace': ('ret0.4', 'ret0.6'), 'take_power': ('take10', 'take40'),
            'dfii_drop': ('dfii0.15', 'dfii0.35'), 'macro_risk': ('macro0', 'macro1.8')}
RISKS = (('risk3.6', '3.6'), ('risk5', '5'), ('risk6', '6'), ('base', '7.5'))


def jobs_for(candidates=None, blocks=None):
    names = candidates or list(CANDIDATES)
    return [(name, block) for name in names
            for block in (['full'] if name in EXECUTION else ['full'] + list(BLOCKS)) if blocks is None or block in blocks]


def job_command(candidate, block, knobs, uid):
    name = f'{candidate}-{block}'
    command = [sys.executable, '-m', 'research.rebuild', name, '--out', str(SCRATCH), '--uid', str(uid)]
    for key, value in knobs.items():
        command += ['--knob', f'{key}={value}']
    if block in STRESS:
        command += STRESS[block]
    elif block != 'full':
        start, end = BLOCKS[block]
        command += ['--from', start, '--until', end]
    return name, command


def run_jobs(jobs, workers, knobs_of=CANDIDATES):
    SCRATCH.mkdir(parents=True, exist_ok=True)
    slots = Queue()
    for uid in range(101, 101 + workers):
        slots.put(uid)
    todo = Queue()
    for job in jobs:
        todo.put(job)
    failures = []

    def work():
        while True:
            try:
                candidate, block = todo.get_nowait()
            except Exception:
                return
            name, command = job_command(candidate, block, knobs_of[candidate], 0)
            if (SCRATCH / f'{name}.json').exists():
                continue
            uid = slots.get()
            try:
                command[command.index('--uid') + 1] = str(uid)
                done = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
                if done.returncode:
                    failures.append((name, done.stderr[-2000:]))
                else:
                    print('done', name, flush=True)
            finally:
                slots.put(uid)

    threads = [threading.Thread(target=work) for _ in range(workers)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return failures


def _daily(result):
    return [(date.fromisoformat(day), float(value)) for day, value in result['daily_close_cny']]


def year_returns(result):
    rows = _daily(result)
    out, previous = {}, 10000.0
    for year in sorted({day.year for day, _ in rows}):
        last = [value for day, value in rows if day.year == year][-1]
        out[str(year)] = last / previous - 1
        previous = last
    return out


def month_concentration(result):
    """CAGR after removing the best k calendar months from the log growth."""
    rows = _daily(result)
    months, previous, logs = {}, 10000.0, []
    for day, value in rows:
        months[(day.year, day.month)] = value
    for key in sorted(months):
        logs.append(math.log(months[key] / previous))
        previous = months[key]
    total = sum(logs)
    years = (date(2026, 9, 20) - date(2020, 1, 1)).days / 365.2425
    best = sorted(logs, reverse=True)
    return {f'without_best_{k}': math.exp((total - sum(best[:k])) / years) - 1 for k in (1, 3, 5)}


def weekly_log_returns(result):
    rows = _daily(result)
    days = [day for day, _ in rows]
    values = [value for _, value in rows]

    def at(target):
        low, high = 0, len(days)
        while low < high:
            middle = (low + high) // 2
            if days[middle] <= target:
                low = middle + 1
            else:
                high = middle
        return values[low - 1] if low else 10000.0
    out, day = [], date(2020, 1, 5)
    previous = at(date(2020, 1, 1))
    while day <= date(2026, 9, 19):
        current = at(day)
        out.append(math.log(current / previous))
        previous = current
        day += timedelta(days=7)
    return out


def moments(values):
    n = len(values)
    mean = sum(values) / n
    var = sum((v - mean) ** 2 for v in values) / n
    sd = math.sqrt(var)
    skew = sum((v - mean) ** 3 for v in values) / n / sd ** 3
    kurt = sum((v - mean) ** 4 for v in values) / n / sd ** 4
    return mean, sd, skew, kurt, n


def deflated_sharpe(weekly, trial_sharpes, trials):
    """Bailey and Lopez de Prado deflated Sharpe ratio, per-period units."""
    mean, sd, skew, kurt, n = moments(weekly)
    sharpe = mean / sd
    normal = NormalDist()
    variance = sum((s - sum(trial_sharpes) / len(trial_sharpes)) ** 2 for s in trial_sharpes) / len(trial_sharpes)
    gamma = 0.5772156649
    threshold = math.sqrt(variance) * ((1 - gamma) * normal.inv_cdf(1 - 1 / trials)
                                       + gamma * normal.inv_cdf(1 - 1 / (trials * math.e)))
    denominator = math.sqrt(1 - skew * sharpe + (kurt - 1) / 4 * sharpe ** 2)
    return dict(weekly_sharpe=sharpe, annual_sharpe=sharpe * math.sqrt(52), weekly_threshold=threshold,
                annual_threshold=threshold * math.sqrt(52), probability=normal.cdf((sharpe - threshold) * math.sqrt(n - 1) / denominator))


def summarize(path):
    raw = path.read_bytes()
    result = json.loads(raw)
    summary = dict(
        final_cny=float(result['final_cny']), cagr=result['cagr'], mdd_envelope=float(result['mdd_envelope']),
        mdd_close=float(result['mdd_close']), fills=result['funnel'].get('ioc_filled'),
        protections=result['funnel'].get('protections'), triggers=result['funnel'].get('triggers'),
        liquidations=result['funnel'].get('liquidations'), known_path=result['known_path'],
        execution_unresolved=result['execution_unresolved'], sessions=result['sessions_executed'],
        complete=result['complete'], window=[result['window_start'], result['window_end']],
        knobs={k: result[k] for k in rebuild.KNOBS}, source=result['source'],
        result_sha256=hashlib.sha256(raw).hexdigest(), result_bytes=len(raw))
    if (result['window_start'], result['window_end']) == (rebuild.START, rebuild.END):
        summary['year_returns'] = year_returns(result)
        summary['concentration'] = month_concentration(result)
        summary['weekly'] = weekly_log_returns(result)
    return summary


def collect(candidates=None):
    table = {}
    for name in candidates or list(CANDIDATES) + list(EXECUTION):
        row = {}
        for block in ['full'] + list(BLOCKS) + list(STRESS):
            path = SCRATCH / f'{name}-{block}.json'
            if path.exists():
                row[block] = summarize(path)
        if row:
            table[name] = row
    return table


def growth(row, blocks):
    values = [row[b]['final_cny'] / 10000 for b in blocks]
    return math.exp(sum(math.log(v) for v in values) / len(values))


def noise_ratio(table):
    """Per-year growth equivalent of the full-window spread caused by the read-budget knob alone."""
    finals = [table[name]['full']['final_cny'] for name in ['base', *EXECUTION] if name in table and 'full' in table[name]]
    return (max(finals) / min(finals)) ** (1 / YEARS) if len(finals) > 1 else 1.0


def analyse(table):
    base = table['base']
    ratio = max(ADOPT_RATIO, noise_ratio(table))
    verdict = dict(splits={}, families={}, risks={}, adopt_ratio=ratio, noise_ratio=noise_ratio(table))
    for label, (dev, test) in SPLITS.items():
        verdict['splits'][label] = dict(dev=list(dev), test=list(test))
    for name, row in table.items():
        if not all(block in row for block in BLOCKS):
            continue
        entry = {}
        for label, (dev, test) in SPLITS.items():
            entry[label] = dict(dev_growth=growth(row, dev), test_growth=growth(row, test),
                                dev_worst_mdd=max(row[b]['mdd_envelope'] for b in dev),
                                test_worst_mdd=max(row[b]['mdd_envelope'] for b in test),
                                dev_ratio_to_base=growth(row, dev) / growth(base, dev))
        entry['blocks'] = {b: dict(ret=row[b]['final_cny'] / 10000 - 1, mdd=row[b]['mdd_envelope']) for b in BLOCKS}
        if 'full' in row:
            entry['full'] = {k: row['full'][k] for k in ('final_cny', 'cagr', 'mdd_envelope', 'fills')}
        verdict['families'][name] = entry
    adopted = []
    for family, names in FAMILIES.items():
        for name in names:
            entry = verdict['families'].get(name)
            if entry and all(entry[s]['dev_ratio_to_base'] >= ratio and entry[s]['dev_worst_mdd'] < 0.5
                             for s in SPLITS):
                adopted.append((family, name, entry['A']['dev_ratio_to_base']))
    verdict['adopted_changes'] = adopted
    chosen = None
    for name, risk in RISKS:
        entry = verdict['families'].get(name)
        if entry is None:
            continue
        ok = all(entry[s]['dev_worst_mdd'] <= MDD_BUFFER for s in SPLITS)
        verdict['risks'][risk] = dict(candidate=name, dev_worst_mdd_A=entry['A']['dev_worst_mdd'], buffer_ok=ok)
        if ok:
            chosen = risk
    verdict['risk_by_buffer_rule'] = chosen
    return verdict


def deflation(table):
    sharpes = []
    for row in table.values():
        if 'full' in row and 'weekly' in row['full']:
            mean, sd, *_ = moments(row['full']['weekly'])
            sharpes.append(mean / sd)
    trials = REGISTERED_BEFORE + len(sharpes)
    return {name: deflated_sharpe(row['full']['weekly'], sharpes, trials)
            for name, row in table.items() if 'full' in row and 'weekly' in row['full']}, trials


def main():
    parser = argparse.ArgumentParser(description='Overfitting audit trials and report')
    parser.add_argument('command', choices=('run', 'report'))
    parser.add_argument('--jobs', type=int, default=4)
    parser.add_argument('--only', nargs='*', default=None)
    parser.add_argument('--blocks', nargs='*', default=None, help="subset of 'full', block and stress names")
    parser.add_argument('--extra', default='{}', help='JSON object of additional candidates {name: {knob: value}}')
    args = parser.parse_args()
    extra = json.loads(args.extra)
    CANDIDATES.update(extra)
    if args.command == 'run':
        CANDIDATES.update(EXECUTION)
        failures = run_jobs(jobs_for(args.only, args.blocks), args.jobs)
        for name, message in failures:
            print('FAILED', name, message)
        raise SystemExit(1 if failures else 0)
    table = collect()
    analysis = analyse(table)
    deflated, trials = deflation(table)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    for row in table.values():
        for block in row.values():
            block.pop('weekly', None)
    payload = dict(analysis=analysis, deflated_sharpe=deflated, trials_counted=trials, extra=extra, table=table)
    (EVIDENCE / 'analysis.json').write_text(json.dumps(payload, indent=1, default=str) + '\n')
    print(json.dumps(analysis, indent=1, default=str))


if __name__ == '__main__':
    main()
