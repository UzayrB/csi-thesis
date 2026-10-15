"""capture_idboth. The DC2 identification capture from 2026-09-24: line A in BOTH directions.

Decided by Uzayr on 2026-09-24, before any Room B data: the walk back is recorded too. Each CYCLE is
one pass away from the TX (`A_fwd`, (2.5, 0) to (2.5, 5), heading N) and one pass back towards it
(`A_rev`, (2.5, 5) to (2.5, 0), heading S), in one recording, alternating, six presses per pass in
both directions (walk mode needs six; `pipeline/io/` is not edited). Odd pass ids are `A_fwd`, even
ids `A_rev`. The pre-registered analyses (PREREG_ID_DC2 addendum B, C) read the `A_fwd` passes only,
exactly as before; the `A_rev` passes and the day 1 pace blocks are additional data, declared in
`reports/PREREG_DC2_ADDENDUM_2026-09-24.md` before any Room B data existed.

It reuses the frozen `capture_idpath` rules (the six participants, the slot order, the pace order,
RX2's spot, the 30 s empty rooms) by import, and changes three things:

  - WHERE: data/room_B/identification/session_0<day>/, never data/room_B/session_*, which is
    tracking's (the DC2 tracking pipeline refuses an `_idpath_` file there);
  - WHAT: both directions, alternating, per block;
  - THE PLAN, in cycles: day 1 natural 10, slow 5, fast 5; day 2 natural 5, slow 5, fast 5. Natural
    comes first on both days, then the participant's pace order (odd P codes slow first).

COMMANDS (from the repo root, PYTHONPATH=.)
  --participant <name> --day {1,2} --block {natural,slow,fast} --height-cm --weight-kg --shoes --clothing
        --nothing-carried --nodes "RX1=..,RX2=..,RX3=.."
  --empty --position {idspot,home} --participant <name> --day {1,2} --move-time HH:MM --nodes "..."
  --plan-day --day {1,2}        --set-spot {primary,fallback}        --dry-run        --rehearsal
  --participant <name> --day <d> --block <b> --amend-count-reason "<why>"
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time
from typing import Optional

from pipeline.identify import capture_idpath as F          # the frozen rules, by import

DATA_ROOT = "data"
ID_SUBDIR = os.path.join("room_B", "identification")
DIRECTIONS = ("A_fwd", "A_rev")
PLAN = {(1, "natural"): 10, (1, "slow"): 5, (1, "fast"): 5,
        (2, "natural"): 5, (2, "slow"): 5, (2, "fast"): 5}          # CYCLES; each is two passes
PRESS_POLICY = ("every metre in the walking direction, six presses per pass, both directions: "
                "A_fwd presses at 0, 1, 2, 3, 4, 5 m; A_rev at 5, 4, 3, 2, 1, 0 m")
Refused = F.Refused


# ------------------------------------------------------------------ pure rules

def planned_cycles(day: int, block: str, override: Optional[int] = None) -> int:
    if (day, block) not in PLAN:
        raise Refused(f"refused: no {block} block on day {day}")
    return int(override) if override else PLAN[(day, block)]


def block_order(code: str) -> tuple:
    return ("natural",) + F.pace_order(code)


def check_block_order(code: str, day: int, block: str, done: set) -> None:
    """Both days: natural first, then the participant's pace order. Never overwrite."""
    if block in done:
        raise Refused(f"refused: the day {day} {block} block for {code} already exists; "
                      "a recording is never overwritten")
    order = block_order(code)
    missing = [b for b in order[:order.index(block)] if b not in done]
    if missing:
        raise Refused(f"refused: {code} walks {' then '.join(order)} on day {day}; "
                      f"{', '.join(missing)} not recorded yet")


def out_dir(day: int, rehearsal: bool = False, root: str = DATA_ROOT) -> str:
    base = F.REHEARSAL_ROOT if rehearsal else os.path.join(root, ID_SUBDIR)
    return os.path.join(base, f"session_0{day}")


def pass_plan(cycles: int) -> list:
    """(pass_id, direction) in walking order: away, back, away, back..."""
    return [(i + 1, DIRECTIONS[i % 2]) for i in range(2 * cycles)]


def recorded_blocks(d: str, code: str, day: int) -> set:
    return F.recorded_blocks(d, code, day)


def count_by_direction(gt_path: str) -> dict:
    with open(gt_path, encoding="utf-8") as f:
        passes = json.load(f).get("passes") or []
    return {k: sum(1 for p in passes if p.get("path_name") == k) for k in DIRECTIONS}


