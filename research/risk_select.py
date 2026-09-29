"""R3: reselect PRIMARY_RISK under the rule registered in research/redesign-PROTOCOL.md.

Jobs are run with `python -m research.robustness run --only m8r6 ... --extra ...`; this module
only reads their results and applies the registered rule.
"""
import argparse
import json

from research import robustness
from research.robustness import BLOCKS, EVIDENCE, SCRATCH, SPLITS, growth, summarize

CANDIDATES = ('6', '6.5', '7', '7.5')
BUFFER = 0.45
HARD_MDD = 0.5


def name_of(risk):
    return f'm8r{risk}'


def neighbours(risk, grid=CANDIDATES):
    index = grid.index(risk)
    return [grid[i] for i in (index - 1, index + 1) if 0 <= i < len(grid)]


def evaluate(row):
    """Per-split development buffer and test growth for one candidate's block results."""
    entry = {}
    for label, (dev, test) in SPLITS.items():
        entry[label] = dict(dev_growth=growth(row, dev), test_growth=growth(row, test),
                            dev_worst_mdd=max(row[b]['mdd_envelope'] for b in dev),
                            test_worst_mdd=max(row[b]['mdd_envelope'] for b in test))
    entry['test_mean'] = (entry['A']['test_growth'] + entry['B']['test_growth']) / 2
    entry['full_mdd'] = row['full']['mdd_envelope']
    entry['full_cagr'] = row['full']['cagr']
    entry['full_final_cny'] = row['full']['final_cny']
    entry['gate_ok'] = entry['full_mdd'] < HARD_MDD and all(entry[s]['dev_worst_mdd'] <= BUFFER for s in SPLITS)
    return entry


def select(table, grid=CANDIDATES, stress_ok=None):
    """Registered rule: hard MDD and buffer, plateau of neighbours, best mean test growth.

    `stress_ok(risk)`, when given, must not return False for the chosen value: the first
    ranked value whose stresses pass is taken. It returns None while stress runs are missing,
    which does not veto (the stress rows are separate registered measurements).
    """
    entries = {risk: evaluate(table[name_of(risk)]) for risk in grid if name_of(risk) in table}
    plateau = {risk: entry['gate_ok'] and all(n in entries and entries[n]['gate_ok'] for n in neighbours(risk, grid))
               for risk, entry in entries.items()}
    ranked = sorted((risk for risk in entries if plateau[risk]), key=lambda risk: -entries[risk]['test_mean'])
    if stress_ok is not None:
        ranked = [risk for risk in ranked if stress_ok(risk) is not False]
    return dict(entries=entries, plateau=plateau, ranked=ranked, chosen=ranked[0] if ranked else '6')


def collect():
    table = {}
    for risk in CANDIDATES:
        name = name_of(risk)
        row = {}
        for block in ['full'] + list(BLOCKS) + list(robustness.STRESS):
            path = SCRATCH / f'{name}-{block}.json'
            if path.exists():
                row[block] = summarize(path)
        if row:
            table[name] = row
    return table


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    table = collect()
    result = select(table)
    for row in table.values():
        for block in row.values():
            for key in ('weekly', 'rolling', 'concentration'):
                block.pop(key, None)
    payload = dict(rule=dict(buffer=BUFFER, hard_mdd=HARD_MDD), result=result, table=table)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / 'r3.json').write_text(json.dumps(payload, indent=1, default=str) + '\n')
    print(json.dumps(result, indent=1, default=str))


if __name__ == '__main__':
    main()
