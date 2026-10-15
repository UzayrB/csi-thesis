"""THE STANDING PAIRING KEY IS session|stem|pass_id. A dict spanning PAIRINGS adds the tag.

THREE COLLISIONS, EACH FOUND AFTER IT HAD ALREADY CORRUPTED AN INTERVAL.

  pass_id alone            2026-09-18, sb3_exitsweep. pass_id restarts at 1 in every recording,
                           so six recordings collapsed into one dict of twenty entries and every
                           recording's passes were compared against the last recording's.
  stem|pass_id             2026-09-20, s2_display. Recording STEMS repeat across sessions, so a
                           dict spanning nine pairings kept 240 of 1080 passes. Nothing showed it:
                           the stage exited 0, and the frame-level totals were right because they
                           are accumulators.
  session|stem|pass_id     still not enough ACROSS PAIRINGS, because three pairings test the same
                           session. A dict that spans pairings carries the pairing tag as well.

THE RULE, standing from 2026-09-20: every per-pass row carries key = session|stem|pass_id, and
every dict that spans pairings is keyed on tag|session|stem|pass_id. This test does not try to
decide by regular expression which dicts span what: it requires every site to be CLASSIFIED below,
with the reason. A new site fails until somebody says which kind it is.
"""

from __future__ import annotations

import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
CONSTRAINED = REPO / "pipeline" / "constrained"

#: Every site that builds a per-pass key, classified by the audit of 2026-09-20.
#: ROWS         the key goes into a LIST, so nothing can collide; callers that span pairings add
#:              the tag or assert uniqueness.
#: ONE_PAIRING  the dict is built and consumed inside one pairing's iteration.
#: TAGGED       the dict spans pairings and the key carries the tag.
CLASSIFIED = {
    # --- the 2026-09-23 tracking batch. All four build session|stem|pass_id to look up per-pass
    # terms that are themselves rebuilt inside the pairing loop, so no dict spans pairings. Where
    # a key is CARRIED across pairings it is carried as a FIELD beside its own `tag`, never as a
    # dict key, which is the failure mode this registry exists to catch.
    # RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
#     "y2a_causal.py": "PER_PAIRING. `key` is used only for terms.get(key) inside the pairing loop",
    "night_arms.py": "ROWS. night_track() emits rows for one recording of one pairing",
    "sb2_structural.py": "ROWS. track2() emits rows, one recording at a time",
    "f1_arms.py": "ROWS. one recording's rows, consumed per pairing",
    "g2_multihead.py": "ROWS. one recording's rows, consumed per pairing",
    "q3_startclf.py": "ROWS. keys.append into a list, one fold at a time",
    "s2_display.py": "TAGGED. per_pass spans nine pairings and keys on tag|session|stem|pass_id",
    # RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
#     "z3a_linkprod.py": "TAGGED. rows per weight span nine pairings and key on tag|session|stem|pass_id",
    # RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
#     "z3b_g100native.py": "TAGGED. a thin entry point onto z3a_linkprod, whose rows key on tag|session|stem|pass_id",
    # RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
#     "d4_headline.py": "TAGGED. rows span nine pairings and key on tag|session|stem|pass_id",
    "dc2_scorerlock.py": "ROOM_KEYED. rows key on room|session|stem|pass_id, the DC2 standing key; the start-term lookups key on session|stem|pass_id inside one session's loop",
    # RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
#     "e2_switch.py": "TAGGED. rows span nine pairings and key on tag|session|stem|pass_id; the start-term lookup inside the pairing loop keys on session|stem|pass_id",
    # RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
#     "e1_switch.py": "TAGGED. rows span nine pairings and key on tag|session|stem|pass_id; the start-term lookup inside the pairing loop keys on session|stem|pass_id",
    # RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
#     "f3_render.py": "ONE_PAIRING. the render draws s0102_to_s03 alone; its walk keys carry the tag and the start-term lookup keys on session|stem|pass_id within that one pairing",
    "f4_render.py": "ONE_PAIRING. f3_render's copy: one pairing per run (F4_TAG, s0102_to_s03 by default); its walk keys carry the tag, the start-term lookup keys on session|stem|pass_id within that pairing, and the result-panel total filters d4_headline's rows by that tag",
    "f5_donor.py": "TAGGED. rows span nine pairings and key on tag|session|stem|pass_id; the own-radio dict keys on (stem, pass_id) and the start-term lookups on session|stem|pass_id, both inside one pairing's loop",
    # RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
#     "d6_lock_commit.py": "TAGGED. rows span nine pairings and key on tag|session|stem|pass_id; the per-walk check against ACCEPTANCE keys on participant and walk within the render's one pairing",
    "veto.py": "PER_PAIRING. the start-term dict is built for one pairing and keyed session|stem|pass_id",
    # RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
#     "fusion.py": "NONE. no pass is keyed here",
    "lattice.py": "NONE. no pass is keyed here",
    "y4_pressalign.py": "TAGGED. both lattices' rows span nine pairings and key on tag|session|stem|pass_id; compare pairs them on that key",
    "t0_oracle.py": "PER_PAIRING. true_regions() keys on session|stem|pass_id and the dict it "
                    "returns is held under cache[tag], one per pairing, never merged across them",
    "t1_region.py": "PER_PAIRING. collect() keys on session|stem|pass_id and each dict is used "
                    "inside one pairing's own train/test split. The only structure that crosses "
                    "pairings is a LIST of keys holding three rows per pass, which is exactly why "
                    "the deciding figure is the per-pairing median and n_rows is labelled in the "
                    "payload as not a sample size",
    "t2_embed.py": "PER_PAIRING. collect_embed() keys on session|stem|pass_id, and its embedding "
                   "cache is keyed session|stem first so pass_id is scoped to its own recording",
    # RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
#     "t6_lockdiag.py": "PER_PAIRING. the per-pass key is built inside one pairing's loop and used "
#                       "to look up that pairing's own start terms and committed lines; nothing "
#                       "keyed on it outlives the pairing",
    "u1_adapt.py": "PER_PAIRING. session_rows() keys on session|stem|pass_id and each dict is "
                   "consumed inside one pairing's own train/test split; the embedding cache is "
                   "keyed mode|session|stem first, so pass_id is scoped to one recording",
    # RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
#     "t9_lengthnorm.py": "PER_PAIRING. the same as t7_lockarms, from which it is derived: the "
#                         "per-pass key looks up that pairing's own start terms and nothing keyed "
#                         "on it outlives the pairing",
    # RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
#     "t7_lockarms.py": "PER_PAIRING. the same, for that pairing's start terms; the tallies it "
#                       "accumulates across pairings are keyed on the LINE, never on the pass",
    # --- the audit of 2026-10-01 (reports/tracking/2026-10-01_restructure-check.md, section 5): the corrected
    # tracker's modules, written after the last audit
    "pd_decode.py": "ONE_PAIRING. decode_inner decodes ONE cell (one training set to one test session); its rows key "
                    "on room|session|stem|pass_id and the start-term lookup keys on session|stem|pass_id inside "
                    "that cell",
    "pd_render.py": "ONE_PAIRING. inner() renders ONE cell; the start-term lookup keys on session|stem|pass_id "
                    "within that cell",
    "pd_report.py": "ROWS. _key builds session|stem|pass_id into row LISTS; the one dict built from them (plumb) "
                    "compares ONE cell with ONE fold of 120 passes of one session",
    "pd_v2.py": "PER_PAIRING. rows_inner rebuilds reg and lin for each (network set, session) and writes them to "
                "that pair's own file; _option4's T is built for one rotation's test session and looked up "
                "inside it",
}

