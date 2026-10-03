"""Retain the accepted delivery once, without replaying any account or test."""
from datetime import datetime, timezone
import gzip
from hashlib import sha256
import json
from pathlib import Path
import shutil

ART = Path('/workspace/btc-alpha-beta-improve/task-artifacts')
FIN = Path('/workspace/scratch/btc-alpha-beta-edge-20261003')
OUT = FIN / 'delivery-packet'
OUT.mkdir(exist_ok=False)
records, links = [], []

def retain(path, relative):
    if path.is_symlink():
        links.append({'original_path':str(path), 'target':str(path.readlink()),
                      'retained':False, 'reason':'Original remains untouched; inert evidence contains no executable symlink.'})
        return
    if not path.is_file() or path.suffix == '.pyc' or '__pycache__' in path.parts or '.git' in path.parts:
        return
    raw = path.read_bytes()
    compressed = len(raw) > 40_000_000 and path.suffix != '.gz'
    relative = relative + ('.retained.gz' if compressed else '')
    target = OUT / relative
    target.parent.mkdir(parents=True,exist_ok=True)
    retained = gzip.compress(raw, compresslevel=6, mtime=0) if compressed else raw
    with target.open('xb') as stream:
        stream.write(retained)
    records.append({'original_path':str(path), 'retained_path':relative,
                    'original_bytes':len(raw), 'original_sha256':sha256(raw).hexdigest(),
                    'retained_bytes':len(retained), 'retained_sha256':sha256(retained).hexdigest(),
                    'storage':'lossless-gzip' if compressed else 'byte-identical'})

def tree(root, relative, exclusions=()):
    for p in sorted(root.rglob('*')):
        rel=p.relative_to(root)
        if any(part in exclusions or part in ('__pycache__','.git') for part in rel.parts): continue
        retain(p, str(Path(relative)/rel))

tree(ART,'task-artifacts')
for name in ('unscaled','canonical-spot','financial-review','delivery-charts','forward'):
    tree(FIN/name,name)
tree(FIN/'assessment','assessment',('public-print-inputs-v1',))
for name in ('unscaled','risk','sensitivity','budgets','selected-budgets'):
    tree(FIN/'recovery1'/name,'recovery1/'+name)
for suffix in ('.zip','.zip.CHECKSUM'):
    path=FIN/'assessment/public-print-inputs-v1'/('BTCUSDT-aggTrades-2026-08-01'+suffix)
    retain(path,'input-retention/'+path.name)
retain(Path('/workspace/btc-alpha-beta-improve/starquant/data/usdcny_frankfurter.json'),
       'input-retention/usdcny_frankfurter.json')
retain(Path('/workspace/btc-alpha-beta-improve/coinquant/research/session_schedule.json'),
       'input-retention/session_schedule.json')

