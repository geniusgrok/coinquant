"""Reproduce a single preregistered account; never search parameter combinations."""
import argparse,json
from decimal import Decimal as D
from pathlib import Path
from research.persistent_hold_replay import run
from research.opportunity_attribution import analyze

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--native',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--candidate',choices=('D3','long','short','V1','V2'),required=True)
    p.add_argument('--schedule',choices=('four_hour','sparse'),required=True)
    p.add_argument('--full-window',action='store_true');a=p.parse_args()
    if a.output.exists():raise SystemExit('refusing to overwrite an existing measured account')
    days=json.loads(Path('research/mechanism-minute-days.json').read_text())
    if not a.full_window:days=[d for d in days if d<'2024-01-01']
    reference={'V1':'impulse_validity','V2':'impulse_confirmation'}.get(a.candidate,'impulse_hold')
    run(a.native,Path('evidence/binance-boundary-20260921'),Path('evidence/binance-mark-repair-20260921'),
        a.output,a.native,False,a.schedule,Path('evidence/binance-boundary-20260921/current-instrument.json'),
        'one_campaign','volatility',reference,full_window=a.full_window,minute_days=days,risk_scale=D('2.4'),
        entry_side=a.candidate if a.candidate in ('long','short') else 'both')
    analyze(a.output)
