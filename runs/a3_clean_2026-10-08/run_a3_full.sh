#!/bin/zsh
# The ONE A3 decode with the full A3-clean configuration: A3's SEVENTH look (POA_DOT.md section 5, step 6).
# Started by hand after A3_CLEAN_CONFIG_FULL is committed; the run's caffeinate (dot/logs/caffeinate.pid) is held through
# it and released at the end; the Now line goes to QUIET with no word that would hold the identification watcher.
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code || exit 1
PY=/opt/anaconda3/bin/python3
D=runs/a3_clean_2026-10-08
L=$D/dot/logs
log() { echo "[$(date '+%H:%M:%S')] $*" >> $L/run_a3_full.log; }
MS() { $PY $D/machine_state.py "$@"; }
CAF=$(cat $L/caffeinate.pid 2>/dev/null)
MS is-mine || { echo "REFUSED: the Now line is not this chat's BUSY"; exit 1; }
[ -f $D/A3_CLEAN_CONFIG_FULL.json.sha256 ] || { echo "REFUSED: no full configuration"; exit 1; }
MS update "A3-clean dot side (Uzayr's go). Now: the five stages are done and the full configuration is committed; the one A3 decode (A3's seventh look, 6 niced CPU processes), its score and the hash checks. ETA for QUIET about 16:00. One caffeinate held."
$PY $D/mem_guard.py $$ dot &!
mkdir -p $D/dot/a3
$PY $D/a3_full.py hashes --out dot/a3/HASHES_before.json >> $L/run_a3_full.log 2>&1 || { log "hashes before failed"; exit 1; }
$PY -m pipeline.live.model_sets check --model final > $D/dot/a3/model_set_check_before.json
log "start the six replays"
for s in $(cat $D/a3_lock/logs/stems.txt); do
  ( $PY $D/a3_full.py replay --stem $s --look 7 >> $L/a3_$s.log 2>&1; echo "[$(date '+%H:%M:%S')] $s EXIT $?" >> $L/run_a3_full.log ) &
done
wait
grep -q "EXIT [1-9]" $L/run_a3_full.log && { log "a replay failed: see the logs"; exit 1; }
$PY $D/a3_full.py score --look 7 > $D/dot/a3/score.log 2>&1; rc=$?
log "score exit $rc"
$PY $D/a3_full.py hashes --out dot/a3/HASHES_after.json >> $L/run_a3_full.log 2>&1
$PY -m pipeline.live.model_sets check --model final > $D/dot/a3/model_set_check_after.json
$PY -c 'import json,sys; a=json.load(open(sys.argv[1]))["files"]; b=json.load(open(sys.argv[2]))["files"]; print("shipped files", len(a), "identical before and after:", a == b, [k for k in set(a) | set(b) if a.get(k) != b.get(k)])' $D/dot/a3/HASHES_before.json $D/dot/a3/HASHES_after.json >> $L/run_a3_full.log
log "done"
