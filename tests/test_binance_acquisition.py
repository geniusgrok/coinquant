import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from research.acquire_binance import acquire


class AcquisitionEvidenceTests(unittest.TestCase):
    def test_native_hour_gap_stays_failed_but_original_is_preserved(self):
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w') as z:
            z.writestr('native.csv','0,10,11,9,10,1,3599999\n7200000,10,11,9,10,1,10799999\n')
        raw=stream.getvalue();checksum=(hashlib.sha256(raw).hexdigest()+'  native.zip\n').encode()
        relative='monthly/markPriceKlines/BTCUSDT/1h/BTCUSDT-1h-2021-07.zip'
        with tempfile.TemporaryDirectory() as temp, patch('research.acquire_binance.download',side_effect=[raw,checksum]):
            root=Path(temp);result=acquire(root,relative)
            self.assertEqual(result['status'],'unavailable')
            self.assertIn('hour gap',result['error'])
            self.assertEqual((root/relative).read_bytes(),raw)
            self.assertEqual(result['sha256'],hashlib.sha256(raw).hexdigest())
