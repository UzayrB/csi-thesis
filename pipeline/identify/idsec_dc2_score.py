"""idsec_dc2_score. The two SECONDARY DC2 identification rows, P1-REV and P7, scored once.

Addendum 2026-09-24, section 3, registers them before any data; this is their scoring code, frozen by
`runs/IDENTIFICATION_FROZEN_2026-09-28.json` before any identification figure existed.

  - P1-REV: analysis P1 exactly (PRIMARY, SECONDARY and S0, all three links) on the `A_rev`
    passes: train on day 1 natural `A_rev`, test on day 2 natural `A_rev`. It neither replaces nor
    rescues analysis P1.
  - P7: pace-matched cross-day, PRIMARY and S0 on `A_fwd`: train on day 1 slow, test on day 2
    slow; the same for fast.

Every feature, head, fold and statistic is the FROZEN `id29_dc2_score`'s, imported unchanged: its
extraction, `build`, `predictors`, sealed-label `score_fold` and `id_stats` (accuracy, n, chance
16.67, a 95 percent bootstrap over participants and the within-day permutation p, 1000 draws each).
It reads `runs/identify/dc2_view_sec/room_B` (`idsec_view`, built from the relabelled source).
  - HASH GATE: refuses unless addendum 2026-09-24 matches the 2026-09-24 freeze, and addendum E and
    the relabel manifest match the 2026-09-28 freeze; and unless the view was built from that
    manifest.
  - LAYOUT: every recording, direction, count and duration is checked before anything is scored;
    `--check-layout` never touches results.
  - ONCE: a second run needs `--rerun-reason "<text>"`, which is logged; the earlier result is moved
    aside, never overwritten.
Tested on SYNTHETIC recordings only (tests/test_idsec_dc2_score.py).

    PYTHONPATH=. python3 -m pipeline.identify.idsec_dc2_score --check-layout
    PYTHONPATH=. python3 -m pipeline.identify.idsec_dc2_score
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import sys
import time
from dataclasses import dataclass, field

import numpy as np

from pipeline.identify import capture_idboth as C
from pipeline.identify import id29_dc2_score as D
from pipeline.identify import idmax_common as IC
from pipeline.identify import idsec_view as V
from pipeline.identify.common import RETIRED, SIX, anon

STAGE = "idsec_dc2_score"
ADDENDUM_24 = os.path.join("reports", "PREREG_DC2_ADDENDUM_2026-09-24.md")
FREEZE_24 = os.path.join("runs", "IDENTIFICATION_FROZEN_2026-09-24.json")
ADDENDUM_E = os.path.join("reports", "PREREG_ID_DC2_2026-09-23_ADDENDUM_E.md")
MANIFEST = os.path.join("runs", "identify", "dc2", "relabel_manifest.json")
FREEZE_28 = os.path.join("runs", "IDENTIFICATION_FROZEN_2026-09-28.json")
DATA_ROOT = V.DST
OUT = os.path.join("runs", "identify", "dc2", "idsec")
FINDINGS = os.path.join("reports", "FINDINGS_stageidsec_dc2.txt")
WALK_SUF = D.WALK_SUF
BLOCKS = tuple(V.KEEP)                                   # natural (A_rev), slow and fast (A_fwd)


@dataclass
class Config:
    addendum_24: str = ADDENDUM_24
    freeze_24: str = FREEZE_24
    addendum_e: str = ADDENDUM_E
    manifest: str = MANIFEST
    freeze_28: str = FREEZE_28
    data_root: str = DATA_ROOT
    out: str = OUT
    report: str = D.REPORT
    findings: str = FINDINGS
    spot_file: str = C.F.SPOT_FILE
    plan: dict = field(default_factory=lambda: dict(C.PLAN))
    cnn_seeds: tuple = (0, 1, 2, 3, 4)
    cnn_epochs: int = 60
    n_boot: int = 1000
    n_perm: int = 1000
    names_loader: object = None          # production: the frozen feature columns id29 uses; tests inject


class Refused(SystemExit):
    def __init__(self, msg: str, kind: str = "other"):
        super().__init__(msg)
        self.kind = kind


# ------------------------------------------------------------------ gate

def check_hashes(cfg: Config) -> dict:
    for f in (cfg.freeze_24, cfg.freeze_28):
        if not os.path.exists(f):
            raise Refused(f"REFUSED: the freeze {f} does not exist", "hash")
    f24 = json.load(open(cfg.freeze_24, encoding="utf-8"))["sha256"]
    f28 = json.load(open(cfg.freeze_28, encoding="utf-8"))["sha256"]
    got = {"addendum_24_sha256": D.sha256(cfg.addendum_24), "addendum_e_sha256": D.sha256(cfg.addendum_e),
           "manifest_sha256": D.sha256(cfg.manifest)}
    want = {"addendum_24_sha256": f24.get(ADDENDUM_24), "addendum_e_sha256": f28.get(ADDENDUM_E),
            "manifest_sha256": f28.get(MANIFEST)}
    bad = [k for k in got if got[k] != want[k]]
    if bad:
        raise Refused(f"REFUSED: {', '.join(bad)} differ from the freezes. A registered file was changed "
                      "after it was frozen.", "hash")
    return got


# ------------------------------------------------------------------ discovery and layout

def _scan(root: str) -> tuple:
    found, bad = {}, []
    for p in glob.glob(os.path.join(root, "**", "*"), recursive=True):
        b = os.path.basename(p)
        if not (os.path.isfile(p) or os.path.islink(p)) or "_idpath_" not in b:
            continue
        if "REHEARSAL" in b:
            bad.append(f"rehearsal file inside the DC2 root: {b}")
            continue
        if any(r in b for r in RETIRED):
            bad.append(f"retired participant: {b}")
            continue
        m = D.NAME_RE.match(b)
        if not m:
            bad.append(f"unexpected file name: {b}")
            continue
        name, day, what, suf = m["name"], int(m["day"]), m["what"], m["suf"]
        if name not in SIX:
            bad.append(f"not one of the six: {b}")
            continue
        if day not in (1, 2) or what not in BLOCKS:
            bad.append(f"unexpected recording: {b}")
            continue
        if suf == "_run.json":
            continue
        rec = found.setdefault((name, day, what), {"dir": os.path.dirname(p), "stem": b[: -len(suf)],
                                                   "have": set()})
        if rec["dir"] != os.path.dirname(p):
            bad.append(f"one recording split across directories: {b}")
        rec["have"].add(suf)
    for name in SIX:
        for day in (1, 2):
            for what in BLOCKS:
                lab = f"{anon(name)} d{day}_{what}"
                rec = found.get((name, day, what))
                if rec is None:
                    bad.append(f"missing recording: {lab}")
                    continue
                for s in WALK_SUF:
                    if s not in rec["have"]:
                        bad.append(f"missing file: {lab}{s}")
    return found, bad


def layout_problems(cfg: Config, found: dict) -> tuple:
    bad, summary = [], {}
    spot_xy = tuple(json.load(open(cfg.spot_file, encoding="utf-8"))["xy"]) if os.path.exists(cfg.spot_file) else None
    if spot_xy is None:
        bad.append(f"RX2 spot not recorded ({cfg.spot_file})")
    for (name, day, what), rec in sorted(found.items()):
        lab = f"{anon(name)} d{day}_{what}"
        side = json.load(open(os.path.join(rec["dir"], rec["stem"] + ".idmax.json"), encoding="utf-8"))
        gt = json.load(open(os.path.join(rec["dir"], rec["stem"] + ".gt.json"), encoding="utf-8"))
        passes = gt.get("passes", [])
        want = V.KEEP[what]
        planned = cfg.plan.get((day, what))
        st = side.get("count", {}).get("status")
        if len(passes) != planned and st != "COUNT_DIFFERS_REASON_LOGGED":
            bad.append(f"{lab}: {len(passes)} {want} passes against a plan of {planned}, no reason logged")
        off = [q.get("path_name") for q in passes if q.get("path_name") != want]
        if off:
            bad.append(f"{lab}: passes on {sorted(set(map(str, off)))}, not {want}")
        durs = [float(q["t_end"]) - float(q["t_start"]) for q in passes]
        wrong = [round(x, 2) for x in durs if not 1.5 <= x <= 12.0]
        if wrong:
            bad.append(f"{lab}: pass durations outside 1.5 to 12 s: {wrong}")
        if spot_xy is not None and tuple(side.get("rx2_xy", ())) != spot_xy:
            bad.append(f"{lab}: sidecar puts RX2 at {side.get('rx2_xy')}, the recorded spot is {spot_xy}")
        summary[lab] = {"path": want, "passes": len(passes), "planned": planned,
                        "duration_s_min_max": [round(min(durs), 2), round(max(durs), 2)] if durs else None}
    return bad, summary


def view_problems(cfg: Config) -> list:
    """The view must have been built from the relabelled source of the frozen manifest."""
    vp = os.path.join(cfg.data_root, V.MARKER)
    if not os.path.exists(vp):
        return [f"{cfg.data_root} is not an idsec view (no {V.MARKER})"]
    got = json.load(open(vp, encoding="utf-8")).get("relabel_manifest_sha256")
    if got != D.sha256(cfg.manifest):
        return [f"the view was built from relabel manifest {str(got)[:12]}, not {D.sha256(cfg.manifest)[:12]}"]
    return []


def check_layout(cfg: Config) -> dict:
    found, bad = _scan(cfg.data_root)
    more, summary = layout_problems(cfg, found)
    probs = bad + more + view_problems(cfg)
    return {"ok": not probs, "problems": probs, "recordings": summary}


# ------------------------------------------------------------------ scoring

def names_default() -> list:
    """The feature columns id29's production run uses: Room A's frozen steady_raw variant."""
    from pipeline.identify import idmax_eval as E
    return list(E.load_variant("steady_raw")["names"])


def matrix(cfg: Config, found: dict) -> tuple:
    dcfg = D.Config(out=cfg.out, cnn_seeds=cfg.cnn_seeds, cnn_epochs=cfg.cnn_epochs,
                    n_boot=cfg.n_boot, n_perm=cfg.n_perm)
    dc2 = D.extract(dcfg, found)
    for r in dc2["rows"]:
        r["line"] = V.KEEP[r["block"]]                   # id29 stamps A_fwd; natural rows here are A_rev
    names = (cfg.names_loader or names_default)()
    ra = {"rows": [], "X": np.empty((0, len(names))), "names": names, "single_RX3": []}
    return dcfg, D.build(dc2, ra)


def score_all(cfg: Config, dcfg, M: dict, y=None) -> dict:
    y = M["y"].copy() if y is None else np.asarray(y)
    P = D.predictors(dcfg, M)
    idx = lambda day, block: np.flatnonzero((M["day"] == day) & (M["block"] == block))  # noqa: E731
    out = {"P1_REV": {}, "P7": {"slow": {}, "fast": {}}}
    d1, d2 = idx(1, "natural"), idx(2, "natural")
    for c in ("PRIMARY", "SECONDARY", "S0"):
        out["P1_REV"][c] = D.id_stats([D.score_fold(f"P1REV|{c}", P[c], d1, d2, y)], M, dcfg)
    for b in ("slow", "fast"):
        for c in ("PRIMARY", "S0"):
            out["P7"][b][c] = D.id_stats([D.score_fold(f"P7|{b}|{c}", P[c], idx(1, b), idx(2, b), y)], M, dcfg)
    out["n"] = {f"d{d}_{b}": int(len(idx(d, b))) for d in (1, 2) for b in BLOCKS}
    return out


# ------------------------------------------------------------------ outputs

def report_text(res: dict, hashes: dict, rerun_reason) -> str:
    L = ["| row | accuracy % | 95% interval (participants) | chance % | p | n |", "|---|---|---|---|---|---|"]
    lab = {"PRIMARY": "PRIMARY", "SECONDARY": "SECONDARY (post hoc)", "S0": "S0 (control)"}
    for c, s in res["P1_REV"].items():
        L.append(D._row(f"P1-REV, A_rev, day 1 natural to day 2 natural, {lab[c]}", s))
    for b in ("slow", "fast"):
        for c, s in res["P7"][b].items():
            L.append(D._row(f"P7, A_fwd, day 1 {b} to day 2 {b}, {lab[c]}", s))
    return "\n".join([
        "", "", "---", "", f"# DC2 identification, secondary rows P1-REV and P7 ({time.strftime('%Y-%m-%d')})", "",
        "Scored once by `pipeline/identify/idsec_dc2_score.py` against addendum 2026-09-24 section 3 "
        f"(SHA-256 {hashes['addendum_24_sha256'][:16]}...) and addendum E (SHA-256 "
        f"{hashes['addendum_e_sha256'][:16]}...), with the frozen id29 features, heads and statistics. "
        "Secondary: P1-REV neither replaces nor rescues analysis P1, and a figure pooling A_fwd and A_rev is "
        "exploratory." + (f" RE-RUN, reason: {rerun_reason}." if rerun_reason else ""),
        "", "\n".join(L), ""])


def write(cfg: Config, res: dict, hashes: dict, rerun_reason) -> None:
    os.makedirs(cfg.out, exist_ok=True)
    doc = {"stage": STAGE, "written": time.strftime("%Y-%m-%dT%H:%M:%S"), **hashes,
           "rerun_reason": rerun_reason, **res}
    txt = json.dumps(doc, indent=1, default=str)
    assert IC.no_names(txt), "a participant name reached the results"
    open(os.path.join(cfg.out, "results.json"), "w", encoding="utf-8").write(txt)
    sec = report_text(res, hashes, rerun_reason)
    assert IC.no_names(sec)
    open(cfg.findings, "w", encoding="utf-8").write("PASSED\nidsec, DC2 identification, secondary rows P1-REV "
                                                    "and P7, scored once.\n" + sec + "\n")
    with open(cfg.report, "a", encoding="utf-8") as f:
        f.write(sec)


def run(cfg: Config, rerun_reason: str = None, y_override=None) -> dict:
    hashes = check_hashes(cfg)
    prior = os.path.join(cfg.out, "results.json")
    if os.path.exists(prior):
        if not rerun_reason:
            raise Refused(f"REFUSED: {prior} exists. The secondary rows are scored once; a re-run needs "
                          '--rerun-reason "<text>", which is logged.', "rerun")
        with open(os.path.join(cfg.out, "RERUNS.log"), "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')}\t{rerun_reason}\n")
        shutil.move(prior, os.path.join(cfg.out, f"results_superseded_{time.strftime('%Y%m%dT%H%M%S')}.json"))
    found, bad = _scan(cfg.data_root)
    if bad:
        raise Refused("REFUSED at discovery, nothing scored:\n  " + "\n  ".join(sorted(bad)), "discovery")
    more, _summary = layout_problems(cfg, found)
    more += view_problems(cfg)
    if more:
        raise Refused("REFUSED at the layout check, nothing scored:\n  " + "\n  ".join(more), "layout")
    dcfg, M = matrix(cfg, found)
    res = score_all(cfg, dcfg, M, y_override)
    write(cfg, res, hashes, rerun_reason)
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data-root", default=DATA_ROOT)
    ap.add_argument("--check-layout", action="store_true")
    ap.add_argument("--rerun-reason", default=None)
    a = ap.parse_args(argv)
    cfg = Config(data_root=a.data_root)
    if a.check_layout:
        r = check_layout(cfg)
        msg = json.dumps(r, indent=1, default=str)
        for n in tuple(SIX) + tuple(RETIRED):
            msg = msg.replace(n, "<name>")
        print(msg)
        return 0 if r["ok"] else 1
    try:
        run(cfg, a.rerun_reason)
    except Refused as e:
        msg = str(e)
        for n in tuple(SIX) + tuple(RETIRED):
            msg = msg.replace(n, "<name>")
        print(msg, file=sys.stderr)
        if e.kind != "rerun":
            open(cfg.findings, "w", encoding="utf-8").write(f"FAILED\nidsec refused ({e.kind}): {msg}\n")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
