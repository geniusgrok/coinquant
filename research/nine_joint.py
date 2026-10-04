"""Four preregistered coupled BTC account comparisons, finite and manual.

Separate worker processes reuse the two real finite sessions. Only one Coin
worker exists. Market inputs and parsed caches persist across serial cases;
wallets, durable identities and orders never cross account/case boundaries.
"""
import argparse
from datetime import datetime, timezone
from decimal import Decimal as D
import gzip
import json
import os
from pathlib import Path
import select
import subprocess
import sys
import tempfile
import time

from research import nine_routes as r, flow_risk as f


def quarter(stamp):
    day=datetime.fromtimestamp(stamp/1000,timezone.utc);month=1+3*((day.month-1)//3)
    begin=datetime(day.year,month,1,tzinfo=timezone.utc)
    end=datetime(day.year+1,1,1,tzinfo=timezone.utc) if month==10 else datetime(day.year,month+3,1,tzinfo=timezone.utc)
    return int(begin.timestamp()*1000),int(end.timestamp()*1000)


def windows(spec):
    info=spec['inputs']['neutral_coin'];raw=Path(info['path']).read_bytes()
    if r.sha(raw)!=info['sha256']:raise ValueError('original independently funded Coin account changed')
    row=json.loads(gzip.decompress(raw))['results']['incumbent']['base']
    entries=[];quantity=D(0)
    for trade in row['trades']:
        delta=D(trade['qty'])*(1 if trade['side']=='BUY' else -1)
        if quantity==0 and delta>0:entries.append(trade['time'])
        quantity+=delta
    selected=[]
    for early in (True,False):
        eligible=[stamp for stamp in entries if (stamp<1640995200000)==early]
        if eligible:selected.append(quarter(min(eligible)))
    return selected,dict(path=info['path'],sha256=info['sha256'],
        independent_new_campaigns=len(entries),selector='Earliest timestamp per registered era, no economic outcome selection.')


def daily_metrics(raw,bars):
    """Derive matching actual UTC closes, never session-tick pseudo closes."""
    spot={int(day):row for day,row in raw['accounts']['spot']['daily'].items()
          if row['timestamp_ms']==int(day)+f.DAY}
    coin={int(datetime.fromisoformat(row['date']).replace(tzinfo=timezone.utc).timestamp()*1000):row
          for row in raw['accounts']['coin']['daily']
          if row['stamp_ms']==int(datetime.fromisoformat(row['date']).replace(tzinfo=timezone.utc).timestamp()*1000)+f.DAY}
    begin,end=raw['window'];days=sorted(set(spot)&set(coin))
    curve={day:dict(equity_usdt=str(D(spot[day]['equity_usdt'])+D(coin[day]['equity_usdt'])))
           for day in days if begin-f.DAY<=day<end}
    metrics=r.portfolio_metrics(curve,{day:bar[3] for day,bar in bars.items()})
    metrics.update(basis='Matched original account ledgers at actual UTC midnight; no forward filling.',
                   matched_closes=len(curve),expected_closes=(end-begin)//f.DAY+1,
                   synchronized_continuous_mdd_proven=False)
    return metrics


def reuse_dependency(root,kind,source):
    """A completed old case proves the fatal missing-file branch was not taken."""
    paths=[kind+'quant','research/nine_worker.py','research/nine_routes.py',
           'research/session_account.py','research/session_exchange.py','research/session_market.py',
           'research/complete_perp.py','research/edge_spot.py']
    changed=subprocess.check_output(['git','-C',str(root),'diff','--name-only',source,'HEAD','--',*paths],text=True).splitlines()
    if not changed:return 'Identical economic dependencies.'
    if changed!=['research/nine_worker.py']:raise ValueError('completed baseline economic dependencies changed')
    old=subprocess.check_output(['git','-C',str(root),'show',source+':research/nine_worker.py'],text=True)
    new=(root/'research/nine_worker.py').read_text()
    fatal="                        if not origin.exists():raise ValueError('selected original print input missing; no download')"
    unknown="                        if not origin.exists():\n                            if suffix=='':\n                                own._day_ms,own._rows=day,None\n                                return None\n                            raise ValueError('selected original print input missing; no download')"
    if old.count(fatal)!=1 or old.replace(fatal,unknown)!=new:
        raise ValueError('completed-account reuse requires identical or exactly unreachable missing-ZIP handling')
    return 'Only fatal missing-ZIP branch returns original TradePrints unknown. Completed old accounts could not have taken fatal branch; all reached dependencies unchanged.'


class Peer:
    def __init__(self,root,kind,args,scratch):
        self.log=(scratch/(kind+'-worker.log')).open('w')
        command=[sys.executable,'-m','research.nine_worker','--kind',kind,
            '--market',str(args.spot_market if kind=='spot' else args.coin_market),
            '--prints',str(args.prints),'--fx',str(args.fx),'--features',str(args.features),
            '--scratch',str(scratch/kind)]
        self.process=subprocess.Popen(command,cwd=root,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
            stderr=self.log,bufsize=0)
        self.buffer=b'';self.deadline=time.monotonic()+1800
        self.loaded=self.read()

    def send(self,message):
        self.process.stdin.write((json.dumps(message,separators=(',',':'))+'\n').encode());self.process.stdin.flush()

    def read(self):
        while b'\n' not in self.buffer:
            remaining=min(60,self.deadline-time.monotonic())
            if remaining<=0 or not select.select([self.process.stdout],[],[],remaining)[0]:
                raise TimeoutError('finite offline worker/resource deadline; preserve partial results')
            chunk=os.read(self.process.stdout.fileno(),1048576)
            if not chunk:raise ValueError('offline worker ended; preserve stderr log')
            self.buffer+=chunk
        line,self.buffer=self.buffer.split(b'\n',1)
        message=json.loads(line)
        if message['event']=='fatal':raise ValueError('offline worker '+message['error']+': '+message['reason'])
        return message

    def close(self):
        if self.process.poll() is None:
            try:self.send(dict(command='stop'));self.process.wait(timeout=10)
            except (BrokenPipeError,subprocess.TimeoutExpired):self.process.terminate();self.process.wait(timeout=10)
        self.log.close()


class Coordinator:
    def __init__(self,peers,bars,source_sha):
        self.peers=peers;self.bars=bars;self.context_sha=source_sha

    def context(self,now):
        through=now//f.DAY*f.DAY
        keys=list(range(through-21*f.DAY,through,f.DAY))
        if not all(key in self.bars for key in keys):return None
        closes=[self.bars[key][3] for key in keys]
        return dict(completed_through_ms=through,available_ms=through+60000,
            source_sha256=self.context_sha,returns20=list(map(str,(b/a-1 for a,b in zip(closes,closes[1:])))),
            momentum20=str(closes[-1]/closes[0]-1))

    def record(self):
        equity=sum(D(s['equity_usdt']) for s in self.snapshots.values())
        fx=D(self.snapshots['spot']['fx']);cny=equity*fx*D('.999')
        self.peak=max(self.peak,cny);self.mdd=max(self.mdd,1-cny/self.peak)
        sample=dict(at_ms=self.now,equity_usdt=str(equity),equity_cny=str(cny),
            gross_notional_usdt=str(sum(D(s['gross_notional_usdt']) for s in self.snapshots.values())))
        self.curve.append(sample)
        self.daily[(self.now-1)//f.DAY*f.DAY]=sample

    def decision(self,kind,message):
        self.snapshots[kind]=message['snapshot'];proposal=message['proposal']
        context=self.context(self.now);accounts=[dict(self.snapshots[k]) for k in ('spot','coin')]
        if context:
            for account in accounts:
                account.update(momentum20=context['momentum20'],momentum_available_ms=context['available_ms'])
        other='coin' if kind=='spot' else 'spot'
        competitor=self.last_proposals.get(other)
        if competitor and (self.now-competitor['at_ms']>15000
                or competitor['_quantity_at_preflight']!=self.snapshots[other]['quantity_btc']):competitor=None
        decisions={rule:r.admission(accounts,proposal,self.now,rule,context,competitor) for rule in r.RULES}
        self.proposals.append(dict(at_ms=self.now,proposal=proposal,accounts=accounts,context=context,decisions=decisions))
        proposal=dict(proposal,_quantity_at_preflight=self.snapshots[kind]['quantity_btc'])
        self.last_proposals[kind]=proposal
        verdict=(dict(status='ADMIT_RESEARCH_PROPOSAL',rule=self.scenario)
            if self.scenario in ('baseline','uniform') else decisions[self.scenario])
        self.peers[kind].send(dict(command='decision',verdict=verdict))
        return self.peers[kind].read()

    def drive(self,events):
        """A tick happens only when every active worker has yielded its next time."""
        active=set(events)
        while active:
            for kind in tuple(active):
                message=events[kind]
                while message['event']=='proposal':message=self.decision(kind,message)
                events[kind]=message
                if message['event']=='done':
                    self.snapshots[kind]=message['snapshot'];active.remove(kind)
                elif message['event']!='advance':raise ValueError('unexpected finite worker event')
                else:self.snapshots[kind]=message['snapshot']
            if not active:break
            next_at=min(events[k]['target'] for k in active)
            if next_at<self.now:raise ValueError('causal common clock reversed')
            finished={k for k in active if events[k]['target']==next_at}
            for kind,peer in self.peers.items():
                peer.send(dict(command='tick',at=next_at,finish=kind in finished))
            for kind,peer in self.peers.items():
                answer=peer.read()
                if answer['event']!='snapshot':raise ValueError('tick did not return independently observed state')
                self.snapshots[kind]=answer['snapshot']
            self.now=next_at;self.record()
            for kind in finished:events[kind]=self.peers[kind].read()

    def case(self,scenario,begin,end,starts,out):
        self.scenario=scenario;self.now=begin;self.proposals=[];self.last_proposals={}
        self.snapshots={};self.peak=D(10000);self.mdd=D(0);self.curve=[];self.daily={}
        for kind,peer in self.peers.items():
            peer.send(dict(command='reset',scenario=scenario,begin=begin,end=end,case=out.name))
            message=peer.read()
            if message['event']!='ready':raise ValueError('independent wallet initialization failed')
            self.snapshots[kind]=message['snapshot']
        self.record()
        for index,start in enumerate(starts):
            for peer in self.peers.values():peer.send(dict(command='session',start=start))
            self.drive({kind:peer.read() for kind,peer in self.peers.items()})
            if index%10==0:print(json.dumps(dict(case=scenario,session=index,date=datetime.fromtimestamp(start/1000,timezone.utc).isoformat())),flush=True)
        for peer in self.peers.values():peer.send(dict(command='tick',at=end,finish=True))
        for kind,peer in self.peers.items():self.snapshots[kind]=peer.read()['snapshot']
        self.now=end;self.record()
        accounts={}
        for kind,peer in self.peers.items():
            peer.send(dict(command='final'));accounts[kind]=peer.read()['row']
        changed={row['proposal']['id'] for row in self.proposals
            if scenario in r.RULES and row['decisions'][scenario]['status']=='BLOCK_NEW_RISK'}
        census={rule:dict(blocked_independent_proposals=len({x['proposal']['id'] for x in self.proposals if x['decisions'][rule]['status']=='BLOCK_NEW_RISK'}),
            unknown_proposals=sum(x['decisions'][rule]['status']=='BLOCK_UNKNOWN' for x in self.proposals),
            actual_competitions=sum(x['decisions'][rule].get('competition',False) for x in self.proposals)) for rule in r.RULES}
        result=dict(format='btc-nine-joint-account-v1',scenario=scenario,window=[begin,end],
            final_cny=str(sum(D(a['final_cny']) for a in accounts.values())),
            synchronized_observed_mdd=str(self.mdd),joint_continuous_mdd_verified=False,
            daily=self.daily,curve=self.curve,accounts=accounts,proposal_ledger=self.proposals,
            changed_commitments=len(changed),census=census,
            finished=all(a['finished'] for a in accounts.values()),
            complete=False,cagr=None,curve_rescaled=False,transfers=0,
            timing='Shared causal virtual API ticks; original finite session/Lifecycle in both independent workers. Research bridge, not old canonical-source equality.')
        out.parent.mkdir(parents=True,exist_ok=True)
        with gzip.open(out,'wt') as stream:json.dump(r.serial(result),stream,separators=(',',':'))
        return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('spot-repo','coin-repo','spot-market','coin-market','prints','fx','features','schedule','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--reuse-completed',type=Path)
    args=parser.parse_args(argv)
    if args.out.exists():raise ValueError('preserve old measurement outputs')
    spec=json.loads(r.SPEC.read_text());chosen,binding=windows(spec)
    starts=json.loads(args.schedule.read_text())['primary']['starts_ms']
    if r.sha(json.dumps(starts,separators=(',',':')).encode())!=spec['contract']['schedule_sha256']:raise ValueError('original starts changed')
    if r.sha(args.features.read_bytes())!=spec['inputs']['features_sha256']:raise ValueError('original feature identity changed')
    args.out.mkdir(parents=True);began=time.monotonic();inputs=[]
    bars=f.market(args.spot_market,f.DAY,inputs)
    context_sha=r.sha(json.dumps(inputs,sort_keys=True).encode())
    report=dict(format='btc-nine-joint-screen-v1',spec_sha256=r.sha(r.SPEC.read_bytes()),
        selector_binding=binding,selected_windows=chosen,market_inputs=inputs,rows=[],
        original795_replays=0,large_vault_scans=0,new_accounts=0,new_sessions=0,
        native_qualified=False,runtime_promoted=False)
    previous=json.loads(args.reuse_completed.read_text()) if args.reuse_completed else None
    if previous and (previous['spec_sha256']!=report['spec_sha256'] or previous['selected_windows']!=chosen):
        raise ValueError('completed-case reuse contract changed')
    peers={};scratch=Path(tempfile.mkdtemp(prefix='btc-nine-pair-',dir='/tmp'))
    report['scratch_path']=str(scratch)
    try:
        if True:
            for kind,root in (('spot',args.spot_repo),('coin',args.coin_repo)):
                peers[kind]=Peer(root,kind,args,scratch)
            report['sources']={kind:peer.loaded['source'] for kind,peer in peers.items()}
            coordinator=Coordinator(peers,bars,context_sha)
            for index,(begin,end) in enumerate(chosen):
                subset=[stamp for stamp in starts if begin<=stamp<end]
                if not subset or len(subset)>40:raise ValueError('registered finite session range invalid')
                cases={};report['rows'].append(dict(window=[begin,end],cases=cases))
                for scenario in ('baseline','uniform',*r.RULES):
                    if time.monotonic()-began>=1800:
                        cases[scenario]=dict(status='RESOURCE_BUDGET_EXHAUSTED');continue
                    if scenario in r.RULES and cases['baseline']['census'][scenario]['blocked_independent_proposals']==0:
                        cases[scenario]=dict(status='SUPPORT_PENDING',reason='No known legal baseline new-risk effect; no zero-treatment account.',census=cases['baseline']['census'][scenario]);continue
                    path=args.out/f'window-{index}-{scenario}.json.gz'
                    old=previous['rows'][index]['cases'].get(scenario) if previous and index<len(previous['rows']) else None
                    if old and old.get('raw_file'):
                        old_path=args.reuse_completed.parent/old['raw_file'];old_bytes=old_path.read_bytes()
                        if r.sha(old_bytes)!=old['raw_sha256']:raise ValueError('completed account bytes changed')
                        reuse_notes={kind:reuse_dependency(root,kind,previous['sources'][kind]['git_head'])
                            for kind,root in (('spot',args.spot_repo),('coin',args.coin_repo))}
                        raw=json.loads(gzip.decompress(old_bytes));path.write_bytes(old_bytes)
                    else:raw=coordinator.case(scenario,begin,end,subset,path)
                    metrics=daily_metrics(raw,bars)
                    row={key:raw[key] for key in ('final_cny','synchronized_observed_mdd','finished','changed_commitments','census')}
                    row.update(raw_file=path.name,raw_sha256=r.sha(path.read_bytes()),metrics=metrics)
                    if scenario in r.RULES:
                        row['gates']=r.pair_gate(row,cases['baseline'],cases['uniform'])
                        row['status']='WINDOW_PASS' if all(row['gates'][key] for key in ('audits','actual_action','risk_wealth','beats_simple')) else 'WINDOW_REJECT' if row['changed_commitments'] else 'SUPPORT_PENDING'
                    cases[scenario]=row
                    if old and old.get('raw_file'):
                        row['reused_original_producer']=previous['sources'];row['reuse_dependency']=reuse_notes
                    else:report['new_accounts']+=2;report['new_sessions']+=2*len(subset)
                    (args.out/'summary.json').write_text(json.dumps(r.serial(report),indent=2)+'\n')
                    print(json.dumps(dict(window=index,scenario=scenario,**row)),flush=True)
                (args.out/'summary.json').write_text(json.dumps(r.serial(report),indent=2)+'\n')
            report['decisions']={rule:('ACCOUNT_ENTRANT' if len(report['rows'])==2 and all(row['cases'][rule].get('status')=='WINDOW_PASS' for row in report['rows']) else 'SUPPORT_PENDING' if any(row['cases'][rule].get('status')=='SUPPORT_PENDING' for row in report['rows']) else 'REJECT_MECHANISM') for rule in r.RULES}
            for kind,peer in peers.items():peer.close()
            for kind in peers:
                (args.out/(kind+'-worker.log')).write_bytes((scratch/(kind+'-worker.log')).read_bytes())
    except BaseException:
        for kind,peer in peers.items():
            peer.close()
            if Path(peer.log.name).exists():(args.out/(kind+'-worker-failed.log')).write_bytes(Path(peer.log.name).read_bytes())
        report.update(status='FAILED_PARTIAL',elapsed_wall_seconds=time.monotonic()-began)
        (args.out/'summary-failed.json').write_text(json.dumps(r.serial(report),indent=2)+'\n')
        raise
    report.update(status='FINITE_SCREEN_COMPLETE',elapsed_wall_seconds=time.monotonic()-began)
    (args.out/'summary.json').write_text(json.dumps(r.serial(report),indent=2)+'\n')
    print(json.dumps(dict(decisions=report['decisions'],new_accounts=report['new_accounts'],new_sessions=report['new_sessions'],wall_seconds=report['elapsed_wall_seconds'])))


if __name__=='__main__':main()
