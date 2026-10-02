"""Read-only discriminating stub: no State, session runner, producer, files or network.

The actual request/snapshot/transport/answer/mark/load methods execute on synthetic
in-memory state. RollingPrints.__init__ is deliberately never called. All paths
are non-filesystem stubs, every urlopen is intercepted, and no real credentials
are read. This probe does not reproduce or claim the original HTTP status.
"""
from collections import deque
from decimal import Decimal as D
from io import BytesIO
import json
from types import SimpleNamespace
from urllib.error import HTTPError
import urllib.request

from coinquant.binance import Binance
from coinquant.types import Unknown
from research.session_exchange import SessionExchange
from research.rolling_prints import RollingPrints


class NoFilesystemPath:
    def __truediv__(self, _name): return self
    def exists(self): return False
    def with_suffix(self, _suffix): return self
    def open(self, *_args, **_kwargs): raise AssertionError('filesystem write prohibited')


class NoNetwork:
    def open(self, *_args, **_kwargs): raise AssertionError('network prohibited')


class Probe(SessionExchange):
    def __init__(self, start, prints):
        self.now_ms = start
        self.q, self.entry, self.margin, self.wallet = D(0), D(0), D(0), D(1000)
        self._changed, self._changed_ms = None, start
        self.uid, self._verified_uid = 12000, '12000'
        self.orders, self.algos, self.trades = {}, {}, []
        self.unknown_from = None
        self.requests = []
        self.prints = prints
        self.market = SimpleNamespace(minute=lambda *_: (D(100), D(101), D(99), D(100), D(1)))
        self.read_latency_ms = 200
        Binance.__init__(self, key='synthetic-unused', secret='synthetic-unused', opener=NoNetwork(),
                         clock=lambda: self.now_ms/1000, monotonic=lambda: self.now_ms/1000)

    def _note_cash(self):
        pass  # No economic measurement: only the real flat virtual-clock path.

    def _transport(self, request, timeout):
        self.requests.append({'method': self._inflight[0], 'path': self._inflight[1],
                              'before_ms': self.now_ms})
        return super()._transport(request, timeout)


def case(start, stage, status):
    tape = object.__new__(RollingPrints)
    tape.root, tape.missing, tape.used = NoFilesystemPath(), set(), []
    tape._day_ms, tape._rows = None, None
    public = []
    def urlopen(url, **kwargs):
        public.append({'url': url, 'timeout': kwargs['timeout']})
        if stage == 'zip' and url.endswith('.CHECKSUM'):
            return BytesIO(('a'*64+'  stub.zip\n').encode())
        raise HTTPError(url, status, 'injected public archive failure', {}, BytesIO(b'public CDN failure'))
    original = urllib.request.urlopen
    urllib.request.urlopen = urlopen
    probe = Probe(start, tape)
    try:
        try:
            probe.snapshot('12000')
            raise AssertionError('injected failure did not propagate')
        except Unknown as exc:
            result = {'session_start_ms': start, 'injected_stage': stage, 'injected_http_status': status,
                'requests': probe.requests, 'public_url_calls': public, 'failure_at_ms': probe.now_ms,
                'exception': type(exc).__name__, 'reason': str(exc), 'http_status': exc.http_status,
                'native_code': exc.native_code}
        assert [r['path'] for r in probe.requests] == [
            '/fapi/v1/accountConfig', '/fapi/v1/symbolConfig', '/fapi/v3/account']
        assert probe.now_ms == start+600
        if status != 404:
            assert result['reason'] == 'Binance HTTP outcome unresolved; query stable identity after cooldown'
        else:
            assert result['reason'] == 'no trade print at or before the request'
        return result
    finally:
        urllib.request.urlopen = original


def local_control(start):
    # Cached verified data bypass the downloader entirely; no retry/clock patch.
    probe = Probe(start, SimpleNamespace(last=lambda at: (at, D(100))))
    result = probe.snapshot('12000')
    assert result['quantity_btc'] == '0'
    return {'case': 'local_prints_no_downloader', 'session_start_ms': start,
            'request_count': len(probe.requests), 'snapshot_at_ms': probe.now_ms,
            'quantity_btc': result['quantity_btc'], 'public_url_calls': 0}


if __name__ == '__main__':
    results = [case(start, stage, status) for start in (1585486800000, 1587355200000)
               for stage, status in (('checksum', 503), ('zip', 503), ('checksum', 404))]
    results += [local_control(1585486800000), local_control(1587355200000)]
    print(json.dumps({'synthetic_only': True, 'network_requests': 0, 'state_or_locks': 0,
                      'source_or_cache_mutations': 0, 'results': results}, indent=2))
