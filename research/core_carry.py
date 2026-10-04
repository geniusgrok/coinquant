"""Single registered carry repair: hold economics rather than pay daily hurdle churn."""
from bisect import bisect_left,bisect_right
from decimal import Decimal as D
from research.core_screen import Wallet,DAY


def measure(spot,coin,funding,begin,end,stress=False):
    a=Wallet(5000,False,stress);b=Wallet(5000,True,stress)
    times=[x[0] for x in funding];avail=[x[1] for x in funding]
    joint=[];opened=None;activations=hedge_days=0
    for t,s in sorted(spot.items()):
        if not begin<=t<end or t not in coin:continue
        f=coin[t];so,fo=s[0],f[0]
        known=funding[bisect_left(avail,t-7*DAY):bisect_right(avail,t)]
        prediction=sum((r[2] for r in known),D(0))*D(30)/7
        hurdle=2*(a.fee+b.fee+2*a.slip)
        fresh=bool(known and t-known[-1][1]<28800000)
        enter=fresh and len(known)>=20 and prediction>hurdle
        # One cause-specific change: separate open economics from held exit.
        exit_=not fresh or prediction<=0 or opened is not None and t>=opened+30*DAY
        if a.q or b.q:
            if exit_ or b.cash<abs(b.q)*fo*D('.37'):
                b.resize(D(0),fo);a.resize(D(0),so);opened=None
        elif enter:
            qty=min(a.cash/(so*(1+a.fee+a.slip)),b.cash/(fo*D('.37')))*D('.90')
            b.resize(-qty,fo);a.resize(qty,so);opened=t;activations+=1
        for observation,available,rate in funding[bisect_left(times,t):bisect_left(times,t+DAY)]:
            cost=b.q*fo*rate;b.cash-=cost;b.funding+=cost
        if b.q and f[1]>=b.stop:
            mark=max(fo,b.stop);b.resize(D(0),mark);a.resize(D(0),so*mark/fo);opened=None
        if b.q:
            b.extreme=min(b.extreme,f[2]);b.stop=b.extreme*D('1.25');hedge_days+=1
        a.mark(t+DAY,s[3]);b.mark(t+DAY,f[3]);joint.append((t+DAY,a.equity(s[3])+b.equity(f[3])))
    last=max(t for t in spot if begin<=t<end and t in coin)
    b.resize(D(0),coin[last][3]);a.resize(D(0),spot[last][3])
    return dict(net_return=(a.cash+b.cash)/10000-1,fees=a.fees+b.fees,funding_paid=b.funding,
        spot_wallet=a.cash,perp_wallet=b.cash,activations=activations,hedge_days=hedge_days,daily=joint,
        native_entrant=False,proof='separate-wallet daily proxy; no executable paired book or native atomic two-leg proof')
