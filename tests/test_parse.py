"""Tests for the CSI line parser, built on real ``csi_recv`` console output.

The parser's contract is that it is total: every line the ESP32 can emit,
including bootloader garbage and lines torn by a read boundary, must return
``None`` rather than raise. These tests hold that contract in place.
"""

from __future__ import annotations

import numpy as np
import pytest

from pipeline.io.parse import (
    CSI_LEN,
    N_FIELDS,
    CsiRecord,
    ParseCounters,
    extract_amplitude,
    extract_sta_mac,
    parse_data_list,
    parse_line,
    parse_lines,
)

# A real CSI payload's leading values, extended to the full 256 so the line
# is genuinely valid rather than merely plausible.
_HEAD = [47, -16, 2, 0, -1, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]


def sample_data(n: int = CSI_LEN) -> list[int]:
    """Build an int8-valid data list of length ``n``."""
    vals = list(_HEAD)
    i = 0
    while len(vals) < n:
        vals.append(((i * 37) % 255) - 127)
        i += 1
    return vals[:n]


def make_line(
    pkt_id: int = 9213,
    declared_len: int = CSI_LEN,
    data: list[int] | None = None,
    rssi: int = -73,
) -> str:
    """Compose a complete ``CSI_DATA`` row in the firmware's field order."""
    if data is None:
        data = sample_data()
    payload = "[" + ",".join(str(v) for v in data) + "]"
    fields = [
        "CSI_DATA", str(pkt_id), "1a:00:00:00:00:00", str(rssi), "11", "1", "0", "0",
        "1", "1", "0", "0", "0", "0", "-96", "0", "11", "0", "15771", "0", "47", "1",
        str(declared_len), "1", f'"{payload}"',
    ]
    return ",".join(fields)


# Lines the receiver really does emit that are not CSI rows.
ESP_IDF_LOG = "I (2534) wifi:mode : sta (68:09:47:4c:ef:b4)"
ESP_IDF_LOG_2 = "I (1123) esp_netif_handlers: sta ip: 192.168.1.4, mask: 255.255.255.0"
BOOT_GARBAGE = "��\x00�l��d�\x00�"
HEADER_LINE = (
    "type,id,mac,rssi,rate,sig_mode,mcs,bandwidth,smoothing,not_sounding,"
    "aggregation,stbc,fec_coding,sgi,noise_floor,ampdu_cnt,channel,"
    "secondary_channel,local_timestamp,ant,sig_len,rx_format,len,first_word,data"
)


# --------------------------------------------------------------------------
# The happy path
# --------------------------------------------------------------------------


def test_valid_line_parses() -> None:
    """A complete row becomes a record carrying every metadata field."""
    c = ParseCounters()
    rec = parse_line(make_line(), node_id="RX1", counters=c)
    assert isinstance(rec, CsiRecord)
    assert rec.node_id == "RX1"
    assert rec.pkt_id == 9213
    assert rec.mac == "1a:00:00:00:00:00"
    assert rec.rssi == -73
    assert rec.rate == 11
    assert rec.noise_floor == -96
    assert rec.channel == 11
    assert rec.local_timestamp == 15771
    assert rec.sig_len == 47
    assert rec.csi_len == CSI_LEN
    assert c.ok == 1 and c.malformed == 0


def test_record_is_tagged_with_host_time() -> None:
    """Both host clocks are recorded, since one is for rates and one for anchors."""
    rec = parse_line(make_line(), node_id="RX2", t_mono=12.5, t_host=1700000000.25)
    assert rec is not None
    assert rec.t_mono == 12.5
    assert rec.t_host == 1700000000.25
    assert rec.node_id == "RX2"


def test_data_array_is_int8_of_256() -> None:
    """The payload lands as int8 of exactly 256 values, in order."""
    rec = parse_line(make_line(), node_id="RX1")
    assert rec is not None
    assert rec.data.dtype == np.int8
    assert rec.data.shape == (CSI_LEN,)
    assert rec.data[0] == 47 and rec.data[1] == -16


