# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: The recorded sessions, for identification without the boards: which recordings a session has and in what...

from __future__ import annotations

import json
import os
import pickle
import re
import time

import numpy as np

from pipeline.identification import engine as EN



OUT = os.path.join(EN.ENG, "replays")


# Function session recordings.
def session_recordings(session: str) -> list:
    recs = [r for r in all_recordings() if r["session"] == session]
    first = {}
    for r in recs:
        gt = json.load(open(r["stem"] + ".gt.json", encoding="utf-8"))
        first[r["stem"]] = min(float(q["t_start"]) for q in gt["passes"])
    return sorted(recs, key=lambda r: first[r["stem"]])


# The engine bank a replay is checked against: v2 (EN.bank_dir) for engine v2 models (names ending in...
def load_bank(T: float, gs: bool, v2: bool = False) -> dict:
    d = EN.bank_dir(T) if v2 else os.path.join(EN.ENG, f"bank_T{T:.1f}{'_gs' if gs else ''}")
    meta = json.load(open(os.path.join(d, "meta.json")))["passes"]
    return {"meta": meta, "X": np.load(os.path.join(d, "features.npy")), "maps": pickle.load(open(os.path.join(d, "maps.pkl"), "rb")),
            "index": {(m["session"], round(m["t_start"], 6)): i for i, m in enumerate(meta)}}


# PLAN 2.4: the detected direction if its accuracy on the identification walks is at least 95 %.
def direction_mode() -> str:
    c = json.load(open(os.path.join(EN.ENG, "checks", "checks.json")))
    return "detected" if c["direction"]["RULE_detected_used"] else "recorded"


# The session through one engine; returns the decisions (dicts), in press order.
def replay(session: str, model_dir: str, T: float, gs: bool, device: str, dmode: str, on_decision=None, realtime=None) -> list:
    from pipeline.io.serial_capture import read_capture_file
    eng = EN.Engine(model_dir, T=T, amp_norm=gs, device=device)
    out = []
    for rec in session_recordings(session):
        layout = "id_spot" if rec["kind"] == "idcap" else "home"
        eng.new_recording(layout)
        fr = {L: read_capture_file(f"{rec['stem']}_{L}.bin")[1] for L in EN.LINKS}
        pos = {L: 0 for L in EN.LINKS}
        gt = json.load(open(rec["stem"] + ".gt.json", encoding="utf-8"))
        for q in sorted(gt["passes"], key=lambda z: z["t_start"]):
            t0 = float(q["t_start"])
            lim = t0 + T + EN.CAP_S
            for L in EN.LINKS:
                n = int(np.searchsorted(fr[L]["t_mono"], lim, side="right"))
                eng.push(L, fr[L][pos[L]:n])
                pos[L] = n
            known = None if (rec["kind"] == "idcap" and dmode == "detected") else q["path_name"]
            eng.press(t0, path=known, info={"session": session, "t_start": t0, "kind": rec["kind"], "block": rec["block"],
                                            "path": q["path_name"], "t_end": float(q["t_end"])})
            for d in eng.poll(lim):
                out.append(d)
                if on_decision:
                    on_decision(d)
    out_upd = list(eng.session.update_s) if eng.session is not None else []
    for d, u in zip(out, out_upd):
        d["update_s"] = u
    return out



SIX = ("PA5", "PA1", "PA2", "PA3", "PA4", "PA6")


RETIRED = ("retired_1", "retired_2")
PINDEX = {p: f"P{i + 1}" for i, p in enumerate(SIX)}


# Function anon.
def anon(name: str) -> str:
    return PINDEX.get(str(name), "P?")


ROOT = os.path.join("runs", "identify", "idmax")
FEAT = os.path.join(ROOT, "features")
READS_LOG = os.path.join(ROOT, "READS.log")
_ALLOWED = re.compile(r"^participant_(%s)(_TEST)?_walk$" % "|".join(SIX))


