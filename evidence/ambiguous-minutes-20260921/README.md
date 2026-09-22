# Native one-minute ambiguity evidence

Exact original Actions ZIP, durably preserved as deterministic 32 KiB parts.
Source run 35559122193, artifact 10622037487, source commit 411419f3cd7796bf3fe73237d8bd796e74e6af13.
Original length 729363 bytes; SHA256 7cf97ac730953674d7da9f503eddf0d16470b7fd3fa885d5ab16b4ace098580f.

Verified on receipt: ZIP CRC, 8 inventory hashes, all 56 referenced payload
lengths/SHA256, and 1440 consecutive minute bars per day (11520 total).
There are 73 ZIP members. All raw responses and normalized bars/funding remain
inside the reconstructed original. No data was reacquired from Bybit.

Reconstruct from repository root:

```python
from pathlib import Path
import hashlib, json
root = Path('evidence/ambiguous-minutes-20260921')
m = json.loads((root / 'manifest.json').read_text())
out = Path(m['original_path'])
offset = 0
h = hashlib.sha256()
with out.open('wb') as stream:
    for row in m['parts']:
        assert row['offset'] == offset
        raw = (root / row['path']).read_bytes()
        assert len(raw) == row['length']
        assert hashlib.sha256(raw).hexdigest() == row['sha256']
        assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == row['git_blob_oid']
        stream.write(raw)
        h.update(raw)
        offset += len(raw)
assert offset == m['bytes'] and h.hexdigest() == m['sha256']
```

## Ordering is not yet resolved

The active branch's saved economic summaries identify dates but do not include
pre-exit position snapshots or an order/equity trace with each event hour and
its exact stop/liquidation levels. The ambiguity request itself only lists dates.
Minute prices alone cannot identify which minute crossed those missing levels,
nor whether a stop fully filled before a subsequent liquidation threshold.

Do not declare eight stops or zero liquidations from this acquisition. Recover
exact baseline event states (or reproduce them from the preserved full native
archive when restoring that dataset is appropriate), then replay minute exits
with partial fills, trade/mark distinction and remaining-minute ambiguity kept
conservative. No economics or production replay ordering was changed here.
