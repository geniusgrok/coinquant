"""Frozen T holding experiment; OHLC order scenarios are not tick evidence."""
from decimal import Decimal as D

CALLBACK=D('.10')

def step(peak,bar,fixed_stop,order):
    """Causal SELL trail through one explicit mark-price path, no future ratchet."""
    o,h,l,c=bar
    if order not in ('low_first','high_first'):raise ValueError('unknown path')
    points=(o,l,h,c) if order=='low_first' else (o,h,l,c)
    for i,price in enumerate(points):
        trigger=max(fixed_stop,peak*(1-CALLBACK))
        if price<=trigger:return peak,(price if i==0 else trigger)
        peak=max(peak,price)
    return peak,None

if __name__=='__main__':
    import argparse,json
    from pathlib import Path
    from research.persistent_hold_replay import run
    p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--order',choices=('low_first','high_first'),required=True)
    p.add_argument('--full-window',action='store_true')
    a=p.parse_args()
    days=[d for d in json.loads(Path('research/mechanism-minute-days.json').read_text())+['2021-01-02','2024-03-05'] if a.full_window or d<'2024-01-01']
    run(a.native,Path('evidence/binance-boundary-20260921'),Path('evidence/binance-mark-repair-20260921'),a.output,
        minutes=a.native,minute_days=days,quantity_rules=Path('evidence/binance-boundary-20260921/current-instrument.json'),
        lifecycle='one_campaign',allocation='volatility',reference='impulse_hold',risk_scale=D('3.6'),entry_side='long',short_risk_scale=D(0),native_trail_order=a.order,full_window=a.full_window)
