# HANDOFF: tracking, 2026-09-29 09:57 SAST (clock read). After the full model attack

## 0. Orientation (for a new chat)

**The project.** TDR-03 is WiFi CSI tracking: one transmitter, three ESP32 receivers (RX1 to RX3 =
links 0 to 2) and 12 taped lines on a 5 x 5 m floor. A participant presses a button at each end of a
walk. The tracker answers three things:
- which line was walked: the COMMITTED answer, at the walk's end;
- the line the display locks onto 2 s after the start press: the LOCK;
- where on the line the walker is: the drawn dot.

**The sessions:** Room A on three days (A1 = "01", A2 = "02", A3 = "03") and Room B on two (B1, B2),
six participants and 120 evaluated passes per session.

**The split:** train and choose on A1, A2 and B1 ONLY. A3 and B2 are the tests and the renders.

**How choices are made:** on three rotations, A1+A2 -> B1 (weighted x2), A1+B1 -> A2 and A2+B1 -> A1,
by `pd_rule`:
- the objective is the weighted mean of committed + lock;
- adopt only if the paired 95% interval is above zero;
- and the edge guard holds: no E_col1, E_col5, E_row1 or E_row5 recall dropped to 0 or halved.

## 0b. Working rules (Uzayr's standing practice; follow them without being asked)

- **Writing:** British spelling, and no em dashes. Run `date` before writing any time into a file.
- **Git:**
  - commit only your own files, added BY NAME; never `git add -A`;
  - end each commit with the co-author line the session gives you.
- **Never edit these:**
  - `data/` (read only);
  - any file listed in `reports/PINNED_FILES.txt` (for example `dc2_run.py`, `dc2_scorerlock.py`,
    `decoder*.py`, `g3_final.py`);
  - any existing report or freeze: they are the thesis record, so write NEW files instead.
- **Never use the free-movement recordings.**
- **Processes:** never `pkill` broadly. Read a process's command line, then kill by PID.
- **Compute:** since 09:55 on 29 September the GPU and CPU belong to the Identification session.
  Before any training or long decode, message it and wait for it to pause its lane 4 (it keeps a
  STOP4 file).
- **Test discipline:** A3 and B2 have had their two sanctioned looks. A new tracking change is judged
  on the rotations only. Any new A3 or B2 figure is a THIRD look: say so plainly, and ask Uzayr first.
- **System requirements:**
  - no leakage: whole-session splits, statistics from training data or causal pre-pass data only;
  - everything claimed live is causal;
  - signal only: no pace feature, elapsed time or dead reckoning; the decoder's motion prior is allowed.

## 1. Read first

1. `reports/MODEL_FINAL_TRACKING.md`: the final model, its results, resolution, latency, the
   ablation ladder, the configuration and the hashes.
2. `reports/ATTACK_MIDPOINT_2026-09-29.md` and `reports/ATTACK_D{1..5}_CLOSING_2026-09-29.md`: one
   report per stage.
3. `reports/DEVLOG_TRACKING_2026-09-28.md`: every change, the reason for it, and the result, in
   order.
4. `reports/BRIEF_tracking_attack_2026-09-28.md`: the brief, verbatim.

`reports/HANDOFF_TRACKING_2026-09-28.md` is the state before the attack, kept as the record.

## 2. State

- **Model work is DONE**, ahead of the brief's stop (23:59, 1 October).
- **The final model:** `runs/dc2_results/cells/fin_A3` (and `fin_B2`, the same weights), decoded with
  `pd_decode --variants relgateU`.
- **Zero-shot:** `runs/dc2_results/cells/zsf_B2`.
- **A3 and B2 have now been tested twice** (the midpoint and FINAL). Under the brief there are no
  further looks at them.
- **The GPU and CPU belong to Identification** since 09:55. Tracking runs nothing.

## 3. The machinery (all in `pipeline/constrained/`)

- `pd_cells.py`: the harness.
  - Cells, views and the pipelined queue (`pqueue`).
  - The `prep` phase for test cells: networks, inference and readers, and never the default decode.
  - The stage-cell registry: `runs/dc2_results/stage_cells.json`.
- `pd_train.py`: training options (aug, mixup, early stopping with snapshots, fixed epochs). With
  every option off it is the recipe bit for bit (`tests/test_pd_train.py`).
- `pd_arch.py`: the shared-encoder architectures (fuse, attn).
- `pd_decode.py`: decode variants with no retraining. Its `ref` reproduces a cell exactly; it also
  records the drawn-dot resolution.
- `pd_rule.py`: the brief's choice rule. The objective counts B1 x2, with a paired bootstrap and the
  edge guard.
- `pd_final.py`: the test tables. `pd_latency.py`: per-window head timing.

