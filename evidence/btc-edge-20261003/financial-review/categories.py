"""Derive acceptance categories from independent account checkpoints and original inputs.
The evaluator is imported ONLY after derivation, for strict typed schema comparison.
"""
from recompute import *
CATEGORIES=['source_and_inputs','original_accounting','baseline_six_groups','calibration_and_actual_risk','adoption_gates','actual_budget_aggregation']
PH=load(OUT/'account-phase-complete.json');A={k:load(p) for k,p in PH['account_paths'].items()};MR=PH['market_returns'];CR=PH['cny_market_returns'];RESULT={k:[] for k in CATEGORIES}
def add(cat,id,raw,**v):RESULT[cat].append(record(cat,id,raw,v))
def category_inputs():
 for k,a in A.items():
  add('source_and_inputs','account:'+k,{k:a['raw_sha256']},project_kind=a['kind'],candidate=a['candidate'],scenario=a['scenario'],initial_cny=a['capital'],start_offset_ms=a['offset'],calibrated=a['risk'],components=a['components'],source=a['source'],original_file=a['path'])
  m=a['metrics'];c=a['curve'];money={'initial_cny':a['capital'],'final_cny':c[-1]['equity_cny'],'final_usdt':c[-1]['equity_usdt'],'fees_usdt':m['fees_usdt'],'funding_paid_usdt':m['funding_paid_usdt'],'fill_count':m['fill_count'],'continuous_proxy_mdd':a['gate_inputs']['values']['mdd'],'cny_cagr':m['registered_account_cagr'],'usdt_cagr':m['registered_account_usdt_cagr']}
  add('original_accounting',k,{k:a['raw_sha256']},money=money,gate_inputs=a['gate_inputs'],daily_days=len(c),daily_curve_sha256=checksum(c),ledger_reconstruction_sha256=checksum(a['monetary_audit']),daily_cny_metrics=m['metrics'],daily_usdt_metrics=m['usdt_metrics'])
 for path in sorted({a['path'] for a in A.values()}):
  a=next(a for a in A.values() if a['path']==path);kind=a['kind'];b=load(path);env={k:v for k,v in b.items() if k!='results'};meta=b if kind=='spot' else b['inputs'];edge=b if kind=='spot' else b['edge']
  for key,expected in [('fx_sha256',sha(arg('--fx'))),('schedule_sha256',sha(arg('--schedule')) if kind=='spot' else R['environment']['primary_sha256'])]:eq(meta[key],expected,'envelope '+key)
  for key in ['spec_sha256','protocol_sha256']:eq(edge[key],R['contracts'][kind][key],'edge contract')
  ids=[k for k,a in A.items() if a['path']==path]
  for k in ids:
   a=A[k];parts=b['edge']['components'] if kind=='spot' else b['edge']['candidates'][a['candidate']];eq(parts,a['components'],'actual components')
   eq(ident(kind,a['candidate'],a['scenario'],a['capital'],0 if kind=='spot' else b['edge']['start_offset_ms'],bool(edge['risk_calibration_sha256'])),k,'raw account identity')
  add('source_and_inputs','raw:'+path,{path:a['raw_sha256']},project_kind=kind,source=meta['source'],spec_sha256=edge['spec_sha256'],protocol_sha256=edge['protocol_sha256'],fx_sha256=meta['fx_sha256'],schedule_sha256=meta['schedule_sha256'],market_sha256=meta['market_sha256'] if kind=='spot' else checksum(meta['market_identity']),feature_sha256=(edge['feature_sha256'] if kind=='spot' else edge['feature_file_sha256']) or 'not_supplied',original_envelope_sha256=checksum(env),all_input_bytes_sha256=checksum(load(OUT/'provenance.json')['input_hashes']))
  del b

