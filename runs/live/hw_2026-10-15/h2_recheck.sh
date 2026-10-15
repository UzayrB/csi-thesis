#!/bin/bash
# H2 re-check (15 Oct 2026, after Uzayr moved RX3 closer to the TX; RX2's cable kept): pause the H5 chain between
# streams (SIGSTOP on its bash only, so the stream in progress finishes untouched), run the check alone, resume.
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
H=runs/live/hw_2026-10-15; PY=/opt/anaconda3/bin/python3; export OMP_NUM_THREADS=1 PYTHONPATH=.
CHAIN=$1; STREAM=$2; L=$H/H2_recheck.log
kill -STOP $CHAIN; echo "[$(date '+%H:%M:%S')] H5 chain $CHAIN paused (SIGSTOP); waiting for stream PID $STREAM to end" > $L
echo "[$(date '+%H:%M:%S')] H5 chain paused for the H2 re-check (SIGSTOP $CHAIN, after the current stream)" >> $H/H5.log
while kill -0 $STREAM 2>/dev/null; do sleep 1; done
echo "[$(date '+%H:%M:%S')] stream ended; load $(sysctl -n vm.loadavg)" >> $L
$PY -m pipeline.io.identify_board >> $L 2>&1; rc=$?; echo "[$(date '+%H:%M:%S')] identify_board rc=$rc" >> $L
mkdir -p $H/H2_capture2
$PY -m pipeline.io.capture_logger --duration 180 --out $H/H2_capture2 --nodes "RX1=/dev/cu.usbserial-3,RX2=/dev/cu.usbserial-4,RX3=/dev/cu.usbserial-0001" --reset --interval 10 >> $L 2>&1; rc=$?
echo "[$(date '+%H:%M:%S')] capture rc=$rc; load $(sysctl -n vm.loadavg)" >> $L
kill -CONT $CHAIN; echo "[$(date '+%H:%M:%S')] H5 chain resumed (SIGCONT)" >> $L
echo "[$(date '+%H:%M:%S')] H5 chain resumed after the H2 re-check (SIGCONT $CHAIN)" >> $H/H5.log
echo "[$(date '+%H:%M:%S')] RECHECK DONE" >> $L
