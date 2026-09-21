"""Same L/L0 accounts; only two preregistered risk-day minute paths added."""
import argparse,json
from pathlib import Path
from decimal import Decimal as D
from research.persistent_hold_replay import run
from research.direction_risk import CONFIGS

def measure(native,output,candidate):
    if output.exists():raise ValueError('refuse to overwrite evidence')
    long,short,side=CONFIGS[candidate]
    days=list(dict.fromkeys(json.loads(Path('research/mechanism-minute-days.json').read_text())+['2024-03-05','2021-01-02']))
    for schedule in ('four_hour','sparse'):
        run(native,Path('evidence/binance-boundary-20260921'),Path('evidence/binance-mark-repair-20260921'),output/schedule,native,
            schedule=schedule,quantity_rules=Path('evidence/binance-boundary-20260921/current-instrument.json'),
            lifecycle='one_campaign',allocation='volatility',reference='impulse_hold',full_window=True,minute_days=days,
            risk_scale=D(long),entry_side=side,short_risk_scale=D(short))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--candidate',choices=['L','L0'],required=True);a=p.parse_args();measure(a.native,a.output,a.candidate)
