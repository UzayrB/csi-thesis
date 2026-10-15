# DC2 identification rehearsal, Thursday 24 or Friday 25 September 2026

Uzayr is the walker. The rehearsal checks the one thing DC2 cannot fix on the day, the physical
setup, and it writes only to `data/rehearsal_idpath/`. The DC2 scorer refuses any `REHEARSAL` file,
so nothing here can reach a result. Every command runs from the repo root with
`PYTHONPATH=. /opt/anaconda3/bin/python3 -m`.

1. **Set up the rig as for DC2.**
   - TX at (2.5, -0.5), RX1 at (2.5, 5.5), RX2 at home (-0.5, 2.5) facing east, RX3 at (5.5, 2.5),
     every node at 1.1 m.
   - The operator seat at (-1.0, 0.5), with the laptop and the powered USB-C hub.
   - Tape RX2's outline and arrow at home and at both candidate spots.
2. **Check the 4 m cable.** It must reach RX2 at (2.0, -0.5) with slack, through the air or from a
   hub on the floor. If it does not, use (1.5, -0.5). Record the choice BEFORE DC2, with
   `pipeline.identify.capture_idpath --set-spot primary` (or `fallback`). It cannot be changed
   once DC2 files exist.
3. **Soak for 10 minutes** at the full rate, with RX2 on the 4 m run at the identification spot:
   `pipeline.io.capture_logger --duration 600 --out data/rehearsal_idpath/soak --reset`.
   - **Confirm no brownout or reboot messages** appear in its output.
   - **Confirm RX2's packet rate and loss match RX1's and RX3's.** Read them from
     `pipeline.identify.rehearsal_check`, section `link_health`.
4. **Run one slot:**
   - move RX2 to the spot (north, aligned, photographed, time noted);
   - `pipeline.identify.capture_idpath --rehearsal --empty --position idspot --participant <code> --day 1 --move-time HH:MM`;
   - `pipeline.identify.capture_idpath --rehearsal --participant <code> --day 1 --block natural --passes 5 --height-cm <cm> --weight-kg <kg>`
     (presses at every metre, six per pass);
   - move RX2 home (east, aligned, photographed, time noted);
   - `pipeline.identify.capture_idpath --rehearsal --empty --position home --participant <code> --day 1 --move-time HH:MM`.

   **Why 5 passes:** `--passes 5` records only 5 against day 1's plan of 10. That is deliberate,
   and the rehearsal checker only reports it.
5. **Check the layout** with `pipeline.identify.rehearsal_check`. It lists the rehearsal
   recordings, sidecars and pass counts.
   - `id29_dc2_score --check-layout` is for the DC2 folder, and it rejects rehearsal files by
     design.
   - **Before DC2,** run `pipeline.identify.id29_dc2_score --check-layout` once on the empty
     `data/room_B`. It must list every recording as missing, and nothing else, which proves it
     runs.
6. **Confirm RX2 modulates during the walks.** In `rehearsal_check`'s `rx2_modulation`, TX-RX2's
   gait or Doppler ratio against its empty room must be at least 2.
   - **If RX2 is flagged FLAT, raise it before DC2**; the exit code is 1.
   - TX-RX1 may read flat in the Doppler band: line A is its line of sight.
7. **Archive.** Keep the rehearsal files in `data/rehearsal_idpath/`, which the scorer never
   searches and whose names it refuses. Write the chosen spot and the soak result into this file.
8. **Confirm tracking capture still works unchanged**, with RX2 home: run the tracking protocol's
   own start-up check.

**Recorded at the rehearsal** (fill in on the day):

- chosen spot:
- cable slack:
- soak packet rates:
- brownouts:
- RX2 modulation ratio:
- tracking check:
