"""idz_audit. Identification audit (`reports/identification/briefs/2026-09-29_audit.md`), stage 1: capture and packet
audit of every recording and receiver in the bank (`runs/identify/audit/PLAN.md` section 1). Reads
`data/` only through `read_capture_file`; writes only under `runs/identify/audit/stage1/`.

The corrected clock is the id29 clock map (`id29_dc2_score._link`'s statements), computed here per frame
so every frame field can be attributed to a pass.

    PYTHONPATH=. python3 -m pipeline.identify.idz_audit
"""

from __future__ import annotations

import collections
import json
import os
import sys
import time

import numpy as np

from pipeline.identify import idmax_common as IC
from pipeline.identify import idx_bank as B
from pipeline.identify.common import anon
from pipeline.identify.id19_bank import KEEP
from pipeline.identify.id19_featbank import SC

OUT = os.path.join("runs", "identify", "audit", "stage1")
LINKS = ("RX1", "RX2", "RX3")
TYPE_FIELDS = ("sig_mode", "bandwidth", "secondary_channel", "stbc", "channel", "rx_format")
TAB_FIELDS = ("sig_mode", "rate", "mcs", "bandwidth", "channel", "secondary_channel", "stbc", "sig_len",
              "rx_format", "ant", "first_word")
STEP_DB, RSSI_DB, FOREIGN_DB = 3.0, 3.0, 20.0


def corrected_time(fr) -> tuple:
    """(t_hat per frame in file order, unwrapped receiver seconds): `id29_dc2_score._link`'s clock map."""
    tm = np.asarray(fr["t_mono"], np.float64)
    lt = np.asarray(fr["local_timestamp"], np.float64) * 1e-6
    for i in np.flatnonzero(np.diff(lt) < -1.0):
        lt[i + 1:] += 2.0 ** 32 * 1e-6
    off = tm - lt
    edges = np.arange(lt.min(), lt.max() + 10.0, 10.0)
    idx = np.clip(np.searchsorted(edges, lt) - 1, 0, len(edges) - 2)
    cen, val = [], []
    for b in range(len(edges) - 1):
        m = idx == b
        if m.sum() >= 20:
            cen.append(float(np.median(lt[m])))
            val.append(float(np.percentile(off[m], 5)))
    t_hat = lt + np.interp(lt, cen, val) if len(cen) >= 2 else tm
    return t_hat, lt


def esp_layout() -> dict:
    """ESP-IDF CSI entry -> (field, subcarrier, valid) for HT20 LLTF + HT-LTF."""
    out = {}
    for e in range(128):
        field = "LLTF" if e < 64 else "HT-LTF"
        j = e % 64
        sc = j if j < 32 else j - 64
        lim = 26 if field == "LLTF" else 28
        out[e] = (field, sc, sc != 0 and abs(sc) <= lim)
    return out


