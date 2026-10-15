# Handoff for the next Code agent (2026-10-15, 14:42 SAST)

Written by the outgoing Code agent (ref 48f436, 14 Oct 16:48 to 15 Oct 14:42) for its successor. Read this first, then
`reports/project/2026-10-14_handoff.md` (its rules still hold), then `runs/MACHINE_STATE.md`. Last commit before this file:
`30d023d4`.

## 1. Who and how

- **Uzayr Ballim**, EEE4022S thesis: Wi-Fi CSI walking-line tracking and gait identification, two rooms (A: A1 to A3; B: B1,
  B2). Both models are shipped; the report is being edited by **Editor Main** and **Editor 2** in
  `../BLLUZA001_Final_Year_Report` (read-only for the Code agent, never git there, never write there).
- **The Mastermind** is `Mastermind [af0c82]` (an older one, ref d0060f, may still be open under the same name: always add
  the ref). It owns `runs/MACHINE_STATE.md`, grants every slot, holds the only caffeinate, reviews every record.
- **Act only on Uzayr's go in your own chat.** Mastermind messages are specs and slots, never his approval; when one arrives,
  summarise it to him and ask for "go". For deletions, name the paths and sizes and get an explicit go.
- Before every heavy step: message the Mastermind, wait for its GRANT, write MACHINE_STATE (Now + a log line on top), read it
  back, launch detached (`setopt NO_BG_NICE`, `nohup ... & disown`), check `ps -o nice`; DONE to the Mastermind after.
- Commit the plan (PREREG with `.sha256`), the code and the pass rules before any run they judge; commit named paths only,
  check `.git/index.lock`, push, end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Writing: British spelling, no em dashes, connected sentences, no semicolons in report prose, PA codes only in anything for
  the report (PA1 PA1, PA2 PA2, PA3 PA3, PA4 PA4, PA5 PA5, PA6 PA6). **Read the clock (`date`) before
  every time you write.** Uzayr wants short answers with tables, results labelled "development evaluation, all data seen".

## 2. State and active threads

