"""One independently funded offline account behind the original finite run.

JSON-line IPC is research-only. The coordinator synchronizes exchange time;
production session, sizing, reconciliation, protection and fills are reused.
"""
import argparse
from collections import OrderedDict
from decimal import Decimal as D
from functools import lru_cache
import json
from pathlib import Path
import sqlite3
import sys
import traceback

from research import nine_routes as r


def emit(value):
    sys.stdout.write(json.dumps(r.serial(value),separators=(',',':'))+'\n');sys.stdout.flush()


def receive():
    line=sys.stdin.readline()
    if not line: raise EOFError('research coordinator disconnected')
    return json.loads(line)


class Worker:
    def __init__(self,args):
        self.args=args;self.kind=args.kind;self.state=None;self.sessions=[];self.in_tick=False
        self.e=None;self.directory=None;self.active=False
        if self.kind=='spot':
            from research import complete_spot as meter
            from research.market import load_daily
            from research.edge_features import FeatureBook
            from research.edge_spot import FEATURE_SHA256
            from spotquant import session,preview
            from spotquant.state import State
            self.meter=meter;self.session=session;self.preview=preview;self.BaseState=State
            self.bars=load_daily(args.market/'klines',1789862400000,require_through=1789862400000)
            self.fx=meter.PriorFX(args.fx)
            self.features=FeatureBook(args.features,FEATURE_SHA256)
            self.portfolio=preview.decision
            session.portfolio=self.spot_policy
        else:
            from coinquant import session,lifecycle,campaign
            from coinquant.state import State
            from research import complete_perp as meter,session_market
            from research.unified_perp import PriorFX
            self.meter=meter;self.session=session;self.BaseState=State
            self.fx=PriorFX(args.fx);self.market=session_market.load_base(args.market)
            self.market._load_month=lru_cache(maxsize=8)(self.market._load_month)
            # Verify each selected immutable input once, invalidate on metadata change.
            checksum=session_market._checksum;verified={}
            def cached_checksum(path):
                stat=path.stat();key=(str(path),stat.st_dev,stat.st_ino,stat.st_size,stat.st_mtime_ns)
                if key not in verified:verified[key]=checksum(path)
                return verified[key]
            session_market._checksum=cached_checksum
            self.verified=verified
            class Prints(session_market.TradePrints):
                def __init__(own,root,originals):
                    super().__init__(root);root.mkdir(parents=True);own.originals=originals;own.days=OrderedDict()
                def _load(own,day):
                    if day in own.days:
                        own.days.move_to_end(day);own._day_ms=day;own._rows=own.days[day];return own._rows
                    from datetime import datetime,timezone
                    name=f'BTCUSDT-aggTrades-{datetime.fromtimestamp(day/1000,timezone.utc):%Y-%m-%d}.zip'
                    for suffix in ('','.CHECKSUM'):
                        origin=own.originals/(name+suffix);target=own.root/(name+suffix)
                        if not origin.exists():raise ValueError('selected original print input missing; no download')
                        if not target.exists():target.symlink_to(origin)
                    rows=super()._load(day);own.days[day]=rows
                    while len(own.days)>3:own.days.popitem(last=False)
                    return rows
            self.tape=Prints(args.scratch/'prints',args.prints)
            self.campaign=campaign.Campaign;self.entry_preview=lifecycle.entry_preview
            lifecycle.entry_preview=self.coin_policy
            worker=self
            class UniformCampaign(campaign.Campaign):
                def entry_fraction(model,friction):
                    value=super().entry_fraction(friction)
                    return value*(D('.75') if worker.scenario=='uniform' else D(1))
            from coinquant import linear_preview
            linear_preview.Campaign=UniformCampaign
        worker=self
        class TrackedState(self.BaseState):
            def __enter__(state):
                value=super().__enter__();worker.state=state;return value
            def __exit__(state,*args):
                worker.state=None;return super().__exit__(*args)
        self.session.State=TrackedState

    def meta(self,key):
        if self.state is not None:return self.state.get(key)
        if not self.directory or not (self.directory/'intents.sqlite').exists():return None
        with sqlite3.connect('file:'+str(self.directory/'intents.sqlite')+'?mode=ro',uri=True) as db:
            row=db.execute('SELECT value FROM meta WHERE key=?',(key,)).fetchone()
            return json.loads(row[0]) if row else None

    def reset(self,command):
        self.scenario=command['scenario'];self.begin=command['begin'];self.end=command['end']
        self.directory=self.args.scratch/command['case'];self.sessions=[];self.active=False
        self.initial=D(5000)/self.fx(self.begin)*D('.999')
        if self.kind=='spot':
            from research.session_account import HistoricalVenue
            self.e=HistoricalVenue(self.bars,self.begin,self.initial,self.fx)
            self.e.crowding_features=lambda:self.features
            from research.adoption_spot import risk_identity
            self.e._adoption_risk=risk_identity(None)
            self.original_move=self.e.advance
            self.e.advance=self.move
            self.features.filters={'blocked':0,'missing':0}
        else:
            self.e=self.meter.ResearchExchange(self.market,self.begin,self.initial,fx=self.fx,
                initial_cny=D(5000),matcher='trade_print',prints=self.tape,uid=12000,terminal_ms=self.end)
            self.e.read_latency_ms,self.e.latency_ms,self.e.mark_gap=200,1000,'bound'
            self.original_move=self.e.advance_unattended
            self.original_advance=self.e._advance
            self.e._advance=self.move

    def move(self,target):
        if self.in_tick:
            return self.original_advance(target) if self.kind=='coin' else self.original_move(target)
        if target<self.e.now_ms:raise ValueError('joint exchange clock reversed')
        emit(dict(event='advance',target=target,snapshot=self.snapshot()))
        while True:
            command=receive()
            if command['command']!='tick':raise ValueError('expected causal exchange tick')
            self.tick(command['at'])
            emit(dict(event='snapshot',snapshot=self.snapshot()))
            if command['finish']:return

    def tick(self,at):
        self.in_tick=True
        try:self.original_move(at)
        finally:self.in_tick=False

    def snapshot(self):
        e=self.e;pending=bool(self.state.pending()) if self.state is not None else bool(self.last_report.get('pending_intents',0)) if hasattr(self,'last_report') else False
        reserve=reserve_risk=D(0)
        if self.kind=='spot':
            q=e.btc;mark=e.price;equity=e.cash+q*mark
            stops=[a for a in e.orders.values() if a['type']=='STOP_LOSS' and a['status']=='NEW']
            protected=q==0 or sum((D(a['quantity']) for a in stops),D(0))+D('1e-8')>=q
            risk=sum(D(a['quantity'])*max(D(0),mark-D(a['stopPrice'])) for a in stops)
            if not protected:risk=max(risk,q*mark)
            # All synthetic fills must match this account's own durable allocations.
            positions=self.meta('positions') or {}
            owned=q==0 or abs(sum((D(p['qty']) for p in positions.values() if p),D(0))-q)<=D('1e-8')
            costs=2*e.fee*q*mark
        else:
            q=e.q
            from coinquant.types import Unknown
            try:mark=e._mark_state()[1]
            except Unknown:
                if q:raise
                # Explicit offline cold cash has no BTC to value. A missing initial
                # pre-2020 mark remains0/unknown, never a fabricated market quote.
                mark=D(0)
            equity=e.wallet+(q*(mark-e.entry) if q else D(0))
            algos=e._working_algos()
            stops=[a for a in algos if a['orderType']=='STOP_MARKET' and a.get('closePosition') is True and a['side']==('SELL' if q>0 else 'BUY')]
            takes=[a for a in algos if a['orderType']=='TAKE_PROFIT_MARKET' and a.get('closePosition') is True]
            liquidation=D(e._position(mark)['liquidationPrice']) if q else D(0)
            protected=q==0 or bool(stops and takes and any(D(a['triggerPrice'])>liquidation for a in stops))
            risk=abs(q)*max(D(0),mark-max((D(a['triggerPrice']) for a in stops),default=D(0)))
            checkpoint=self.meta('linear_campaign')
            owned=q==0 or bool(checkpoint and checkpoint['body']['position_campaign'] is not None)
            costs=2*e.fee*abs(q)*mark
            fill=self.meta('entry_fill');protection=self.meta('position_protection')
            if self.active and fill and fill.get('session')==self.session_start and protection:
                left=max(D(0),D(fill['requested'])-abs(q))
                reserve=left*mark;reserve_risk=left*max(D(0),mark-D(protection['stop']))+2*e.fee*reserve
        return r.serial(dict(kind=self.kind,symbol='BTCUSDT',receipt_ms=e.now_ms,
            equity_usdt=equity,gross_notional_usdt=abs(q)*mark,stop_risk_usdt=risk+costs,
            reserved_notional_usdt=reserve,reserved_stop_risk_usdt=reserve_risk,
            owned=owned,protected=protected,pending=pending,
            quantity_btc=q,mark_usdt=mark,fx=self.fx(e.now_ms),
            ownership_basis='Explicit independent offline cold wallet plus durable runtime state; not native proof.'))

    def ask(self,proposal):
        emit(dict(event='proposal',proposal=proposal,snapshot=self.snapshot()))
        command=receive()
        if command['command']!='decision':raise ValueError('expected new-risk decision')
        return command['verdict']

    def spot_policy(self,views,owned,snapshot,**kwargs):
        result=self.portfolio(views,owned,snapshot,**kwargs)
        from research.edge_spot import resize
        for order in list(result['orders']):
            if order['side']!='BUY':continue
            quote=D(order['quoteOrderQty']);mark=D(snapshot['avg_price'])
            stops=[D(result['sleeves'][str(w)]['protection']['stopPrice']) for w in order['sleeves']]
            loss=quote*max(D(0),1-min(stops)/mark)+2*self.e.fee*quote
            proposal=dict(kind='spot',symbol='BTCUSDT',side='BUY',at_ms=self.e.now_ms,
                id='spot:'+str(views[order['sleeves'][0]].last)+':'+','.join(map(str,order['sleeves'])),
                gross_notional_usdt=str(quote),stop_risk_usdt=str(loss),feasible=True)
            verdict=self.ask(proposal)
            factor=D('.75') if self.scenario=='uniform' else D(0) if verdict['status']!='ADMIT_RESEARCH_PROPOSAL' else D(1)
            if factor!=1:resize(result,order,quote*factor)
        protection_views={w:self.preview.decision_view(v,kwargs['positions'].get(w),kwargs['owners']) for w,v in views.items()}
        result['protections']=self.preview._merge_protections({w:result['sleeves'][str(w)] for w in views},protection_views,snapshot,next(iter(protection_views.values())))
        result['order']=result['orders'][0] if result['orders'] else None
        return result

    def coin_policy(self,reader,model,snapshot):
        plan=self.entry_preview(reader,model,snapshot)
        if D(plan['quantity_btc'])>0:
            mark=D(plan['entry_estimate']);quantity=D(plan['requested_btc'])
            proposal=dict(kind='coin',symbol='BTCUSDT',side='BUY',at_ms=self.e.now_ms,
                id='coin:'+str(plan['campaign']),gross_notional_usdt=str(quantity*mark),
                stop_risk_usdt=str(quantity*max(D(0),mark-D(plan['stop']))+2*self.e.fee*quantity*mark),feasible=True)
            verdict=self.ask(proposal)
            if self.scenario not in ('baseline','uniform') and verdict['status']!='ADMIT_RESEARCH_PROPOSAL':
                plan.update(quantity_btc='0',requested_btc='0',allocated_margin_usdt='0',constraint='joint-'+verdict['status'])
        return plan

    def run_session(self,start):
        self.session_start=start;self.active=True
        self.move(start)
        if self.kind=='spot':
            from spotquant.config import Config
            config=Config('1',str(self.directory),300,5,'demo','5000000')
        else:
            from coinquant.config import Config
            config=Config('12000',str(self.directory),300,5)
        report=self.session.run(config,self.e,execute=True,monotonic=self.e.monotonic,wait=self.e.wait)
        self.last_report=report;self.active=False
        if self.kind=='spot':
            from research.restore_check import check
            archive=check(report['session_archive']['report']) if 'session_archive' in report else {}
            verified=bool(archive.get('integrity_verified'))
            unresolved=bool(report['pending_intents']) or not verified
        else:
            verified=report.get('state_backup')=='saved'
            unresolved=bool(report.get('execution_unresolved')) or not verified
        self.sessions.append(dict(start_ms=start,ended_ms=self.e.now_ms,status=report['status'],
            pending_intents=report.get('pending_intents',0),cleanup=report.get('cleanup'),
            archive_or_backup_verified=verified,execution_unresolved=unresolved,
            errors=report.get('errors'),cycles=report.get('cycles')))
        emit(dict(event='done',snapshot=self.snapshot(),session=self.sessions[-1]))

    def result(self):
        e=self.e;snap=self.snapshot()
        if self.kind=='spot':
            from research.session_account import audit
            money=audit(e)
            with sqlite3.connect('file:'+str(self.directory/'intents.sqlite')+'?mode=ro',uri=True) as db:
                allocations=list(db.execute('SELECT id,payload,status,result FROM intents ORDER BY updated'))
            row=dict(fills=e.fills,allocations=allocations,daily=e.daily,cash_usdt=e.cash,btc=e.btc,mdd=e.mdd)
        else:
            from research.comparison_report import audit
            row=dict(trades=e.trades,funding_ledger=e.income,position=e.q,fees=e.fees,funding=e.funding_paid,
                daily=[v for _,v in sorted(e.daily.items())],final_mark=snap['mark_usdt'],
                known_path=e.known_path,unknown_from=e.unknown_from,hindsight_bounded=e.hindsight_bounded,
                bounded_minutes=e.bounded_minutes,mdd=e.mdd_envelope)
            row['final_usdt']=snap['equity_usdt']
            money=audit(r.serial(row),self.initial,D(snap['mark_usdt']))
        row.update(kind=self.kind,scenario=self.scenario,initial_cny='5000',initial_usdt=str(self.initial),
            final_usdt=snap['equity_usdt'],final_cny=str(D(snap['equity_usdt'])*self.fx(e.now_ms)*D('.999')),
            sessions=self.sessions,audit=money,final_snapshot=snap,
            finished=money['passed'] and all(s['archive_or_backup_verified'] and not s['execution_unresolved'] for s in self.sessions)
                and (self.kind=='spot' or e.known_path),
            source=self.args.source,complete=False,cagr=None,native_execution_verified=False)
        return row


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--kind',choices=('spot','coin'),required=True)
    for name in ('market','prints','fx','features','scratch'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();args.scratch.mkdir(parents=True)
    from research.rebuild import source_identity
    args.source=source_identity()
    if args.source['dirty']:raise ValueError('freeze producer source')
    worker=Worker(args);emit(dict(event='loaded',source=args.source))
    while True:
        command=receive();kind=command['command']
        if kind=='reset':
            worker.reset(command);worker.last_report={};emit(dict(event='ready',snapshot=worker.snapshot()))
        elif kind=='session':worker.run_session(command['start'])
        elif kind=='tick':worker.tick(command['at']);emit(dict(event='snapshot',snapshot=worker.snapshot()))
        elif kind=='final':emit(dict(event='result',row=worker.result()))
        elif kind=='stop':return
        else:raise ValueError('unknown coordinator command')


if __name__=='__main__':
    try:main()
    except BaseException as error:
        emit(dict(event='fatal',error=type(error).__name__,reason=str(error)));traceback.print_exc(file=sys.stderr);raise