def run() -> dict:
    from pipeline.identify.raw_access import amplitude_from_frames
    from pipeline.io.capture_logger import read_capture_file
    kept = KEEP[SC]
    null_count = np.zeros(128)
    n_frames_total = 0
    per_rec, per_pass = [], []
    for rec in B.recordings():
        gt = json.load(open(rec["stem"] + ".gt.json", encoding="utf-8"))
        passes = sorted(gt["passes"], key=lambda q: q["t_start"])
        rid = f"{rec['session']}|{anon(rec['name'])}|{rec['block']}"
        pass_acc = [collections.defaultdict(float) for _ in passes]
        for L in LINKS:
            hdr, fr = read_capture_file(f"{rec['stem']}_{L}.bin")
            d = np.asarray(fr["data"], np.int8)
            n = len(fr)
            n_frames_total += n
            zero_pair = (d[:, 0::2] == 0) & (d[:, 1::2] == 0)
            null_count += zero_pair.sum(0)
            ht_bad = ~np.any(d[:, 128:] != 0, axis=1)
            ll_bad = ~np.any(d[:, :128] != 0, axis=1)
            tup = np.array(["|".join(str(fr[f][i]) for f in TYPE_FIELDS) for i in range(n)])
            vals, cnts = np.unique(tup, return_counts=True)
            major = vals[np.argmax(cnts)]
            suspect = (tup != major) | ht_bad | ll_bad
            rssi = np.asarray(fr["rssi"], float)
            med = float(np.median(rssi))
            foreign = np.abs(rssi - med) > FOREIGN_DB
            gain = np.asarray(fr["gain"], float)
            t_hat, lt = corrected_time(fr)
            span = lt.max() - lt.min()
            amp = amplitude_from_frames(fr)[:, kept]
            m = amp.mean(axis=1)
            o = np.argsort(t_hat, kind="stable")
            tab = {f: {str(k): int(v) for k, v in zip(*np.unique(np.asarray(fr[f]), return_counts=True))} for f in TAB_FIELDS}
            per_rec.append({"rec": rid, "link": L, "n_frames": n, "rate_hz": round((n - 1) / span, 2) if span > 0 else None,
                            "payload_bytes": int(d.shape[1]), "types": tab, "majority_type": major,
                            "suspect_frames": int(suspect.sum()), "ht_ltf_zero": int(ht_bad.sum()), "lltf_zero": int(ll_bad.sum()),
                            "rssi": {"median": med, "p1": float(np.percentile(rssi, 1)), "p99": float(np.percentile(rssi, 99))},
                            "foreign_flagged": int(foreign.sum()),
                            "gain": {"distinct": int(len(np.unique(gain))), "min": float(gain.min()), "max": float(gain.max()),
                                     "frac_not_1": round(float(np.mean(gain != 1.0)), 4)}})
            ts, ms, rs, gs = t_hat[o], m[o], rssi[o], gain[o]
            sus, frg = suspect[o], foreign[o]
            for k, q in enumerate(passes):
                w = (ts >= float(q["t_start"])) & (ts <= float(q["t_end"]))
                if w.sum() < 2:
                    pass_acc[k][f"{L}|n_frames"] = int(w.sum())
                    continue
                gap = np.diff(ts[w])
                with np.errstate(divide="ignore", invalid="ignore"):
                    step = np.abs(20 * np.log10(ms[w][1:] / ms[w][:-1])) >= STEP_DB
                rchg = np.abs(np.diff(rs[w])) >= RSSI_DB
                gchg = np.diff(gs[w]) != 0
                acc = pass_acc[k]
                acc[f"{L}|n_frames"] = int(w.sum())
                acc[f"{L}|suspect"] = int(sus[w].sum())
                acc[f"{L}|foreign"] = int(frg[w].sum())
                acc[f"{L}|max_gap_ms"] = round(float(gap.max() * 1000), 1)
                acc[f"{L}|gaps_over_20ms"] = int(np.sum(gap > 0.020))
                acc[f"{L}|gaps_over_50ms"] = int(np.sum(gap > 0.050))
                acc[f"{L}|gain_steps"] = int(step.sum())
                acc[f"{L}|gain_steps_with_rssi_change"] = int(np.sum(step & rchg))
                acc[f"{L}|gain_field_changes"] = int(gchg.sum())
                acc[f"{L}|gain_steps_with_gain_field_change"] = int(np.sum(step & gchg))
                acc[f"{L}|gain_field_distinct"] = int(len(np.unique(gs[w])))
        for k, q in enumerate(passes):
            per_pass.append({"rec": rid, "k": k, "path": q["path_name"], **pass_acc[k]})
        print(f"{time.strftime('%H:%M:%S')} {rid}: {len(passes)} passes", flush=True)
    lay = esp_layout()
    null_frac = null_count / max(n_frames_total, 1)
    kept_set = set(int(e) for e in kept)
    sc_map = {"kept_null_entries": [], "dropped_valid_entries": [], "kept_entries": len(kept_set)}
    for e in range(128):
        field, sc, valid = lay[e]
        if e in kept_set and (not valid or null_frac[e] > 0.5):
            sc_map["kept_null_entries"].append({"entry": e, "field": field, "subcarrier": sc, "valid": valid,
                                                "null_frac": round(float(null_frac[e]), 4)})
        if e not in kept_set and valid:
            sc_map["dropped_valid_entries"].append({"entry": e, "field": field, "subcarrier": sc,
                                                    "null_frac": round(float(null_frac[e]), 4)})
    uniq = sorted({lay[e][1] for e in kept_set})
    both = sorted({lay[e][1] for e in kept_set if lay[e][0] == "LLTF"} & {lay[e][1] for e in kept_set if lay[e][0] == "HT-LTF"})
    sc_map["unique_subcarriers"] = len(uniq)
    sc_map["in_both_fields"] = len(both)
    sc_map["only_one_field"] = len(uniq) - len(both)
    sc_map["null_frac_by_entry"] = [round(float(x), 4) for x in null_frac]
    summary = summarise(per_rec, per_pass)
    doc = {"built": time.strftime("%Y-%m-%dT%H:%M:%S"), "label": "development evaluation, all data seen",
           "thresholds": {"gain_step_db": STEP_DB, "rssi_change_db": RSSI_DB, "foreign_rssi_db": FOREIGN_DB},
           "summary": summary, "subcarrier_map": sc_map, "per_recording": per_rec}
    os.makedirs(OUT, exist_ok=True)
    txt = json.dumps(doc, indent=1, default=str)
    assert IC.no_names(txt)
    open(os.path.join(OUT, "audit.json"), "w").write(txt)
    ptxt = json.dumps(per_pass, default=str)
    assert IC.no_names(ptxt)
    open(os.path.join(OUT, "per_pass.json"), "w").write(ptxt)
    rssi_figure(per_rec)
    print(json.dumps(summary, indent=1, default=str))
    print(json.dumps({k: v for k, v in sc_map.items() if k != "null_frac_by_entry"}, indent=1))
    return doc


