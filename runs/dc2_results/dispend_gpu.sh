#!/bin/zsh
# The final display head (DISP_END) on the GPU, beside the CPU chain (Uzayr, 29 Sep: the GPU when free,
# Identification first). Trains on A1+A2+B1 only, then infers A3 and B2. Started only after Identification's go.
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
export OMP_NUM_THREADS=1
for a in "train --cell fin_A3" "infer --cell fin_A3" "infer --cell fin_B2"; do
  echo "[$(date '+%H:%M:%S')] START pd_dispend $a (gpu)"
  caffeinate -dimsu python3 -m pipeline.constrained.pd_dispend ${=a} --device gpu || { echo "[$(date '+%H:%M:%S')] DISPEND GPU FAILED at $a"; exit 1; }
  echo "[$(date '+%H:%M:%S')] DONE pd_dispend $a"
done
echo "DISPEND GPU DONE $(date '+%F %T')"
