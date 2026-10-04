"""Finite BTC information receipts and five frozen forward-only predicates."""
import argparse
import csv
from datetime import datetime, timezone
from decimal import Decimal as D
from html.parser import HTMLParser
import io
import json
from pathlib import Path
import subprocess
import time
from urllib.parse import urlencode

from research import nine_routes as r, persistent_data as prior


class Table(HTMLParser):
    def __init__(self):
        super().__init__(); self.rows=[]; self.row=[]; self.cell=None

    def handle_starttag(self, tag, attrs):
        if tag == 'tr': self.row=[]
        if tag in ('td', 'th'): self.cell=[]

    def handle_data(self, data):
        if self.cell is not None: self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self.cell is not None:
            self.row.append(''.join(self.cell).strip()); self.cell=None
        if tag == 'tr' and self.row: self.rows.append(self.row)


def date_ms(value):
    return int(datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp()*1000)


def points(name, raw, receipt_ms):
    """All downloaded old observations become available NOW, never historically."""
    rows=[]
    if name == 'etf-demand':
        table=Table(); table.feed(raw.decode())
        if 'US$m' not in raw.decode() and 'US$ million' not in raw.decode():
            raise ValueError('ETF table USD-million units not established')
        for row in table.rows:
            try:
                stamp=int(datetime.strptime(row[0], '%d %b %Y').replace(tzinfo=timezone.utc).timestamp()*1000)
            except (ValueError, IndexError): continue
            if len(row) != 14: raise ValueError('unexpected ETF fund/total columns')
            def amount(text):
                negative=text.startswith('(') and text.endswith(')')
                return r.number(text.strip('()').replace(',', ''))*(-1 if negative else 1)
            values=list(map(amount,row[1:]))
            if abs(sum(values[:-1])-values[-1]) > D(len(values))*D('.05'):
                raise ValueError('ETF total inconsistent with fund components')
            rows.append(dict(day_ms=stamp, net_usd=str(values[-1]*1000000)))
    elif name in ('sofr', 'iorb'):
        reader=csv.DictReader(io.StringIO(raw.decode()))
        if not reader.fieldnames or name.upper() not in reader.fieldnames:
            raise ValueError('named FRED observation series missing')
        for row in reader:
            value=row[name.upper()]
            if value in ('', '.'): continue
            stamp=date_ms(row[reader.fieldnames[0]])
            rows.append(dict(day_ms=stamp, rate_fraction=str(r.number(value)/100)))
    elif name == 'old-coin-supply':
        packet=json.loads(raw)
        for row in packet.get('data', []):
            # These fields require actual completed UTXO input-age accounting.
            # Active supply, transfer volume or retrospective address labels do not substitute.
            if row.get('asset') != 'btc' or row.get('meaning') != 'completed-utxo-input-ages':
                raise ValueError('old-coin input age and denominator are not qualified')
            old=r.number(row['old_spend_btc'],nonnegative=True)
            total=r.number(row['total_spend_btc'],nonnegative=True)
            if total <= 0 or old > total or type(row['block_height']) is not int:
                raise ValueError('invalid completed old-coin spend accounting')
            rows.append(dict(day_ms=date_ms(row['time'][:10]), old_fraction=str(old/total),
                             block_height=row['block_height']))
    else: raise ValueError('unsupported receipt source')
    if not rows: raise ValueError('no qualified completed observations')
    days=[row['day_ms'] for row in rows]
    if len(set(days)) != len(days): raise ValueError('duplicate source observation day')
    rows=[row for row in rows if row['day_ms']+r.DAY <= receipt_ms]
    for row in rows:
        row.update(available_ms=receipt_ms,source_sha256=r.sha(raw),
                   historical_vintage_proven=False,qualification='FORWARD_RECEIPT_ONLY')
    return sorted(rows,key=lambda row:row['day_ms'])


def read_source(folder, receipt, name):
    if receipt.get('status') != 200 or not receipt.get('raw_file'):
        return dict(status='SOURCE_UNAVAILABLE',points=[],http_status=receipt.get('status'))
    filename=receipt['raw_file']
    if Path(filename).name != filename: raise ValueError('raw path escapes receipt directory')
    path=folder/filename
    if path.stat().st_size > prior.MAX_BYTES: raise ValueError('finite source size exceeded')
    raw=path.read_bytes()
    if r.sha(raw) != receipt['sha256']: raise ValueError('receipt source bytes changed')
    stamp=receipt.get('receipt_ms')
    if stamp is None: stamp=int(datetime.fromisoformat(receipt['received_utc']).timestamp()*1000)
    try:
        parsed=points(name,raw,stamp)
        return dict(status='FORWARD_OBSERVATIONS',points=parsed,first_available_ms=stamp,
                    raw_sha256=r.sha(raw),historical_vintage_proven=False)
    except (KeyError,TypeError,ValueError,ArithmeticError) as error:
        return dict(status='DATA_NOT_QUALIFIED',points=[],reason=str(error),raw_sha256=r.sha(raw))


