"""Three explicit commands, no default live mode or strategy selection menu."""
import argparse
import json
import sys

from .bybit import Bybit
from .config import load
from .execution import run_once
from .types import Blocked, Unknown, serial


def main(argv=None):
    parser = argparse.ArgumentParser(description='On-demand BTC perpetual research and bounded execution.')
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('run', 'status', 'backtest'):
        command = commands.add_parser(name)
        command.add_argument('--config', default='config.json', help='The current explicit account/model configuration')
        if name == 'run':
            command.add_argument('--execute', action='store_true', help='Authorize bounded writes on the matching configured account')
        elif name == 'backtest':
            command.add_argument('--manifest', required=True, help='Hash-verified native-contract data manifest')
            command.add_argument('--output', required=True, help='New, empty evidence output directory')
            command.add_argument('--stress-absence', action='store_true', help='Apply the predeclared multi-day absence to the same trigger sequence')
    args = parser.parse_args(argv)
    try:
        config = load(args.config)
        if args.command == 'status':
            venue = Bybit(config)
            snapshot = venue.snapshot()
            report = dict(status='read_only', environment=config.environment, account_uid=snapshot.account_id,
                          actual=serial(snapshot), note='Observed exchange state; no strategy order or account write sent.')
        elif args.command == 'run':
            venue = Bybit(config, execute=args.execute)
            report = run_once(venue, config, execute=args.execute)
        else:
            # Live trading paths never import the long-history replay engine.
            from .replay import run
            report = run(args.manifest, args.output, config, stress=args.stress_absence)
    except (Blocked, Unknown) as exc:
        report = dict(status='unknown' if isinstance(exc, Unknown) else 'blocked', reason=str(exc))
    except (OSError, ValueError, KeyError, TypeError, ArithmeticError):
        # No signed HTTP requests, secrets or raw response fragments in errors.
        report = dict(status='unknown', reason='Invalid input or unexpected schema; inspect preserved local evidence. No success is inferred.')
    print(json.dumps(serial(report), indent=2, allow_nan=False))
    target = report.get('target', {})
    detail = report.get('reason') or target.get('reason') or report.get('note', '')
    print(f"{report['status']}: {detail}", file=sys.stderr)
    if target:
        print(f"Target {target.get('quantity')} USD contracts; TP {target.get('take_profit')}; SL {target.get('stop_loss')}", file=sys.stderr)
    return 2 if report['status'] in ('unknown', 'blocked', 'failed', 'partial') else 0
