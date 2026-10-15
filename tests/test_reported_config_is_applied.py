"""A stage that RECORDS a setting must APPLY it.

WHY THIS IS A TEST. On 2026-09-20 f3_render recorded its entry prior as "soft" in the results
under shipped.entry, and in ACCEPTANCE.md, and never once wrote it into the options the decoder
reads. The render therefore drew the FREE entry prior for a month while every artefact said soft.
It mattered: A1 restricts the entry to the first 1.0 m of each chain, and inside that window
"free" is flat where "soft" is the first window's own posterior, so the render was showing a
decoder that neither the arm's selection stage nor its confirmation stage had measured.

Nothing caught it. The value was consistent everywhere it was written down, and the only place it
was absent was the one place it had to be present.
"""

from __future__ import annotations

import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[1]


# RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
# def test_f3_render_applies_the_entry_it_reports():
#     src = (REPO / "pipeline" / "retired" / "constrained" / "f3_render.py").read_text(encoding="utf-8")
#     assert re.search(r'^\s*ENTRY = ', src, re.M), "f3_render no longer declares an entry prior"
#     assert 'opts["entry"] = ENTRY' in src, (
#         'f3_render declares ENTRY and records it under shipped.entry, but never writes it into '
#         'opts. The decoder reads opts["entry"], so the render would draw a different entry prior '
#         'from the one it reports.')


def test_the_display_stages_use_the_shipped_configuration():
    """A comparison run on default_opts() is a comparison of a decoder that does not ship."""
    # s2b_decision_causality.py was removed on 2026-09-24 with the finished stage modules (git tag pre-cleanup; reports/project/repository/archive-code.md).
    for name in ("s2_display.py",):
        src = (REPO / "pipeline" / "constrained" / name).read_text(encoding="utf-8")
        assert "opts = shipped_opts(st, tr_s)" in src, (
            f"{name} builds its options from something other than shipped_opts. The shipped "
            f"decoder carries the three night-combo arms and the soft entry; default_opts() "
            f"alone is a different decoder and its figures are not comparable")
        assert 'opts["entry"] = "soft"' in src, f"{name} does not apply the soft entry"