def count_status(cycles: int, got: dict, reason: Optional[str]) -> dict:
    """COMPLETE only if both directions hold the planned number of passes, else a reason is logged."""
    out = {"planned_cycles": cycles, "recorded": got}
    if all(got.get(k, 0) == cycles for k in DIRECTIONS):
        return {"status": "COMPLETE", **out}
    if reason and reason.strip():
        return {"status": "COUNT_DIFFERS_REASON_LOGGED", "reason": reason.strip(), **out}
    return {"status": "REFUSED_COUNT_DIFFERS_NO_REASON", **out}


def write_sidecar(d: str, st: str, doc: dict) -> str:
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, f"{st}.idmax.json")
    doc = {"stem": st, "capture": "capture_idboth (2026-09-24)", "paths": list(DIRECTIONS),
           "alternating": True, "press_policy": PRESS_POLICY, "operator_seat": list(F.SEAT),
           "tx": list(F.TX), **doc}
    with open(p, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1, default=str)
    return p


def set_spot(label: str, root: str = DATA_ROOT) -> dict:
    """The frozen rule, extended to this folder: the spot never changes once DC2 files exist."""
    if os.path.exists(F.SPOT_FILE):
        with open(F.SPOT_FILE, encoding="utf-8") as f:
            old = json.load(f)
        ours = glob.glob(os.path.join(root, ID_SUBDIR, "session_*", "*_idpath_*"))
        if old["label"] != label and ours:
            raise Refused(f"refused: the spot is {old['label']} and DC2 identification files exist; "
                          "it is never changed during DC2")
    return F.set_spot(label, spot_file=F.SPOT_FILE, root=root)


# ------------------------------------------------------------------ hardware

def _capture_walk(a, code, st, d, cycles, rx) -> tuple:
    """Walk mode on A_fwd and A_rev, alternating, for `cycles` cycles. Returns (gt path, started, ended)."""
    import queue
    import threading
    from pipeline.io.anchors import PATHS, CellOrder, SessionPlan
    from pipeline.io.capture_logger import resolve_nodes, run_capture
    from pipeline.io.ground_truth import (GroundTruthSession, KeyReader, PassStep, SessionConfig,
                                          load_rt_bias, refuse_overwrite)
    if refuse_overwrite(d, st, False):
        raise Refused(f"refused: {st} already exists in {d}")
    plan = pass_plan(cycles)
    steps = [PassStep(path=PATHS[name], pass_id=pid) for pid, name in plan]
    config = SessionConfig(participant_code=code, room=F.ROOM, session_id=f"0{a.day}", test=False,
                           clothing=a.clothing, footwear=a.shoes, height_cm=a.height_cm,
                           weight_kg=a.weight_kg, chair_position=f"seat {F.SEAT}, fixed for DC2",
                           rx_positions=rx, tx_position=F.TX, baseline_path="",
                           notes=f"idboth {st}", data_root=a.data_root)
    keys: "queue.Queue" = queue.Queue()
    stop = threading.Event()
    states: dict = {}
    session = GroundTruthSession(steps=steps, config=config, bias=load_rt_bias(),
                                 plan=SessionPlan(seed=0, paths=tuple(PATHS[n] for _p, n in plan)),
                                 cell_order=CellOrder(seed=0, cells=()), mode_order="idboth_A_fwd_A_rev",
                                 out_dir=d, stem=st, key_queue=keys, node_states=states,
                                 show_images=False)
    started = time.time()
    try:
        with KeyReader(keys, stop):
            run_capture(nodes=resolve_nodes(a.nodes), duration=None, out_dir=d, interval=1.0,
                        quiet_monitor=True, run_config={"ground_truth": True, "idboth": st},
                        reset=True, extra_consumers=[session], stop_when=lambda: session.finished,
                        writer_prefix=f"{st}_", timestamped_subdir=False, states_out=states)
    finally:
        if not session.finished:
            session.aborted = True
        session.close()
    return os.path.join(d, f"{st}.gt.json"), started, time.time()


# ------------------------------------------------------------------ CLI

def build_parser() -> argparse.ArgumentParser:
    p = F.build_parser()
    p.description = "DC2 identification capture, both directions on line A (2026-09-24)"
    return p


