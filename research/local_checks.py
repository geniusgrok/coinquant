"""Named offline execution cases; native qualification is never inferred."""
import argparse
import io
import json
import unittest
from pathlib import Path

from research.rebuild import source_identity

CASES = {
    'partial_fill': 'tests.test_session.SessionTests.test_partial_fill_protects_actual_size_then_tops_up_under_same_protection',
    'lost_ack': 'tests.test_session.SessionTests.test_timeout_after_fill_recovers_without_duplicate',
    'restart_unknown': 'tests.test_session.SessionTests.test_unknown_entry_never_resends_even_after_restart',
    'replacement': 'tests.test_session.SessionTests.test_protection_amendment_keeps_old_until_new_pair_confirmed',
    'disconnect': 'tests.test_session.SessionTests.test_disconnection_never_infers_flat_or_successful_cleanup',
    'stopped_protection': 'tests.test_session.SessionTests.test_finite_long_entry_hold_and_offline_protection',
}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    source = source_identity()
    if args.out.exists() or source['dirty']:
        parser.error('use clean committed source and a new report')
    rows = {}
    for case, name in CASES.items():
        output = io.StringIO()
        result = unittest.TextTestRunner(stream=output).run(unittest.defaultTestLoader.loadTestsFromName(name))
        rows[case] = {'test': name, 'tests_run': result.testsRun,
                      'passed': result.wasSuccessful() and result.testsRun == 1 and not result.skipped,
                      'log': output.getvalue()}
    report = {'source': source, 'cases': rows, 'offline_passed': all(row['passed'] for row in rows.values()),
              'native_execution_verified': False, 'qualification': 'NOT_QUALIFIED'}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({name: row['passed'] for name, row in rows.items()}))
    return 0 if report['offline_passed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
