"""Causal market-only estimate; no replay account feedback or fitted constants."""
from decimal import Decimal as D
from coinquant.types import ZERO


def target_fraction(observations):
    n=len(observations)
    if n<60:return ZERO
    mean=sum(observations,ZERO)/n
    second=sum((r*r for r in observations),ZERO)/n
    if mean<=0 or second<=0:return ZERO
    return min(D(2),D('.5')*D(n)/D(n+252)*mean/second)
