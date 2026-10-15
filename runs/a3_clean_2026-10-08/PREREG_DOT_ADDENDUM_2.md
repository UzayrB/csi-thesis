# PREREG_DOT addendum 2, 9 October 2026, 10:27 SAST (clock read): the A3 dot label rule, fixed before A3 is decoded

**Status.** Written and committed during stage 2. This is before stage 5, before the full A3-clean configuration is
written, and before A3's seventh look. The authority is Uzayr's instruction of 9 Oct (about 10:25), "Keep the plan, and
fix the label rule before A3 is decoded". `PREREG_DOT.md` (cdab65c4) and addendum 1 (7aa5b1ff) stand unchanged. This
closes the gap in PREREG_DOT section 5, which had no rule for a clean dot that is worse than the shipped one.

**What had been seen when it was written:** stage 1's rotation figures (development data). Nothing on A3 from the dot
side.

## The rule (Uzayr's words, verbatim)

> The shipped A3 dot drops its OPTIMISTIC label only if the clean configuration's A3 dot error is not worse than the
> shipped one. The test is the paired difference (clean minus shipped) in median dot error on correct-lock walks, by the
> same cluster bootstrap as the rest of the run: its 95 % interval must include zero or lie wholly below it. Otherwise the
> shipped A3 dot keeps OPTIMISTIC, and the clean figure is reported beside it. No label changes by judgement after the
> decode.

## How it is computed, fixed now

- **The two decodes:**
  - **clean:** A3's seventh look, with the full A3-clean configuration (`a3_full.py`);
  - **shipped:** the shipped A3 replay, `runs/live/replay/final/semi_disp-K1g_causal_realtime_screen/` (the 0.5 s
    ship). A3's sixth look (Overall, lock side) is identical to it on every walk and every dot.
- **The walks:** A3's 120 evaluated walks. A walk counts when its lock is correct in BOTH decodes; the same walk set is
  used for both, so the difference is paired.
- **The frames:** `app_score`'s correct-lock dot error, the A3 dot figure the report quotes. That is every drawn frame of
  the walk from its first decoded frame on (the park and the anchor span excluded, rule 2b), against the truth at frame
  time minus 2.0 s. Each decode uses its own frames.
- **The statistic:** the median of the pooled frame errors over the counted walks, clean minus shipped.
- **The interval:** a cluster bootstrap with the walk as the cluster, as everywhere in this run (`app_score`'s 1,000
  draws, seed 0). Each draw resamples the counted walks with replacement, and the SAME drawn walks give both medians. The
  95 % interval is the 2.5th and 97.5th percentiles of the 1,000 differences.
- **The decision, mechanical:**
  - **the interval includes zero or lies wholly below it:** "not worse", and the shipped A3 dot drops OPTIMISTIC;
  - **the interval lies wholly above zero:** the shipped A3 dot keeps OPTIMISTIC, and the clean figure is reported beside
    it.
- **No label changes by judgement after the decode.** `a3_full.py score` writes the decision with its inputs.
