# reports/: the index

Rewritten 1 October 2026, when the reports were split into tracking and identification and renamed
(`project/repository/2026-10-01_reports-reorganisation.md`). Reports are never rewritten: a correction or a later
state is a new, dated file.

**Naming.** `YYYY-MM-DD_topic.md`, the date first and the topic in lower case with hyphens. A letter after the date
keeps the batch it came from (`2026-09-23f_...`). A document that is kept up to date has no date
(`render-rules.md`, `thesis-summary.md`).

**Old paths.** Anything written before the evening of 1 October names the old paths (`reports/ID_FINAL_2026-09-30.md`
and so on). `project/repository/2026-10-01_reports-moves.json` gives every old path its new one, with the reason
for where it went. The freeze records in `runs/` and the pin list keep the old paths too; the freeze tests read them
through that map (`tests/_restructure.py`).

## The layout

| folder | what is in it |
|---|---|
| `tracking/` | the tracking model's records; `briefs/`, `attack/`, `dc2/`, `history/`, `teaching/` |
| `identification/` | the identification model's records; `briefs/`, `dc2/`, `history/`, `teaching/`, `figures/` |
| `project/` | what belongs to both: the DC2 capture days (`dc2-capture/`) and the repository's own records (`repository/`) |
| `attempts/` | superseded and retired documents, safe to delete (`attempts/README.md`) |

## Start here

| document | what it is |
|---|---|
| `tracking/2026-10-01_handoff.md` | **tracking, for a new chat**: the live app as the model (display K1g), every figure with its interval and edge lines, the tags, Uzayr's decisions, open items, files, commands and rules |
| `identification/2026-10-02_handoff.md` | **identification, for a new chat**: identification is closed on engine v4 (Uzayr, 2 October): the final engine, its figures, the render, the teaching pack and the decisions. It supersedes `identification/2026-10-01_handoff.md` |
| `identification/thesis-summary.md` | the summary to write the identification chapter from |
| `../README.md`, `../STATE.md` | the repository's front page, and the state on one screen |

## tracking/

**The current model: the live app (30 September onwards)**

| document | what it is |
|---|---|
| `2026-09-30_live-app-model.md` | the tracking model is the live app: its figures, its gates, and what changed |
| `2026-09-30_live-app-second-instruction.md` | the live app, second instruction: A3's exposure, the identity hook, the dot, the first press, the streamed run |
| `2026-10-01_display-k1g.md` | the live app's display is K1g (Uzayr's decisions of 1 October) |
| `2026-10-01_k1g-check-and-stream.md` | the K1g anchor check, and the streamed B2 run with K1g |
| `2026-10-01_restructure-check.md` | tracking's check of the `pipeline/` restructure |
| `render-rules.md` | the rendering contract; the tests enforce it |
| `2026-09-30_rig-run-protocol.md`, `2026-09-30_rig-run-protocol-addendum.md` | the rig run: the streamed demonstration, the boards as the plugged-in path, one press per walk |
| `2026-10-01_presence.md`, `2026-10-01_propagation.md`, `2026-10-01_freeform-baseline.md` | presence detection, the propagation investigation, and Room A's free-form 2D result (nothing adopted) |
| `future-work.md` | future work |

**The final model and how it was reached (28 to 30 September)**

| document | what it is |
|---|---|
| `2026-09-29_architecture.md` | how the final tracker works, stage by stage |
| `2026-09-29_final-model.md` | the final tracker with the reader leak fixed (the first decode is `history/2026-09-29_final-model-first-decode.md`) |
| `2026-09-29_audit-leakage.md` | the leakage audit of the final tracker |
| `2026-09-29_checks.md`, `2026-09-30_display-provenance.md`, `2026-09-30_time-step-disclosure.md` | the checks of 29 September, where the display's settings come from, and the time-step disclosure |
| `2026-09-30_v2-round.md` | the V2 round: stopped by its own rule, nothing adopted |
| `2026-09-28_devlog.md` | the tracking development log from 28 September |
| `attack/` | the model end to end before the attack (`2026-09-28_architecture.md`), the midpoint check, and the closing reports of stages D1 to D5 |

**The other folders**

