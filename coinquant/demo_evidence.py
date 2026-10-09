"""Read-only native Demo closure check for an explicitly selected live trial."""
import json
from decimal import Decimal as D
from pathlib import Path

from .ownership import TERMINAL, fill_history, owned_observation
from .state import State
from .types import Blocked, Unknown, number

IDS=('entry_order_id','stop_algo_id','take_algo_id','reduction_order_id',
     'offline_trigger_order_id')


def _observations(state):
    """Read the durable report archive and live rows once, rejecting conflicts."""
    rows={}
    def add(sequence,recorded,report):
        if type(sequence) is not int or sequence<=0 or not isinstance(recorded,(int,float)) or not isinstance(report,dict):
            raise Unknown('invalid Demo observation record')
        value=(recorded,report)
        if sequence in rows and rows[sequence]!=value:
            raise Unknown('conflicting Demo observation archive row')
        rows[sequence]=value
    try:
        archive=state.directory/'observations-archive.jsonl'
        if archive.exists():
            with archive.open() as stream:
                for line in stream:
                    item=json.loads(line)
                    add(item['sequence'],item['recorded_at'],item['report'])
        for sequence,recorded,payload in state.db.execute(
                'SELECT sequence,recorded_at,payload FROM observations'):
            add(sequence,recorded,json.loads(payload))
    except (OSError,ValueError,KeyError,TypeError):
        raise Unknown('Demo observation archive is unreadable') from None
    return [rows[key] for key in sorted(rows)]


