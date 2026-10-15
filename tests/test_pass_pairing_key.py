"""Passes from two arms must be matched on a key that includes the RECORDING STEM.

WHY THIS IS A TEST AND NOT A NOTE. On 2026-09-18 sb3_exitsweep paired a swept decode against its
baseline with ``{r["pass_id"]: r for r in base_rows}``. pass_id restarts at 1 in every recording,
so six recordings collapsed into one dict of twenty entries and every recording's passes were
compared against the LAST recording's. The per-pass differences and therefore the bootstrap
intervals were computed from mismatched pairs, and the ship rule read those intervals: it reported
three pairings winning outside the interval when the corrected pairing shows the sweep changing
nothing at all.

Nothing about that was visible from outside. The stage exited 0, produced a full results.json, and
the numbers were the right shape and the right order of magnitude. It is exactly the failure mode
the asserted-not-measured audit exists for, in a place that audit does not look.

THE RULE. A dict keyed on ["pass_id"] is safe if it is built and consumed inside ONE recording's
iteration, and unsafe the moment it spans recordings. That distinction is not decidable by reading
a regular expression, so this test does not try: it requires every such site to be CLASSIFIED, in
the list below, with the reason recorded. A new site fails until somebody says which kind it is.
"""

from __future__ import annotations

import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]

#: Every dict comprehension keyed on ["pass_id"], classified by the audit of 2026-09-18.
#: PER_RECORDING means the dict is built from one recording's passes and consumed inside that same
#: recording's loop, where pass_id is unique and the key is therefore sufficient.
PER_RECORDING = {
    # --- classified by the audit of 2026-10-01 (reports/tracking/2026-10-01_restructure-check.md, section 5): sites
    # written after the last audit, found by this test failing before the restructure; each read in context
    "pipeline/constrained/pd_subst.py":
        "decode(stem, ...) builds `com` and `lock` from ONE recording's night_track rows and returns them for that "
        "stem alone; the caller stores them under own[stem] and compares within the stem",
    "pipeline/constrained/pd_render.py":
        "inner() builds `disp` from one recording's display rows and `pstart` from that recording's own .gt.json, "
        "both inside the `for stem, rec, ... in todo` loop",
    "pipeline/live/app_teaching.py":
        "the pack is ONE recording (B2 PA2): `gt` is its own .gt.json, `fc_c` and `fc_l` are the session's rows "
        "filtered to `r[\"stem\"] == STEM`, and `app_c` is that recording's own session",
    "pipeline/live/final_model.py":
        "gate_inner() builds `com` from one recording's FinalTrackingSession inside `for stem in todo`, and compares "
        "it only with the reference keys of that stem, (stem, pass_id)",
    "pipeline/live/app_score.py":
        "score_recording(), dot_from_press() and score_log() each read ONE recording's .gt.json beside that "
        "recording's own replay log, and return per-recording rows",
    "pipeline/identify/idrelabel.py":                     # Identification's file; its audit and wording (1 Oct)
        "Both pass_id-keyed dicts are per recording: scan() builds `old` from one block's .gt.json and consumes it in "
        "the same loop iteration, and relabelled_gt() builds `after` and `gone` from that block's own manifest entry, "
        "matched by file path (by_file[rel]), and applies them only to that block's passes.",
    # RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
#     "pipeline/retired/constrained/rc8_demo.py": "render caption for one recording; consumed in its own loop",
    "pipeline/constrained/rb7_demo.py": "render caption for one recording",
    # RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
#     "pipeline/retired/constrained/e2_switch.py": "pstart and pend are built and consumed inside one recording's loop; every emitted row carries tag|session|stem|pass_id",
    # RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
#     "pipeline/retired/constrained/e1_switch.py": "pstart, pend and alt_true are built and consumed inside one recording's loop; every emitted row carries tag|session|stem|pass_id",
    # RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
#     "pipeline/retired/constrained/d6_lock_commit.py": "locks, true and b_line are built and consumed inside one recording's loop; every emitted row carries tag|session|stem|pass_id",
    "pipeline/constrained/y4_pressalign.py": "pstart and the per-pass press dicts are built and consumed inside one recording's loop; every emitted row carries tag|session|stem|pass_id",
    # RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
#     "pipeline/retired/constrained/re4_semibounded.py": "substitution within one recording's own loop",
    "pipeline/live/tracker_live.py":
        "the acceptance harness builds one row per pass inside ONE recording's loop, and the row "
        "carries pass_id only for printing; nothing keyed on it outlives that recording. The live "
        "runner itself holds no per-pass dict at all, only the running emission stack",
    "pipeline/constrained/t1_region.py":
        "previous_end_regions(): one recording's anchor end regions, consumed inside that same "
        "recording's own pass loop; the dict it returns is keyed session|stem|pass_id",
    "pipeline/constrained/f1_arms.py":
        "bounded_line(): one recording's bounded verdicts, consumed inside that recording's own "
        "loop; the rows it emits carry stem|pass_id",
    "pipeline/constrained/p1_runup.py":
        "first_presses(): the FIRST anchor press of ONE recording, read from that recording's own "
        "ground-truth sidecar and consumed only inside that recording's own pass loop. It is the "
        "mirror of press_ends(), which returns the LAST press, and the two are different "
        "quantities that must not be confused",
    "pipeline/constrained/f4_render.py":
        "f3_render's copy (2026-09-24): the same b_line, pstart and disp_by_pid, each built from "
        "ONE recording's passes and consumed inside the same iteration of the src loop",
    # RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
#     "pipeline/retired/constrained/f3_render.py":
#         "the bounded rescore's chosen line for ONE recording, built from that recording's "
#         "bounded_track and consumed inside the same iteration of the src loop; since 23e it is "
#         "kept beside the shipped decision as the disclosed price, not shown. It never crosses "
#         "recordings",
    "pipeline/constrained/g2_multihead.py":
        "bounded_rows(): the verdicts of ONE recording's bounded decode, built from that "
        "recording's bounded_track and consumed inside that same iteration of the src loop. The "
        "rows it emits carry stem|pass_id, and g3_final imports this same function",
    "pipeline/constrained/sb2_structural.py":
        "press_ends(): the anchor presses of ONE recording, cached under (session, stem) and "
        "consumed only inside that recording's own pass loop",
}

