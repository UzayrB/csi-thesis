"""A3_CLEAN_CONFIG_0p5.md and its .sha256, from lock/SELECTION.json and the plumbing logs (ADDENDUM.md: written, hashed
and committed before A3 is touched). Refuses to overwrite. Its one machine line, `A3_CLEAN_LOCK_SIDE = {...}`, is what
a3_replay.py reads after checking the hash.
"""

from __future__ import annotations

import glob
import hashlib
import json
import os
import sys
import time

J = os.path.join
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = J(HERE, "A3_CLEAN_CONFIG_0p5.md")
ROTS = (("B1", "A1+A2 -> B1, weight 2"), ("A2", "A1+B1 -> A2"), ("A1", "A2+B1 -> A1"))
EDGES = ("E_col1", "E_col5", "E_row1", "E_row5")


def ci(x) -> str:
    return f"{x['diff']:+.2f} [{x['ci95'][0]:+.2f}, {x['ci95'][1]:+.2f}]"


def win(w) -> str:
    return "1.0 m" if w else "none"


def main() -> int:
    if os.path.exists(OUT):
        raise SystemExit(f"REFUSED: {OUT} exists")
    with open(J(HERE, "lock", "SELECTION.json"), encoding="utf-8") as f:
        S = json.load(f)
    ch, sh = S["A3_CLEAN_LOCK_SIDE"], S["SHIPPED"]
    plumb = {r: json.load(open(J(HERE, "logs", f"plumb_{r}.json"))) for r, _ in ROTS}
    ref = {r: json.load(open(J(HERE, "logs", f"ref_{r}.json"))) for r, _ in ROTS}
    arms = {}
    for p in glob.glob(J(HERE, "lock", "decodes", "*", "*", "arm.json")):
        m = json.load(open(p))
        arms[(m["rotation"], m["arm"])] = m
    assert len(arms) == 96 and all(m["against_record"]["committed_changed"] == 0 and not m["a3_inputs_opened"]
                                   and m["geometry_equals_session_01_alone"] for m in arms.values()), len(arms)
    shipped_exact = {r: arms[(r, sh["arm"])]["against_record"]["EXACT"] for r, _ in ROTS}
    assert all(shipped_exact.values()), shipped_exact
    curve = S["S1_spread"]["curve_lock_weighted"]
    best = max(curve.values())
    ties = [k for k, v in curve.items() if v == best]
    cf, sf = S["chosen_figures"], S["shipped_figures"]
    line = json.dumps({"sd_scale": ch["sd_scale"], "display_entry": ch["display_entry"],
                       "display_entry_window_m": ch["display_entry_window_m"]})
    L = [f"# A3_CLEAN_CONFIG_0p5: the display settings chosen without A3, on the shipped all-0.5 s heads. Lock side, "
         f"{time.strftime('%-d October %Y, %H:%M')} SAST (clock read)",
         "",
         "**Status.** The LOCK SIDE only, selected exactly as `runs/a3_clean_2026-10-08/PREREG.md` (SHA-256 bf0284de..., "
         "committed in 9f8972ae on 8 October) fixes, on the shipped all-0.5 s heads, with this folder's `ADDENDUM.md` "
         "(SHA-256 62369e46..., committed in 24a4358b before anything ran). Written, hashed and committed before A3 is "
         "touched.",
         "",
         "**Not adopted.** This is a configuration for one A3 decode (A3's sixth look), set in that decode's processes "
         "only. `FINAL_CONFIG.md`, the live app's defaults, B2, the zero-shot model and every shipped file are unchanged.",
         "",
         "## The lock side (the display decode: the lock and the dot read it; the committed decision does not)",
         "",
         "| setting | shipped | A3-clean | how it was chosen here |",
         "|---|---|---|---|",
         f"| display spread (sd_scale) | {sh['sd_scale']} | **{ch['sd_scale']}** | S1: argmax of rotation-weighted display "
         f"lock over {{2.5, ..., 6.0}}; best {best:.2f} at {', '.join(ties)}"
         f"{', ties to the smallest' if len(ties) > 1 else ''} (shipped 4.5: {curve['4.5']:.2f}) |",
         f"| display entry | {sh['display_entry']} | **{ch['display_entry']}** | S2: soft minus free "
         f"{ci(S['S2_soft_entry']['soft_minus_free'])}; soft ships if the interval contains zero or lies above it |",
         f"| display entry window | {win(sh['display_entry_window_m'])} | **{win(ch['display_entry_window_m'])}** | S3: "
         f"window minus none {ci(S['S3_entry_window']['window_minus_none'])}; the window ships only if the interval lies "
         f"entirely above zero |",
         "",
         "The machine line a3_replay.py reads (after checking this file's hash):",
         "",
         f"A3_CLEAN_LOCK_SIDE = {line}",
         "",
         "**Everything else in the display decode is as shipped:** the cap of 0.80 m per window, the A2 term alone as its "
         "start term, relgateU, abstain, the A2 weight 0.25 and the frozen A1+A2 pace.",
         "",
         "**The committed decision** is the shipped decode, untouched. On all 96 decodes (32 arms x 3 rotations), every "
         "committed line equals the reference `D05.relgateU+abstain+a2w0.25`.",
         "",
         "## The evidence (development evaluation, all data seen)",
         "",
         "- **The cells:** `f05r_0102_to_B1`, `f05r_01B1_to_02`, `f05r_02B1_to_01` (registered in memory, `reg.py`), "
         "built beside `d4c_fuse_*`; the readers came from `d4c_fuse_*`'s byte copies of the d1sp twins' files, since the "
         "twins' trees were removed in the 6 Oct cleanup.",
         "- **The plumbing gate before the swap:** each new cell, with the old heads, reproduces "
         "`d4c_fuse_<rotation>/d3/DT0.relgateU+abstain+a2w0.25` exactly (committed line, display lock, scorer lock): "
         + ", ".join(f"{r} {120 - len(plumb[r]['differ'])}/120" for r, _ in ROTS) + ".",
         "- **The swap:** the four slots replaced by the stride ablation's ALL05 seed set 0 networks (fh1s slot seed 3, "
         "g1s1 seed 1, g1s2 seed 2, g100 seed 0), byte-checked, inferred on the GPU; half unchanged.",
         "- **The new reference D05** (shipped display settings, DT0 settings, new heads), committed / display lock: "
         + "; ".join(f"{r} {ref[r]['new_heads']['committed']:.2f} / {ref[r]['new_heads']['lock']:.2f} (old heads "
                     f"{ref[r]['old_heads_DT0']['committed']:.2f} / {ref[r]['old_heads_DT0']['lock']:.2f})"
                     for r, _ in ROTS) + ".",
         "- **The plumbing gate of PREREG section 7:** the shipped arm reproduces D05 exactly on all three rotations.",
         "- **No input naming session 03** was opened by any decode, beyond A3's ground-truth sidecars, which "
         "`paths.load_paths` opens for the line geometry; the geometry was checked to be session 01's alone on every "
         "decode. Nothing was written outside this folder (audit hook).",
         "",
         "| rotation-weighted | chosen | shipped |",
         "|---|---|---|",
         f"| display lock | {cf['lock_weighted']:.2f} | {sf['lock_weighted']:.2f} |",
         f"| committed line | {cf['committed_weighted']:.2f} | {sf['committed_weighted']:.2f} |",
         f"| display lock, chosen minus shipped (paired, walks resampled within rotations) | "
         f"{ci(S['chosen_minus_shipped_lock'])} | |",
         "",
         "| rotation | chosen lock | shipped lock | lock edges E_col1 / E_col5 / E_row1 / E_row5, chosen | the same, shipped |",
         "|---|---|---|---|---|"]
    for r, name in ROTS:
        c, s = cf["per_rotation"][r], sf["per_rotation"][r]
        L.append(f"| {name} | {c['lock']:.2f} | {s['lock']:.2f} | "
                 + " / ".join(f"{c['edges'][e]['lock']:.1f}" for e in EDGES) + " | "
                 + " / ".join(f"{s['edges'][e]['lock']:.1f}" for e in EDGES) + " |")
    L += ["", "**The figures:** `lock/SELECTION.json`; the decodes are under `lock/decodes/<rotation>/<arm>/`.", ""]
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    h = hashlib.sha256(open(OUT, "rb").read()).hexdigest()
    with open(OUT + ".sha256", "w", encoding="utf-8") as f:
        f.write(f"{h}  A3_CLEAN_CONFIG_0p5.md\n")
    print(f"wrote {OUT} ({h[:16]}); {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
