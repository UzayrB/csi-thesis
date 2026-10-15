"""Re-cut B1's 0.5 s press-aligned window arrays (deleted 1 October) into a scratch folder with the shipped cutter
(`y4_pressalign.cut_one`, as `dc2_run.do_cut` calls it). The driver restores them only if every meta.json is
byte-identical to the surviving one."""
import json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, REPO)
import pipeline.io.windows as W
from pipeline.constrained.y4_pressalign import cut_one
# the DC2 tree's own data view (links to data/), so rx_files records the same path as the original cut
sdir = os.path.join("runs", "constrained", "dc2_room_B_s0.5_pressalign", "by_session", "B1", "data", "room_B", "session_B1")
out = os.path.join(HERE, "b1_recut_s0.5_pressalign", "room_B", "session_B1")
os.makedirs(out, exist_ok=True)
cache, rows = {}, []
for stem in W.recordings_in(sdir):
    bdir = W.baseline_dir_for(sdir, stem)
    if bdir not in cache:
        cache[bdir] = W.session_baseline(bdir)
    t0 = time.time()
    r = cut_one(sdir, stem, cache[bdir], out)
    rows.append(r)
    print(f"[{time.strftime('%H:%M:%S')}] {stem}: {r['n']} windows, lo at press - 1 s on "
          f"{r['passes_with_lo_at_press_minus_1s']} of {r['n_passes_sidecar']}, {time.time() - t0:.0f} s", flush=True)
json.dump(rows, open(os.path.join(HERE, "logs", "b1_cut_05.json"), "w"), indent=1)
