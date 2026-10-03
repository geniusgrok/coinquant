"""Retain an actual source-bound export/init invocation; no retries or extra checks."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import time

def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()

def new(path, body):
    with path.open('x') as stream:
        json.dump(body, stream, indent=2, allow_nan=False); stream.write('\n')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--operation', required=True, type=Path)
    args=parser.parse_args()
    operation=json.loads(args.operation.read_bytes())
    root=args.operation.parent
    label=operation['label']
    start=root/(label+'.command-start.json')
    finish=root/(label+'.command-finish.json')
    log=root/(label+'.run.log')
    new(start,{'state':'launch_requested','requested_utc':datetime.now(timezone.utc).isoformat(),
               'operation':operation,'operation_sha256':digest(args.operation),'driver_sha256':digest(__file__)})
    began=time.monotonic()
    with log.open('xb') as stream:
        process=subprocess.Popen(operation['command'],cwd=operation['cwd'],stdout=stream,stderr=subprocess.STDOUT)
        code=process.wait()
    output=Path(operation['output'])
    result={'state':'exited','pid':process.pid,'exit_code':code,'reaped':True,
            'finished_utc':datetime.now(timezone.utc).isoformat(),'elapsed_seconds':time.monotonic()-began,
            'command_start_sha256':digest(start),'log_sha256':digest(log),
            'output_sha256':digest(output) if output.is_file() else None,
            'output_bytes':output.stat().st_size if output.is_file() else None}
    new(finish,result)
    print(json.dumps({'label':label,**result}))
    return code

if __name__=='__main__':
    raise SystemExit(main())