def test_extract_amplitude_shape_and_values() -> None:
    """Amplitude is 128 float32 magnitudes over (imag, real) pairs."""
    rec = parse_line(make_line(), node_id="RX1")
    assert rec is not None
    amp = extract_amplitude(rec)
    assert amp.shape == (CSI_LEN // 2,)
    assert amp.dtype == np.float32
    assert amp[0] == pytest.approx(np.sqrt(47.0**2 + 16.0**2), rel=1e-6)
    assert np.all(amp >= 0)


def test_header_field_count_matches_parser() -> None:
    """The firmware's own header line has the field count the parser expects."""
    assert len(HEADER_LINE.split(",")) == N_FIELDS


# --------------------------------------------------------------------------
# Rejections: none of these may raise
# --------------------------------------------------------------------------


def test_esp_idf_log_line_returns_none() -> None:
    """An ESP-IDF log line is not CSI and is counted as such."""
    c = ParseCounters()
    assert parse_line(ESP_IDF_LOG, "RX1", c) is None
    assert parse_line(ESP_IDF_LOG_2, "RX1", c) is None
    assert c.non_csi == 2 and c.malformed == 0


def test_header_line_returns_none() -> None:
    """The column header printed once at boot is not a data row."""
    c = ParseCounters()
    assert parse_line(HEADER_LINE, "RX1", c) is None
    assert c.non_csi == 1


def test_boot_garbage_returns_none() -> None:
    """Bootloader noise decoded with errors='replace' is survivable."""
    c = ParseCounters()
    assert parse_line(BOOT_GARBAGE, "RX1", c) is None
    assert c.non_csi == 1


def test_empty_and_whitespace_lines_return_none() -> None:
    """Blank lines are ordinary and must not raise."""
    c = ParseCounters()
    for line in ("", "\n", "   ", "\r\n"):
        assert parse_line(line, "RX1", c) is None
    assert c.non_csi == 4


def test_torn_line_returns_none() -> None:
    """A row glued onto the tail of a log line is torn, and counted as torn."""
    c = ParseCounters()
    torn = "I (2534) wifi:<ba-add>idx:0" + make_line()
    assert parse_line(torn, "RX1", c) is None
    assert c.torn == 1


def test_truncated_row_returns_none() -> None:
    """A row cut off before its payload fails the field count check."""
    c = ParseCounters()
    truncated = make_line()[:60]
    assert truncated.count(",") < N_FIELDS - 1
    assert parse_line(truncated, "RX1", c) is None
    assert c.bad_field_count == 1


def test_row_cut_inside_payload_returns_none() -> None:
    """A row cut mid-payload still has 25 fields, so the payload check catches it."""
    c = ParseCounters()
    truncated = make_line()[:120]
    assert parse_line(truncated, "RX1", c) is None
    assert c.bad_data == 1


def test_truncated_data_list_returns_none() -> None:
    """The exact tear from the brief: a data list with no closing bracket."""
    c = ParseCounters()
    line = (
        'CSI_DATA,9213,1a:00:00:00:00:00,-73,11,1,0,0,1,1,0,0,0,0,-96,0,11,0,'
        '15771,0,47,1,256,1,"[47,-16,2,0,'
    )
    assert parse_line(line, "RX1", c) is None
    assert c.bad_data == 1


def test_len_128_returns_none() -> None:
    """A receiver reporting len=128 is rejected: this project needs LLTF+HT-LTF."""
    c = ParseCounters()
    line = make_line(declared_len=128, data=sample_data(128))
    assert parse_line(line, "RX1", c) is None
    assert c.bad_len == 1


def test_declared_len_256_but_short_data_returns_none() -> None:
    """A row claiming 256 while carrying fewer values is rejected."""
    c = ParseCounters()
    line = make_line(declared_len=CSI_LEN, data=sample_data(200))
    assert parse_line(line, "RX1", c) is None
    assert c.bad_data == 1


def test_non_numeric_metadata_returns_none() -> None:
    """Corrupted metadata is caught before the payload is touched."""
    c = ParseCounters()
    line = make_line().replace(",9213,", ",92x3,", 1)
    assert parse_line(line, "RX1", c) is None
    assert c.bad_metadata == 1


def test_out_of_range_int8_value_returns_none() -> None:
    """A value outside int8 means the line is not what it claims to be."""
    data = sample_data()
    data[5] = 999
    c = ParseCounters()
    assert parse_line(make_line(data=data), "RX1", c) is None
    assert c.bad_data == 1


def test_empty_data_list_returns_none() -> None:
    """An empty payload list is malformed, not an empty capture."""
    assert parse_data_list('"[]"') is None
    assert parse_data_list('"["') is None
    assert parse_data_list("") is None


@pytest.mark.parametrize(
    "line",
    [
        "",
        "   ",
        "\x00\x01\x02",
        "CSI_DATA",
        "CSI_DATA,",
        "CSI_DATA," + "," * 40,
        'CSI_DATA,1,mac,-1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,256,1,"[1,2,3]"',
        ESP_IDF_LOG,
        BOOT_GARBAGE,
        HEADER_LINE,
        make_line()[:5],
        make_line()[10:],
        make_line() + make_line(),
    ],
)
def test_never_raises(line: str) -> None:
    """No input string, however mangled, may raise out of the parser."""
    c = ParseCounters()
    assert parse_line(line, "RX1", c) is None or isinstance(parse_line(line, "RX1", c), CsiRecord)


# --------------------------------------------------------------------------
# Counters and batch parsing
# --------------------------------------------------------------------------


def test_counters_account_for_every_line() -> None:
    """Accepted plus rejected equals lines seen: no line goes unaccounted for."""
    c = ParseCounters()
    lines = [
        make_line(pkt_id=1),
        ESP_IDF_LOG,
        make_line(pkt_id=2),
        BOOT_GARBAGE,
        make_line(declared_len=128, data=sample_data(128)),
        make_line()[:100],
        HEADER_LINE,
    ]
    recs = parse_lines(lines, node_id="RX1", counters=c)
    assert len(recs) == 2
    d = c.as_dict()
    accounted = d["ok"] + d["non_csi"] + d["torn"] + d["bad_field_count"] + d["bad_metadata"] + d["bad_len"] + d["bad_data"]
    assert accounted == d["lines_seen"] == len(lines)
    assert c.ok == 2 and c.bad_len == 1


def test_parse_lines_tags_every_record_with_node_id() -> None:
    """Node identity comes from the caller, never from the transmitter MAC."""
    recs = parse_lines([make_line(pkt_id=i) for i in range(5)], node_id="RX3")
    assert len(recs) == 5
    assert {r.node_id for r in recs} == {"RX3"}
    assert {r.mac for r in recs} == {"1a:00:00:00:00:00"}


# --------------------------------------------------------------------------
# Station MAC recovery
# --------------------------------------------------------------------------


def test_extract_sta_mac_from_boot_banner() -> None:
    """The board's own MAC is recovered from its boot banner."""
    assert extract_sta_mac(ESP_IDF_LOG) == "68:09:47:4c:ef:b4"


def test_extract_sta_mac_ignores_other_lines() -> None:
    """No other line may be mistaken for the banner."""
    assert extract_sta_mac(make_line()) is None
    assert extract_sta_mac(ESP_IDF_LOG_2) is None
    assert extract_sta_mac(BOOT_GARBAGE) is None


# --------------------------------------------------------------------------
# Base64 payload format (project firmware)
# --------------------------------------------------------------------------


def firmware_b64(data: list[int]) -> str:
    """Encode exactly as ``csi_b64_encode`` in csi_recv does.

    Written independently of :func:`pipeline.io.parse.parse_data_b64` so the
    tests check agreement between two implementations rather than a function
    agreeing with itself.
    """
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    raw = [v & 0xFF for v in data]
    out = []
    for i in range(0, len(raw), 3):
        v = raw[i] << 16
        if i + 1 < len(raw):
            v |= raw[i + 1] << 8
        if i + 2 < len(raw):
            v |= raw[i + 2]
        out.append(alphabet[(v >> 18) & 0x3F])
        out.append(alphabet[(v >> 12) & 0x3F])
        out.append(alphabet[(v >> 6) & 0x3F] if i + 1 < len(raw) else "=")
        out.append(alphabet[v & 0x3F] if i + 2 < len(raw) else "=")
    return "".join(out)


def make_b64_line(
    pkt_id: int = 9213,
    declared_len: int = CSI_LEN,
    data: list[int] | None = None,
    gain_x10000: int = 10000,
    rssi: int = -73,
) -> str:
    """Compose a base64 ``CSI_DATA`` row in the project firmware's format."""
    if data is None:
        data = sample_data()
    fields = [
        "CSI_DATA", str(pkt_id), "1a:00:00:00:00:00", str(rssi), "11", "1", "0", "0",
        "1", "1", "0", "0", "0", "0", "-96", "0", "11", "0", "15771", "0", "47", "1",
        str(declared_len), "1", str(gain_x10000), firmware_b64(data),
    ]
    return ",".join(fields)


def test_b64_line_parses() -> None:
    """A base64 row parses, and its payload matches the decimal form exactly."""
    c = ParseCounters()
    data = sample_data()
    rec = parse_line(make_b64_line(data=data), node_id="RX1", counters=c)
    assert isinstance(rec, CsiRecord)
    assert rec.pkt_id == 9213
    assert rec.csi_len == CSI_LEN
    assert rec.data.dtype == np.int8
    assert rec.data.shape == (CSI_LEN,)
    assert rec.data.tolist() == data
    assert c.ok == 1 and c.malformed == 0


def test_b64_and_decimal_agree() -> None:
    """The two wire formats produce byte-identical records."""
    data = sample_data()
    a = parse_line(make_line(data=data), node_id="RX1")
    b = parse_line(make_b64_line(data=data), node_id="RX1")
    assert a is not None and b is not None
    assert np.array_equal(a.data, b.data)
    assert a.pkt_id == b.pkt_id and a.rssi == b.rssi and a.noise_floor == b.noise_floor


def test_b64_gain_is_decoded_and_applied() -> None:
    """The scaled integer gain is divided back out and scales the amplitude."""
    data = sample_data()
    unity = parse_line(make_b64_line(data=data, gain_x10000=10000), node_id="RX1")
    doubled = parse_line(make_b64_line(data=data, gain_x10000=20000), node_id="RX1")
    assert unity is not None and doubled is not None
    assert unity.compensate_gain == pytest.approx(1.0)
    assert doubled.compensate_gain == pytest.approx(2.0)
    # Raw payload is identical; only the amplitude is scaled.
    assert np.array_equal(unity.data, doubled.data)
    assert extract_amplitude(doubled) == pytest.approx(2.0 * extract_amplitude(unity), rel=1e-5)


def test_decimal_records_report_unity_gain() -> None:
    """Legacy rows already had gain applied on the device, so the host adds none."""
    rec = parse_line(make_line(), node_id="RX1")
    assert rec is not None
    assert rec.compensate_gain == 1.0


def test_b64_negative_values_survive_round_trip() -> None:
    """Two's-complement negatives survive encode and decode unchanged."""
    data = [-128, -127, -1, 0, 1, 126, 127] + sample_data()[7:]
    rec = parse_line(make_b64_line(data=data), node_id="RX1")
    assert rec is not None
    assert rec.data.tolist()[:7] == [-128, -127, -1, 0, 1, 126, 127]


def test_b64_truncated_payload_returns_none() -> None:
    """A row torn mid-payload decodes to the wrong length and is rejected."""
    c = ParseCounters()
    line = make_b64_line()[:-40]
    assert parse_line(line, "RX1", c) is None
    assert c.bad_data == 1


def test_b64_non_base64_payload_returns_none() -> None:
    """A payload outside the base64 alphabet is rejected, not guessed at."""
    c = ParseCounters()
    line = make_b64_line().rsplit(",", 1)[0] + "," + "!" * 344
    assert parse_line(line, "RX1", c) is None
    assert c.bad_data == 1


def test_b64_bad_gain_field_returns_none() -> None:
    """An unparseable gain field is caught as bad metadata."""
    c = ParseCounters()
    parts = make_b64_line().split(",")
    parts[24] = "x"
    assert parse_line(",".join(parts), "RX1", c) is None
    assert c.bad_metadata == 1


def test_b64_len_128_returns_none() -> None:
    """The len check applies to the base64 format too."""
    c = ParseCounters()
    assert parse_line(make_b64_line(declared_len=128, data=sample_data(128)), "RX1", c) is None
    assert c.bad_len == 1


def test_b64_row_is_shorter_than_decimal() -> None:
    """The whole point: a base64 row costs far fewer bytes on the console."""
    d = len(make_line())
    b = len(make_b64_line())
    assert b < d
    assert b < 500 and d > 800


def test_b64_payload_is_fixed_width() -> None:
    """Base64 rows are constant width, so console bandwidth cannot vary."""
    small = make_b64_line(data=[0] * CSI_LEN)
    large = make_b64_line(data=[127] * CSI_LEN)
    assert len(small.rsplit(",", 1)[1]) == len(large.rsplit(",", 1)[1]) == 344
