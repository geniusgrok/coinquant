"""Offline evidence checks; synthetic data and normal account locks only."""
from copy import deepcopy
import gzip
import json
from pathlib import Path
import tempfile
import unittest

import driver
from research import complete_perp
from test_compat import MINUTE, START, binding_for, session_fixture


class PathTraceTests(unittest.TestCase):
    def test_original_points_resume_boundary_and_tamper_rejection(self):
        with tempfile.TemporaryDirectory(prefix='coinquant-trace-compat-') as temporary:
            root=Path(temporary)
            first_before=dict(count=0,rolling_sha256='0'*64)
            first_path,stream,buffer=driver.open_path_trace(root,1)
            try:
                config,inputs,venue,report=session_fixture(self,root)
            finally:
                complete_perp.PATH_TRACE=None
                driver.finish_path_trace(first_path,stream,buffer)
            first=driver.path_trace_receipt(first_path,first_before,venue)
            self.assertTrue(first['verified'],first)
            self.assertEqual(first['first_sequence'],1)
            self.assertEqual(first['points'],venue._path_audit['count'])
            self.assertGreater(first['points'],1)
            first['segment_failed']=False

            report=dict(start_ms=START,**driver.plain(report))
            journal=root/'reports.jsonl'
            journal.write_text(json.dumps(report)+'\n')
            binding=binding_for(config,venue)
            last=driver.checkpoint(venue,config,binding,[report],journal,root)
            previous=dict(complete=False,can_resume=True,failure=None,binding=binding,
                last_checkpoint=last,session_count=1,path_trace=first,
                reports=dict(path=str(journal),sha256=driver.sha(journal),count=1))
            # A restore constructor's provisional point must never be retained.
            resumed=inputs.venue(config)
            driver.restore(previous,{},binding,config,[START],journal,resumed)
            before={key:resumed._path_audit[key] for key in ('count','rolling_sha256')}
            second_path,stream,buffer=driver.open_path_trace(root,2)
            try:
                resumed.advance_unattended(venue.now_ms+2*MINUTE)
            finally:
                complete_perp.PATH_TRACE=None
                driver.finish_path_trace(second_path,stream,buffer)
            second=driver.path_trace_receipt(second_path,before,resumed)
            self.assertTrue(second['verified'],second)
            self.assertEqual(second['first_sequence'],first['last_sequence']+1)
            self.assertEqual(second['rolling_before'],first['rolling_after'])
            venue.advance_unattended(resumed.now_ms)
            self.assertEqual(resumed._path_audit,venue._path_audit)
            self.assertEqual((resumed.wallet,resumed.q,resumed.fees),
                             (venue.wallet,venue.q,venue.fees))
            with self.assertRaises(FileExistsError):
                driver.open_path_trace(root,2)

            # A modified evidence file cannot validate or authorize continuation.
            with gzip.open(first_path,'rt') as source:lines=source.readlines()
            point=json.loads(lines[0]);point[3]='1'
            lines[0]=json.dumps(point)+'\n'
            with gzip.open(first_path,'wt') as target:target.writelines(lines)
            self.assertFalse(driver.path_trace_receipt(first_path,first_before,venue)['verified'])
            with self.assertRaisesRegex(ValueError,'path trace prefix changed'):
                driver.restore(deepcopy(previous),{},binding,config,[START],journal,inputs.venue(config))


if __name__=='__main__':unittest.main(verbosity=2)
