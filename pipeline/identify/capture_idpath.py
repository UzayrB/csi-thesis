"""capture_idpath. The DC2 identification capture wrapper, per-person slot design (2026-09-23e).

It drives the EXISTING `walk` mode of `pipeline/io/ground_truth.py` on one line, `A_fwd` (line A,
x = 2.5, walked away from the TX, direction N), without editing anything in `pipeline/io/`. How
walk mode works, and why presses fall at every metre, is in `reports/CAPTURE_INTERFACE_NOTES.md`.

COMMANDS
  --participant <code> --day {1,2} --block {natural,slow,fast} [--passes N]
        identification walks; 10 natural on day 1, 5 per block on day 2; slow/fast refused on day 1;
        on day 2 natural comes first, then slow before fast (odd P-codes) or fast before slow (even)
  --empty --position {idspot,home} --participant <code> --day {1,2} [--move-time HH:MM]
        30 s of empty room, RX2 at the identification spot or at home
  --plan-day --day {1,2}
        the participant order: day 1 P1 to P6 as on the sheet, day 2 reversed
  --set-spot {primary,fallback}
        records RX2's identification spot, (2.0, -0.5) or (1.5, -0.5), once, at the rehearsal
  --rehearsal   writes to data/rehearsal_idpath/ with a REHEARSAL infix the scorer refuses
  --dry-run     prints what would be recorded, touches no hardware

Every recording gets `<stem>.idmax.json`: RX2's position with coordinates, times, the metadata
line, the operator seat, and the planned and recorded pass counts.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time
from typing import Optional

from pipeline.identify.common import RETIRED, SIX

DATA_ROOT = "data"
ROOM = "B"
REHEARSAL_ROOT = os.path.join("data", "rehearsal_idpath")
SPOT_FILE = os.path.join("runs", "identify", "dc2", "rx2_spot.json")
SPOTS = {"primary": (2.0, -0.5), "fallback": (1.5, -0.5)}
TX = (2.5, -0.5)
RX1, RX2_HOME, RX3 = (2.5, 5.5), (-0.5, 2.5), (5.5, 2.5)
SEAT = (-1.0, 0.5)
PATH = "A_fwd"
PLAN = {(1, "natural"): 10, (2, "natural"): 5, (2, "slow"): 5, (2, "fast"): 5}
EMPTY_S = 30.0
PRESS_POLICY = "every metre, 0 m to 5 m, six presses per pass (walk mode closes a pass on the sixth)"


class Refused(SystemExit):
    pass


# ------------------------------------------------------------------ pure rules

def number(code: str) -> int:
    if code in RETIRED or code not in SIX:
        raise Refused(f"refused: {code!r} is not one of the six DC2 participants")
    return SIX.index(code) + 1


def day_order(day: int) -> list:
    """(P-code, capture code) in slot order. Day 2 is day 1 reversed."""
    order = [(f"P{i + 1}", c) for i, c in enumerate(SIX)]
    return order if day == 1 else list(reversed(order))


def pace_order(code: str) -> tuple:
    return ("slow", "fast") if number(code) % 2 == 1 else ("fast", "slow")


def planned_passes(day: int, block: str, override: Optional[int] = None) -> int:
    if (day, block) not in PLAN:
        raise Refused(f"refused: no {block} block on day {day} (slow and fast are day 2 only)")
    return int(override) if override else PLAN[(day, block)]


def stem(code: str, day: int, what: str, rehearsal: bool = False) -> str:
    return f"participant_{code}_idpath_d{day}_{what}" + ("_REHEARSAL" if rehearsal else "")


def out_dir(day: int, rehearsal: bool = False, root: str = DATA_ROOT) -> str:
    base = REHEARSAL_ROOT if rehearsal else os.path.join(root, f"room_{ROOM}")
    return os.path.join(base, f"session_0{day}")


def recorded_blocks(d: str, code: str, day: int) -> set:
    got = set()
    for p in glob.glob(os.path.join(d, f"participant_{code}_idpath_d{day}_*.gt.json")):
        got.add(os.path.basename(p).split(f"_d{day}_")[1].split(".")[0].replace("_REHEARSAL", ""))
    return got


def check_block_order(code: str, day: int, block: str, done: set) -> None:
    """Day 2: natural first, then the participant's pace order. Refuse anything else."""
    if day != 2:
        return
    first, second = pace_order(code)
    if block in (first, second) and "natural" not in done:
        raise Refused("refused: on day 2 the 5 natural passes come before the pace blocks")
    if block == second and first not in done:
        raise Refused(f"refused: {code} walks {first} before {second} on day 2")
    if block in done:
        raise Refused(f"refused: the day {day} {block} block for {code} already exists; "
                      "a recording is never overwritten")


def spot(spot_file: str = SPOT_FILE) -> tuple:
    if not os.path.exists(spot_file):
        raise Refused("refused: RX2's identification spot has not been recorded. Decide it at the "
                      "rehearsal and run --set-spot primary (or fallback)")
    d = json.load(open(spot_file, encoding="utf-8"))
    return d["label"], tuple(d["xy"])


