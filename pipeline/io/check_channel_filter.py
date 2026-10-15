"""Test whether ``channel_filter_en`` is degrading the across-subcarrier shape.

The receiver's AGC normalises level away before storage (measured 8 September
2026: -11.8 dB in, -0.5 dB out), so the pipeline is shape-based: everything
downstream reads frequency-selective fading across subcarriers, never
amplitude. IDF's own ``csi_config`` header says ``channel_filter_en``
"enable[s] channel filter to smooth adjacent sub-carrier. Disable it to keep
independence of adjacent sub-carrier." That smoothing sits directly on top of
the one thing the pipeline now depends on, so this module measures whether
turning it off actually helps.

WHAT THIS MEASURES
-------------------
Two capture directories, each holding a simultaneous multi-node ``.bin``
capture at a different geometry (near/far, or with an obstacle in the path).
For each node, after dead-bin masking and the mandatory per-packet shape
normalisation (:func:`pipeline.io.clean.normalise_shape`):

* **correlation** -- Pearson r between the near and far mean shape vectors.
  Lower means the two positions are more distinguishable.
* **ratio** -- RMS shape difference between conditions, divided by the RMS
  of the pooled within-condition standard deviation. This is the effective
  SNR of the position signal: how big the between-position shape change is
  relative to the noise floor a fixed position produces on its own.

Comparing these two numbers for a board with ``channel_filter_en = false``
against a board left at ``true`` is the whole experiment. A higher ratio
(and a lower correlation) on the modified board means disabling the filter
buys separability; a ratio that only gets worse means the filter was not the
problem, or noise dominates more than smoothing did.

HOW TO RUN THE EXPERIMENT
--------------------------
Room still, a clear difference in geometry between the two conditions, both
boards attached and captured together so the comparison is not confounded by
time or room state::

    make baseline BASELINE_S=30 OUT=filtertest/near NODES="..."
    # move the transmitter, or put an obstacle in the path
    make baseline BASELINE_S=30 OUT=filtertest/far  NODES="..."
    python -m pipeline.io.check_channel_filter filtertest/near filtertest/far --modified RX2

Do not reboot the receivers between the two captures: nothing here depends on
a boot-time baseline the way the gain check does, but a reboot costs time and
buys nothing.
"""

from __future__ import annotations

import argparse
import glob
import os
import sys
from typing import Optional, Sequence

import numpy as np

from pipeline.io.clean import normalise_shape, select_subcarriers
from pipeline.io.capture_logger import read_capture_file

#: Packets skipped at the start of each capture, to match the gain check and
#: avoid any radio warm-up transient at the very beginning of a run.
SKIP_PACKETS: int = 300


def summarise_capture(path: str) -> dict:
    """Compute the normalised-shape summary of one capture, for one node.

    Args:
        path: A ``.bin`` capture file.

    Returns:
        Dict with the node id, packet count, the mean shape vector across
        packets, and the per-bin variance of shape within this capture.

    Constraints:
        Dead bins are dropped and each packet is normalised to its own mean
        before anything is averaged, per the project's mandatory shape
        normalisation. Amplitude itself is never compared: the AGC has
        already erased what it meant.
    """
    header, fr = read_capture_file(path)
    fr = fr[SKIP_PACKETS:]
    n = len(fr)
    if n == 0:
        raise ValueError(f"{path} has too few packets to judge")

    data = fr["data"].astype(np.float32).reshape(n, -1, 2)
    amp = np.sqrt((data**2).sum(axis=-1))
    amp = select_subcarriers(amp)
    shape = normalise_shape(amp)

    return {
        "node": header.get("node_id") or os.path.basename(path),
        "n": n,
        "mean_shape": shape.mean(axis=0),
        "var_shape": shape.var(axis=0),
    }


def compare_shapes(near: dict, far: dict) -> dict:
    """Compare one node's near and far shape summaries.

    Args:
        near: :func:`summarise_capture` output for the near/reference
            geometry.
        far: The same, for the far/obstructed geometry.

    Returns:
        Dict with the node id, ``correlation`` (Pearson r between the two
        mean shape vectors, lower is more separable), ``between`` (RMS shape
        difference across bins), ``within`` (RMS of the pooled per-bin
        standard deviation, the noise floor), and ``ratio`` (``between`` /
        ``within``, the effective SNR of the position signal).

    Raises:
        ValueError: If the two summaries do not share the same live
            subcarrier count, which would mean they came from different
            dead-bin sets and are not comparable bin for bin.
    """
    mn, mf = near["mean_shape"], far["mean_shape"]
    vn, vf = near["var_shape"], far["var_shape"]
    if mn.shape != mf.shape:
        raise ValueError(f"bin count mismatch: near has {mn.shape[0]}, far has {mf.shape[0]}")

    correlation = float(np.corrcoef(mn, mf)[0, 1])
    diff = mf - mn
    between = float(np.sqrt(np.mean(diff**2)))
    within = float(np.sqrt(np.mean((vn + vf) / 2.0)))
    ratio = between / within if within > 0 else float("inf")

    return {
        "node": near["node"],
        "n_near": near["n"],
        "n_far": far["n"],
        "correlation": correlation,
        "between": between,
        "within": within,
        "ratio": ratio,
    }


