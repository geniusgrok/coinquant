"""Fixed mechanism screen with separately funded coarse wallets, never native proof."""
import argparse
from bisect import bisect_left, bisect_right
from collections import deque
from datetime import datetime, timezone
from decimal import Decimal as D
import gzip
import hashlib
import importlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT.name
target = importlib.import_module(PACKAGE+'.target')
DAY = 86400000
ERAS = (('2020-01-01','2022-01-01'),('2022-01-01','2024-01-01'),('2024-01-01','2026-09-19'))


def stamp(value):
    return int(datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp()*1000)


def serial(value):
    if isinstance(value,D):return str(value)
    if isinstance(value,dict):return {str(k):serial(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [serial(v) for v in value]
    return value


def inputs(cache, feature_path):
    raw=cache.read_bytes();receipt=json.loads(Path(str(cache)+'.receipt.json').read_text())
    if hashlib.sha256(raw).hexdigest()!=receipt['parsed_sha256']:
        raise ValueError('parsed cache changed')
    for path,size,mtime,inode in receipt['fingerprints']:
        s=Path(path).stat()
        if (s.st_size,s.st_mtime_ns,s.st_ino)!=(size,mtime,inode):raise ValueError('input metadata changed')
    packet=json.loads(gzip.decompress(raw));spot={int(t):tuple(map(D,v[:4])) for t,v in packet['spot'].items()}
    four={int(t):tuple(map(D,v[:4])) for t,v in packet['coin4'].items()}
    warm=ROOT.parent/'coinquant/evidence/binance-boundary-20260921/warmup-trade.json'
    rows=json.loads(warm.read_text())
    if hashlib.sha256(warm.read_bytes()).hexdigest()!='62e9a9ecddccac737f99032a224f7a2a1932756cf200db34fb5c5641b72c4094':
        raise ValueError('warmup identity changed')
    coin={}
    for row in rows:
        t=int(row[0]);d=t//DAY*DAY
        o,h,l,c=map(D,row[1:5])
        prior=coin.get(d);coin[d]=(prior[0],max(prior[1],h),min(prior[2],l),c) if prior else (o,h,l,c)
    for t,(o,h,l,c) in sorted(four.items()):
        d=t//DAY*DAY;prior=coin.get(d)
        coin[d]=(prior[0],max(prior[1],h),min(prior[2],l),c) if prior else (o,h,l,c)
    from research.edge_features import FeatureBook
    # Reuse the project's full provenance/lag validator once, not raw unvalidated features.
    FEATURE_SHA256 = 'bf920626cc13653b8bbeafd171650cc1a76888e15aad0c20bbd1061fb41da512'
    book=FeatureBook(feature_path,FEATURE_SHA256)
    funding=[(a,b,v) for a,b,v,cause in book.records['funding'] if cause is None]
    return spot,coin,funding,dict(cache_sha256=receipt['parsed_sha256'],features_sha256=book.sha256,
        cache_receipt_sha256=hashlib.sha256(Path(str(cache)+'.receipt.json').read_bytes()).hexdigest())


class Wallet:
    """Exact decimal cash/fill arithmetic under disclosed daily execution proxies."""
    def __init__(self, initial, perp, stress=False):
        self.initial=self.cash=D(initial);self.q=self.entry=D(0);self.perp=perp
        self.fee=D('.00075') if perp else D('.001');self.slip=D('.0005')
        if stress:self.fee*=2;self.slip*=2
        self.fees=self.funding=D(0);self.fills=0;self.stop=None;self.extreme=None
        self.peak=D(initial);self.mdd=D(0);self.daily=[];self.closed=False

    def equity(self,price):return self.cash+self.q*(price-self.entry) if self.perp else self.cash+self.q*price

    def resize(self,q,price):
        q=D(q);delta=q-self.q
        if not delta:return
        if self.perp and self.q*q<0:self.resize(D(0),price);delta=q
        p=price*(1+self.slip if delta>0 else 1-self.slip);fee=abs(delta)*p*self.fee
        if self.perp:
            if abs(q)<abs(self.q):self.cash+=(self.q-q)*(p-self.entry)
            elif abs(q)>abs(self.q):self.entry=(abs(self.q)*self.entry+abs(delta)*p)/abs(q)
        else:self.cash-=delta*p
        self.cash-=fee;self.fees+=fee;self.q=q;self.fills+=1
        if not self.q:self.entry=D(0);self.stop=self.extreme=None
        elif self.stop is None:self.extreme=p;self.stop=p*(D('.75') if self.q>0 and self.perp else D('.8') if self.q>0 else D('1.25'))
        if not self.perp and self.cash < -D('1e-12'):raise ValueError('unfunded spot proxy')

    def mark(self,t,price):
        eq=self.equity(price);self.peak=max(self.peak,eq);self.mdd=max(self.mdd,1-eq/self.peak)
        self.daily.append((t,eq));self.closed=eq<=0


def run(mode,kind,bars,funding,begin,end,stress=False):
    wallet=Wallet(10000,kind=='coin',stress);history=deque((v[3] for t,v in sorted(bars.items()) if t<begin),maxlen=64)
    fund_times=[x[0] for x in funding]
    for t,(o,h,l,c) in sorted(bars.items()):
        if not begin<=t<end:continue
        fraction=target.exposure(history,mode=mode,spot=kind=='spot')
        if wallet.q*fraction<0:wallet.resize(D(0),o)
        capital=max(D(0),wallet.equity(o));desired=capital*fraction/o
        if kind=='spot':desired=min(desired,wallet.q+max(D(0),wallet.cash)/(o*(1+wallet.fee+wallet.slip)))
        else:
            # Independent collateral pays a 25% stop, 10% gap and funding reserve.
            desired=max(-wallet.cash/(o*D('.37')),min(wallet.cash/(o*D('.37')),desired))
        if abs(desired-wallet.q)*o>=max(D(5),capital*target.DEADBAND) or not fraction:
            wallet.resize(desired,o)
        if kind=='coin' and wallet.q:
            for observation,available,rate in funding[bisect_left(fund_times,t):bisect_left(fund_times,t+DAY)]:
                cost=wallet.q*o*rate;wallet.cash-=cost;wallet.funding+=cost
        if wallet.q and wallet.stop is not None:
            stop=wallet.stop
            breached=l<=stop if wallet.q>0 else h>=stop
            if breached:wallet.resize(D(0),min(o,stop) if wallet.q>0 else max(o,stop))
            else:
                wallet.extreme=max(wallet.extreme,h) if wallet.q>0 else min(wallet.extreme,l)
                wallet.stop=wallet.extreme*(D('.75') if kind=='coin' and wallet.q>0 else D('.8') if wallet.q>0 else D('1.25'))
        wallet.mark(t+DAY,c);history.append(c)
        if wallet.closed:break
    last=next(v[3] for t,v in reversed(sorted(bars.items())) if t<end)
    wallet.resize(D(0),last)
    return dict(net_return=wallet.cash/wallet.initial-1,mdd_daily_proxy=wallet.mdd,
        fees=wallet.fees,funding_paid=wallet.funding,fills=wallet.fills,daily=wallet.daily,
        terminal_liquidated=True,insolvent=wallet.closed)


def carry(spot,coin,funding,begin,end,stress=False):
    a=Wallet(5000,False,stress);b=Wallet(5000,True,stress)
    times=[x[0] for x in funding];avail=[x[1] for x in funding]
    joint=[];activations=0;hedge_days=0;unhedged=0
    for t,s in sorted(spot.items()):
        if not begin<=t<end or t not in coin:continue
        f=coin[t];so,fo=s[0],f[0]
        known=funding[bisect_left(avail,t-7*DAY):bisect_right(avail,t)]
        prediction=sum((row[2] for row in known),D(0))*D(30)/7
        # 30-day expected settled funding must cover both legs' modeled round-trip costs.
        hurdle=2*(a.fee+b.fee+2*a.slip)
        fresh=bool(known and t-known[-1][1]<28800000)
        enabled=fresh and len(known)>=20 and prediction>hurdle
        if enabled and not a.q and not b.q:
            qty=min(a.cash/(so*(1+a.fee+a.slip)),b.cash/(fo*D('.37')))*D('.90')
            b.resize(-qty,fo);a.resize(qty,so);activations+=1
        elif not enabled and (a.q or b.q):b.resize(D(0),fo);a.resize(D(0),so)
        for observation,available,rate in funding[bisect_left(times,t):bisect_left(times,t+DAY)]:
            cost=b.q*fo*rate;b.cash-=cost;b.funding+=cost
        if b.q and f[1]>=b.stop:
            exit_mark=max(fo,b.stop)
            b.resize(D(0),exit_mark);a.resize(D(0),so*exit_mark/fo)
        if b.q:
            b.extreme=min(b.extreme,f[2]);b.stop=b.extreme*D('1.25');hedge_days+=1
        unhedged+=int(a.q!=-b.q)
        a.mark(t+DAY,s[3]);b.mark(t+DAY,f[3]);joint.append((t+DAY,a.equity(s[3])+b.equity(f[3])))
    last=max(t for t in spot if begin<=t<end and t in coin)
    b.resize(D(0),coin[last][3]);a.resize(D(0),spot[last][3])
    return dict(net_return=(a.cash+b.cash)/10000-1,fees=a.fees+b.fees,funding_paid=b.funding,
        spot_wallet=a.cash,perp_wallet=b.cash,activations=activations,hedge_days=hedge_days,
        unhedged_daily_points=unhedged,daily=joint,
        assumptions='Independent two-wallet daily proxy; paired synchronous fills and daily mark funding, no executable basis/LOB/native proof')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,required=True);parser.add_argument('--features',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    if args.out.exists():raise ValueError('preserve existing negative/positive result')
    spot,coin,funding,identity=inputs(args.cache,args.features);results={}
    for kind,bars,modes in [('spot',spot,('trend','shock','state')),('coin',coin,('trend','shock','downside','state'))]:
        for mode in modes:
            rows=[run(mode,kind,bars,funding,stamp(a),stamp(b)) for a,b in ERAS]
            stress=[run(mode,kind,bars,funding,stamp(a),stamp(b),True) for a,b in ERAS]
            results[kind+':'+mode]=dict(base=rows,stress=stress,
                positive_eras=sum(r['net_return']>0 and not r['insolvent'] for r in rows),
                screen_entrant=sum(r['net_return']>0 and not r['insolvent'] for r in rows)>=2)
    rows=[carry(spot,coin,funding,stamp(a),stamp(b)) for a,b in ERAS]
    stress=[carry(spot,coin,funding,stamp(a),stamp(b),True) for a,b in ERAS]
    results['carry']=dict(base=rows,stress=stress,positive_eras=sum(r['net_return']>0 for r in rows),
        screen_entrant=sum(r['net_return']>0 for r in rows)>=2,
        native_entrant=False,native_blocker='no recorded simultaneous executable two-leg books/fills; daily basis cannot prove locked basis profit')
    for kind in ('spot','coin'):
        state=results[kind+':state'];components=[results[kind+':'+m] for m in ('trend','shock')]
        state['complementary_improved_eras']=sum(s['net_return']>max(c['base'][i]['net_return'] for c in components)
            for i,s in enumerate(state['base']))
        state['screen_entrant']=state['screen_entrant'] and state['complementary_improved_eras']>=2
    source={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/PACKAGE/'target.py',Path(__file__),ROOT/'research/core-spec.json')}
    args.out.write_text(json.dumps(serial(dict(identity=identity,source_sha256=source,
        eras=ERAS,results=results,proof='historical development daily proxy, not prospective/native/finite-session qualification')),indent=2)+'\n')
    print(json.dumps({k:{x:v[x] for x in ('positive_eras','screen_entrant')} for k,v in results.items()}))

if __name__=='__main__':main()
