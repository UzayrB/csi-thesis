"""Guard test for tracking's announcements (15 Oct 2026): the 13:26 board tracking recording fed through the worktree's
rig.TrackingConsumer (no screen), records in t_mono order, ONE record per loop and a tick after it at a wall clock that
follows the data, with a 3.6 s stall at +60 s after the first press (the arrivals queue, then drain, as on the boards).
Optional drop "RX3:100:125": that receiver's frames in the interval removed. Prints every TRACKING message with its
time, the consumer's outages, the walks overlapping one, and each walk's committed line.

    python3 track_guard_consumer.py WT REC BASE [DROP]
"""
import glob
import importlib.util
import io
import json
import os
import sys
import contextlib

WT, SRC, BASE = sys.argv[1:4]
DROP = sys.argv[4] if len(sys.argv) > 4 else None
REPO = "/Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code"
sys.path.insert(0, REPO)
from pipeline.constrained.pd_clean import force_cpu  # noqa: E402
force_cpu()
import numpy as np  # noqa: E402
from pipeline.io.capture_logger import read_capture_file  # noqa: E402
from pipeline.io.ground_truth import KeyEvent  # noqa: E402
from pipeline.io.windows import session_baseline  # noqa: E402
from pipeline.live.final_model import MODEL_CELLS, FinalTrackingSession, _components, end_head_for, final_variant  # noqa: E402
from pipeline.live.identify_recorded import record_of  # noqa: E402

spec = importlib.util.spec_from_file_location("wt_rig", os.path.join(WT, "pipeline/live/rig.py"))
wt_rig = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wt_rig)

stem = os.path.basename(glob.glob(os.path.join(SRC, "*.keys.json"))[0])[:-len(".keys.json")]
keys = sorted(json.load(open(os.path.join(SRC, f"{stem}.keys.json")))["keys"], key=lambda k: k["t_mono"])
t1 = min(float(k["t_mono"]) for k in keys if k["key"] == " ")
fr = {}
for f in sorted(glob.glob(os.path.join(SRC, f"{stem}_RX*.bin"))):
    L = f[:-4].rsplit("_", 1)[1]
    fr[L] = read_capture_file(f)[1]
dropped = 0
if DROP:
    L_, a_, b_ = DROP.split(":")
    tm = np.asarray(fr[L_]["t_mono"], float)
    keep = (tm < t1 + float(a_)) | (tm > t1 + float(b_))
    dropped = int((~keep).sum())
    fr[L_] = fr[L_][keep]

PC, c, pieces, pool, terms, G0 = _components(MODEL_CELLS["final"]["03"], final_variant())
st, _cfg, _ne, _tr, _kind, alpha = pieces
s = FinalTrackingSession(pool=pool, terms=terms, G0=G0, session="live", stem=stem, train=c["train"], test=(c["test"],),
                         reader_tag=c["reader_tag"], pieces=pieces, baseline=session_baseline(BASE),
                         end_head=end_head_for(st, alpha), mode="semi")
con = wt_rig.TrackingConsumer(s, None)

recs = [(float(f["t_mono"]), L, j) for L in fr for j, f in enumerate(fr[L])]
recs.sort()
STALL_AT, STALL = t1 + 60.0, 3.6
msgs, err, stalled = [], None, False
buf = io.StringIO()
q, ri, wall = [], 0, recs[0][0]
import collections  # noqa: E402
q = collections.deque()
try:
    with contextlib.redirect_stdout(buf):
        while ri < len(recs) or q:
            while ri < len(recs) and recs[ri][0] <= wall:
                q.append(recs[ri]); ri += 1
            while keys and keys[0]["t_mono"] <= wall:
                k = keys.pop(0)
                con.keys.put(KeyEvent(k["key"], float(k["t_mono"]), float(k["t_host"])))
            if q:
                t, L, j = q.popleft()
                con.handle(record_of(L, fr[L][j]))
            before = buf.tell()
            con.tick(wall)
            out = buf.getvalue()[before:]
            for ln in out.splitlines():
                if ln.startswith("TRACKING:"):
                    msgs.append({"wall_s": round(wall - t1, 2), "msg": ln})
            if con.stop.is_set():
                break
            if not stalled and wall >= STALL_AT:
                wall += STALL; stalled = True
            elif q:
                wall += 0.0005
            elif ri < len(recs):
                wall = max(wall, recs[ri][0])
        for k in keys:
            con.keys.put(KeyEvent(k["key"], float(k["t_mono"]), float(k["t_host"])))
        con.tick(wall)
        s.close()
except Exception:  # noqa: BLE001
    import traceback
    err = traceback.format_exc()
outages = [{"node": o["node"], "from_s": round(o["from"] - t1, 2), "to_s": None if o["to"] is None else round(o["to"] - t1, 2)}
           for o in con.outages]
over = sorted(int(pid) for pid, p in s.passes.items() for o in con.outages
              if p["press"] - 1.0 <= (o["to"] or np.inf) and p["press"] + 10.0 >= o["from"])
com = {int(d["pass_id"]): d["final_line"] for d in s.decisions}
live = {}
for ln in open(os.path.join(SRC, f"{stem}.log.jsonl")):
    r = json.loads(ln)
    if r.get("kind") == "committed":
        live[int(r["pid"])] = r["line"]
diff = sorted(p for p in set(com) | set(live) if com.get(p) != live.get(p))
print(json.dumps({"drop": DROP, "dropped": dropped, "stall_at_s": 60.0, "stall_s": STALL, "error": err.splitlines()[-1] if err else None,
                  "messages": msgs, "outages": outages, "walks_overlapping_an_outage": over, "passes": len(s.passes),
                  "committed_differs_from_live_run": {p: {"here": com.get(p), "live": live.get(p)} for p in diff},
                  "committed_equal": f"{len(set(com) | set(live)) - len(diff)} of {len(set(com) | set(live))}"}, indent=1, default=str))
if err:
    print(err)
