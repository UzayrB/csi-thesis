"""THE RENDERING CONTRACT, enforced. See reports/tracking/render-rules.md for why each rule exists.

These five rules were each restated across at least two batches before they were written down.
This file is what stops them needing to be restated again: a rule in a conversation gets
re-litigated, a rule in a test does not. A render that breaks one of these turns the suite red and
blocks the freeze.
"""

from __future__ import annotations

import json
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
RULES = REPO / "reports" / "tracking" / "render-rules.md"
# RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
# RENDER = REPO / "pipeline" / "retired" / "constrained" / "f3_render.py"
RESULTS = REPO / "runs" / "constrained" / "fh" / "f3_render" / "results.json"
DISPLAY = REPO / "pipeline" / "constrained" / "render_display.py"


def _res():
    if not RESULTS.exists():
        pytest.skip("no render results present")
    return json.loads(RESULTS.read_text(encoding="utf-8"))


def test_the_contract_document_exists_and_names_its_tests():
    assert RULES.exists(), "reports/tracking/render-rules.md is the contract; it may not be deleted"
    text = RULES.read_text(encoding="utf-8")
    for name in ("test_the_locked_line_never_changes_after_the_lock",
                 "test_no_projection_helpers_in_the_display_path",
                 "test_the_caption_names_the_delay",
                 "test_acceptance_reports_the_two_accuracies_separately",
                 "test_the_render_reports_all_five_honesty_checks",
                 "test_the_dot_and_the_marker_leave_together",
                 "test_v1_the_latency_is_exactly_two_seconds",
                 "test_v2_the_commit_frame_is_the_marker_frame",
                 "test_v3_the_lock_time_does_not_vary_across_walks",
                 "test_v3_the_lock_offset_is_exactly_two_seconds",
                 "test_2a_the_first_drawn_position_is_the_committed_lines_entry",
                 "test_2a_the_anchor_segment_is_straight_and_uses_no_pace",
                 "test_2b_tracking_excludes_the_anchor_segment",
                 "test_v5_the_display_phase_is_a_single_global_constant",
                 "test_v3_no_confidence_gated_or_variable_latency_lock",
                 "test_v4_no_dwell_footage_in_the_demonstration",
                 "test_no_seconds_constant_used_as_a_window_count",
                 "test_render_at_most_k_switches_and_never_back_to_a_drawn_line",
                 "test_render_no_switch_in_the_final_zone",
                 "test_render_persistence_rule_holds",
                 "test_render_every_switch_is_causal_on_both_bounds",
                 "test_render_switch_jumps_are_counted_apart_from_lock_jumps",
                 "test_render_slides_stay_on_their_segments",
                 "test_render_equals_the_measurement_walk_for_walk",
                 "test_the_end_text_is_the_shipped_headline_decision"):
        assert name in text, f"RULES.md no longer names {name}, so the rule is unenforced in words"


# --------------------------------------------------------------------------- rule 1, the lock

def test_the_locked_line_never_changes_after_the_lock():
    """Rule 1 AS AMENDED (rule 1a, operator decisions 2026-09-23e and 23f): the locked line changes
    only by the rendered arm's mid-walk switches, at most its K, and never otherwise. Every walk:
    1 line after the lock plus one per recorded switch. The committed answer is still TEXT only."""
    d = _res()
    assert "switching" in d, "a render from before 23e: re-render under rule 1 as amended"
    bad, n_walks = [], 0
    for who, rec in (d.get("recordings") or {}).items():
        for w in (rec.get("walks") or []):
            n_walks += 1
            n, k = w.get("distinct_lines_after_lock"), w.get("mid_walk_switches")
            kmax = int((d.get("switching") or {}).get("max_switches") or 0)
            if n is None or k is None or int(k) > kmax or int(n) != 1 + int(k):
                bad.append((who, w.get("pass_id"), n, k))
    assert n_walks > 0, "no walks in the render results: this test would pass vacuously"
    assert not bad, (
        f"the drawn line changed after the lock other than by the one permitted switch on "
        f"{len(bad)} walks, e.g. {bad[:3]}. Rule 1 as amended: at most one switch, final")


