"""The shared contract for the constrained batch. Every stage imports its standards from here.

This module exists so that eleven stages cannot quietly disagree about seeding, about what a
reportable row contains, about what counts as beating a comparator, or about the one rule that has
cost this project the most when it was broken.

THE RULES THIS MODULE ENFORCES, each because it was broken at least once before.

  never pool regimes   ``regime_split`` is the ONLY way an aggregate is formed. A pooled mean once
                       hid a real cross-day regression of 0.048 m behind a real within-day gain of
                       0.111 m and the batch reported "no effect". Cross-day and within-day are
                       reported separately, always, with their counts.

  decompose position   ``path_error`` splits every positional error into the component ALONG the
                       true path and the component ACROSS it. They answer different questions:
                       cross-path error is path-identification error, along-path error is what the
                       CSI is responsible for. A single median cannot separate them, and the whole
                       first requirement of this batch is about the along-path component.

  seeding              ``seed_all`` sets torch, numpy and python. Setting only numpy left weight
                       init and dropout uncontrolled in an earlier batch and its estimates did not
                       reproduce.

  the verdict rule     ``verdict`` applies both acceptance criteria and RECORDS WHICH ONE decided
                       it. A variant beats a comparator only if it does so outside the bootstrap
                       interval on more than one pairing AND the mean effect exceeds the 0.11 m
                       noise floor, OR it is consistent in sign on all twelve pairings.

The noise floor is two seed standard deviations from stage 9 of the push (median sd 0.055 m).
"""

from __future__ import annotations

import csv
import json
import os
import random
import time
from typing import Optional, Sequence

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
#: Cache root for features, RSSI, models and posteriors. Overridable ONLY through the environment,
#: so the 0.5 s arm (D1) writes an ISOLATED tree. The feature cache is keyed
#: session_<id>_<stem>.npy with NO stride in the filename, so without this a 0.5 s run would
#: silently overwrite 6.3 GB of 1 s features that every other stage depends on.
ART_DIR = os.environ.get("TDR_ART_DIR") or os.path.join(REPO, "runs", "artefacts")
RUN_DIR = os.path.join(REPO, "runs", "constrained")
REPORT_DIR = os.path.join(REPO, "reports")
FIG_DIR = os.path.join(REPORT_DIR, "fig")
STATUS = os.path.join(REPORT_DIR, "status.txt")
RESULTS_CSV = os.path.join(REPORT_DIR, "results.csv")

SESSIONS = ("01", "02", "03")
SIX = ("PA5", "PA1", "PA2", "PA3", "PA4", "PA6")
SEEDS = (0, 1, 2)
NOISE_FLOOR_M = 0.11
N_BOOT = 1000
BOOT_SEED = 0
CHANCE_PATH_PCT = 100.0 / 12.0
ROOM_CENTRE = np.array([2.5, 2.5], dtype=float)

#: The frozen budget from 2026-09-16. Read from EPOCHS_XD.json where it exists; these are the
#: fallbacks so a stage never dies on a missing file.
E_REG, E_POST = 20, 24

#: The pace model on record, and the reason this batch exists. sigma_v is the between-pass spread of
#: MEAN walking speed, not the within-pass variation of displacement, so using it as a per-window
#: transition sd makes the decoder demand almost exactly 1.298 m every second. Stage 1 measures what
#: that prior is worth; nothing here assumes it is right.
V_MEAN, V_SD, DT = 1.298, 0.123, 1.0

CSV_COLUMNS = ["stage", "arm", "regime", "train_sessions", "test_sessions", "participant", "metric",
               "value", "ci_low", "ci_high", "unit", "comparator", "comparator_value", "clears",
               "n", "seed_sd", "posthoc"]


# --------------------------------------------------------------------------- seeding


def seed_all(seed: int) -> None:
    """torch, numpy and python, all three. Anything less is not reproducible."""
    import torch
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.backends.mps.is_available():
        torch.mps.manual_seed(seed)


