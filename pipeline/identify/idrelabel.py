"""idrelabel. The pre-scoring press relabel for DC2 identification (addendum E), as METADATA.

One rule, written before it was applied and frozen with addendum E, is applied to every
identification walk block on both days. It never edits a raw capture: it writes a manifest of what
it changes (`runs/identify/dc2/relabel_manifest.json`), and builds a RELABELLED SOURCE, a copy of
`data/room_B/identification/` under `runs/` in which every file is a read-only link to the capture
except the `.gt.json` files the manifest names, which are rewritten with the relabel applied. The
frozen view (`idboth_view --src <relabelled source>`) and the secondary view read that copy.

    PYTHONPATH=. python3 -m pipeline.identify.idrelabel --write-manifest    # once
    PYTHONPATH=. python3 -m pipeline.identify.idrelabel                     # build the relabelled source
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import shutil
import sys
import time

SRC = os.path.join("data", "room_B", "identification")
DST = os.path.join("runs", "identify", "dc2_src_relabelled", "identification")
MANIFEST = os.path.join("runs", "identify", "dc2", "relabel_manifest.json")
MARKER = "RELABELLED.json"
GAP_S = 0.3
PRESSES = 6
RULE = ("Where two consecutive presses in a walk block are 0.3 s apart or less, the later is an extra "
        "press and is removed, and the block's presses from that pass on are regrouped in sixes, in "
        "order. A pass left with fewer than six presses is excluded.")
RULE_ID = "idrelabel-2026-09-28"


class Refused(SystemExit):
    pass


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# ------------------------------------------------------------------ the rule, pure

def apply_rule(passes: list) -> tuple:
    """The rule on one block's passes. Returns (new passes, relabelled pass ids, excluded passes).

    A pass keeps its slot (pass_id, path_name, direction, anchor_coords); only its presses move.
    """
    ps = [dict(q) for q in sorted(passes, key=lambda z: z["t_start"])]
    relabelled, excluded = [], []
    while True:
        flat = [(k, t) for k, q in enumerate(ps) for t in q["anchor_times"]]
        close = [i for i in range(1, len(flat)) if flat[i][1] - flat[i - 1][1] <= GAP_S]
        if not close:
            break
        i = close[0]
        k0 = flat[i][0]                                   # the pass holding the extra press
        rest = [t for j, (k, t) in enumerate(flat) if k >= k0 and j != i]
        for n, k in enumerate(range(k0, len(ps))):
            chunk = rest[n * PRESSES:(n + 1) * PRESSES]
            old = ps[k]
            ps[k] = {**old, "anchor_times": chunk}
            if chunk:
                ps[k]["t_start"], ps[k]["t_end"] = chunk[0], chunk[-1]
            if chunk != old["anchor_times"] and old["pass_id"] not in relabelled:
                relabelled.append(old["pass_id"])
    keep = []
    for q in ps:
        if len(q["anchor_times"]) < PRESSES:
            excluded.append({"pass_id": q["pass_id"], "path_name": q["path_name"],
                             "presses": len(q["anchor_times"]),
                             "why": "left with fewer than six presses by the relabel rule"})
        else:
            keep.append(q)
    relabelled = [p for p in relabelled if p not in {e["pass_id"] for e in excluded}]
    return keep, relabelled, excluded


# ------------------------------------------------------------------ the manifest

def scan(src: str = SRC) -> dict:
    """Apply the rule to every walk block on every day; the manifest lists what it changes."""
    blocks = sorted(glob.glob(os.path.join(src, "session_0*", "*.gt.json")))
    changes = []
    for p in blocks:
        gt = json.load(open(p, encoding="utf-8"))
        new, rel, exc = apply_rule(gt.get("passes", []))
        if not rel and not exc:
            continue
        old = {q["pass_id"]: q for q in gt["passes"]}
        changes.append({
            "file": os.path.relpath(p, src), "sha256_before": sha256(p),
            "relabelled": [{"pass_id": q["pass_id"], "path_name": q["path_name"],
                            "before": {k: old[q["pass_id"]][k] for k in ("t_start", "t_end", "anchor_times")},
                            "after": {k: q[k] for k in ("t_start", "t_end", "anchor_times")}}
                           for q in new if q["pass_id"] in rel],
            "excluded": exc})
    return {"rule_id": RULE_ID, "rule": RULE, "gap_s": GAP_S, "written_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "src": src, "blocks_scanned": len(blocks),
            "passes_relabelled": sum(len(c["relabelled"]) for c in changes),
            "passes_excluded": sum(len(c["excluded"]) for c in changes), "changes": changes}


def write_manifest(src: str = SRC, path: str = MANIFEST) -> dict:
    if os.path.exists(path):
        raise Refused(f"refused: {path} exists; the manifest is written once and frozen")
    doc = scan(src)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(doc, open(path, "w", encoding="utf-8"), indent=1)
    return doc


# ------------------------------------------------------------------ the relabelled source

def relabelled_gt(gt: dict, change: dict) -> dict:
    """The block with the manifest's change applied, and every other field as captured."""
    from pipeline.io.ground_truth import validate_pass
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


def build(src: str = SRC, dst: str = DST, manifest: str = MANIFEST) -> dict:
    if not os.path.isdir(src):
        raise Refused(f"refused: no identification capture at {src}")
    real_data = os.path.realpath("data")
    if os.path.realpath(dst).startswith(real_data + os.sep):
        raise Refused(f"refused: the relabelled source {dst} would sit inside data/, which is read only")
    if not os.path.exists(manifest):
        raise Refused(f"refused: no manifest at {manifest}; write it once with --write-manifest")
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


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="the DC2 identification press relabel, as metadata")
    ap.add_argument("--src", default=SRC)
    ap.add_argument("--dst", default=DST)
    ap.add_argument("--manifest", default=MANIFEST)
    ap.add_argument("--write-manifest", action="store_true")
    a = ap.parse_args(argv)
    try:
        if a.write_manifest:
            doc = write_manifest(a.src, a.manifest)
            print(f"manifest at {a.manifest}: {doc['blocks_scanned']} blocks scanned, "
                  f"{doc['passes_relabelled']} passes relabelled, {doc['passes_excluded']} excluded")
            return 0
        doc = build(a.src, a.dst, a.manifest)
    except Refused as e:
        print(str(e), file=sys.stderr)
        return 2
    print(f"relabelled source at {a.dst}: {len(doc['rewritten'])} block(s) rewritten, everything else linked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