def known_rows(sources, name, at):
    rows={}
    for source in sources:
        for row in source.get(name,{}).get('points',[]):
            if row['available_ms'] > at: continue
            old=rows.get(row['day_ms'])
            # First actual receipt fixes each vintage for research; later revisions don't backfill it.
            if old is None or row['available_ms'] < old['available_ms']:
                rows[row['day_ms']]=row
    return [rows[day] for day in sorted(rows)]


def features(sources, persistent_history, at, context=None):
    result={name:dict(status='WAIT_QUALIFIED_DATA',weak=None,release=None) for name in r.FAMILIES}
    etf=known_rows(sources,'etf-demand',at)
    if len(etf)>=10:
        latest,previous=etf[-5:],etf[-10:-5]
        total=sum(r.number(row['net_usd']) for row in latest)
        old=sum(r.number(row['net_usd']) for row in previous)
        try:
            r.context_at(context,at)
            volumes=context['spot_quote_turnover_by_day']
            denominator=sum(r.number(volumes[str(row['day_ms'])],nonnegative=True) for row in latest)
            if denominator<=0 or context.get('usd_usdt_basis_assumption') != 'declared-parity-proxy':
                raise ValueError('matching BTC quote turnover and declared USD/USDT proxy required')
            if at-etf[-1]['day_ms']>5*r.DAY: raise ValueError('stale ETF trading observations')
            result['etf-demand']=dict(status='FEATURE_READY',weak=total<0,release=old<0<total,
                net_usd=str(total),net_over_turnover=str(total/denominator),
                available_ms=max(row['available_ms'] for row in latest+previous),
                historical_qualification=False,meaning='Received ETF table vintage; not historical publication proof.')
        except (KeyError,TypeError,ValueError,ArithmeticError) as error:
            result['etf-demand'].update(status='WAIT_FRESH_MATCHED_CONTEXT',reason=str(error))
    inherited=prior.features(persistent_history,at,context.get('persistent_context') if context else None)
    for family,key in (('oi-deleveraging','oi_deleveraging'),('option-insurance','option_skew')):
        flag=inherited.get(key)
        if flag is not None:
            result[family]=dict(status='FEATURE_READY',weak=not flag,release=bool(flag),
                                available_ms=inherited['latest_ms'])
        else:
            result[family].update(status=inherited['status'],independent_receipt_days=inherited.get('independent_receipt_days',0))
    # The alternate OI expression uses the same real contraction and market context.
    if result['oi-deleveraging']['status']=='FEATURE_READY':
        pc=context.get('persistent_context') if context else None
        by_day={}
        for packet in persistent_history:
            oi=packet.get('oi')
            if oi and oi['available_ms']<=at:
                day=oi['available_ms']//r.DAY
                if day not in by_day or oi['available_ms']<by_day[day]['available_ms']:by_day[day]=oi
        last=max(by_day,default=0);old=by_day.get(last-1)
        ratio=(r.number(by_day[last]['oi_btc'])/r.number(old['oi_btc'])-1) if old and r.number(old['oi_btc'])>0 else None
        result['oi-deleveraging']['weak']=bool(ratio is not None and ratio<=D('-.10') and pc and r.number(pc['spot_taker_imbalance'])<=0)
    if result['option-insurance']['status']=='FEATURE_READY':
        daily={}
        for packet in persistent_history:
            option=packet.get('option_features')
            if option and option['available_ms']<=at:
                day=option['available_ms']//r.DAY
                if day not in daily or option['available_ms']<daily[day]['available_ms']:daily[day]=option
        last=max(daily);old=daily.get(last-7)
        if old:
            result['option-insurance']['weak']=(r.number(daily[last]['rr_near30'])<r.number(old['rr_near30'])<0 or r.number(daily[last]['term_ratio'])>1)
    chain=known_rows(sources,'old-coin-supply',at)
    if len(chain)>=8 and at-chain[-1]['day_ms']<2*r.DAY:
        from statistics import median
        value=r.number(chain[-1]['old_fraction']);base=median(r.number(row['old_fraction']) for row in chain[-8:-1])
        result['old-coin-supply']=dict(status='FEATURE_READY',weak=value>2*base,release=value<=base,
                                     available_ms=max(row['available_ms'] for row in chain[-8:]),
                                     supply_is_not_sale=True)
    sofr={row['day_ms']:row for row in known_rows(sources,'sofr',at)}
    iorb={row['day_ms']:row for row in known_rows(sources,'iorb',at)}
    dates=sorted(set(sofr)&set(iorb))
    if len(dates)>=10 and at-dates[-1]<5*r.DAY:
        spreads=[r.number(sofr[day]['rate_fraction'])-r.number(iorb[day]['rate_fraction']) for day in dates[-10:]]
        old=sum(spreads[:5])/5;new=sum(spreads[5:])/5
        result['dollar-financing']=dict(status='FEATURE_READY',weak=new>0 and new>=old,release=old>0 and new<old,
            spread_previous5=str(old),spread_latest5=str(new),
            available_ms=max(max(sofr[day]['available_ms'],iorb[day]['available_ms']) for day in dates[-10:]),
            meaning='Secured financing spread proxy. Not directional BTC alpha or old-vintage proof.')
    return dict(format='btc-nine-feature-decision-v1',at_ms=at,families=result,
                account_days=0,orders=0,historical_backfill=False,prospective_alpha_proven=False)