## 4. Open items for Uzayr

1. **The edge guard at small counts.** It rejected three options singly on 1- or 2-walk moves (see
   the midpoint report, section 5). The combination passed, so the outcome was unaffected.
2. **Configuration B.** It equals A on this model: the relative gate replaces the calibrated gate,
   and the null re-anchoring falls outside DC2's guard. DC2's own B definition was not decoded on the
   final model. Doing so would be a third look at B2.
3. **Renders and the live system.** The live system (`pipeline/live/`) still runs the frozen
   per-link heads and the absolute gate. Porting the final model means three things:
   - the shared-encoder heads (`install_arch_infer` shows the loading);
   - relative RSSI;
   - the relative gate: one multiply per recording, from pre-press idle radio.

   This has not been done yet.
4. **The start-of-walk readers** still come from the pooled per-link heads. Retraining them on the
   final architecture was not tried.

## 5. How to operate the harness (commands, run from the repo root)

**Why commands go through `pd_cells` and `pd_decode`.** Every step runs in its own subprocess with
environment variables that bind its data roots (`pd_cells.env_for`). Several modules refuse to import
unless those roots are bound (`u1_adapt`, `p1_runup`, `q1_diag`, `t2_embed`). So do not import them in
a bare shell. Use these entry points:

```
python3 -m pipeline.constrained.pd_cells run --cell <cell> [--phase gpu|cpu|prep|all]
python3 -m pipeline.constrained.pd_cells pqueue --cells <c1> <c2> ...        # train one at a time, decode alongside
python3 -m pipeline.constrained.pd_decode --cell <cell> --variants ref relgateU ...
python3 -m pipeline.constrained.pd_rule compare --name <N> --base <prefix>[@variant] --arm <prefix>[@variant] [--lock scorer]
python3 -m pipeline.constrained.pd_final --name <N> --a3 <cell@variant> --b2 <cell@variant>   # TEST tables: third look
```

**Cells.**
- A rotation cell is `<prefix>_<train>_to_<validation>`, for example `d4c_fuse_0102_to_B1`.
- New cells are registered in `runs/dc2_results/stage_cells.json`, so no code edit is needed. Keys:
  `opts` (aug, rrel, early, ...), `heads`, `arch`, `base`; `rotations: false` for test cells.

**The rotation prefixes on record:**

| prefix | what it is | objective |
|---|---|---|
| `d1sp` | D0, the pooled per-link recipe | 76.04 |
| `d2pc_ar` | + aug and rrel | 85.83 |
| `d2pc_ar@relgateU` | + the relative gate | 100.21 |
| `d4c_fuse@relgateU` | **THE FINAL CONFIGURATION** | **122.50** |

A new change must beat `d4c_fuse@relgateU` by the rule.

**Always check before trusting:**
- `pd_decode`'s `ref` variant must reproduce a cell's own rows exactly: it prints `PLUMB ... EXACT`.
- `pd_train` with every option off is the recipe bit for bit: `tests/test_pd_train.py`.

**Gotchas that cost time on 28 and 29 September:**
- **Every step subprocess re-imports `pd_cells.py`.** Editing it while a queue runs changes that
  queue's later steps. Keep it importable at every moment: write to a temporary file, then
  `os.replace`, then `python3 -c "import pipeline.constrained.pd_cells"`.
- **zsh does not split an unquoted `$VAR` into words.** Use `${=VAR}`, or arrays.
- **`Windows.subset` takes a BOOLEAN mask.** An index array silently returns everything.
- **Test cells must use `--phase prep`.** Running `run` on a test cell would decode A3 or B2 with the
  shipped default decode: an unsanctioned look.
- **Monitors expire after 30 minutes.** Queues keep running without them; re-arm them.
- **Room B training sessions are linked without their calibration recording** (`<name>_C`). Test
  sessions are linked whole, because configuration B needs the walk.

**Logs:**
- `runs/dc2_results/logs/` (queues, chains, decodes);
- rule outputs in `runs/dc2_results/rule/`;
- tables in `runs/dc2_results/final/`.

## 6. A paste-ready opening prompt for a new tracking chat

> Tracking session. Read `reports/HANDOFF_TRACKING_2026-09-29.md` in full first (sections 0 and 0b
> are the rules), then `reports/MODEL_FINAL_TRACKING.md`. The final model is fixed and A3/B2 have had
> both sanctioned looks, so do not produce new A3 or B2 figures without asking me. The GPU and CPU
> belong to the Identification session: message it before running anything heavy. The task: <what you
> want, e.g. "port the final model into the live system (pipeline/live/) and check it reproduces
> pd_decode's decisions on a development session">.