#: any f-string that pastes a pass id straight onto a stem, with or without a session in front
KEY_SITE = re.compile(r'\{(?:rec\.)?stem\}\|\{')
#: the OLD forms, which must not come back anywhere
OLD_FORM = re.compile(r'f["\']\{(?:rec\.)?stem\}\|\{(?:int\()?(?:pid|r\[)')


# RETIRED 2026-10-01: this scan no longer includes pipeline/retired/constrained/, deleted with that folder
# (git tag tracking-final-2026-10-01). It was: + sorted((REPO / "pipeline" / "retired" / "constrained").glob("*.py"))
@pytest.mark.parametrize("path", sorted(CONSTRAINED.glob("*.py")), ids=lambda p: p.name)
def test_every_per_pass_key_site_is_classified(path):
    text = path.read_text(encoding="utf-8")
    if not KEY_SITE.search(text):
        return
    assert path.name in CLASSIFIED, (
        f"{path.name} builds a per-pass key. The standing key is session|stem|pass_id, and a dict "
        f"spanning pairings needs the pairing tag on top of it. Add {path.name!r} to CLASSIFIED "
        f"with the reason it is safe, or fix the key."
    )


# RETIRED 2026-10-01: this scan no longer includes pipeline/retired/constrained/, deleted with that folder
# (git tag tracking-final-2026-10-01). It was: + sorted((REPO / "pipeline" / "retired" / "constrained").glob("*.py"))
@pytest.mark.parametrize("path", sorted(CONSTRAINED.glob("*.py")), ids=lambda p: p.name)
def test_the_old_stem_pass_key_is_gone(path):
    """stem|pass_id without a session in front is the 2026-09-20 collision. It may not return."""
    bad = [ln for ln in path.read_text(encoding="utf-8").splitlines() if OLD_FORM.search(ln)]
    assert not bad, (
        f"{path.name} still builds stem|pass_id without a session: {bad[:2]}. Recording stems "
        f"repeat across sessions, so that key is not unique. Use session|stem|pass_id."
    )


def test_the_stage_that_spans_pairings_carries_the_tag():
    # The second stage this checked, n1_diag, was removed on 2026-09-24 with the finished stage modules (git tag pre-cleanup; reports/project/repository/archive-code.md).
    s2 = (CONSTRAINED / "s2_display.py").read_text(encoding="utf-8")
    assert 'key = f"{tag}|{r[\'key\']}"' in s2 or 'f"{tag}|' in s2
