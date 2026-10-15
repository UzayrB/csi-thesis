"""Items 4b to 4d of reports/BRIEF_RESTRUCTURE_CHECK_2026-10-01.md, on the restructured code (6769f8c): the app's own
functions, called exactly as their command lines call them, with their output folder pointed at
runs/dc2_results/restructure_check/ so no committed record is overwritten.

    python3 runs/dc2_results/restructure_check/app_check.py replays     # 4b: five K1g causal replays, in parallel
    python3 runs/dc2_results/restructure_check/app_check.py teaching    # 4c: the teaching pack, B2 PA2
    python3 runs/dc2_results/restructure_check/app_check.py stream      # 4d: one B2 recording streamed, then re-replayed
    python3 runs/dc2_results/restructure_check/app_check.py compare     # every comparison, written to APP_CHECK.json

Each job runs in its own process with the cell's environment (`final_model._env`) and OMP_NUM_THREADS=1, as
runs/dc2_results/k1g_chain.sh ran the committed logs.
"""

import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)
J = os.path.join
OUT = J(ROOT, "runs", "dc2_results", "restructure_check")
REPLAY = J(ROOT, "runs", "live", "replay")
#: (name, model, recording, presses, m, the committed log it must equal byte for byte)
JOBS = [("semi_B2", "final", "B2/participant_PA2_walk", "start", None,
         ["final/semi_disp-K1g_causal_realtime_screen", "final/semi_disp-K1g_causal"]),
        ("semi_A3", "final", "03/participant_PA5_TEST_walk", "start", None, ["final/semi_disp-K1g_causal_realtime_screen"]),
        ("semi_zsB2", "zeroshot", "B2/participant_PA2_walk", "start", None, ["zeroshot/semi_disp-K1g_causal"]),
        ("full_B2", "final", "B2/participant_PA2_walk", "start_end", None, ["final/full_disp-K1g_causal"]),
        ("unc_B2", "final", "B2/participant_PA2_walk", "none", 4, ["final/unconstrained_m4_disp-K1g_causal"])]
STREAM_REC = "B2/participant_PA5_walk"
TEACH_UNC = J(REPLAY, "final", "unconstrained_m4_disp-K1g_causal", "B2__participant_PA2_walk.jsonl")


def env_for(model, session, extra=None):
    from pipeline.live.app_replay import cell_for
    from pipeline.live.final_model import _env
    return dict(_env(cell_for(model, session)), OMP_NUM_THREADS="1", **(extra or {}))


def inner_replay(name):
    from pipeline.constrained.pd_clean import force_cpu
    force_cpu()
    import pipeline.live.app_replay as AR
    _n, model, rec, presses, m, _ref = next(j for j in JOBS if j[0] == name)
    AR.OUT = J(OUT, "replay", name)
    session, stem = rec.split("/", 1)
    return AR.session_inner(model, session, presses, "causal", False, [stem], None, m, "K1g")


def inner_teaching():
    import pipeline.live.app_replay as AR
    AR.OUT = J(OUT, "teaching", "replay")                       # the pack's own replay log goes here, not to runs/live
    import pipeline.live.app_teaching as T
    return T.inner()


def inner_stream():
    import pipeline.live.stream_source as SS
    SS.OUT = J(OUT, "stream", "stream")                         # out_root() adds _disp-K1g
    session, stem = STREAM_REC.split("/", 1)
    SS.stream_inner(session, stem, J(OUT, "stream", "video"), 1.0)
    return 0


def inner_rereplay():
    import pipeline.live.stream_source as SS
    SS.OUT = J(OUT, "stream", "stream")
    session, stem = STREAM_REC.split("/", 1)
    SS.rereplay_inner(session, stem)
    return 0


def spawn(what, model, session, log, extra=None):
    os.makedirs(J(OUT, "logs"), exist_ok=True)
    f = open(J(OUT, "logs", log), "w")
    return subprocess.Popen([sys.executable, os.path.abspath(__file__), "inner", what], cwd=ROOT,
                            env=env_for(model, session, extra), stdout=f, stderr=subprocess.STDOUT)


