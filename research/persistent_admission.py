"""Finite read-only joint new-order proposal, from explicit supplied snapshots."""
import argparse
import json
from pathlib import Path
import time

from research.persistent_routes import joint_admission


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--snapshots',type=Path,required=True)
    p.add_argument('--proposal',type=Path,required=True)
    p.add_argument('--rule',choices=('gross-entry-cap','stress-entry-cap','state-exposure'),required=True)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args(argv)
    if args.out.exists():raise ValueError('preserve old admission receipt')
    data=json.loads(args.snapshots.read_text());proposal=json.loads(args.proposal.read_text())
    at=int(time.time()*1000)
    result=joint_admission(data['accounts'],proposal,at,data.get('completed_returns',[]),args.rule,data.get('context'))
    result.update(received_evaluation_ms=at,qualification='RESEARCH_READ_ONLY',
                  snapshot_authority='Caller must supply actual confirmed separately financed ownership; JSON is not independent account attestation.')
    args.out.write_text(json.dumps(result,default=str,indent=2)+'\n')
    print(result['status'])


if __name__=='__main__':main()
