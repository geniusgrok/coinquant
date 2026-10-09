"""Registered default-runtime paired replay, derived from the restored PR72 producer."""
import argparse
from datetime import datetime, timezone
from decimal import Decimal as D
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time

HERE=Path(__file__).resolve().parent
ROOT=Path(os.environ['CQR_RUNTIME_ROOT']).resolve()
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(HERE))
from coinquant import campaign, session
from coinquant.config import Config
from coinquant.state import State
from coinquant.types import Unknown
from research import complete_perp
from research.complete_perp import ResearchExchange
from research.comparison_report import audit
from research.data_loader import setup, release_private_bins
from research.dfii10_history import History
from research.session_exchange import SessionExchange
from research.unified_perp import PriorFX
from research.replay_checkpoint import decode,digest,restore_venue,snapshot_venue,source_fingerprint
DAY=86400000
HEAD=os.environ['CQR_RUNTIME_SHA']
VERSION='coinquant-default-runtime-paired-replay-v2'


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as src:
        for block in iter(lambda:src.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()


def plain(value):
    from collections import deque
    from dataclasses import asdict,is_dataclass
    if is_dataclass(value):return plain(asdict(value))
    if isinstance(value,D):return str(value)
    if isinstance(value,dict):return {str(k):plain(v) for k,v in value.items()}
    if isinstance(value,(tuple,list,deque)):return [plain(v) for v in value]
    if isinstance(value,set):return [plain(v) for v in sorted(value)]
    return value


def write(path,value):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():raise ValueError('preserve existing receipt '+str(path))
    opener=gzip.open if path.suffix=='.gz' else open
    with opener(path,'wt') as dst:
        json.dump(plain(value),dst,separators=(',',':'),allow_nan=False)
        dst.write('\n')


def read(path):
    path=Path(path)
    opener=gzip.open if path.suffix=='.gz' else open
    with opener(path,'rt') as src:return json.load(src)


def open_path_trace(scratch,segment):
    path=scratch/'path-traces'/f'segment-{segment:03d}.jsonl.gz'
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():raise FileExistsError('preserve original path trace')
    buffer=tempfile.SpooledTemporaryFile(max_size=64*1024*1024,mode='w+b')
    stream=io.TextIOWrapper(gzip.GzipFile(filename='',fileobj=buffer,mode='wb'),encoding='utf-8')
    complete_perp.PATH_TRACE=stream
    return path,stream,buffer


def finish_path_trace(path,stream,buffer):
    # The compressed stream has no long-lived named workspace file. Publish only
    # after the gzip footer exists, then retain the original full readback gate.
    stream.close()
    buffer.seek(0)
    temporary=path.with_name(path.name+'.publishing')
    with temporary.open('xb') as destination:
        shutil.copyfileobj(buffer,destination)
        destination.flush()
        os.fsync(destination.fileno())
        written=os.fstat(destination.fileno())
    os.link(temporary,path)  # Exclusive final name; never overwrite an old trace.
    actual=path.stat()
    if (actual.st_dev,actual.st_ino,actual.st_size)!=(written.st_dev,written.st_ino,written.st_size):
        raise ValueError('published path differs from the completed trace file')
    temporary.unlink()
    directory=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(directory)
    finally:os.close(directory)
    buffer.close()


def path_trace_receipt(path,before,venue):
    after=venue._path_audit if venue is not None else None
    row=dict(path=str(path),bytes=path.stat().st_size,sha256=sha(path),
        first_sequence=None,last_sequence=None,points=0,sequence_before=before['count'],
        sequence_after=after['count'] if after else None,rolling_before=before['rolling_sha256'],
        rolling_after=after['rolling_sha256'] if after else None,verified=False)
    rolling=before['rolling_sha256'];cursor=before['count']
    try:
        with gzip.open(path,'rt',encoding='utf-8') as stream:
            for line in stream:
                point=json.loads(line)
                if len(point)!=10 or point[0]!=cursor+1:
                    raise ValueError('path trace sequence/row shape mismatch')
                encoded=json.dumps(point[1:5],separators=(',',':')).encode()
                rolling=hashlib.sha256(bytes.fromhex(rolling)+encoded).hexdigest()
                cursor=point[0]
                if row['first_sequence'] is None:row['first_sequence']=cursor
                row['last_sequence']=cursor;row['points']+=1
        row['verified']=bool(after and cursor==after['count'] and rolling==after['rolling_sha256'])
        if not row['verified']:row['error']='path trace does not match original path audit boundary'
    except Exception as exc:
        row['error']=type(exc).__name__+': '+str(exc)
    row['trace_rolling_after']=rolling
    return row


def registered_arm(spec):
    matches=[name for name,head in spec['runtime_heads'].items()
             if head==HEAD and Path(spec['runtime_roots'][name]).resolve()==ROOT]
    if len(matches)!=1:raise ValueError('runtime root/head must match exactly one registered arm')
    return matches[0]


def current_source(spec):
    expected=read(spec['source_files_by_arm'][registered_arm(spec)])
    actual={str(p.relative_to(ROOT)):sha(p) for p in sorted((ROOT/'coinquant').glob('*.py'))}
    if actual!=expected:raise ValueError('frozen production bytes changed')
    for name,module in sys.modules.items():
        if name=='coinquant' or name.startswith('coinquant.'):
            path=Path(module.__file__).resolve()
            if not path.is_relative_to(ROOT/'coinquant'):raise ValueError('foreign production import: '+name)
    from coinquant.binance import Binance
    if not issubclass(ResearchExchange,Binance):raise ValueError('foreign Binance kernel')
    return dict(git_head=HEAD,files=actual,runtime_module=str(Path(session.__file__).resolve()),
        tooling_files={str(p.relative_to(HERE)):sha(p) for p in sorted((HERE/'research').glob('*.py'))},
        producer_sha256=sha(__file__),source_sha256=source_fingerprint())


def sidecars(spec):
    return {str(path.resolve()):path.read_text() for root in ('prints','market') for path in
        sorted(Path(spec[root]).rglob('*.CHECKSUM'))}


def dependencies(spec,spec_path,market,tape,fx,starts,source):
    history=History()
    SessionExchange._dfii10_history=history
    input_packet=dict(specification_sha256=sha(spec_path),schedule_sha256=sha(spec['schedule']),fx_sha256=fx.sha256,
        market_root=str(market.root.resolve()),prints_root=str(Path(spec['prints']).resolve()),
        market_identity_sha256=digest(market.identity),market_values_sha256=digest((market.h4,market.funding,market.funding_grid)),
        macro_sha256=digest((history.dates,history.updates,history.times,history.counts)),
        official_sidecars=sidecars(spec),starts_ms=starts,terminal_ms=spec['terminal_ms'],initial_cny='10000',
        parsed_pack_roots=spec['parsed_pack_roots'],shared_parsed_cache=spec['shared_parsed_cache'],parser_sha256=spec['parser_sha256'],
        qualified_metadata_sha256=sha(spec['qualified_metadata']))
    strategy=dict(kind=VERSION,primary_risk=campaign.PRIMARY_RISK,macro_risk=campaign.MACRO_RISK,
        session_seconds=300,poll_seconds=5,read_latency_ms=200,write_latency_ms=1000,mark_gap='bound',matcher='trade_print',uid='12000',
        **spec['risk_by_arm'][registered_arm(spec)])
    binding=dict(source_sha256=source['source_sha256'],strategy_sha256=digest(strategy),input_sha256=digest(input_packet),
        schedule_sha256=input_packet['schedule_sha256'],producer_sha256=source['producer_sha256'])
    return binding,input_packet,strategy


def checkpoint(venue,config,binding,reports,journal_path,scratch):
    with journal_path.open('rb') as stream:os.fsync(stream.fileno())
    saved=snapshot_venue(venue,binding=binding,config=config,session_report=reports[-1])
    packet=dict(version=VERSION,binding=binding,state_directory=config.state_dir,
        cursor=len(reports),starts_ms=[r['start_ms'] for r in reports],
        reports=dict(path=str(journal_path),sha256=sha(journal_path),count=len(reports)),venue=saved)
    envelope=dict(body=packet,sha256=digest(packet))
    path=scratch/'checkpoints'/f'cursor-{len(reports):06d}.json.gz'
    write(path,envelope)
    return dict(path=str(path),sha256=sha(path),envelope_sha256=envelope['sha256'],cursor=len(reports),
        durable_sqlite_sha256=decode(saved['body'])['account']['durable_sha256'])


def restore(previous,spec,binding,config,starts,journal_path,venue):
    if previous['complete'] or not previous['can_resume'] or previous['failure'] is not None:
        raise ValueError('requires original safe-boundary resumable receipt')
    last=previous['last_checkpoint']
    if previous['binding']!=binding or sha(last['path'])!=last['sha256']:
        raise ValueError('checkpoint source/input binding changed')
    envelope=read(last['path']);saved=envelope['body']
    if digest(saved)!=envelope['sha256'] or envelope['sha256']!=last['envelope_sha256']:
        raise ValueError('checkpoint digest mismatch')
    if saved['version']!=VERSION or saved['binding']!=binding or saved['state_directory']!=config.state_dir or saved['reports']!=previous['reports']:
        raise ValueError('checkpoint original account mismatch')
    if saved['reports']['path']!=str(journal_path) or sha(journal_path)!=saved['reports']['sha256']:
        raise ValueError('original report prefix changed; no truncation')
    reports=[json.loads(line) for line in journal_path.read_text().splitlines()]
    cursor=saved['cursor']
    if cursor!=previous['session_count'] or len(reports)!=cursor or saved['starts_ms']!=starts[:cursor] or [r['start_ms'] for r in reports]!=starts[:cursor]:
        raise ValueError('original full schedule/cursor mismatch')
    restore_venue(venue,saved['venue'],binding=binding,config=config)
    trace=previous['path_trace']
    if (not trace['verified'] or trace['segment_failed']
            or Path(trace['path']).stat().st_size!=trace['bytes'] or sha(trace['path'])!=trace['sha256']
            or trace['sequence_after']!=venue._path_audit['count']
            or trace['rolling_after']!=venue._path_audit['rolling_sha256']):
        raise ValueError('original path trace prefix changed')
    return reports,last


def financial(venue,initial):
    if venue.q:
        try:mark=venue._mark_state()[1]
        except Unknown:
            open_ms,_=venue._completed_minute();row=venue.market.minute('mark',open_ms)
            if row is None:raise
            mark=row[3]
    else:mark=D(0)
    final=venue.wallet+venue.q*(mark-venue.entry)
    row=dict(wallet_usdt=venue.wallet,quantity_btc=venue.q,position=venue.q,entry=venue.entry,margin=venue.margin,
        fees=venue.fees,funding=venue.funding_paid,trades=venue.trades,funding_ledger=venue.income,final_mark=mark,
        final_usdt=final,final_cny=final*venue.fx(venue.now_ms)*D('.999'),daily=[v for _,v in sorted(venue.daily.items())],
        daily_cny=venue.daily_cny,mdd=venue.mdd_envelope,mdd_close=venue.mdd_close,
        mdd_close_at=venue.mdd_close_at,mdd_envelope_at=venue.mdd_envelope_at,path_audit=venue._path_audit,peak_cny=venue.peak_cny,
        peak_envelope_cny=venue.peak_envelope_cny,known_path=venue.known_path,unknown_from=venue.unknown_from,
        hindsight_bounded=venue.hindsight_bounded,bounded_minutes=venue.bounded_minutes,funnel=venue.funnel,
        orders=venue.orders,algos=venue.algos,sent=venue.sent,now_ms=venue.now_ms,
        loaded_minute_files=venue.market.loaded,loaded_print_files=venue.prints.loaded,
        input_qualification_reuse=venue.market.qualification_summary)
    row['audit']=audit(plain(row),initial,mark)
    if venue._path_audit['envelope']['mdd'] != venue.mdd_envelope or venue._path_audit['close']['mdd'] != venue.mdd_close:
        raise ValueError('independent continuous simulated path audit disagrees')
    return row


def main():
    started=time.monotonic()
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',required=True,choices=('start','resume'))
    parser.add_argument('--spec',required=True,type=Path)
    parser.add_argument('--scratch',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--previous',type=Path)
    parser.add_argument('--limit',type=int,choices=(6,))
    args=parser.parse_args()
    args.spec,args.scratch,args.out=args.spec.resolve(),args.scratch.resolve(),args.out.resolve()
    if args.out.exists():raise ValueError('preserve original segment receipt')
    row=dict(version=VERSION,mode=args.mode,process_pid=os.getpid(),
        started_at=datetime.now(timezone.utc).isoformat(),complete=False,can_resume=False,failure=None,stop_reason=None,
        no_live_account=True,no_state_reset=True,qualification='NOT_QUALIFIED',native_verified=False,
        state_directory=str(args.scratch/'state'),partial_has_terminal_return_or_final_fx=False)
    phase='admission';reports=[];prior_elapsed=0;segment=1;newly=0;last=None;safe=False;venue=None
    trace_path=trace=trace_before=trace_buffer=None
    requested=[False]
    def request_stop(_signum,_frame):requested[0]=True
    signal.signal(signal.SIGTERM,request_stop);signal.signal(signal.SIGINT,request_stop)
    try:
        spec=read(args.spec)
        arm=registered_arm(spec)
        if (spec['version']!=VERSION or spec['initial_cny']!='10000' or spec['uid']!='12000' or spec['session_count']!=795
                or spec['chunk_wall_seconds']!=540 or spec['total_wall_seconds']!=7200 or spec['min_free_bytes']!=250000000):
            raise ValueError('fixed registered default-wallet specification required')
        source=current_source(spec);row['source']=source
        if source['source_sha256']!=spec['source_sha256_by_arm'][arm] or source['producer_sha256']!=spec['producer_sha256']:
            raise ValueError('registered exact latest-main execution/tooling changed')
        starts=read(spec['schedule'])['primary']['starts_ms'];terminal=spec['terminal_ms']
        if (sha(spec['schedule'])!='c21b4fcfe3cb12fb062bb01d3c3591aa0ee8c65db9e9afde3c26b1bcdc2ac28e'
                or len(starts)!=795 or starts!=sorted(set(starts)) or starts[0]!=1577836800000
                or terminal!=1789862400000 or any(not starts[0]<=s<terminal for s in starts)):
            raise ValueError('exact original795 schedule/window required')
        risk=spec['risk_by_arm'][arm]
        if set(risk)!={'capital_limit_usdt','max_stop_loss_fraction','stop_slippage_fraction'}:
            raise ValueError('exact registered risk configuration required')
        config=Config('12000',str(args.scratch/'state'),300,5,**risk)
        if config!=Config('12000',str(args.scratch/'state'),300,5):
            raise ValueError('measurement requires the selected runtime default risk configuration')
        if args.limit is not None: starts=starts[:args.limit]
        row['scope']=dict(kind='smoke' if args.limit else 'original-full',planned_sessions=len(starts))
        journal_path=args.scratch/'reports.jsonl'
        if args.mode=='start':
            if args.previous or args.scratch.exists():raise ValueError('cold start must use new independent original account')
            args.scratch.mkdir(parents=True);(args.scratch/'checkpoints').mkdir();journal_path.touch(exist_ok=False)
        else:
            if not args.previous or not (args.scratch/'state/intents.sqlite').is_file():raise ValueError('same original SQLite required')
            previous=read(args.previous);prior_elapsed=previous['cumulative_wall_seconds'];segment=previous['segment']+1
            if prior_elapsed>=7200 or segment>spec['max_segments']:raise ValueError('registered execution budget exhausted')
            row['previous_receipt']=dict(path=str(args.previous.resolve()),sha256=sha(args.previous))
        if shutil.disk_usage(args.scratch).free<spec['min_free_bytes']:raise ValueError('storage below250MB')
        phase='setup'
        market,tape=setup(spec,args.scratch)
        fx=PriorFX(Path(spec['fx']));initial=D(10000)/fx(starts[0])*D('.999')
        if args.mode=='start':
            trace_before=dict(count=0,rolling_sha256='0'*64)
            trace_path,trace,trace_buffer=open_path_trace(args.scratch,segment)
        venue=ResearchExchange(market,starts[0],initial,fx=fx,initial_cny=D(10000),matcher='trade_print',prints=tape,uid=12000,terminal_ms=terminal)
        venue.read_latency_ms,venue.latency_ms,venue.mark_gap=200,1000,'bound';venue.offline=True
        venue.loss_fraction,venue.slip_fraction=config.loss_fraction,config.slip_fraction
        binding,inputs,strategy=dependencies(spec,args.spec,market,tape,fx,starts,source)
        row.update(binding=binding,inputs=inputs,strategy=strategy,initial_cny='10000',initial_usdt=str(initial),terminal_ms=terminal)
        if args.mode=='resume':
            phase='restore';reports,last=restore(previous,spec,binding,config,starts,journal_path,venue);safe=True
            trace_before={key:venue._path_audit[key] for key in ('count','rolling_sha256')}
            trace_path,trace,trace_buffer=open_path_trace(args.scratch,segment)
        deadline=started+min(spec['chunk_wall_seconds'],7200-prior_elapsed)
        for start in starts[len(reports):]:
            if requested[0]:row['stop_reason']='requested-safe-boundary-stop';break
            if time.monotonic()>=deadline:row['stop_reason']='registered-chunk-wall-budget';break
            if shutil.disk_usage(args.scratch).free<spec['min_free_bytes']:row['stop_reason']='storage-below250MB';break
            phase='session';safe=False
            venue.advance_unattended(start)
            calls={}; prefix=str(ROOT/'coinquant')+'/'
            def profile(frame,event,arg):
                if event=='call' and frame.f_code.co_filename.startswith(prefix):
                    key='coinquant/'+frame.f_code.co_filename[len(prefix):]+':'+frame.f_code.co_name
                    calls[key]=calls.get(key,0)+1
            sys.setprofile(profile)
            report=dict(start_ms=start,**plain(session.run(config,venue,execute=True,monotonic=venue.monotonic,wait=venue.wait)))
            sys.setprofile(None)
            proof_path=args.scratch/'production-calls.jsonl'
            with proof_path.open('a') as proof: proof.write(json.dumps(dict(start_ms=start,calls=calls))+'\n')
            reports.append(report);newly+=1
            with journal_path.open('a') as stream:stream.write(json.dumps(report,separators=(',',':'),allow_nan=False)+'\n')
            invalid=[e for e in report.get('errors',[]) if e.get('error_type') in ('TypeError','KeyError','ValueError','ArithmeticError') or e.get('reason')=='Invalid observation or state']
            if invalid or report.get('pending_intents') or report.get('execution_unresolved'):
                raise ValueError('session integration/unsettled execution: '+json.dumps(invalid))
            release_private_bins(tape,args.scratch,report)
            if len(reports)%spec['checkpoint_every']==0:
                phase='checkpoint';last=checkpoint(venue,config,binding,reports,journal_path,args.scratch);safe=True
                print(json.dumps(dict(segment=segment,cursor=len(reports),newly_run=newly,wall_seconds=time.monotonic()-started)),flush=True)
        if len(reports)==len(starts) and not row['stop_reason']:
            phase='terminal';safe=False
            if not args.limit: venue.advance_unattended(terminal)
            phase='financial-export';money=financial(venue,initial)
            with State(config.state_dir,config.scope) as state:
                durable=dict(pending=state.pending(),ownership=state.get('entry_fill'),model=state.get('linear_campaign'),lifecycle_identity=state.get('lifecycle_identity'))
            row.update(financial=plain(money),sqlite=plain(durable))
            row['complete']=bool(not durable['pending'] and money['audit']['passed'] and venue.known_path)
            row['original_window_complete']=row['complete'] and args.limit is None
            if not row['complete']:raise ValueError('complete financial audit/path/pending failed')
            release_private_bins(tape,args.scratch,reports[-1])
        elif reports and not safe:
            phase='checkpoint';last=checkpoint(venue,config,binding,reports,journal_path,args.scratch);safe=True
        phase='final-source-freeze'
        if current_source(spec)!=source or sidecars(spec)!=inputs['official_sidecars']:raise ValueError('source or official inputs changed during segment')
        row['can_resume']=bool(row['stop_reason'] and safe and last and segment<spec['max_segments'] and prior_elapsed+time.monotonic()-started<7200)
    except Exception as exc:
        row['failure']=dict(phase=phase,error_type=type(exc).__name__,reason=str(exc))
        row['complete']=row['can_resume']=False
    sys.setprofile(None)
    complete_perp.PATH_TRACE=None
    if trace is not None:
        try:
            finish_path_trace(trace_path,trace,trace_buffer)
            row['path_trace']=path_trace_receipt(trace_path,trace_before,venue)
            if not row['path_trace']['verified']:
                raise ValueError(row['path_trace']['error'])
        except Exception as exc:
            row.setdefault('path_trace',dict(path=str(trace_path),verified=False,error=str(exc)))
            row['failure']=row['failure'] or dict(phase='path-trace-finalize',error_type=type(exc).__name__,reason=str(exc))
            row['complete']=row['can_resume']=False
        row['path_trace']['segment_failed']=row['failure'] is not None
    row.update(segment=segment,session_count=len(reports),newly_run_session_count=newly,last_checkpoint=last,
        current_sqlite_matches_last_checkpoint=bool(last and safe),segment_wall_seconds=time.monotonic()-started,
        cumulative_wall_seconds=prior_elapsed+time.monotonic()-started,at_ms=venue.now_ms if venue else None)
    if 'journal_path' in locals() and journal_path.exists():row['reports']=dict(path=str(journal_path),sha256=sha(journal_path),count=len(reports))
    write(args.out,row)
    print(json.dumps({k:row[k] for k in ('segment','session_count','newly_run_session_count','complete','can_resume','stop_reason','failure')},allow_nan=False),flush=True)

if __name__=='__main__':main()
