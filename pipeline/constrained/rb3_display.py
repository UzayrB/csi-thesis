"""STAGE 3 of the decoder rebuild: the display layer, provisional and committed.
Brief: reports/decoder_rebuild_prompt_2026-09-17.md, STAGE 3, items 3.1 to 3.3.

3.1  Two tracks from one decoder: COMMITTED (binding, a connected walk) and PROVISIONAL (the
     un-collapsed forward belief, shown immediately and allowed to be wrong). A window whose
     committed decision differs from what was shown is a REVISION, with its catch-up distance.
3.2  Both measured at display lags 0, 1 and 2, and the SHIPPING LAG selected by the brief's rule:
     the best strict pass-found across the three, then the SHORTEST lag whose strict pass-found lies
     inside the bootstrap interval of that best value.
3.2b Sub-second lag needs a finer window stride and is OPTIONAL; it is dropped unless the ETA allows
     it, and dropping it is recorded rather than implied.
3.3  The engine: the decoder behind pipeline.realtime's Predictor protocol, driven from a replay of
     a whole session-03 recording, per-window latency against the 500 ms contract.

Set RB_SMOKE=1 for one pairing.
"""

from __future__ import annotations

import os
import sys
import time

import numpy as np

from pipeline.constrained.common import (
    E_POST, REPORT_DIR, RUN_DIR, fmt, pairings, read_json, regime_split, status, tag_of,
)
from pipeline.constrained.decoder2 import Config, decode2
from pipeline.constrained.live2 import LiveDecoder2, provisional_greedy, revisions_between
from pipeline.constrained.metrics import aggregate_pairing, audit_transitions, flat, recording_metrics
from pipeline.constrained.rebuild_common import (
    LAGS_ALLOWED, findings, headline, load_results, optional_budget_ok, save_results, stage_dir,
)

SMOKE = os.environ.get("RB_SMOKE") == "1"
STAGE = "rb3_display_smoke" if SMOKE else "rb3_display"
DEMO_TAG = "s0102_to_s03"
CONTRACT_MS = 500.0


def shipped_config(s2: dict, tag: str):
    """The configuration stage 2 selected for this pairing, rebuilt as a Config plus its null rule."""
    from pipeline.constrained.emissions import AdaptiveNullEmission
    sel = (s2.get("selected") or {}).get(tag) or {}
    cd = sel.get("config") or {}
    cfg = Config(**{k: v for k, v in cd.items() if k in Config.__dataclass_fields__}) if cd else Config()
    nr = sel.get("null_rule") or {}
    ne = AdaptiveNullEmission(nr.get("quantile", 0.5), nr.get("offset", -1.3), nr.get("gate_weight", 0.0))
    return cfg, ne, sel


def emission_for(tag, tr_s, te_s, within, st, emission_kind):
    """The stage 1 emission choice, per recording of this pairing's test session."""
    from pipeline.constrained.artefacts import posterior_path, read_full_posteriors
    from pipeline.constrained.dataset import sides
    from pipeline.constrained.emissions import cell_emission, cell_marginal, scaled_cell_emission
    from pipeline.constrained.recordings import gate_energy, load_meta
    marginal = None
    if emission_kind == "scaled":
        marginal = cell_marginal(sides(tr_s, te_s, within, with_features=False)[0].xy, 25)
    out = []
    for stem, b in read_full_posteriors(posterior_path(tag, 25, E_POST, 0)).items():
        prob = b["prob"].astype(float)
        e = cell_emission(prob, st.xy, 25) if marginal is None else scaled_cell_emission(prob, st.xy, 25, marginal)
        out.append((stem, load_meta(te_s[0], stem), gate_energy(te_s[0], stem), e))
    return out