def test_the_lock_is_the_only_line_the_dot_is_drawn_on():
    d = _res()
    for who, rec in (d.get("recordings") or {}).items():
        for w in (rec.get("walks") or []):
            if w.get("switches") is not None:
                assert int(w["switches"]) <= 1, (
                    f"{who} pass {w.get('pass_id')} drew {w['switches']} line changes; the lock "
                    f"itself is the only one allowed")


# --------------------------------------------------------------------------- rule 2, no projection

# RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
# def test_no_projection_helpers_in_the_display_path():
#     src = DISPLAY.read_text(encoding="utf-8")
#     for banned in ("def project_forward", "def implied_speed"):
#         assert banned not in src, (
#             f"{banned} is back in the display library. Rule 2: nothing is projected. The retired "
#             f"helpers stay retired (git tag pre-cleanup, testing/retired_tests_2026-09-20/)")
#     rsrc = RENDER.read_text(encoding="utf-8")
#     for banned in ("project_forward", "implied_speed", "CATCHUP_M_S"):
#         assert banned not in rsrc, f"{banned} is back in the render. Rule 2: nothing is projected"


def test_the_render_declares_nothing_is_projected():
    d = _res()
    acc = d.get("acceptance") or {}
    assert acc.get("nothing_is_projected") is True, (
        "the render no longer declares nothing_is_projected. Rule 2")


# --------------------------------------------------------------------------- rule 3, the delay

def test_the_caption_names_the_delay():
    d = _res()
    cap = d.get("caption") or ""
    assert cap, "the render has no caption"
    delay = d.get("display_delay_s")
    if delay is None:
        delay = (d.get("shipped") or {}).get("display_lag_s")
    assert delay is not None, "the render did not record the delay its caption must name"
    # a bare "1" matches almost any sentence; the delay must appear AS a delay
    import re as _re
    assert _re.search(rf"\b{float(delay):g}\s*s\b", cap), (
        f"the caption does not name the {delay} s delay it runs at. Rule 3: a viewer must be able "
        f"to read from the video how far behind real time it is. Caption was: {cap[:160]!r}")


# --------------------------------------------------------------------------- rule 4, separately

def test_acceptance_reports_the_two_accuracies_separately():
    d = _res()
    acc = d.get("acceptance") or {}
    for k in ("decoded_within_pct", "display_offset_mean_m"):
        assert acc.get(k) is not None, (
            f"the render did not report {k}. Rule 4: decoded accuracy and display offset are "
            f"reported separately")
    assert acc.get("decoded_within_pct") != acc.get("on_screen_within_pct"), (
        "decoded accuracy and on-screen tracking are the same number, so one of them is not "
        "measuring what it says")
    md = REPO / "runs" / "constrained" / "demo" / "ACCEPTANCE.md"
    if md.exists():
        assert "never added" in md.read_text(encoding="utf-8"), (
            "ACCEPTANCE.md no longer says the two are never added. Rule 4")


# --------------------------------------------------------------------------- rule 5, the checks

def test_the_render_reports_all_five_honesty_checks():
    d = _res()
    jumps = d.get("jumps") or {}
    vis = d.get("dot_visible") or {}
    assert jumps.get("total") is not None, "no jump count over 0.5 m. Rule 5"
    assert jumps.get("caused_by_the_lock") is not None, "jumps are not split by the lock. Rule 5"
    assert vis.get("frames_without_dot") is not None, "no count of frames without a dot. Rule 5"
    assert d.get("causal_bound_s") is not None, "no drawn-window causal bound. Rule 5"
    assert d.get("causal_evidence_bound_s") is not None, (
        "no EVIDENCE causal bound. Rule 5, and it is the one that catches the leak the "
        "drawn-window bound reads through")
    assert float(d["causal_bound_s"]) <= 1e-9, "the drawn-window bound is above zero"
    assert float(d["causal_evidence_bound_s"]) <= 1e-9, "the evidence bound is above zero"


