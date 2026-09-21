"""Targeted future-perturbation check; mutated paths are NOT economic evidence."""
import contextlib
import csv
import gzip
import io
import json
from pathlib import Path
from unittest.mock import patch
from decimal import Decimal as D
import research.persistent_hold_replay as replay
from pancakequant.research import timestamp


def run(root,output):
    original=replay.inputs;cutoff=timestamp('2023-07-01T00:00:00Z');checks=[]
    def changed(*args):
        series,funding,warm,identity=original(*args)
        for table in series.values():
            for t,row in table.items():
                if t>=cutoff:
                    row=list(row)
                    for col in range(1,5):row[col]=str(D(row[col])*D('1.1'))
                    table[t]=row
        funding={t:r*(3 if t>=cutoff else 1) for t,r in funding.items()}
        return series,funding,warm,identity
    def rows(path,name):
        with gzip.open(path/name,'rt') as f:return list(csv.DictReader(f))
    for schedule in ('sparse','hourly'):
        for modified in (False,True):
            out=output/(schedule+('-synthetic-future' if modified else '-control'))
            with patch.object(replay,'inputs',changed if modified else original),contextlib.redirect_stdout(io.StringIO()):
                replay.run(root,Path('evidence/binance-boundary-20260921'),Path('evidence/binance-mark-repair-20260921'),out,root,False,schedule,Path('evidence/binance-boundary-20260921/current-instrument.json'),'one_campaign','edge')
        control=output/(schedule+'-control');changed_path=output/(schedule+'-synthetic-future')
        for filename in ('decisions.csv.gz','equity.csv.gz','orders.csv.gz'):
            left=[r for r in rows(control,filename) if int(r['time'])<cutoff]
            right=[r for r in rows(changed_path,filename) if int(r['time'])<cutoff]
            assert left==right,(schedule,filename)
            checks.append(dict(schedule=schedule,file=filename,identical_prefix_rows=len(left)))
    hourly={r['time']:r for r in rows(output/'hourly-control','decisions.csv.gz')}
    sparse=rows(output/'sparse-control','decisions.csv.gz')
    for r in sparse:
        for field in ('regime','edge_target_fraction','edge_samples'):
            assert r[field]==hourly[r['time']][field],(r['time'],field)
    report=dict(passed=True,cutoff=cutoff,checks=checks,matched_sparse_market_states=len(sparse),synthetic_paths_not_economic_evidence=True)
    (output/'checks.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.root,a.output)
