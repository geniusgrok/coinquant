"""One Binance observation entrypoint; unqualified execution stays blocked."""
import argparse
import json
import os
import sys

from .binance import Binance
from .config import load
from .state import State
from .types import Blocked, Unknown, serial


# Demo keys never reach live hosts and live keys never reach demo hosts.
CREDENTIALS = {'live': ('COINQUANT_BINANCE_KEY', 'COINQUANT_BINANCE_SECRET'),
               'demo': ('COINQUANT_BINANCE_DEMO_KEY', 'COINQUANT_BINANCE_DEMO_SECRET')}


def connect(config):
    """Read-only adapter for the configured environment and its own credentials."""
    names=CREDENTIALS[config.environment]
    key,secret=(os.environ.get(name,'') for name in names)
    if not key or not secret:
        raise Blocked(f'explicit Binance {config.environment} read credentials required ({names[0]}, {names[1]})')
    return Binance(key=key,secret=secret,environment=config.environment,capital_limit=config.capital_limit)


def observe(config_path, *, execute=False):
    # Reject before credential access or network I/O.
    if execute:
        raise Blocked('Binance write lifecycle and economic model are not qualified; execution unavailable')
    config=load(config_path)
    venue=connect(config)
    with State(config.state_dir,config.scope) as state:
        snapshot=venue.snapshot(config.account_uid)
        recovery={'resolved':0,'pending':0}
        if state.pending():
            recovery=venue.recover_pending(state)
            # Recovery may observe fills newer than the first account read.
            snapshot=venue.snapshot(config.account_uid)
        report=dict(status='read_only',exchange='Binance',environment=config.environment,symbol='BTCUSDT',
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
            from .dfii10 import eastern
            from .session import run
            eastern()  # fail before credentials when time zone data is missing
            config=load(args.config)
            report=run(config,connect(config))
    except (Blocked,Unknown) as exc:
        report=dict(status='unknown' if isinstance(exc,Unknown) else 'blocked',reason=str(exc))
    except (OSError,ValueError,KeyError,TypeError,ArithmeticError):
        report=dict(status='unknown',reason='Invalid input or unexpected schema; no success inferred')
    print(json.dumps(serial(report),indent=2,allow_nan=False))
    print(report['status']+': '+report.get('reason',''),file=sys.stderr)
    return 2 if report['status'] in ('unknown','blocked','failed','partial') else 0
