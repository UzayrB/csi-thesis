"""The lock side of the A3-clean display on the shipped all-0.5 s heads (ADDENDUM.md here, with
runs/a3_clean_2026-10-08/PREREG.md unchanged): the display decode's spread and entry, re-selected on the three development
rotations, with no A3 anywhere.

    python3 runs/a3_clean_0p5_2026-10-09/lock_side.py decode --rot B1  # every arm of the grid on one rotation
    python3 runs/a3_clean_0p5_2026-10-09/lock_side.py score            # the pre-registered selection, from the decodes

This is runs/a3_clean_2026-10-08/lock_side.py with four changes, all from the addendum: the rotation cells are the
f05r_* cells (registered in memory by reg.py, all-0.5 s heads), the record every arm is checked against is each cell's
own D05.<variant> (the shipped display settings on the new heads, decoded by build_rot.py ref), the 30 Sep SD comparison
is not repeated, and the paths point at this folder.

Each arm is decoded by `pd_decode.inner`, unchanged, the way `pd_clean.decode_inner` ran it for the rotation records
`DT0.relgateU+abstain+a2w0.25` (`pd_dt` arm 0; here D05, the same settings on the new heads): the clean reader map, the frozen A1+A2 pace, the cell's cached
posteriors, on the CPU. What differs, all of it here:
  - the output tree is this folder (`pd_cells.cfg`'s base is redirected); nothing is copied into cells/;
  - the start-of-walk readers are fitted fresh in this process and kept in memory across arms (`pd_clean`'s reader
    cache is neither read nor written);
  - the arm's display-decode settings. The spread goes in through the variant's `sd<x>` part, which only the display
    decode reads (`cfg_disp`). The entry goes in by replacing `opts["entry"]` and `opts["entry_window_m"]` in the call
    `night_track` receives with `want_display=True`, the display decode the lock and the dot read. The committed
    decision's call is passed through untouched, and every arm's committed lines are checked against the record.
An audit hook refuses any write outside this folder, and records every file opened, so the score step can show
that no A3 input was read.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time

J = os.path.join
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
OUT = J(HERE, "lock")
VARIANT = "relgateU+abstain+a2w0.25"
REF = f"D05.{VARIANT}"
#: rotation -> (cell, weight), as pd_rule.ROTS and DISPLAY_PREREG weight them; the f05r cells hold the all-0.5 s heads
ROT = {"B1": ("f05r_0102_to_B1", 2.0), "A2": ("f05r_01B1_to_02", 1.0), "A1": ("f05r_02B1_to_01", 1.0)}
EDGES = ("E_col1", "E_col5", "E_row1", "E_row5")
SD_GRID = (2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0)
ENTRIES = ("soft", "free")
WINDOWS = (1.0, None)
SHIPPED = (4.5, "soft", 1.0)


def arm_name(sd: float, entry: str, win) -> str:
    return f"sd{sd}_{entry}_w{win if win else 0}"


def parse_arm(name: str) -> tuple:
    m = re.fullmatch(r"sd([0-9.]+)_(soft|free)_w([0-9.]+)", name)
    assert m, name
    w = float(m.group(3))
    return float(m.group(1)), m.group(2), (w if w > 0 else None)


GRID = [arm_name(*SHIPPED)] + [arm_name(sd, e, w) for sd in SD_GRID for e in ENTRIES for w in WINDOWS
                               if (sd, e, w) != SHIPPED]


# ------------------------------------------------------------------------------------------ the guard

def install_guard(opened: dict) -> None:
    """Refuse any write outside this folder (Python's bytecode caches, /dev/null and the temp dir excepted)."""
    tmp = os.path.realpath(tempfile.gettempdir())
    here = os.path.realpath(HERE) + os.sep

    def allowed(p: str) -> bool:
        rp = os.path.realpath(p)
        return (rp.startswith(here) or rp == "/dev/null" or "__pycache__" in rp or rp.startswith(tmp)
                or rp.startswith("/private/var/folders/"))

    def hook(ev, args):
        if ev == "open" and args and isinstance(args[0], (str, bytes, os.PathLike)):
            p = os.path.abspath(os.fsdecode(args[0]))
            mode = args[1] if len(args) > 1 and isinstance(args[1], str) else None
            flags = args[2] if len(args) > 2 and isinstance(args[2], int) else 0
            write = (any(ch in mode for ch in "wax+") if mode is not None
                     else bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC)))
            if not (p.endswith((".py", ".pyc")) or "/site-packages/" in p or p.startswith("/opt/")):
                opened.setdefault(p, set()).add("w" if write else "r")
            if write and not allowed(p):
                raise PermissionError(f"A3C GUARD: write outside {HERE} refused: {p}")
        elif ev in ("os.mkdir", "os.remove", "os.rmdir", "shutil.rmtree", "os.truncate", "os.symlink", "os.link"):
            if args and isinstance(args[0], (str, bytes, os.PathLike)) and not allowed(os.fsdecode(args[0])):
                raise PermissionError(f"A3C GUARD: {ev} outside {HERE} refused: {os.fsdecode(args[0])}")
        elif ev == "os.rename":
            for p in args[:2]:
                if isinstance(p, (str, bytes, os.PathLike)) and not allowed(os.fsdecode(p)):
                    raise PermissionError(f"A3C GUARD: rename outside {HERE} refused: {os.fsdecode(p)}")
    sys.addaudithook(hook)


