"""pd_provenance: what every component of a decode was fitted on, and a check that FAILS LOUDLY on a forbidden
session (29 September 2026; Uzayr's instruction 4 for the corrected FINAL).

    python3 -m pipeline.constrained.pd_provenance --cell zsf_B2 --variant V --allowed 01 02 [--trace <clean.json>]

For each component the decoder uses it lists the recordings (session|stem) its fitted parameters came from:
  - the five heads and their input standardisation (the cell's training records);
  - the position head;
  - the start-of-walk readers (training rows by session, through the reader map, and the heads that made them);
  - the test-side reader heads;
  - the A2 start term, the veto or abstain;
  - the relative gate's G0;
  - the chain prior;
  - the emission marginal.
Separately it lists:
  - the test recording's own causal statistics (relative RSSI reference, g_rec, AdaBN: its idle windows before
    its first press);
  - the decoder's DESIGN CONSTANTS with their recorded provenance.

A FITTED component whose recordings include a session outside --allowed makes the run exit 1 with the list.
With --trace (a decode's clean.json from pd_clean) every network file the decode actually opened is checked
the same way, and so is every recording's data outside the test session. The only exception is the ground-truth
sidecars paths.load_paths reads for the taped line geometry.
Writes runs/dc2_results/verify/provenance_<cell>.json and .md.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
J = os.path.join
RES = J(REPO_ROOT, "runs", "dc2_results")

#: the decoder's design constants, not fitted per model, with their recorded provenance
#: (reports/tracking/2026-09-29_audit-leakage.md section 3)
DESIGN_CONSTANTS = [
    ("pace prior N(1.3034, 0.1125) m/s (was N(1.298, 0.123))", ["01", "02"],
     "RECOMPUTED 29 Sep from the A1+A2 tape anchors by stage1_pace's own method (240 passes; the same method gives "
     "1.2982 / 0.1230 on A1+A2+A3's 360, the old constant). Changes within 0.02 m/s, so no re-selection (Uzayr)"),
    ("display cap 0.80 m per window", ["01", "02", "03"],
     "swept 2026-09-21 in f3_render on the s0102_to_s03 demonstration pairing, A3's 120 walks (git 8590d47): SET ON A3. "
     "Kept (Uzayr); the A3 LOCK is optimistic, the B2 lock is the headline; committed answers do not read it"),
    ("display spread 4.5", ["01", "02", "03"],
     "introduced 2026-09-20 with the 3 m/s ceiling in a3_lock / f3_render on the s0102_to_s03 pairing's session-03 walks "
     "(git 0b18ee6), no independent tuning recorded: SET ON A3 or untraceable. Treated as the cap"),
    ("decoder configuration (margin, null_self, exit, clock, bout prior) and null rule (-7.5, gate weight 4.0, threshold 0.431)",
     ["01", "02"], "rb2_decoder, selected for s0102_to_s03 on its training side (A1+A2)"),
    ("veto threshold 0.01 / abstain threshold 0.90 and weight 0.25", ["01", "02"],
     "u2_useit selection folds s01_to_s02 and s02_to_s01"),
    ("A2 start-term weight 0.25, abstain in place of the veto, and every other decode option", ["01", "02", "B1"],
     "chosen on the development rotations (A1+A2->B1, A1+B1->A2, A2+B1->A1): design choices"),
]


def tag_train(tag: str) -> list:
    tr = tag[1:].split("_to_")[0]
    return [tr[i:i + 2] for i in range(0, len(tr), 2)]


def inner(cell: str, variant: str, allowed: list, trace: str = None) -> int:
    from pipeline.constrained.pd_clean import _bound, plan_for, variant_spec
    PC, c, tfs = _bound(cell)
    v = variant_spec(variant)
    plan = plan_for(c, tfs)
    tmap = json.loads(os.environ.get("TDR_TEST_TAG_MAP") or "{}")
    for s, p in plan.items():
        if p["changed"]:
            tmap[s] = p["clean"]
    os.environ["TDR_TEST_TAG_MAP"] = json.dumps(tmap)
    from pipeline.constrained.recordings import session_recordings
    recs = {s: [f"{s}|{stem}" for _s, stem in session_recordings(s) if stem not in PC.cal_stems(s)] for s in c["train"]}
    train_recs = [r for s in c["train"] for r in recs[s]]
    rows, fail = [], []

    def add(component, sessions, recordings, source):
        bad = sorted(set(sessions) - set(allowed))
        rows.append({"component": component, "sessions": sorted(set(sessions)), "recordings": recordings, "source": source,
                     "outside_allowed": bad})
        if bad:
            fail.append((component, bad))

    # the heads and their standardisation; a cell sharing another's weights byte for byte reads its records
    src_cell = cell
    shared = J(c["base"], "shared_models.json")
    if not os.path.exists(J(c["base"], "train_half.json")) and os.path.exists(shared):
        with open(shared, encoding="utf-8") as f:
            sm = json.load(f)
        assert sm.get("byte_identical"), f"{cell}: shared weights not recorded as byte-identical"
        src_cell = sm["from"]
    for h in ("half", "fh1s", "g1s1", "g1s2", "g100"):
        with open(J(RES, "cells", src_cell, f"train_{h}.json"), encoding="utf-8") as f:
            tj = json.load(f)
        ses = sorted(tj["by_session"])
        add(f"head {h} (weights and input standardisation)", ses, [r for s in ses for r in recs.get(s, [])],
            f"cells/{src_cell}/train_{h}.json ({tj['windows']} windows)" + (f"; {cell} holds byte-identical copies" if src_cell != cell else ""))
        if tj.get("pos_copied_from"):
            with open(J(RES, "cells", tj["pos_copied_from"], "train_half.json"), encoding="utf-8") as f:
                pj = json.load(f)
            add("position head (half)", sorted(pj["by_session"]), [r for s in sorted(pj["by_session"]) for r in recs.get(s, [])],
                f"copied from {tj['pos_copied_from']} (its train_half.json)")
    # the readers' training rows: the session's recordings, made by heads trained on the tag's sessions
    for s in c["train"]:
        t = tfs(s)
        add(f"reader rows of {s} (A2 region reader and {'abstain' if v['abstain'] else 'veto'} reader)",
            [s] + tag_train(t), recs[s], f"rows of {s} made by heads {t} (trained on {'+'.join(tag_train(t))})")
    rt = c["reader_tag"]
    add("test-side reader heads (V0: position and g25)", tag_train(rt.replace("V0", "")), [],
        f"{rt}: the pooled twin's per-link heads")
    add("A2 start term (LDA) and the reader (LDA)", list(c["train"]), train_recs, "fitted on the reader rows above")
    add("relative gate G0", [s for s in c["train"] if not s.startswith("B")],
        [r for s in c["train"] if not s.startswith("B") for r in recs[s]], "pd_decode.gate_reference(train, room_a_only=True)")
    add("chain prior", list(c["train"]), train_recs, "n2_arms.fit_chain_prior(st, train)")
    add("emission cell marginal", list(c["train"]), train_recs, "the training windows' positions")
    causal = [{"component": nm, "on": f"each test recording of {c['test']}: its own idle windows ending before its first press"}
              for nm in ("relative RSSI reference (per link mean)", "relative gate g_rec (median band energy)",
                         "AdaBN statistics of the reader heads")]
    # the decode's own file trace
    tr_rows = []
    if trace:
        with open(trace, encoding="utf-8") as f:
            opened = json.load(f)["files_opened"]
        for pth in opened:
            base = os.path.basename(pth)
            if base.endswith((".pt", ".npz")) and "_to_s" in base and "/d3/" not in pth:
                tag = base.split("_g")[0].split("_pos")[0]
                ses = tag_train(tag.replace("V0", ""))
                tr_rows.append({"file": pth, "tag": tag, "trained_on": ses})
                bad = sorted(set(ses) - set(allowed))
                if bad:
                    fail.append((f"trace: network {tag}", bad))
            m = re.search(r"session_(0[123]|B[12])", pth)
            if m and m.group(1) not in allowed and m.group(1) != c["test"]:
                geometry = pth.startswith("data/room_A/") and pth.endswith(".gt.json")
                tr_rows.append({"file": pth, "session": m.group(1), "geometry_only": geometry})
                if not geometry:
                    fail.append((f"trace: data of {m.group(1)} ({pth})", [m.group(1)]))
    out = {"cell": cell, "variant": variant, "train": list(c["train"]), "test": c["test"], "allowed": allowed,
           "fitted": rows, "test_recording_causal": causal,
           "design_constants": [{"constant": a, "sessions": b, "provenance": s_} for a, b, s_ in DESIGN_CONSTANTS],
           "trace": trace, "trace_rows": tr_rows, "FAILED": [f"{a}: {b}" for a, b in fail], "PASS": not fail}
    os.makedirs(J(RES, "verify"), exist_ok=True)
    with open(J(RES, "verify", f"provenance_{cell}.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    L = [f"# Provenance of {cell} ({variant}): what every component was fitted on", "",
         f"Training sessions {', '.join(c['train'])}; test {c['test']}; allowed for fitted components: {', '.join(allowed)}.", "",
         "| component | sessions | recordings | source | outside allowed |", "|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['component']} | {', '.join(r['sessions'])} | {len(r['recordings'])} | {r['source']} | "
                 f"{', '.join(r['outside_allowed']) or 'none'} |")
    L += ["", "**The test recording's own causal statistics** (not fitted on other data):", ""]
    L += [f"- {x['component']}: {x['on']}" for x in causal]
    L += ["", "**Design constants** (not fitted per model):", "", "| constant | sessions it was set on | provenance |", "|---|---|---|"]
    L += [f"| {a} | {', '.join(b)} | {s_} |" for a, b, s_ in DESIGN_CONSTANTS]
    if trace:
        nets = sorted({(r["tag"], tuple(r["trained_on"])) for r in tr_rows if "tag" in r})
        L += ["", f"**The decode's file trace** ({os.path.relpath(trace, REPO_ROOT)}): networks opened:", ""]
        L += [f"- {t}: trained on {', '.join(s_)}" for t, s_ in nets]
        other = [r for r in tr_rows if "session" in r]
        if other:
            L += ["", "Data of other sessions opened: " + "; ".join(
                f"{r['file']} ({'line geometry only' if r['geometry_only'] else 'DATA'})" for r in other[:12])]
    L += ["", f"**{'PASS' if out['PASS'] else 'FAIL'}**" + ("" if out["PASS"] else ": " + "; ".join(out["FAILED"])), ""]
    with open(J(RES, "verify", f"provenance_{cell}.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print("\n".join(L))
    if fail:
        print(f"PROVENANCE FAILED for {cell}: {out['FAILED']}", flush=True)
        return 1
    print(f"PROVENANCE PASS for {cell}", flush=True)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cell", required=True)
    ap.add_argument("--variant", required=True)
    ap.add_argument("--allowed", nargs="+", required=True)
    ap.add_argument("--trace", default=None)
    ap.add_argument("--inner", action="store_true")
    a = ap.parse_args(argv)
    if a.inner:
        return inner(a.cell, a.variant, a.allowed, a.trace)
    sys.path.insert(0, REPO_ROOT)
    from pipeline.live.final_model import _env
    return subprocess.call([sys.executable, "-m", "pipeline.constrained.pd_provenance", "--inner", "--cell", a.cell,
                            "--variant", a.variant, "--allowed", *a.allowed] + (["--trace", a.trace] if a.trace else []),
                           cwd=REPO_ROOT, env=_env(a.cell))


if __name__ == "__main__":
    sys.exit(main())