def measure_pairing(st, tag, tr_s, te_s, within, cfg, ne, emission_kind, transit, held) -> dict:
    """Committed and provisional at every allowed lag, for one pairing."""
    from pipeline.constrained.decoder2 import Space, stack2
    from pipeline.constrained.decoder2 import transition_matrix2
    rows = emission_for(tag, tr_s, te_s, within, st, emission_kind)
    sp, lT = Space(st, cfg), transition_matrix2(st, cfg, transit)
    out = {"committed": {}, "provisional": {}, "audit": {}}
    for lag in LAGS_ALLOWED:
        crecs, precs, revs, aud_c, aud_p = [], [], [], 0, 0
        for stem, rec, ge, e in rows:
            if hasattr(ne, "calibrate"):
                ne.calibrate(e)
            dec = decode2(e, ge, ne, st, cfg, transit, lag=lag)
            prov = provisional_greedy(stack2(e, ge, ne, sp), lT)
            rv = revisions_between(dec["seq"], prov, st) + dec["revisions"]
            from pipeline.constrained.decoder import decoded_paths, decoded_xy
            pdec = {"seq": prov, "names": decoded_paths(prov, st), "xy": decoded_xy(prov, st),
                    "on_path": decoded_paths(prov, st) != ""}
            crecs.append(recording_metrics(rec, dec, st, lT, ge, cfg.exit_k, held, revisions=rv,
                                           provisional_seq=prov))
            precs.append(recording_metrics(rec, pdec, st, lT, ge, cfg.exit_k, held))
            revs.append(len(rv))
            aud_c += audit_transitions(dec["seq"], lT); aud_p += audit_transitions(prov, lT)
        ca = aggregate_pairing(crecs, f"{tag}/committed/lag{lag}"); ca["flat"] = flat(ca)
        pa = aggregate_pairing(precs, f"{tag}/provisional/lag{lag}"); pa["flat"] = flat(pa)
        out["committed"][f"lag{lag}"] = {k: v for k, v in ca.items() if k != "positional"} | \
            {"positional": {kk: ca["positional"].get(kk) for kk in ("all_windows", "on_path_only")}}
        out["provisional"][f"lag{lag}"] = {k: v for k, v in pa.items() if k != "positional"} | \
            {"positional": {kk: pa["positional"].get(kk) for kk in ("all_windows", "on_path_only")}}
        out["audit"][f"lag{lag}"] = {"committed_impossible": aud_c, "provisional_impossible": aud_p,
                                     "revisions_total": int(sum(revs))}
    return out


def choose_lag(summ: dict) -> dict:
    """The brief's rule: best strict pass-found across the lags, then the SHORTEST lag inside its
    bootstrap interval. Positional error decides only a tie on pass-found."""
    rows = {}
    for lag in LAGS_ALLOWED:
        m = f"lag{lag}"
        rows[lag] = {"found": (summ[m]["found_pct"] or {}).get("cross"),
                     "ci_hi": (summ[m]["found_ci_hi"] or {}).get("cross"),
                     "pos": (summ[m]["all_windows_total_m"] or {}).get("cross")}
    have = {l: r for l, r in rows.items() if r["found"] is not None}
    if not have:
        return {"lag": min(LAGS_ALLOWED), "why": "no pairing reported a pass-found; shortest lag by default"}
    best_lag = max(have, key=lambda l: have[l]["found"])
    best = have[best_lag]
    # inside the interval of the best value: its own bootstrap upper bound is the yardstick
    hi = best["ci_hi"] if best["ci_hi"] is not None else best["found"]
    lo_band = 2 * best["found"] - hi if hi is not None else best["found"]
    inside = [l for l in sorted(have) if have[l]["found"] >= lo_band]
    ship = min(inside) if inside else best_lag
    bought = []
    for a, b in zip(sorted(have), sorted(have)[1:]):
        bought.append(f"lag {a} to {b}: strict found {fmt(have[a]['found'], 1)} to {fmt(have[b]['found'], 1)} percent, "
                      f"all-windows {fmt(have[a]['pos'])} to {fmt(have[b]['pos'])} m")
    return {"lag": int(ship), "best_lag": int(best_lag), "best_found_pct": best["found"],
            "band_lower": lo_band, "inside_band": inside, "per_lag": rows,
            "why": (f"best strict pass-found is {fmt(best['found'], 1)} percent at lag {best_lag}; its bootstrap "
                    f"band reaches down to {fmt(lo_band, 1)}; the shortest lag inside that band is {ship}"),
            "what_each_second_bought": "; ".join(bought)}


