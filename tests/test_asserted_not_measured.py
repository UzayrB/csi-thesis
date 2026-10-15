"""Two guards against a document asserting what the code did not do.

WHY THESE EXIST. It has happened three times in this project:

  1. A render stage listed "E8 highlight" in its items array and never implemented it.
  2. A coverage figure of 100 percent was written up as a tracking result when the windows it
     covered were placed by dead reckoning.
  3. A render job reported rc=0 and thirteen files, and the files were 0.07 MB truncated stubs
     because every frame raised and the exception was caught per frame.

All three passed review because the artefact under inspection was the claim, not the measurement.
A test cannot read intent, but it can refuse a status that was never computed and a video that is
too small to contain its own frames.
"""

from __future__ import annotations

import ast
import json
import os
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]

#: Stages whose results are frozen and quoted. They are recorded in the audit rather than edited,
#: because changing them would move a number that is already on record.
FROZEN_EXEMPT = {
    # RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
#     "pipeline/retired/constrained/stage4_unified.py",
    # RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
#     "pipeline/retired/constrained/stage5_live.py",
}

#: A status may be a literal only on a failure path, where the stage is reporting that it could
#: not run at all. A literal True is never acceptable: it is a claim, not a measurement.
def _status_calls(tree):
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        name = getattr(fn, "id", None) or getattr(fn, "attr", None)
        if name in ("findings", "write_findings") and len(node.args) >= 2:
            yield node, node.args[1]


def _py_files():
    for p in (REPO / "pipeline").rglob("*.py"):
        if "__pycache__" in str(p):
            continue
        if str(p.relative_to(REPO)).replace(os.sep, "/") in FROZEN_EXEMPT:
            continue
        yield p


def test_no_status_is_a_hardcoded_true():
    """A PASSED must be derived from something the run measured."""
    bad = []
    for p in _py_files():
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node, arg in _status_calls(tree):
            if isinstance(arg, ast.Constant) and arg.value is True:
                bad.append(f"{p.relative_to(REPO)}:{node.lineno}")
    assert not bad, ("these stages write PASSED without computing it, which is how a document "
                     f"comes to assert what the code did not do: {bad}")


def test_no_items_array_claims_without_evidence():
    """A module that DECLARES items must also evidence them from measured quantities."""
    bad = []
    for p in _py_files():
        src = p.read_text(encoding="utf-8")
        if "items_declared" in src and "items_evidenced" not in src:
            bad.append(str(p.relative_to(REPO)))
        if "items_implemented" in src:
            bad.append(f"{p.relative_to(REPO)}: items_implemented asserts rather than evidences")
    assert not bad, f"items claimed without evidence: {bad}"


#: Bytes per frame below which an mp4 cannot plausibly hold its own frames. The truncated stubs of
#: 2026-09-18 were about 18 bytes per frame; a real render of the same figure is about 550.
MIN_BYTES_PER_FRAME = 120


def _demo_videos():
    d = REPO / "runs" / "constrained" / "demo"
    return sorted(d.glob("*.mp4")) if d.is_dir() else []


def test_rendered_videos_are_not_truncated_stubs():
    """Size against frame count, because an exit code of zero proved nothing here.

    The renderer catches a per-frame exception and carries on, so ffmpeg can close a file that has
    almost no frames in it while the job still exits 0 and the stage still reports the video. The
    only honest check is whether the bytes could hold the frames.
    """
    vids = _demo_videos()
    if not vids:
        pytest.skip("no demonstration renders present")

    # A video named in a results file but absent from the demonstration folder is a FAILURE unless
    # it was deliberately retired, which means it is sitting in a retirement folder beside a
    # manifest. A render set that is superseded is moved, never deleted, so "missing" and "retired"
    # are distinguishable and only the first one is a defect. Added 2026-09-19, when the live
    # render replaced the bounded set and this test could not tell the two apart.
    retired = set()
    rdir = REPO / "testing" / "demo_retired"
    if rdir.is_dir():
        for man in rdir.glob("*/MANIFEST.json"):
            retired |= {f.name for f in man.parent.iterdir() if f.suffix == ".mp4"}

    # rc8_demo's bounded and highlight renders were retired to testing/demo_retired/ on 2026-09-19,
    # and their manifest went with testing/ on 2026-09-24 (git tag pre-cleanup). Only the render the
    # demonstration ships, f3_render's, is checked; a future retirement still uses the manifest above.
    sources = [(REPO / "runs" / "constrained" / "fh" / "f3_render" / "results.json", (None,))]
    checked, bad = 0, []
    for res, keys in sources:
        if not res.exists():
            continue
        d = json.loads(res.read_text(encoding="utf-8"))
        fps = float(d.get("fps") or 10)
        for rec in d.get("recordings", {}).values():
            for key in keys:
                blk = rec if key is None else (rec.get(key) or {})
                mp4 = blk.get("mp4") or blk.get("video")
                # the live renderer records a frame COUNT; the bounded one records seconds
                frames = blk.get("n_frames") or (float(blk["seconds"]) * fps
                                                 if blk.get("seconds") else None)
                if not mp4 or not frames:
                    continue
                name = pathlib.Path(mp4).name
                f = REPO / mp4 if "/" in mp4 else REPO / "runs" / "constrained" / "demo" / name
                if not f.exists():
                    if name not in retired:
                        bad.append(f"{mp4}: recorded in results, missing on disk, and NOT in any "
                                   f"retirement manifest")
                    continue
                checked += 1
                frames = max(1.0, float(frames))
                per = f.stat().st_size / frames
                if per < MIN_BYTES_PER_FRAME:
                    bad.append(f"{mp4}: {f.stat().st_size} bytes for ~{frames:.0f} frames "
                               f"= {per:.0f} B/frame, below {MIN_BYTES_PER_FRAME}")
    assert not bad, f"renders are implausibly small for their frame count: {bad}"
    assert checked, "no video was actually checked, so this test proved nothing"
