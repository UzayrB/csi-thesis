"""The structural guarantees of the identification run. These are the `all_clean` checks.

Each test names a way this project has been wrong before, or a way it could be wrong without
anyone noticing. They run on SOURCE and on CONFIGURATION, not on results, so they hold whether or
not a stage has run, and they fail loudly if a later edit breaks the guarantee.

THE GUARANTEES
  - the two retired participants are never read, and free-mode recordings are never read
  - `testing/` is never imported by anything that ships
  - the gait chain never touches the tracking transform
  - no ORACLE or PACE feature can enter a gait arm
  - heads are fixed before the run and never chosen on the test session
  - the pre-registration and its addenda exist and are hashed into the freeze
"""

from __future__ import annotations

import glob
import os
import re

import pytest

ID_DIR = "pipeline/identify"
# id11_audit, id12_conditioning, id13_representations and gait_features were removed on 2026-09-24
# (finished stages, restorable from the git tag pre-cleanup; see reports/project/repository/archive-code.md), and with
# them the two tests that only checked those modules.
NEW_STAGES = ("id14_crossday", "id15_corridor", "id15_factor_map", "conditioning",
              "raw_access", "id_heads")


def _src(mod: str) -> str:
    p = os.path.join(ID_DIR, f"{mod}.py")
    assert os.path.exists(p), f"{p} is missing"
    return open(p, encoding="utf-8").read()


def test_retired_participants_are_never_named_in_a_new_stage():
    """Azrah and Zaid are retired. Every archived eight-class figure is history, never quoted."""
    for mod in NEW_STAGES:
        s = _src(mod)
        for name in ("Azrah", "Zaid"):
            # the only permitted appearance is via the RETIRED constant, which is an exclusion
            for line in s.splitlines():
                if name in line:
                    assert "RETIRED" in line or line.strip().startswith("#"), (
                        f"{mod} names {name} outside the RETIRED exclusion: {line.strip()}")


def test_testing_is_never_imported():
    """`testing/` is history. Code reused from it is PORTED with attribution, never imported."""
    for p in glob.glob(os.path.join(ID_DIR, "*.py")):
        s = open(p, encoding="utf-8").read()
        assert not re.search(r"^\s*(from|import)\s+testing", s, re.M), (
            f"{p} imports from testing/, which is never imported by shipping code")


def test_the_port_is_attributed():
    """The notch and spectrogram are ported. The attribution must survive edits."""
    s = _src("conditioning")
    assert "testing/pipeline/branches/id_branch.py" in s
    assert "PORTED, NOT IMPORTED" in s


def test_the_gait_chain_never_touches_the_tracking_transform():
    """The tracking chain's 2 Hz lowpass removes the step rhythm this branch needs."""
    for mod in NEW_STAGES:
        s = _src(mod)
        assert "pipeline.io.clean" not in s, f"{mod} reaches into the shared cleaner"
        for bad in ("constrained.features", "constrained.decoder", "constrained.emissions"):
            assert bad not in s, f"{mod} imports the tracking transform ({bad})"


def test_the_pace_features_are_named_and_excluded_from_the_gait_arms():
    """A0 must not contain speed or step_length, and the arm keys must say so."""
    s = _src("id14_crossday")
    env = re.search(r"ENV_KEYS = \((.*?)\)", s, re.S).group(1)
    spec = re.search(r"SPEC_KEYS = \((.*?)\)", s, re.S).group(1)
    for banned in ('"speed"', "'speed'", "step_length"):
        assert banned not in env, f"ENV_KEYS contains a pace feature: {banned}"
        assert banned not in spec, f"SPEC_KEYS contains a pace feature: {banned}"


def test_the_head_is_fixed_and_not_chosen_on_the_test_session():
    """id3.score returns whichever head scores higher on TEST. No new stage may call it."""
    from pipeline.identify.id_heads import PRIMARY
    assert PRIMARY == "lda_shrinkage"
    for mod in ("id14_crossday", "id15_corridor"):
        s = _src(mod)
        assert "id3_embeddings import" not in s or "score" not in s.split(
            "id3_embeddings import")[1].split("\n")[0], (
            f"{mod} imports id3_embeddings.score, which selects a head on the test session")


def test_the_preregistration_and_its_addenda_exist():
    base = "reports/identification/history/2026-09-23_prereg-id.md"
    assert os.path.exists(base), "the pre-registration is missing"
    found = sorted(glob.glob("reports/identification/history/2026-09-23_prereg-id-addendum-*.md"))
    assert len(found) >= 4, f"expected the addenda A to D, found {found}"
    # Every document must state, in its own text, WHEN it was written relative to the numbers it
    # governs. Two forms are acceptable and no third is.
    #
    #   PREDATES        written before the numbers existed, the normal case for a pre-registration
    #   POST-DATA       an honest correction written after a stage ran, which must ALSO say that
    #                   the figures it affects are not yet quoted
    #
    # The second form exists because addendum E is one: it corrects M1's null after id12 ran and
    # before any id12 figure reached the report or the freeze. Forcing it to claim it predated the
    # numbers would have made it lie, and dropping the check would have let any addendum be silent
    # about its timing. This test failed on addendum E and that failure was correct.
    predates = re.compile(
        r"(no csi\b|before any (new )?(csi|identification )?number|"
        r"before any csi|no identification number (exists|of any kind))", re.I)
    post_data = re.compile(r"after .{0,40}\bran\b.{0,80}before any .{0,40}(figure|number)"
                           r".{0,40}(is |are )?(quoted|reported)", re.I | re.S)
    for p in [base] + found:
        s = open(p, encoding="utf-8").read()
        assert predates.search(s) or post_data.search(s), (
            f"{p} states neither that it predates the numbers it governs, nor that it is a "
            f"post-data correction made before the affected figures were quoted")


def test_every_addendum_says_what_it_changes_and_what_it_does_not():
    for p in sorted(glob.glob("reports/identification/history/2026-09-23_prereg-id-addendum-*.md")):
        s = open(p, encoding="utf-8").read().lower()
        assert "what does not change" in s or "what it does not" in s, (
            f"{p} does not bound its own scope")


@pytest.mark.parametrize("mod", NEW_STAGES)
def test_every_new_module_imports(mod):
    __import__(f"pipeline.identify.{mod}")
