"""Finite independent wallets on the actual manual session path; no full795."""
import argparse
from collections import OrderedDict
from contextlib import contextmanager
from decimal import Decimal as D
from functools import lru_cache
import importlib
import json
from pathlib import Path
import sqlite3
import subprocess
import time
import types

from research.core_screen import inputs, stamp, serial
from dataclasses import is_dataclass, asdict

_base_serial=serial
def serial(value):
    if is_dataclass(value):return serial(asdict(value))
    if isinstance(value,dict):return {str(k):serial(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)):return [serial(v) for v in value]
    return _base_serial(value)

ROOT=Path(__file__).resolve().parents[1]
PACKAGE=ROOT.name
WINDOWS=(('2020-01-01','2020-04-01'),('2021-04-01','2021-07-01'),('2022-04-01','2022-07-01'),('2023-01-01','2023-04-01'))
BASE={'spotquant':'38e05f3b98b59595d00ec14eb7e7f27ab78e1b53','coinquant':'113a792efc1531e1f00d5629f45e09756dce6e9c'}


@contextmanager
def baseline():
    if PACKAGE=='spotquant':
        module=types.ModuleType('spotquant.historical_session');module.__package__='spotquant';module.__file__=str(ROOT/'spotquant/session.py')
        source=subprocess.check_output(['git','show',BASE[PACKAGE]+':spotquant/session.py'],cwd=ROOT,text=True)
        exec(compile(source,BASE[PACKAGE]+':spotquant/session.py','exec'),module.__dict__)
        yield module
    else:
        from coinquant import linear_preview, session
        from coinquant.campaign import Campaign
        old=linear_preview.Campaign;linear_preview.Campaign=Campaign
        try:yield session
        finally:linear_preview.Campaign=old