def main(argv=None) -> int:
    a = build_parser().parse_args(argv)
    try:
        if a.set_spot:
            print(json.dumps(set_spot(a.set_spot, root=a.data_root), indent=1))
            return 0
        if a.plan_day:
            if a.day not in (1, 2):
                raise Refused("refused: --plan-day needs --day 1 or 2")
            for i, (pc, c) in enumerate(F.day_order(a.day), 1):
                blocks = ", ".join(f"{b} {PLAN[(a.day, b)]}" for b in block_order(c))
                print(f"slot {i}: {pc}  (capture code {c})   cycles: {blocks}")
            return 0
        if not a.participant or a.day not in (1, 2):
            raise Refused("refused: --participant and --day are required")
        F.number(a.participant)
        label, xy = (F.spot(F.SPOT_FILE) if not a.rehearsal or os.path.exists(F.SPOT_FILE)
                     else ("primary", F.SPOTS["primary"]))
        d = out_dir(a.day, a.rehearsal, a.data_root)
        meta = {"shoes": a.shoes, "clothing": a.clothing, "nothing_carried": bool(a.nothing_carried)}
        if a.empty:
            if a.position not in ("idspot", "home"):
                raise Refused("refused: --empty needs --position idspot or home")
            st = F.stem(a.participant, a.day, f"empty_{a.position}", a.rehearsal)
            rx = F.rx_positions(a.position, xy)
            print(f"{st}: {F.EMPTY_S:.0f} s empty room, RX2 at {a.position} {rx['RX2']} -> {d}")
            if a.dry_run:
                return 0
            if glob.glob(os.path.join(d, f"{st}_RX*.bin")) or os.path.exists(os.path.join(d, f"{st}.idmax.json")):
                raise Refused(f"refused: {st} already exists in {d}; a recording is never overwritten")
            t0, t1 = F._capture_empty(a, st, d)
            write_sidecar(d, st, {"kind": "empty", "position": a.position, "rx2_xy": list(rx["RX2"]),
                                  "rx2_spot_label": label if a.position == "idspot" else "home",
                                  "move_time": a.move_time, "started": t0, "ended": t1,
                                  "duration_s": t1 - t0, "metadata": meta, "rehearsal": a.rehearsal})
            return 0
        if a.block is None:
            raise Refused("refused: --block natural, slow or fast is required")
        st = F.stem(a.participant, a.day, a.block, a.rehearsal)
        if a.amend_count_reason:
            p = os.path.join(d, f"{st}.idmax.json")
            if not os.path.exists(p):
                raise Refused(f"refused: no sidecar {p} to amend")
            with open(p, encoding="utf-8") as f:
                doc = json.load(f)
            c = doc.get("count", {})
            doc["count"] = {**count_status(c.get("planned_cycles", 0), c.get("recorded", {}),
                                           a.amend_count_reason),
                            "amended_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
            with open(p, "w", encoding="utf-8") as f:
                json.dump(doc, f, indent=1, default=str)
            print(json.dumps(doc["count"]))
            return 0
        n = planned_cycles(a.day, a.block, a.passes)
        check_block_order(a.participant, a.day, a.block, recorded_blocks(d, a.participant, a.day))
        rx = F.rx_positions("idspot", xy)
        print(f"{st}: {n} cycles = {2 * n} passes on line A, alternating away (A_fwd) and back (A_rev); "
              f"presses {PRESS_POLICY}")
        print(f"RX2 at the identification spot {label} {xy}; operator seat {F.SEAT}; -> {d}")
        if a.dry_run:
            return 0
        if a.height_cm is None or a.weight_kg is None:
            raise Refused("refused: --height-cm and --weight-kg are required, as in walk mode")
        gt, t0, t1 = _capture_walk(a, a.participant, st, d, n, rx)
        got = count_by_direction(gt) if os.path.exists(gt) else {k: 0 for k in DIRECTIONS}
        reason = a.count_reason
        if not all(got[k] == n for k in DIRECTIONS) and not reason and sys.stdin.isatty():
            reason = input(f"recorded {got} against {n} cycles. Reason (required): ")
        cs = count_status(n, got, reason)
        write_sidecar(d, st, {"kind": "walk", "day": a.day, "block": a.block, "position": "idspot",
                              "rx2_xy": list(xy), "rx2_spot_label": label, "started": t0,
                              "ended": t1, "metadata": meta, "count": cs, "rehearsal": a.rehearsal})
        if cs["status"].startswith("REFUSED"):
            print(f"REFUSED: recorded {got} against {n} cycles and no reason logged. The block is NOT "
                  "finished: log why with --amend-count-reason \"<text>\" (same --participant, --day, --block).")
            return 3
        return 0
    except Refused as e:
        print(str(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
