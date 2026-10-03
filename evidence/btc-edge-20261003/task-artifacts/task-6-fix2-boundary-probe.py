"""SYNTHETIC old/new interface and publication-age boundary, no network."""
from pathlib import Path
import inspect
import sys
sys.path.insert(0, str(Path.cwd()))
from research import edge_forward as f
out=Path(sys.argv[1]);out.mkdir(exist_ok=False)
stamp=int(f.datetime(2026,10,3,4,40,tzinfo=f.timezone.utc).timestamp()*1000)
csv=b'observation_date,DEXCHUS\n2026-09-25,6.7110\n'
html=b'<script type="application/ld+json">{"@context":"http://schema.org","@type":"Dataset","alternateName":"DEXCHUS","dateModified":"2026-09-28T15:16:00-05:00"}</script><table id="recent-obs"><tr><td>2026-09-25:&nbsp;</td><td class="series-obs value">6.7110</td></tr></table>'
def raw(name,body,url,category):
 p=out/name;p.write_bytes(body)
 return dict(path=str(p),sha256=f.sha(body),url=url,category=category,request_ms=stamp-20,receipt_ms=stamp-10)
pair=raw('csv.raw',csv,f.FX_URL,'fx');pair['metadata']=raw('metadata.raw',html,'https://fred.stlouisfed.org/graph/?id=DEXCHUS','fx_metadata')
result=dict(synthetic=True,default_fx_url=f.FX_URL,deferred_init_interface='defer_market_warmup' in inspect.signature(f.initialize).parameters)
try: result['fx_result']=f.fx_from(pair,stamp)
except Exception as e: result['fx_rejection']=str(e)
print(f.dump(result).decode())