readme = '''# BTC edge delivery — 2026-10-03

Complete71 original accounts and5 separate canonical Spot accounts are independently reviewed. Spot adopts registered crowding-interaction for development; Coin retains incumbent. Original goals NOT_MET; native cases/account-days0, NOT_QUALIFIED, prospective alpha unproven. Historical Spot improvement is associated with missing-feature entry blocking; no actual triple-condition halving event was observed.

The repositories share the same immutable packet. Current result and operation: [result](../../research/edge-RESULT.md), [guide](../../research/edge-GUIDE.md). This directory is evidence, not a second progress ledger. Consult PROJECT_STATE.md for integration status.

- [Financial review](financial-review/financial-review.md)
- [Five canonical cases](financial-review/spot-canonical-five-financial-review.md)
- [Exact artifact index](financial-review/delivery-artifacts.json)
- [Final machine proof](assessment/independent-financial-review-proof.json)
- [Account metrics CSV](delivery-charts/account-metrics.csv)
- [Funded curves](delivery-charts/funded-performance.png), [SVG](delivery-charts/funded-performance.svg)
- [Alpha/beta/risk](delivery-charts/alpha-beta-and-risk.png), [SVG](delivery-charts/alpha-beta-and-risk.svg)
- [Forward initialization/bindings](forward/delivery-forward-receipt.json)
- [Every original/retained byte identity](MANIFEST.json)

## Retention and reproduction

MANIFEST maps each original absolute path to a retained path, byte counts and SHA256. `byte-identical` preserves the original bytes (including producer-created .json.gz); `lossless-gzip` is an explicit delivery storage derivative for very large original plain files. To restore such a file, decompress its retained bytes into a NEW file and require the decompressed bytes/length/SHA to equal original_bytes/original_sha256. Do not confuse retained compressed SHA with measured original raw SHA. Original workspace files remain untouched, including failures and zero-byte unsuccessful output.

The large final/preliminary reports and forward export may be losslessly stored; use manifest entries rather than infer names. The forward export is a reviewed, externally pinned trust anchor containing both project bridges and all embedded final/prior/proof evidence. Its original raw SHA, independent approval, actual init argv/exit and cold state are in forward/. It can be restored to a new file for the standalone reader. Initialization is cash/zero-events, not retrospective observations/native execution. Receipt paths in an existing ledger must resolve to their original bound raw bytes; restore the directory layout instead of rewriting sealed ledger paths. A newly initialized ledger has a genuinely new timestamp and is a separate observation record.

Original measured Spot74bd/f2d6, Coin37061/ba638, new canonicalSpot609606/b81f and later protected-byte-identical metadata commits remain different identities. All commits remain in normal Git history. Original/current full protected byte maps and integer Git archive modes are retained in task-artifacts and financial-review/final-binding. Historical reproduction requires the original executable Git checkout plus its exact source/config/spec/protocol/input identities; current default is not a replacement executable for older raws.

The packet contains registered command argv, actual source/input guards and real exit/reaping receipts, frozen inputs/profiles/source archives, complete success/raw/negative evidence, first storage-failure evidence and ONE approved serial recovery, failed/successful final-assessor paths, all independent scoped financial/review reports and original test failures. No failed raw is included as a successful account. Synthetic check artifacts are labeled by their original paths and must not become native/account-days evidence.

Public market data (roughly14GB) and the previous218MB packet are not duplicated. Original market/vault manifests, official ZIP/CHECKSUM input provenance and exact consumed hashes remain bound; original prior evidence remains in evidence/alpha-beta-next-20261002. Reproduction must obtain the exact official public data and recreate the recorded input layout where required. The extra2026-08-01 aggTrades ZIP/CHECKSUM used by the fixed-minus60s rolling loader is retained in input-retention with the correction and HTTP retrieval receipts; this was a verification-path correction, not new prices/source/account replay.

No original symlink is copied into inert evidence, because the source reader rejects repository symlinks. MANIFEST records skipped original symlink targets; originals remain preserved. No Git/native state/cache/lock cleanup, source rewrite, automatic reroll, private account, credentials, order, setting or transfer action was performed for retention.

One final whole-branch review and one full exact-head CI per project finish integration. Passed unchanged scoped checks and all71/5 calculations are reused; no optional/repeated/full research replay is run for packaging. CI completion does not qualify economic returns or native execution.
'''
(OUT/'README.md').write_text(readme)
records.append({'original_path':None,'retained_path':'README.md','original_bytes':(OUT/'README.md').stat().st_size,
                'original_sha256':sha256((OUT/'README.md').read_bytes()).hexdigest(),
                'retained_bytes':(OUT/'README.md').stat().st_size,
                'retained_sha256':sha256((OUT/'README.md').read_bytes()).hexdigest(),'storage':'delivery-prose'})
manifest={'format':'btc-edge-delivery-retention-v1','created_utc':datetime.now(timezone.utc).isoformat(),
          'files':records,'original_symlinks_preserved_not_copied':links,
          'exclusions':['temporary native state/cache/locks','public-print-inputs-v1 except extra bound official pair','Python/Git cache'],
          'prior_packet':'evidence/alpha-beta-next-20261002','new_financial_producers':0,'new_tests':0}
(OUT/'MANIFEST.json').write_text(json.dumps(manifest,indent=2,allow_nan=False)+'\n')
receipt={'packet':str(OUT),'files':len(records),'bytes':sum(r['retained_bytes'] for r in records),
         'manifest_sha256':sha256((OUT/'MANIFEST.json').read_bytes()).hexdigest(),
         'skipped_symlinks':len(links),'source_inputs_rewritten':False,'financial_replays':0}
with (FIN/'delivery-packet-retention-receipt.json').open('x') as stream:
    json.dump(receipt,stream,indent=2);stream.write('\n')
print(json.dumps(receipt))