| folder | what is in it |
|---|---|
| `briefs/` | Uzayr's tracking briefs, saved verbatim, 22 September to 1 October |
| `dc2/` | the pre-registered cross-room test: the pre-registration (`2026-09-22_prereg-crossroom.md`) and its five addenda, the model freeze and the files it depended on, the capture summary, **the results (`2026-09-28_results.md`)**, the Room B reports, and the training after DC2 with its two post-hoc addenda |
| `history/` | the Room A work before DC2 (16 to 25 September) that a freeze, a pin, a test or a kept record still names: pre-registrations, findings, corrections, batch reports, the geometry audit, the first live system, `semibounded-state.md` (whose section 10 is the ship rule freeze 23h cites), the combined record `record-tracking.md` and the headline log |
| `teaching/` | the app's teaching pack (`2026-10-01_teaching-pack-app-v3.json`) and the first pack, which the app's export reads |

## identification/

| document | what it is |
|---|---|
| `2026-10-02_handoff.md` | the closing handoff: engine v4 is final (supersedes `2026-10-01_handoff.md`) |
| `2026-10-02_v5-check.md` | the v5 check: engine v4 without same-day calibration, +2.78 against v4 (not separable); it failed its check on Room B tracking, so engine v4 stands and identification closed |
| `2026-10-02_overnight.md` | the overnight levers (learned speed, more CNN seeds, a physics vote, MiniRocket): none helped, so engine v4 stands; section 9 has v4's verified figures, the render and the teaching pack; section 10 says why it sits at the speed ceiling. **Identification's current figures** |
| `2026-10-02_lean-in.md` | the lean-in brief and the build of engine v4 (the 4.0 s window, direction from its first 3 s, the radio-only end detector) |
| `2026-10-02_window-gait.md` | longer windows and gait analysis: screens, engine v3 unchanged |
| `2026-10-01_v3-dann.md` | engine v3 (calibration per antenna layout, no rhythm or step rate) and the DANN test |
| `2026-10-01_teaching-pack.md` | the teaching pack, its checks, the addendum, and engine v2 |
| `2026-10-01_lever-screen.md` | the lever screen (1 October, evening) |
| `2026-09-30_final.md` | the GS confirmation and the one-press engine |
| `2026-09-30_extras.md` | a last attempt at a gain, two measures, the B2 rig run and the render |
| `2026-09-30_audit.md`, `2026-09-29_identification-walks.md`, `2026-09-29_development-batch-2.md` | the audit, the identification walks, and development batch 2 (the final ensemble) |
| `2026-09-29_architecture.md` | the identification system end to end: architecture and every transformation |
| `live-interface.md` | the engine's live output: one JSON line per decision |
| `2026-09-28_devlog.md` | the identification development log from 28 September |

**The other folders**

| folder | what is in it |
|---|---|
| `briefs/` | Uzayr's identification briefs, saved verbatim, 28 September to 2 October (the latest are `2026-10-01_window-gait.md`, `2026-10-01_lean-in.md`, `2026-10-02_overnight.md` and `2026-10-02_v5.md`) |
| `dc2/` | DC2 identification, confirmatory: the pre-registration and addenda B to E, the identification sheets (`2026-09-23b` to `d`), the runbook, field card and rehearsal, the scored findings (P1 to P6, P1-GP, the secondary rows), and the v2 registration made after DC2 |
| `history/` | before DC2: the 18 September report, the 23 September pre-registration with addenda A to E, the decisions, the quotable figures, the stage findings `id19` to `id26`, the IDGP queue, and the combined record of the IDMAX batch |
| `teaching/` | the identification teaching packs: engine v4's (`2026-10-02_teaching-pack.json`, `2026-10-02_teaching-notes.md`, `2026-10-02_teaching-readme.md`, `check_png/2026-10-02_*`) beside engine v2's of 1 October; `pipeline/identify/ixt_pack.py` writes here |
| `figures/` | identification figures (`2026-09-23/`, `idmax/`); the thesis summary cites them |

## project/

| folder | what is in it |
|---|---|
| `dc2-capture/` | the capture days for both models: the protocol (`2026-09-18_protocol.md`), the day plan, the field checklist and the capture interface notes |
| `repository/` | how the repository changed: the 24 September cleanup record, its map of moved reports and the note on restoring the code removed then (`archive-code.md`, git tag `pre-cleanup`); the 1 October `pipeline/` restructure with its moves map, the deletion of `pipeline/retired/`, the cleanups of the repository, `tests/` and `runs/`, and this reorganisation with its moves map; the pin list of 24 September (`pinned-files.txt`, released on 1 October) |

## attempts/

Superseded handoffs, check-in logs, older teaching packs and plans that were never carried out. Nothing reads them
and every one is in git; `attempts/README.md` lists them and why each can go.