def set_spot(label: str, spot_file: str = SPOT_FILE, root: str = DATA_ROOT) -> dict:
    if label not in SPOTS:
        raise Refused(f"refused: spot must be one of {sorted(SPOTS)}")
    if os.path.exists(spot_file):
        old = json.load(open(spot_file, encoding="utf-8"))
        dc2 = glob.glob(os.path.join(root, f"room_{ROOM}", "session_*", "*_idpath_*"))
        if old["label"] != label and dc2:
            raise Refused(f"refused: the spot is {old['label']} and DC2 identification files exist; "
                          "it is never changed during DC2")
    os.makedirs(os.path.dirname(spot_file), exist_ok=True)
    d = {"label": label, "xy": list(SPOTS[label]), "set_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
         "rule": "decided at the rehearsal from whether the 4 m cable reaches with slack; never changed during DC2"}
    json.dump(d, open(spot_file, "w", encoding="utf-8"), indent=1)
    return d


def rx_positions(position: str, spot_xy: tuple) -> dict:
    return {"RX1": RX1, "RX2": tuple(spot_xy) if position == "idspot" else RX2_HOME, "RX3": RX3}


def count_status(planned: int, recorded: int, reason: Optional[str]) -> dict:
    """A block finishes only if its count matches the plan, or a reason is logged."""
    if recorded == planned:
        return {"status": "COMPLETE", "planned": planned, "recorded": recorded}
    if reason and reason.strip():
        return {"status": "COUNT_DIFFERS_REASON_LOGGED", "planned": planned, "recorded": recorded,
                "reason": reason.strip()}
    return {"status": "REFUSED_COUNT_DIFFERS_NO_REASON", "planned": planned, "recorded": recorded}


def write_sidecar(d: str, st: str, doc: dict) -> str:
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, f"{st}.idmax.json")
    doc = {"stem": st, "path": PATH, "press_policy": PRESS_POLICY, "operator_seat": list(SEAT),
           "tx": list(TX), **doc}
    json.dump(doc, open(p, "w", encoding="utf-8"), indent=1, default=str)
    return p


# ------------------------------------------------------------------ hardware

def _capture_walk(a, code, st, d, n, rx) -> tuple:
    """Run walk mode on A_fwd for n passes. Returns (recorded passes, started, ended)."""
    import queue
    import threading
    from pipeline.io.anchors import PATHS, CellOrder, SessionPlan
    from pipeline.io.capture_logger import resolve_nodes, run_capture
    from pipeline.io.ground_truth import (GroundTruthSession, KeyReader, PassStep, SessionConfig,
                                          load_rt_bias, refuse_overwrite)
    if refuse_overwrite(d, st, False):
        raise Refused(f"refused: {st} already exists in {d}")
    path = PATHS[PATH]
    steps = [PassStep(path=path, pass_id=i + 1) for i in range(n)]
    config = SessionConfig(participant_code=code, room=ROOM, session_id=f"0{a.day}", test=False,
                           clothing=a.clothing, footwear=a.shoes, height_cm=a.height_cm,
                           weight_kg=a.weight_kg, chair_position=f"seat {SEAT}, fixed for DC2",
                           rx_positions=rx, tx_position=TX, baseline_path="",
                           notes=f"idpath {st}", data_root=a.data_root)
    keys: "queue.Queue" = queue.Queue()
    stop = threading.Event()
    states: dict = {}
    session = GroundTruthSession(steps=steps, config=config, bias=load_rt_bias(),
                                 plan=SessionPlan(seed=0, paths=tuple(path for _ in range(n))),
                                 cell_order=CellOrder(seed=0, cells=()), mode_order="idpath_A_fwd",
                                 out_dir=d, stem=st, key_queue=keys, node_states=states,
                                 show_images=False)
    started = time.time()
    try:
        with KeyReader(keys, stop):
            run_capture(nodes=resolve_nodes(a.nodes), duration=None, out_dir=d, interval=1.0,
                        quiet_monitor=True, run_config={"ground_truth": True, "idpath": st},
                        reset=True, extra_consumers=[session], stop_when=lambda: session.finished,
                        writer_prefix=f"{st}_", timestamped_subdir=False, states_out=states)
    finally:
        if not session.finished:
            session.aborted = True
        session.close()
    return len(session.passes), started, time.time()


def _capture_empty(a, st, d) -> tuple:
    from pipeline.io.capture_logger import resolve_nodes, run_capture
    started = time.time()
    run_capture(nodes=resolve_nodes(a.nodes), duration=EMPTY_S, out_dir=d, interval=1.0,
                run_config={"ground_truth": False, "idpath_empty": st}, reset=True,
                writer_prefix=f"{st}_", timestamped_subdir=False)
    return started, time.time()


