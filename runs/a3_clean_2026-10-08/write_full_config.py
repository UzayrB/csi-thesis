"""Write the FULL A3-clean configuration after stage 5 (POA_DOT.md section 5, step 5), before A3 is touched.

    python3 runs/a3_clean_2026-10-08/write_full_config.py

It reads the lock side from dot/LOCK_SIDE.json (Overall's 2c701274) and the dot side from the five stages' SELECTION.json
(stage 5's chosen variant carries every earlier winner), and writes:
  - A3_CLEAN_CONFIG_FULL.json (+ .sha256): the machine-read configuration a3_full.py checks before its decode;
  - A3_CLEAN_CONFIG_FULL.md (+ .sha256): the same, for the record, with every stage's choice against the shipped value.
It refuses to overwrite either.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time

J = os.path.join
HERE = os.path.dirname(os.path.abspath(__file__))
DOT = J(HERE, "dot")


def sha(p: str) -> str:
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main() -> int:
    sys.path.insert(0, HERE)
    import dot_harness as H
    out_j, out_m = J(HERE, "A3_CLEAN_CONFIG_FULL.json"), J(HERE, "A3_CLEAN_CONFIG_FULL.md")
    for p in (out_j, out_m):
        if os.path.exists(p):
            raise SystemExit(f"REFUSED: {p} exists")
    ls = json.load(open(J(DOT, "LOCK_SIDE.json"), encoding="utf-8"))
    sel = {n: json.load(open(J(DOT, f"stage{n}", "SELECTION.json"), encoding="utf-8")) for n in (1, 2, 3, 4, 5)}
    v = H.variant(**sel[5]["chosen_variant"])
    assert (v["sd"], v["display_entry"], v["display_window"]) == (ls["sd"], ls["entry"], ls["window"]), (v, ls)
    shipped = H.variant()
    at = time.strftime("%Y-%m-%d %H:%M:%S")
    cfg = {"what": "the full A3-clean display configuration: lock side (Overall) and dot side (this run)",
           "written": at, "cell": "f05_A3", "variant": v,
           "lock_side": {"from": ls["commit"], "config": ls["config"], "config_sha256": ls["config_sha256"]},
           "dot_side": {f"stage{n}": {"chosen": sel[n]["chosen"]} for n in sel},
           "rules": ["PREREG_DOT.md (cdab65c4)", "PREREG_DOT_ADDENDUM_1.md (7aa5b1ff)", "PREREG_DOT_ADDENDUM_2.md (cec9d891)"],
           "next": "ONE A3 decode with it: A3's SEVENTH look (a3_full.py)"}
    with open(out_j, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=1)
    head = {"end_head": "display head", "prior_f": "display prior (flatten)", "head_offset": "head offset (s)",
            "shift_w": "dot phase SHIFT_W (strides)", "switch": "switch arm", "sd": "display spread (sd_scale)",
            "display_entry": "display entry", "display_window": "display entry window (m)"}
    name = {"shipped": "DISP_END (shipped)", "pooled": "centre_labelled (the pooled heads)", "heldout": "DISP_END"}
    rows = "\n".join(f"| {head[k]} | {name.get(shipped[k], shipped[k])} | **{name.get(v[k], v[k])}** |" for k in head)
    md = f"""# A3_CLEAN_CONFIG_FULL: every display setting chosen without A3. Written {at} (clock), before A3 is touched

**Status.** The full A3-clean configuration:
- **the lock side:** Overall's on the shipped all-0.5 s heads (`{ls['config']}`, {ls['commit']}, SHA-256
  {ls['config_sha256'][:16]}...);
- **the dot side:** selected by this run's five stages under `PREREG_DOT.md` (cdab65c4), addendum 1 (7aa5b1ff) and
  addendum 2 (cec9d891).

**What comes next:** it is used for ONE A3 decode, A3's SEVENTH look (`a3_full.py`), set in that decode's processes only.
**Nothing shipped changes:** `FINAL_CONFIG.md`, the live app's defaults, the model sets, B2 and zero-shot.

| setting | shipped | A3-clean |
|---|---|---|
{rows}

**Also as shipped:**
- the cap of 0.80 m per window;
- latency 2.0 s, lock at press + 2.0 s, 10 frames per second;
- K1g's look-ahead and glide;
- the pool's five 0.5 s networks (`f05_A3`).

**The stages** (development evaluation, all data seen; `dot/stage<n>/SELECTION.json`):
- stage 1: {sel[1]['chosen']};
- stage 2: {sel[2]['chosen']};
- stage 3: {sel[3]['chosen']};
- stage 4: {sel[4]['chosen']};
- stage 5: {sel[5]['chosen']}.

**The machine-read form:** `A3_CLEAN_CONFIG_FULL.json` (SHA-256 {sha(out_j)}).
"""
    with open(out_m, "w", encoding="utf-8") as f:
        f.write(md)
    for p in (out_j, out_m):
        with open(p + ".sha256", "w", encoding="utf-8") as f:
            f.write(f"{sha(p)}  {os.path.basename(p)}\n")
    print(md)
    print("json", sha(out_j), "md", sha(out_m))
    return 0


if __name__ == "__main__":
    sys.exit(main())
