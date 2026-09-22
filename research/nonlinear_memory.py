"""L20 local conditional mean using exactly the previously frozen L3 features."""
import argparse
import math
from pathlib import Path
from research.linear_forecast import run


def predict(observations,now,x):
    eligible=[(sum((a-b)**2 for a,b in zip(features[1:],x[1:])),i,y)
              for i,(maturity,features,y) in enumerate(observations) if maturity<=now]
    n=len(eligible)
    if not n:return 0.0,0
    k=max(1,math.isqrt(n))
    neighbors=sorted(eligible)[:k]
    return sum(y for _,_,y in neighbors)/k,n

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ('root','warmup','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();run(a.root,a.warmup,a.output,predictor=predict,candidate='L20')
