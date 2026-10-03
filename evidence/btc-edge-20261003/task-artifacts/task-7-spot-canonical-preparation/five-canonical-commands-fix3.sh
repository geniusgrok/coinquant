# PREPARED ONLY. No financial execution occurred. Required source: 609606d9c0e0ad8d3c3038b329c9c4ab6d1b9629
set -eu
cd /workspace/btc-alpha-beta-canonical-prepare/spotquant
python3.13 -m research.adoption_spot --scenario base --features /workspace/btc-alpha-beta-improve/task-artifacts/edge-features-v1.json --out /workspace/scratch/btc-alpha-beta-edge-20261003/canonical-spot/spot-canonical-base.json
python3.13 -m research.adoption_spot --scenario fee150 --features /workspace/btc-alpha-beta-improve/task-artifacts/edge-features-v1.json --out /workspace/scratch/btc-alpha-beta-edge-20261003/canonical-spot/spot-canonical-fee150.json
python3.13 -m research.adoption_spot --scenario slip2 --features /workspace/btc-alpha-beta-improve/task-artifacts/edge-features-v1.json --out /workspace/scratch/btc-alpha-beta-edge-20261003/canonical-spot/spot-canonical-slip2.json
python3.13 -m research.adoption_spot --scenario outage --features /workspace/btc-alpha-beta-improve/task-artifacts/edge-features-v1.json --out /workspace/scratch/btc-alpha-beta-edge-20261003/canonical-spot/spot-canonical-outage.json
python3.13 -m research.adoption_spot --scenario base --features /workspace/btc-alpha-beta-improve/task-artifacts/edge-features-v1.json --out /workspace/scratch/btc-alpha-beta-edge-20261003/canonical-spot/spot-canonical-unity-risk-base.json --risk-calibration /workspace/scratch/btc-alpha-beta-edge-20261003/assessment/spot-calibration.json
