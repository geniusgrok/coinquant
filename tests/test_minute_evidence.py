import csv
from decimal import Decimal as D
import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from coinquant.research import timestamp
from research.minute_evidence import load, steps

class MinuteEvidenceTests(unittest.TestCase):
    def test_exact_native_reconstruction_and_rejection(self):
        day='2023-06-05';start=timestamp(day+'T00:00:00Z')
        hourly={k:{} for k in ('klines','markPriceKlines')}
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for kind in hourly:
                text=io.StringIO();writer=csv.writer(text)
                for t in range(start,start+86400000,60000):
                    writer.writerow([t,100,110,90,101,0,t+59999])
                p=root/f'daily/{kind}/BTCUSDT/1m/BTCUSDT-1m-{day}.zip'
                p.parent.mkdir(parents=True)
                with zipfile.ZipFile(p,'w') as z:z.writestr('data.csv',text.getvalue())
                Path(str(p)+'.CHECKSUM').write_text(hashlib.sha256(p.read_bytes()).hexdigest()+' data.zip')
                for t in range(start,start+86400000,3600000):
                    hourly[kind][t]=[t,'100','110','90','101']
            with patch('research.minute_evidence.DATES',(day,)):
                minutes,identity=load(root,hourly)
                self.assertEqual(len(identity),2)
                bars=steps(start,(D(100),)*4,(D(100),)*4,minutes)
                self.assertEqual(len(bars),60)
                self.assertEqual(bars[-1][0],start+59*60000)
                hourly['klines'][start][2]='111'
                with self.assertRaises(ValueError):load(root,hourly)