def a3_inputs(paths) -> list:
    """Every opened path that names session 03: its data, or a head trained or tested on it."""
    bad = []
    for p in paths:
        if "session_03" in p or "/room_A/03/" in p:
            bad.append(p)
            continue
        base = os.path.basename(p)
        for tr in re.findall(r"(?:^|[^0-9A-Za-z])s((?:[0-9A-Z][0-9])+)_to_s", base):
            if "03" in [tr[i:i + 2] for i in range(0, len(tr), 2)]:
                bad.append(p)
        if re.search(r"_to_s03(?![0-9])", base):
            bad.append(p)
    return sorted(set(bad))


def geometry_from_session_01() -> bool:
    """paths.load_paths' twelve lines equal the ones session 01's sidecars give alone (load_paths' own rule)."""
    import glob

    import numpy as np
    from pipeline.constrained import paths as P
    used = P.load_paths()
    own: dict = {}
    for p in sorted(glob.glob(J(REPO, "data", "room_A", "session_01", "participant_*_walk.gt.json"))):
        if "_DEMO_" in p:
            continue
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        if (d.get("participant_code") or "") not in P.SIX:
            continue
        for ps in d.get("passes", []):
            nm, c = ps.get("path_name") or "", ps.get("anchor_coords") or []
            if nm and len(c) >= 2 and nm not in own:
                own[nm] = np.asarray(c, dtype=float)
    return sorted(own) == sorted(used) and all(np.array_equal(own[k], used[k]) for k in own)


# ------------------------------------------------------------------------------------------ the decode

