"""Offline native API tape replay through the production finite-session runner.

This is an engineering parity check, never a historical economic account. Tapes
contain identified native-shape responses and exact unsigned request parameters;
never credentials, signatures or authorization headers. Reads cannot look ahead:
the next recorded request must match before its response becomes visible.
"""
import argparse
import json
from pathlib import Path

from coinquant.binance import Binance
from coinquant.config import Config
from coinquant.session import run
from coinquant.types import Unknown, serial


class Tape(Binance):
    def __init__(self, records, start_ms):
        self.records=records
        self.index=0
        self.now=start_ms
        super().__init__(clock=lambda:self.now/1000,authorize_writes=True)

    def _request(self, method, path, parameters=None):
        if self.index>=len(self.records):
            raise Unknown('replay tape exhausted')
        record=self.records[self.index]
        if (record['method'],record['path'],record.get('parameters',{}))!=(method,path,parameters or {}):
            raise Unknown('replay request differs at index '+str(self.index))
        if record['time_ms']<self.now:
            raise Unknown('replay response predates its request')
        self.index+=1;self.now=record['time_ms']
        if record.get('unknown'):
            raise Unknown('recorded unknown transport outcome')
        return record['response']

    def wait(self,seconds):
        self.now+=int(seconds*1000)


def replay(tape, config, *, execute=False):
    reader=Tape(tape['records'],tape['start_ms'])
    result=run(config,reader,execute=execute,monotonic=reader.clock,wait=reader.wait)
    result['tape_complete']=reader.index==len(reader.records)
    result['records_consumed']=reader.index
    if not result['tape_complete']:
        result.update(status='unknown',reason='unconsumed replay records')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('tape',type=Path)
    p.add_argument('--state-dir',type=Path,required=True)
    args=p.parse_args()
    if args.state_dir.exists():p.error('use an isolated new replay state directory')
    data=json.loads(args.tape.read_text())
    config=Config(state_dir=str(args.state_dir),**data['config'])
    if 'checkpoint' in data:
        from coinquant.state import State
        with State(config.state_dir,'binance:BTCUSDT:live:'+config.account_uid) as state:
            state.set('linear_campaign',data['checkpoint'])
    result=replay(data,config,execute=data.get('execute') is True)
    print(json.dumps(serial(result),indent=2))
    return 0 if result['tape_complete'] and result['status'] not in ('unknown','blocked') else 2


if __name__=='__main__':
    raise SystemExit(main())