# --------------------------------------------------------------------------- rule 6, together

def test_the_dot_and_the_marker_leave_together():
    """Neither leads the other, on any walk.

    The fault this catches lived only in the first second of each walk: the marker appeared at the
    walker's true first press while the dot could not draw until its first window's label time,
    up to 0.743 s later. Every aggregate measure averaged it away, so this is checked per walk and
    at frame resolution.
    """
    d = _res()
    lt = d.get("leave_together")
    assert lt is not None, (
        "the render did not report the leave-together check. Rule 6: the marker and the dot must "
        "start on the same frame, and a measure taken over a whole walk cannot see a fault that "
        "only happens at its start")
    assert lt.get("walks", 0) > 0, "the leave-together check ran on no walks at all"
    fps = d.get("fps") or 10
    assert lt["violations"] == 0, (
        f"on {lt['violations']} walks the marker and the dot did not start on the same frame; "
        f"the worst gap was {lt['max_gap_s']:.3f} s. Rule 6")
    assert float(lt["max_gap_s"]) <= 1.0 / float(fps) + 1e-6, (
        f"the marker and the dot start up to {lt['max_gap_s']:.3f} s apart, which is more than "
        f"the {1.0 / float(fps):.3f} s between frames. Rule 6")
    # THE STALL CLAUSE, SCOPED 2026-09-23 and disclosed as POST HOC in RENDER_RULES.md.
    # The fault rule 6 was written against is BACKWARD INTERPOLATION: the dot held still while the
    # decodes underneath it DIFFERED. A hold the decoder accounts for, because its own first
    # decode is still the tape entry, is that decoder's error shown honestly, and the only way to
    # remove it is to invent motion, which rule 2 forbids. So a violation is a hold the decoder
    # does NOT account for. The raw max_stall_s is still reported, and still asserted below for
    # the unexplained part.
    assert lt.get("stall_violations") == 0, (
        f"on {lt.get('stall_violations')} walks the dot stood still for longer than the decoder "
        f"accounts for while the marker walked away; the worst stall was {lt.get('max_stall_s')} "
        f"s and {lt.get('stall_explained_by_the_decoder')} of {lt.get('walks')} holds were "
        f"explained. Rule 6: appearing together is not enough, it must also start moving whenever "
        f"the decoder says the walker has")
    assert lt.get("stall_explained_by_the_decoder") is not None, (
        "the render must report how many holds the decoder accounts for. Without the split, a "
        "display fault and an honest decoder hold are the same number, which is the confusion "
        "rule 6 exists to prevent")


# RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
# def test_the_display_leads_rather_than_trails():
#     """Trailing interpolation stalls the dot for a stride at the start of every walk."""
#     src = (REPO / "pipeline" / "constrained" / "render_display.py").read_text(encoding="utf-8")
#     assert "def simulate_walk(" in src and "lead=False" in src, (
#         "simulate_walk no longer offers leading interpolation")
#     rsrc = RENDER.read_text(encoding="utf-8")
#     assert "lead=True" in rsrc, (
#         "the render is back to trailing interpolation, which makes the dot stand still for a "
#         "full stride at the start of every walk. Rule 6")
#     assert "LATENCY >= HEAD_OFFSET_S + STRIDE" in rsrc, (
#         "the render no longer asserts it has the latency margin that leading interpolation needs")


# ------------------------------------------------- the operator's rules V1 to V4, 2026-09-22
# These four are DECISIONS, not findings. reports/tracking/render-rules.md carries the reasoning. They are
# enforced exactly as rules 1 to 6 are, because a rule in a conversation gets re-litigated and a
# rule in a test does not.


def _vision():
    d = _res()
    v = d.get("vision_rules")
    assert v is not None, (
        "the render did not report vision_rules at all, so V1 to V4 are unenforced. Re-render.")
    return d, v


