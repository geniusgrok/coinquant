"""Necessary derived-cache identity and performance-only fallback checks."""
import array
import gzip
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research.progress_accounts import cached_market

NAME = 'BTCUSDT-aggTrades-2020-05-08.zip'
DAY = 1588896000000


class QualifiedBytesTape:
    """Pure already-qualified parser bytes, with no venue or account."""
    def __init__(self, private, data, qualified):
        self.private, self.data, self.qualified = private, data, qualified
        self._day_ms, self.loaded, self.origin = None, {}, None
        self.clock_marker = DAY+12345

    def _load(self, day):
        binary = self.private/(NAME+'.'+self.qualified+'.bin')
        packed = Path(str(binary)+'.gz')
        if packed.is_file():
            with gzip.open(packed, 'rb') as stream:
                binary.write_bytes(stream.read())
            self.origin = 'shared-gzip'
        else:
            binary.write_bytes(self.data)
            self.origin = 'qualified-original'
        self.loaded[NAME], self._day_ms = self.qualified, day
        with binary.open('rb') as stream:
            count = array.array('q'); count.fromfile(stream, 1)
            rows = tuple(array.array('q') for _ in range(4))
            for column in rows:
                column.fromfile(stream, count[0])
        return rows


def fixture_bytes(price):
    columns = ((DAY, DAY+10), (1, 2), (price, price+1), (10, 20))
    return array.array('q', [2]).tobytes()+b''.join(array.array('q', v).tobytes() for v in columns)


class ProgressCacheTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root/'prints').mkdir()
        self.spec = dict(prints=str(self.root/'prints'),
            shared_parsed_cache=str(self.root/'shared'), shared_parsed_cache_max_bytes=100000)

    def consumer(self, label, data):
        scratch = self.root/label
        private = scratch/'private-parsed-prints-cache'
        private.mkdir(parents=True)
        qualified = hashlib.sha256(data).hexdigest()
        (self.root/'prints'/(NAME+'.CHECKSUM')).write_text(qualified+'  '+NAME+'\n')
        tape, events = QualifiedBytesTape(private, data, qualified), []
        marker = object()
        market, result = cached_market(self.spec, scratch, lambda *_: (marker, tape), events)
        self.assertIs(market, marker)
        self.assertIs(result, tape)
        return tape, events

    def test_independent_private_hit_and_changed_source_never_reuses_stale_rows(self):
        first, events = self.consumer('first', fixture_bytes(100))
        rows = first._load(DAY)
        self.assertEqual(events[-1]['status'], 'published')
        second, events2 = self.consumer('second', fixture_bytes(100))
        self.assertEqual(second._load(DAY), rows)
        self.assertEqual(second.origin, 'shared-gzip')
        self.assertTrue(events2[-1]['shared_hit'])
        changed, events3 = self.consumer('changed', fixture_bytes(200))
        changed_rows = changed._load(DAY)
        self.assertNotEqual(changed_rows, rows)
        self.assertEqual(changed_rows[2], array.array('q', (200, 201)))
        self.assertEqual(changed.origin, 'qualified-original')
        self.assertFalse(events3[-1]['shared_hit'])
        for tape in (first, second, changed):
            self.assertEqual(tape.clock_marker, DAY+12345)

    def test_capacity_and_publish_io_skip_do_not_change_rows_or_clock(self):
        self.spec['shared_parsed_cache_max_bytes'] = 1
        capped, events = self.consumer('capped', fixture_bytes(100))
        expected = capped._load(DAY)
        self.assertEqual(events[-1]['status'], 'capacity-skip')
        self.assertFalse(list((self.root/'shared').rglob('*.bin.gz')))
        self.spec['shared_parsed_cache_max_bytes'] = 100000
        failed, failures = self.consumer('io-fallback', fixture_bytes(100))
        with patch('tempfile.mkstemp', side_effect=OSError('mock full storage')):
            actual = failed._load(DAY)
        self.assertEqual(actual, expected)
        self.assertEqual(failures[-1]['status'], 'cache-io-skip')
        self.assertEqual(failed.clock_marker, DAY+12345)


if __name__ == '__main__':
    unittest.main()
