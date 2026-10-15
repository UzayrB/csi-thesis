"""Step 3 of option (c) (Uzayr's go, 11 Oct; agreed with the Mastermind 12:51): B2 through the live app on cpu at full speed,
untimed, through the real serial parser (iv5_rig.FakeSerialSource), loso_B2_v5, room B, every decision saved at full
precision, the closing-poll decisions marked. Run once with the code before option (c) (f80266b7's pipeline/, from a
`git archive`, the repository's other folders linked) and once with the code after it; `compare` then requires the two
bit-identical on every decision, and the after run against loso_B2_v5's replay: argmax on all, the ensemble within step
7's 8.1e-06 on the decisions step 7 compared (those decided during the stream), the closing-poll ones reported as measured
(step 7 never compared them).

    cd <code tree> && OMP_NUM_THREADS=1 PYTHONPATH=. python3 runs/identify/v5/cpu_exact.py run <tag> <out dir>
    python3 runs/identify/v5/cpu_exact.py compare <out dir>

Development evaluation, all data seen.
"""

import json
import os
import sys
import time

import numpy as np

EXACT_CPU = 8.1e-06


def run(tag: str, out: str) -> None:
    from pipeline.identify import engine as EN
    from pipeline.identify import ide_train as IT
    from pipeline.identify.iv5_rig import FakeSerialSource
    from pipeline.live import identify_engine as IE
    from pipeline.live.identify_recorded import RecordedSource, stream
    os.makedirs(out, exist_ok=True)
    t_all = time.time()
    md = IE.model_dir("loso_B2_v5")
    ts = IE.guard(md, "B2")
    eng = EN.Engine(md, T=EN.T_S, amp_norm=IT.gs_adopted(), layout="id_spot", device="cpu", room="B")
    app = IE.EngineApp(eng, f"loso_B2_v5 (trained on {', '.join(ts)})", replay=True,
                       jsonl=os.path.join(out, f"{tag}.jsonl"), dmode=IE.direction_mode())
    app.stream_label = "B2"
    c = IE.EngineConsumer(app, None)
    closing = []
    end = c.end_stream

    def end_stream():
        n = len(app.decisions)
        end()
        closing.extend(range(n, len(app.decisions)))
    c.end_stream = end_stream
    info = stream(c, FakeSerialSource(RecordedSource("B2")), speed="max", log=print)
    D = app.decisions
    np.savez(os.path.join(out, f"{tag}.npz"), t0=np.array([d["t0"] for d in D]), t_dec=np.array([d["t_dec"] for d in D]),
             ensemble=np.array([d["ensemble"] for d in D]), ensemble_nopace=np.array([d["ensemble_nopace"] for d in D]),
             confidence=np.array([d["confidence"] for d in D]), calib_n=np.array([d["calib_n"] for d in D]),
             top=np.array([d["top"] for d in D]), closing=np.isin(np.arange(len(D)), closing))
    res = {"tag": tag, "code": os.path.abspath(IE.__file__), "decisions": len(D), "presses": info["presses"],
           "closing_poll_decisions": len(closing), "pool": len(app.e.session), "seconds": round(time.time() - t_all, 1),
           "threads": os.environ.get("OMP_NUM_THREADS"), "nice": os.nice(0), "built": time.strftime("%Y-%m-%d %H:%M:%S")}
    json.dump(res, open(os.path.join(out, f"{tag}.json"), "w"), indent=1)
    print(json.dumps(res), flush=True)


def compare(out: str, result: str = None) -> bool:
    """`result`: where the comparison is written (default checks/cpu_exact.json, the 11 Oct option (c) check)."""
    a, b = np.load(os.path.join(out, "before.npz")), np.load(os.path.join(out, "after.npz"))
    same = {k: bool(a[k].shape == b[k].shape and (a[k] == b[k]).all()) for k in a.files}
    z = np.load(os.path.join("runs", "identify", "engine", "replays", "loso_B2_v5_B2_T4.0.npz"))
    pos = {round(float(t), 6): j for j, t in enumerate(z["t0"])}
    idx = np.array([pos[round(float(t), 6)] for t in b["t0"]])
    diff = np.abs(b["ensemble"] - z["ensemble"][idx]).max(axis=1)
    arg = (b["ensemble"].argmax(1) == z["ensemble"][idx].argmax(1))
    cl = b["closing"]
    res = {"built": time.strftime("%Y-%m-%d %H:%M:%S"), "label": "development evaluation, all data seen",
           "before": json.load(open(os.path.join(out, "before.json"))), "after": json.load(open(os.path.join(out, "after.json"))),
           "before_vs_after_bit_identical": same, "after_vs_replay": {
               "decisions": int(len(b["t0"])), "replay_decisions": int(len(z["t0"])), "argmax_equal": int(arg.sum()),
               "during_stream": {"n": int((~cl).sum()), "max_abs_ensemble_diff": float(diff[~cl].max()), "bound": EXACT_CPU},
               "closing_poll": {"n": int(cl.sum()), "max_abs_ensemble_diff": float(diff[cl].max()) if cl.any() else None,
                                "per_decision": [{"t0": float(t), "max_abs_ensemble_diff": float(d)}
                                                 for t, d in zip(b["t0"][cl], diff[cl])],
                                "note": "step 7 never compared these (they were decided by each recording's closing poll)"}}}
    res["PASSED_bit_identical"] = bool(all(same.values()))
    v = res["after_vs_replay"]
    res["PASSED_vs_replay"] = bool(v["argmax_equal"] == v["decisions"] == v["replay_decisions"]
                                   and v["during_stream"]["max_abs_ensemble_diff"] <= EXACT_CPU)
    res["PASSED"] = res["PASSED_bit_identical"] and res["PASSED_vs_replay"]
    json.dump(res, open(result or os.path.join("runs", "identify", "v5", "checks", "cpu_exact.json"), "w"), indent=1)
    print(json.dumps({k: res[k] for k in ("before_vs_after_bit_identical", "PASSED_bit_identical", "PASSED_vs_replay", "PASSED")}
                     | {"during": v["during_stream"], "closing_max": v["closing_poll"]["max_abs_ensemble_diff"]}), flush=True)
    return res["PASSED"]


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "compare":
        sys.exit(0 if compare(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None) else 1)