# --------------------------------------------------------------------------- status and reporting


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def status(msg: str) -> None:
    os.makedirs(REPORT_DIR, exist_ok=True)
    line = f"[{now()}] {msg}"
    print(line, flush=True)
    with open(STATUS, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def headline(text: str) -> None:
    """One timestamped line per resolved test. Append only, never rewritten."""
    os.makedirs(REPORT_DIR, exist_ok=True)
    with open(os.path.join(REPORT_DIR, "HEADLINES.txt"), "a", encoding="utf-8") as f:
        f.write(f"[{now()}] {text}\n")
    status(f"HEADLINE: {text}")


def write_findings(stage, passed: Optional[bool], body: str) -> None:
    """FINDINGS_stage<N>.txt: plain text, under 400 words, opening PASSED, FAILED or INFO."""
    os.makedirs(REPORT_DIR, exist_ok=True)
    head = "PASSED" if passed else ("FAILED" if passed is False else "INFO")
    words = body.split()
    if len(words) > 380:
        body = " ".join(words[:380]) + " ... (truncated at 380 words)"
    p = os.path.join(REPORT_DIR, f"FINDINGS_stage{stage}.txt")
    with open(p, "w", encoding="utf-8") as f:
        f.write(f"{head}\n\n{body}\n")
    status(f"wrote {os.path.basename(p)}")


def _jsonable(o):
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return str(o)


def write_json(path: str, obj) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=_jsonable)


def read_json(path: str, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def fmt(x, nd: int = 3) -> str:
    return "n/a" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:.{nd}f}"


def row(stage: str, arm: str, regime: str, metric: str, value, *, train_sessions: str = "",
        test_sessions: str = "", participant: str = "", ci=None, unit: str = "",
        comparator: str = "", comparator_value="", clears: str = "", n="", seed_sd="") -> dict:
    lo, hi = "", ""
    if ci is not None and ci[0] is not None and np.isfinite(float(ci[0])):
        lo, hi = round(float(ci[0]), 4), round(float(ci[1]), 4)
    return {"stage": stage, "arm": arm, "regime": regime, "train_sessions": train_sessions,
            "test_sessions": test_sessions, "participant": participant, "metric": metric,
            "value": (round(float(value), 4) if isinstance(value, (int, float, np.floating)) else value),
            "ci_low": lo, "ci_high": hi, "unit": unit, "comparator": comparator,
            "comparator_value": comparator_value, "clears": clears, "n": n, "seed_sd": seed_sd,
            "posthoc": "yes"}


def append_rows(rows: Sequence[dict]) -> None:
    if not rows:
        return
    os.makedirs(REPORT_DIR, exist_ok=True)
    new = not os.path.exists(RESULTS_CSV)
    with open(RESULTS_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        if new:
            w.writeheader()
        for r in rows:
            r.setdefault("posthoc", "yes")
            w.writerow(r)


# --------------------------------------------------------------------------- pairings and regimes


def pairings():
    """All nine directional cross-day splits plus the three within-day. Reported in full."""
    out = [((a,), (b,)) for a in SESSIONS for b in SESSIONS if a != b]
    out += [(tuple(s for s in SESSIONS if s != h), (h,)) for h in SESSIONS]
    out += [((s,), (s,)) for s in SESSIONS]
    return out


def tag_of(tr, te, within: bool) -> str:
    return f"within_s{tr[0]}" if within else f"s{''.join(tr)}_to_s{''.join(te)}"


def is_cross(tag: str) -> bool:
    return not tag.startswith("within")


def regime_split(per_pairing: dict, getter) -> dict:
    """The ONLY way an aggregate is formed. Cross-day and within-day, never pooled.

    There is deliberately no combined mean. The pooled number is what once hid a cross-day
    regression behind a within-day gain and let a batch report "no effect".
    """
    c, w = [], []
    for k, v in per_pairing.items():
        try:
            x = getter(v)
        except Exception:
            continue
        if x is None or not np.isfinite(float(x)):
            continue
        (c if is_cross(k) else w).append(float(x))
    return {"cross": float(np.mean(c)) if c else None, "n_cross": len(c),
            "cross_sd": float(np.std(c)) if len(c) > 1 else None,
            "within": float(np.mean(w)) if w else None, "n_within": len(w),
            "within_sd": float(np.std(w)) if len(w) > 1 else None}


def regime_line(label: str, s: dict, unit: str = "m", nd: int = 3) -> str:
    return (f"{label}: cross-day {fmt(s.get('cross'), nd)} {unit} (n={s.get('n_cross')}), "
            f"within-day {fmt(s.get('within'), nd)} {unit} (n={s.get('n_within')})")


# --------------------------------------------------------------------------- the bootstrap


def group_bootstrap(values: np.ndarray, keys: np.ndarray, stat=np.median,
                    n_boot: int = N_BOOT, seed: int = BOOT_SEED) -> tuple:
    """Cluster bootstrap over WHOLE PASSES. Windows inside a pass are not independent."""
    values = np.asarray(values, dtype=float)
    keys = np.asarray(keys)
    ok = np.isfinite(values)
    values, keys = values[ok], keys[ok]
    uniq = np.unique(keys)
    if len(uniq) < 2 or len(values) == 0:
        return (float("nan"), float("nan"))
    idx_by_key = {k: np.flatnonzero(keys == k) for k in uniq}
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n_boot):
        pick = rng.choice(uniq, size=len(uniq), replace=True)
        sel = np.concatenate([idx_by_key[k] for k in pick])
        v = float(stat(values[sel]))
        if np.isfinite(v):
            out.append(v)
    if not out:
        return (float("nan"), float("nan"))
    return (float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5)))


