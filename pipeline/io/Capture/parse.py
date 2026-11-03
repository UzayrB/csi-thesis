# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: Parse raw ESP32 CSI_DATA serial lines into validated CSI records.

from __future__ import annotations

import base64
import binascii
import re
import time
from dataclasses import dataclass, field
from typing import Iterable, Optional

import numpy as np

CSI_LEN: int = 256

N_SUBCARRIERS: int = 128

N_FIELDS: int = 25

N_FIELDS_B64: int = 26

GAIN_SCALE: float = 10000.0

CSI_PREFIX: str = "CSI_DATA,"

STA_MAC_RE = re.compile(r"mode\s*:\s*sta\s*\(([0-9a-fA-F:]{17})\)")


# Tally of parse outcomes, one instance per node per run.
@dataclass
class ParseCounters:

    lines_seen: int = 0
    ok: int = 0
    non_csi: int = 0
    torn: int = 0
    bad_field_count: int = 0
    bad_metadata: int = 0
    bad_len: int = 0
    bad_data: int = 0

    # Count of lines that looked like CSI rows but failed validation.
    @property
    def malformed(self) -> int:
        return self.torn + self.bad_field_count + self.bad_metadata + self.bad_len + self.bad_data

    # Return the counters as a plain dict for JSON sidecars and reports.
    def as_dict(self) -> dict[str, int]:
        return {
            "lines_seen": self.lines_seen,
            "ok": self.ok,
            "non_csi": self.non_csi,
            "torn": self.torn,
            "bad_field_count": self.bad_field_count,
            "bad_metadata": self.bad_metadata,
            "bad_len": self.bad_len,
            "bad_data": self.bad_data,
            "malformed": self.malformed,
        }


# One validated CSI packet from one receiver node.
@dataclass
class CsiRecord:

    node_id: str
    t_mono: float
    t_host: float
    pkt_id: int
    mac: str
    rssi: int
    rate: int
    sig_mode: int
    mcs: int
    bandwidth: int
    smoothing: int
    not_sounding: int
    aggregation: int
    stbc: int
    fec_coding: int
    sgi: int
    noise_floor: int
    ampdu_cnt: int
    channel: int
    secondary_channel: int
    local_timestamp: int
    ant: int
    sig_len: int
    rx_format: int
    csi_len: int
    first_word: int
    data: np.ndarray = field(repr=False)
    compensate_gain: float = 1.0


_INT_FIELDS: tuple[tuple[int, str], ...] = (
    (1, "pkt_id"),
    (3, "rssi"),
    (4, "rate"),
    (5, "sig_mode"),
    (6, "mcs"),
    (7, "bandwidth"),
    (8, "smoothing"),
    (9, "not_sounding"),
    (10, "aggregation"),
    (11, "stbc"),
    (12, "fec_coding"),
    (13, "sgi"),
    (14, "noise_floor"),
    (15, "ampdu_cnt"),
    (16, "channel"),
    (17, "secondary_channel"),
    (18, "local_timestamp"),
    (19, "ant"),
    (20, "sig_len"),
    (21, "rx_format"),
    (22, "csi_len"),
    (23, "first_word"),
)


# Parse the quoted CSI data list into an int8 array.
def parse_data_list(text: str) -> Optional[np.ndarray]:
    s = text.strip().strip('"').strip()
    if len(s) < 2 or s[0] != "[" or s[-1] != "]":
        return None
    body = s[1:-1].strip()
    if not body:
        return None
    parts = body.split(",")
    if len(parts) != CSI_LEN:
        return None
    out = np.empty(CSI_LEN, dtype=np.int8)
    for i, p in enumerate(parts):
        p = p.strip()
        if not p:
            return None
        try:
            v = int(p)
        except ValueError:
            return None
        if v < -128 or v > 127:
            return None
        out[i] = v
    return out


# Decode a base64 CSI payload into an int8 array.
def parse_data_b64(text: str) -> Optional[np.ndarray]:
    s = text.strip().strip('"').strip()
    if not s:
        return None
    try:
        blob = base64.b64decode(s, validate=True)
    except (binascii.Error, ValueError):
        return None
    if len(blob) != CSI_LEN:
        return None
    return np.frombuffer(blob, dtype=np.int8)


# Parse one raw serial line into a validated:class:CsiRecord.
def parse_line(
    raw: str,
    node_id: str = "",
    counters: Optional[ParseCounters] = None,
    t_mono: Optional[float] = None,
    t_host: Optional[float] = None,
) -> Optional[CsiRecord]:
    if counters is not None:
        counters.lines_seen += 1
    if t_mono is None:
        t_mono = time.monotonic()
    if t_host is None:
        t_host = time.time()

    line = raw.strip()
    if not line.startswith(CSI_PREFIX):
        if CSI_PREFIX in line:
            if counters is not None:
                counters.torn += 1
        elif counters is not None:
            counters.non_csi += 1
        return None

    parts = line.split(",", N_FIELDS - 1)
    if len(parts) != N_FIELDS:
        if counters is not None:
            counters.bad_field_count += 1
        return None

    tail = parts[24]
    if tail.startswith('"') or tail.startswith("["):
        b64 = False
        payload = tail
        gain_text = ""
    else:
        sub = tail.split(",", 1)
        if len(sub) != 2:
            if counters is not None:
                counters.bad_field_count += 1
            return None
        b64 = True
        gain_text, payload = sub

    values: dict[str, int] = {}
    for idx, name in _INT_FIELDS:
        try:
            values[name] = int(parts[idx])
        except ValueError:
            if counters is not None:
                counters.bad_metadata += 1
            return None

    if values["csi_len"] != CSI_LEN:
        if counters is not None:
            counters.bad_len += 1
        return None

    if b64:
        try:
            gain = int(gain_text) / GAIN_SCALE
        except ValueError:
            if counters is not None:
                counters.bad_metadata += 1
            return None
        data = parse_data_b64(payload)
    else:
        gain = 1.0
        data = parse_data_list(payload)

    if data is None:
        if counters is not None:
            counters.bad_data += 1
        return None

    if counters is not None:
        counters.ok += 1
    return CsiRecord(
        node_id=node_id,
        t_mono=t_mono,
        t_host=t_host,
        mac=parts[2],
        data=data,
        compensate_gain=gain,
        **values,
    )


# Convert a record's interleaved int8 CSI into subcarrier amplitudes.
def extract_amplitude(record: CsiRecord) -> np.ndarray:
    pairs = record.data.astype(np.float32).reshape(N_SUBCARRIERS, 2)
    imag = pairs[:, 0]
    real = pairs[:, 1]
    amp = np.sqrt(imag * imag + real * real, dtype=np.float32)
    if record.compensate_gain != 1.0:
        amp *= np.float32(record.compensate_gain)
    return amp


# Recover a receiver's own station MAC from its boot banner.
def extract_sta_mac(raw: str) -> Optional[str]:
    m = STA_MAC_RE.search(raw)
    return m.group(1).lower() if m else None


# Parse many raw serial lines from one node.
def parse_lines(
    lines: Iterable[str],
    node_id: str = "",
    counters: Optional[ParseCounters] = None,
) -> list[CsiRecord]:
    out: list[CsiRecord] = []
    for line in lines:
        rec = parse_line(line, node_id=node_id, counters=counters)
        if rec is not None:
            out.append(rec)
    return out
