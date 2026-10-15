"""pd_report: per-pass rows, accuracy and paired intervals for the DC2 results batch (items 2 to 5).

    python3 -m pipeline.constrained.pd_report plumb        # the harness plumbing check (plumb_A3)
    python3 -m pipeline.constrained.pd_report summary      # every cell, item 2 and the comparators

Accuracy and paired intervals are the confirmatory pipeline's own (`dc2_pipeline._acc`, `_paired`,
bootstrap over passes), imported unchanged, so items 2 to 4 are measured one way. Every row is keyed
session|stem|pass_id, so any two sources pair pass by pass on the same test passes.
"""

from __future__ import annotations

import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
J = os.path.join
RES = J(REPO_ROOT, "runs", "dc2_results")
DC2 = J(REPO_ROOT, "runs", "constrained", "dc2_room_B_s0.5_pressalign")
D6 = J(REPO_ROOT, "runs", "constrained", "fh", "d6_lock_commit", "rows.json")
EDGE = ("E_col1", "E_col5", "E_row1", "E_row5")
#: Room A comparators: the two-session folds (item 4 column i) and the six single-day pairings (item 3)
ROOM_A_FOLD = {"01": "s0203_to_s01", "02": "s0103_to_s02", "03": "s0102_to_s03"}
ROOM_A_SINGLE = ("s01_to_s02", "s01_to_s03", "s02_to_s01", "s02_to_s03", "s03_to_s01", "s03_to_s02")


def _load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _key(sess, stem, pid):
    return f"{sess}|{stem}|{int(pid)}"


def decode_rows(decode_json: str) -> dict:
    """{session: {config: [row]}}: the committed decision per evaluated pass."""
    out = {}
    for b, node in _load(decode_json)["sessions"].items():
        out[b] = {}
        for cn, rows in node["rows"].items():
            out[b][cn] = [{"key": _key(b, r["stem"], r["pass_id"]), "true": r["true"],
                           "line": r["final_line"], "correct": bool(r["correct"])} for r in rows]
    return out


def lock_rows(scorerlock_json: str, field: str = "display_lock") -> dict:
    """{session: {config: [row]}}: the drawn (display) lock per evaluated pass, or the scorer lock."""
    out = {}
    for b, node in _load(scorerlock_json)["sessions"].items():
        out[b] = {}
        for cn, rows in node["rows"].items():
            out[b][cn] = [{"key": _key(b, r["stem"], r["pass_id"]), "true": r["true"],
                           "line": r[field], "correct": bool(r[field] == r["true"])}
                          for r in rows]
    return out


def d1_rows(cell: str) -> dict:
    """committed (A, B) and both lock methods (A, B) for one D1 or item 4 cell."""
    base = J(RES, "cells", cell)
    d = decode_rows(J(base, "decode.json"))
    (b,) = list(d)
    return {"session": b, "committed": d[b],
            "lock_display": lock_rows(J(base, "scorerlock.json"), "display_lock")[b],
            "lock_scorer": lock_rows(J(base, "scorerlock.json"), "scorer_lock")[b]}


