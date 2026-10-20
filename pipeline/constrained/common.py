# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: The shared contract for the constrained batch.

from __future__ import annotations

import csv
import json
import os
import random
import time
from typing import Optional, Sequence

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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

E_REG, E_POST = 20, 24

V_MEAN, V_SD, DT = 1.298, 0.123, 1.0

CSV_COLUMNS = ["stage", "arm", "regime", "train_sessions", "test_sessions", "participant", "metric",
               "value", "ci_low", "ci_high", "unit", "comparator", "comparator_value", "clears",
               "n", "seed_sd", "posthoc"]




# Torch, numpy and python, all three.
def seed_all(seed: int) -> None:
    import torch
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.backends.mps.is_available():
        torch.mps.manual_seed(seed)




# Function now.
def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


# Function status.
def status(msg: str) -> None:
    os.makedirs(REPORT_DIR, exist_ok=True)
    line = f"[{now()}] {msg}"
    print(line, flush=True)
    with open(STATUS, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# One timestamped line per resolved test.
def headline(text: str) -> None:
    os.makedirs(REPORT_DIR, exist_ok=True)
    with open(os.path.join(REPORT_DIR, "HEADLINES.txt"), "a", encoding="utf-8") as f:
        f.write(f"[{now()}] {text}\n")
    status(f"HEADLINE: {text}")


# FINDINGS_stage<N>.txt: plain text, under 400 words, opening PASSED, FAILED or INFO.
def write_findings(stage, passed: Optional[bool], body: str) -> None:
    os.makedirs(REPORT_DIR, exist_ok=True)
    head = "PASSED" if passed else ("FAILED" if passed is False else "INFO")
    words = body.split()
    if len(words) > 380:
        body = " ".join(words[:380]) + " ... (truncated at 380 words)"
    p = os.path.join(REPORT_DIR, f"FINDINGS_stage{stage}.txt")
    with open(p, "w", encoding="utf-8") as f:
        f.write(f"{head}\n\n{body}\n")
    status(f"wrote {os.path.basename(p)}")


# Function jsonable.
def _jsonable(o):
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return str(o)


# Function write json.
def write_json(path: str, obj) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=_jsonable)


# Function read json.
def read_json(path: str, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


# Function fmt.
def fmt(x, nd: int = 3) -> str:
    return "n/a" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:.{nd}f}"


# Function row.
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


# Function append rows.
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




# All nine directional cross-day splits plus the three within-day.
def pairings():
    out = [((a,), (b,)) for a in SESSIONS for b in SESSIONS if a != b]
    out += [(tuple(s for s in SESSIONS if s != h), (h,)) for h in SESSIONS]
    out += [((s,), (s,)) for s in SESSIONS]
    return out


# Function tag of.
def tag_of(tr, te, within: bool) -> str:
    return f"within_s{tr[0]}" if within else f"s{''.join(tr)}_to_s{''.join(te)}"


# Function is cross.
def is_cross(tag: str) -> bool:
    return not tag.startswith("within")


# The ONLY way an aggregate is formed.
def regime_split(per_pairing: dict, getter) -> dict:
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


# Function regime line.
def regime_line(label: str, s: dict, unit: str = "m", nd: int = 3) -> str:
    return (f"{label}: cross-day {fmt(s.get('cross'), nd)} {unit} (n={s.get('n_cross')}), "
            f"within-day {fmt(s.get('within'), nd)} {unit} (n={s.get('n_within')})")




# Cluster bootstrap over WHOLE PASSES.
def group_bootstrap(values: np.ndarray, keys: np.ndarray, stat=np.median,
                    n_boot: int = N_BOOT, seed: int = BOOT_SEED) -> tuple:
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




# Split the error into ALONG the true path and ACROSS it.
def path_error(pred: np.ndarray, true: np.ndarray, direction: np.ndarray) -> tuple:
    d = np.asarray(pred, float) - np.asarray(true, float)
    u = np.asarray(direction, float)
    n = np.linalg.norm(u, axis=1, keepdims=True)
    u = np.divide(u, n, out=np.zeros_like(u), where=n > 1e-12)
    along = np.sum(d * u, axis=1)
    cross = np.linalg.norm(d - along[:, None] * u, axis=1)
    return along, cross, np.linalg.norm(d, axis=1)


# The full positional row the standards require: along, across and total, each decomposed.
def position_report(pred: np.ndarray, true: np.ndarray, direction: np.ndarray, keys: np.ndarray,
                    tag: str = "") -> dict:
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


# Write the full decomposed set for one arm on one pairing.
def emit_position(stage: str, arm: str, tag: str, rep: dict, tr_s, te_s, comparator: str,
                  comparator_value, extra: Optional[dict] = None) -> None:
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




# Both acceptance criteria, and a record of which one decided it.
def verdict(name: str, per_pairing: Sequence[tuple], comparator_name: str) -> dict:
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


# The acceptance rule run TWICE, once per regime, and never on the pooled set.
def verdict_by_regime(name: str, per_pairing: Sequence[tuple], comparator_name: str) -> dict:
    out = {}
    for regime, sel in (("cross", is_cross), ("within", lambda k: not is_cross(k))):
        rows = [r for r in per_pairing if sel(r[0])]
        if rows:
            out[regime] = verdict(f"{name} [{regime}-day]", rows, comparator_name)
    return out


# Function seed spread.
def seed_spread(values: Sequence[float]) -> dict:
    v = np.asarray(list(values), dtype=float)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return {"mean": None, "sd": None, "n": 0}
    return {"mean": float(v.mean()), "sd": float(v.std()), "min": float(v.min()),
            "max": float(v.max()), "n": int(v.size), "per_seed": [float(x) for x in v]}




# Function write eta.
def write_eta(text: str) -> None:
    os.makedirs(REPORT_DIR, exist_ok=True)
    with open(os.path.join(REPORT_DIR, "ETA.txt"), "w", encoding="utf-8") as f:
        f.write(text.rstrip() + "\n")
