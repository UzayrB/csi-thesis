"""idx_live. Identification development (the operator's direction of 2026-09-28): the chosen model run
causally, pass by pass, on a held-out session, with measured latency.

For the held-out session, the model the inner validation chose for that fold (from a selector result,
`idx_sel`) is trained on the other four sessions. The held-out session is then replayed in recording
order. At each pass's end press, only the frames that had arrived by end press + `WAIT_S` (21 s, the wait
that completes the clock map's bins around the pass; `pipeline.live.identify`) are used:
- the clock map is rebuilt from them (`pipeline.live.identify.link_from_frames`);
- the pass's 150 Hz grid, gait features and conditioned maps are computed;
- the pass is classified with the session's earlier recordings as its only calibration.

Reported per pass: whether the live features and maps equal the OFFLINE bank's (so the offline figures are
the live ones), the extraction and model times, and the decision latency (the wait plus compute); per
session, how many decisions equal the offline fold's. (Before 2026-09-29 08:25 the equality was checked
against the bank after the live substitution under --predict-live, which always passed.)

    PYTHONPATH=. python3 -m pipeline.identify.idx_live --session B2 --selection sel_batch2
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

from pipeline.identify import idmax_common as IC
from pipeline.identify import idv2_core as C
from pipeline.identify import idx_bank as B
from pipeline.identify import idx_dev as X
from pipeline.identify import idx_loso as L
from pipeline.identify import idx_sel as S

OUT = os.path.join("runs", "identify", "dev", "live")


def stems_for(session: str) -> list:
    return [r for r in B.recordings() if r["session"] == session]


def live_pass(frames: dict, t0: float, t1: float, wait_s: float) -> tuple:
    """(A, R, maps, features, extraction seconds) from the frames that had arrived by t1 + wait_s."""
    from pipeline.identify import id19_featbank as FB
    from pipeline.identify.id19_bank import _interp_cols
    from pipeline.identify.id19_featbank import SC
    from pipeline.live.identify import link_from_frames
    c0 = time.perf_counter()
    links = []
    for L_ in ("RX1", "RX2", "RX3"):
        fr = frames[L_]
        links.append(link_from_frames(fr[np.asarray(fr["t_mono"], float) <= t1 + wait_s]))
    grid = np.arange(t0, t1, 1.0 / C.HP["fs"])
    A = np.asarray([_interp_cols(grid, t, a) for t, a, _r, _c in links], np.float64)[:, :, SC]
    R = np.asarray([_interp_cols(grid, t, r) for t, _a, r, _c in links], np.float64)
    maps = np.stack([C.conditioned_map(A[li]) for li in range(3)]).astype(np.float32)
    feats = FB.pass_features(A, R)
    return maps, feats, time.perf_counter() - c0


def run(session: str, selection: str, seeds=(0, 1, 2), steps=3000, wait_s: float = 21.0, device="cpu",
        predict_live: bool = False) -> dict:
    """predict_live: classify from the LIVE-extracted features and maps (substituted for the test passes
    in a copy of the bank), as needed when a shorter wait makes them differ from the bank's."""
    from pipeline.io.capture_logger import read_capture_file
    from pipeline.live.identify import nan_equal
    import torch
    torch.set_num_threads(min(4, int(os.environ.get("OMP_NUM_THREADS", "4"))))
    bank = L.load()
    a = bank["a"]
    sel = json.load(open(os.path.join(L.OUT, f"{selection}.json")))
    choice = sel["folds"][session]["choice"]
    tr, te = np.flatnonzero(a["session"] != session), np.flatnonzero(a["session"] == session)
    orig_X, orig_maps = bank["X"].copy(), list(bank["maps"])   # the offline bank, before any live substitution
    live_cache = {}
    if predict_live:
        for rec in stems_for(session):
            frames = {L_: read_capture_file(f"{rec['stem']}_{L_}.bin")[1] for L_ in ("RX1", "RX2", "RX3")}
            gt = json.load(open(rec["stem"] + ".gt.json", encoding="utf-8"))
            for q in gt["passes"]:
                hit = np.flatnonzero((a["session"] == session) & (np.abs(a["t_start"] - float(q["t_start"])) < 1e-6))
                maps_l, feats_l, _e = live_pass(frames, float(q["t_start"]), float(q["t_end"]), wait_s)
                live_cache[int(hit[0])] = (maps_l, feats_l)
        bank = dict(bank)
        bank["X"] = bank["X"].copy()
        bank["maps"] = list(bank["maps"])
        bank["W"] = list(bank["W"])
        for i, (maps_l, feats_l) in live_cache.items():
            bank["X"][i] = [feats_l.get(n, np.nan) if feats_l.get(n) is not None else np.nan for n in bank["names"]]
            bank["maps"][i] = maps_l
            bank["W"][i] = C.windows(maps_l)
        L.register_variant("dev", bank["X"], bank["names"])
    t0 = time.time()
    if choice == "all":                                        # the equal-weight product of every component (idx_all_eval)
        comp = S.components(bank, tr, te, tuple(seeds), steps, need=set(S.FEATURES) | {"cnn", "cnn_prior", "cnn_perlink_prior"},
                            device=device)
        Lte = C.normalise_logp(sum(comp.values()))
    else:
        Lte = S.with_fusions(S.components(bank, tr, te, tuple(seeds), steps, need=S.needs(choice), device=device))[choice]
    train_s = time.time() - t0
    names = bank["names"]
    # inference timing: a 300-tree RF on the gait features and the CNN on the pass's windows, per seed.
    # Inference cost does not depend on the trained weights, so these timing models are fitted on the
    # training side only and never classify anything.
    from pipeline.identify import idmax_eval as E
    cols = L.columns("U_all_gait")
    Xtr = np.nan_to_num(bank["X"][tr][:, cols])
    rf_timer = E.make_model("rf").fit(Xtr, a["anon"][tr])
    # one 3-link net per seed, or three 1-link nets per seed when the choice uses the per-link CNN
    nets = [C.make_net(1 if "perlink" in choice else 3, 6).eval() for _ in seeds for _k in range(3 if "perlink" in choice else 1)]
    nets = nets if "cnn" in choice else []                    # a feature-only choice runs no CNN
    if choice == "all":                                        # the 3-link CNN (plain and AdaBN) and the three 1-link CNNs
        nets = [C.make_net(3, 6).eval() for _ in seeds] * 2 + [C.make_net(1, 6).eval() for _ in seeds for _k in range(3)]
    rows = []
    pos = {int(i): k for k, i in enumerate(te)}
    for rec in stems_for(session):
        frames = {L_: read_capture_file(f"{rec['stem']}_{L_}.bin")[1] for L_ in ("RX1", "RX2", "RX3")}
        gt = json.load(open(rec["stem"] + ".gt.json", encoding="utf-8"))
        for q in sorted(gt["passes"], key=lambda z: z["t_start"]):
            hit = np.flatnonzero((a["session"] == session) & (np.abs(a["t_start"] - float(q["t_start"])) < 1e-6))
            assert len(hit) == 1, (session, q["t_start"], len(hit))   # exact: np.isclose allowed about 8 s here
            i = int(hit[0])
            maps, feats, ext_s = live_pass(frames, float(q["t_start"]), float(q["t_end"]), wait_s)
            fv = np.array([feats.get(n, np.nan) if feats.get(n) is not None else np.nan for n in names], float)
            bank_fv = orig_X[i]                                   # compared with the OFFLINE bank, never the substituted copy
            feats_equal = bool(np.allclose(np.nan_to_num(fv, nan=-9e9), np.nan_to_num(bank_fv, nan=-9e9), rtol=1e-4, atol=1e-5))
            maps_equal = bool(maps.shape == orig_maps[i].shape and np.allclose(maps, orig_maps[i], atol=1e-4))
            ok_c = np.isfinite(fv[cols]) & np.isfinite(bank_fv[cols])
            rel = np.abs(fv[cols][ok_c] - bank_fv[cols][ok_c]) / (np.abs(bank_fv[cols][ok_c]) + 1e-12)
            gait_cols_equal = float(np.mean(rel <= 1e-4)) if ok_c.any() else float("nan")
            m0 = time.perf_counter()
            for _r in range(4 if choice == "all" else 1):         # "all" runs three RFs and extra trees (LDA is negligible)
                rf_timer.predict_proba(np.nan_to_num(fv[cols])[None, :])
            w = C.windows(maps)
            with torch.no_grad():
                xw = torch.tensor(w, dtype=torch.float32)
                dw = torch.nn.functional.one_hot(torch.full((len(w),), int(q["path_name"].endswith("_rev"))), 2).float()
                for net in nets:
                    c_in = net.f[0].in_channels
                    torch.log_softmax(net(xw[:, :c_in], dw), 1)
            model_s = time.perf_counter() - m0
            pred = L.CLASSES[int(Lte[pos[i]].argmax())]           # the chosen model's decision for this pass
            rows.append({"i": i, "kind": rec["kind"], "block": rec["block"], "features_equal_bank": feats_equal,
                         "maps_equal_bank": maps_equal, "gait_cols_equal_frac": round(gait_cols_equal, 4), "extract_s": round(ext_s, 3), "model_s": round(model_s, 5),
                         "decision_latency_s": round(wait_s + ext_s + model_s, 2), "pred": pred})
    order = np.array([r["i"] for r in rows])
    truth = IC.SealedLabels(a["anon"][order], f"live|{session}").reveal(np.array([r["pred"] for r in rows]))
    ok = np.array([r["pred"] for r in rows]) == truth
    off = sel.get("preds", {}).get(session)                    # the offline decisions of the same fold
    offline = dict(zip(off["te"], off["pred"])) if off else {}
    same = [r["pred"] == offline[r["i"]] for r in rows if r["i"] in offline]
    ext = np.array([r["extract_s"] for r in rows])
    doc = {"built": time.strftime("%Y-%m-%dT%H:%M:%S"), "session": session, "choice": choice, "train_s": round(train_s, 1),
           "wait_s": wait_s, "predict_live": predict_live, "n_passes": len(rows),
           "features_equal_bank": int(sum(r["features_equal_bank"] for r in rows)),
           "maps_equal_bank": int(sum(r["maps_equal_bank"] for r in rows)),
           "gait_cols_equal_frac_median": round(float(np.median([r["gait_cols_equal_frac"] for r in rows])), 4),
           "decisions_equal_offline": f"{int(sum(same))}/{len(same)}" if same else None,
           "extract_s_median": round(float(np.median(ext)), 3), "extract_s_p95": round(float(np.percentile(ext, 95)), 3),
           "decision_latency_s_median": round(float(np.median([r["decision_latency_s"] for r in rows])), 2),
           "model_s_median": round(float(np.median([r["model_s"] for r in rows])), 4),
           "acc_pct_all": round(100 * float(ok.mean()), 2), "truth_revealed": len(truth) == len(rows), "passes": rows}
    txt = json.dumps(doc, indent=1, default=str)
    assert IC.no_names(txt)
    os.makedirs(OUT, exist_ok=True)
    suffix = f"_wait{wait_s:g}" + ("_live" if predict_live else "")
    open(os.path.join(OUT, f"live_{session}_{selection}{suffix if predict_live or wait_s != 21.0 else ''}.json"), "w").write(txt)
    print(json.dumps({k: v for k, v in doc.items() if k != "passes"}, indent=1))
    return doc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--session", required=True)
    ap.add_argument("--selection", default="sel_batch2")
    ap.add_argument("--steps", type=int, default=3000)
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    ap.add_argument("--wait", type=float, default=21.0)
    ap.add_argument("--predict-live", action="store_true")
    ap.add_argument("--device", default="cpu", choices=("cpu", "mps"))
    ap.add_argument("--wide", action="store_true", help="the selection used the --wide candidates")
    ap.add_argument("--perlink", action="store_true", help="the selection used the per-link CNN")
    a = ap.parse_args(argv)
    S.PERLINK = a.perlink
    if a.wide:
        S.widen()
    run(a.session, a.selection, tuple(a.seeds), a.steps, a.wait, device=a.device, predict_live=a.predict_live)
    return 0


if __name__ == "__main__":
    sys.exit(main())