def d1() -> str:
    """D1: per held-out session, the configuration chosen on inner validation, and its held-out result."""
    from itertools import combinations
    import numpy as np
    SESS5 = ("01", "02", "03", "B1", "B2")
    NAME = {"01": "A1", "02": "A2", "03": "A3", "B1": "B1", "B2": "B2"}
    out, L = {"folds": {}}, ["## D1: per-recording normalisation, chosen on inner validation", ""]
    L += ["| held out | inner criterion, pooled / display | pooled / scorer | per-recording / display | per-recording / scorer | chosen |",
          "|---|---|---|---|---|---|"]
    finals = {}
    for T in SESS5:
        train4 = [s for s in SESS5 if s != T]
        crit, have = {}, True
        for nk in ("p", "r"):
            val = {"committed": [], "lock_display": [], "lock_scorer": []}
            for S in combinations(train4, 3):
                v = [s for s in train4 if s not in S][0]
                cell = f"d1{nk}_{''.join(S)}_to_{v}"
                if not _have(cell):
                    have = False
                    continue
                r = d1_rows(cell)
                val["committed"] += r["committed"]["A"]
                val["lock_display"] += r["lock_display"]["A"]
                val["lock_scorer"] += r["lock_scorer"]["A"]
            if not val["committed"]:
                continue
            c = acc(val["committed"])["pct"]
            for lm in ("display", "scorer"):
                crit[(nk, lm)] = (c + acc(val[f"lock_{lm}"])["pct"]) / 2.0
        if not have or len(crit) < 4:
            L.append(f"| {NAME[T]} | inner cells incomplete | | | | |")
            continue
        # ties go to the baseline configuration, pooled with the display lock
        order = [("p", "display"), ("p", "scorer"), ("r", "display"), ("r", "scorer")]
        best = max(order, key=lambda k: (round(crit[k], 6), -order.index(k)))
        L.append(f"| {NAME[T]} | " + " | ".join(f"{crit[k]:.2f}" for k in order) +
                 f" | {'per-recording' if best[0] == 'r' else 'pooled'}, {best[1]} lock |")
        fcell = f"d1r_final_{NAME[T]}" if best[0] == "r" else f"4ii_{NAME[T]}"
        finals[T] = (fcell, best)
        out["folds"][NAME[T]] = {"criterion": {f"{k[0]}_{k[1]}": v for k, v in crit.items()}, "chosen": list(best),
                                 "final_cell": fcell}
    L += ["", "Held-out results: the chosen configuration, then both normalisations with the display lock for reference.", "",
          "| held out | configuration | committed A | committed B | lock A | lock B | edges, committed A |",
          "|---|---|---|---|---|---|---|"]
    pooled = {"chosen": {}, "p": {}, "r": {}}
    for T in SESS5:
        rows_by = {}
        if T in finals and _have(finals[T][0]):
            fcell, best = finals[T]
            rows_by["chosen"] = (d1_rows(fcell), f"lock_{best[1]}", f"chosen: {'per-recording' if best[0] == 'r' else 'pooled'}, {best[1]} lock")
        if _have(f"4ii_{NAME[T]}"):
            rows_by["p"] = (d1_rows(f"4ii_{NAME[T]}"), "lock_display", "pooled (D0), display lock")
        if _have(f"d1r_final_{NAME[T]}"):
            rows_by["r"] = (d1_rows(f"d1r_final_{NAME[T]}"), "lock_display", "per-recording, display lock")
        for key, (r, lk, label) in rows_by.items():
            parts = [acc(r["committed"]["A"]), acc(r["committed"]["B"]), acc(r[lk]["A"]), acc(r[lk]["B"])]
            e = parts[0]["edge"]
            L.append(f"| {NAME[T]} | {label} | " + " | ".join(f"{a['pct']:.2f} [{a['ci95'][0]:.2f}, {a['ci95'][1]:.2f}]" for a in parts)
                     + " | " + " / ".join('-' if e[k] is None else f"{e[k]:.0f}" for k in EDGE) + " |")
            for w, rr in (("committed_A", r["committed"]["A"]), ("committed_B", r["committed"]["B"]),
                          ("lock_A", r[lk]["A"]), ("lock_B", r[lk]["B"])):
                pooled[key].setdefault(("A" if T in ("01", "02", "03") else "B", w), []).extend(rr)
    L += ["", "Per room, pooled over held-out sessions:", "", "| room | configuration | committed A | committed B | lock A | lock B |",
          "|---|---|---|---|---|---|"]
    for room in ("A", "B"):
        for key, label in (("chosen", "chosen on inner validation"), ("p", "pooled (D0), display lock"),
                           ("r", "per-recording, display lock")):
            if (room, "committed_A") not in pooled[key]:
                continue
            n_sess = 3 if room == "A" else 2
            if len(pooled[key][(room, "committed_A")]) != 120 * n_sess:
                continue
            a = [acc(pooled[key][(room, w)]) for w in ("committed_A", "committed_B", "lock_A", "lock_B")]
            L.append(f"| Room {room} | {label} | " + " | ".join(f"**{x['pct']:.2f}** [{x['ci95'][0]:.2f}, {x['ci95'][1]:.2f}]" for x in a) + " |")
    md = "\n".join(L) + "\n"
    with open(J(RES, "d1.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=str)
    with open(J(RES, "d1.md"), "w", encoding="utf-8") as f:
        f.write(md)
    return md


def room_a_rows(tag: str) -> dict:
    """The shipped Room A fold, pass by pass: committed (d4_headline's line) and the drawn lock."""
    rows = [r for r in _load(D6) if r["tag"] == tag]
    assert len(rows) == 120, f"{tag}: {len(rows)} rows"
    sess = tag.split("_to_s")[1]
    com = [{"key": _key(sess, r["stem"], r["pass_id"]), "true": r["true"], "line": r["headline_line"],
            "correct": bool(r["headline_correct"])} for r in rows]
    lk = [{"key": _key(sess, r["stem"], r["pass_id"]), "true": r["true"], "line": r["lock_drawn"],
           "correct": bool(r["lock_drawn_correct"])} for r in rows]
    return {"committed": com, "lock": lk}


def cell_rows(cell: str) -> dict:
    """{"committed": {config: rows}, "lock": {config: rows}} for one pd_cells cell."""
    base = J(RES, "cells", cell)
    d, lk = decode_rows(J(base, "decode.json")), lock_rows(J(base, "scorerlock.json"))
    (b,) = list(d)
    return {"session": b, "committed": d[b], "lock": lk[b]}


def item2_rows() -> dict:
    """The confirmatory run's rows, per Room B session, from the merged decode and scorer lock."""
    d, lk = decode_rows(J(DC2, "decode.json")), lock_rows(J(DC2, "scorerlock.json"))
    return {b: {"committed": d[b], "lock": lk.get(b, {})} for b in d}


def acc(rows):
    from pipeline.constrained.dc2_pipeline import _acc
    return _acc(rows)


def paired(ref, arm, level=95.0):
    from pipeline.constrained.dc2_pipeline import _paired
    return _paired(ref, arm, level)


def plumb(cell: str = "plumb_A3", tag: str = "s0102_to_s03") -> int:
    """A plumbing cell through the harness against the shipped fold, pass by pass."""
    c = cell_rows(cell)
    ref = room_a_rows(tag)
    out = {}
    for what, mine in (("committed", c["committed"]["A"]), ("lock", c["lock"]["A"])):
        a = {r["key"]: r["line"] for r in ref[what]}
        b = {r["key"]: r["line"] for r in mine}
        ks = sorted(set(a) | set(b))
        eq = sum(1 for k in ks if a.get(k) == b.get(k))
        out[what] = {"n_shipped": len(a), "n_harness": len(b), "equal": eq,
                     "EXACT": bool(eq == len(ks) == 120),
                     "first_differences": [(k, a.get(k), b.get(k)) for k in ks if a.get(k) != b.get(k)][:5]}
    out["PASSED"] = bool(out["committed"]["EXACT"] and out["lock"]["EXACT"])
    with open(J(RES, f"{cell}.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(json.dumps(out, indent=1))
    return 0 if out["PASSED"] else 1


def _fmt_acc(a):
    if not a:
        return "not run", ""
    e = a["edge"]
    edges = " / ".join("-" if e[k] is None else f"{e[k]:.0f}" for k in EDGE)
    return f"{a['pct']:.2f} [{a['ci95'][0]:.2f}, {a['ci95'][1]:.2f}]", edges


def _fmt_pair(p):
    if not p:
        return "not run"
    lo, hi = p["ci95"]
    return f"{p['points']:+.2f} [{lo:.2f}, {hi:.2f}] ({p['passes']:+d} passes)"


def _have(cell):
    b = J(RES, "cells", cell)
    return os.path.exists(J(b, "decode.json")) and os.path.exists(J(b, "scorerlock.json"))


def summary() -> dict:
    import numpy as np
    S = {"item2": {}, "item3": {}, "item4": {}, "room_A": {}}
    # Room A comparators
    for tag in ROOM_A_SINGLE + tuple(ROOM_A_FOLD.values()):
        r = room_a_rows(tag)
        S["room_A"][tag] = {"committed": acc(r["committed"]), "lock": acc(r["lock"])}
    # item 2, the confirmatory run (configuration A and B, committed and lock)
    it2 = item2_rows() if os.path.exists(J(DC2, "decode.json")) and os.path.exists(J(DC2, "scorerlock.json")) else {}
    for b, r in it2.items():
        S["item2"][b] = {f"committed_{cn}": acc(r["committed"][cn]) for cn in r["committed"]}
        S["item2"][b].update({f"lock_{cn}": acc(r["lock"][cn]) for cn in r["lock"]})
    # item 3
    for cell, te in (("3a", "B2"), ("3b", "B1")):
        if not _have(cell):
            continue
        c = cell_rows(cell)
        node = {w: {cn: acc(rows) for cn, rows in c[w].items() if cn in ("A", "B")} for w in ("committed", "lock")}
        if te in it2:
            node["vs_item2a_same_test"] = {w: paired(it2[te][w]["A"], c[w]["A"]) for w in ("committed", "lock")}
        S["item3"][cell] = node
    # ADDENDUM (recipe): Room A's single-day pairings through the harness (plumbT_A2 is s01_to_s02)
    ref = {"s01_to_s02": "plumbT_A2", **{t: f"3ref_{t}" for t in ROOM_A_SINGLE if t != "s01_to_s02"}}
    got = {t: cell_rows(c) for t, c in ref.items() if _have(c)}
    S["item3_recipe_matched_room_A"] = {t: {w: acc(r[w]["A"]) for w in ("committed", "lock")} for t, r in got.items()}
    if len(got) == len(ref):
        S["item3_recipe_matched_room_A"]["POOLED"] = {
            w: acc(sum((r[w]["A"] for r in got.values()), [])) for w in ("committed", "lock")}
    # item 4
    for row, te in (("B2", "B2"), ("B1", "B1"), ("A1", "01"), ("A2", "02"), ("A3", "03")):
        i = (({w: it2[te][w]["A"] for w in ("committed", "lock")} if te in it2 else None) if row.startswith("B")
             else room_a_rows(ROOM_A_FOLD[te]))
        node = {"i": {w: acc(i[w]) for w in ("committed", "lock")} if i else None}
        cells = {}
        for col in ("ii", "iii"):
            cell = f"4{col}_{row}"
            if _have(cell):
                cells[col] = cell_rows(cell)
                node[col] = {w: acc(cells[col][w]["A"]) for w in ("committed", "lock")}
                if row.startswith("B"):
                    node[f"{col}_config_B"] = {w: acc(cells[col][w]["B"]) for w in ("committed", "lock")}
        if i and "ii" in cells:
            node["ii_minus_i"] = {w: paired(i[w], cells["ii"][w]["A"]) for w in ("committed", "lock")}
        if "ii" in cells and "iii" in cells:
            node["iii_minus_ii"] = {w: paired(cells["ii"][w]["A"], cells["iii"][w]["A"]) for w in ("committed", "lock")}
        # ADDENDUM (recipe): the Room A rows' recipe-matched column (i'), beside the pre-registered (i)
        if not row.startswith("B") and _have(f"4i_{row}"):
            ip = cell_rows(f"4i_{row}")
            node["i_recipe"] = {w: acc(ip[w]["A"]) for w in ("committed", "lock")}
            if "ii" in cells:
                node["ii_minus_i_recipe"] = {w: paired(ip[w]["A"], cells["ii"][w]["A"]) for w in ("committed", "lock")}
        if row.startswith("B") and "ii" in cells:
            c3 = {"B2": "3a", "B1": "3b"}[row]
            if _have(c3):
                r3 = cell_rows(c3)
                node["ii_minus_item3"] = {w: paired(r3[w]["A"], cells["ii"][w]["A"]) for w in ("committed", "lock")}
        S["item4"][row] = node
    with open(J(RES, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(S, f, indent=1, default=str)
    return S


def render(S: dict) -> str:
    """The item 3 and item 4 tables, in markdown, from summary()."""
    L = ["## Item 3: new day against new room", "",
         "| cell | train | test | committed, A [95%] | edges | lock, A | committed, B | lock, B |",
         "|---|---|---|---|---|---|---|---|"]
    for cell, (tr, te) in (("3a", ("B1", "B2")), ("3b", ("B2", "B1"))):
        n = S["item3"].get(cell)
        if not n:
            L.append(f"| {cell} | {tr} | {te} | not run | | | | |")
            continue
        ca, ea = _fmt_acc(n["committed"]["A"])
        la, _ = _fmt_acc(n["lock"]["A"])
        cb, _ = _fmt_acc(n["committed"].get("B"))
        lb, _ = _fmt_acc(n["lock"].get("B"))
        L.append(f"| {cell} | {tr} | {te} | {ca} | {ea} | {la} | {cb} | {lb} |")
    L += ["", "Paired on the same test passes, configuration A, item 3 minus item 2a (new day minus new room):", ""]
    for cell, te in (("3a", "B2"), ("3b", "B1")):
        n = S["item3"].get(cell) or {}
        p = n.get("vs_item2a_same_test")
        if p:
            L.append(f"- {cell} on {te}: committed {_fmt_pair(p['committed'])}; lock {_fmt_pair(p['lock'])}")
    L += ["", "Room A's six single-day pairings, the same amount of training data:", "",
          "| pairing | committed [95%] | edges | lock |", "|---|---|---|---|"]
    for tag in ROOM_A_SINGLE:
        v = S["room_A"][tag]
        c, e = _fmt_acc(v["committed"])
        lk, _ = _fmt_acc(v["lock"])
        L.append(f"| {tag} | {c} | {e} | {lk} |")
    L += ["", "## Item 4: training on both rooms (EXPLORATORY, configuration A throughout)", "",
          "| test | (i) one room only | (ii) pooled | (iii) per-room normalisation | (ii) minus (i) | (iii) minus (ii) |",
          "|---|---|---|---|---|---|"]
    for row in ("B2", "B1", "A1", "A2", "A3"):
        n = S["item4"].get(row) or {}
        cells = []
        for col in ("i", "ii", "iii"):
            v = n.get(col)
            if v:
                c, e = _fmt_acc(v["committed"])
                lk, _ = _fmt_acc(v["lock"])
                cells.append(f"{c}; edges {e}; lock {lk}")
            else:
                cells.append("not run")
        d1 = n.get("ii_minus_i", {}).get("committed")
        d2 = n.get("iii_minus_ii", {}).get("committed")
        L.append(f"| {row} | " + " | ".join(cells) + f" | {_fmt_pair(d1)} | {_fmt_pair(d2)} |")
    L += ["", "The same differences on the drawn lock, and the B rows against item 3 (same test day):", ""]
    for row in ("B2", "B1", "A1", "A2", "A3"):
        n = S["item4"].get(row) or {}
        bits = []
        for k, lab in (("ii_minus_i", "(ii)-(i)"), ("iii_minus_ii", "(iii)-(ii)")):
            if n.get(k):
                bits.append(f"lock {lab} {_fmt_pair(n[k]['lock'])}")
        if n.get("ii_minus_item3"):
            bits.append(f"committed (ii)-item3 {_fmt_pair(n['ii_minus_item3']['committed'])}")
            bits.append(f"lock (ii)-item3 {_fmt_pair(n['ii_minus_item3']['lock'])}")
        for col in ("ii", "iii"):
            if n.get(f"{col}_config_B"):
                c, _ = _fmt_acc(n[f"{col}_config_B"]["committed"])
                bits.append(f"({col}) under configuration B {c}")
        if n.get("i_recipe"):
            c, e = _fmt_acc(n["i_recipe"]["committed"])
            lk, _ = _fmt_acc(n["i_recipe"]["lock"])
            bits.append(f"recipe-matched (i') {c}, edges {e}, lock {lk}")
        if n.get("ii_minus_i_recipe"):
            bits.append(f"committed (ii)-(i') {_fmt_pair(n['ii_minus_i_recipe']['committed'])}")
            bits.append(f"lock (ii)-(i') {_fmt_pair(n['ii_minus_i_recipe']['lock'])}")
        if bits:
            L.append(f"- {row}: " + "; ".join(bits))
    rm = S.get("item3_recipe_matched_room_A") or {}
    if rm:
        L += ["", "Room A single-day pairings through the harness (recipe-matched, addendum):", "",
              "| pairing | committed | edges | lock |", "|---|---|---|---|"]
        for t, v in rm.items():
            c, e = _fmt_acc(v["committed"])
            lk, _ = _fmt_acc(v["lock"])
            L.append(f"| {t} | {c} | {e} | {lk} |")
    return "\n".join(L) + "\n"


def posthoc_cell() -> str:
    """ADDENDUM (posthoc_cell), POST HOC: the one A1+A2+B1 model on A3 and on B2, with its comparators."""
    out, L = {}, ["## POST HOC cell: one model on A1+A2+B1, tested on A3 and B2", ""]
    a3, b2 = cell_rows("ph_A3"), cell_rows("ph_B2")
    ref_a3 = {"4i_A3 (A1+A2, same harness and recipe)": cell_rows("4i_A3"),
              "shipped s0102_to_s03 (A1+A2, grid-lattice 0.5 s head)": None}
    ship = room_a_rows("s0102_to_s03")
    it2 = item2_rows()["B2"]
    L += ["| test | configuration | committed [95%] | edges | lock [95%] |", "|---|---|---|---|---|"]
    for name, rows, cfgs in (("A3", a3, ("A",)), ("B2", b2, ("A", "B"))):
        for cn in cfgs:
            c, e = _fmt_acc(acc(rows["committed"][cn]))
            lk, _ = _fmt_acc(acc(rows["lock"][cn]))
            L.append(f"| {name} | {cn} | {c} | {e} | {lk} |")
            out[f"{name}_{cn}"] = {"committed": acc(rows["committed"][cn]), "lock": acc(rows["lock"][cn])}
    L += ["", "Paired on the same passes (this model minus the comparator):", ""]
    comps = [("A3", "A", "Room-A-only model 4i_A3 (A1+A2, same harness and recipe)",
              ref_a3["4i_A3 (A1+A2, same harness and recipe)"]["committed"]["A"],
              ref_a3["4i_A3 (A1+A2, same harness and recipe)"]["lock"]["A"], a3),
             ("A3", "A", "shipped fold s0102_to_s03 (A1+A2, grid-lattice 0.5 s head)", ship["committed"],
              ship["lock"], a3),
             ("B2", "A", "frozen A1+A2+A3 model, item 2a", it2["committed"]["A"], it2["lock"]["A"], b2),
             ("B2", "B", "frozen A1+A2+A3 model, item 2b", it2["committed"]["B"], it2["lock"]["B"], b2)]
    for te, cn, label, rc, rl, mine in comps:
        pc, pl = paired(rc, mine["committed"][cn]), paired(rl, mine["lock"][cn])
        L.append(f"- {te}, configuration {cn}, against the {label}: committed {_fmt_pair(pc)}; "
                 f"lock {_fmt_pair(pl)}; edge walks {pc['edge_walks']}")
        out[f"{te}_{cn}_vs_{label}"] = {"committed": pc, "lock": pl}
    L += ["", "Context, not tested (item 4 column ii):", ""]
    for cell, cns in (("4ii_A3", ("A",)), ("4ii_B2", ("A", "B"))):
        r = cell_rows(cell)
        for cn in cns:
            c, e = _fmt_acc(acc(r["committed"][cn]))
            lk, _ = _fmt_acc(acc(r["lock"][cn]))
            L.append(f"- {cell}, configuration {cn}: committed {c}, edges {e}, lock {lk}")
    md = "\n".join(L) + "\n"
    with open(J(RES, "posthoc_cell.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=str)
    with open(J(RES, "posthoc_cell.md"), "w", encoding="utf-8") as f:
        f.write(md)
    return md


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["posthoc"]:
        print(posthoc_cell())
        return 0
    if argv[:1] == ["d1"]:
        print(d1())
        return 0
    if argv[:1] == ["plumb"]:
        return plumb(*argv[1:3]) if len(argv) >= 3 else plumb()
    if argv[:1] == ["summary"]:
        S = summary()
        md = render(S)
        with open(J(RES, "summary_tables.md"), "w", encoding="utf-8") as f:
            f.write(md)
        print(md)
        return 0
    raise SystemExit("usage: pd_report plumb | summary")


if __name__ == "__main__":
    sys.exit(main())
