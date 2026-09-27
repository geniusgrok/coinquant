import csv
from datetime import date, datetime, timedelta, timezone
from io import BytesIO, StringIO
from unittest import TestCase
from unittest.mock import patch
from zipfile import ZipFile

from coinquant.dfii10 import Source, eligible
from coinquant.types import Unknown


class DFII10Tests(TestCase):
    def test_official_sparse_vintages_are_reconstructed_only_as_of_call(self):
        dates=[date(2026,3,1)+timedelta(days=i) for i in range(26)]
        html=('<select id="form_selected_vintage_dates">'+''.join(
            f'<option value="{v}">{v}</option>' for v in dates)+
            '<option value="2026-04-01">future</option></select>').encode()
        out=StringIO();writer=csv.writer(out)
        writer.writerow(['observation_date']+[f'DFII10_{v:%Y%m%d}' for v in dates])
        for i,v in enumerate(dates):
            values=['']*len(dates);values[i]='1.0' if i>=20 else '1.3'
            writer.writerow([v,*values])
        archive=BytesIO()
        with ZipFile(archive,'w') as z:z.writestr('DFII10.csv',out.getvalue())
        requests=[]
        class Opener:
            def open(self,request,timeout):
                requests.append(request)
                return BytesIO(html if request.data is None else archive.getvalue())
        now=int(datetime(2026,3,31,tzinfo=timezone.utc).timestamp()*1000)
        with patch('coinquant.dfii10.build_opener',return_value=Opener()):
            row=Source().snapshot(now)
        self.assertEqual(len(requests),2)
        self.assertNotIn(b'2026-04-01',requests[1].data)
        self.assertEqual(row['latest_observation_date'],'2026-03-26')
        self.assertEqual(row['prior20_observation_date'],'2026-03-06')
        self.assertTrue(eligible(row,now))
        with self.assertRaises(Unknown):eligible(row,row['latest_value_available_ms'])