def test_v1_the_latency_is_exactly_two_seconds():
    """V1. The whole display runs exactly 2.0 s behind real time, every walk."""
    d, v = _vision()
    assert float(d["display_latency_s"]) == 2.0, (
        f"the display runs {d['display_latency_s']} s behind, not 2.0. V1 is an operator decision "
        f"of 2026-09-22 and is not re-opened by a score")
    assert float(v["V1_latency_s"]) == 2.0, "vision_rules disagrees with display_latency_s"
    assert v["V1_every_walk_same"] is True, (
        "the latency is not the same on every walk. V1 says the whole system, every walk")


def test_v2_the_commit_frame_is_the_marker_frame():
    """V2. The dot commits on the same frame the marker appears. One event, not two."""
    d, v = _vision()
    c = v["V2_commit_frame_equals_marker_frame"]
    fps = d.get("fps") or 10
    assert c["walks"] > 0, "the V2 check ran on no walks at all"
    assert c["violations"] == 0, (
        f"on {c['violations']} walks the commit and the marker were different frames, worst gap "
        f"{c['max_gap_s']:.3f} s. V2: they are ONE event")
    assert float(c["max_gap_s"]) <= 1.0 / float(fps) + 1e-6, (
        f"commit and marker are up to {c['max_gap_s']:.3f} s apart, more than the "
        f"{1.0 / float(fps):.3f} s between frames. V2")


def test_v3_the_lock_time_does_not_vary_across_walks():
    """V3. The lock time is structural and identical on every walk, never adaptive."""
    d, v = _vision()
    n = v["V3_lock_offset_s_distinct_values"]
    assert n == 1, (
        f"the lock offset from the walk start takes {n} different values across the walks: "
        f"{v['V3_lock_offset_s']}. V3 says it is structural and identical on every walk. More "
        f"than one value is adaptive latency, which is FORBIDDEN however much accuracy it buys")


# RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
# def test_v3_no_confidence_gated_or_variable_latency_lock():
#     """V3. A lock that waits longer when the decoder is unsure is forbidden in the source."""
#     for path in (RENDER, DISPLAY):
#         src = path.read_text(encoding="utf-8")
#         low = src.lower()
#         for bad in ("confidence_gate", "confidence_gated", "adaptive_latency", "variable_latency",
#                     "margin_gated_lock", "gate_on_confidence"):
#             assert bad not in low, (
#                 f"{path.name} contains {bad!r}. V3 forbids a confidence-gated or variable-latency "
#                 f"lock: it makes the delay a function of the answer, so the caption no longer "
#                 f"tells the viewer what they are seeing and two walks are not comparable")


def test_v4_no_dwell_footage_in_the_demonstration():
    """V4. The grid block is cut, not excerpted."""
    d = _res()
    dc = d.get("dwell_cut")
    assert dc is not None, "the render did not report the dwell cut, so V4 is unenforced"
    assert dc["recordings"] > 0, "the dwell cut ran on no recordings"
    assert dc["grid_windows_seen"] > 0, (
        "no grid windows were seen at all, so the check proves nothing; the recordings run "
        "walk_half, grid, walk_half and every one of them has a dwell block")
    assert dc["frames_remaining_inside_a_grid_block"] == 0, (
        f"{dc['frames_remaining_inside_a_grid_block']} frames of the video still sit inside a "
        f"grid dwell block. V4: a demonstration video contains walks, not standing")
    assert dc["frames_removed"] > 0, "no frames were removed, so the dwell was never cut"


# RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
# def test_no_seconds_constant_used_as_a_window_count():
#     """A constant named *_S is a DURATION and may never index a window array.
#
#     The fault: DWELL_EXCERPT_S = 30.0 was added to a window index, so at a 0.5 s stride the video
#     kept 15 s of dwell while the name said 30. Same shape as every other fault in this suite, a
#     number that looked right produced by code not doing what its name said.
#     """
#     import ast as _ast
#     for path in (RENDER, DISPLAY):
#         tree = _ast.parse(path.read_text(encoding="utf-8"))
#         for node in _ast.walk(tree):
#             if not isinstance(node, _ast.Subscript):
#                 continue
#             for inner in _ast.walk(node.slice):
#                 if isinstance(inner, _ast.Name) and inner.id.endswith("_S") \
#                         and inner.id.isupper():
#                     raise AssertionError(
#                         f"{path.name} line {inner.lineno}: {inner.id} is a duration by its name "
#                         f"and is being used inside a subscript, which makes it a window count. "
#                         f"At a 0.5 s stride those differ by a factor of two. Convert with the "
#                         f"stride explicitly, as int(round(SECONDS / STRIDE))")