def strip_summary(s):
    drop = ("timing", "minutes", "at", "video", "log")
    return {k: v for k, v in s.items() if k not in drop}


def compare():
    res = {"replays": {}, "teaching": None, "stream": None}
    for name, model, rec, presses, m, refs in JOBS:
        session, stem = rec.split("/", 1)
        mode = {"start": "semi", "start_end": "full", "none": f"unconstrained_m{m}"}[presses] + "_disp-K1g_causal"
        new = J(OUT, "replay", name, model, mode, f"{session}__{stem}")
        row = {"new": os.path.relpath(new + ".jsonl", ROOT), "against": {}}
        for ref in refs:
            old = J(REPLAY, ref, f"{session}__{stem}")
            a, b = open(old + ".jsonl", "rb").read(), open(new + ".jsonl", "rb").read()
            sa, sb = (json.load(open(p + ".summary.json", encoding="utf-8")) for p in (old, new))
            diff_keys = sorted(k for k in set(strip_summary(sa)) | set(strip_summary(sb)) if sa.get(k) != sb.get(k))
            row["against"][os.path.relpath(old + ".jsonl", ROOT)] = {
                "log_bytes_identical": a == b, "log_bytes": [len(a), len(b)],
                "summary_differs_in": diff_keys,
                "summary_values": {k: [sa.get(k), sb.get(k)] for k in diff_keys}}
        res["replays"][name] = row
    tp = J(OUT, "teaching", "teaching_pack.json")
    if os.path.exists(tp):
        old = json.load(open(J(ROOT, "reports", "teaching_pack_app_v3_2026-10-01.json"), encoding="utf-8"))
        new = json.load(open(tp, encoding="utf-8"))
        diffs = []

        def walk(x, y, path):
            if isinstance(x, dict) and isinstance(y, dict):
                for k in sorted(set(x) | set(y)):
                    walk(x.get(k), y.get(k), f"{path}.{k}")
            elif isinstance(x, list) and isinstance(y, list) and len(x) == len(y):
                for i, (u, v) in enumerate(zip(x, y)):
                    walk(u, v, f"{path}[{i}]")
            elif x != y:
                diffs.append({"at": path, "v3": x, "now": y})
        walk(old, new, "")
        res["teaching"] = {"differences": diffs}
    sd = J(OUT, "stream", "stream_disp-K1g", f"B2__{STREAM_REC.split('/')[1]}")
    if os.path.exists(J(sd, "summary.json")):
        s = json.load(open(J(sd, "summary.json"), encoding="utf-8"))
        rr = json.load(open(J(sd, "rereplay.json"), encoding="utf-8")) if os.path.exists(J(sd, "rereplay.json")) else None
        res["stream"] = {"exit": s["exit"], "n_committed": s["n_committed"], "n_locks": s["n_locks"],
                         "receivers": s["receivers"], "rereplay": rr}
    with open(J(OUT, "APP_CHECK.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, default=str)
    print(json.dumps(res, indent=1, default=str)[:6000])


def main(argv):
    if argv[0] == "inner":
        return {"teaching": inner_teaching, "stream": inner_stream, "rereplay": inner_rereplay}.get(
            argv[1], lambda: inner_replay(argv[1]))()
    if argv[0] == "replays":
        ps = []
        for name, model, rec, *_ in JOBS:
            ps.append((name, spawn(name, model, rec.split("/")[0], f"replay_{name}.log")))
        for name, p in ps:
            print(name, "exit", p.wait(), flush=True)
    elif argv[0] == "teaching":
        os.makedirs(J(OUT, "teaching"), exist_ok=True)
        p = spawn("teaching", "final", "B2", "teaching.log",
                  {"TEACHING_OUT": J(OUT, "teaching", "teaching_pack.json"), "TEACHING_UNC_LOG": TEACH_UNC})
        print("teaching exit", p.wait(), flush=True)
    elif argv[0] == "stream":
        p = spawn("stream", "final", "B2", "stream.log")
        print("stream exit", p.wait(), flush=True)
        p = spawn("rereplay", "final", "B2", "rereplay.log")
        print("rereplay exit", p.wait(), flush=True)
    elif argv[0] == "compare":
        compare()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