def run(near_dir: str, far_dir: str, modified: Optional[str] = None) -> int:
    """Compare two capture directories node by node and print the verdict.

    Args:
        near_dir: Directory of the near/reference-geometry capture.
        far_dir: Directory of the far/obstructed-geometry capture.
        modified: Node id (e.g. ``"RX2"``) carrying the firmware under test.
            If given, that node's ratio and correlation are set against the
            best of the remaining (unmodified) nodes and a recommendation is
            printed.

    Returns:
        0 always; this is a measurement, not a pass/fail gate.
    """
    near_files = {os.path.basename(p): p for p in glob.glob(os.path.join(near_dir, "**", "*RX*.bin"), recursive=True)}
    far_files = {os.path.basename(p): p for p in glob.glob(os.path.join(far_dir, "**", "*RX*.bin"), recursive=True)}
    shared = sorted(set(near_files) & set(far_files))

    if not shared:
        print(f"No matching RX .bin files in {near_dir} and {far_dir}")
        return 2

    print("=" * 96)
    print("CHANNEL FILTER CHECK")
    print("=" * 96)
    print("Lower correlation and a higher ratio both mean the two positions are more")
    print("distinguishable in shape. ratio = between-condition shape RMS / within-condition")
    print("noise RMS: the effective SNR of the position signal.")
    print()
    head = f"{'node':<8} {'n near':>8} {'n far':>8} {'corr':>8} {'between':>9} {'within':>9} {'ratio':>8}"
    print(head)
    print("-" * len(head))

    results: dict[str, dict] = {}
    for name in shared:
        a = summarise_capture(near_files[name])
        b = summarise_capture(far_files[name])
        r = compare_shapes(a, b)
        results[r["node"]] = r
        print(
            f"{r['node']:<8} {r['n_near']:>8} {r['n_far']:>8} "
            f"{r['correlation']:>8.3f} {r['between']:>9.4f} {r['within']:>9.4f} {r['ratio']:>8.3f}"
        )

    print("-" * len(head))

    if modified is not None:
        if modified not in results:
            print(f"\n--modified {modified} was not among the shared nodes: {sorted(results)}")
            return 2
        others = {k: v for k, v in results.items() if k != modified}
        if not others:
            print(f"\nOnly {modified} present; no unmodified board to compare against.")
            return 2
        best_other = max(others.values(), key=lambda r: r["ratio"])

        print()
        print(f"MODIFIED   ({modified}): ratio {results[modified]['ratio']:.3f}, correlation {results[modified]['correlation']:.3f}")
        print(f"UNMODIFIED ({best_other['node']}): ratio {best_other['ratio']:.3f}, correlation {best_other['correlation']:.3f}")
        print()

        ratio_gain = results[modified]["ratio"] - best_other["ratio"]
        corr_gain = best_other["correlation"] - results[modified]["correlation"]
        if ratio_gain > 0 and corr_gain > 0:
            print(
                f"RESULT: {modified} improved on both measures (ratio +{ratio_gain:.3f}, "
                f"correlation {corr_gain:+.3f} lower). channel_filter_en=false is worth "
                f"flashing to the other receivers."
            )
        elif ratio_gain <= 0 and corr_gain <= 0:
            print(
                f"RESULT: {modified} did not improve on either measure (ratio {ratio_gain:+.3f}, "
                f"correlation {-corr_gain:+.3f}). Revert {modified} and leave all three at "
                f"channel_filter_en=true."
            )
        else:
            print(
                "RESULT: mixed (ratio and correlation disagree). Not a clean signal either way; "
                "repeat with a larger geometry difference before deciding."
            )

    print("=" * 96)
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Entry point for ``python -m pipeline.io.check_channel_filter``."""
    p = argparse.ArgumentParser(
        prog="python -m pipeline.io.check_channel_filter",
        description="Measure whether disabling channel_filter_en improves across-subcarrier "
        "shape separability, by comparing two simultaneous multi-node captures at different "
        "geometries.",
    )
    p.add_argument("near", help="capture directory for the near/reference geometry")
    p.add_argument("far", help="capture directory for the far/obstructed geometry")
    p.add_argument("--modified", default=None, help="node id (e.g. RX2) flashed with channel_filter_en=false")
    args = p.parse_args(argv)
    return run(args.near, args.far, args.modified)


if __name__ == "__main__":
    sys.exit(main())
