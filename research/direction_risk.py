"""Preregistered direction budgets, one account and unchanged D3 mechanism."""
import argparse,json
from pathlib import Path
from decimal import Decimal as D
from research.persistent_hold_replay import run
from research.opportunity_attribution import analyze
from research.target_attribution import summarize as annual

CONFIGS={'L0':('2.4','0','long'),'H':('2.4','1.2','both'),'L':('3.6','0','long')}

def measure(native,output,candidate,full=False):
    if output.exists():raise ValueError('refuse to overwrite evidence')
    long,short,side=CONFIGS[candidate]
    days=json.loads(Path('research/mechanism-minute-days.json').read_text())
    if not full:days=[d for d in days if d<'2024-01-01']
    for schedule in ('four_hour','sparse'):
        dest=output/schedule
        run(native,Path('evidence/binance-boundary-20260921'),Path('evidence/binance-mark-repair-20260921'),dest,native,
            schedule=schedule,quantity_rules=Path('evidence/binance-boundary-20260921/current-instrument.json'),
            lifecycle='one_campaign',allocation='volatility',reference='impulse_hold',full_window=full,minute_days=days,
            risk_scale=D(long),entry_side=side,short_risk_scale=D(short))
        annual(dest);analyze(dest)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--candidate',choices=CONFIGS,required=True);p.add_argument('--full-window',action='store_true')
    a=p.parse_args();measure(a.native,a.output,a.candidate,a.full_window)
