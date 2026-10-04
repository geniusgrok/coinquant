"""Finite manual BTC research receipts, qualification and new-period inputs.

No account credentials, trading adapter, scheduler, or old paper-ledger writes.
Receipt time is first availability for future research, never past publication.
"""
import argparse
from datetime import datetime, timezone
from decimal import Decimal as D
import hashlib
import json
import math
from pathlib import Path
import subprocess
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError

DAY=86400000
MAX_BYTES=2097152


def digest(raw):return hashlib.sha256(raw).hexdigest()


def finite_request(name,url,out):
    started=int(time.time()*1000)
    record=dict(name=name,url=url,request_ms=started,symbol='BTCUSDT',status=None)
    try:
        with urlopen(Request(url,headers={'User-Agent':'btc-personal-research/1.0'}),timeout=5) as response:
            raw=response.read(MAX_BYTES+1); record['status']=response.status
        if len(raw)>MAX_BYTES:raise ValueError('response exceeds registered bound')
        name_file=name+'.json'
        with (out/name_file).open('xb') as stream:stream.write(raw)
        record.update(raw_file=name_file,sha256=digest(raw),bytes=len(raw))
    except HTTPError as error:
        raw=error.read(MAX_BYTES+1)
        record.update(status=error.code,error='HTTPError: '+str(error))
        if len(raw)<=MAX_BYTES:
            name_file=name+'-error.bin'
            with (out/name_file).open('xb') as stream:stream.write(raw)
            record.update(raw_file=name_file,sha256=digest(raw),bytes=len(raw))
    except Exception as error:
        record.update(status=getattr(error,'code',record['status']),error=type(error).__name__+': '+str(error))
    record['receipt_ms']=int(time.time()*1000)
    record['qualification']='FORWARD_RECEIPT_ONLY' if record.get('status')==200 and record.get('raw_file') else 'SOURCE_UNAVAILABLE'
    return record


def option_candidates(packet,now):
    """Black delta selects only candidate tickers; qualification uses real greeks."""
    choices={}
    for row in packet.get('result',[]):
        try:
            symbol,expiry,strike,side=row['instrument_name'].split('-')
            if symbol!='BTC' or side not in ('C','P'):continue
            expiry_ms=int(datetime.strptime(expiry,'%d%b%y').replace(hour=8,tzinfo=timezone.utc).timestamp()*1000)
            days=(expiry_ms-now)/DAY
            forward=float(row['underlying_price']);iv=float(row['mark_iv'])/100;strike=float(strike)
            if not (7<=days<=120 and forward>0 and strike>0 and iv>0):continue
            term=30 if days<60 else 90
            delta=.5*(1+math.erf((math.log(forward/strike)+.5*iv*iv*days/365)/(iv*math.sqrt(days/365)*math.sqrt(2))))
            delta=delta if side=='C' else delta-1
            score=(abs(days-term),abs(abs(delta)-.25),row['instrument_name'])
            key=term,side
            if key not in choices or score<choices[key][0]:choices[key]=score,row['instrument_name']
        except (KeyError,ValueError,TypeError,OverflowError):continue
    return [(term,side,v[1]) for (term,side),v in sorted(choices.items())]