# Function stem allowed.
def stem_allowed(stem: str) -> bool:
    return bool(_ALLOWED.match(stem)) and "DEMO" not in stem and "free" not in stem.lower() \
        and not any(r in stem for r in RETIRED)


# Function assert allowed.
def assert_allowed(path: str) -> None:
    base = os.path.basename(path)
    stem = re.sub(r"(_RX\d)?\.(bin|gt\.json|meta\.json|npz)$", "", base)
    if not stem_allowed(stem):
        raise PermissionError(f"IDMAX refuses to read {path}: not one of the six walk recordings")
    os.makedirs(ROOT, exist_ok=True)
    with open(READS_LOG, "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')}\t{os.getpid()}\t{path}\n")


# The eighteen (session, stem) walk recordings, each asserted allowed.
def idmax_recordings() -> list:
    from pipeline.tracking.settings import idmax_recordings as _r
    out = [(s, st) for s, st in _r() if stem_allowed(st)]
    assert len(out) == 18, f"expected 18 walk recordings, found {len(out)}"
    return out


# Function participant of.
def participant_of(stem: str) -> str:
    return stem.replace("participant_", "").split("_")[0]


# Every pass with its presses, 1 m anchors, walk_edge window span and metadata.
def pass_inventory() -> list:
    p = os.path.join(ROOT, "inventory.json")
    if os.path.exists(p):
        return json.load(open(p, encoding="utf-8"))
    rows = []
    for s, stem in idmax_recordings():
        gtp = os.path.join("data", "room_A", f"session_{s}", f"{stem}.gt.json")
        mp = os.path.join("runs", "constrained", "windows_s1.0_roomA", "room_A", f"session_{s}", f"{stem}.meta.json")
        assert_allowed(gtp)
        assert_allowed(mp)
        gt = json.load(open(gtp, encoding="utf-8"))
        wins = json.load(open(mp, encoding="utf-8"))["windows"]
        who = participant_of(stem)
        ps = sorted(gt["passes"], key=lambda q: q["t_start"])
        for order, q in enumerate(ps):
            t = [w["t_start_abs"] for w in wins if w.get("pass_id") == q["pass_id"]]
            coords = np.asarray(q["anchor_coords"], float)
            length = float(np.sum(np.linalg.norm(np.diff(coords, axis=0), axis=1)))
            dur = float(q["t_end"] - q["t_start"])
            rows.append({
                "session": s, "stem": stem, "participant": who, "anon": anon(who),
                "rec": f"{s}|{anon(who)}", "pass_id": int(q["pass_id"]), "order": order,
                "line": q["path_name"], "base_line": q["path_name"].split("_")[0]
                if not q["path_name"].startswith("E_") else q["path_name"],
                "direction": ("rev" if q["path_name"].endswith("_rev") else
                              "fwd" if q["path_name"].endswith("_fwd") else "edge"),
                "t_start_press": float(q["t_start"]), "t_end_press": float(q["t_end"]),
                "anchor_times": [float(x) for x in q["anchor_times"]],
                "walk_edge_lo": float(min(t)) if t else None,
                "walk_edge_hi": float(max(t)) if t else None,
                "prev_end_press": float(ps[order - 1]["t_end"]) if order else None,
                "next_start_press": float(ps[order + 1]["t_start"]) if order + 1 < len(ps) else None,
                "line_length_m": length, "duration_s": dur,
                "speed_m_s": length / dur if dur > 0 else None,
                "flagged": bool(q.get("flagged")),
            })
    os.makedirs(ROOT, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=0)
    return rows


# Function pass key.
def pass_key(r: dict) -> str:
    return f"{r['session']}|{r['anon']}|{r['pass_id']}"



SRC = os.path.join("data", "room_B", "identification")


