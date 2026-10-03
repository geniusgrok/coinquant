"""One pure review probe: malformed crowding input must not abort safety decisions."""
import hashlib
import io
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from research import edge_forward as f
from spotquant import crowding as c

now = 1790985720000
raw = b'<html>temporarily unavailable</html>'
url = c.PUBLIC_URLS['funding']

class Response(io.BytesIO):
    def __init__(self, requested):
        super().__init__(raw if requested == url else b'[]')
        self.url = requested
    def geturl(self):
        return self.url

result = {'source_head': 'bd9fbc04813d29015c8231cdc63ec784d4a46256',
          'input_sha256': hashlib.sha256(raw).hexdigest(),
          'scope': 'pure mocked public parsing only; no State/Lifecycle/account/network'}
native = c.PublicFeatures()
with patch.object(c, 'urlopen', side_effect=lambda url, timeout: Response(url)), \
        patch.object(c.time, 'time_ns', return_value=(now - 1) * 1000000):
    native.refresh(now - 1)
result['native_value'] = native.value('funding', now)
result['native_missing_cause'] = native.last_lookup['cause']
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / 'funding.raw'
    path.write_bytes(raw)
    receipt = dict(category=f.endpoint(url), url=url, request_ms=now - 2,
                   receipt_ms=now - 1, sha256=f.sha(raw), path=str(path))
    try:
        source = f.crowding_from([receipt], now)
        result['forward_value'] = source.value('funding', now)
    except ValueError as exc:
        result['forward_exception'] = type(exc).__name__
        result['forward_message'] = str(exc)
print(json.dumps(result, indent=2, sort_keys=True))