# --------------------------------------------------------------------------- the positional report


def path_error(pred: np.ndarray, true: np.ndarray, direction: np.ndarray) -> tuple:
    """Split the error into ALONG the true path and ACROSS it.

    ``direction`` is the unit vector of the TRUE path at each window. All twelve paths are straight,
    so it is constant within a pass, but it is passed per window so a curved path would still work.

    Returns (along_signed, cross_abs, total). Along is signed: positive means the estimate is ahead
    of the person along their direction of travel, which is the sign a pace prior running fast would
    produce, so it is worth keeping rather than taking the magnitude immediately.
    """
    d = np.asarray(pred, float) - np.asarray(true, float)
    u = np.asarray(direction, float)
    n = np.linalg.norm(u, axis=1, keepdims=True)
    u = np.divide(u, n, out=np.zeros_like(u), where=n > 1e-12)
    along = np.sum(d * u, axis=1)
    cross = np.linalg.norm(d - along[:, None] * u, axis=1)
    return along, cross, np.linalg.norm(d, axis=1)


def position_report(pred: np.ndarray, true: np.ndarray, direction: np.ndarray, keys: np.ndarray,
                    tag: str = "") -> dict:
    """The full positional row the standards require: along, across and total, each decomposed.

    A total median alone is not reportable in this batch. The whole first requirement is about the
    along-path component, and a total cannot separate "the radio placed them on the wrong line" from
    "the radio placed them in the wrong spot along the right line".
    """
    along, cross, total = path_error(pred, true, direction)
    out = {"tag": tag, "n": int(len(total))}
    for name, e in (("along", np.abs(along)), ("cross", cross), ("total", total)):
        lo, hi = group_bootstrap(e, keys)
        out[name] = {
            "median_m": float(np.median(e)), "median_ci": [lo, hi],
            "p90_m": float(np.percentile(e, 90)), "mean_m": float(e.mean()),
            "within_0.5m_pct": float(100 * (e <= 0.5).mean()),
            "within_1.0m_pct": float(100 * (e <= 1.0).mean()),
        }
    out["along_signed_mean_m"] = float(along.mean())
    out["along_signed_median_m"] = float(np.median(along))
    return out


def emit_position(stage: str, arm: str, tag: str, rep: dict, tr_s, te_s, comparator: str,
                  comparator_value, extra: Optional[dict] = None) -> None:
    """Write the full decomposed set for one arm on one pairing."""
    regime = "cross" if is_cross(tag) else "within"
    base = {"train_sessions": "+".join(tr_s), "test_sessions": "+".join(te_s), "n": rep.get("n", "")}
    rows = []
    for comp in ("along", "cross", "total"):
        r = rep[comp]
        beats = (comparator_value not in ("", None) and comp == "along"
                 and r["median_ci"][1] < float(comparator_value))
        rows += [
            row(stage, arm, regime, f"{comp}-path median error", r["median_m"], ci=r["median_ci"],
                unit="m", comparator=comparator if comp == "along" else "",
                comparator_value=comparator_value if comp == "along" else "",
                clears="beats" if beats else "", **base),
            row(stage, arm, regime, f"{comp}-path p90 error", r["p90_m"], unit="m", **base),
            row(stage, arm, regime, f"{comp}-path within 0.5 m", r["within_0.5m_pct"], unit="%", **base),
            row(stage, arm, regime, f"{comp}-path within 1.0 m", r["within_1.0m_pct"], unit="%", **base),
        ]
    rows.append(row(stage, arm, regime, "along-path signed mean", rep["along_signed_mean_m"],
                    unit="m", comparator="0 = no lead or lag", comparator_value=0.0, **base))
    for k, v in (extra or {}).items():
        rows.append(row(stage, arm, regime, k.replace("_", " "), v,
                        unit="%" if k.endswith("_pct") else ("m" if k.endswith("_m") else ""), **base))
    append_rows(rows)


