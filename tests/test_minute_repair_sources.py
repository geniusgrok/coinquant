import csv
import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from research.bounded_execution_data import _mark_repair


class MinuteRepairSourceTests(unittest.TestCase):
    def test_monthly_repairs_from_multiple_months_are_combined(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            records = []
            expected = {}
            for month, timestamp in (('2021-01', 1611964800000), ('2021-02', 1612224000000)):
                archive_name = f'monthly-{month}.zip'
                member = f'BTCUSDT-markPriceKlines-1m-{month}.csv'
                output = io.BytesIO()
                rows = [[str(timestamp+minute*60000), '1', '2', '0.5', '1.5', '0',
                         str(timestamp+minute*60000+59999), '0', '0', '0', '0', '0']
                        for minute in range(60)]
                with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
                    content = io.StringIO()
                    csv.writer(content).writerows(rows)
                    archive.writestr(member, content.getvalue())
                raw = output.getvalue()
                sha = hashlib.sha256(raw).hexdigest()
                (root/archive_name).write_bytes(raw)
                (root/(archive_name+'.CHECKSUM')).write_text(f'{sha}  {archive_name}\n')
                records.append(dict(source=f'https://data.binance.vision/data/futures/um/monthly/markPriceKlines/BTCUSDT/1m/BTCUSDT-1m-{month}.zip',
                    archive_path=archive_name,sha256=sha,bytes=len(raw),required_rows=60,
                    required_hours_ms=[timestamp],complete_required_hour=True))
                expected.update({timestamp+minute*60000: row for minute,row in enumerate(rows)})
            (root/'RECEIPT.json').write_text(json.dumps(dict(records=records)))

            rows, identity = _mark_repair(root)

            self.assertEqual(rows, {timestamp: row for timestamp, row in expected.items()})
            self.assertEqual(len(identity['archives']), 2)
            self.assertEqual({record['sha256'] for record in identity['archives']},
                             {record['sha256'] for record in records})


if __name__ == '__main__':
    unittest.main()
