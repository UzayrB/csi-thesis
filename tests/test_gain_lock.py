"""Tests for the gain-lock check.

The direction matters and is easy to state backwards: with the gain LOCKED,
CSI amplitude follows the field and so tracks RSSI. An AGC that is still
active compensates instead, holding amplitude roughly flat while RSSI moves.
Getting this the wrong way round would report a working lock as broken and a
broken one as working, so it is pinned down here.

No hardware required.
"""

from __future__ import annotations

import pytest

from pipeline.io.check_gain_lock import (
    MIN_RSSI_DELTA_DB,
    TRACKING_RATIO_FAIL,
    TRACKING_RATIO_PASS,
    compare,
)


def cap(node: str, rssi: float, amp_db: float) -> dict:
    """Build a capture summary with a given RSSI and amplitude."""
    return {"node": node, "n": 5000, "rssi_dbm": rssi, "amp": 30.0, "amp_db": amp_db, "gain_values": [1.0]}


def test_amplitude_tracking_rssi_means_the_lock_engaged() -> None:
    """A fixed amplifier passes the field change straight through."""
    r = compare(cap("RX1", -65.0, 30.0), cap("RX1", -77.0, 18.0))
    assert r["verdict"] == "locked"
    assert r["ratio"] == pytest.approx(1.0)


def test_amplitude_holding_still_means_the_agc_is_active() -> None:
    """A working AGC absorbs the change, which is the failure case here."""
    r = compare(cap("RX1", -65.0, 30.0), cap("RX1", -77.0, 29.5))
    assert r["verdict"] == "agc active"
    assert "did not engage" in r["why"]


def test_partial_tracking_is_reported_as_inconclusive() -> None:
    """Half-tracking is not evidence either way, and says so."""
    r = compare(cap("RX1", -65.0, 30.0), cap("RX1", -77.0, 24.6))
    assert TRACKING_RATIO_FAIL < r["ratio"] < TRACKING_RATIO_PASS
    assert r["verdict"] == "inconclusive"


def test_too_small_a_power_change_is_inconclusive() -> None:
    """Below a few dB the AGC would not have moved either way."""
    r = compare(cap("RX1", -65.0, 30.0), cap("RX1", -67.0, 28.0))
    assert abs(r["d_rssi_db"]) < MIN_RSSI_DELTA_DB
    assert r["verdict"] == "inconclusive"
    assert "Move the transmitter" in r["why"]


def test_it_works_when_the_signal_gets_stronger_too() -> None:
    """The test is symmetric: near and far can be given either way round."""
    r = compare(cap("RX1", -77.0, 18.0), cap("RX1", -65.0, 30.0))
    assert r["verdict"] == "locked"
    assert r["d_rssi_db"] == pytest.approx(12.0)


def test_verdict_wording_states_the_direction() -> None:
    """The explanation must not leave the direction ambiguous.

    Reporting a working lock as broken would send someone reflashing three
    boards to fix nothing.
    """
    locked = compare(cap("RX1", -65.0, 30.0), cap("RX1", -77.0, 18.0))
    assert "amplitude follows the field" in locked["why"]
    agc = compare(cap("RX1", -65.0, 30.0), cap("RX1", -77.0, 29.8))
    assert "AGC absorbed" in agc["why"]