def source_identity():
    return dict(git_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
                dirty=bool(subprocess.check_output(['git','status','--porcelain'],text=True).strip()),
                program_sha256=r.sha(Path(__file__).read_bytes()),spec_sha256=r.sha(r.SPEC.read_bytes()))


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    capture=sub.add_parser('capture');capture.add_argument('--family',choices=('old-coin-supply','dollar-financing','etf-demand','oi-deleveraging','option-insurance'),nargs='+',required=True)
    capture.add_argument('--out',type=Path,required=True)
    evaluate=sub.add_parser('evaluate');evaluate.add_argument('--history',type=Path,nargs='*',default=[])
    evaluate.add_argument('--reuse-etf',type=Path);evaluate.add_argument('--reuse-persistent',type=Path,nargs='*',default=[])
    evaluate.add_argument('--context',type=Path);evaluate.add_argument('--at-ms',type=int,required=True);evaluate.add_argument('--out',type=Path,required=True)
    args=parser.parse_args(argv)
    if args.out.exists(): raise ValueError('preserve original research evidence')
    if args.command=='capture':
        identity=source_identity()
        if identity['dirty']: raise ValueError('freeze source before public collection')
        args.out.mkdir(parents=True)
        requests=[]
        urls={'etf-demand':[('etf-demand','https://farside.co.uk/btc/')],
            'old-coin-supply':[('old-coin-supply','https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?assets=btc&metrics=RevivedSply1yr%2CTxTfrValNtv&frequency=1d&page_size=10')],
            'dollar-financing':[(name,'https://fred.stlouisfed.org/graph/fredgraph.csv?id='+name.upper()) for name in ('sofr','iorb')],
            'oi-deleveraging':[('btc-oi','https://fapi.binance.com/fapi/v1/openInterest?symbol=BTCUSDT')]}
        if len(set(args.family))!=len(args.family): raise ValueError('duplicate source family')
        bound=sum(5 if family=='option-insurance' else len(urls[family]) for family in args.family)
        if bound>9: raise ValueError('finite manual source request cap9')
        for family in args.family:
            if family=='option-insurance':
                receipt=prior.finite_request('option-summary','https://www.deribit.com/api/v2/public/get_book_summary_by_currency?currency=BTC&kind=option',args.out)
                requests.append(receipt)
                if receipt.get('status')==200:
                    packet=json.loads((args.out/receipt['raw_file']).read_bytes())
                    for term,side,instrument in prior.option_candidates(packet,receipt['receipt_ms']):
                        requests.append(prior.finite_request(f'option-{term}-{side}','https://www.deribit.com/api/v2/public/ticker?'+urlencode({'instrument_name':instrument}),args.out))
            else:
                for name,url in urls[family]: requests.append(prior.finite_request(name,url,args.out))
        packet=dict(format='btc-nine-public-v1',source=identity,receipts=requests,
                    finite_requests=len(requests),retries=0,private_requests=0,orders=0)
        (args.out/'receipts.json').write_text(json.dumps(packet,indent=2)+'\n')
        print(json.dumps(dict(status='PUBLIC_RECEIPTS_RECORDED',requests=len(requests),orders=0)))
    else:
        sources=[];persistent=[];bindings=[]
        for folder in args.history:
            raw=(folder/'receipts.json').read_bytes();packet=json.loads(raw);data={}
            for receipt in packet['receipts']:
                if receipt['name'] in ('etf-demand','old-coin-supply','sofr','iorb'):
                    data[receipt['name']]=read_source(folder,receipt,receipt['name'])
            sources.append(data);bindings.append(dict(path=str(folder/'receipts.json'),sha256=r.sha(raw)))
            if any(row['name']=='btc-oi' or row['name'].startswith('option-') for row in packet['receipts']):
                persistent.append(prior.qualify(folder))
        if args.reuse_etf:
            raw=(args.reuse_etf/'receipts.json').read_bytes()
            receipt=next(row for row in json.loads(raw) if row['name']=='btc-etf-flow')
            sources.append({'etf-demand':read_source(args.reuse_etf,receipt,'etf-demand')})
            bindings.append(dict(path=str(args.reuse_etf/'receipts.json'),sha256=r.sha(raw),reused=True))
        for folder in args.reuse_persistent:
            persistent.append(prior.qualify(folder));raw=(folder/'receipts.json').read_bytes()
            bindings.append(dict(path=str(folder/'receipts.json'),sha256=r.sha(raw),reused=True))
        result=features(sources,persistent,args.at_ms,json.loads(args.context.read_text()) if args.context else None)
        result.update(source=source_identity(),receipt_bindings=bindings,qualified_sources=sources,
                      failure_routes={name:r.failure_route(row['status']) for name,row in result['families'].items()},
                      additional_requests=0)
        args.out.write_text(json.dumps(r.serial(result),indent=2)+'\n')
        print(json.dumps({name:row['status'] for name,row in result['families'].items()}))


if __name__=='__main__': main()