def baselines():
 annotations=['candidate','scenario','original_row_sha256','research_identity','risk_calibration','subpools'];reference_paths={h:p for p,h in R['inputs'].items()}
 for kind in BASE:
  for scenario in STRESS[kind]+['actual_unity']:
   actual=A[ident(kind,BASE[kind],scenario if scenario!='actual_unity' else 'base',risk=scenario=='actual_unity')]
   refhash=R['baseline_equality'][kind][scenario]['reference_raw_sha256'];p=reference_paths[refhash];b=load(p);row=b['results'][BASE[kind]+'-'+(scenario if scenario!='actual_unity' else 'base')] if kind=='spot' else b['results'][BASE[kind]][scenario if scenario!='actual_unity' else 'base']
   g=groups(row,kind);eq(g,actual['groups'],'baseline all six '+kind+scenario);eq({z:row[z] for z in annotations if z in row},actual['annotations'],'baseline original annotations');add('baseline_six_groups',kind+':'+scenario,{'reference':refhash,actual['id']:actual['raw_sha256']},reference_groups=g,actual_groups=actual['groups'])

def risk_and_gates():
 documents={};derived={};selected={};initial=float(D(10000)/fx(START)*D('.999'));profile_digests={k:sha(arg('--'+k+'-calibration')) for k in BASE}
 for kind in BASE:
  baseline=A[ident(kind,BASE[kind])];profiles={}
  for name in [BASE[kind]]+ORDER[kind]:
   a=A[ident(kind,name)];c=risk_stats(daily([x['equity_usdt'] for x in a['curve'][:731]],initial)[1],MR[:731]);b=risk_stats(daily([x['equity_usdt'] for x in baseline['curve'][:731]],initial)[1],MR[:731]);scales=[1.0]
   if c['volatility']>0:scales.append(b['volatility']/c['volatility'])
   if c['beta']>b['beta'] and c['beta']>0:scales.append(max(.01,b['beta'])/max(.01,c['beta']))
   scale='1' if name==BASE[kind] else str(min(scales));profile=dict(candidate=name,project_kind=kind,scale=scale,effective_from_ms=CUT,calibration_end_ms=CUT,training_end_day_exclusive='2022-01-01',baseline_candidate=BASE[kind],base_bundle_sha256=a['raw_sha256']);profiles[name]=profile
   require([p['day_ms'] for p in a['curve'][:731]]==list(range(START,CUT,DAY)),'training boundary 731')
   add('calibration_and_actual_risk','profile:'+kind+':'+name,{a['id']:a['raw_sha256']},profile=profile,document_sha256=[profile_digests[kind]],training_days=731,training_candidate=c,training_baseline=b,source=a['source'])
  doc=dict(format=1,project_kind=kind,baseline_candidate=BASE[kind],cutoff_ms=CUT,spec_sha256=R['contracts'][kind]['spec_sha256'],profiles=profiles);eq(doc,load(arg('--'+kind+'-calibration')),'independent project profile');documents[kind]=doc
  for name in [BASE[kind]]+ORDER[kind]:
   a=A[ident(kind,name,risk=True)];control=A[ident(kind,BASE[kind],risk=True)];v=a['metrics']['validation_2022_plus'];profile=profiles[name]
   add('calibration_and_actual_risk','actual:'+a['id'],{a['id']:a['raw_sha256'],'unscaled_base':profile['base_bundle_sha256'],'actual_unity':control['raw_sha256']},document_sha256=profile_digests[kind],profile=profile,validation=dict(beta=v['regression']['beta_btc'],volatility=v['usdt']['daily_volatility_annualized'],total_usdt_return=a['curve'][-1]['equity_usdt']/a['curve'][730]['equity_usdt']-1,continuous_proxy_mdd=a['gate_inputs']['values']['mdd']))
  derived[kind]={}
  for name in ORDER[kind]:
   av=A[ident(kind,name,risk=True)];bv=A[ident(kind,BASE[kind],risk=True)];c=risk_stats(daily([p['equity_usdt'] for p in av['curve']],initial)[1][731:],MR[731:]);b=risk_stats(daily([p['equity_usdt'] for p in bv['curve']],initial)[1][731:],MR[731:]);matched=D(str(c['volatility']))<=D(str(b['volatility']))*D('1.05') and D(str(c['beta']))<=D(str(b['beta']))+D('.02');gain=av['curve'][-1]['equity_usdt']/av['curve'][730]['equity_usdt']-bv['curve'][-1]['equity_usdt']/bv['curve'][730]['equity_usdt']
   # Classification retains original float band convention; exact Decimal upper bands govern eligibility.
   oldmatch=c['volatility']<=b['volatility']*1.05 and c['beta']<=b['beta']+.02
   achieved={'achieved_match':matched,'candidate':c,'baseline':b,'validation_total_usdt_return_gain':gain,'classification':('conditional_historical_matched_return_evidence' if gain>0 else 'no_positive_matched_return_evidence') if oldmatch else 'risk_match_failed_or_unidentifiable','prospective_alpha_proven':False}
   cg={s:A[ident(kind,name,s)]['gate_inputs']['values'] for s in STRESS[kind]};bg={s:A[ident(kind,BASE[kind],s)]['gate_inputs']['values'] for s in STRESS[kind]};checks={'baseline_equality':True}
   d=lambda x:D(str(x))
   for s in STRESS[kind]:checks[s+':cagr']=d(cg[s]['cagr'])>=d(bg[s]['cagr'])-D('.01');checks[s+':mdd']=d(cg[s]['mdd'])<=d(bg[s]['mdd']) if kind=='spot' else d(cg[s]['mdd'])<D('.50')
   c0=cg['base'];b0=bg['base'];checks['base_improvement']=d(c0['cagr'])>=d(b0['cagr'])+D('.01') or d(c0['mdd'])<=d(b0['mdd'])-D('.01') and d(c0['cagr'])>=d(b0['cagr'])-D('.01');checks['worst_cny_day']=d(c0['worst_day'])>=d(b0['worst_day'])-D('.005');checks['es99']=d(c0['es99'])<=d(b0['es99'])*D('1.05');checks['underwater']=c0['underwater']<=b0['underwater'];checks['actual_risk_bands']=matched;checks['actual_validation']=d(gain)>0 or d(av['gate_inputs']['values']['mdd'])<=d(bv['gate_inputs']['values']['mdd'])-D('.01') and d(gain)>=D('-.01')
   decision={'eligible':all(checks.values()),'checks':checks,'reasons':[k for k,v in checks.items() if not v],'worst_stress_cagr':str(min(d(x['cagr']) for x in cg.values())),'status':'complete','achieved_risk':achieved};derived[kind][name]=decision;keys=[ident(kind,n,s) for n in [BASE[kind],name] for s in STRESS[kind]]+[ident(kind,n,risk=True) for n in [BASE[kind],name]];add('adoption_gates',kind+':'+name,{k:A[k]['raw_sha256'] for k in keys},gate_inputs={k:A[k]['gate_inputs'] for k in keys},result=decision)
  ranked=sorted([n for n in ORDER[kind] if derived[kind][n]['eligible']],key=lambda n:(-D(derived[kind][n]['worst_stress_cagr']),ORDER[kind].index(n)));best=ranked[0] if ranked else BASE[kind];eligible=[n for n in ORDER[kind] if derived[kind][n]['eligible']];parts=eligible if len(eligible)>=2 else [];require(not parts,'new combination required');selected[kind]=best;add('adoption_gates',kind+':ranking',{n:A[ident(kind,n)]['raw_sha256'] for n in ORDER[kind]},registered_order=ORDER[kind],ranked_eligible_singles=ranked,best_single=best,all_eligible_components=parts,selected=best)
 eq(derived,R['decisions'],'all actual adoption decisions');eq(selected,R['selected'],'selection');eq(R['combinations'],{},'combination inapplicable')
 return selected