#: Modules that pair passes ACROSS arms or recordings. These must key on something carrying the
#: stem, and the key builder must actually include it.
#: Both registered modules (sb3_exitsweep, re6_heads) were removed on 2026-09-24 with the finished stage modules (git tag pre-cleanup; reports/project/repository/archive-code.md).
#: The set stays so a future cross-arm pairing has a place to be registered.
CROSS_ARM: set = set()

#: A LOOKUP dict keyed on pass_id, not a row dict that merely has "pass_id" as a field.
#: The key expression must be a subscript, optionally wrapped in one call, immediately before the
#: colon. Two earlier versions of this pattern were wrong in both directions: the first required
#: the bare ``{p["pass_id"]:`` and missed ``{int(p["pass_id"]):`` in re1_endlabels, a FALSE
#: NEGATIVE; the second was loose enough to match row literals like ``{"pass_id": p["pass_id"],``
#: in rb10_bounded_demo, a false positive that would have trained everyone to ignore this test.
DICT_ON_PASS_ID = re.compile(r"""\{\s*(?:\w+\(\s*)?\w+\[["']pass_id["']\]\s*\)?\s*:""")


def _py_files():
    for p in (REPO / "pipeline").rglob("*.py"):
        if "__pycache__" not in str(p):
            yield p


def test_every_pass_id_keyed_dict_is_classified():
    """A new dict keyed on pass_id alone fails until the audit list says which kind it is."""
    unclassified = []
    for p in _py_files():
        rel = str(p.relative_to(REPO))
        if DICT_ON_PASS_ID.search(p.read_text(encoding="utf-8")) and rel not in PER_RECORDING:
            unclassified.append(rel)
    assert not unclassified, (
        "these files key a dict on pass_id alone and are not classified in the audit list: "
        f"{unclassified}. pass_id restarts at 1 in every recording. If the dict is built and "
        "consumed inside one recording's loop, add it to PER_RECORDING with the reason. If it "
        "spans recordings, use the standing key, which since 2026-09-20 is "
        "f'{session}|{stem}|{pass_id}', plus the pairing tag if it spans pairings. See "
        "tests/test_cross_pairing_key.py.")


def test_the_classification_list_is_honest():
    """Every file claimed as per-recording must actually contain such a dict."""
    stale = [rel for rel in PER_RECORDING
             if not DICT_ON_PASS_ID.search((REPO / rel).read_text(encoding="utf-8"))]
    assert not stale, (
        f"these files are listed as per-recording but no longer key a dict on pass_id: {stale}. "
        "Remove them, so the list keeps meaning something.")


@pytest.mark.parametrize("rel", sorted(CROSS_ARM))
def test_cross_arm_pairing_uses_a_stem_bearing_key(rel):
    """A module pairing passes across arms must BUILD a stem-bearing key or CONSUME one.

    sb3_exitsweep consumes the key that track2 builds, so requiring every cross-arm module to
    contain the builder itself was wrong; what matters is that neither end pairs on pass_id alone.
    """
    src = (REPO / rel).read_text(encoding="utf-8")
    builds = bool(re.search(r"""f["']\{\s*(?:rec\.)?stem\s*\}\|""", src)) or "stem}|{" in src
    consumes = '["key"]' in src
    assert builds or consumes, (
        f"{rel} pairs passes across arms but neither builds nor consumes a stem-bearing key. "
        "Use f'{stem}|{pass_id}', the convention re6_heads already uses.")
    assert not re.search(r"""\{\s*\w*\[["']pass_id["']\]\s*:\s*\w+\s+for\s+\w+\s+in\s+"""
                         r"""(base_rows|swept_rows|old\["passes"\]|new\["passes"\])""", src), (
        f"{rel} still keys a cross-arm pairing dict on pass_id alone")


def test_track2_rows_carry_the_standing_pairing_key():
    """The row builder every semi-bounded comparison consumes must emit the standing key.

    Amended 2026-09-20: the key gained a SESSION prefix. Recording stems repeat across sessions,
    so stem|pass_id is unique inside one session and not across three, and a dict spanning
    pairings silently kept a quarter of its passes. See tests/test_cross_pairing_key.py.
    """
    src = (REPO / "pipeline/constrained/sb2_structural.py").read_text(encoding="utf-8")
    assert '"key": f"{rec.session}|{rec.stem}|{int(pid)}"' in src, \
        "track2 rows must carry a key of session|stem|pass_id"
