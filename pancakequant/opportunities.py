"""Causal event opportunities, shared by research and future read-only model use.

Independent definitions, not a reproduction of a redacted external strategy.
Input bars are completed UTC four-hour candles; no account or exchange writes.
"""
from collections import deque
from dataclasses import dataclass, replace
from decimal import Decimal as D

FOUR_HOURS = 14400000

@dataclass(frozen=True)
class Opportunity:
    identity: int
    direction: int
    stop: D
    take: D
    expires: int | None
    entry_limit: D | None = None
    entry_open: bool = True
    confirm_at: D | None = None
    confirmed_stop: D | None = None

class Opportunities:
    def __init__(self, mechanism, interval=FOUR_HOURS):
        if mechanism not in ('squeeze','sweep','shock','impulse','impulse_hold','impulse_validity','impulse_confirmation','persistent_impulse'):raise ValueError('unknown mechanism')
        if interval not in (3600000,FOUR_HOURS):raise ValueError('unsupported completed interval')
        self.interval=interval
        self.mechanism=mechanism;self.bars=deque(maxlen=21);self.tr=deque(maxlen=14)
        self.ema=None;self.last=None;self.active=None;self.box=None;self.contraction=0
        self.armed=None;self.pivots=[];self.count=0

    def update(self, end, high, low, close):
        if self.last is not None and end!=self.last+self.interval:raise ValueError('incomplete model clock')
        if not 0<low<=close<=high:raise ValueError('invalid completed candle')
        prior=self.bars[-1][3] if self.bars else close
        prior_atr=sum(self.tr)/14 if len(self.tr)==14 else None
        self.tr.append(max(high-low,abs(high-prior),abs(low-prior)))
        self.ema=close if self.ema is None else self.ema+D(2)/21*(close-self.ema)
        self.bars.append((end,high,low,close));self.last=end;self.count+=1
        if self.active:
            a=self.active
            if (a.expires is not None and end>=a.expires) or (low<=a.stop or high>=a.take if a.direction>0 else high>=a.stop or low<=a.take):self.active=None
        if self.active and self.active.entry_limit is not None and self.active.direction*(close-self.active.entry_limit)>=0:
            self.active=replace(self.active,entry_open=False)
        if self.active and self.active.confirm_at is not None and self.active.direction*(close-self.active.confirm_at)>=0:
            self.active=replace(self.active,stop=self.active.confirmed_stop,confirm_at=None)
        if self.mechanism=='squeeze':
            if len(self.bars)<20 or len(self.tr)<14:return self.active
            closes=[r[3] for r in list(self.bars)[-20:]];mean=sum(closes)/20
            sd=(sum((c-mean)**2 for c in closes)/19).sqrt();atr=sum(self.tr)/14
            squeeze=mean-2*sd>self.ema-D('1.5')*atr and mean+2*sd<self.ema+D('1.5')*atr
            if squeeze:
                self.box=(max(high,self.box[0]),min(low,self.box[1])) if self.contraction else (high,low)
                self.contraction+=1;self.armed=None
            else:
                if self.contraction>=3:self.armed=(*self.box,end,end+7*86400000)
                self.contraction=0;self.box=None
                if self.armed and not self.active:
                    upper,lower,identity,expiry=self.armed
                    if end>=expiry:self.armed=None
                    elif close>upper or close<lower:
                        side=1 if close>upper else -1;stop=lower if side>0 else upper
                        take=close+2*(close-stop)
                        self.armed=None
                        if take>0:self.active=Opportunity(identity,side,stop,take,expiry)
        elif self.mechanism in ('shock','impulse','impulse_hold','impulse_validity','impulse_confirmation','persistent_impulse'):
            shock=bool(prior_atr and abs(close-prior)>3*prior_atr)
            if self.mechanism=='persistent_impulse' and shock and self.active and self.active.direction*(close-prior)<0:
                self.active=None
            if not self.active and shock:
                side=-1 if close>prior else 1
                stop=high if side<0 else low
                if self.mechanism in ('impulse','impulse_hold','impulse_validity','impulse_confirmation','persistent_impulse'):
                    side=-side;stop=(prior+close)/2
                    take=close*(close/stop)**20 if self.mechanism in ('impulse_hold','impulse_validity','impulse_confirmation','persistent_impulse') else close+2*(close-stop)
                    if take>0:self.active=Opportunity(end,side,stop,take,None if self.mechanism=='persistent_impulse' else end+42*FOUR_HOURS,close+2*(close-stop) if self.mechanism=='impulse_validity' else None,True,close+2*(close-stop) if self.mechanism=='impulse_confirmation' else None,close if self.mechanism=='impulse_confirmation' else None)
                elif stop!=close:
                    self.active=Opportunity(end,side,stop,(prior+close)/2,end+6*FOUR_HOURS)
        else:
            bars=list(self.bars)
            # Only pivots known before the current sweep bar can trigger it.
            self.pivots=[p for p in self.pivots if self.count-p[0]<=20]
            up=[p for p in self.pivots if p[1]==1 and high>p[2] and close<p[2]]
            down=[p for p in self.pivots if p[1]==-1 and low<p[2] and close>p[2]]
            if not self.active and bool(up)!=bool(down):
                side=-1 if up else 1;stop=high if up else low;take=close+2*(close-stop)
                if take>0 and stop!=close:self.active=Opportunity(end,side,stop,take,end+20*FOUR_HOURS)
                used=up or down;self.pivots=[p for p in self.pivots if p not in used]
            if len(bars)>=7:
                seven=bars[-7:];pivot=seven[3]
                if all(pivot[1]>r[1] for i,r in enumerate(seven) if i!=3):self.pivots.append((self.count-3,1,pivot[1]))
                if all(pivot[2]<r[2] for i,r in enumerate(seven) if i!=3):self.pivots.append((self.count-3,-1,pivot[2]))
        return self.active
