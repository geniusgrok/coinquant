# PREPARED ONLY. No execution occurred. Required source: 9797cfd9110286c5a9c10c00bb0a5dfd798d47c4
set -eu
cd /workspace/btc-alpha-beta-canonical-prepare/spotquant
python3.13 -m research.adoption_spot --scenario base --features /workspace/btc-alpha-beta-improve/task-artifacts/edge-features-v1.json --out /workspace/scratch/btc-alpha-beta-edge-20261003/canonical-spot/spot-canonical-base.json
python3.13 -m research.adoption_spot --scenario fee150 --features /workspace/btc-alpha-beta-improve/task-artifacts/edge-features-v1.json --out /workspace/scratch/btc-alpha-beta-edge-20261003/canonical-spot/spot-canonical-fee150.json
python3.13 -m research.adoption_spot --scenario slip2 --features /workspace/btc-alpha-beta-improve/task-artifacts/edge-features-v1.json --out /workspace/scratch/btc-alpha-beta-edge-20261003/canonical-spot/spot-canonical-slip2.json
python3.13 -m research.adoption_spot --scenario outage --features /workspace/btc-alpha-beta-improve/task-artifacts/edge-features-v1.json --out /workspace/scratch/btc-alpha-beta-edge-20261003/canonical-spot/spot-canonical-outage.json
python3.13 -m research.adoption_spot --scenario base --features /workspace/btc-alpha-beta-improve/task-artifacts/edge-features-v1.json --out /workspace/scratch/btc-alpha-beta-edge-20261003/canonical-spot/spot-canonical-unity-risk-base.json --risk-calibration /workspace/scratch/btc-alpha-beta-edge-20261003/assessment/spot-calibration.json