def summarise(per_rec, per_pass) -> dict:
    s = {"n_recording_links": len(per_rec), "n_passes": len(per_pass)}
    s["rate_hz"] = {L: {"median": float(np.median([r["rate_hz"] for r in per_rec if r["link"] == L])),
                        "min": float(np.min([r["rate_hz"] for r in per_rec if r["link"] == L])),
                        "max": float(np.max([r["rate_hz"] for r in per_rec if r["link"] == L]))} for L in LINKS}
    s["types_seen"] = sorted({r["majority_type"] for r in per_rec})
    s["suspect_frames_total"] = int(sum(r["suspect_frames"] for r in per_rec))
    s["ht_ltf_zero_total"] = int(sum(r["ht_ltf_zero"] for r in per_rec))
    s["foreign_flagged_total"] = int(sum(r["foreign_flagged"] for r in per_rec))
    s["gain_field"] = {"recording_links_with_gain_not_1": int(sum(r["gain"]["frac_not_1"] > 0 for r in per_rec)),
                       "max_distinct_in_a_recording": int(max(r["gain"]["distinct"] for r in per_rec)),
                       "min": float(min(r["gain"]["min"] for r in per_rec)), "max": float(max(r["gain"]["max"] for r in per_rec))}

    def frac(key, thr=0):
        v = [any(p.get(f"{L}|{key}", 0) > thr for L in LINKS) for p in per_pass]
        return round(float(np.mean(v)), 4)
    s["passes_with_suspect_frames"] = frac("suspect")
    s["passes_with_foreign_frames"] = frac("foreign")
    s["passes_with_gap_over_20ms_any_link"] = frac("gaps_over_20ms")
    s["passes_with_gap_over_50ms_any_link"] = frac("gaps_over_50ms")
    s["longest_gap_ms"] = float(max(p.get(f"{L}|max_gap_ms", 0) for p in per_pass for L in LINKS))
    s["passes_with_gain_step_any_link"] = frac("gain_steps")
    s["passes_with_gain_field_change_any_link"] = frac("gain_field_changes")
    for L in LINKS:
        s[f"{L}|passes_gap_over_50ms"] = round(float(np.mean([p.get(f"{L}|gaps_over_50ms", 0) > 0 for p in per_pass])), 4)
        s[f"{L}|passes_with_gain_step"] = round(float(np.mean([p.get(f"{L}|gain_steps", 0) > 0 for p in per_pass])), 4)
        s[f"{L}|gain_steps_total"] = int(sum(p.get(f"{L}|gain_steps", 0) for p in per_pass))
        s[f"{L}|gain_steps_with_rssi_change"] = int(sum(p.get(f"{L}|gain_steps_with_rssi_change", 0) for p in per_pass))
        s[f"{L}|gain_steps_with_gain_field_change"] = int(sum(p.get(f"{L}|gain_steps_with_gain_field_change", 0) for p in per_pass))
        s[f"{L}|passes_gain_field_varies"] = round(float(np.mean([p.get(f"{L}|gain_field_distinct", 1) > 1 for p in per_pass])), 4)
    return s


def rssi_figure(per_rec):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(3, 1, figsize=(14, 8), sharex=True)
    for ax, L in zip(axes, LINKS):
        rr = [r for r in per_rec if r["link"] == L]
        x = np.arange(len(rr))
        ax.vlines(x, [r["rssi"]["p1"] for r in rr], [r["rssi"]["p99"] for r in rr], color="0.6")
        ax.plot(x, [r["rssi"]["median"] for r in rr], "o", ms=3)
        ax.set_ylabel(f"{L} RSSI (dBm)")
    axes[-1].set_xticks(np.arange(len(rr)))
    axes[-1].set_xticklabels([r["rec"] for r in rr], rotation=90, fontsize=5)
    fig.suptitle("RSSI per recording: median and 1st to 99th percentile (development evaluation, all data seen)", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "rssi.png"), dpi=120)


def main() -> int:
    run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