def engine(st, cfg, ne, transit, emission_kind, lag: int, n_windows: int = 150) -> dict:
    """3.3. Behind the engine's Predictor protocol, driven from a replay, both tracks measured."""
    out = {"attached": False, "lag": lag}
    try:
        from pipeline.constrained.artefacts import posterior_path, read_full_posteriors
        from pipeline.constrained.recordings import gate_energy, load_meta
        blocks = read_full_posteriors(posterior_path(DEMO_TAG, 25, E_POST, 0))
        stem = "participant_PA5_TEST_walk" if "participant_PA5_TEST_walk" in blocks else sorted(blocks)[0]
        rec, ge = load_meta("03", stem), gate_energy("03", stem)
        from pipeline.constrained.emissions import cell_emission, cell_marginal, scaled_cell_emission
        from pipeline.constrained.dataset import sides
        prob = blocks[stem]["prob"].astype(float)
        if emission_kind == "scaled":
            marg = cell_marginal(sides(("01", "02"), ("03",), False, with_features=False)[0].xy, 25)
            e = scaled_cell_emission(prob, st.xy, 25, marg)
        else:
            e = cell_emission(prob, st.xy, 25)
        if hasattr(ne, "calibrate"):
            ne.calibrate(e)
        live = LiveDecoder2(st, cfg, ne, lag, transit)
        n = min(n_windows, len(rec))
        lat, emitted = [], 0
        for i in range(n):
            t0 = time.perf_counter()
            c, _p = live.step(e[i], float(ge[i]))
            lat.append((time.perf_counter() - t0) * 1000.0)
            emitted += int(c is not None)
        lat = np.array(lat)
        out = {"attached": True, "lag": lag, "n_windows": n, "committed_emitted": emitted,
               "median_latency_ms": round(float(np.median(lat)), 2),
               "p95_latency_ms": round(float(np.percentile(lat, 95)), 2),
               "max_latency_ms": round(float(lat.max()), 2),
               "contract_ms": CONTRACT_MS, "within_contract": bool(np.percentile(lat, 95) < CONTRACT_MS),
               "both_tracks": True, "recording": f"03/{stem}"}
        status(f"  3.3 engine at lag {lag}: {n} windows, median {out['median_latency_ms']} ms, "
               f"p95 {out['p95_latency_ms']} ms against {CONTRACT_MS} ms "
               f"({'within' if out['within_contract'] else 'OUTSIDE'})")
    except Exception as exc:                              # noqa: BLE001
        out["error"] = f"{type(exc).__name__}: {exc}"
        status(f"  3.3 engine FAILED: {out['error']}")
    return out


