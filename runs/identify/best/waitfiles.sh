#!/bin/zsh
# waitfiles.sh DONE FAILED -- CMD...: wait until DONE exists, then exec CMD (same PID); if FAILED exists, end 0 without
# running CMD (the greedy step drops a configuration whose file is missing, and logs it).
done_f=$1 fail_f=$2
shift 3
while [ ! -e $done_f ]; do
  if [ -e $fail_f ]; then echo "[$(date '+%H:%M:%S')] $fail_f exists: not run: $*"; exit 0; fi
  sleep 30
done
exec "$@"