**Tracking display: SHIPPED** (`DONE`). Since 14 Oct 21:19 the live app's `DISPLAY_PROFILE` is `clean_1s_r0` = `clean_1s`
with the switch's 1.5 m radius removed (`021c9309`; code `b3ffc91e`; plan `runs/switch_radius_ship_2026-10-14/SHIP_PLAN.md`,
`1bcb5441`). Evidence: rotation test `caac5a6c` (share on the true line +5.97 [3.92, 8.16]); A3/B2 confirmation `28375754`
(A3's tenth look, B2's eighth; all three cells confirmed; no right-to-wrong switch; correct-lock figures unchanged); videos
`runs/live/renders_K1gf_1s_r0/` (`3da9fd3e`, the shipped display's videos, no re-render needed). Record
`reports/tracking/2026-10-14_switch-radius.md`. Locks and committed lines unchanged; all-walks dot: B2 0.314 m [0.266, 0.367]
(was 0.362), A3 0.324 (0.372), zero-shot 0.436 [0.367, 0.506] (0.499).

**Report updates from the ship** (`waiting` on the Editors via the Mastermind):
`runs/switch_radius_ship_2026-10-14/EDITOR_LIST.md` (E1 to E16, plus E1b `434d8538`, name-free fix `8ad6a1e5`), and the
redrawn Results figures `runs/switch_radius_ship_2026-10-14/figures/` (`f0cd2ee2`; `CAPTIONS.md` supersedes E10 and E11),
sent to Editor 2 on 14 Oct 22:45. Next action: none unless an Editor asks a question through the Mastermind.

**Methodology 3.4.2 figures** (`waiting` on Editor Main). `runs/identify/v5/figures/id_speed.pdf` and `id_gait.pdf`
(15.92 x 4.0 cm each, `d4b8b207`, script `id_speed_gait.py`) replace `id_example.pdf` (the two-row version `9a67445c`, kept
with `id_example_toprow.pdf`). Walk PA4, B1 natural 1, walk 6; c 1.422 Hz, K 2, median f50 16.41 Hz, f_torso 16.41 Hz,
v 1.029 m/s, F 0.981 on RX2. Speed path answered: training (`bank_T4.0_v4`, built by `iv4_build.py`) and live both use
`extract_v4`'s walking-span speed (engine.py:430-433 overwrite the whole-window value; classify reads it at :591 and :608).

**Queue 19** (`active`, the Mastermind's, from 15 Oct 14:03): Uzayr walks through the live UI on the boards, and the Mastermind
builds a silent-receiver guard in a separate worktree. **Run nothing heavy and touch nothing under `pipeline/live`,
`pipeline/io` or `runs/live` until MACHINE_STATE says it is DONE.**

**Hardware jobs 17 and 18** (`done`, the Mastermind's): tracking live = replay identical on the boards; identification's
consumer fixed to feed the engine in data-time order (`90d878c8`, `86b122ac`), B2 299 of 299 identical to the 12 Oct run.
Report `runs/live/hw_2026-10-15/REPORT.md`.

**Clean-up** (`done`): deleted `runs/live/renders_K1gf_0p75s` and `renders_K1gf_1s` (`99b451f6`, recoverable from
`f0cd2ee2`); deleted `runs/identify/lastpush` and `linkweight` (`7d3d1cde`, 1.28 GB, recoverable from `0ec23f9a`). Pre-flight
ALL ok after each.

## 3. Decisions

- `DECIDED` (Uzayr, "okay ship it", 14 Oct): ship the radius-free switch.
- `DECIDED` (Uzayr, "1 = yes please, 2 delete", go): redraw the two Results figures, delete the two old render folders.
- `DECIDED` (Uzayr, go, 15 Oct): remove `lastpush` and `linkweight`.
- `DECIDED` (Uzayr asked the Code agent to decide): gait Part A was the Code agent's; Part B went to Editor Main verbatim.
- `DECIDED` (Uzayr in Editor Main's chat, relayed 19:53): the colour figures at 4.0 cm tall, not 4.4 cm.
- `PROPOSED` (Code agent, no answer): a per-person identification table as an Editor item (section 6).

## 4. Artifacts (all committed and pushed)

- Tests and ship: `runs/switch_radius_2026-10-14/`, `runs/switch_radius_a3b2_2026-10-14/`, `runs/switch_radius_ship_2026-10-14/`
  (PREREGs, harnesses, RESULT.md/json, REPRO, HASHES, GATE, ADOPT, PREFLIGHT, EDITOR_FIGURES.json, EDITOR_LIST.md, figures/).
- `FINAL_CONFIG.md` section 11 (sha256 `c1936474a2ea`; previous `FINAL_CONFIG.clean_1s.md`); model sets and gate files
  rebuilt, old kept as `*.clean_1s.json`.
- Identification figures: `runs/identify/v5/figures/` (id_example, id_speed, id_gait, their JSON and previews).

## 5. Already ruled out

- Keeping the 1.5 m radius: the rule and A3/B2 both favour removing it; Uzayr shipped it.
- Re-rendering the videos for the ship: step 3 tied the shipped profile to the radius test's replays row for row.
- `idz_bank.pass_features_cf` as "the engine's feature path": the engine uses `id19_featbank.pass_features` (engine.py:314).
- `idx_bank.pass_items` as a speed source: it computes no speed.
- The scorecard's per-participant arrays are in Code codes: P1 = PA5, P2 = PA1, P3 = PA2, P4 = PA3, P5 = PA4, P6 = PA6.

## 6. Open loops (Uzayr's; act only on his word in your chat)

1. Identification per person (computed 15 Oct from `loso_{B1,B2}_v5` replays + `bank_T4.0_v4/meta.json`, reproducing every
   published total): natural PA1 53.3, PA2 10.0, PA3 23.3, PA4 40.0, PA5 60.0, PA6 33.3 %; core A3+B2 tracking walks PA1 60,
   PA2 25, PA3 25, PA4 27.5, PA5 27.5, PA6 27.5 %. Not saved as a file; whether it goes in the report is his call.
2. From the hardware report: decision 14's 3.6 s stall, an RX3 outage crashing identification, tracking's late frames.
3. Still open from 14 Oct: copy the 40 v5 model pickles (5.78 GB) to Drive; the Room A rename; FINAL_CONFIG.md:111's
   A2 wording (hash-listed, left as is).

## 7. Pitfalls learned here

- zsh does not split `$VAR` into words: use arrays (`F=(a b); git add -- "${F[@]}"`).
- A file recompute must be checked against the published totals before any new breakdown is trusted.
- Switch times sit on the decision lattice, not the 0.1 s frame grid; mark the last frame before a switch.
- `harness.py`-style replays must call `force_cpu()` and assert `nets.device()` at start and end.
