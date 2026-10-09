"""Read only qualified market/print inputs; each wallet owns its mutable arrays."""
from collections import OrderedDict
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
import array
import gzip
import hashlib
import json
import shutil
from research import session_market as sm


def setup(spec, scratch):
    parser_sha = hashlib.sha256(Path(sm.__file__).read_bytes()).hexdigest()
    if parser_sha != spec['parser_sha256']:
        raise ValueError('exact qualified parser source required')
    original = sm._checksum
    raw=Path(spec['qualified_metadata']).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=spec['qualified_metadata_sha256']:
        raise ValueError('registered prior-content/current-metadata binding changed')
    qualification=json.loads(raw)['qualification_maps']['files']
    summary=dict(reused_prior_content_qualified_files=0,on_demand_new_or_changed_hashes=0)
    verified = {}
    def checksum(path):
        path = Path(path).resolve()
        stat = path.stat()
        key = (str(path),stat.st_dev,stat.st_ino,stat.st_size,stat.st_mtime_ns)
        if key not in verified:
            known=qualification.get(str(path))
            expected=dict(device=stat.st_dev,inode=stat.st_ino,bytes=stat.st_size,mtime_ns=stat.st_mtime_ns,mode=stat.st_mode,uid=stat.st_uid)
            if known and known['metadata']==expected and Path(str(path)+'.CHECKSUM').read_text()==known['sidecar']['text']:
                verified[key]=known['original_content_sha256']
                summary['reused_prior_content_qualified_files']+=1
            else:
                verified[key]=original(path)
                summary['on_demand_new_or_changed_hashes']+=1
        return verified[key]
    sm._checksum = checksum
    market = sm.load_base(Path(spec['market']))
    market._load_month = lru_cache(maxsize=8)(market._load_month)
    market.qualification_summary=summary
    private = scratch/'private-parsed-prints-cache'
    private.mkdir(exist_ok=True)
    selected = scratch/'selected-prints'
    selected.mkdir(exist_ok=True)
    link = scratch/'selected-prints-cache'
    if not link.exists():
        link.symlink_to(private)
    elif link.resolve() != private:
        raise ValueError('private cache directory binding changed')
    roots = [Path(root) for root in spec['parsed_pack_roots']]
    roots.insert(0,Path(spec['shared_parsed_cache'])/parser_sha)
    class Prints(sm.TradePrints):
        def __init__(self):
            super().__init__(selected)
            self.days=OrderedDict()
        def _load(self,day):
            if day in self.days:
                self.days.move_to_end(day)
                self._day_ms=day
                self._rows=self.days[day]
                return self._rows
            name=f'BTCUSDT-aggTrades-{datetime.fromtimestamp(day/1000,timezone.utc):%Y-%m-%d}.zip'
            for suffix in ('','.CHECKSUM'):
                origin=Path(spec['prints'])/(name+suffix)
                target=selected/(name+suffix)
                if not origin.exists():
                    if suffix=='':
                        self._day_ms,self._rows=day,None
                        return None
                    raise ValueError('selected print checksum missing')
                if not target.exists():
                    target.symlink_to(origin)
                elif target.resolve()!=origin.resolve():
                    raise ValueError('selected print original path changed')
            digest=checksum(selected/name)
            binary=private/(name+'.'+digest+'.bin')
            if not binary.exists():
                for root in roots:
                    packed=root/(binary.name+'.gz')
                    if packed.is_file():
                        with gzip.open(packed,'rb') as src,binary.open('xb') as dst:
                            shutil.copyfileobj(src,dst)
                        break
            rows=super()._load(day)
            self.days[day]=rows
            while len(self.days)>1:
                self.days.popitem(last=False)
            return rows
    return market,Prints()


def release_private_bins(tape,scratch,report):
    if report.get('cleanup')!='verified':
        return
    rows=[tape._rows,*tape.days.values()]
    if any(row is not None and (type(row) is not tuple or len(row)!=4 or any(
            type(column) is not array.array or column.typecode!='q' for column in row)) for row in rows):
        raise ValueError('private binary release requires independent owning arrays')
    private=scratch/'private-parsed-prints-cache'
    if (scratch/'selected-prints-cache').resolve()!=private.resolve():
        raise ValueError('private cache ownership binding changed')
    for binary in private.glob('*.bin'):
        binary.unlink()
