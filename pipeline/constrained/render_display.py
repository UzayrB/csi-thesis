"""The display model: what the red dot does, and the one rule it obeys on every frame.

THE ONE RULE. Every drawn red position is either a decoded position or a point on the straight
segment between two decoded positions, and nothing is ever drawn ahead of the latest decode.
`check_rule` returns the violation rather than a boolean, so a render can say which frame failed
and why instead of merely failing.

WHY THIS IS A LIBRARY AND NOT CODE INSIDE THE RENDERER. The previous renderer measured frames,
folders and byte counts and never measured what was on the screen: it drew no red dot at all,
reported a causality count that had never been incremented, and took its highlighted line from the
TRUE label. Every stage in this batch imports this module, so the thing measured is the same object
that is drawn.

THE LIVE DOT IS THE DECODER'S RUNNING PATH. `fixed_lag_path` reads a Viterbi backtrace at each
display step rather than taking a per-window argmax. The chain structure forbids backward
transitions, so a single Viterbi path is monotone along its line by construction; the argmax had no
continuity constraint at all and stepped backwards, which `backward_steps` counts on the old
display as the record of what this fixes.
"""

from __future__ import annotations

import numpy as np

#: drawn motion cap while CROSSING from one line to another, metres per second
SWITCH_CAP_M_S = 2.0
#: the room centre, which is also the decoded position of the null state
CENTRE = (2.5, 2.5)


# --------------------------------------------------------------------------- the decoded path

def fixed_lag_path(e_stacked, lT, st_lo, st, lo, hi, lag_w):
    """The decoded position at each display step, from a fixed-lag Viterbi backtrace.

    Display step i is window lo+i, decoded with every window up to lo+i+lag_w, which is exactly
    the evidence available at the moment that step is shown. Returns one record per step.

    An off-chain state (null or transit) carries no position, so the last on-chain state is held
    and the hold is counted rather than drawn as a jump to the room centre.
    """
    from pipeline.constrained.decoder import viterbi
    n = hi - lo + 1
    out, held = [], 0
    last_on = None
    for i in range(n):
        end = min(hi, lo + i + lag_w)
        s = viterbi(e_stacked[lo:end + 1], lT, log_start=st_lo)
        k = int(s[i]) if i < len(s) else int(s[-1])
        on_chain = k < st.n_states
        if on_chain:
            last_on = k
        elif last_on is not None:
            held += 1
            k = last_on
        else:
            held += 1
        name = chain_of(st, k) if k < st.n_states else ""
        out.append({"step": i, "window": lo + i, "evidence_window": int(end), "state": int(k),
                    "line": name, "on_chain": bool(on_chain)})
    return out, held


def locked_chain_path(e_res, lT_chains, st, lo, hi, lag_w, chain, log_start=None):
    """The drawn path AFTER the lock: a fixed-lag Viterbi restricted to ONE chain.

    Once the display has committed to a line it stays on that line for the rest of the walk, right
    or wrong. The position is still DECODED, not projected: the restricted Viterbi runs over that
    chain's own states with that chain's own transitions, so every drawn point remains a decoded
    position and the one rule still holds. Projecting onto the line instead would draw positions
    the decoder never produced.

    log_start IS NOT OPTIONAL IN PRACTICE. Without it every state on the chain is equally likely at
    the first window, and when the emissions are flat WITHIN a chain the path degenerates: it
    starts at the chain's first state and advances at the preferred step, so the drawn position
    becomes a function of ELAPSED TIME rather than of the radio. Measured on 2026-09-20: every pass
    locked at exactly 2.25 m of arc, which is three windows at the preferred step from zero. That
    is the clock failure this project refuses elsewhere, and it reached the screen because a
    display construct was not put through the substitution test. Pass the entry distribution
    restricted to this chain.
    """
    from pipeline.constrained.decoder import viterbi
    a, b = st.slice_of[chain]
    sub_T = lT_chains[a:b, a:b]
    e_sub = np.asarray(e_res)[:, a:b]
    ls = None
    if log_start is not None:
        ls = np.asarray(log_start, float)[a:b].copy()
        m = float(np.max(ls[np.isfinite(ls)])) if np.isfinite(ls).any() else 0.0
        ls = ls - m
    out = []
    n = hi - lo + 1
    for i in range(n):
        end = min(hi, lo + i + lag_w)
        s_ = viterbi(e_sub[lo:end + 1], sub_T, log_start=ls)
        k = int(s_[i]) if i < len(s_) else int(s_[-1])
        # evidence_window is the LATEST window that entered this step's Viterbi. It is not the
        # same as `window`, and the difference is the whole of the causality question: `window` is
        # the position being named, `evidence_window` is the radio that named it. A check that
        # looks only at `window` cannot see a decode that read the future.
        out.append({"step": i, "window": lo + i, "evidence_window": int(end), "state": int(a + k),
                    "line": chain, "on_chain": True})
    return out


