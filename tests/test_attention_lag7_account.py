import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from pancakequant.research import invocations, spec, timestamp
import research.attention_lag7_account as lag7
from research.attention_lag7_account import DAY, copy_frozen_inputs, prediction_streams, verify_native_inputs, write_report


class AttentionLag7AccountTests(unittest.TestCase):
    def row(self, t, u):
        week_end = t - 9*DAY
        return dict(t=t, u=u, week_end=week_end, assumed_available_at=t, available_at=None,
                    status='eligible', C0=.1, C1=-.1, C2=.2)

    def test_maps_only_the_saved_three_controls(self):
        start = timestamp(spec()['start'])
        t = next(call for call in invocations(spec()) if call >= start + 9*DAY)
        u = next(call for call in invocations(spec()) if call >= t + 7*DAY)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'lag7_predictions.json'
            path.write_text(json.dumps([self.row(t, u)]))
            rows, streams = prediction_streams(Path(tmp))
        self.assertEqual(len(rows), 1)
        self.assertEqual(set(streams), {'C0', 'C1', 'C2_lag7'})
        self.assertEqual(streams['C2_lag7'][t], .2)

    def test_rejects_unmatured_tail_row(self):
        end = timestamp(spec()['development_end'])
        t = next(call for call in invocations(spec()) if call >= end - 10*DAY)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'lag7_predictions.json'
            path.write_text(json.dumps([self.row(t, end + DAY)]))
            with self.assertRaisesRegex(ValueError, 'outside the development account'):
                prediction_streams(Path(tmp))

    def test_allows_a_saved_tail_prediction_to_mark_at_window_end(self):
        end = timestamp(spec()['development_end'])
        t = max(call for call in invocations(spec()) if call < end)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'lag7_predictions.json'
            path.write_text(json.dumps([self.row(t, end)]))
            try:
                _, streams = prediction_streams(Path(tmp))
            except ValueError as error:
                self.fail(f'window-tail prediction was rejected: {error}')
        self.assertIn(t, streams['C2_lag7'])

    def test_run_reads_the_verified_frozen_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); output = root/'output'; output.mkdir(); (output/'PROTOCOL.md').write_text('protocol\n')
            frozen = root/'frozen'; frozen.mkdir()
            seen = []
            def stop(path):
                seen.append(Path(path))
                raise RuntimeError('stop after frozen read')
            with patch.object(lag7, 'copy_frozen_inputs', return_value=(frozen, {})), \
                    patch.object(lag7, 'prediction_streams', side_effect=stop):
                with self.assertRaisesRegex(RuntimeError, 'stop after frozen read'):
                    lag7.run(root/'native', root/'untrusted-attention', root/'labels', root/'prior', output)
        self.assertEqual(seen, [frozen])

    def test_run_uses_the_frozen_b1_snapshot_for_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); output = root/'output'; output.mkdir(); (output/'PROTOCOL.md').write_text('protocol\n')
            frozen = root/'frozen'; (frozen/'prior_B1').mkdir(parents=True)
            seen = []
            def stop(bundle, minutes, prior):
                seen.append(Path(prior))
                raise RuntimeError('stop after B1 identity check')
            with patch.object(lag7, 'copy_frozen_inputs', return_value=(frozen, {})), \
                    patch.object(lag7, 'prediction_streams', return_value=([], {'C0': {}, 'C1': {}, 'C2_lag7': {}})), \
                    patch.object(lag7, 'load', return_value=(({}, {}, {}, []), ({}, []))), \
                    patch.object(lag7, 'verify_native_inputs', side_effect=stop):
                with self.assertRaisesRegex(RuntimeError, 'stop after B1 identity check'):
                    lag7.run(root/'native', root/'attention', root/'labels', root/'mutable-B1', output)
        self.assertEqual(seen, [frozen/'prior_B1'])

    def test_rejects_prior_identity_with_an_extra_raw_record(self):
        minutes = [dict(path=f'daily/klines/BTCUSDT/1m/{i}.zip', sha256=str(i)) for i in range(22)]
        base = [dict(path='monthly/klines/BTCUSDT/1h/a.zip', sha256='base')]
        with tempfile.TemporaryDirectory() as tmp:
            prior = Path(tmp)/'B1'; prior.mkdir()
            (prior/'inputs.json').write_text(json.dumps(base + minutes + [dict(path='current-instrument.json', sha256='rule')]))
            result = verify_native_inputs(({}, {}, {}, base), ({}, minutes), prior)
        self.assertFalse(result['passed'])

    def test_rejects_unpinned_archived_b1_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); attention = root/'attention'; attention.mkdir(); prior = root/'B1'; prior.mkdir(); output = root/'output'; output.mkdir()
            files = {'lag7_predictions.json': '[]', 'lag7_fits.json': '[]', 'weeks.json': '[]', 'labels.json': '[]'}
            for name, content in files.items():
                (attention/name).write_text(content)
            labels = root/'labels.json'; labels.write_text(files['labels.json'])
            (prior/'inputs.json').write_text('wrong-inputs')
            (prior/'result.json').write_text('wrong-result')
            expected = {name: lag7.sha256(attention/name) for name in lag7.INPUT_FILES}
            expected['labels.json'] = lag7.sha256(labels)
            with patch.dict(lag7.EXPECTED_INPUT_SHA256, expected, clear=True), \
                    patch.object(lag7, 'EXPECTED_PRIOR_B1_SHA256', {'inputs.json': lag7.sha256(root/'labels.json'), 'result.json': lag7.sha256(root/'labels.json')}):
                with self.assertRaises(ValueError):
                    copy_frozen_inputs(attention, labels, prior, output)

    def test_report_does_not_claim_skipped_full_window_ran(self):
        candidates = {name: dict(cagr_percent=1, mdd_percent=2, final_cny='3', result=dict(counts=dict(entry=4), holding_hours=5))
                      for name in ('C0', 'C1', 'C2_lag7', 'L3.6')}
        summary = dict(development=dict(candidates=candidates), development_gate=dict(passed=True, C1_vs_prior_B1=dict(trace_equal=True, input_identity_equal=True)),
                       changed_signal_attribution=dict(changed_prediction_signs=0), full_window=dict(ran=False))
        with tempfile.TemporaryDirectory() as tmp:
            write_report(Path(tmp), summary)
            report = (Path(tmp)/'REPORT.md').read_text()
        self.assertNotIn('已执行完整窗口复核', report)


if __name__ == '__main__':
    unittest.main()
