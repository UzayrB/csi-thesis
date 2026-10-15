# Addendum B to `reports/PREREG_ID_2026-09-23.md`: C1 and C3

**Written 2026-09-23 01:52 SAST during the tracking gate. NO CSI HAS BEEN READ.** Everything below
comes from reading source and listing files. It changes a pre-registered conditioning stage, so it
is written before any number exists and the change is disclosed in those words.

---

## 1. Three open questions from section 10, now answered from the code

### 10.1, the largest technical risk: RESOLVED, and favourably

`pipeline/io/capture_logger.py:119` defines the on-disk frame layout of every `.bin` capture:

    t_host, t_mono, pkt_id, local_timestamp, rssi, noise_floor, ampdu_cnt, sig_len,
    rate, sig_mode, mcs, bandwidth, ..., channel, secondary_channel, ant, rx_format,
    first_word, gain_x10000

**Per-packet host time, monotonic time, receiver microsecond timestamp AND a packet sequence
number are all on disk**, and `read_capture_file` returns them as a structured array.

- **C1 is fully feasible**, and `pkt_id` gives packet loss directly as gaps in the sequence rather
  than as an inference from timing.
- **It is NOT feasible from the windowed artefact.** `common.pass_stream` reconstructs a stream
  from `data/windows/...npz`, which carries only per-WINDOW start times. **Every stage from `id12`
  onward that needs C1 reads the `.bin` files through `capture_logger.read_capture_file`, not
  through `pass_stream`.** `data/` stays read only.

### 10.4, the channel and therefore lambda: RESOLVED

`channel` is a per-packet field. `id11` reads it, asserts it is constant within a recording, and
the band-(b) physics uses the measured value. The 2.437 GHz default in `id15_factor_map.py` gives
lambda 0.1230 m and 16.26 Hz per m/s at F = 1, which agrees with the archived branch's independent
constant `DOPPLER_HZ_PER_MPS_PER_UNIT_FACTOR = 8.13` Hz per m/s per unit factor. Two independent
derivations agreeing is worth more than either alone, but the logged channel still decides.

### 10.5, AGC gain: RESOLVED, and THE BRIEF'S EXPECTATION IS WRONG

The brief says of AGC gain that "on this chip it generally is not [available], which is why C3 uses
a gain-invariant normalisation". **On this rig it IS available.** `gain_x10000` is a per-packet
field, described at `capture_logger.py:144` as "AGC gain compensation for this packet. **Stored
rather than applied**", and `pipeline/io/parse.py:36` confirms it is in this project's own firmware
format.

**That changes what C3 should do**, because the brief's mean-amplitude normalisation is lossy by
its own admission: it "also removes genuine broadband amplitude change, such as body shadowing",
and shadow depth is already a measured feature in this project.

**The caveat, from `pipeline/io/check_gain_lock.py`:** `gain_x10000` reads a constant 1.0 both when
the gain is genuinely locked and when it merely never moved, so the field alone cannot distinguish
those. The near/far experiment that would settle it needs two captures at different received power,
and **no such capture exists in this repository**, so it was either never run or not kept.

---

## 2. The change to C3, pre-registered now as a branch on what `id11` finds

`id11` reports, per recording and per link: whether `gain_x10000` is constant, its distinct values,
and the rate of step discontinuities shared across all subcarriers at one instant. **C3 then takes
exactly one of three forms, chosen by that report and by nothing else:**

| what `id11` finds | C3 becomes | why |
|---|---|---|
| **`gain_x10000` varies** | **C3-exact: divide each packet's amplitude by its own logged gain.** The gain-invariant normalisation becomes an ablation arm, not the method | the correction is exact and **keeps body shadowing**, which the lossy version destroys |
| **constant 1.0 AND no shared step discontinuities** | **C3-null: no gain correction at all**, recorded as not needed, with the discontinuity rate as the evidence | correcting a gain that never moved can only remove signal |
| **constant 1.0 BUT shared step discontinuities present** | **C3-normalise: the brief's per-packet mean-amplitude normalisation**, evaluated separately on band (a) and band (b) by M1 and M4, kept only where it helps | the gain moved without being logged, so the lossy fix is the only one available |

**In every branch, C3 remains a switchable stage and is ablated under R1 and R2 exactly as
registered.** What changes is only which operation the stage performs, and that is now decided by a
measurement rather than by an assumption about the chip.

**If C3-exact applies, the report must state that the gain was recoverable and the brief's premise
did not hold on this rig.** That is a finding about the capture, not a correction to be buried.

## 3. What does not change

C0, C1, C2, C4, C5, C6 and C7 are unchanged. M1 to M5 are unchanged. The falsifiable C4 prediction
for session 02 is unchanged. Nothing outside C3 moves.