def chain_of(st, state_idx):
    for nm in st.names:
        a, b = st.slice_of[nm]
        if a <= state_idx < b:
            return nm
    return ""


def xy_of(st, state_idx):
    from pipeline.constrained.decoder import decoded_xy
    q = decoded_xy(np.array([int(state_idx)]), st)
    return (float(q[0][0]), float(q[0][1]))


def entry_position(e_stacked, st_lo, st, lo):
    """Where the dot jumps to at the start press: the best ON-CHAIN state under the entry prior.

    For soft entry this is the first window's own position posterior, so the dot starts where the
    radio says the walker is. For free entry the prior is flat and this is the argmax of the
    emission alone, which is still a decoded position and not an assumption.
    """
    v = np.asarray(st_lo, float)[:st.n_states] + np.asarray(e_stacked[lo], float)[:st.n_states]
    if not np.isfinite(v).any():
        return None, ""
    k = int(np.nanargmax(np.where(np.isfinite(v), v, -np.inf)))
    return k, chain_of(st, k)


def monotonicity_violations(path, st):
    """Backward steps ALONG A LINE. Zero is expected for a Viterbi path, by chain structure."""
    bad = 0
    for a, b in zip(path, path[1:]):
        if a["line"] and a["line"] == b["line"] and b["state"] < a["state"]:
            bad += 1
    return bad


def backward_steps(names, states):
    """The same census on the OLD per-window argmax display, which had no continuity constraint."""
    bad = 0
    for i in range(1, len(names)):
        if names[i] and names[i] == names[i - 1] and 0 <= states[i] < states[i - 1]:
            bad += 1
    return bad


# --------------------------------------------------------------------------- the drawn dot

class Dot:
    """The drawn red position, frame by frame.

    WITHIN A LINE it glides between the two most recent decoded points, so it never holds for five
    frames and steps. It glides from P[i-1] towards P[i] rather than from P[i] towards P[i+1],
    because P[i+1] is not yet decoded and drawing towards it would be drawing ahead of the latest
    decode. That costs one stride of on-screen lag and the cost is measured rather than argued.

    ACROSS A LINE SWITCH the drawn motion is capped at SWITCH_CAP_M_S so a switch reads as a move
    and not a teleport, and the destination is RETARGETED to the latest decoded point on the new
    line as each decode arrives rather than fixed when the switch began.

    THE CAP NEVER HOLDS THE DOT BACK ALONG ITS OWN LINE. The moment the dot is on the decoder's
    line it snaps to the latest decoded point on that line, so a slide can never leave it trailing
    a decode it has already caught.
    """

    def __init__(self, cap_m_s=SWITCH_CAP_M_S):
        self.cap = cap_m_s
        self.pos = CENTRE
        self.line = ""
        self.anchor = CENTRE          # a decoded position: one end of the segment we are on
        self.target = CENTRE          # a decoded position: the other end
        self.crossing = False
        self.arrivals = 0
        self.capped_frames = 0

    def park(self):
        """Between walks the dot is parked at the room centre, the null state's own position."""
        self.pos = CENTRE
        self.line = ""
        self.anchor = self.target = CENTRE
        self.crossing = False

    def jump_to_entry(self, xy, line):
        """At the start press the dot jumps to the entry position. Permitted by the brief."""
        self.pos = tuple(xy)
        self.line = line
        self.anchor = self.target = tuple(xy)
        self.crossing = False

    def step(self, dt, dec_line, p_prev, p_now, frac):
        """Advance one frame.

        dec_line  the line the decoder is on at the latest available step
        p_prev    the decoded position one step earlier, or None
        p_now     the decoded position at the latest available step
        frac      how far through the current display interval this frame is, in [0, 1)
        """
        if p_now is None:
            return self.pos
        if self.line == dec_line and not self.crossing:
            # on the decoder's own line: glide between the two most recent decoded points
            a = p_prev if p_prev is not None else p_now
            self.anchor, self.target = tuple(a), tuple(p_now)
            f = float(np.clip(frac, 0.0, 1.0))
            self.pos = (a[0] + (p_now[0] - a[0]) * f, a[1] + (p_now[1] - a[1]) * f)
            return self.pos
        # a switch: cross to the new line, capped, retargeting onto the latest decoded point.
        # The crossing is anchored on p_prev, the last DECODED point on the line being left, and
        # the dot snaps onto it first. That snap is at most one glide interval short of where the
        # dot already was, about 0.13 m, and it is what keeps the drawn point on a segment whose
        # BOTH ends are decoded positions rather than one end being a mid-glide point.
        if not self.crossing:
            self.crossing = True
            if p_prev is not None:
                self.pos = tuple(p_prev)
                self.anchor = tuple(p_prev)
            else:
                self.anchor = tuple(self.pos)
        self.target = tuple(p_now)
        vx, vy = self.target[0] - self.pos[0], self.target[1] - self.pos[1]
        d = float(np.hypot(vx, vy))
        reach = self.cap * dt if self.cap is not None else d
        if d <= reach or d < 1e-9:
            # ARRIVED: snap to the latest decoded point on that line, and never trail it again
            self.pos = self.target
            self.line = dec_line
            self.crossing = False
            self.anchor = self.target
            self.arrivals += 1
        else:
            self.capped_frames += 1
            self.pos = (self.pos[0] + vx / d * reach, self.pos[1] + vy / d * reach)
        return self.pos


