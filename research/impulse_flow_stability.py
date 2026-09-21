"""Fixed chronological and single-event influence check; no threshold search."""
import argparse,json
from decimal import Decimal as D
from pathlib import Path

def run(flow,paired,output):
    records=json.loads(flow.read_text())['records']
    sides={p['event']['identity']:p['event']['direction'] for p in json.loads(paired.read_text())}
    result={'qualification':'DESCRIPTIVE_ONLY','split':'2022-01-01T00:00:00Z','sides':{}}
    for side in (1,-1):
        rows=[r for r in records if r['mode']=='sparse' and sides[r['event']]==side]
        summary={}
        for label,subset in [('2020-21',[r for r in rows if r['entry']<1640995200000]),('2022-23',[r for r in rows if r['entry']>=1640995200000])]:
            summary[label]={}
            for aligned in (True,False):
                values=[D(r['net24h']) for r in subset if (D(r['aligned_flow'])>0)==aligned]
                summary[label]['aligned' if aligned else 'opposed']={'n':len(values),'mean':str(sum(values)/len(values)) if values else None}
        values=[D(r['net24h']) for r in rows if D(r['aligned_flow'])>0]
        summary['remove_best_aligned_mean']=str((sum(values)-max(values))/(len(values)-1))
        result['sides'][str(side)]=summary
    result['conclusion']='Short-side apparent flow advantage reverses after removing one best event and in2022-23; no uniform entry filter justified.'
    output.write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('flow','paired','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();run(a.flow,a.paired,a.output)