def decode_inner(rot: str, arms: list) -> int:
    opened = {}
    install_guard(opened)
    sys.path.insert(0, REPO)
    sys.path.insert(0, HERE)
    import reg
    assert sorted(reg.register()) == sorted(c for c, _w in ROT.values()), "the f05r cells did not register"
    cell = ROT[rot][0]
    from pipeline.constrained import pd_clean as CL
    CL.force_cpu()
    PC, c0, tfs = CL._bound(cell)
    plan = CL.plan_for(c0, tfs)
    tmap = json.loads(os.environ.get("TDR_TEST_TAG_MAP") or "{}")
    tree = c0["tree"]("half")
    for s, p in plan.items():
        if p["changed"]:
            need = [J(tree, "posteriors", f"{p['clean']}_g25_e{CL.E_POST}_s0_full.npz")] + \
                   [J(tree, "models", f"{p['clean']}_g25_e{CL.E_POST}_s0_link{li}.pt") for li in range(3)]
            miss = [x for x in need if not os.path.exists(x)]
            if miss:
                raise SystemExit(f"{cell}: the clean reader files are missing: {miss}")
            tmap[s] = p["clean"]
    os.environ["TDR_TEST_TAG_MAP"] = json.dumps(tmap)
    assert all(tfs(s) == plan[s]["clean"] for s in plan), "the clean map did not take"
    pace = CL.apply_pace()
    with open(J(REPO, "runs", "dc2_results", "final", "PACE_A1A2.json"), encoding="utf-8") as f:
        frozen = json.load(f)
    assert pace and pace["v_mean"] == frozen["v_mean"] and pace["v_sd"] == frozen["v_sd"], pace

    # the readers, fitted once in this process and kept in memory (pd_clean.install_reader_cache's keys)
    import pipeline.constrained.q4_arms as Q4
    import pipeline.constrained.u1_adapt as U1
    store, o_rows, o_a2 = {}, U1.session_rows, Q4.start_terms

    def session_rows(sessions, st, mode, cache):
        k = ("rows", tuple(sessions), mode)
        if k not in store:
            store[k] = o_rows(sessions, st, mode, cache)
        return store[k]

    def start_terms(tr_s, te_s, st, weight):
        k = ("a2", tuple(tr_s), tuple(te_s), float(weight))
        if k not in store:
            store[k] = o_a2(tr_s, te_s, st, weight)
        return store[k]
    U1.session_rows, Q4.start_terms = session_rows, start_terms

    # the output tree, and the record comparison done below rather than by pd_decode's own plumb
    stage = [None]
    orig_cfg = PC.cfg

    def cfg(cell_, cmd=None):
        c_ = orig_cfg(cell_, cmd)
        return dict(c_, base=stage[0]) if cell_ == cell else c_
    PC.cfg = cfg
    import pipeline.constrained.pd_decode as PD
    PD.plumb = lambda *a, **k: None

    # the arm's entry, in the display decode's call only
    import pipeline.constrained.night_arms as NA
    orig_nt = NA.night_track
    arm = {}
    calls = {}

    def night_track(*a, **k):
        if k.get("want_display"):
            o = a[8]
            assert o["entry"] == "soft" and o["entry_window_m"] == 1.0, "the display decode's entry is not the shipped one"
            o2 = dict(o, entry=arm["entry"], entry_window_m=arm["win"])
            a = a[:8] + (o2,) + a[9:]
            calls["display"] = calls.get("display", 0) + 1
        else:
            assert a[8]["entry"] == "soft" and a[8]["entry_window_m"] == 1.0, "the committed decode's entry changed"
            calls["committed"] = calls.get("committed", 0) + 1
        return orig_nt(*a, **k)
    NA.night_track = night_track

    ref_dir = J(c0["base"], "d3", REF)
    for name in arms:
        sd, entry, win = parse_arm(name)
        d = J(OUT, "decodes", rot, name)
        if os.path.exists(J(d, "arm.json")):
            print(f"{rot} {name}: done already, kept", flush=True)
            continue
        if os.path.exists(d):
            raise SystemExit(f"REFUSED: {d} exists without arm.json; look before removing it")
        os.makedirs(d)
        stage[0] = d
        arm.update(entry=entry, win=win)
        calls.clear()
        t0 = time.time()
        v = f"{VARIANT}+sd{sd}"
        code = PD.inner(cell, [v])
        if code:
            raise SystemExit(f"{cell} {name}: pd_decode.inner returned {code}")
        cmp_ = CL.compare(J(d, "d3", v), ref_dir)
        meta = {"rotation": rot, "cell": cell, "arm": name, "sd_scale": sd, "display_entry": entry,
                "display_entry_window_m": win, "variant": v, "ref": os.path.relpath(ref_dir, REPO),
                "against_record": cmp_, "night_track_calls": dict(calls), "pace": pace, "tag_map_used": tmap,
                "plan": plan, "readers": "fitted in this process (no cache read or written)",
                "at": time.strftime("%Y-%m-%d %H:%M:%S"), "minutes": round((time.time() - t0) / 60.0, 2)}
        print(f"[{time.strftime('%H:%M:%S')}] {rot} {name}: committed changed {cmp_['committed_changed']}, display lock "
              f"changed {cmp_['display_lock_changed']} of {cmp_['n']} ({meta['minutes']} min)", flush=True)
        if cmp_["committed_changed"]:
            raise SystemExit(f"STOP: {rot} {name} moved {cmp_['committed_changed']} committed lines; the committed "
                             f"decision must equal the record on every arm")
        if (sd, entry, win) == SHIPPED and not cmp_["EXACT"]:
            raise SystemExit(f"STOP: the plumbing check failed on {rot}: {cmp_}")
        files = {os.path.relpath(p, REPO) if p.startswith(REPO) else p: sorted(m) for p, m in sorted(opened.items())}
        flagged = a3_inputs(opened)
        # the one documented exception (pd_provenance; the 29 Sep leakage audit, note 1): paths.load_paths opens every
        # Room A sidecar but takes each line's taped endpoints from the FIRST sidecar naming it, session 01's
        side = [p for p in flagged if re.fullmatch(r".*/data/room_A/session_03/participant_[^/]+_walk\.gt\.json", p)]
        meta["a3_sidecars_opened_for_geometry"] = [os.path.relpath(p, REPO) for p in side]
        meta["geometry_equals_session_01_alone"] = geometry_from_session_01()
        meta["a3_inputs_opened"] = [p for p in flagged if p not in side]
        meta["files_opened"] = files
        if not meta["geometry_equals_session_01_alone"]:
            raise SystemExit("STOP: the line geometry is not session 01's alone")
        if meta["a3_inputs_opened"]:
            raise SystemExit(f"STOP: {rot} {name} opened inputs that name session 03: {meta['a3_inputs_opened']}")
        with open(J(d, "arm.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=1, default=str)
    return 0


def decode_outer(rot: str, arms: list) -> int:
    sys.path.insert(0, REPO)
    sys.path.insert(0, HERE)
    import reg
    reg.register()
    from pipeline.constrained import pd_cells as PC
    with open(J(REPO, "runs", "dc2_results", "final", "PACE_A1A2.json"), encoding="utf-8") as f:
        p = json.load(f)
    c = PC.cfg(ROT[rot][0], "decode")
    env = dict(PC.env_for(c, "half", "decode"), PYTHONPATH=REPO, PD_PACE_MEAN=repr(p["v_mean"]),
               PD_PACE_SD=repr(p["v_sd"]), PD_CLEAN_NOCACHE="1", PD_CLEAN_PREFIX="A3C", OMP_NUM_THREADS="1",
               MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", VECLIB_MAXIMUM_THREADS="1",
               PYTORCH_ENABLE_MPS_FALLBACK="0")
    return subprocess.call(["nice", "-n", "10", sys.executable, os.path.abspath(__file__), "decode", "--inner",
                            "--rot", rot, "--arms", *arms], cwd=REPO, env=env)


# ------------------------------------------------------------------------------------------ the score

def rows_of(rot: str, name: str) -> dict:
    d = J(OUT, "decodes", rot, name)
    with open(J(d, "arm.json"), encoding="utf-8") as f:
        v = json.load(f)["variant"]
    with open(J(d, "d3", v, "decode.json"), encoding="utf-8") as f:
        dj = json.load(f)
    with open(J(d, "d3", v, "scorerlock.json"), encoding="utf-8") as f:
        sj = json.load(f)
    (b,) = list(dj["sessions"])
    lk = {r["key"]: r for r in sj["sessions"][b]["rows"]["A"]}
    out = {}
    for r in dj["sessions"][b]["rows"]["A"]:
        L = lk[r["key"]]
        out[r["key"]] = {"true": r["true"], "committed": r["final_line"], "lock": L["display_lock"],
                         "scorer": L["scorer_lock"]}
    assert len(out) == 120, (rot, name, len(out))
    return out


def figures(rows: dict) -> dict:
    """Committed, display lock and scorer lock percentages, with the edge lines beside them."""
    import numpy as np
    k = sorted(rows)
    f = {m: 100.0 * float(np.mean([rows[x][m] == rows[x]["true"] for x in k])) for m in ("committed", "lock", "scorer")}
    f["n"] = len(k)
    f["edges"] = {}
    for e in EDGES:
        ke = [x for x in k if rows[x]["true"] == e]
        f["edges"][e] = {"n": len(ke), **{m: (100.0 * float(np.mean([rows[x][m] == e for x in ke])) if ke else None)
                                          for m in ("committed", "lock")}}
    return f


def paired(a: dict, b: dict, n_boot: int = 1000, seed: int = 0) -> dict:
    """Display lock, a minus b, paired per walk, weighted over the rotations; 95 % bootstrap with walks resampled
    within each rotation (pd_dt._paired's method, DISPLAY_PREREG section 3)."""
    import numpy as np
    rng = np.random.default_rng(seed)
    est, boots, per = 0.0, np.zeros(n_boot), {}
    W = sum(w for _c, w in ROT.values())
    for rot, (_c, w) in ROT.items():
        ks = sorted(a[rot])
        assert ks == sorted(b[rot])
        d = np.array([100.0 * (int(a[rot][k]["lock"] == a[rot][k]["true"]) - int(b[rot][k]["lock"] == b[rot][k]["true"]))
                      for k in ks])
        per[rot] = {"diff": float(d.mean()), "gained": int((d > 0).sum()), "lost": int((d < 0).sum())}
        est += w * d.mean()
        boots += w * d[rng.integers(0, len(d), size=(n_boot, len(d)))].mean(axis=1)
    lo, hi = np.percentile(boots / W, [2.5, 97.5])
    return {"diff": float(est / W), "ci95": [float(lo), float(hi)], "per_rotation": per}


def weighted(rows_by_rot: dict) -> dict:
    W = sum(w for _c, w in ROT.values())
    f = {rot: figures(rows_by_rot[rot]) for rot in ROT}
    out = {"per_rotation": f}
    for m in ("committed", "lock", "scorer"):
        out[f"{m}_weighted"] = sum(ROT[r][1] * f[r][m] for r in ROT) / W
    pooled = {f"{r}|{k}": v for r in ROT for k, v in rows_by_rot[r].items()}
    out["pooled_360"] = figures(pooled)
    return out


def score() -> int:
    have = {rot: [n for n in GRID if os.path.exists(J(OUT, "decodes", rot, n, "arm.json"))] for rot in ROT}
    miss = {rot: [n for n in GRID if n not in have[rot]] for rot in ROT}
    if any(miss.values()):
        raise SystemExit(f"REFUSED: arms not decoded yet: { {r: len(m) for r, m in miss.items()} }")
    R = {n: {rot: rows_of(rot, n) for rot in ROT} for n in GRID}
    for n in GRID:
        for rot in ROT:
            with open(J(OUT, "decodes", rot, n, "arm.json"), encoding="utf-8") as f:
                m = json.load(f)
            assert m["against_record"]["committed_changed"] == 0 and not m["a3_inputs_opened"], (rot, n)
    S = {n: weighted(R[n]) for n in GRID}
    # S1: the spread, with the entry as shipped (soft, 1.0 m); the argmax, exact ties to the smallest
    curve = {sd: S[arm_name(sd, "soft", 1.0)]["lock_weighted"] for sd in SD_GRID}
    best = max(curve.values())
    sd_star = min(sd for sd in SD_GRID if curve[sd] == best)
    # S2: soft against free at sd*, window 1.0 m held; soft ships on non-inferiority (interval contains zero or above)
    s2 = paired(R[arm_name(sd_star, "soft", 1.0)], R[arm_name(sd_star, "free", 1.0)])
    e_star = "soft" if s2["ci95"][1] >= 0.0 else "free"
    # S3: the 1.0 m window against none, at sd* and e*; the window ships only if the interval is entirely above zero
    s3 = paired(R[arm_name(sd_star, e_star, 1.0)], R[arm_name(sd_star, e_star, None)])
    w_star = 1.0 if s3["ci95"][0] > 0.0 else None
    chosen, shipped = arm_name(sd_star, e_star, w_star), arm_name(*SHIPPED)
    res = {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "label": "development evaluation, all data seen",
           "S1_spread": {"curve_lock_weighted": curve, "argmax": sd_star, "tie_rule": "exact ties to the smallest"},
           "S2_soft_entry": {"soft_minus_free": s2, "rule": "soft ships if the interval contains zero or lies above it",
                             "chosen": e_star},
           "S3_entry_window": {"window_minus_none": s3, "rule": "the 1.0 m window ships only if the interval lies "
                               "entirely above zero", "chosen": w_star},
           "A3_CLEAN_LOCK_SIDE": {"sd_scale": sd_star, "display_entry": e_star, "display_entry_window_m": w_star,
                                  "arm": chosen},
           "SHIPPED": {"sd_scale": SHIPPED[0], "display_entry": SHIPPED[1], "display_entry_window_m": SHIPPED[2],
                       "arm": shipped},
           "chosen_figures": S[chosen], "shipped_figures": S[shipped],
           "chosen_minus_shipped_lock": paired(R[chosen], R[shipped]),
           "every_arm": {n: {"lock_weighted": S[n]["lock_weighted"], "committed_weighted": S[n]["committed_weighted"],
                             "lock_pooled": S[n]["pooled_360"]["lock"]} for n in GRID}}
    out = J(OUT, "SELECTION.json")
    if os.path.exists(out):
        raise SystemExit(f"REFUSED: {out} exists")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    print(json.dumps({k: res[k] for k in ("S1_spread", "A3_CLEAN_LOCK_SIDE", "SHIPPED")}, indent=1))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["decode", "score"])
    ap.add_argument("--rot", choices=tuple(ROT))
    ap.add_argument("--arms", nargs="*", default=None)
    ap.add_argument("--inner", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "score":
        return score()
    arms = a.arms or GRID
    for n in arms:
        parse_arm(n)
    if a.inner:
        return decode_inner(a.rot, arms)
    return decode_outer(a.rot, arms)


if __name__ == "__main__":
    sys.exit(main())