DST = os.path.join("runs", "identify", "dc2_src_relabelled", "identification")
MANIFEST = os.path.join("runs", "identify", "dc2", "relabel_manifest.json")
MARKER = "RELABELLED.json"
RULE = ("Where two consecutive presses in a walk block are 0.3 s apart or less, the later is an extra "
        "press and is removed, and the block's presses from that pass on are regrouped in sixes, in "
        "order. A pass left with fewer than six presses is excluded.")
RULE_ID = "idrelabel-2026-09-28"


# Class Refused.
class Refused(SystemExit):
    pass


# Function sha256.
def sha256(path: str) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# The block with the manifest's change applied, and every other field as captured.
def relabelled_gt(gt: dict, change: dict) -> dict:
    after = {r["pass_id"]: r["after"] for r in change["relabelled"]}
    gone = {e["pass_id"] for e in change["excluded"]}
    passes = []
    for q in gt["passes"]:
        if q["pass_id"] in gone:
            continue
        if q["pass_id"] in after:
            flagged, flags = validate_pass(after[q["pass_id"]]["anchor_times"], q["anchor_coords"])
            q = {**q, **after[q["pass_id"]], "flagged": flagged, "flags": flags,
                 "relabel": {"rule_id": RULE_ID, "before": {k: q[k] for k in ("t_start", "t_end", "anchor_times",
                                                                               "flagged", "flags")}}}
        passes.append(q)
    return {**gt, "passes": passes, "n_passes": len(passes),
            "n_flagged": sum(bool(q.get("flagged")) for q in passes),
            "relabel": {"rule_id": RULE_ID, "rule": RULE, "excluded": change["excluded"],
                        "sha256_before": change["sha256_before"]}}


# Function build.
def build(src: str = SRC, dst: str = DST, manifest: str = MANIFEST) -> dict:
    import glob
    import shutil
    import time
    if not os.path.isdir(src):
        raise Refused(f"refused: no identification capture at {src}")
    real_data = os.path.realpath("data")
    if os.path.realpath(dst).startswith(real_data + os.sep):
        raise Refused(f"refused: the relabelled source {dst} would sit inside data/, which is read only")
    if not os.path.exists(manifest):
        raise Refused(f"refused: no manifest at {manifest}")
    man = json.load(open(manifest, encoding="utf-8"))
    if man.get("rule_id") != RULE_ID:
        raise Refused(f"refused: the manifest's rule {man.get('rule_id')} is not {RULE_ID}")
    by_file = {c["file"]: c for c in man["changes"]}
    for f, c in by_file.items():
        got = sha256(os.path.join(src, f))
        if got != c["sha256_before"]:
            raise Refused(f"refused: {f} changed since the manifest was written ({got[:12]} against "
                          f"{c['sha256_before'][:12]})")
    if os.path.exists(dst):
        if not os.path.exists(os.path.join(dst, MARKER)):
            raise Refused(f"refused: {dst} exists and was not built here; remove it by hand")
        shutil.rmtree(dst)
    os.makedirs(dst)
    for p in sorted(glob.glob(os.path.join(src, "session_0*", "*"))):
        rel = os.path.relpath(p, src)
        out = os.path.join(dst, rel)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        if rel in by_file:
            gt = json.load(open(p, encoding="utf-8"))
            json.dump(relabelled_gt(gt, by_file[rel]), open(out, "w", encoding="utf-8"), indent=2)
        else:
            os.symlink(os.path.abspath(p), out)
    doc = {"built_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "src": os.path.abspath(src),
           "manifest": manifest, "manifest_sha256": sha256(manifest), "rewritten": sorted(by_file)}
    json.dump(doc, open(os.path.join(dst, MARKER), "w", encoding="utf-8"), indent=1)
    return doc


N_ANCHORS = 6
MAX_SPEED_MPS = 4.0
MIN_SPEED_MPS = 0.3


