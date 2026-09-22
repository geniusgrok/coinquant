"""Research imports the shared linear sizing without copying its formulas."""
from decimal import Decimal as D
from pancakequant.types import ZERO
from pancakequant.linear_sizing import target_fraction, funded_target, GAP, FUNDING_RESERVE

def channel_position(window):
    if len(window)<21:return 0,ZERO
    prior=list(window)[-21:-1];close=window[-1][2]
    high=max(r[0] for r in prior);low=min(r[1] for r in prior)
    if high<=low:return 0,ZERO
    score=max(D(-1),min(D(1),(2*close-high-low)/(high-low)))
    return (1 if score>0 else -1 if score<0 else 0),abs(score)
