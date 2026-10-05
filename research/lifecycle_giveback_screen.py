"""Recover qualified initial Spot stop receipts; reuse original debt screen."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import time

from research.lifecycle import SPEC, serial, spot_initial_stops, giveback_spot_screen
from research.lifecycle_screen import bound


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--debt-screen', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('preserve prior giveback outcome')
    began = time.monotonic()
    spec = json.loads(SPEC.read_text())
    packet = json.loads(bound(spec['daily_packet'],spec['daily_sha256']))
    source = spec['projections']['spot']
    ledger = json.loads(gzip.decompress(bound(source['path'],source['sha256'])))
    parent = ledger['parent_binding']
    original = json.loads(gzip.decompress(bound(parent['path'], parent['sha256'])))
    row = original['results'][parent['candidate']]
    if row['audit']['passed'] is not True or row['fills'] != ledger['fills'] or row['allocations'] != ledger['allocations']:
        raise ValueError('accepted parent cannot prove these exact fills/stop allocations')
    stops = spot_initial_stops(ledger, row['client_events'])
    result = giveback_spot_screen(ledger, packet, stops, spec['cutoff_ms'])
    out = dict(format='btc-owned-giveback-screen-v1',
        registered_spec_sha256=hashlib.sha256(SPEC.read_bytes()).hexdigest(),
        mechanism_source_sha256=hashlib.sha256(SPEC.with_name('lifecycle.py').read_bytes()).hexdigest(),
        screening_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        prior_debt_screen=dict(path=str(args.debt_screen), sha256=hashlib.sha256(args.debt_screen.read_bytes()).hexdigest(), recomputed=False),
        installed_receipt_source=parent, results=dict(spot=result,
            coin=dict(status='BLOCKED_INPUT', reason='Coin pinned projection contains attempted stops without original accepted installation receipt UTC clock.')),
        elapsed_seconds=time.monotonic()-began, original795_replays=0,
        independently_financed_new_wallets=0, default_changed=False, prospective_alpha_proven=False)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open('x') as stream:
        stream.write(json.dumps(serial(out), indent=2)+'\n')
    print(json.dumps(serial(dict(elapsed_seconds=out['elapsed_seconds'], qualified_initial_stops=len(stops),
        result={p:dict(status=v['status'],eras=v['eras']) for p,v in result.items()})),indent=2))


if __name__ == '__main__':
    main()