def parse_receipt(receipt,folder):
    if not receipt.get('raw_file'):return dict(status='SOURCE_UNAVAILABLE',name=receipt['name'])
    filename=receipt['raw_file']
    if Path(filename).name!=filename or (folder/filename).stat().st_size>MAX_BYTES:
        raise ValueError('receipt file outside finite raw bound')
    raw=(folder/filename).read_bytes()
    if digest(raw)!=receipt['sha256']:raise ValueError('public receipt bytes changed')
    if receipt.get('status')!=200:return dict(status='SOURCE_UNAVAILABLE',name=receipt['name'])
    if not 0<=receipt['receipt_ms']-receipt['request_ms']<=30000:
        return dict(status='INVALID_RECEIPT_CLOCK',name=receipt['name'])
    packet=json.loads(raw);name=receipt['name']; result=dict(name=name,available_ms=receipt['receipt_ms'])
    if name=='btc-oi':
        value=D(packet['openInterest']);stamp=packet['time']
        if packet['symbol']!='BTCUSDT' or not value.is_finite() or value<0 or not 0<=receipt['receipt_ms']-stamp<=30000:
            raise ValueError('invalid BTC OI observation')
        result.update(status='FORWARD_RESEARCH_OBSERVATION',oi_btc=str(value),observation_ms=stamp)
    elif name=='option-summary':
        if not isinstance(packet.get('result'),list):raise ValueError('invalid option selection summary')
        result.update(status='SELECTION_INPUT_ONLY',contracts=len(packet['result']))
    elif name.startswith('option-'):
        row=packet['result'];delta=D(str(row['greeks']['delta']));iv=D(str(row['mark_iv']))/100
        pieces=name.split('-');term=int(pieces[1]);side=pieces[2]
        expiry=row['instrument_name'].split('-')[1]
        expiry_ms=int(datetime.strptime(expiry,'%d%b%y').replace(hour=8,tzinfo=timezone.utc).timestamp()*1000)
        days=(expiry_ms-receipt['receipt_ms'])/DAY
        if (not row['instrument_name'].startswith('BTC-') or row['instrument_name'].split('-')[-1]!=side
                or not iv.is_finite() or iv<=0 or not delta.is_finite() or not D('.15')<=abs(delta)<=D('.35')
                or not (7<=days<60 if term==30 else 60<=days<=120)
                or not 0<=receipt['receipt_ms']-row['timestamp']<=30000
                or (delta>0)!=(side=='C')):
            raise ValueError('option delta, maturity or clock outside registered qualification')
        result.update(status='FORWARD_RESEARCH_OBSERVATION',term=term,side=side,iv=str(iv),
                      delta=str(delta),days=days,instrument=row['instrument_name'],
                      observation_ms=row['timestamp'],meaning='Actual nearby-maturity mark IV/greeks; not executable IV or exact interpolated30/90day.')
    elif name.endswith('-book'):
        bid,ask=packet['bids'][0],packet['asks'][0]
        price_bid,price_ask=D(bid[0]),D(ask[0])
        if (not 0<price_bid<price_ask or D(bid[1])<=0 or D(ask[1])<=0):raise ValueError('invalid book')
        result.update(status='FORWARD_RESEARCH_OBSERVATION',bid=bid,ask=ask,
                      spread_fraction=str((price_ask-price_bid)/((price_bid+price_ask)/2)),
                      meaning='One received public snapshot; no queue priority or maker/IOC fill proof.')
    else:result.update(status='SELECTION_INPUT_ONLY')
    return result


def qualify(folder):
    packet=json.loads((folder/'receipts.json').read_text())
    parsed=[]
    for receipt in packet['receipts']:
        try:parsed.append(parse_receipt(receipt,folder))
        except (KeyError,TypeError,ValueError,ArithmeticError) as error:
            parsed.append(dict(name=receipt['name'],status='DATA_NOT_QUALIFIED',reason=str(error)))
    options={ (r['term'],r['side']):r for r in parsed if r['name'].startswith('option-') and r['status']=='FORWARD_RESEARCH_OBSERVATION'}
    feature={}
    if all((term,side) in options for term in (30,90) for side in ('C','P')):
        # Compare exactly the selected nearby maturities; never relabel as exact tenors.
        if all(options[t,'C']['instrument'].split('-')[1]==options[t,'P']['instrument'].split('-')[1] for t in (30,90)):
            feature=dict(rr_near30=str(D(options[30,'C']['iv'])-D(options[30,'P']['iv'])),
                term_ratio=str((D(options[30,'C']['iv'])+D(options[30,'P']['iv']))/(D(options[90,'C']['iv'])+D(options[90,'P']['iv']))),
                available_ms=max(r['available_ms'] for r in options.values()),exact_tenor=False)
    oi=next((r for r in parsed if r['name']=='btc-oi' and r['status']=='FORWARD_RESEARCH_OBSERVATION'),None)
    return dict(format='btc-persistent-data-qualification-v1',source=packet['source'],parsed=parsed,
                option_features=feature,oi=oi,historical_qualification=False,
                prospective_alpha_proven=False,account_days=0,private_requests=0)


