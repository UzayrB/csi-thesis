"""Parse raw ESP32 ``CSI_DATA`` serial lines into validated CSI records.

The receivers run Espressif's ``esp-csi`` ``csi_recv`` example, whose console
prints one comma-separated ``CSI_DATA`` row per received packet, preceded at
boot by a garbage burst (ROM bootloader at a different baud) and by ESP-IDF
log lines. Log lines keep appearing during a run, and a line can be torn in
half when a read boundary falls mid-line.

The stock Espressif parser crashes on that. This one must not. Every
function here is total: bad input produces ``None`` and a counter increment,
never an exception.

PROJECT RULES ENCODED HERE
--------------------------
* Every accepted packet asserts the declared ``len`` field is 256 AND that
  the data list holds exactly 256 int8 values: 128 complex pairs, imaginary
  first then real, LLTF followed by HT-LTF.
* Malformed lines are COUNTED and DROPPED. Parsing NEVER raises.
* Every record is tagged with ``node_id`` and host receive timestamps.

TWO WIRE FORMATS
----------------
Both are accepted, and both yield identical records, so the firmware can be
rolled back without touching the pipeline.

*Decimal* is upstream esp-csi: 25 fields, the payload a quoted list of 256
decimal values with gain compensation already applied on the device::

    type,id,mac,rssi,rate,sig_mode,mcs,bandwidth,smoothing,not_sounding,
    aggregation,stbc,fec_coding,sgi,noise_floor,ampdu_cnt,channel,
    secondary_channel,local_timestamp,ant,sig_len,rx_format,len,first_word,data

    CSI_DATA,9213,1a:00:00:00:00:00,-73,11,1,0,0,1,1,0,0,0,0,-96,0,11,0,
    15771,0,47,1,256,1,"[47,-16,2,0, ... ]"

*Base64* is this project's firmware: the same metadata, then ``gain_x10000``,
then the raw payload as 344 base64 characters::

    ...,len,first_word,gain_x10000,data_b64

    CSI_DATA,9213,1a:00:00:00:00:00,-73,11,1,0,0,1,1,0,0,0,0,-96,0,11,0,
    15771,0,47,1,256,1,10000,L/ACAP8DAAAA ... AA==

A decimal row costs about 900 bytes and caps the 921600 baud console near
102 rows per second; a base64 row costs about 440 and raises that to roughly
209, which is what makes 150 Hz sampling possible. Base64 also contains no
commas and is fixed width, so rows split cleanly and console bandwidth no
longer varies with the values.

The two are told apart by the payload's first character, not by field count,
because the decimal payload is itself full of commas.

Note that ``mac`` is the TRANSMITTER's ESP-NOW address and is identical on
every receiver. It does not identify the node; ``node_id`` does, and it is
supplied by the caller.
"""

from __future__ import annotations

import base64
import binascii
import re
import time
from dataclasses import dataclass, field
from typing import Iterable, Optional

import numpy as np

#: Number of int8 values in the CSI payload: 128 complex pairs.
CSI_LEN: int = 256

#: Number of complex subcarriers, i.e. ``CSI_LEN // 2``.
N_SUBCARRIERS: int = 128

#: Number of comma-separated fields in a decimal ``CSI_DATA`` row (upstream
#: esp-csi format, payload as a quoted list of 256 decimal values).
N_FIELDS: int = 25

#: Number of fields in a base64 ``CSI_DATA`` row (project firmware): the same
#: metadata, then ``gain_x10000``, then the payload as base64. Base64 contains
#: no commas, so both formats split cleanly on the same separator.
N_FIELDS_B64: int = 26

#: The device cannot print floats with ``ets_printf``, so the gain
#: compensation factor is sent as an integer scaled by this and divided back
#: out here.
GAIN_SCALE: float = 10000.0

#: Marker that begins every CSI row.
CSI_PREFIX: str = "CSI_DATA,"

#: Matches the boot banner line that reveals a receiver's own station MAC,
#: e.g. ``wifi:mode : sta (68:09:47:4c:ef:b4)``.
STA_MAC_RE = re.compile(r"mode\s*:\s*sta\s*\(([0-9a-fA-F:]{17})\)")


