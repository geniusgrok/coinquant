"""Diagnostic request/cycle traces over the existing historical session path."""
import argparse
import gzip
import hashlib
import json
import sqlite3
from pathlib import Path
from unittest.mock import patch

from research import rebuild
from research.session_exchange import SessionExchange


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--market', default='/tmp/coinquant-market')
    parser.add_argument('--prints', default='/tmp/coinquant-prints')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.out.exists() or rebuild.source_identity()['dirty']:
        parser.error('use clean committed source and a new diagnostic directory')
    events = []

    class TracedExchange(SessionExchange):
        def _transport(self, request, timeout):
            method, path, parameters = self._inflight
            row = {'event': 'request', 'start_ms': self.now_ms, 'method': method, 'path': path,
                   'parameters': {k: v for k, v in parameters.items() if k not in ('signature', 'timestamp', 'recvWindow')},
                   'wallet_before': str(self.wallet), 'position_before': str(self.q), 'entry_before': str(self.entry)}
            try:
                return super()._transport(request, timeout)
            except Exception as exc:
                row['error_type'] = type(exc).__name__
                raise
            finally:
                row.update(end_ms=self.now_ms, wallet_after=str(self.wallet), position_after=str(self.q))
                events.append(row)

    original = rebuild._harvest

    def harvest(directory):
        with sqlite3.connect(Path(directory) / 'intents.sqlite') as db:
            for payload, in db.execute('SELECT payload FROM observations ORDER BY sequence'):
                report = json.loads(payload)
                events.append({'event': 'cycle', 'report': {key: report[key] for key in (
                    'cycles', 'status', 'actual', 'model_preview', 'actions', 'errors') if key in report}})
        return original(directory)

    args.out.mkdir(parents=True)
    summary = {'purpose': 'diagnostic paths only; not full-window economic qualification', 'probes': []}
    probes = [('read100', '6', 100, '0.00075', '2020-01-04T00:00:00Z'),
              ('read200', '6', 200, '0.00075', '2020-01-04T00:00:00Z'),
              ('read400', '6', 400, '0.00075', '2020-01-04T00:00:00Z'),
              ('fee-base', '7.5', 200, '0.00075', '2020-01-15T00:00:00Z'),
              ('fee150', '7.5', 200, '0.001125', '2020-01-15T00:00:00Z')]
    for name, risk, latency, fee, end in probes:
        events.clear()
        with patch.object(rebuild, 'SessionExchange', TracedExchange), patch.object(rebuild, '_harvest', harvest):
            report = rebuild.trial('F2-' + name, primary_risk=risk, read_latency_ms=latency, fee=fee,
                                   market=args.market, prints=args.prints, out='/tmp/coinquant-f2-raw',
                                   window_end=end)
        blob = ('\n'.join(json.dumps(row, default=str) for row in events) + '\n').encode()
        path = args.out / (name + '.jsonl.gz')
        path.write_bytes(gzip.compress(blob, mtime=0))
        original_name = {'read100': 'M10-r6-l100', 'read200': 'M10-r6', 'read400': 'M10-r6-l400',
                         'fee-base': 'M10-r75', 'fee150': 'M10-fee150'}[name]
        old = json.loads((rebuild.ROOT / f'evidence/remeasure-20260929-m10/{original_name}.json').read_text())
        expected = [row for row in old['trades'] if row['time'] < rebuild.timestamp(end)]
        fields = ('time', 'side', 'qty', 'price')
        reproduced = [[row[key] for key in fields] for row in report['trades']] == [
            [row[key] for key in fields] for row in expected]
        summary['probes'].append({'name': name, 'events': len(events), 'trace_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                                  'trade_prefix_matches_M10': reproduced,
                                  'source': report['source'], 'market_identity': report['market_identity'],
                                  'trades': report['trades'], 'execution_unresolved': report['execution_unresolved'],
                                  'sessions': report['sessions'], 'window_end': end})
        print(name, len(events), len(report['trades']), flush=True)
    (args.out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