def portfolios(selected):
 full={}
 for label,selection in [('current_default',BASE),('selected',selected)]:
  full[label]=[]
  for budgets in [(2500,7500),(5000,5000),(7500,2500)]:
   keys=[ident(k,selection[k],capital=b) for k,b in zip(BASE,budgets)];aa,bb=[A[k] for k in keys];cur=[]
   for x,y in zip(aa['curve'],bb['curve']):
    require(x['day_ms']==y['day_ms'],'joint clock');usd=x['equity_usdt']+y['equity_usdt'];gross=abs(x['net_btc'])*x['price_usdt']+abs(y['net_btc'])*y['price_usdt'];signed=x['net_btc']*x['price_usdt']+y['net_btc']*y['price_usdt'];cur.append(dict(day_ms=x['day_ms'],equity_cny=x['equity_cny']+y['equity_cny'],equity_usdt=usd,absolute_btc_notional_usdt=gross,gross_exposure_over_equity=gross/usd,signed_exposure_over_equity=signed/usd))
   cm,rr=daily([p['equity_cny'] for p in cur],10000,True);um,ur=daily([p['equity_usdt'] for p in cur],float(D(10000)/fx(START)*D('.999')),usd=True);regression=dict(reg(ur,MR),identifiable=True);returns=[daily([p['equity_usdt'] for p in a['curve']],float(D(b)/fx(START)*D('.999')))[1] for a,b in zip([aa,bb],budgets)];corr=statistics.correlation(*returns);fees=[a['metrics']['fees_usdt'] for a in [aa,bb]];funding=[a['metrics']['funding_paid_usdt'] for a in [aa,bb]];fills=[a['metrics']['fill_count'] for a in [aa,bb]]
   # Compare the entire portfolio, including HAC/capture-independent daily evidence.
   original=next(p for p in R['portfolios'][label] if p['budgets']==list(budgets))
   for k,v in dict(curve=cur,daily_cny=cm,daily_usdt=um,regression=regression,account_return_correlation=corr,fees_usdt=fees,funding_usdt=funding,fill_counts=fills,neutral_reference=budgets==(5000,5000)).items():eq(v,original[k],'joint '+label+str(budgets)+' '+k)
   add('actual_budget_aggregation',label+':'+ '/'.join(map(str,budgets)),{k:A[k]['raw_sha256'] for k in keys},budgets=list(budgets),initial_cny=10000,cash_flows=0,daily_days=len(cur),daily_equity_exposure_sha256=checksum(cur),daily_cny_metrics=cm,daily_usdt_metrics=um,beta=ds(regression['beta_btc']),correlation={'identifiable':True,'value':ds(corr)},closing_gross_exposure=ds(cur[-1]['gross_exposure_over_equity']),fees_usdt=[ds(v) for v in fees],funding_usdt=[ds(v) for v in funding],fill_counts=fills)
   full[label].append({'budgets':list(budgets),'daily_cny':cm,'daily_usdt':um,'regression':regression,'correlation':corr,'curve_sha256':checksum(cur),'neutral_reference':budgets==(5000,5000)})
 put(OUT/'independent-portfolio-statistics.json',full)

