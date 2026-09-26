"""One Binance observation entrypoint; unqualified execution stays blocked."""
import argparse
import json
import os
import sys

from .binance import Binance
from .config import load
from .state import State
from .types import Blocked, Unknown, serial


def observe(config_path, *, execute=False):
    # Reject before credential access or network I/O. No old venue fallback.
    if execute:
        raise Blocked('Binance write lifecycle and economic model are not qualified; execution unavailable')
    from dataclasses import asdict
    config = asdict(load(config_path))
    key=os.environ.get('COINQUANT_BINANCE_KEY','')
    secret=os.environ.get('COINQUANT_BINANCE_SECRET','')
    if not key or not secret:
        raise Blocked('explicit Binance read credentials required')
    identity='binance:BTCUSDT:live:'+config['account_uid']
    with State(config['state_dir'],identity) as state:
        venue=Binance(key=key,secret=secret)
        snapshot=venue.snapshot(config['account_uid'])
        recovery={'resolved':0,'pending':0}
        if state.pending():
            recovery=venue.recover_pending(state)
            # Recovery may observe fills newer than the first account read.
            snapshot=venue.snapshot(config['account_uid'])
        report=dict(status='read_only',exchange='Binance',symbol='BTCUSDT',
                    actual=snapshot,qualification='NOT_QUALIFIED',write_attempted=False,
                    reason='Account observation only')
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


def main(argv=None):
    parser=argparse.ArgumentParser(prog='coinquant', description='Coinquant Binance BTCUSDT observation; execution requires economic and safety qualification.')
    commands=parser.add_subparsers(dest='command',required=True)
    for name in ('status','run'):
        command=commands.add_parser(name)
        command.add_argument('--config',default='config.json')
        if name=='run':
            command.add_argument('--execute',action='store_true',help='Currently blocked pending economic and execution qualification')
    args=parser.parse_args(argv)
    try:
        if args.command=='status':
            report=observe(args.config)
        else:
            # Engineering completion is not permission to trade or qualification.
            if args.execute:
                raise Blocked('Native exchange validation and economic acceptance remain incomplete; execution unavailable')
            from .session import run
            config=load(args.config)
            key=os.environ.get('COINQUANT_BINANCE_KEY','')
            secret=os.environ.get('COINQUANT_BINANCE_SECRET','')
            if not key or not secret:raise Blocked('explicit Binance read credentials required')
            report=run(config,Binance(key=key,secret=secret))
    except (Blocked,Unknown) as exc:
        report=dict(status='unknown' if isinstance(exc,Unknown) else 'blocked',reason=str(exc))
    except (OSError,ValueError,KeyError,TypeError,ArithmeticError):
        report=dict(status='unknown',reason='Invalid input or unexpected schema; no success inferred')
    print(json.dumps(serial(report),indent=2,allow_nan=False))
    print(report['status']+': '+report.get('reason',''),file=sys.stderr)
    return 2 if report['status'] in ('unknown','blocked','failed','partial') else 0
