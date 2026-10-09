"""Focused storage-boundary regression; no strategy, account or market calls."""
import gzip
from pathlib import Path
import tempfile
import unittest

import driver
from research import complete_perp


class TraceStorageTests(unittest.TestCase):
    def test_private_stream_round_trip_in_memory_and_after_spill(self):
        payload = ''.join(f'[{i},"a durable original point"]\n' for i in range(10000))
        with tempfile.TemporaryDirectory() as directory:
            for segment, spill in enumerate((False, True), 1):
                path, stream, buffer = driver.open_path_trace(Path(directory), segment)
                self.assertFalse(path.exists())
                stream.write(payload[:50000])
                if spill:
                    buffer.rollover()
                stream.write(payload[50000:])
                complete_perp.PATH_TRACE = None
                driver.finish_path_trace(path, stream, buffer)
                self.assertEqual(gzip.decompress(path.read_bytes()).decode(), payload)
                self.assertFalse(path.with_name(path.name + '.publishing').exists())
                self.assertTrue(buffer.closed)

    def test_named_open_file_replacement_reproduces_failed_readback(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'old.jsonl.gz'
            with gzip.open(path, 'wt') as stream:
                stream.write('first\n' * 10000)
                stream.flush()
                prefix = path.read_bytes()
                replacement = path.with_suffix('.replacement')
                replacement.write_bytes(prefix[:-1])
                replacement.replace(path)
                stream.write('last\n' * 10000)
            with self.assertRaises(EOFError):
                gzip.decompress(path.read_bytes())

    def test_conflicting_final_path_is_preserved_and_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path, stream, buffer = driver.open_path_trace(Path(directory), 1)
            stream.write('original points\n')
            path.write_bytes(b'concurrent path')
            complete_perp.PATH_TRACE = None
            try:
                with self.assertRaises(FileExistsError):
                    driver.finish_path_trace(path, stream, buffer)
                self.assertEqual(path.read_bytes(), b'concurrent path')
            finally:
                buffer.close()


if __name__ == '__main__':
    unittest.main(verbosity=2)