def features(history,at,context=None):
    """First valid receipt of each UTC day; values never move backward in time."""
    daily={}
    for packet in history:
        option=packet['option_features'];oi=packet['oi']
        times=[x['available_ms'] for x in (option,oi) if x]
        if not times:continue
        stamp=max(times)
        if stamp>at:continue
        day=stamp//DAY
        if day not in daily or stamp<daily[day][0]:daily[day]=stamp,packet
    if not daily:return dict(status='WAIT_NEW_INTERVAL',oi_deleveraging=None,option_skew=None)
    days=sorted(daily);last=daily[days[-1]];now_packet=last[1]
    if at-last[0]>DAY:return dict(status='STALE_RESEARCH_RECEIPTS',oi_deleveraging=None,option_skew=None)
    oi_signal=None;skew_signal=None
    prior=daily.get(days[-1]-1)
    if prior and prior[1]['oi'] and now_packet['oi'] and context is not None and D(prior[1]['oi']['oi_btc'])>0:
        # Price context must identify a complete UTC day available before this call.
        if (context['completed_day_ms']+DAY<=at and context['available_ms']<=at
                and context['completed_day_ms']//DAY==days[-1]-1 and context['source_sha256']):
            ratio=D(now_packet['oi']['oi_btc'])/D(prior[1]['oi']['oi_btc'])-1
            oi_signal=(ratio<=D('-.10') and D(context['day_return'])<=D('-.02')
                       and D(context['spot_taker_imbalance'])>0)
    week=daily.get(days[-1]-7)
    if week and week[1]['option_features'] and now_packet['option_features']:
        a,b=now_packet['option_features'],week[1]['option_features']
        skew_signal=D(b['rr_near30'])<D(a['rr_near30'])<0 and D(a['term_ratio'])<=1
    return dict(status='RESEARCH_FEATURES_READY' if oi_signal is not None or skew_signal is not None else 'WAIT_NEW_INTERVAL',
                oi_deleveraging=oi_signal,option_skew=skew_signal,independent_receipt_days=len(daily),
                oldest_ms=daily[days[0]][0],latest_ms=last[0],orders=0,account_days=0,
                purpose='Frozen hypotheses for future research only; no historical backfill or profitability qualification.')


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('capture');a.add_argument('--out',type=Path,required=True)
    b=sub.add_parser('evaluate');b.add_argument('--history',type=Path,nargs='+',required=True)
    b.add_argument('--at-ms',type=int,required=True);b.add_argument('--context',type=Path);b.add_argument('--out',type=Path,required=True)
    args=p.parse_args(argv)
    if args.command=='capture':
        args.out.mkdir(parents=True,exist_ok=False)
        receipts=[]
        for name,url in (
            ('btc-oi','https://fapi.binance.com/fapi/v1/openInterest?symbol=BTCUSDT'),
            ('spot-book','https://api.binance.com/api/v3/depth?symbol=BTCUSDT&limit=5'),
            ('perp-book','https://fapi.binance.com/fapi/v1/depth?symbol=BTCUSDT&limit=5'),
            ('option-summary','https://www.deribit.com/api/v2/public/get_book_summary_by_currency?currency=BTC&kind=option')):
            receipts.append(finite_request(name,url,args.out))
        summary=receipts[-1]
        if summary.get('raw_file'):
            packet=json.loads((args.out/summary['raw_file']).read_bytes())
            for term,side,instrument in option_candidates(packet,summary['receipt_ms']):
                url='https://www.deribit.com/api/v2/public/ticker?'+urlencode({'instrument_name':instrument})
                receipts.append(finite_request(f'option-{term}-{side}',url,args.out))
        packet=dict(source=dict(git_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
                                program_sha256=digest(Path(__file__).read_bytes())),
                    receipts=receipts,finite_requests=len(receipts),orders=0,retries=0)
        (args.out/'receipts.json').write_text(json.dumps(packet,indent=2)+'\n')
        result=qualify(args.out)
        (args.out/'qualification.json').write_text(json.dumps(result,indent=2)+'\n')
    else:
        if args.out.exists():raise ValueError('preserve old forward research result')
        result=features([qualify(folder) for folder in args.history],args.at_ms,
                        json.loads(args.context.read_text()) if args.context else None)
        args.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result.get('status','PUBLIC_RECEIPTS_RECORDED'),
                         observations=len(result.get('parsed',[])),account_days=0)))


if __name__=='__main__':main()
