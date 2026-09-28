"""Frozen session-start schedule for the economic rebuild.

`research/session_schedule.json` is committed and frozen. Primary and absence
starts are fixed timestamps verified by their recorded SHA-256. The two extra
stresses are re-derived here from the primary starts and a fixed seed, never
from market data. The strategy never receives this list.
"""
import hashlib
import json
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / 'research' / 'session_schedule.json'
SEED = 'coinquant-session-stress-20260927'
SKIP_RATIO = 0.2
BLOCK_MS = 21 * 86_400_000
PRIMARY_SHA256 = 'f8fb73bebf142ddcc3ed4a3e6b12b4dd7abed1e27bcd8a4ff1c93aec4fe0b32a'


def _unit(*parts):
    digest = hashlib.sha256('|'.join(map(str, (SEED,) + parts)).encode()).digest()
    return int.from_bytes(digest[:8], 'big') / 2 ** 64


def _sha(values):
    return hashlib.sha256(json.dumps(values, separators=(',', ':')).encode()).hexdigest()


def derived(starts):
    skip = [start for index, start in enumerate(starts) if _unit('skip', index) >= SKIP_RATIO]
    first = starts[int(_unit('block') * len(starts))]
    block = [start for start in starts if not first <= start < first + BLOCK_MS]
    return {'random_skip': skip, 'block_21d': block}, first


def load():
    committed = json.loads(PATH.read_text(encoding='utf-8'))
    primary = committed['primary']['starts_ms']
    if (committed['primary']['sha256'] != PRIMARY_SHA256 or _sha(primary) != PRIMARY_SHA256
            or len(primary) != 795 or primary != sorted(set(primary))):
        raise ValueError('primary session schedule changed')
    if (committed['session_seconds'], committed['poll_seconds'], committed['request_latency_ms']) != (300, 5, 1000):
        raise ValueError('session clock changed')
    stresses, first = derived(primary)
    if committed['stress']['block_21d']['first_ms'] != first:
        raise ValueError('block stress origin changed')
    for name, entry in committed['stress'].items():
        starts = entry['starts_ms']
        if name in stresses and starts != stresses[name]:
            raise ValueError(f'{name} stress does not follow its rule')
        if _sha(starts) != entry['sha256'] or len(starts) != entry['count']:
            raise ValueError(f'{name} stress identity changed')
    return committed


if __name__ == '__main__':
    data = load()
    print(json.dumps({'primary': data['primary']['count'], 'sha256': data['primary']['sha256'],
                      **{k: v['count'] for k, v in data['stress'].items()}}))
