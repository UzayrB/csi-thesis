"""The three rotation cells of the shipped all-0.5 s heads, registered in memory (ADDENDUM.md).

`f05r_<rotation>` mirrors stage_cells.json's `d4c_fuse` entry exactly (options aug + rrel, all five heads, arch fuse,
base d1sp, so the readers are the d1sp twin's), with its weights first shared from `d4c_fuse_<rotation>`. They are NOT
written into runs/dc2_results/stage_cells.json, whose hash the shipped model's lists hold; every process that uses them
calls register() first.
"""

from __future__ import annotations


def register() -> list:
    from pipeline.constrained import pd_cells as P
    out = []
    for v in P.DEV3:
        tr = tuple(x for x in P.DEV3 if x != v)
        rt = f"{''.join(tr)}_to_{v}"
        c = f"f05r_{rt}"
        d4c = f"d4c_fuse_{rt}"
        assert P.D2[d4c] == {"heads": list(P.HEADS), "opts": {"aug": True, "rrel": True}, "arch": "fuse",
                             "pos_from": f"d1sp_{rt}"}, P.D2[d4c]
        P.CELLS[c], P.TWIN[c] = (tr, v, "pooled"), f"d1sp_{rt}"
        P.D2[c] = {"heads": list(P.HEADS), "opts": {"aug": True, "rrel": True}, "arch": "fuse", "pos_from": f"d1sp_{rt}"}
        P.SHARED_MODELS[c] = d4c
        out.append(c)
    return out


CELLS = {"B1": "f05r_0102_to_B1", "A2": "f05r_01B1_to_02", "A1": "f05r_02B1_to_01"}
OLD = {"B1": "d4c_fuse_0102_to_B1", "A2": "d4c_fuse_01B1_to_02", "A1": "d4c_fuse_02B1_to_01"}
