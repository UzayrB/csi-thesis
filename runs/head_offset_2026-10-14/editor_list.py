"""Step 7 of DECISION_1p0.md: the Editor list for the 1.0 s head offset, NOT applied (the report repository is only read).

Each item gives a place, the exact old text, the new text and the source of every figure. When this runs, every old text is
looked up in the report repository's current files (whitespace collapsed, since the .tex wraps lines), and the list says
whether it was found exactly once, so an item the Editor or Uzayr has already changed is marked rather than quoted stale.
The per-video item (Results 4.5) is filled from RENDERS_TABLE.json. Writes EDITOR_LIST.md beside this file.

    python3 runs/head_offset_2026-10-14/editor_list.py

Development evaluation, all data seen.
"""

from __future__ import annotations

import json
import os
import re
import time

J = os.path.join
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
THESIS = os.path.join(os.path.dirname(REPO), "BLLUZA001_Final_Year_Report")
REC = "Code/reports/tracking/2026-10-14_head-offset-1s.md"
S4 = "Code/runs/head_offset_2026-10-14/STEP4_CPU_RESULT.json; Code/runs/head_offset_2026-10-14/EDITOR_FIGURES.json"


def squash(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def found(rel: str, old: str) -> int:
    p = J(THESIS, rel)
    if not os.path.exists(p):
        return -1
    text = "\n".join(ln for ln in open(p, encoding="utf-8").read().split("\n") if not ln.lstrip().startswith("%"))
    return squash(text).count(squash(old))                       # comment lines dropped, as LaTeX drops them


ITEMS = [
    {"place": "Methodology, the switch paragraph (Chapters/Methodology.tex)", "file": "Chapters/Methodology.tex",
     "why": "Section 5 of the record: the switch reads the drawn marker, so a display setting can change it.",
     "old": "To correct a wrong lock the drawn line may switch once sliding over 0.5~s to a line whose $J(L)$, without the "
            "line prior, has led by over 2~nats at two consecutive checks.",
     "new": "To correct a wrong lock the drawn line may switch once, sliding over 0.5~s, to a line whose $J(L)$, without the "
            "line prior, has led by over 2~nats at two consecutive checks while that line's current state lay within "
            "1.5~m of the drawn marker, and never in the marker's last metre of its line. Because both of these read the "
            "drawn marker, the display's timing can change a switch, though never the lock or the committed line.",
     "source": f"{REC}, Section 5; Code/pipeline/constrained/switching.py, decide_walk"},
    {"place": "Methodology, the position-track sentence (Chapters/Methodology.tex; already rewritten for 1.0 s)",
     "file": "Chapters/Methodology.tex",
     "why": "At 1.0 s there is no glide: the marker first appears at a drawn decoded position on the line, not exactly at "
            "the line's start (rule 2a retired, Uzayr). No glide remains in the code (the anchor span is empty).",
     "old": "Using the first window (-1s to 1s) and its center it places the tracker at the start of the chosen line.",
     "new": "From the first window ($-1$ to 1~s), centred on the press, it places the marker on the chosen line at its first "
            "decoded position, a median of about 0.1~m and at most about 1.1~m from the line's start, with no glide.",
     "source": f"{S4} (rule_2a_retired_reported: B2 median 0.090 m, max 1.140 m; A3 0.130 m, 1.003 m)"},
    {"place": "Methodology, fig:lock-timing (already rewritten for 1.0 s): the caption", "file": "Chapters/Methodology.tex",
     "why": "Optional precision: the dot sits on average 4 to 6 cm ahead, not exactly level (decision 2).",
     "old": "draws each window's position at its centre, level with the truth.",
     "new": "draws each window's position at its centre, about level with the truth (on average 4 to 6~cm ahead).",
     "source": f"{S4} (signed offset, correct-lock: A3 +0.037, B2 +0.063, zero-shot B2 +0.058 m)"},
    {"place": "Results, tab:tracking-headline, footnote a (Chapters/Results.tex)", "file": "Chapters/Results.tex",
     "why": "The head offset was changed after A3 and B2 were seen.",
     "old": "Every display setting was re-chosen without A3 and the lock and committed line were unchanged on all 120 walks, "
            "and the live app now draws that display.",
     "new": "Every display setting was re-chosen without A3 and the lock and committed line were unchanged on all 120 walks; "
            "the live app now draws that display with its head offset raised to 1.0~s after A3 and B2 were seen, which "
            "again leaves every lock and committed line unchanged.",
     "source": f"{REC}, Sections 4 and 6.2"},
    {"place": "Results, the A3 paragraph after tab:tracking-headline (Chapters/Results.tex)", "file": "Chapters/Results.tex",
     "why": "The glide no longer exists, and the A3 figures above (0.304 m) are the 0.75 s display's, no longer the live app's.",
     "old": "The live app now draws this re-chosen display. Its glide over the first quarter of a second after the lock was "
            "changed to start exactly at the locked line's entry, which removes the one render rule the re-chosen settings "
            "broke (on 11 of the 120 walks) without moving any decoded position, lock or committed line, so the A3 figures "
            "above are the live app's.",
     "new": "The live app now draws this re-chosen display with one change made after A3 and B2 had been seen: its head "
            "offset was raised from 0.75~s to 1.0~s, so that each position is drawn at its own window's centre with no "
            "glide (Uzayr's decision, overriding the 0.875~s the pre-registered rule chose on the development rotations). "
            "Every lock and committed line is unchanged, and A3's correct-lock dot error falls further, from 0.304~m to "
            "0.246~m [0.207, 0.285], a paired difference of $-0.059$~m [$-0.113$, $-0.004$].",
     "source": f"{S4} (final|03 correct_lock_walks median_m); {REC}, Sections 3, 4 and 6.2"},
    {"place": "Results, the dot paragraph before tab:tracking-dot (Chapters/Results.tex)", "file": "Chapters/Results.tex",
     "why": "The new dot figures from step 4, measured from the first decoded frame (the table's own measure).",
     "old": "On B2 its median error is 0.430~m [0.367, 0.503] over all walks, with 56.1\\% [50.0, 62.5] of frames within "
            "0.5~m, and on the walks whose lock is correct the median falls to 0.313~m [0.281, 0.344], with 75.5\\% [70.7, "
            "80.4] of frames within 0.5~m. A3 is almost the same, at 0.407~m over all walks and 0.304~m [0.271, 0.340] on "
            "correct-lock walks.",
     "new": "On B2 its median error is 0.362~m [0.298, 0.449] over all walks, with 60.0\\% [53.3, 66.9] of frames within "
            "0.5~m, and on the walks whose lock is correct the median falls to 0.219~m [0.191, 0.256], with 82.0\\% [77.6, "
            "85.8] of frames within 0.5~m. A3 is close, at 0.372~m over all walks and 0.246~m [0.207, 0.285] on "
            "correct-lock walks.",
     "source": S4},
    {"place": "Results, the same paragraph: the 90th percentiles (Chapters/Results.tex)", "file": "Chapters/Results.tex",
     "why": "The new 90th percentiles.",
     "old": "on correct-lock walks nine frames in ten lie within 0.71~m on B2 and 0.84~m on A3, whereas over all walks the "
            "90th percentile reaches 2.68~m on both,",
     "new": "on correct-lock walks nine frames in ten lie within 0.69~m on B2 and 0.79~m on A3, whereas over all walks the "
            "90th percentile reaches 2.65~m on B2 and 2.61~m on A3,",
     "source": f"{S4} (p90_m: B2 0.686 and 2.648, A3 0.790 and 2.607)"},
    {"place": "Results, the same paragraph: the comparison sentence (Chapters/Results.tex)", "file": "Chapters/Results.tex",
     "why": "The comparison that matters now is against the 0.75 s display the app drew until 14 October; the signed offset "
            "and the disclosure belong here.",
     "old": "Compared on the same B2 walks with the display the application drew until 10~October, the clean display puts "
            "5.4 points [0.3, 10.8] more frames within 0.5~m over all walks and leaves the correct-lock walks where they "
            "were, with their median moved by only 0.010~m [$-0.046$, 0.058].",
     "new": "Compared on the same B2 walks with the 0.75~s head offset the application drew until 14~October, drawing each "
            "position at its own window's centre lowers the correct-lock median by 0.093~m [0.046, 0.137] and puts 6.6 "
            "points [0.8, 12.6] more of those frames within 0.5~m, with every lock and committed line unchanged. The dot, "
            "which trailed the walker by 0.25~m, now sits slightly ahead of it, by 0.063~m [0.006, 0.117] on average on "
            "B2's correct-lock walks. The head offset of 1.0~s was chosen by the author after the development results "
            "were seen, over the 0.875~s the pre-registered rule chose and against a guard fixed beforehand (on one "
            "development walk the drawn line made a switch it had not made before), and after A3 and B2 were decoded "
            "with it he accepted the slight lead and that one B2 walk (PA6, walk~5) loses the switch that had corrected "
            "its wrong lock.",
     "source": f"{S4} (final|B2: median diff -0.093 [-0.137, -0.046], within diff +6.555 [+0.756, +12.570], signed offset "
               f"-0.249 -> +0.063 [+0.006, +0.117]); {REC}, Sections 4, 5 and 7"},
    {"place": "Results, tab:tracking-dot, the B2 row", "file": "Chapters/Results.tex",
     "why": "Step 4's figures, from the first decoded frame.",
     "old": "B2 & 0.430 & 56.1 & 0.313 & 0.707 & 75.5 \\\\",
     "new": "B2 & 0.362 & 60.0 & 0.219 & 0.686 & 82.0 \\\\",
     "source": f"{S4} (final|B2)"},
    {"place": "Results, tab:tracking-dot, the A3 row", "file": "Chapters/Results.tex",
     "why": "Step 4's figures, from the first decoded frame. (Optional: keep the 0.75 s rows as \"0.75~s display\" rows.)",
     "old": "A3\\textsuperscript{a} & 0.407 & 57.4 & 0.304 & 0.836 & 74.2 \\\\",
     "new": "A3\\textsuperscript{a} & 0.372 & 58.5 & 0.246 & 0.790 & 75.8 \\\\",
     "source": f"{S4} (final|03)"},
    {"place": "Results, tab:tracking-dot, the caption's intervals", "file": "Chapters/Results.tex",
     "why": "The new intervals (the 10 Oct record's bootstrap, which reproduces the old ones exactly).",
     "old": "B2's figures are 0.430~m [0.367, 0.503] and 56.1\\% [50.0, 62.5] over all walks and 0.313~m [0.281, 0.344], "
            "0.707~m [0.645, 0.774] and 75.5\\% [70.7, 80.4] on correct-lock walks. For A3 only the correct-lock medians "
            "have intervals on record, 0.304~m [0.271, 0.340] with the live app's display and 0.391~m [0.354, 0.435] with "
            "the earlier one.",
     "new": "B2's figures are 0.362~m [0.298, 0.449] and 60.0\\% [53.3, 66.9] over all walks and 0.219~m [0.191, 0.256], "
            "0.686~m [0.587, 0.765] and 82.0\\% [77.6, 85.8] on correct-lock walks. For A3 the correct-lock median is "
            "0.246~m [0.207, 0.285] with the live app's display, 0.304~m [0.271, 0.340] with the 0.75~s head offset drawn "
            "from 10 to 14~October, and 0.391~m [0.354, 0.435] with the display before that.",
     "source": S4},
    {"place": "Results, tab:tracking-dot, footnote a", "file": "Chapters/Results.tex",
     "why": "The head offset was changed after A3 and B2 were seen.",
     "old": "Every display setting re-chosen on the development rotations without A3, now the live app's display, with "
            "A3's exposure as in \\cref{tab:tracking-headline}.",
     "new": "Every display setting re-chosen on the development rotations without A3, then the head offset raised to "
            "1.0~s after A3 and B2 were seen, the live app's display since 14~October, with A3's exposure as in "
            "\\cref{tab:tracking-headline}.",
     "source": f"{REC}, Section 4"},
]


def render_rows() -> list:
    p = J(HERE, "RENDERS_TABLE.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else []


def main() -> int:
    rows = render_rows()
    out = ["# The Editor list for the 1.0 s head offset (not applied)", "",
           f"Generated {time.strftime('%d %b %Y %H:%M:%S')} SAST by `runs/head_offset_2026-10-14/editor_list.py`, against "
           "the report repository as it read then (only read, never written). Development evaluation, all data seen. PA "
           "codes as the report uses them. For each item: the place, the exact old text (checked against the current file), "
           "the new text, and the source of every figure.", ""]
    for i, it in enumerate(ITEMS, 1):
        n = found(it["file"], it["old"])
        state = {1: "found once", 0: "NOT FOUND (already changed?)", -1: "file missing"}.get(n, f"found {n} times")
        out += [f"### E{i}. {it['place']}", "", f"*Why:* {it['why']}  ", f"*Old text ({state}):*", "",
                "```", it["old"], "```", "", "*New text:*", "", "```", it["new"], "```", "", f"*Source:* {it['source']}", ""]
    k = len(ITEMS)
    if rows:
        b2 = [r for r in rows if r["session"] == "B2"]
        a3 = [r for r in rows if r["session"] == "A3"]
        rng = lambda v: f"{min(v):.3f} to {max(v):.3f}"                              # noqa: E731
        pct = lambda rs, key: f"{min(100 * r[key] / r['walks'] for r in rs):.0f} to {max(100 * r[key] / r['walks'] for r in rs):.0f}"  # noqa: E731
        corr = [f"{r['pa']}'s {r['session']} video (walk {p})" for r in rows for p, o, n_, kind in r["switches"]
                if kind == "corrects a wrong lock"]
        fails = sum(r["park"] + r["together"] + r["over_one_switch"] + (1 if r["lock_changes"] else 0) for r in rows)
        lag = {s: max(r["draw_lag_max_s"] for r in rows if r["session"] == s) for s in ("A3", "B2")}
        fe = [r["first_frame_from_entry_m"] for r in rows]
        out += [f"### E{k + 1}. Results 4.5, the twelve demonstration videos (the per-video figures and the showcase)", "",
                "*Why:* the videos were re-recorded with the 1.0 s display (`runs/live/renders_K1gf_1s/`); PA6's B2 walk 5 no "
                "longer shows a corrected lock; rule 2a is retired.  ",
                "*Old text:* the paragraph from \"The twelve demonstration videos, one per participant\" to \"while the committed "
                "line stays right.\" (Chapters/Results.tex, Section 4.5).", "", "*New text:*", "", "```",
                "The twelve demonstration videos, one per participant for A3 and for B2, are recordings replayed through the "
                "application with its current display, the head offset at 1.0~s, at real-time pace, semi-constrained with one "
                "start press per walk, with the application's own screen recorded, and each video's log equals its replay at "
                f"full speed row for row. Per video the lock and the committed line are right on {pct(a3, 'lock_right')}\\% "
                f"and {pct(a3, 'committed_right')}\\% of A3's walks and on {pct(b2, 'lock_right')}\\% and "
                f"{pct(b2, 'committed_right')}\\% of B2's, and the dot's median error is "
                f"{rng([r['dot_all_median_m'] for r in a3])}~m on A3 and {rng([r['dot_all_median_m'] for r in b2])}~m on B2 "
                f"over all walks, and {rng([r['dot_ok_median_m'] for r in a3])}~m and {rng([r['dot_ok_median_m'] for r in b2])}~m "
                f"on correct-lock walks. The render rules hold on all twelve, with {'no' if fails == 0 else fails} park, "
                "together or lock-change failure and no walk with more than one switch, the dot on the locked line on the "
                f"green marker's first frame, a median of {min(f['median'] for f in fe):.2f} to {max(f['median'] for f in fe):.2f}~m "
                f"and at most {max(f['max'] for f in fe):.2f}~m from its entry since the glide is gone, and a draw lag of at "
                f"most {max(lag.values()):.3f}~s. "
                + "".join(f"{r['pa']}'s B2 video shows the headline session as it usually runs, with "
                          f"{'every committed line right' if r['committed_right'] == r['walks'] else str(r['committed_right']) + ' of ' + str(r['walks']) + ' committed lines right'}, "
                          f"{r['lock_right']} of {r['walks']} locks and "
                          f"{'the lowest all-walks dot error of the twelve' if r['dot_all_median_m'] == min(x['dot_all_median_m'] for x in rows) else 'an all-walks dot error'} "
                          f"of {r['dot_all_median_m']:.3f}~m. " for r in b2 if r["pa"] == "PA3")
                + ("A switch corrects a wrong lock in " + " and ".join(corr) + ", while PA6's B2 video now shows only a switch "
                   "from one wrong line to another on walk~11, with the committed line right." if corr else
                   "No video now shows a switch correcting a wrong lock."),
                "```", "",
                f"*Source:* `Code/runs/live/renders_K1gf_1s/ACCEPTANCE.md`; `Code/runs/head_offset_2026-10-14/RENDERS_TABLE.json` "
                "and `RENDERS.json` (every log equal to its full-speed replay). Which video to feature is the Editor's choice: "
                "PA3's B2 video was the \"as it usually runs\" pick; its figures are in ACCEPTANCE.md.", ""]
        k += 1
    out += [f"### E{k + 1}. Results, the latency table's draw lag", "",
            "*No change:* the draw lag is the same at 1.0 s as at 0.75 s, at most 0.141 s on B2 and 0.153 s on A3 "
            "(Code/runs/head_offset_2026-10-14/STEP4_CPU_RESULT.json, draw_lag_s; the renders' ACCEPTANCE.md). The lock "
            "frame's median 0.13 s there comes from the 30 Sep streamed run, not touched by this change.", "",
            f"### E{k + 2}. Results, fig:error-cdf (results_dot_cdf.pdf)", "",
            "*Its data change:* the cumulative distributions should be redrawn from the 1.0 s logs "
            "(`Code/runs/head_offset_2026-10-14/step4_cpu/final/semi_disp-K1gf_causal/`, identical row for row to the live "
            "app's renders). Not redrawn here.", "",
            f"### E{k + 3}. The ledger (Appendices/appendixa.tex, tab:ledger, Tracking): a new row", "", "```",
            "Head offset of the drawn dot, 0.75, 0.875 and 1.0~s\n"
            "    & Development rotations (A1 and A2 to B1, A1 and B1 to A2, A2 and B1\n"
            "      to A1), 360 passes, correct-lock walks\n"
            "    & Median dot error from the press 0.387, 0.326 and 0.311~m (0.311\n"
            "      $[0.277, 0.350]$); signed offset $-0.35$, $-0.19$ and $-0.04$~m\n"
            "    & 1.0~s kept by the author over the rule's 0.875~s, against a guard\n"
            "      fixed beforehand (one walk's switch changed); on A3 and B2 every\n"
            "      lock and committed line unchanged \\\\",
            "```", "", f"*Source:* `Code/runs/head_offset_2026-10-14/SELECTION.json`; {REC}, Sections 3 and 4.", "",
            f"### E{k + 4}. The look table (Appendices/appendixa.tex): new rows", "",
            "Uzayr's count calls the 1.0 s decode A3's eighth and B2's sixth look; the table's own convention, which counts the "
            "11 Oct re-read as A3's eighth and B2's sixth, makes it the ninth and seventh. Proposed rows, the numbering for "
            "Uzayr to choose:", "", "```",
            "    Head offset 0.875~s, stopped part-way, unscored & 14 Oct & (part) & (part) \\\\\n"
            "    Head offset 1.0~s, first run on the GPU, not used & 14 Oct & (+1) & (+1) \\\\\n"
            "    Head offset 1.0~s, the live app's display & 14 Oct & 9 & 7 \\\\\n"
            "    Total, with the dwell ablation and the GPU run & & 11 & 9 \\\\",
            "```", "", f"*Source:* {REC}, Section 10.", "",
            f"### E{k + 5}. Discussion and Recommendations", "",
            "*Nothing to remove:* the report holds no recommendation to extend the head-offset grid (searched "
            "Chapters/Discussion.tex, Chapters/Recommendations.tex and the Results for \"grid\" and \"edge of\"); the remark "
            "\"part of the remaining lag is set by the grid range\" is only in the 9 Oct Code record, which is not edited.", ""]
    open(J(HERE, "EDITOR_LIST.md"), "w", encoding="utf-8").write("\n".join(out))
    print("\n".join(l for l in out if l.startswith("### ") or l.startswith("*Old text")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
