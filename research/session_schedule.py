"""Frozen session-start schedule for the economic rebuild.

Primary and absence sequences are the frozen legacy invocation timestamps used
as session starts (rule 2 of the rebuild protocol). The two extra stresses are
derived only from a fixed seed and the start indices, never from market data.
"""
import hashlib
import json
from pathlib import Path

from research.session_b0 import load_schedule

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'research' / 'session_schedule.json'
SEED = 'coinquant-session-stress-20260927'
SKIP_RATIO = 0.2
BLOCK_MS = 21 * 86_400_000


def _unit(*parts):
    digest = hashlib.sha256('|'.join(map(str, (SEED,) + parts)).encode()).digest()
    return int.from_bytes(digest[:8], 'big') / 2 ** 64


def _sha(values):
    return hashlib.sha256(json.dumps(values, separators=(',', ':')).encode()).hexdigest()


def body():
    frozen = load_schedule()
    starts = frozen['starts_ms']
    skip = [start for index, start in enumerate(starts) if _unit('skip', index) >= SKIP_RATIO]
    first = starts[int(_unit('block') * len(starts))]
    block = [start for start in starts if not first <= start < first + BLOCK_MS]
    return {
        'identity': 'coinquant bounded-session schedule, frozen before any rebuild measurement',
        'timezone': 'UTC',
        'start': frozen['start'],
        'end': frozen['end'],
        'end_exclusive': True,
        'generator': 'legacy invocation timestamps as session starts (research.session_b0.schedule_body)',
        'draws_sha256': frozen['draws_sha256'],
        'session_seconds': 300,
        'poll_seconds': 5,
        'request_latency_ms': 1000,
        'cleanup': 'deadline ends new decisions; owned protection finishes; exchange state persists between sessions',
        'development_end': frozen['development_end'],
        'development_sessions': frozen['development_sessions'],
        'primary': {'count': len(starts), 'sha256': _sha(starts), 'starts_ms': starts},
        'stress': {
            'absence': {'rule': 'frozen legacy absence-stress invocation sequence',
                        'count': len(frozen['absence_starts_ms']),
                        'sha256': _sha(frozen['absence_starts_ms']),
                        'starts_ms': frozen['absence_starts_ms']},
            'random_skip': {'rule': 'drop primary index i when sha256(seed|skip|i) unit < ratio',
                            'seed': SEED, 'ratio': SKIP_RATIO, 'count': len(skip), 'sha256': _sha(skip),
                            'starts_ms': skip},
            'block_21d': {'rule': 'drop primary starts in [first, first+21d); first = primary[floor(sha256(seed|block) unit*count)]',
                          'seed': SEED, 'first_ms': first, 'count': len(block), 'sha256': _sha(block),
                          'starts_ms': block},
        },
    }


def write():
    PATH.write_text(json.dumps(body()) + '\n', encoding='utf-8')


def load():
    committed = json.loads(PATH.read_text(encoding='utf-8'))
    if committed != body():
        raise ValueError('committed session schedule does not match its frozen generator')
    return committed


if __name__ == '__main__':
    write()
    data = load()
    print(json.dumps({'primary': data['primary']['count'], 'sha256': data['primary']['sha256'],
                      **{k: v['count'] for k, v in data['stress'].items()}}))