# (flagged, reasons) for a pass: missed or spurious presses, judged by the speed between anchors.
def validate_pass(anchor_times, anchor_coords) -> tuple:
    flags = []
    if len(anchor_times) != N_ANCHORS:
        flags.append(f"closed with {len(anchor_times)} anchors, expected {N_ANCHORS}")
        return True, flags
    for i in range(len(anchor_times) - 1):
        dt = anchor_times[i + 1] - anchor_times[i]
        ax, ay = anchor_coords[i]
        bx, by = anchor_coords[i + 1]
        dist = ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5
        if dt <= 0:
            flags.append(f"anchors {i + 1}->{i + 2} out of order (dt={dt:.3f}s)")
            continue
        speed = dist / dt
        if speed > MAX_SPEED_MPS:
            flags.append(f"anchors {i + 1}->{i + 2}: {speed:.1f} m/s implies a MISSED press")
        elif speed < MIN_SPEED_MPS:
            flags.append(f"anchors {i + 1}->{i + 2}: {speed:.2f} m/s implies a SPURIOUS press")
    return bool(flags), flags


TRACK = {"A1": ("data/room_A/session_01", "_walk"), "A2": ("data/room_A/session_02", "_walk"),
         "A3": ("data/room_A/session_03", "_TEST_walk"), "B1": ("data/room_B/session_B1", "_walk"),
         "B2": ("data/room_B/session_B2", "_walk")}
IDCAP = {"B1": os.path.join(DST, "session_01"), "B2": os.path.join(DST, "session_02")}


# Build the relabelled identification source from data/ and the relabel manifest the first time it is needed.
def ensure_relabelled() -> None:
    if os.path.exists(os.path.join(DST, MARKER)):
        return
    try:
        doc = build()
    except Refused as e:
        raise SystemExit(f"REFUSED: the identification recordings are needed in data/room_B/identification ({e})")
    print(f"built {DST} from data/: {len(doc['rewritten'])} block(s) relabelled, every other file linked", flush=True)


# Function all recordings.
def all_recordings() -> list:
    ensure_relabelled()
    out = []
    for ses, (d, suf) in TRACK.items():
        for name in SIX:
            stem = os.path.join(d, f"participant_{name}{suf}")
            assert os.path.exists(stem + ".gt.json"), stem
            out.append({"session": ses, "room": ses[0], "kind": "track", "block": "track", "name": name, "stem": stem})
    for ses, d in IDCAP.items():
        day = ses[1]
        for name in SIX:
            for blk in ("natural", "slow", "fast"):
                stem = os.path.join(d, f"participant_{name}_idpath_d{day}_{blk}")
                assert os.path.exists(stem + ".gt.json"), stem
                out.append({"session": ses, "room": "B", "kind": "idcap", "block": blk, "name": name, "stem": stem})
    for r in out:
        assert "DEMO_free" not in r["stem"] and "_C_walk" not in r["stem"]
    return out



MAC = "1a:00:00:00:00:00"


LINKS = ("RX1", "RX2", "RX3")
INT_FIELDS = ("pkt_id", "rssi", "rate", "sig_mode", "mcs", "bandwidth", "smoothing", "not_sounding", "aggregation",
              "stbc", "fec_coding", "sgi", "noise_floor", "ampdu_cnt", "channel", "secondary_channel", "local_timestamp",
              "ant", "sig_len", "rx_format", "first_word")


# One capture frame as the CsiRecord the serial reader would have produced for it.
def record_of(node: str, f) -> object:
    from pipeline.io.serial_capture import CSI_LEN, CsiRecord
    kw = {k: int(f[k]) for k in INT_FIELDS}
    return CsiRecord(node_id=node, t_mono=float(f["t_mono"]), t_host=float(f["t_host"]), mac=MAC, csi_len=CSI_LEN,
                     data=np.asarray(f["data"], np.int8).copy(), compensate_gain=float(f["gain"]), **kw)


