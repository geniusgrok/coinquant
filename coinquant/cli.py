"""Read-only by default; explicit bounded demo and dedicated-account trials."""
import argparse
import hashlib
import json
import os
import signal
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .binance import Binance
from .config import load
from .lifecycle import Lifecycle
from .state import State
from .types import Blocked, Unknown, serial


# Demo keys never reach live hosts and live keys never reach demo hosts.
CREDENTIALS = {'live': ('COINQUANT_BINANCE_KEY', 'COINQUANT_BINANCE_SECRET'),
               'demo': ('COINQUANT_BINANCE_DEMO_KEY', 'COINQUANT_BINANCE_DEMO_SECRET')}


def connect(config, *, authorize_writes=False):
    """Environment-specific credentials never fall back to the other account."""
    names=CREDENTIALS[config.environment]
    key,secret=(os.environ.get(name,'') for name in names)
    if not key or not secret:
        raise Blocked(f'explicit Binance {config.environment} read credentials required ({names[0]}, {names[1]})')
    reader=Binance(key=key,secret=secret,environment=config.environment,
                   capital_limit=config.capital_limit,authorize_writes=authorize_writes)
    reader.align_time=True
    return reader


def source_digest():
    """Pin the execution code used for a separately reviewed Demo closure."""
    digest=hashlib.sha256()
    for path in sorted(Path(__file__).parent.glob('*.py')):
        digest.update(path.name.encode()+b'\0'+path.read_bytes()+b'\0')
    return digest.hexdigest()


def trial_gate(path, config, *, mode, uid, evidence=None):
    # All conditions are checked before reading credentials or reaching a host.
    raw=json.loads(Path(path).read_text())
    if (raw.get('environment')!=mode or uid!=config.account_uid
            or mode not in ('demo','live') or config.capital_limit is None):
        raise Blocked('trial requires explicit environment, UID confirmation and positive capital_limit_usdt')
    if mode=='live':
        try:
            proof=json.loads(Path(evidence).read_text())
        except (OSError,TypeError,ValueError):
            raise Blocked('live trial requires reviewed Demo closure evidence') from None
        if not isinstance(proof,dict):
            raise Blocked('Demo closure evidence must be an object')
        required=('demo_uid','entry_order_id','stop_algo_id','take_algo_id',
                  'reduction_order_id','offline_trigger_order_id')
        try:demo_limit=Decimal(proof['demo_capital_limit_usdt'])
        except (KeyError,InvalidOperation,TypeError):demo_limit=Decimal(0)
        if (proof.get('source_digest')!=source_digest() or
                not demo_limit.is_finite() or demo_limit<config.capital_limit or
                any(not isinstance(proof.get(k),str) or not proof[k] for k in required)):
            raise Blocked('Demo closure evidence is absent or belongs to different execution code')


def observe(config_path, *, execute=False):
    # Reject before credential access or network I/O.
    if execute:
        raise Blocked('use run --execute with explicit trial environment and UID')
    config=load(config_path)
    venue=connect(config)
    # The signing clock is aligned once under the request budget before any private
    # read. A failed time read is an explicit unknown; nothing is signed or written.
    venue.begin_cycle(60)
    with State(config.state_dir,config.scope) as state:
        had_pending=bool(state.pending())
        recovery=venue.recover_pending(state)  # also reopens legacy false rejections
        snapshot=venue.snapshot(config.account_uid)
        Lifecycle(venue,state,config.account_uid).instrument()
        if had_pending or recovery['resolved']:
            # Recovery may observe fills newer than the first account read.
            snapshot=venue.snapshot(config.account_uid)
        report=dict(status='read_only',exchange='Binance',environment=config.environment,symbol='BTCUSDT',
                    actual=snapshot,qualification='NOT_QUALIFIED',write_attempted=False,
                    contract_rules_checked=True,source_digest=source_digest(),
                    reason='Account and contract observation only')
        report['intent_recovery']=recovery
        report['pending_intents']=recovery['pending']
        if recovery['pending']:
            report.update(status='unknown',reason='Durable intents remain unresolved; no retry or new risk authorized')
        replacement=state.get('binance_protection_replacement')
        if replacement and not replacement.get('done'):
            report.update(status='unknown',reason='Protection replacement incomplete; reconcile before changing exposure')
            report['protection_replacement']=replacement
        state.report(report)
        return report


class _FirstSignal:
    """The first SIGINT/SIGTERM interrupts observation; later ones during the
    bounded cleanup are ignored so protection and reduction can finish."""
    signals=(signal.SIGINT,signal.SIGTERM)

    def __init__(self):
        self.fired=False;self.previous={}

    def __call__(self,signum,frame):
        if not self.fired:
            self.fired=True
            raise KeyboardInterrupt

    def __enter__(self):
        for number in self.signals:self.previous[number]=signal.signal(number,self)
        return self

    def __exit__(self,*exc):
        for number,handler in self.previous.items():signal.signal(number,handler)


def _dispatch(args):
    if args.command=='status':
        return observe(args.config)
    if args.execute and (not args.trial or not args.authorize_uid):
        raise Blocked('write trial requires --trial and --authorize-uid')
    if not args.execute and (args.trial or args.authorize_uid or args.demo_evidence):
        raise Blocked('trial options require --execute')
    from .dfii10 import eastern
    from .session import run
    eastern()  # fail before credentials when time zone data is missing
    config=load(args.config)
    if args.execute:
        trial_gate(args.config,config,mode=args.trial,uid=args.authorize_uid,evidence=args.demo_evidence)
    return run(config,connect(config,authorize_writes=args.execute),execute=args.execute,
               trial_mode=args.trial if args.execute else None,source_digest=source_digest())


def main(argv=None):
    parser=argparse.ArgumentParser(prog='coinquant', description='Coinquant BTCUSDT bounded observation and controlled trial.')
    commands=parser.add_subparsers(dest='command',required=True)
    for name in ('status','run'):
        command=commands.add_parser(name)
        command.add_argument('--config',default='config.json')
        if name=='run':
            command.add_argument('--execute',action='store_true',help='Enable only an explicitly selected bounded trial')
            command.add_argument('--trial',choices=('demo','live'))
            command.add_argument('--authorize-uid',help='Repeat the dedicated account UID for this run')
            command.add_argument('--demo-evidence',help='Reviewed native Demo closure JSON, required for live')
    args=parser.parse_args(argv)
    try:
        with _FirstSignal():
            report=_dispatch(args)
    except KeyboardInterrupt:
        report=dict(status='unknown',reason='Interrupted before or outside the bounded session; reconcile before any new action')
    except (Blocked,Unknown) as exc:
        report=dict(status='unknown' if isinstance(exc,Unknown) else 'blocked',reason=str(exc))
    except (OSError,ValueError,KeyError,TypeError,ArithmeticError):
        report=dict(status='unknown',reason='Invalid input or unexpected schema; no success inferred')
    print(json.dumps(serial(report),indent=2,allow_nan=False))
    print(report['status']+': '+report.get('reason',''),file=sys.stderr)
    return 2 if report['status'] in ('unknown','blocked','failed','partial') else 0
