"""pipeline.live: the TDR-03 system running live on the rig, identification mode then tracking mode.

Design: `reports/tracking/history/2026-09-25_live-system-design.md`. Results: `reports/tracking/history/2026-09-25_live-system.md`. Built
beside the frozen code, never in it: every module here imports `pipeline/constrained/`,
`pipeline/identify/` and `pipeline/io/` and edits nothing. Each piece is proved EQUAL to its offline
counterpart on replayed recordings (`gates.py`, `tests/test_live_*.py`).

    stream.py      packets and presses -> the press-aligned tree's windows, bit for bit
    anchor.py      the device clock anchored causally, as a live system must
    pool.py        the five-head pool, and the DISP_END display head, one window at a time
    start_terms.py A2 and the veto for one pass; AdaBN on the idle windows before the first press
    decoder.py     the committed decision: the frozen decoder called on each prefix
    display.py     the dot, the lock, the switch: f3_render's composition, frame by frame
    tracking.py    all of the above in the causal order, one session
    identify.py    id29's features and PRIMARY and S0, pass by pass
    screen.py      the window; rig.py the capture consumer and keys; replay.py recorded sessions
    __main__.py    the one entry command: python3 -m pipeline.live {gates,replay,replay-identify,rig}
"""