# ------------------------------------------------------------------ CLI

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="DC2 identification capture, slot design (23e)")
    p.add_argument("--participant")
    p.add_argument("--day", type=int, choices=(1, 2))
    p.add_argument("--block", choices=("natural", "slow", "fast"))
    p.add_argument("--passes", type=int, default=None)
    p.add_argument("--empty", action="store_true")
    p.add_argument("--position", choices=("idspot", "home"))
    p.add_argument("--move-time", default="", help="HH:MM when RX2 was moved to this position")
    p.add_argument("--plan-day", action="store_true")
    p.add_argument("--set-spot", choices=tuple(SPOTS))
    p.add_argument("--rehearsal", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--count-reason", default=None)
    p.add_argument("--amend-count-reason", default=None,
                   help="log a reason for an EXISTING block whose pass count differs from the plan")
    p.add_argument("--shoes", default="")
    p.add_argument("--clothing", default="")
    p.add_argument("--nothing-carried", action="store_true")
    p.add_argument("--height-cm", type=float, default=None)
    p.add_argument("--weight-kg", type=float, default=None)
    p.add_argument("--nodes", default=None)
    p.add_argument("--data-root", default=DATA_ROOT)
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
            for i, (pc, c) in enumerate(day_order(a.day), 1):
                p1, p2 = pace_order(c)
                extra = f"   day 2: natural, then {p1}, then {p2}" if a.day == 2 else ""
                print(f"slot {i}: {pc}  (capture code {c}){extra}")
            return 0
        if not a.participant or a.day not in (1, 2):
            raise Refused("refused: --participant and --day are required")
        number(a.participant)
        label, xy = spot() if not a.rehearsal or os.path.exists(SPOT_FILE) else ("primary", SPOTS["primary"])
        d = out_dir(a.day, a.rehearsal, a.data_root)
        meta = {"shoes": a.shoes, "clothing": a.clothing, "nothing_carried": bool(a.nothing_carried)}
        if a.empty:
            if a.position not in ("idspot", "home"):
                raise Refused("refused: --empty needs --position idspot or home")
            st = stem(a.participant, a.day, f"empty_{a.position}", a.rehearsal)
            rx = rx_positions(a.position, xy)
            print(f"{st}: {EMPTY_S:.0f} s empty room, RX2 at {a.position} {rx['RX2']} -> {d}")
            if a.dry_run:
                return 0
            t0, t1 = _capture_empty(a, st, d)
            write_sidecar(d, st, {"kind": "empty", "position": a.position, "rx2_xy": list(rx["RX2"]),
                                  "rx2_spot_label": label if a.position == "idspot" else "home",
                                  "move_time": a.move_time, "started": t0, "ended": t1,
                                  "duration_s": t1 - t0, "metadata": meta, "rehearsal": a.rehearsal})
            return 0
        if a.block is None:
            raise Refused("refused: --block natural, slow or fast is required")
        if a.amend_count_reason:
            st = stem(a.participant, a.day, a.block, a.rehearsal)
            p = os.path.join(d, f"{st}.idmax.json")
            if not os.path.exists(p):
                raise Refused(f"refused: no sidecar {p} to amend")
            doc = json.load(open(p, encoding="utf-8"))
            c = doc.get("count", {})
            doc["count"] = {**count_status(c.get("planned", 0), c.get("recorded", 0), a.amend_count_reason),
                            "amended_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
            json.dump(doc, open(p, "w", encoding="utf-8"), indent=1, default=str)
            print(json.dumps(doc["count"]))
            return 0
        n = planned_passes(a.day, a.block, a.passes)
        check_block_order(a.participant, a.day, a.block, recorded_blocks(d, a.participant, a.day))
        st = stem(a.participant, a.day, a.block, a.rehearsal)
        rx = rx_positions("idspot", xy)
        print(f"{st}: {n} passes on {PATH} (line A, away from the TX), presses {PRESS_POLICY}")
        print(f"RX2 at the identification spot {label} {xy}; operator seat {SEAT}; -> {d}")
        if a.dry_run:
            return 0
        if a.height_cm is None or a.weight_kg is None:
            raise Refused("refused: --height-cm and --weight-kg are required, as in walk mode")
        got, t0, t1 = _capture_walk(a, a.participant, st, d, n, rx)
        reason = a.count_reason
        if got != n and not reason and sys.stdin.isatty():
            reason = input(f"{got} passes recorded against a plan of {n}. Reason (required): ")
        cs = count_status(n, got, reason)
        write_sidecar(d, st, {"kind": "walk", "day": a.day, "block": a.block, "position": "idspot",
                              "rx2_xy": list(xy), "rx2_spot_label": label, "started": t0,
                              "ended": t1, "metadata": meta, "count": cs, "rehearsal": a.rehearsal})
        if cs["status"].startswith("REFUSED"):
            print(f"REFUSED: {got} passes against a plan of {n} and no reason logged. The block is "
                  "NOT finished: log why with --amend-count-reason \"<text>\" (same --participant, "
                  "--day, --block), or the scorer's layout check will reject it.")
            return 3
        return 0
    except Refused as e:
        print(str(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
