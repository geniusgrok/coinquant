"""One Binance observation entrypoint; unqualified execution stays blocked."""
import argparse
import json
import os
from pathlib import Path
import sys

from .binance import BinanceReadOnly
from .state import State
from .types import Blocked, Unknown, serial


def observe(config_path, *, decision=False, execute=False):
    # Reject before credential access or network I/O. No old venue fallback.
    if execute:
        raise Blocked('Binance write lifecycle and economic model are not qualified; execution unavailable')
    config = json.loads(Path(config_path).read_text())
    if (not isinstance(config, dict) or set(config) != {'account_uid','state_dir'}
            or not isinstance(config['account_uid'],str)
            or not config['account_uid'].isascii() or not config['account_uid'].isdigit()
            or int(config['account_uid']) <= 0
            or not isinstance(config['state_dir'],str) or not config['state_dir'].strip()):
        raise Blocked('explicit Binance UID and persistent state_dir required; obsolete venue configuration refused')
    key=os.environ.get('PANCAKEQUANT_BINANCE_KEY','')
    secret=os.environ.get('PANCAKEQUANT_BINANCE_SECRET','')
    if not key or not secret:
        raise Blocked('explicit Binance read credentials required')
    identity='binance:BTCUSDT:live:'+config['account_uid']
    with State(config['state_dir'],identity) as state:
        venue=BinanceReadOnly(key=key,secret=secret)
        snapshot=venue.snapshot(config['account_uid'])
        recovery={'resolved':0,'pending':0}
        if state.pending():
            recovery=venue.recover_pending(state)
            # Recovery may observe fills newer than the first account read.
            snapshot=venue.snapshot(config['account_uid'])
        market=None;model_preview=None;model_error=None
        if decision:
            from .linear_preview import advance, preview
            try:
                model,market,reconstructed=advance(state,venue)
                model_preview=preview(model,snapshot)
                model_preview['reconstructed_market_only']=reconstructed
                if model_preview['action']=='enter' and not recovery['pending']:
                    replacement=state.get('binance_protection_replacement')
                    if not replacement or replacement.get('done'):
                        from .native_preview import entry_preview
                        model_preview.update(entry_preview(venue,model,snapshot))
            except (Blocked,Unknown) as exc:
                model_error=str(exc)
        report=dict(status='blocked' if decision else 'read_only',exchange='Binance',symbol='BTCUSDT',
                    actual=snapshot,qualification='NOT_QUALIFIED',write_attempted=False,
                    reason='No qualified production alpha or write lifecycle' if decision else 'Account observation only')
        report['intent_recovery']=recovery
        report['pending_intents']=recovery['pending']
        if recovery['pending']:
            report.update(status='unknown',reason='Durable intents remain unresolved; no retry or new risk authorized')
        replacement=state.get('binance_protection_replacement')
        if replacement and not replacement.get('done'):
            report.update(status='unknown',reason='Protection replacement incomplete; reconcile before changing exposure')
            report['protection_replacement']=replacement
        if market is not None:report['market']=market
        if model_preview is not None:report['model_preview']=model_preview
        if model_error is not None:report['model_blocker']=model_error
        state.report(report)
        return report


def main(argv=None):
    parser=argparse.ArgumentParser(description='Bounded Binance BTCUSDT observation; research migration incomplete.')
    commands=parser.add_subparsers(dest='command',required=True)
    for name in ('status','run'):
        command=commands.add_parser(name)
        command.add_argument('--config',default='config.json')
        if name=='run':
            command.add_argument('--execute',action='store_true',help='Currently blocked pending economic and execution qualification')
    args=parser.parse_args(argv)
    try:
        report=observe(args.config,decision=args.command=='run',execute=getattr(args,'execute',False))
    except (Blocked,Unknown) as exc:
        report=dict(status='unknown' if isinstance(exc,Unknown) else 'blocked',reason=str(exc))
    except (OSError,ValueError,KeyError,TypeError,ArithmeticError):
        report=dict(status='unknown',reason='Invalid input or unexpected schema; no success inferred')
    print(json.dumps(serial(report),indent=2,allow_nan=False))
    print(report['status']+': '+report.get('reason',''),file=sys.stderr)
    return 2 if report['status'] in ('unknown','blocked','failed','partial') else 0