def verify(proof, digest, live_limit, reader):
    """Match local durable requests, native orders/fills and saved Demo sessions.

    An ID supplied in JSON is only a lookup key. It never attests a trade by
    itself. The Demo reader is credentialed read-only and cannot send orders.
    """
    try:
        if (not isinstance(proof,dict) or proof.get('source_digest')!=digest
                or not all(isinstance(proof.get(k),str) and proof[k] for k in IDS)
                or not isinstance(proof.get('demo_uid'),str) or not proof['demo_uid'].isdigit()
                or number(proof['demo_capital_limit_usdt'],positive=True)<live_limit):
            raise Blocked('Demo evidence identity, code or capital limit mismatch')
        directory=Path(proof['demo_state_dir']).expanduser()
    except (KeyError,TypeError,ValueError):
        raise Blocked('Demo evidence lacks a persistent state source') from None
    if not directory.is_absolute() or not (directory/'intents.sqlite').is_file():
        raise Blocked('Demo evidence state source is missing')
    uid=proof['demo_uid']
    if reader.environment!='demo' or reader.authorize_writes is not False or reader.account_identity()!=uid:
        raise Blocked('Demo evidence requires a read-only Demo adapter')
    with State(directory,f'binance:BTCUSDT:demo:{uid}') as state:
        def read(key,conditional=False):
            identity=proof[key]
            owned=owned_observation(state,reader,identity,conditional=conditional)
            if reader.query_intent(identity,conditional=conditional)!=owned:
                raise Unknown('durable Demo observation differs from fresh native order')
            return owned
        entry=read('entry_order_id')['parent']
        stop=read('stop_algo_id',True)
        take=read('take_algo_id',True)
        reduction=read('reduction_order_id')['parent']
        offline=read('offline_trigger_order_id',True)
        if (entry.get('status') not in TERMINAL or number(entry['executedQty'])<=0
                or entry.get('reduceOnly') is not False
                or stop['parent'].get('orderType')!='STOP_MARKET'
                or take['parent'].get('orderType')!='TAKE_PROFIT_MARKET'
                or any(x['parent'].get('closePosition') is not True for x in (stop,take,offline))
                or reduction.get('reduceOnly') is not True
                or reduction.get('status') not in TERMINAL
                or not 0<number(reduction['executedQty'])<number(reduction['origQty'])
                or offline['child'] is None or offline['child'].get('status') not in TERMINAL
                or number(offline['child']['executedQty'])<=0
                or offline['parent'].get('algoStatus') not in ('FINISHED','TRIGGERED')):
            raise Blocked('Demo native entry, protection, partial reduction or trigger is unproven')
        for identity in (proof['stop_algo_id'],proof['take_algo_id']):
            row=state.db.execute('SELECT status,result FROM intents WHERE id=?',(identity,)).fetchone()
            if not row or row[0]!='confirmed' or json.loads(row[1]).get('status')!='NEW':
                raise Blocked('Demo protection lacks native active readback')
        observed=_observations(state)
        # A current-code report of a later recovery does not prove that code
        # placed an older order. Require the exact native identity to appear in
        # a current-code write attempt within that Demo session's recorded time.
        for key in IDS:
            path='/fapi/v1/algoOrder' if key in ('stop_algo_id','take_algo_id','offline_trigger_order_id') else '/fapi/v1/order'
            if not any(r.get('trial_mode')=='demo' and r.get('source_digest')==digest
                       and r.get('write_attempted') is True
                       and type(r.get('session_started_at_ms')) is int
                       and isinstance(action,dict) and action.get('method')=='POST'
                       and action.get('path')==path and action.get('id')==proof[key]
                       and type(action.get('at_ms')) is int
                       and r['session_started_at_ms']<=action['at_ms']<=int(recorded*1000)+5000
                       for recorded,r in observed
                       for action in (r.get('actions') or [])+(r.get('cleanup_actions') or [])):
                raise Blocked('Demo native order lacks a current-source session write: '+key)
        all_reports=[r for _,r in observed]
        reports=[r for r in all_reports if r.get('trial_mode')=='demo' and r.get('source_digest')==digest
                 and r.get('cleanup')=='verified' and r.get('pending_intents')==0
                 and isinstance(r.get('actual'),dict)]
        protected=[r for r in reports if r['actual'].get('native_full_position_protected') is True
                   and number(r['actual'].get('quantity_btc','0'))!=0
                   and number(r.get('sizing_capital_usdt','0'))==number(proof['demo_capital_limit_usdt'])]
        # A completed run must predate the native offline child fill, followed
        # by a separate completed run that reconciles the resulting exposure.
        first=min((r['session_started_at_ms']+int(r['elapsed_seconds']*1000)
                   for r in protected if 'elapsed_seconds' in r),default=None)
        if first is None:
            raise Blocked('Demo protected position report is missing')
        child=offline['child']
        now=int(reader.clock()*1000)
        page=fill_history(reader,first,now)
        fills=[t for t in page if str(t.get('orderId'))==str(child['orderId'])]
        if (any(t.get('symbol')!='BTCUSDT' or t.get('positionSide')!='BOTH'
                or t.get('side')!=child['side'] or number(t.get('price'),positive=True)<=0
                for t in fills)
                or sum((number(t['qty'],positive=True) for t in fills),D(0))!=number(child['executedQty'])
                or not fills or min(t['time'] for t in fills)<=first):
            raise Blocked('Demo trigger did not fill after the completed session')
        triggered=max(t['time'] for t in fills)
        prior=max((r['session_started_at_ms']+int(r['elapsed_seconds']*1000)
                   for r in protected if r.get('elapsed_seconds') is not None
                   and r['session_started_at_ms']+int(r['elapsed_seconds']*1000)<triggered),default=None)
        if prior is None or any(prior<r.get('session_started_at_ms',0)<=triggered
                                for r in all_reports if r.get('trial_mode')=='demo'):
            raise Blocked('Demo trigger was not observed between completed sessions')
        if not any(r.get('session_started_at_ms',0)>triggered and
                   (number(r['actual'].get('quantity_btc','0'))==0 or
                    r['actual'].get('native_full_position_protected') is True)
                   for r in reports):
            raise Blocked('Demo restart after offline trigger is unverified')
    return True
