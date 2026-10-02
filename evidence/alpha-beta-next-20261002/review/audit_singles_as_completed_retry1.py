"""Read-only completed-original audit queue, external to product sources."""
import hashlib, json, os
from pathlib import Path
import subprocess, sys, time
ROOT = Path('/workspace/btc-alpha-beta-next/review')
OUT = Path('/workspace/scratch/alpha-beta-next')
CHECKER = ROOT/'independent_financial_audit.py'
SPEC = json.loads((ROOT.parent/'spotquant/research/alpha_beta_spec.json').read_text())

def sha(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()

def write(path,body):
    with path.open('x') as stream: json.dump(body,stream,indent=2);stream.write('\n')

def audit(raw,kind,label,existing=None):
    digest=sha(raw);checker=sha(CHECKER);target=existing or ROOT/('financial-audit-'+label+'.json')
    if existing is None and target.exists(): existing=target
    if existing:
        report=json.loads(target.read_text())
        if report['raw_sha256'] != digest: raise ValueError('Existing audit refers to different raw bytes')
    else:
        log=ROOT/('financial-audit-'+label+'.run.log')
        command=[sys.executable,str(CHECKER),'--bundle',str(raw),'--sha256',digest,'--kind',kind,'--out',str(target)]
        begin=time.monotonic()
        with log.open('x') as stream:
            result=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
        if result.returncode: raise RuntimeError('Independent checker failed; evidence/log retained: '+label)
        if sha(CHECKER)!=checker: raise ValueError('Checker source changed during audit')
        write(ROOT/('financial-audit-'+label+'.command.json'),{'command':command,'checker_sha256':checker,
              'elapsed_seconds':time.monotonic()-begin,'exit_code':result.returncode,'log_sha256':sha(log),'output_sha256':sha(target)})
        report=json.loads(target.read_text())
    print(json.dumps({'audited_bundle':label,'accounts':len(report['accounts']),
          'all_checks_passed':report['all_examined_checks_passed'],'all_reported_complete':report['all_reported_complete']}),flush=True)
    return target,report

def main():
    audits=[];spot_accounts={}
    for name in SPEC['spot_candidates']:
        raw=OUT/'spot-singletons'/(name+'.json.gz')
        while not raw.exists() or raw.with_suffix('').exists(): time.sleep(10)
        existing=ROOT/'financial-audit-spot-consensus-v2-final.json' if name=='consensus' else (
                 ROOT/'financial-audit-spot-trend-reentry.json' if name=='trend-reentry' else None)
        path,report=audit(raw,'spot','spot-'+name,existing)
        if set(spot_accounts)&set(report['accounts']): raise ValueError('Duplicate audit account')
        spot_accounts.update(report['accounts']);audits.append({'path':str(path),'sha256':sha(path),'raw_sha256':report['raw_sha256']})
    write(ROOT/'financial-audit-spot-unscaled-comparison.json',{'format':'independent-derived-audit-comparison-v1',
          'purpose':'Derived audit rows only, not a raw financial bundle or source relabeling.','source_audits':audits,'accounts':spot_accounts})
    receipt=OUT/'registered-unscaled.command.json'
    while not receipt.exists(): time.sleep(10)
    if json.loads(receipt.read_text())['exit_code']!=0: raise RuntimeError('Unscaled assessment failed; stop independent queue')
    path,report=audit(OUT/'perp-singletons-retry1.json.gz','perp','perp-singletons')
    audits.append({'path':str(path),'sha256':sha(path),'raw_sha256':report['raw_sha256']})
    write(ROOT/'financial-audit-unscaled-index.json',{'scope':'Registered48 actual unscaled cases only; risks/combos/sensitivities/adoption still require review.',
          'audits':audits,'account_count':len(spot_accounts)+len(report['accounts'])})
    print(json.dumps({'finished_unscaled_audits':True,'account_count':len(spot_accounts)+len(report['accounts'])}),flush=True)

if __name__=='__main__':main()
