"""Safe offline venue continuation at a verified finite-session boundary.

This retains the original account SQLite directory. It never restores an old
receipt without a venue checkpoint, moves account state, or changes account
locks. Parsed market buffers are deterministic caches, not account state.
"""
from collections import deque
from datetime import date
from decimal import Decimal
import hashlib
import json
import math
import os
from pathlib import Path

from coinquant.state import State

VERSION = 'default-runtime-research-exchange-checkpoint-v2'
ROOT = Path(os.environ['CQR_RUNTIME_ROOT']).resolve()
TOOLING = Path(__file__).resolve().parents[1]
FIELDS = tuple('now_ms wallet q entry margin _changed _changed_ms fees funding_paid '
    'orders algos trades income _seq _tran sent funnel held_from _scanned '
    'hindsight_bounded print_miss_days bounded_minutes unknown_from peak_cny '
    'peak_envelope_cny mdd_close mdd_envelope mdd_close_at mdd_envelope_at '
    'daily_cny known_path daily _initial_peak_pending cooldown_until request_weights '
    'check_all_orders all_orders_checked_at deadline hard_deadline align_time '
    'time_offset_ms time_aligned_at server_weight _cycle_config _config_at '
    '_verified_uid _inflight _last_mark _commission _path_audit'.split())
PARAMETERS = tuple('uid matcher fee trigger_slippage market_slippage print_window_ms '
    'latency_ms read_latency_ms mark_gap rules_sha256 rules environment capital_limit '
    'authorize_writes terminal_ms initial_cny exit_conversion loss_fraction slip_fraction'.split())
EXTERNAL = {'market', 'prints', 'fx', 'by_order_id', 'key', 'secret', 'opener',
            'clock', '_monotonic', '_dfii10', 'offline'}
OPTIONAL_FIELDS = {'_cycle_config', '_config_at', '_verified_uid', '_inflight', '_last_mark', '_commission'}


def encode(value):
    """Explicit JSON types; no pickle, object reconstruction, or lossy keys."""
    if value is None or type(value) in (str, int, bool):
        return value
    if type(value) is float and math.isfinite(value):
        return {'type': 'float', 'value': repr(value)}
    if isinstance(value, Decimal) and value.is_finite():
        return {'type': 'decimal', 'value': str(value)}
    if type(value) is date:
        return {'type': 'date', 'value': value.isoformat()}
    if type(value) is dict:
        return {'type': 'dict', 'value': [[encode(k), encode(v)] for k, v in value.items()]}
    if type(value) in (tuple, list, set, deque):
        name = type(value).__name__
        values = sorted(value) if type(value) is set else value
        return {'type': name, 'value': [encode(v) for v in values]}
    raise ValueError('unsupported or nonfinite checkpoint value: ' + type(value).__name__)


def decode(value):
    if value is None or type(value) in (str, int, bool):
        return value
    if type(value) is not dict or set(value) != {'type', 'value'}:
        raise ValueError('invalid checkpoint codec')
    kind, items = value['type'], value['value']
    if kind in ('decimal', 'float', 'date'):
        result = {'decimal': Decimal, 'float': float, 'date': date.fromisoformat}[kind](items)
        if (kind == 'decimal' and not result.is_finite()) or (kind == 'float' and not math.isfinite(result)):
            raise ValueError('nonfinite checkpoint value')
        return result
    if kind == 'dict':
        pairs = [(decode(k), decode(v)) for k, v in items]
        result = dict(pairs)
        if len(result) != len(pairs):
            raise ValueError('duplicate checkpoint key')
        return result
    if kind in ('list', 'tuple', 'set', 'deque'):
        return {'list': list, 'tuple': tuple, 'set': set, 'deque': deque}[kind](decode(v) for v in items)
    raise ValueError('unknown checkpoint codec type')