@dataclass
class ParseCounters:
    """Tally of parse outcomes, one instance per node per run.

    Every rejected line increments exactly one rejection counter, so
    ``lines_seen`` equals ``ok`` plus the sum of the rejection counters.

    Attributes:
        lines_seen: Total lines offered to :func:`parse_line`.
        ok: Lines that produced a valid :class:`CsiRecord`.
        non_csi: Lines that were not CSI rows at all: ESP-IDF logs, boot
            banners, blank lines, bootloader garbage.
        torn: Lines containing the ``CSI_DATA`` marker somewhere other than
            the start, i.e. a row glued onto the tail of something else.
        bad_field_count: Rows whose field count was not :data:`N_FIELDS`,
            which is what a truncated row looks like.
        bad_metadata: Rows whose numeric metadata fields would not parse.
        bad_len: Rows whose declared ``len`` field was not
            :data:`CSI_LEN`; counted separately because a receiver
            configured for LLTF only reports 128 and the whole run is then
            invalid rather than merely lossy.
        bad_data: Rows whose quoted data list was malformed, truncated, or
            did not hold exactly :data:`CSI_LEN` int8 values.
    """

    lines_seen: int = 0
    ok: int = 0
    non_csi: int = 0
    torn: int = 0
    bad_field_count: int = 0
    bad_metadata: int = 0
    bad_len: int = 0
    bad_data: int = 0

    @property
    def malformed(self) -> int:
        """Count of lines that looked like CSI rows but failed validation.

        Excludes :attr:`non_csi`, which counts ordinary log output rather
        than corruption.
        """
        return self.torn + self.bad_field_count + self.bad_metadata + self.bad_len + self.bad_data

    def as_dict(self) -> dict[str, int]:
        """Return the counters as a plain dict for JSON sidecars and reports."""
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


@dataclass
class CsiRecord:
    """One validated CSI packet from one receiver node.

    Attributes:
        node_id: Receiver identifier, supplied by the caller. The ``mac``
            field cannot serve this role: it is the transmitter's address
            and is the same on every node.
        t_mono: Host receive time from :func:`time.monotonic`, used for all
            rate and interval arithmetic because it cannot jump.
        t_host: Host receive time from :func:`time.time`, wall-clock seconds
            since the epoch, used for correlating with the anchor log.
        pkt_id: The ``id`` field: the transmitter's packet counter. It is
            shared across receivers because every node hears the same
            broadcast, so gaps here measure that node's drops. May wrap.
        mac: Transmitter ESP-NOW address, e.g. ``1a:00:00:00:00:00``.
        rssi: Received signal strength in dBm.
        rate: PHY rate index.
        sig_mode: 0 = non-HT, 1 = HT, 3 = VHT.
        mcs: Modulation and coding scheme index.
        bandwidth: 0 = 20 MHz, 1 = 40 MHz.
        smoothing: PHY smoothing flag.
        not_sounding: PHY not-sounding flag.
        aggregation: 0 = MPDU, 1 = AMPDU.
        stbc: Space-time block coding flag.
        fec_coding: 0 = BCC, 1 = LDPC.
        sgi: Short guard interval flag.
        noise_floor: Noise floor in dBm.
        ampdu_cnt: AMPDU counter.
        channel: Primary Wi-Fi channel.
        secondary_channel: 0 = none, 1 = above, 2 = below.
        local_timestamp: Receiver-side microsecond timestamp. Each node has
            its own unsynchronised clock, so this is not comparable across
            nodes; use :attr:`t_mono` for cross-node alignment.
        ant: Receive antenna index.
        sig_len: Length of the received packet.
        rx_format: 0 = non-HT, 1 = HT, 2 = VHT.
        csi_len: Declared CSI payload length. Always :data:`CSI_LEN` on an
            accepted record.
        first_word: First-word-invalid flag from the driver.
        data: Raw CSI as ``int8`` of shape ``(256,)``, interleaved
            (imaginary, real) per subcarrier, LLTF then HT-LTF.
        compensate_gain: AGC gain compensation factor for this packet.

            In the base64 format the device sends the payload UNSCALED and
            reports this factor separately, so the host applies it; scaling
            on the device would widen every value to int16 and double the
            payload. In the legacy decimal format the device has already
            applied it, so this is 1.0. Either way
            :func:`extract_amplitude` returns comparable amplitudes, and
            nothing downstream needs to know which format was captured.
    """

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


# Order of the integer metadata fields as they appear in the row, excluding
# ``type`` (index 0), ``mac`` (index 2) and ``data`` (index 24).
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


def parse_data_list(text: str) -> Optional[np.ndarray]:
    """Parse the quoted CSI data list into an int8 array.

    Args:
        text: The final field of a CSI row, e.g. ``"[47,-16,2,0,...]"``.
            Surrounding double quotes and whitespace are tolerated.

    Returns:
        Int8 array of shape ``(256,)``, or ``None`` if the list is
        malformed, truncated, holds a non-integer, holds a value outside the
        int8 range, or does not hold exactly :data:`CSI_LEN` values.

    Constraints:
        Never raises. A torn line most often shows up here, as a list whose
        closing bracket is missing.
    """
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


def parse_data_b64(text: str) -> Optional[np.ndarray]:
    """Decode a base64 CSI payload into an int8 array.

    Args:
        text: The final field of a base64 CSI row: 344 base64 characters
            encoding 256 raw bytes. Surrounding whitespace is tolerated.

    Returns:
        Int8 array of shape ``(256,)``, or ``None`` if the text is not valid
        base64 or does not decode to exactly :data:`CSI_LEN` bytes.

    Constraints:
        Never raises. A line torn mid-payload decodes to the wrong length,
        or fails the alphabet check, and is rejected either way.
    """
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


