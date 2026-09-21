"""Fixed-ledger evidence impact; never relabel as a resimulated account."""
import argparse,bisect,csv,gzip,hashlib,json
from datetime import datetime,timezone
from pathlib import Path
from research.persistent_hold_replay import inputs,HOUR
from pancakequant.research import spec,timestamp


def read_rows(p):return list(csv.DictReader(gzip.open(p,'rt')))
def day(t):return datetime.fromtimestamp(t/1000,timezone.utc).strftime('%Y-%m-%d')

def run(native,accounts,sources,output):
    s,f,w,identity=inputs(native,Path('evidence/binance-boundary-20260921'),Path('evidence/binance-mark-repair-20260921'),True)
    observed={};mismatches=[]
    for p in (sources/'funding-held-months').glob('20*.json'):
        for r in json.loads(p.read_text()):
            t=int(r['fundingTime'])
            if t in f and float(f[t])!=float(r['fundingRate']):mismatches.append(t)
            if r.get('markPrice'):observed[t]=float(r['markPrice'])
    if mismatches:raise ValueError('funding archive/API rates disagree')
    fx={r['observation_date']:float(r['DEXCHUS']) for r in csv.DictReader((sources/'fx.csv').open()) if r['DEXCHUS'] not in ('','.','nan')}
    dates=sorted(fx);last=dates[-1];frozen_fx=float(spec()['cny_per_usd']);result={}
    for c in ('L-full','L0-full'):
        for mode in ('sparse','four_hour'):
            root=accounts/c/mode;eq=read_rows(root/'equity.csv.gz');orders=read_rows(root/'orders.csv.gz');old=json.loads((root/'result.json').read_text())
            trades=[r for r in orders if r['event']!='funding_adverse_bound'];fund=[r for r in orders if r['event']=='funding_adverse_bound']
            observed_paid=exact_paid=uncertainty=0.;coverage=0
            for r in fund:
                t=int(r['time']);q=float(r['quantity_btc']);rate=float(r['funding_rate']);paid=q*float(r['price_or_mark'])*rate
                marks=s['markPriceKlines'][t//HOUR*HOUR]
                uncertainty+=abs(q*rate)*(float(marks[2])-float(marks[3]))
                if t in observed:
                    coverage+=1;observed_paid+=paid;exact_paid+=q*observed[t]*rate
            position_events=sorted((int(r['time']),i,float(r['quantity_after'])) for i,r in enumerate(trades));times=[x[0] for x in position_events]
            credits=0.;credit_events=0;ambiguous=[]
            for t,rate in f.items():
                ix=bisect.bisect_left(times,t)-1
                if ix<0:continue
                q=position_events[ix][2]
                if q*float(rate)>=0:continue
                # Same-hour fills/exits cannot identify exact funding eligibility from OHLC.
                if any(t//HOUR==x//HOUR for x in times):ambiguous.append(t);continue
                mark=observed.get(t,float(s['markPriceKlines'][t//HOUR*HOUR][3 if q*float(rate)<0 else 2]))
                credits-=q*float(rate)*mark;credit_events+=1
            max_notional=max(abs(float(r['quantity']))*float(r['mark']) for r in eq)
            entries=[r for r in trades if r['event']=='entry']
            turnover=sum(abs(float(r['quantity_btc']))*float(r['price_or_mark']) for r in trades)
            # Revalue unchanged USDT ledger. No FX in signal, sizing or funding.
            peak=10000.;mdd=0.;last_value=0.;last_t=0;values=[]
            for r in eq:
                t=int(r['time']);date=day(t)
                if date>last:continue
                ix=bisect.bisect_right(dates,date)-1
                if ix<0:continue
                value=float(r['equity_usdt'])*fx[dates[ix]];peak=max(peak,value);mdd=max(mdd,1-value/peak);last_value=value;last_t=t
                values.append([t,r['event'],r['equity_usdt'],dates[ix],fx[dates[ix]],value])
            years=(last_t-timestamp(spec()['start']))/(365.25*24*HOUR)
            result[c+'/'+mode]=dict(qualification='FIXED_LEDGER_SENSITIVITY_NOT_ACCOUNT_REPLAY',old_cagr=old['cagr'],old_final_cny=old['final_cny'],max_position_notional_usdt=max_notional,max_entry_btc=max(float(r['quantity_btc']) for r in entries),min_entry_notional_usdt=min(float(r['quantity_btc'])*float(r['price_or_mark']) for r in entries),turnover_usdt=turnover,one_basis_point_fee_change_fixed_quantity_usdt=turnover*.0001,zero_fee_fixed_quantity_saving_usdt=turnover*.00075,funding=dict(charged_events=len(fund),exact_mark_events=coverage,matched_proxy_charge_usdt=observed_paid,matched_exact_charge_usdt=exact_paid,matched_charge_reduction_usdt=observed_paid-exact_paid,all_charges_hour_high_low_width_usdt=uncertainty,nonboundary_omitted_credit_events=credit_events,nonboundary_omitted_credit_lower_estimate_usdt=credits,credit_boundary_ambiguous=ambiguous),fx=dict(last_observation=last,valuation_last_time=last_t,last_value_cny=last_value,cagr_to_observed_endpoint=(last_value/10000)**(1/years)-1,mdd_revalued_envelope=mdd,full_window_cagr=None,missing_tail='2026-09-12 through exclusive 2026-09-20',convention='retrospective same-date H10 valuation; previous observed rate on nonbusiness dates; not publication-time information; no tail fill; USDT=USD unresolved'))
            with gzip.open(output/(c+'-'+mode+'-revaluation.csv.gz'),'wt') as out:
                wr=csv.writer(out);wr.writerow(['time','event','equity_usdt','fx_observation_date','cny_per_usd','equity_cny']);wr.writerows(values)
    payload=dict(results=result,source_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources.rglob('*') if p.is_file()},funding_rate_mismatches=mismatches,limitations=['Fixed quantities and event sequence; fee/funding changes affect future sizing in a true resimulation','Historical fee eligibility, brackets, continuous USDT/USD and FX release vintages remain unresolved','No full-window adjusted account CAGR or alpha claim'])
    (output/'result.json').write_text(json.dumps(payload,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('native','accounts','sources','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);run(a.native,a.accounts,a.sources,a.output)