# --------------------------------------------------------------------------- the one rule

def check_rule(drawn, anchor, target, latest_xy_set, tol=1e-6):
    """THE ONE RULE, per frame. Returns None when the frame is legal, else why it is not.

    `anchor` and `target` must both be decoded positions and `target` must be one the decoder has
    already produced. The drawn point must lie on the segment between them.
    """
    if anchor is None or target is None:
        return "no segment: the dot was drawn without two decoded endpoints"
    if tuple(np.round(target, 6)) not in latest_xy_set:
        return f"target {target} is not a decoded position the decoder has produced"
    a, b, p = np.asarray(anchor, float), np.asarray(target, float), np.asarray(drawn, float)
    ab = b - a
    L2 = float(ab @ ab)
    if L2 < 1e-12:
        off = float(np.linalg.norm(p - a))
        return None if off <= 1e-3 else f"drawn {drawn} is {off:.4f} m from the single decoded point"
    t = float((p - a) @ ab / L2)
    if t < -1e-6 or t > 1.0 + 1e-6:
        return f"drawn {drawn} is off the segment at t={t:.4f}, so it is beyond a decoded endpoint"
    off = float(np.linalg.norm(p - (a + t * ab)))
    if off > 1e-3:
        return f"drawn {drawn} is {off:.4f} m off the straight segment between two decoded points"
    return None


# --------------------------------------------------------------------------- the acceptance metric

def on_screen_tracking(red, green, within_m=0.5, missing_is_a_miss=True):
    """The acceptance number, at the DISPLAYED time so the display lag counts against it.

    red and green are the DRAWN positions, frame by frame, over one walk. Frames where the truth
    is unavailable are excluded and counted, never treated as a hit.
    """
    d, skipped, missing = [], 0, 0
    for r, g in zip(red, green):
        if g is None:
            skipped += 1                       # no truth to compare against, never a hit
            continue
        if r is None:
            # the OLD renderer hid the dot. A frame with no red dot cannot be tracking the green
            # one, so it counts against the figure rather than being quietly dropped.
            missing += 1
            if missing_is_a_miss:
                d.append(float("inf"))
            continue
        d.append(float(np.hypot(r[0] - g[0], r[1] - g[1])))
    if not d:
        return {"n_frames": 0, "n_skipped": skipped, "n_no_red_dot": missing,
                "within_pct": None, "mean_m": None}
    d = np.asarray(d, float)
    fin = d[np.isfinite(d)]
    return {"n_frames": int(len(d)), "n_skipped": int(skipped), "n_no_red_dot": int(missing),
            "within_pct": float(100.0 * np.mean(d <= within_m)),
            "mean_m": (float(np.mean(fin)) if len(fin) else None),
            "median_m": (float(np.median(fin)) if len(fin) else None),
            "mean_excludes_frames_with_no_dot": bool(missing and missing_is_a_miss),
            "within_m": within_m}


