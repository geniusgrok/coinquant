import hashlib,json,pathlib,sys,time,subprocess
sys.path.insert(0,str(pathlib.Path.cwd()))
from coinquant.binance import Binance,market_quantity
from coinquant.linear_preview import advance
from coinquant.state import State
from coinquant.types import serial,Blocked,Unknown,number
root=pathlib.Path('evidence/bounded-session-20260926/public')
venue=Binance();started=time.time();requests=[]
original=venue.get

def get(path,parameters=None):
    before=time.time()
    result=original(path,parameters)
    requests.append(dict(path=path,parameters=parameters or {},received_at_ms=int(time.time()*1000),elapsed_seconds=round(time.time()-before,3),response_sha256=hashlib.sha256(json.dumps(result,sort_keys=True,separators=(',',':')).encode()).hexdigest()))
    return result
venue.get=get
result=dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(), source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(pathlib.Path('coinquant').glob('*.py'))},started_at_ms=int(started*1000),private_requests=0,writes=0,checks=[])
def save(name,value):
    data=(json.dumps(serial(value),sort_keys=True,indent=2)+'\n').encode()
    (root/name).write_bytes(data)
    return dict(file=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
try:
    venue.begin_cycle()
    rules=venue.get('/fapi/v1/exchangeInfo')
    rows=[r for r in rules['symbols'] if r.get('symbol')=='BTCUSDT']
    assert len(rows)==1
    instrument=rows[0]
    assert instrument['status']=='TRADING' and instrument['contractType']=='PERPETUAL' and instrument['marginAsset']=='USDT'
    result['rules']=save('rules.json',dict(instrument=instrument,rateLimits=rules['rateLimits']))
    result['checks'].append('current BTCUSDT perpetual instrument rules decoded')
    mark=venue.get('/fapi/v1/premiumIndex',{'symbol':'BTCUSDT'})
    assert mark['symbol']=='BTCUSDT' and abs(int(time.time()*1000)-mark['time'])<=15000
    number(mark['markPrice'],positive=True)
    result['mark']=save('mark.json',mark)
    book=venue.get('/fapi/v1/depth',{'symbol':'BTCUSDT','limit':100})
    assert abs(int(time.time()*1000)-book['E'])<=15000
    bids=[(number(p,positive=True),number(q,positive=True)) for p,q in book['bids']]
    asks=[(number(p,positive=True),number(q,positive=True)) for p,q in book['asks']]
    assert bids and asks and bids[0][0]<asks[0][0]
    assert all(a[0]>b[0] for a,b in zip(bids,bids[1:])) and all(a[0]<b[0] for a,b in zip(asks,asks[1:]))
    result['book']=save('book.json',book)
    result['checks'].append('live mark and 100-level order book freshness/order validated')
    result['rounded_quantity_btc']=str(market_quantity(number('.0109'),mark['markPrice'],instrument))
    # Public market-only checkpoint is isolated from every trading account.
    with State('/tmp/coinquant-public-market-state','public-market-validation') as state:
        saved=state.get('linear_campaign')
        result['initial_checkpoint_last']=saved['body']['last'] if saved else None
        for attempt in range(8):
            venue.begin_cycle(120)
            try:
                model,market,reconstructed=advance(state,venue)
                result['model']=dict(complete_through=model.last,origin=1575158400000,total_bars=(model.last-1575158400000)//14400000,reconstructed=reconstructed,consumed_campaign=model.consumed)
                result['checkpoint']=save('checkpoint.json',model.checkpoint())
                result['checks'].append('production advance rebuilt complete four-hour model from fixed origin')
                print('complete model',result['model'],flush=True)
                break
            except (Blocked,Unknown) as exc:
                result.setdefault('interruptions',[]).append(dict(attempt=attempt+1,reason=str(exc)))
                print('market catch-up interrupted',str(exc),flush=True)
                if isinstance(exc,Blocked):raise
                time.sleep(1)
        else:raise Unknown('public bootstrap did not complete in bounded attempts')
        venue.begin_cycle()
        again,market,reconstructed=advance(state,venue)
        assert not reconstructed and again.last>=model.last
        result['checks'].append('production model checkpoint resumed without cold-bootstrap consumption')
    result['status']='PASS_PUBLIC_ONLY'
except Exception as exc:
    result.update(status='INCOMPLETE',error=type(exc).__name__+': '+str(exc))
finally:
    result.update(elapsed_seconds=round(time.time()-started,3),requests=requests,finished_at_ms=int(time.time()*1000))
    save('RESULT.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('requests',)},indent=2),flush=True)