def digest(value):
    return hashlib.sha256(json.dumps(encode(value), sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def source_fingerprint():
    """Actual current runtime plus privately adapted replay tools; no old runtime."""
    files = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted((ROOT/'coinquant').glob('*.py'))}
    files.update({'tooling/'+str(p.relative_to(TOOLING)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted((TOOLING/'research').glob('*.py'))})
    files['tooling/driver.py'] = hashlib.sha256((TOOLING/'driver.py').read_bytes()).hexdigest()
    return digest(files)


def _binding(binding):
    required = {'source_sha256', 'strategy_sha256', 'input_sha256', 'schedule_sha256'}
    if not isinstance(binding, dict) or not required <= binding.keys():
        raise ValueError('checkpoint requires execution, strategy, input and schedule bindings')
    if any(not isinstance(binding[k], str) or len(binding[k]) != 64
           or any(c not in '0123456789abcdef' for c in binding[k]) for k in required):
        raise ValueError('invalid checkpoint dependency digest')
    if binding['source_sha256'] != source_fingerprint():
        raise ValueError('checkpoint execution source changed')
    return dict(binding)


def _venue(venue, config):
    from research.complete_perp import ResearchExchange
    from research.session_market import Market, TradePrints
    from research.unified_perp import PriorFX
    if (type(venue) is not ResearchExchange or getattr(venue, 'offline', False) is not True
            or type(venue.market) is not Market or not isinstance(venue.prints, TradePrints)
            or type(venue.fx) is not PriorFX):
        raise ValueError('checkpoint requires the actual offline ResearchExchange and bound inputs')
    if (str(venue.uid) != config.account_uid or venue.key != 'historical-proxy'
            or venue.secret != 'historical-proxy' or venue._dfii10 is not None):
        raise ValueError('checkpoint account or offline boundary mismatch')
    unknown = set(vars(venue)) - set(FIELDS) - set(PARAMETERS) - EXTERNAL
    if unknown:
        raise ValueError('new venue state needs an explicit checkpoint version: ' + ','.join(sorted(unknown)))
    if {k: v['orderId'] for k, v in venue.orders.items()} != {
            v['clientOrderId']: k for k, v in venue.by_order_id.items()} or any(
            venue.by_order_id[v['orderId']] is not v for v in venue.orders.values()):
        raise ValueError('venue order identity index inconsistent')
    return dict(parameters={k: getattr(venue, k) for k in PARAMETERS},
        market_type='research.session_market.Market',
        market_inputs=digest((venue.market.h4, venue.market.funding, venue.market._funding_times,
                             venue.market.funding_grid, venue.market.identity)),
        market_root=str(venue.market.root.resolve()) if venue.market.root else None,
        prints_type=type(venue.prints).__module__ + '.' + type(venue.prints).__qualname__,
        prints_root=str(venue.prints.root.resolve()), fx_sha256=venue.fx.sha256,
        fx_inputs=digest((venue.fx.days, venue.fx.rates)))


def _account(state, config):
    """Fingerprint durable economic state while holding the normal two locks."""
    if state.db is None or state.lock is None or state.account_lock is None:
        raise ValueError('checkpoint requires normal state and account locks')
    if state.identity != config.scope or state.get('identity') != config.scope:
        raise ValueError('checkpoint SQLite identity mismatch')
    if state.pending() or state.get('session_replacement'):
        raise ValueError('checkpoint unresolved durable execution')
    tables = {}
    for (name,) in state.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
        # State supplies names, never a checkpoint or caller-provided SQL identifier.
        quoted = '"' + name.replace('"', '""') + '"'
        columns = [r[1] for r in state.db.execute('PRAGMA table_info(' + quoted + ')')]
        rows = list(state.db.execute('SELECT * FROM ' + quoted + ' ORDER BY ' +
            ','.join('"' + c.replace('"', '""') + '"' for c in columns)))
        if name == 'meta':
            # Normal State.__enter__ refreshes this lock lease. It is not an
            # economic/model/clock cursor and is never imported from a checkpoint.
            rows = [row for row in rows if row[0] != 'writer_host']
        tables[name] = {'columns': columns, 'rows': rows}
    archive = Path(config.state_dir).expanduser().resolve() / 'observations-archive.jsonl'
    archive_identity = dict(present=archive.exists(), bytes=0, sha256=None)
    if archive.exists():
        content = hashlib.sha256()
        with archive.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                content.update(block)
                archive_identity['bytes'] += len(block)
        archive_identity['sha256'] = content.hexdigest()
    return dict(directory=str(Path(config.state_dir).expanduser().resolve()),
                scope=config.scope, database='intents.sqlite', durable_sha256=digest(tables),
                observations_archive=archive_identity)


def _config(config):
    from dataclasses import asdict
    result = asdict(config)
    result['state_dir'] = str(Path(config.state_dir).expanduser().resolve())
    return result


def _history_snapshot():
    from research.session_exchange import SessionExchange
    history = SessionExchange._dfii10_history
    if history is None:
        return None
    return dict(inputs=digest((history.dates, history.updates, history.times, history.counts)),
        state={k: getattr(history, k) for k in ('index', 'current', 'last_now', 'cached')})


def _protected(venue):
    if not venue.q:
        return True
    live = venue._working_algos()
    stop, take = venue._triggers()
    side = 'SELL' if venue.q > 0 else 'BUY'
    return (len(live) == 2 and {a.get('orderType') for a in live} ==
            {'STOP_MARKET', 'TAKE_PROFIT_MARKET'} and all(
            a.get('symbol') == 'BTCUSDT' and a.get('side') == side
            and a.get('positionSide') == 'BOTH' and a.get('closePosition') is True
            and a.get('workingType') == 'MARK_PRICE' and a.get('priceProtect') is False
            and str(a.get('clientAlgoId', '')).startswith('cq-') for a in live)
            and stop is not None and take is not None and
            (stop > venue._liquidation() if venue.q > 0 else stop < venue._liquidation()))


def snapshot_venue(venue, *, binding, config, session_report):
    """Export only after session.run returned verified cleanup with no intent."""
    binding, constructor = _binding(binding), _venue(venue, config)
    if (session_report.get('cleanup') != 'verified'
            or session_report.get('pending_intents') != 0
            or session_report.get('execution_unresolved') is not False
            or session_report.get('protection_replacement_pending')
            or session_report.get('income_audit', {}).get('status') == 'unresolved'):
        raise ValueError('checkpoint is not a verified finite-session boundary')
    actual = session_report.get('actual') or {}
    if venue._working_orders() or not _protected(venue) or (venue.q and (
            not actual.get('native_full_position_protected') or not actual.get('stop_before_liquidation')
            or Decimal(actual.get('quantity_btc', '0')) != venue.q)):
        raise ValueError('checkpoint requires settled orders and protected owned exposure')
    with State(config.state_dir, config.scope) as state:
        account = _account(state, config)
        body = dict(version=VERSION, binding=binding, config=_config(config),
            constructor=constructor, account=account,
            venue={k: getattr(venue, k) for k in FIELDS if hasattr(venue, k)},
            market_loaded=venue.market.loaded, prints_loaded=venue.prints.loaded,
            prints_aux={k: getattr(venue.prints, k) for k in ('missing', 'used') if hasattr(venue.prints, k)},
            history=_history_snapshot())
        # Encoding also makes an independent copy before the venue moves again.
        encoded = encode(body)
    return {'body': encoded, 'sha256': digest(encoded)}


def restore_venue(venue, checkpoint, *, binding, config):
    """Restore a fresh venue, using the unchanged original SQLite and locks."""
    binding, constructor = _binding(binding), _venue(venue, config)
    if (not isinstance(checkpoint, dict) or set(checkpoint) != {'body', 'sha256'}
            or digest(checkpoint['body']) != checkpoint['sha256']):
        raise ValueError('checkpoint digest mismatch')
    body = decode(checkpoint['body'])
    if (body['version'] != VERSION or body['binding'] != binding
            or body['config'] != _config(config) or body['constructor'] != constructor):
        raise ValueError('checkpoint dependencies, strategy, config or venue changed')
    if venue.q or venue.orders or venue.algos or venue.trades or venue.income or venue.sent or venue.request_weights:
        raise ValueError('restore requires a fresh venue, never merge an active account')
    if (not set(body['venue']) <= set(FIELDS) or
            not set(FIELDS) - OPTIONAL_FIELDS <= set(body['venue'])):
        raise ValueError('unsupported checkpoint field')
    from research.dfii10_history import History
    from research.session_exchange import SessionExchange
    history = None
    if body['history'] is not None:
        history = SessionExchange._dfii10_history or History()
        if digest((history.dates, history.updates, history.times, history.counts)) != body['history']['inputs']:
            raise ValueError('checkpoint historical macro input changed')
    with State(config.state_dir, config.scope) as state:
        if _account(state, config) != body['account']:
            raise ValueError('checkpoint SQLite was changed or replaced; no state reset')
        for key in FIELDS:
            if key in body['venue']:
                setattr(venue, key, body['venue'][key])
            elif key in vars(venue):
                delattr(venue, key)
        venue.by_order_id = {v['orderId']: v for v in venue.orders.values()}
        venue.market.loaded = body['market_loaded']
        venue.market._months.clear()
        venue.market._order.clear()
        if hasattr(venue.market._load_month, 'cache_clear'):
            venue.market._load_month.cache_clear()
        venue.prints.loaded = body['prints_loaded']
        venue.prints._day_ms = venue.prints._rows = None
        if hasattr(venue.prints, 'days'):
            venue.prints.days.clear()
        for key, value in body['prints_aux'].items():
            setattr(venue.prints, key, value)
        if history is not None:
            for key, value in body['history']['state'].items():
                setattr(history, key, value)
        SessionExchange._dfii10_history = history
    return venue

