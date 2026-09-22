import unittest
from research.probe_okx import START, _rows, _listed_before_start


def candle(t, confirm='1'):
    return [str(t), '100', '102', '99', '101', confirm]


class ProbeTests(unittest.TestCase):
    def test_missing_listing_is_not_pre_2020_evidence(self):
        for value in (None, '', '0', '-1', 'broken', str(START + 1)):
            self.assertFalse(_listed_before_start(value))
        self.assertTrue(_listed_before_start(str(START - 1)))

    def test_boundary_gap_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'missing hourly'):
            _rows({'data': [candle(START - 3600000), candle(START + 3600000)]})

    def test_complete_exact_boundary(self):
        result = _rows({'data': [candle(START + 3600000), candle(START)]})
        self.assertTrue(result['contains_start'])
        self.assertEqual(result['rows'], 2)

    def test_incomplete_duplicate_and_bad_prices_rejected(self):
        cases = [[candle(START, '0')], [candle(START), candle(START)],
                 [[str(START), '100', '101', '99', '102', '1']],
                 [[str(START), 'NaN', '101', '99', '100', '1']]]
        for rows in cases:
            with self.assertRaises(ValueError):
                _rows({'data': rows})

    def test_funding_requires_realized_rate_and_correct_instrument(self):
        row = {'instId': 'BTC-USDT-SWAP', 'fundingTime': str(START), 'realizedRate': '0.0001'}
        self.assertTrue(_rows({'data': [row]}, timestamp_key='fundingTime')['contains_start'])
        with self.assertRaises(ValueError):
            _rows({'data': [{**row, 'instId': 'ETH-USDT-SWAP'}]}, timestamp_key='fundingTime')
        with self.assertRaises(KeyError):
            _rows({'data': [{k: v for k, v in row.items() if k != 'realizedRate'}]}, timestamp_key='fundingTime')