# A recorded session: its recordings in the harness's order, each with its frames, presses, routes and truth.
class RecordedSource:

    # Sets up the object.
    def __init__(self, session: str):
        from pipeline.tracking.settings import PA_OF
        self.session = session
        self.recs = []
        for r in session_recordings(session):
            gt = json.load(open(r["stem"] + ".gt.json", encoding="utf-8"))
            passes = sorted(gt["passes"], key=lambda q: q["t_start"])
            self.recs.append({"stem": r["stem"], "kind": r["kind"], "block": r["block"], "name": PA_OF[r["name"]],
                              "code": anon(r["name"]), "label": f"{r['kind']}_{r['block']}_{PA_OF[r['name']]}",
                              "presses": [float(q["t_start"]) for q in passes],
                              "routes": [q["path_name"] for q in passes],
                              "layout": "id_spot" if r["kind"] == "idcap" else "home"})

    # A recording by its index, its label (kind_block_name) or a substring of its stem.
    def index_of(self, which: str) -> int:
        if which.isdigit():
            return int(which)
        from pipeline.tracking.settings import name_text
        hits = [i for i, r in enumerate(self.recs) if which == r["label"] or name_text(which) in r["stem"]]
        if len(hits) != 1:
            raise SystemExit(f"--from {which!r} matches {len(hits)} recordings; labels: {[r['label'] for r in self.recs]}")
        return hits[0]

    # (stream time, [records]) in one global order by recorded t_mono (ties: RX1, RX2, RX3, then file order).
    def batches(self, rec: dict):
        from pipeline.io.serial_capture import read_capture_file
        fr = {L: read_capture_file(f"{rec['stem']}_{L}.bin")[1] for L in LINKS}
        tm = np.concatenate([np.asarray(fr[L]["t_mono"], np.float64) for L in LINKS])
        li = np.concatenate([np.full(len(fr[L]), k) for k, L in enumerate(LINKS)])
        ix = np.concatenate([np.arange(len(fr[L])) for L in LINKS])
        order = np.lexsort((ix, li, tm))
        tm, li, ix = tm[order], li[order], ix[order]
        cut = np.flatnonzero(np.diff(tm) > 0) + 1
        for a, b in zip(np.r_[0, cut], np.r_[cut, len(tm)]):
            yield float(tm[a]), [record_of(LINKS[li[j]], fr[LINKS[li[j]]][ix[j]]) for j in range(a, b)]


# Feed the session through the consumer, the rig's way: handle each record, space-bar KeyEvents at the...
def stream(consumer, source: RecordedSource, speed="max", start: int = 0, play=None, log=None, until: int = None) -> dict:
    from pipeline.io.boards import KeyEvent
    info = {"recordings": [], "presses": 0}
    for k, rec in enumerate(source.recs):
        if until is not None and k > until:
            break
        shown = k >= start and (play is None or play(rec))
        consumer.new_stream(rec["layout"], display=shown,
                            routes=None if rec["kind"] == "idcap" else dict(zip(rec["presses"], rec["routes"])))
        for t in rec["presses"]:
            consumer.set_truth(t, rec["name"])
        presses = list(rec["presses"])
        wall0, first = None, None
        for tau, recs in source.batches(rec):
            while presses and presses[0] <= tau:
                t = presses.pop(0)
                consumer.keys.put(KeyEvent(" ", t, t))
                info["presses"] += 1
            for r in recs:
                consumer.handle(r)
            if shown and speed != "max":
                if wall0 is None:
                    wall0, first = time.time(), tau
                lag = (tau - first) / float(speed) - (time.time() - wall0)
                if lag > 0:
                    time.sleep(lag)
            consumer.tick(tau)
        for t in presses:
            consumer.keys.put(KeyEvent(" ", t, t))
            info["presses"] += 1
        consumer.end_stream()
        info["recordings"].append({"label": rec["label"], "shown": shown, "walks": len(rec["presses"])})
        if log:
            log(f"{time.strftime('%H:%M:%S')} {rec['label']}: {len(rec['presses'])} walks{' (shown)' if shown else ''}")
    return info