# --------------------------------------------------------------------------- verdicts


def verdict(name: str, per_pairing: Sequence[tuple], comparator_name: str) -> dict:
    """Both acceptance criteria, and a record of which one decided it.

    ``per_pairing`` entries are (tag, arm_value, arm_ci_hi, comparator_value), lower being better.
    """
    beats = [t for t, m, hi, c in per_pairing if c is not None and hi is not None and hi < c]
    deltas = [c - m for _t, m, _hi, c in per_pairing if c is not None]
    mean_effect = float(np.mean(deltas)) if deltas else 0.0
    same_sign = len(deltas) > 0 and (all(d > 0 for d in deltas) or all(d < 0 for d in deltas))
    n = len(deltas)
    sign_p = float(0.5 ** n) if same_sign else 1.0
    crit_interval = len(beats) > 1 and mean_effect > NOISE_FLOOR_M
    crit_sign = same_sign and n >= 12 and mean_effect > 0
    passed = bool(crit_interval or crit_sign)
    if crit_interval and crit_sign:
        used = ("both: interval on more than one pairing with mean effect over the floor, and a "
                "sign test on all twelve")
    elif crit_interval:
        used = (f"interval: beats on {len(beats)} pairings and mean effect {mean_effect:.3f} "
                f"exceeds the {NOISE_FLOOR_M} floor")
    elif crit_sign:
        used = (f"sign test: consistent in sign on all {n} pairings, p = {sign_p:.5f}, though the "
                f"mean effect {mean_effect:.3f} is below the floor")
    else:
        why = []
        if len(beats) <= 1:
            why.append(f"beats outside the interval on only {len(beats)} pairing(s), needs more than one")
        if mean_effect <= NOISE_FLOOR_M:
            why.append(f"mean effect {mean_effect:.3f} does not exceed the {NOISE_FLOOR_M} noise floor")
        if not same_sign:
            why.append("not consistent in sign across all pairings")
        used = "; ".join(why)
    out = {"name": name, "comparator": comparator_name, "passed": passed, "criterion": used,
           "beats_on": len(beats), "n_pairings": n, "mean_effect": round(mean_effect, 4),
           "sign_consistent": same_sign, "sign_test_p": sign_p, "beats_splits": beats}
    headline(f"{'PASSED' if passed else 'FAILED'} {name} vs {comparator_name}: {used}")
    return out


def verdict_by_regime(name: str, per_pairing: Sequence[tuple], comparator_name: str) -> dict:
    """The acceptance rule run TWICE, once per regime, and never on the pooled set."""
    out = {}
    for regime, sel in (("cross", is_cross), ("within", lambda k: not is_cross(k))):
        rows = [r for r in per_pairing if sel(r[0])]
        if rows:
            out[regime] = verdict(f"{name} [{regime}-day]", rows, comparator_name)
    return out


def seed_spread(values: Sequence[float]) -> dict:
    v = np.asarray(list(values), dtype=float)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return {"mean": None, "sd": None, "n": 0}
    return {"mean": float(v.mean()), "sd": float(v.std()), "min": float(v.min()),
            "max": float(v.max()), "n": int(v.size), "per_seed": [float(x) for x in v]}


# --------------------------------------------------------------------------- the ETA file


def write_eta(text: str) -> None:
    os.makedirs(REPORT_DIR, exist_ok=True)
    with open(os.path.join(REPORT_DIR, "ETA.txt"), "w", encoding="utf-8") as f:
        f.write(text.rstrip() + "\n")