def main():
 category_inputs();baselines();selected=risk_and_gates();portfolios(selected)
 # All economic values have been reconstructed above. This import supplies only comparison/schema.
 sys.path.insert(0,str(ROOT/'spotquant'));from research.edge_assessment import review_expectations,verify_review_value,inventory_binding
 inventory=checksum(inventory_binding(R));require(inventory==R['inventory_sha256']=='c3f4e9d3bee09bac4242660aafaed51e767d849dae5549343af7176c62226e74','full inventory binding');expected=review_expectations(R);artifacts={}
 for cat,records in RESULT.items():
  require({r['id'] for r in records}==set(expected[cat]),'category complete coverage '+cat)
  for r in records:verify_review_value(r,expected[cat][r['id']])
  p=OUT/(cat+'.json');put(p,{'inventory_sha256':inventory,'category':cat,'recomputations':records});artifacts[cat]={'passed':True,'artifact':{'path':str(p),'sha256':sha(p)}};print('CATEGORY PASS',cat,len(records),sha(p),flush=True)
 # Financial attestation file is produced after separate canonical/provenance supplements close.
 put(OUT/'category-phase-complete.json',{'checks':artifacts,'inventory_sha256':inventory,'preliminary':{'path':str(PRE),'sha256':sha(PRE)},'reviewer_source':load(OUT/'provenance.json')['sources']['spot']['source'],'script_sha256':sha(__file__)})
if __name__=='__main__':
 try:main()
 except Exception:traceback.print_exc();sys.exit(1)
