#!/bin/bash
# Identification engine, replay lane (PLAN section 4): each session replayed through the engine as soon as its
# fold model exists; pauses while runs/identify/audit/queue/HOLD_GPU exists; then the evaluation and the tests.
cd "$(dirname "$0")/../../../.." || exit 1
export OMP_NUM_THREADS=1 PYTHONPATH=.
M=runs/identify/engine/models
hold() { while [ -e runs/identify/audit/queue/HOLD_GPU ]; do sleep 30; done; }
run() {  # session model T
  while [ ! -e "$M/$2/meta_feat_cnn.json" ]; do sleep 30; done
  hold
  if [ -e "runs/identify/engine/replays/$2_$1_T$3.json" ]; then echo "$(date +%H:%M:%S) SKIP $2 $1 (done)"; return; fi
  echo "$(date +%H:%M:%S) START replay $1 $2 T$3"
  python3 -m pipeline.identify.ide_replay --session "$1" --model "$2" --T "$3" --device mps
  echo "$(date +%H:%M:%S) END replay $1 $2 rc=$?"
}
run B2 loso_B2 3.0; run B1 loso_B1 3.0; run A1 loso_A1 3.0; run A2 loso_A2 3.0; run A3 loso_A3 3.0
run B2 T2.5_toB2 2.5; run B1 T2.5_toB1 2.5; run B2 T3.5_toB2 3.5; run B1 T3.5_toB1 3.5
hold
echo "$(date +%H:%M:%S) START eval"
python3 -m pipeline.identify.ide_eval --device mps
echo "$(date +%H:%M:%S) END eval rc=$?"
while [ ! -e "$M/deploy_all5/manifest.json" ]; do sleep 30; done
hold
echo "$(date +%H:%M:%S) START tests"
python3 -m pytest -q tests/test_ide_engine.py
echo "$(date +%H:%M:%S) END tests rc=$?"
echo "$(date +%H:%M:%S) lane_replay finished"
