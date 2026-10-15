"""Check that presence.cut_capture's windows live in the tree's space: cut ONE recording with the same code, cleaned
against its baseline's shape as the tree is, at the tree's own window starts, and compare band energies window by
window with the tree's. Run in a cell's environment (presence.py's inner does this for the real runs)."""
import json, os, sys
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)
from pipeline.constrained.pd_clean import force_cpu
force_cpu()
import pipeline.constrained.recordings as R
from pipeline.io.clean import baseline_shape, clean_arrays
from pipeline.io.windows import FS, NODES, WINDOW_S, load_node
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from presence import energies, data_dir
out = {}
for session, stem in (("01", "participant_PA5_walk"), ("B2", "participant_PA2_walk")):
    sd = data_dir(session)
    sc = json.load(open(os.path.join(sd, f"{stem}.gt.json")))
    bdir = os.path.join(ROOT, sc["baseline_capture"].rstrip("/"))
    nodes = {}
    for n in NODES:
        bamp, _t, _s, _e = load_node(os.path.join(bdir, f"{n}.bin"))
        amp, ts, start, _ = load_node(os.path.join(sd, f"{stem}_{n}.bin"))
        nodes[n] = clean_arrays(amp, ts, FS, baseline=baseline_shape(bamp), grid_origin=0.0, n_dropped_restart=start)
    rec = R.load_meta(session, stem)
    tree = np.load(os.path.join(R.ART_DIR, "gate_energy", f"session_{session}_{stem}.npy"))
    ns = int(round(WINDOW_S * FS))
    pick = np.linspace(0, len(rec.t0) - 1, 60).astype(int)
    X = np.zeros((len(pick), 3, ns, nodes[NODES[0]].amplitude.shape[1]), np.float16)
    for k, i in enumerate(pick):
        for j, n in enumerate(NODES):
            i0 = int(round((rec.t0[i] - nodes[n].grid[0]) * FS))
            X[k, j] = nodes[n].amplitude[i0:i0 + ns]
    mine = energies(X)
    r = mine / tree[pick]
    out[f"{session}/{stem}"] = {"n": int(len(pick)), "ratio_median": float(np.median(r)), "ratio_p5": float(np.percentile(r, 5)),
                                "ratio_p95": float(np.percentile(r, 95)), "max_abs_rel_diff": float(np.max(np.abs(r - 1)))}
    print(session, stem, out[f"{session}/{stem}"], flush=True)
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "validate_cut.json"), "w"), indent=1)