def optimize_market(market_root,prints_root,scratch):
    from research import session_market as sm
    market=sm.load_base(market_root);market._load_month=lru_cache(maxsize=8)(market._load_month)
    old=sm._checksum;verified={}
    def check(path):
        s=path.stat();key=(str(path),s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)
        if key not in verified:verified[key]=old(path)
        return verified[key]
    sm._checksum=check
    class Prints(sm.TradePrints):
        def __init__(self):
            root=scratch/'selected-prints';root.mkdir();super().__init__(root);self.days=OrderedDict()
            self.cache_dir=scratch.parent/'parsed-prints-cache';self.cache_dir.mkdir(exist_ok=True)
            (scratch/'selected-prints-cache').symlink_to(self.cache_dir)
        def _load(self,day):
            if day in self.days:
                self.days.move_to_end(day);self._day_ms=day;self._rows=self.days[day];return self._rows
            from datetime import datetime,timezone
            name=f'BTCUSDT-aggTrades-{datetime.fromtimestamp(day/1000,timezone.utc):%Y-%m-%d}.zip'
            for suffix in ('','.CHECKSUM'):
                origin=prints_root/(name+suffix);path=self.root/(name+suffix)
                if not origin.exists():
                    if suffix=='':self._day_ms,self._rows=day,None;return None
                    raise ValueError('selected print checksum missing')
                if not path.exists():path.symlink_to(origin)
            digest=check(self.root/name)
            cache=self.cache_dir/(name+'.'+digest+'.bin')
            import gzip,shutil
            packed=Path(str(cache)+'.gz')
            if not cache.exists() and packed.exists():
                with gzip.open(packed,'rb') as src,cache.open('wb') as dst:shutil.copyfileobj(src,dst)
            rows=super()._load(day);self.days[day]=rows
            while len(self.days)>3:
                expired,_=self.days.popitem(last=False)
                prefix=datetime.fromtimestamp(expired/1000,timezone.utc).strftime('BTCUSDT-aggTrades-%Y-%m-%d.zip.')
                for cached in self.cache_dir.glob(prefix+'*.bin'):
                    zipped=Path(str(cached)+'.gz')
                    if not zipped.exists():
                        with cached.open('rb') as src,gzip.open(zipped,'wb',compresslevel=1) as dst:shutil.copyfileobj(src,dst)
                    cached.unlink()
            return rows
    return market,Prints()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cache',type=Path,required=True);p.add_argument('--features',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--scratch',type=Path,required=True)
    p.add_argument('--market',type=Path,default=Path('/tmp/coinquant-market'))
    p.add_argument('--prints',type=Path,default=Path('/workspace/scratch/alpha-beta-next/public-print-vault'))
    p.add_argument('--policy',choices=('baseline','core'),help='Restrict recovery to one policy; reuse other completed wallets')
    p.add_argument('--case',help='One absent/failed case only; never overwrites a prior receipt')
    a=p.parse_args()
    if a.policy != 'baseline':
        raise ValueError('target core retired: reproduce core wallets only from their frozen producer source; use --policy baseline here')
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():raise ValueError('freeze source first')
    if a.out.exists():raise ValueError('preserve previous output; choose new path for recovery')
    a.scratch.mkdir(parents=True,exist_ok=False);a.out.mkdir()
    spot,coin,funding,identity=inputs(a.cache,a.features)
    schedule_path=ROOT.parent/'coinquant/research/session_schedule.json'
    starts=json.loads(schedule_path.read_text())['primary']['starts_ms']
    import hashlib
    identity.update(source_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        baseline_source=BASE[PACKAGE],schedule_sha256=hashlib.sha256(schedule_path.read_bytes()).hexdigest())
    if PACKAGE=='spotquant':
        from research.session_account import HistoricalVenue, audit
        from research.complete_spot import PriorFX
        from research.edge_features import FeatureBook
        from spotquant.config import Config
        from spotquant import session
        from spotquant.state import State
        fx=PriorFX(ROOT.parent/'starquant/data/usdcny_frankfurter.json')
        bars=[(t,*v,D(0)) for t,v in sorted(spot.items())]
        features=FeatureBook(a.features,identity['features_sha256'])
    else:
        from research.complete_perp import ResearchExchange
        from research.comparison_report import audit
        from research.unified_perp import PriorFX
        from coinquant.config import Config
        from coinquant import session
        from coinquant.state import State
        market,tape=optimize_market(a.market,a.prints,a.scratch)
        fx=PriorFX(ROOT.parent/'starquant/data/usdcny_frankfurter.json')
    started=time.monotonic();summary=[]
    for begin,end in WINDOWS:
        b,e=stamp(begin),stamp(end);schedule=[s for s in starts if b<=s<e]
        for policy in ('baseline','core'):
            key=begin+'-'+policy
            if a.policy and a.policy!=policy:continue
            if a.case and a.case!=key:continue
            directory=a.scratch/key;directory.mkdir();initial=D(10000)/fx(b)*D('.999')
            if PACKAGE=='spotquant':
                venue=HistoricalVenue(bars,b,initial,fx);venue.crowding_features=lambda:features
                from research.adoption_spot import risk_identity
                venue._adoption_risk=risk_identity(None)
                config=Config('1',str(directory),300,5,'demo','5000000')
                move=venue.advance
            else:
                venue=ResearchExchange(market,b,initial,fx=fx,initial_cny=D(10000),matcher='trade_print',
                    prints=tape,uid=12000,terminal_ms=e)
                venue.read_latency_ms,venue.latency_ms,venue.mark_gap=200,1000,'bound'
                config=Config('12000',str(directory),300,5)
                move=venue.advance_unattended
            reports=[];failure=None;case_started=time.monotonic()
            from contextlib import nullcontext
            with baseline() if policy=='baseline' else nullcontext(session) as runtime:
                for i,s in enumerate(schedule):
                    try:
                        move(s);r=runtime.run(config,venue,execute=True,monotonic=venue.monotonic,wait=venue.wait)
                        reports.append({k:r.get(k) for k in ('status','cleanup','cycles','errors','pending_intents',
                            'execution_unresolved','state_backup','session_archive','model_preview')})
                        reports[-1]['start_ms']=s
                        if r.get('pending_intents') or r.get('execution_unresolved'):
                            failure=dict(phase='session',start_ms=s,reason='unresolved finite execution',report=r);break
                    except Exception as exc:
                        failure=dict(phase='session',start_ms=s,error_type=type(exc).__name__,reason=str(exc));break
                if failure is None:
                    try:move(e)
                    except Exception as exc:failure=dict(phase='terminal',error_type=type(exc).__name__,reason=str(exc))
            with State(str(directory),config.scope) as state:
                pending=state.pending();ownership=state.get('positions') if PACKAGE=='spotquant' else state.get('entry_fill')
            if PACKAGE=='spotquant':
                final=venue.cash+venue.btc*venue.price
                row=dict(fills=venue.fills,daily=venue.daily,cash_usdt=venue.cash,btc=venue.btc,mdd=venue.mdd,
                    audit=audit(venue),price_model='high-before-low daily OHLC proxy, not actual minute/native')
            else:
                from research.rebuild import _final_mark
                try:mark=_final_mark(venue) if venue.q else D(0)
                except Exception:mark=None
                final=venue.wallet+venue.q*(mark-venue.entry) if mark is not None else None
                row=dict(trades=venue.trades,funding_ledger=venue.income,position=venue.q,fees=venue.fees,
                    wallet_usdt=venue.wallet,entry=venue.entry,
                    funding=venue.funding_paid,final_mark=mark,final_usdt=final,daily=[v for _,v in sorted(venue.daily.items())],
                    mdd=venue.mdd_envelope,mdd_close=venue.mdd_close,known_path=venue.known_path,
                    unknown_from=venue.unknown_from,hindsight_bounded=venue.hindsight_bounded,
                    bounded_minutes=venue.bounded_minutes,funnel=venue.funnel,
                    price_model='official minute mark; actual prints where present; explicit unresolved/bounded path retained')
                row['audit']=audit(serial(row),initial,mark) if final is not None else {'passed':False}
            row.update(identity=identity,case=key,window=[begin,end],initial_cny='10000',initial_usdt=initial,
                final_usdt=final,final_cny=final*fx(e)*D('.999') if final is not None else None,
                sessions=reports,session_count=len(reports),registered_session_count=len(schedule),failure=failure,
                pending_intents=pending,ownership=ownership,elapsed_seconds=time.monotonic()-case_started,
                qualification='NOT_QUALIFIED',native_verified=False)
            row['return_cny']=row['final_cny']/10000-1 if final is not None else None
            row['complete_finite']=failure is None and not pending and len(reports)==len(schedule) and row['audit']['passed']
            (a.out/(key+'.json')).write_text(json.dumps(serial(row),indent=2)+'\n')
            brief={k:row[k] for k in ('case','return_cny','mdd','complete_finite','session_count','elapsed_seconds','failure')}
            summary.append(brief);print(json.dumps(serial(brief)),flush=True)
    (a.out/'summary.json').write_text(json.dumps(serial(dict(identity=identity,results=summary,
        elapsed_seconds=time.monotonic()-started)),indent=2)+'\n')

if __name__=='__main__':main()
