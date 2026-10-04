"""Finite read-only admission for the four frozen joint BTC risk rules."""
import argparse
import json
from pathlib import Path

from research import nine_routes as r


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--rule',choices=r.RULES,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args(argv)
    raw=args.input.read_bytes();packet=json.loads(raw)
    verdict=r.admission(packet['accounts'],packet['proposal'],packet['now_ms'],args.rule,
                        packet.get('context'),packet.get('competitor'))
    verdict.update(format='btc-nine-read-only-admission-v1',input_sha256=r.sha(raw),
                   spec_sha256=r.sha(r.SPEC.read_bytes()),native_ownership_verified=False,
                   meaning='Research caller inputs; does not authenticate accounts or authorize execution.')
    with args.out.open('x') as stream:json.dump(verdict,stream,indent=2);stream.write('\n')
    print(json.dumps(verdict))


if __name__=='__main__':main()