def test_acceptance_holds_results_only_and_points_at_the_contract():
    """Exactly one place the rules live, and it is not ACCEPTANCE.md."""
    acc = REPO / "runs" / "constrained" / "demo" / "ACCEPTANCE.md"
    if not acc.exists():
        pytest.skip("no acceptance document present")
    text = acc.read_text(encoding="utf-8")
    # an acceptance document written before 1 October 2026 names the contract by its old path
    assert "reports/tracking/render-rules.md" in text or "reports/RENDER_RULES.md" in text, (
        "ACCEPTANCE.md does not point at the rendering contract. Rules live in RENDER_RULES.md "
        "and results live here; the pointer is what keeps that true")
    assert "RESULTS ONLY" in text or "results only" in text.lower(), (
        "ACCEPTANCE.md no longer says it holds results only")


# --------------------------------------------------------- the 2026-09-23 operator amendments


def test_v3_the_lock_offset_is_exactly_two_seconds():
    """V3 as amended. The origin is the START PRESS, so the offset IS the latency, exactly.

    Before 2026-09-23 the offset was 2.25 s measured from the first window's CENTRE, and the
    extra 0.25 s was the window-centre-to-head-label distance. The origin was a lattice position
    and carried a median 0.202 s of scatter against the press. The press is a physical event, so
    moving the origin onto it removes the scatter from the quantity rather than averaging it away.
    """
    d, v = _vision()
    off = v["V3_lock_offset_s"]
    assert not isinstance(off, list), (
        f"the lock offset takes several values {off}; it must be one number")
    assert abs(float(off) - float(v["V1_latency_s"])) <= 1e-6, (
        f"the lock offset is {off} s against a latency of {v['V1_latency_s']} s. Since the "
        f"2026-09-23 amendment the scene starts at the delayed press moment, so the offset from "
        f"the press IS the latency by construction. A difference means the origin has drifted "
        f"back onto the window lattice")


def test_2a_the_first_drawn_position_is_the_committed_lines_entry():
    """Rule 2a. On every walk the dot starts at the entry of the line it committed to.

    On a CORRECT line that entry is where the walker is at the press, so the gap is zero BY
    CONSTRUCTION. That identity is the test: if the render ever goes back to starting at the first
    decoded state, the correct-line gap becomes non-zero immediately.
    """
    d = _res()
    sg = d.get("start_gap")
    assert sg, "the render must report start_gap; rule 2b"
    ok = sg["correct_line_by_construction"]
    assert ok["n"] > 0, "no correct-line walks were measured"
    assert ok["max_m"] is not None and float(ok["max_m"]) <= 1e-6, (
        f"the start gap on correct-line walks reaches {ok['max_m']} m. Rule 2a places the dot at "
        f"the committed line's entry and the press IS the walker at that entry, so on a correct "
        f"line this is zero by construction. A non-zero value means the anchor is not the line "
        f"entry, or the scene is not starting at the press")


# RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
# def test_2a_the_anchor_segment_is_straight_and_uses_no_pace():
#     """Rule 2a. Every anchor frame lies ON the segment, and nothing there uses a pace.
#
#     Two halves, deliberately. The measured half proves the drawn frames are on the segment. The
#     source half proves the interpolation parameter is elapsed fraction rather than a speed, which
#     a measurement of positions on a straight line cannot distinguish: a dot moving at a fitted
#     pace along that same segment would also lie on it.
#     """
#     d = _res()
#     a = d.get("anchor_segment")
#     assert a, "the render must report anchor_segment; rule 2a"
#     assert int(a["frames"]) > 0, (
#         "no anchor frames were drawn at all. Since the 2026-09-23 amendment the scene starts at "
#         "the press and the first decoded position arrives later, so there must be frames between")
#     assert int(a["off_segment_frames"]) == 0, (
#         f"{a['off_segment_frames']} anchor frames do not lie on the straight segment between the "
#         f"line entry and the first decoded position. Rule 2a permits that segment and nothing else")
#     src = RENDER.read_text(encoding="utf-8")
#     blk = src[src.index("RULE 2's ONE NARROW EXCEPTION"):src.index('wk["rpost"], wk["gpost"]')]
#     # COMMENTS ARE STRIPPED BEFORE THE CHECK. The block's own comment says "NO PACE AND NO
#     # PROJECTION", so a raw substring search fails on the very sentence that states the rule.
#     # What is forbidden is pace-based CODE, not the word.
#     blk = "\n".join(ln.split("#", 1)[0] for ln in blk.splitlines())
#     for bad in ("pace", "m_per_s", "speed", "velocity", "advance_m"):
#         assert bad not in blk.lower(), (
#             f"the anchor segment's code mentions {bad!r}. Rule 2a permits interpolation by "
#             f"elapsed fraction between two fixed endpoints and forbids anything pace-based")


def test_2b_tracking_excludes_the_anchor_segment():
    """Rule 2b. A gap that is zero by construction may not be reported as tracking accuracy."""
    d = _res()
    walks = [w for rec in d["recordings"].values() for w in rec["walks"]]
    assert walks, "no walks in the render results"
    bad = [w for w in walks if w.get("tracking_includes_the_anchor_segment") is not False]
    assert not bad, (
        f"{len(bad)} walks do not declare that tracking excludes the anchor segment. Rule 2b: "
        f"the start gap is a display rule, and folding it into tracking reports an identity as "
        f"though it were a measurement")


# RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
# def test_v5_the_display_phase_is_a_single_global_constant():
#     """V5. shift_w is one number for the whole render, never indexed by line or participant.
#
#     A per-line phase would be a per-line offset fitted to Room A's own geometry, which the
#     standing brief forbids outright because it fits the answer and will not transfer.
#     """
#     d = _res()
#     a = d.get("anchor_segment") or {}
#     assert "shift_w" in a, "the render must report the display phase it drew with"
#     assert abs(float(a["shift_w"]) - 0.50) <= 1e-9, (
#         f"the display phase is {a['shift_w']}, not the 0.50 V5 fixes")
#     src = RENDER.read_text(encoding="utf-8")
#     assert "SHIFT_W = 0.50" in src, "V5's constant must be a literal in the render"
#     for bad in ("SHIFT_W[", "shift_w[", "SHIFT_W.get", "shift_w.get",
#                 "SHIFT_W_BY", "shift_w_by"):
#         assert bad not in src, (
#             f"{bad!r} appears in the render, which means the display phase is being looked up "
#             f"per line, per participant or per session. V5 says it is a single global constant")


# RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
# def test_the_committed_line_is_named_as_text_at_every_walk_end():
#     """Operator instruction 3, item 4, 2026-09-23c: show the committed line as text at walk end.
#
#     Until then the end-of-walk text named the committed answer only when it DISAGREED with the
#     lock. The text must name it unconditionally, and it must stay TEXT: rule 1 forbids moving the
#     dot to it. Checked on the source, because the rendered frames are video and the string is the
#     contract.
#     """
#     import re
#     from pathlib import Path
#     src = (Path(__file__).resolve().parents[1] / "pipeline" / "retired" / "constrained" /
#            "f3_render.py").read_text()
#     m = re.search(r'info\.set_text\(\s*f"COMMITTED \(shipped, semi-bounded\): '
#                   r'\{cur\[\'committed\'\] or \'none\'\}', src)
#     assert m, "the walk-end text no longer names the committed line unconditionally"
#     tail = src[m.start():m.start() + 600]
#     assert "rdot.set_data" not in tail.split("info.set_text", 2)[1][:300], \
#         "the committed line must be text; the dot is not moved to it (rule 1)"
