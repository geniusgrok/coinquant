"""Reproduce one archived account from exact originals into a new output directory.

Run from the repository root with PYTHONPATH=.; no network or exchange writes.
Unpack dependency ZIPs separately; never run an old source-overwrite script.
"""
import argparse
import json
from pathlib import Path
from research.multiscale_data import restore_inputs, extend_minutes
from research.multiscale_replay import run_account


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bounded-originals',type=Path,required=True)
    parser.add_argument('--sx60-originals',type=Path,required=True)
    parser.add_argument('--development-data',type=Path,required=True)
    parser.add_argument('--protection-data',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--control',action='store_true')
    parser.add_argument('--first-pass',action='store_true')
    args=parser.parse_args()
    if args.output.exists() or args.output.with_suffix('.invocation.json').exists():
        parser.error('refusing to overwrite an existing account or partial attempt')
    root,prepared,warmup,_=restore_inputs(args.bounded_originals,args.sx60_originals,[args.development_data])
    if not args.first_pass:
        scope=json.loads(Path(__file__).with_name('FINAL_REFINEMENT_SCOPE.json').read_text())
        prepared=extend_minutes(prepared,[args.bounded_originals/'inputs',args.sx60_originals/'exit-minutes',
                            args.development_data,args.protection_data],scope['refined_hours'])
    run_account(root,args.output,prepared,warmup,control=args.control)


if __name__=='__main__':main()