def parse_line(
    raw: str,
    node_id: str = "",
    counters: Optional[ParseCounters] = None,
    t_mono: Optional[float] = None,
    t_host: Optional[float] = None,
) -> Optional[CsiRecord]:
    """Parse one raw serial line into a validated :class:`CsiRecord`.

    Args:
        raw: One line of serial text, already decoded with
            ``errors="replace"``. A trailing newline is tolerated.
        node_id: Receiver identifier to tag the record with. The caller
            supplies it; it cannot be recovered from the line.
        counters: Optional :class:`ParseCounters` updated in place. Exactly
            one counter is incremented per call, plus ``lines_seen``.
        t_mono: Host monotonic receive time. Defaults to now.
        t_host: Host wall-clock receive time. Defaults to now.

    Returns:
        A :class:`CsiRecord` if the line is a complete, valid CSI row,
        otherwise ``None``.

    Constraints:
        * NEVER raises, for any input string, including empty strings,
          bootloader garbage and replacement characters.
        * Rejects unless the declared ``len`` field is exactly
          :data:`CSI_LEN` and the data list holds exactly :data:`CSI_LEN`
          int8 values.
        * The returned record always carries ``node_id`` and both host
          timestamps.
    """
    if counters is not None:
        counters.lines_seen += 1
    if t_mono is None:
        t_mono = time.monotonic()
    if t_host is None:
        t_host = time.time()

    line = raw.strip()
    if not line.startswith(CSI_PREFIX):
        # A row glued onto the tail of a log line is torn, not merely
        # uninteresting; distinguish the two so the report is diagnostic.
        if CSI_PREFIX in line:
            if counters is not None:
                counters.torn += 1
        elif counters is not None:
            counters.non_csi += 1
        return None

    # Split only as far as the shared metadata, because the decimal payload
    # is full of commas and must not be cut into. Everything after that is
    # the tail, whose shape tells the two formats apart: the decimal payload
    # opens with a quoted bracket, while the base64 format puts the gain
    # field there and the payload after one more comma.
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
        # The decimal format applies gain compensation on the device, so
        # there is nothing left for the host to apply.
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


def extract_amplitude(record: CsiRecord) -> np.ndarray:
    """Convert a record's interleaved int8 CSI into subcarrier amplitudes.

    Args:
        record: A validated :class:`CsiRecord`.

    Returns:
        Float32 array of shape ``(128,)``, one magnitude per subcarrier,
        computed as ``sqrt(imag**2 + real**2)`` over the interleaved pairs.

    Constraints:
        * Amplitude only; phase is computed nowhere and stored nowhere.
        * TODO(null-bins): no null or pilot subcarrier stripping is done
          here. The 128 pairs are LLTF (64 subcarriers, of which the DC bin
          and the guard bins carry nothing) followed by HT-LTF (64 more,
          likewise). Those bins are near-zero noise and must be removed
          before any learning, but the mask depends on the measured
          bandwidth and secondary-channel setting, so it belongs in
          ``pipeline/clean/common.select_subcarriers`` once a real capture
          exists to confirm which bins are dead. Nothing downstream may
          assume these 128 values are all informative.
    """
    pairs = record.data.astype(np.float32).reshape(N_SUBCARRIERS, 2)
    imag = pairs[:, 0]
    real = pairs[:, 1]
    amp = np.sqrt(imag * imag + real * real, dtype=np.float32)
    # Applied here rather than at parse time so that `data` always holds
    # exactly what the radio reported. For legacy decimal captures the
    # device already applied it and the factor is 1.0, so both formats
    # produce comparable amplitudes.
    if record.compensate_gain != 1.0:
        amp *= np.float32(record.compensate_gain)
    return amp


def extract_sta_mac(raw: str) -> Optional[str]:
    """Recover a receiver's own station MAC from its boot banner.

    Args:
        raw: One line of serial text.

    Returns:
        The lower-cased MAC string if the line is the ``wifi:mode : sta
        (xx:xx:xx:xx:xx:xx)`` banner, otherwise ``None``.

    Constraints:
        This is the only way to tell physical boards apart, because
        ``/dev/cu.usbserial-*`` names are not stable across boards and the
        ``mac`` field of a CSI row is the transmitter's. It is printed once
        per boot, so a node attached after boot has no MAC and that is not
        an error.
    """
    m = STA_MAC_RE.search(raw)
    return m.group(1).lower() if m else None


def parse_lines(
    lines: Iterable[str],
    node_id: str = "",
    counters: Optional[ParseCounters] = None,
) -> list[CsiRecord]:
    """Parse many raw serial lines from one node.

    Args:
        lines: Raw serial lines in capture order.
        node_id: Receiver identifier applied to every resulting record.
        counters: Optional counters updated in place across the batch.

    Returns:
        The records that passed validation, in input order.

    Constraints:
        Drops are silent apart from the counters; no exception escapes for
        malformed content.
    """
    out: list[CsiRecord] = []
    for line in lines:
        rec = parse_line(line, node_id=node_id, counters=counters)
        if rec is not None:
            out.append(rec)
    return out
