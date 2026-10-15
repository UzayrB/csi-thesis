#!/bin/bash
# Identification engine, training lane (runs/identify/engine/PLAN.md section 3). One training at a time;
# ide_train waits on runs/identify/audit/queue/HOLD_GPU and on any tracking training before each one.
cd "$(dirname "$0")/../../../.." || exit 1
export OMP_NUM_THREADS=1 PYTHONPATH=.
for m in loso_B2 loso_B1 loso_A1 loso_A2 loso_A3 T2.5_toB2 T2.5_toB1 T3.5_toB2 T3.5_toB1 deploy_all5; do
  echo "$(date +%H:%M:%S) START $m"
  python3 -m pipeline.identify.ide_train "$m"
  echo "$(date +%H:%M:%S) END $m rc=$?"
done
echo "$(date +%H:%M:%S) lane_train finished"
