"""Recorded comparisons refuse different contracts and reconcile direct fees."""
from copy import deepcopy
from decimal import Decimal as D
import unittest

from research.path_analysis import IDENTITY_FIELDS, KNOBS, compare


def account():
    row = {key: 'same' for key in IDENTITY_FIELDS + KNOBS}
    row.update(complete=True, known_path=True, execution_unresolved=0, path_complete=True,
               source={'dirty': False, 'python_sources_sha256': 'frozen'},
               market_identity={'vision': {'a': 'hash'}, 'loaded_print_files': {'a': 'hash'}},
               fee='0.001', fees='1', final_usdt='1100', session_rows=[],
               trades=[{'time': 1, 'side': 'BUY', 'qty': '10', 'price': '100'}])
    return row


class PathAnalysisTests(unittest.TestCase):
    def test_more_fees_cannot_improve_the_fixed_fill_attribution(self):
        base = account()
        changed = deepcopy(base)
        changed.update(fee='0.002', final_usdt='1200')
        result = compare(base, changed, varying=['fee'])
        self.assertEqual(D(result['fixed_fills_extra_fee_usdt']), D(1))
        self.assertEqual(D(result['fixed_fills_final_usdt']), D(1099))
        self.assertEqual(D(result['remaining_path_effect_usdt']), D(101))

    def test_mismatched_source_input_and_undeclared_risk_are_rejected(self):
        for kind in ('source', 'input', 'risk'):
            base = account()
            changed = deepcopy(base)
            if kind == 'source':
                changed['source']['python_sources_sha256'] = 'other'
            elif kind == 'input':
                changed['market_identity']['loaded_print_files']['a'] = 'other'
            else:
                changed['primary_risk'] = 'other'
            with self.assertRaises(ValueError):
                compare(base, changed, varying=['fee'])