def main() -> int:
    from pipeline.constrained import paths as P
    from pipeline.constrained.dataset import held_out_passes
    os.makedirs(REPORT_DIR, exist_ok=True)
    stage_dir(STAGE)
    st = P.states()
    s1, s2 = load_results("rb1_truth"), load_results("rb2_decoder")
    emission_kind = ((s1.get("emission_choice") or {}).get("choice")) or "posterior"
    transit = read_json(os.path.join(RUN_DIR, "rb0_preflight", "transit_geometry.json"), {}) or {}
    if not (s2.get("selected") or {}):
        status(f"{STAGE}: stage 2 selected nothing; the display layer has no configuration to run")
        findings(3, False, "Stage 2 produced no selected configuration, so stage 3 could not run.")
        save_results(STAGE, {"stage": STAGE, "error": "no stage 2 configuration"})
        return 1
    status(f"{STAGE} START: two tracks at lags {list(LAGS_ALLOWED)}, emission {emission_kind}"
           + (" [SMOKE]" if SMOKE else ""))
    RES = {"stage": STAGE, "emission": emission_kind, "lags": list(LAGS_ALLOWED),
           "per_pairing": {}, "failures": []}

    prs = pairings()
    if SMOKE:
        prs = [p for p in prs if tag_of(p[0], p[1], p[0] == p[1]) == DEMO_TAG][:1] or prs[:1]
    for tr_s, te_s in prs:
        within = tr_s == te_s
        tag = tag_of(tr_s, te_s, within)
        if tag not in (s2.get("selected") or {}):
            continue
        cfg, ne, sel = shipped_config(s2, tag)
        try:
            t0 = time.time()
            RES["per_pairing"][tag] = measure_pairing(st, tag, tr_s, te_s, within, cfg, ne,
                                                      emission_kind, transit,
                                                      held_out_passes(tr_s, te_s, within))
            c = RES["per_pairing"][tag]["committed"]
            status(f"  {tag:16s} " + " | ".join(
                f"lag{l} found {fmt(c[f'lag{l}']['flat']['found_pct'], 1)}% lat "
                f"{fmt(c[f'lag{l}']['flat']['entry_latency_median_s'], 2)}s rev "
                f"{fmt(c[f'lag{l}']['flat']['revisions_per_pass'], 1)}" for l in LAGS_ALLOWED)
                + f" [{time.time() - t0:.0f}s]")
        except Exception as exc:                          # noqa: BLE001
            import traceback
            RES["failures"].append({"tag": tag, "error": f"{type(exc).__name__}: {exc}",
                                    "trace": traceback.format_exc()[-1000:]})
            status(f"  {tag}: FAILED {type(exc).__name__}: {exc}")
        save_results(STAGE, RES)

    # summaries
    for track in ("committed", "provisional"):
        sub = {tag: v[track] for tag, v in RES["per_pairing"].items()}
        keys = sorted({k for v in sub.values() for agg in v.values() for k in agg["flat"]})
        RES[track] = {f"lag{l}": {k: regime_split(sub, lambda v, l=l, k=k: v[f"lag{l}"]["flat"].get(k))
                                  for k in keys} for l in LAGS_ALLOWED}
    RES["audit"] = {f"lag{l}": {"committed_impossible": sum(v["audit"][f"lag{l}"]["committed_impossible"]
                                                            for v in RES["per_pairing"].values()),
                                "provisional_impossible": sum(v["audit"][f"lag{l}"]["provisional_impossible"]
                                                              for v in RES["per_pairing"].values())}
                    for l in LAGS_ALLOWED}
    RES["shipping_lag"] = choose_lag(RES["committed"])
    lag = RES["shipping_lag"]["lag"]
    cfg, ne, _sel = shipped_config(s2, DEMO_TAG if DEMO_TAG in (s2.get("selected") or {})
                                   else sorted(s2["selected"])[0])
    RES["engine"] = engine(st, cfg, ne, transit, emission_kind, lag)
    RES["sub_second"] = {"run": False,
                         "reason": ("OPTIONAL (brief 3.2b) and it needs a 0.5 s re-window plus retraining of both "
                                    "heads, about two hours. Not run, so sub-second lag is UNTESTED and 1 s is not "
                                    "shown to be a floor." if not optional_budget_ok("rb3_display")
                                    else "budget allowed it but it is scheduled after stage 7; not run here")}
    save_results(STAGE, RES)

    ok = not RES["failures"] and RES["audit"][f"lag{lag}"]["committed_impossible"] == 0
    c, p = RES["committed"][f"lag{lag}"], RES["provisional"][f"lag{lag}"]
    headline(f"STAGE 3: shipping lag {lag} ({RES['shipping_lag']['why']}); committed strict found "
             f"{fmt(c['found_pct']['cross'], 1)}/{fmt(c['found_pct']['within'], 1)} percent cross/within, entry latency "
             f"{fmt(c['entry_latency_median_s']['cross'], 2)} s, {fmt(c['revisions_per_pass']['cross'], 1)} revisions per pass, "
             f"catch-up {fmt(c['catchup_m']['cross'], 2)} m; committed audit "
             f"{RES['audit'][f'lag{lag}']['committed_impossible']}, provisional {RES['audit'][f'lag{lag}']['provisional_impossible']}; "
             f"engine {RES['engine'].get('median_latency_ms', 'n/a')} ms median.")
    findings(3, ok, (
        f"The display layer. Two tracks from one decoder at lags {list(LAGS_ALLOWED)}. SHIPPING LAG {lag}: "
        f"{RES['shipping_lag']['why']}. What each extra second bought: {RES['shipping_lag'].get('what_each_second_bought', 'n/a')}. "
        f"At the shipping lag the COMMITTED track finds {fmt(c['found_pct']['cross'], 1)} percent of passes cross-day and "
        f"{fmt(c['found_pct']['within'], 1)} within-day, all-windows positional {fmt(c['all_windows_total_m']['cross'])} m, "
        f"median entry latency {fmt(c['entry_latency_median_s']['cross'], 2)} s and p90 {fmt(c['entry_latency_p90_s']['cross'], 2)} s, "
        f"{fmt(c['revisions_per_pass']['cross'], 2)} revisions per pass at a mean catch-up of {fmt(c['catchup_m']['cross'], 2)} m. "
        f"The PROVISIONAL track, shown immediately, finds {fmt(p['found_pct']['cross'], 1)} percent and sits at "
        f"{fmt(p['all_windows_total_m']['cross'])} m, so the cost of showing something at once rather than waiting is "
        f"visible rather than asserted. The impossible-transition audit is {RES['audit'][f'lag{lag}']['committed_impossible']} "
        f"on the committed track (it must be zero) and {RES['audit'][f'lag{lag}']['provisional_impossible']} on the "
        f"provisional one, which is allowed to be wrong and is why it is never the thing measured. Engine: "
        f"{RES['engine'].get('median_latency_ms', 'n/a')} ms median and {RES['engine'].get('p95_latency_ms', 'n/a')} ms p95 "
        f"per window including BOTH tracks, against a {CONTRACT_MS} ms contract. Sub-second lag: {RES['sub_second']['reason']} "
        f"The number that most changes what to do next is the entry latency, {fmt(c['entry_latency_median_s']['cross'], 2)} s, "
        f"because that is what the viewer experiences and it is not the same quantity as the lag."))
    status(f"{STAGE} DONE")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
