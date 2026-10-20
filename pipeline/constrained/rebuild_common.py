# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: Shared plumbing for the decoder rebuild batch.

from __future__ import annotations

import json
import os
import subprocess
import time

from pipeline.constrained.common import REPO, REPORT_DIR, RUN_DIR, read_json, status, write_json

STAGES = [
    ("rb0_preflight", 30, False),
    ("rb1_truth", 150, False),
    ("rb2_decoder", 180, False),
    ("rb2b_stride", 150, False),
    ("rb3_display", 60, False),
    ("rb4_bout", 120, False),
    ("rb5_calibrate", 150, False),
    ("rb6_crossing", 150, True),
    ("rb7_demo", 60, False),
    ("rb8_verify", 45, False),
    ("rb9_report", 60, False),
]
DEADLINE_H = 16.0
BRIEF = os.path.join(REPO, "reports", "decoder_rebuild_prompt_2026-09-17.md")
OPEN_PROBLEMS = os.path.join(REPO, "reports", "OPEN_PROBLEMS_2026-09-17.md")

V_WALK = 1.298
STRIDE_S = 1.0
WINDOW_S = 2.0
LAGS_ALLOWED = (0, 1, 2)
LAG_REFERENCE = 3


# Function stage dir.
def stage_dir(name: str) -> str:
    p = os.path.join(RUN_DIR, name)
    os.makedirs(p, exist_ok=True)
    return p


# Function results path.
def results_path(name: str) -> str:
    return os.path.join(RUN_DIR, name, "results.json")


# Function load results.
def load_results(name: str) -> dict:
    return read_json(results_path(name), {}) or {}


# Function save results.
def save_results(name: str, res: dict) -> str:
    p = results_path(name)
    write_json(p, res)
    return p


# Function now.
def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


# <N>.txt, plain text, opening PASSED or FAILED (or NOTE when neither applies, for stages that only build).
def findings(n: int, passed, text: str) -> str:
    head = "PASSED" if passed is True else ("FAILED" if passed is False else "NOTE")
    p = os.path.join(REPORT_DIR, f"FINDINGS_stage{n}.txt")
    with open(p, "w", encoding="utf-8") as f:
        f.write(f"{head}\n\n{text.strip()}\n\n({now()}, decoder rebuild batch)\n")
    status(f"wrote FINDINGS_stage{n}.txt ({head})")
    return p


# A one-line result: into status.txt via status() and appended to
def headline(text: str) -> None:
    status("HEADLINE: " + text)
    with open(os.path.join(REPORT_DIR, "HEADLINES.txt"), "a", encoding="utf-8") as f:
        f.write(f"[{now()}] {text}\n")


# From the stage list and what has results.
def refresh_eta(note: str = "") -> str:
    started = _batch_started()
    elapsed = time.time() - started
    timings = read_json(os.path.join(REPORT_DIR, "STAGE_TIMES.json"), {}) or {}
    remaining = 0.0
    rows = []
    for name, mins, optional in STAGES:
        done = os.path.exists(results_path(name))
        est = float(timings.get(name, {}).get("estimate_min", mins))
        if done:
            took = timings.get(name, {}).get("actual_min")
            rows.append(f"  {name:16s} DONE" + (f" in {took:.0f} min" if took else ""))
        else:
            remaining += est
            rows.append(f"  {name:16s} {'optional, ' if optional else ''}up to {est:.0f} min")
    finish = time.strftime("%Y-%m-%d %H:%M", time.localtime(time.time() + remaining * 60))
    deadline = time.strftime("%Y-%m-%d %H:%M", time.localtime(started + DEADLINE_H * 3600))
    lines = [
        f"Projected finish {finish} if every remaining stage runs to its cap; deadline {deadline}.",
        f"{remaining / 60:.1f} h of capped work remain, {elapsed / 3600:.1f} h elapsed.",
        f"Refreshed {now()}. {note}".strip(),
        "",
        *rows,
    ]
    p = os.path.join(REPORT_DIR, "ETA.txt")
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return p


# Function record stage time.
def record_stage_time(name: str, actual_min: float) -> None:
    p = os.path.join(REPORT_DIR, "STAGE_TIMES.json")
    d = read_json(p, {}) or {}
    d.setdefault(name, {})["actual_min"] = round(float(actual_min), 1)
    write_json(p, d)


# Function set estimate.
def set_estimate(name: str, estimate_min: float, basis: str) -> None:
    p = os.path.join(REPORT_DIR, "STAGE_TIMES.json")
    d = read_json(p, {}) or {}
    d.setdefault(name, {}).update({"estimate_min": round(float(estimate_min), 1), "basis": basis})
    write_json(p, d)


# Function batch started.
def _batch_started() -> float:
    p = os.path.join(REPORT_DIR, "BATCH_STARTED.txt")
    try:
        return float(open(p).read().strip())
    except Exception:
        t = time.time()
        with open(p, "w") as f:
            f.write(f"{t:.0f}\n")
        return t


# Function git head.
def git_head() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO,
                              capture_output=True, text=True).stdout.strip()
    except Exception:
        return "unknown"


# Whether an OPTIONAL arm fits: elapsed plus every remaining non-optional cap plus this arm's cap must leave...
def optional_budget_ok(stage_name: str) -> bool:
    started = _batch_started()
    elapsed_min = (time.time() - started) / 60
    remaining = 0.0
    this = 0.0
    for name, mins, optional in STAGES:
        if os.path.exists(results_path(name)):
            continue
        if name == stage_name:
            this = mins
        elif not optional:
            remaining += mins
    return elapsed_min + remaining + this + 30 <= DEADLINE_H * 60


# (kind, alpha) for every stage after amendment D2.
def emission_choice() -> tuple:
    s1 = load_results("rb1_truth")
    kind = ((s1.get("emission_choice") or {}).get("choice")) or "posterior"
    sweep = load_results("rb2c_alpha")
    sel = sweep.get("selection") or {}
    if sel.get("chosen_alpha") is not None:
        return kind, float(sel["chosen_alpha"]), {"source": "rb2c_alpha (D2)", **sel}
    return kind, (1.0 if kind == "scaled" else 0.0), {
        "source": "stage 1.5 fallback; the D2 sweep has not reported",
        "chosen_alpha": 1.0 if kind == "scaled" else 0.0}
