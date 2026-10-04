"""Record one exclusive authorized operation; no retry or extra verification."""
import datetime
import json
import subprocess
import sys
from pathlib import Path

repo, name, *argv = sys.argv[1:]
root = Path(__file__).resolve().parent
cwd = root.parent/repo
record = dict(argv=argv, cwd=str(cwd),
              head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=cwd,text=True).strip(),
              started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
with (root/(name+'.log')).open('x') as log:
    process = subprocess.Popen(argv,cwd=cwd,stdout=log,stderr=subprocess.STDOUT)
    record['pid'] = process.pid
    with (root/(name+'-start.json')).open('x') as stream:
        json.dump(record,stream,indent=2)
    code=process.wait()
record.update(exit_code=code,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
with (root/(name+'-finish.json')).open('x') as stream:
    json.dump(record,stream,indent=2)
print(json.dumps(record))
sys.exit(code)
