"""Create deterministic, complete account archive and byte-verified Git parts."""
import gzip
from hashlib import sha1, sha256
import json
from pathlib import Path
import tarfile

HERE = Path(__file__).resolve().parent
CHUNK = 512 * 1024


def digest(raw):
    return dict(bytes=len(raw), sha256=sha256(raw).hexdigest(),
                git_blob_sha1=sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest())


def members(path):
    with tarfile.open(path,'r:gz') as source:
        result=[]
        for entry in source:
            if not entry.isfile():
                continue
            parts=Path(entry.name).parts
            if '..' in parts or entry.name.startswith('/'):
                raise ValueError('unsafe original member')
            data=source.extractfile(entry).read()
            result.append(dict(path=entry.name,**digest(data)))
        assert len(result)==len({x['path'] for x in result})
        return sorted(result,key=lambda item:item['path'])


def account_archive(path):
    files=sorted(p for p in (HERE/'accounts').rglob('*')
                 if p.is_file() and not p.name.endswith(('.partial','.failure.txt')))
    assert len(files)>200 and all(p.is_file() for p in files)
    with path.open('wb') as target:
        with gzip.GzipFile(filename='',mode='wb',fileobj=target,mtime=0,compresslevel=9) as gz:
            with tarfile.open(fileobj=gz,mode='w',format=tarfile.PAX_FORMAT) as tar:
                for file in files:
                    name=file.relative_to(HERE).as_posix()
                    info=tar.gettarinfo(str(file),arcname=name)
                    info.mtime=0;info.uid=info.gid=0;info.uname=info.gname=''
                    with file.open('rb') as source:
                        tar.addfile(info,source)
    return files


def main():
    account_path=HERE/'ACCOUNT_ORIGINALS.tar.gz'
    files=account_archive(account_path)
    archived=members(account_path)
    assert len(archived)==len(files)
    for name in ('SX60','DFII10'):
        for stage in ('development','full','full-stress','absence-787'):
            assert any(x['path']==f'accounts/{name}-{stage}/decisions.csv.gz' for x in archived)
            assert any(x['path']==f'accounts/{name}-{stage}.invocation.json' for x in archived)
    packed={}
    for key,filename in (('accounts','ACCOUNT_ORIGINALS.tar.gz'),
                         ('minutes_development','MINUTE_ORIGINALS.tar.gz'),
                         ('minutes_formal','FULL_MINUTE_ORIGINALS.tar.gz')):
        source=HERE/filename
        raw=source.read_bytes()
        parts=[]
        for offset in range(0,len(raw),CHUNK):
            piece=raw[offset:offset+CHUNK]
            relative=f'archive/{key}/part-{offset//CHUNK:04d}.bin'
            path=HERE/relative;path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(piece)
            parts.append(dict(path=relative,offset=offset,**digest(piece)))
        packed[key]=dict(original_name=filename,**digest(raw),parts=parts,members=members(source))
    alfred=sorted((dict(path='alfred/'+p.name,**digest(p.read_bytes()))
                   for p in (HERE/'alfred').iterdir() if p.is_file()),
                  key=lambda item:item['path'])
    meta=dict(format=1,part_size=CHUNK,
        source_main='de15e5b7a178fd0903e5d464da8e92840756ba7a',
        protocol_pre_result_commit='a1d5dd34267f14c2f2a32174e0a4a319b5928fd9',
        artifact_transport=dict(
            development_github_artifact_id=10825754772,
            development_outer_sha256='a5f24ca6539111474a1c5a606135bc1fb19ce69ac73f88f64e3323c251409a16',
            formal_github_artifact_id=10825699716,
            formal_outer_sha256='5fd7c07fc35c735829662ade637df4cb8c70eb80f390bc2debb5151f9ab1f931'),
        archives=packed,alfred=alfred)
    (HERE/'ORIGINALS.json').write_text(json.dumps(meta,indent=2)+'\n')
    print(json.dumps({key:dict(bytes=item['bytes'],sha256=item['sha256'],
        parts=len(item['parts']),members=len(item['members'])) for key,item in packed.items()}))


if __name__=='__main__':main()