# --------------------------------------------------------------------------- the frame loop

def simulate_walk(path, st, t_start, t_press, entry_xy, entry_line, stride, lag_w, fps,
                  cap, green_at, frames=None, lead=False, shift_w=0.0):
    """One walk, frame by frame. THE SAME LOOP the renderer draws with, so the measured display
    and the drawn display cannot drift apart.

    `green_at(tq)` returns the truth position at that frame time, or None.
    Returns the drawn red positions, the green positions, and every rule violation found.
    """
    pts = [xy_of(st, p["state"]) if p["state"] >= 0 else None for p in path]
    lines = [p["line"] for p in path]
    dot = Dot(cap_m_s=cap)
    dot.jump_to_entry(entry_xy, entry_line)
    decoded = {tuple(np.round(entry_xy, 6))}
    red, green, viol = [], [], []
    # the caller may hand in ITS OWN frame times. The renderer does, so the frames measured here
    # are the very frames drawn, rather than a parallel grid that happens to look similar.
    frames = np.arange(t_start, t_press, 1.0 / fps) if frames is None else np.asarray(frames, float)
    prev_tq = None
    for tq in frames:
        dt = (1.0 / fps) if prev_tq is None else float(tq - prev_tq)
        prev_tq = tq
        g = green_at(float(tq))
        green.append(g)
        # SHIFT_W: the drawn dot's phase, in strides. 0.0 is trailing interpolation and
        # is the default, so every caller that does not pass it is bit-identical. It
        # exists so that `lead=True`, which is a +1 stride phase shift wearing the
        # clothes of an interpolation choice, becomes one member of a one-parameter
        # family that can be swept and reported with a sign.
        raw = (tq - t_start) / stride - lag_w + shift_w
        i_max = int(np.floor(raw))
        if i_max < 0:
            red.append(dot.pos)                  # holding at the entry position, a decoded point
            continue
        i_max = min(i_max, len(pts) - 1)
        for j in range(i_max + 1):               # everything decoded so far is available
            if pts[j] is not None:
                decoded.add(tuple(np.round(pts[j], 6)))
        if lead:
            # LEADING INTERPOLATION. The dot glides from the decoded point it is on TOWARDS the
            # next one, instead of from the previous one towards the current.
            #
            # Trailing interpolation stalls on the first step, because the previous point and the
            # current point are the same point: the dot appears and then sits still for a full
            # stride, 0.6 s at a 0.5 s stride and 10 fps, while the truth marker walks away. That
            # is the same fault as a marker shown before the dot, one stride smaller, and it
            # happens at the start of EVERY walk.
            #
            # Both endpoints are decoded positions, so rule 2 holds: this is a point on the
            # straight segment between two of them and nothing is projected. It is causally legal
            # because the display runs behind by more than the extra half second it needs, which
            # the render asserts before it starts.
            p_prev = pts[i_max]
            p_now = pts[i_max + 1] if (i_max + 1) < len(pts) else pts[i_max]
            if p_now is not None:
                decoded.add(tuple(np.round(p_now, 6)))
        else:
            p_now = pts[i_max]
            p_prev = pts[i_max - 1] if i_max > 0 else entry_xy
        frac = float(np.clip(raw - i_max, 0.0, 1.0))
        dot.step(dt, lines[i_max], p_prev, p_now, frac)
        bad = check_rule(dot.pos, dot.anchor, dot.target, decoded)
        if bad:
            viol.append({"t": float(tq), "step": int(i_max), "why": bad})
        red.append(dot.pos)
    return {"red": red, "green": green, "violations": viol, "frames": [float(x) for x in frames],
            "n_frames": int(len(frames)),
            "capped_frames": int(dot.capped_frames), "arrivals": int(dot.arrivals),
            "n_frames_without_dot": int(sum(1 for r in red if r is None))}
