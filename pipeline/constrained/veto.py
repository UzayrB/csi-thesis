"""THE SHIPPED COMMITTED-DECISION VETO, `a_veto_1.0`. One definition, for the render and the headline.

Shipped 2026-09-23d (batch 23d, item 3; `reports/ITEM3_REPORT_2026-09-23.md`): it passes every
condition of the ship rule with (f) as amended, on the ONE lattice, and the operator's instruction 4
says a passing item-1 arm is included. On 2026-09-22 it had been declined by judgement (multiple
testing across eleven arms, a result exactly on the two-pass bar with the two readings disagreeing
in sign), not by a rule; that caveat still describes it and is carried beside every figure.

WHAT IT IS. A pre-press REGION reader (`u1_adapt`'s AdaBN features, `u2_useit.fit_reader`, an LDA
fitted on the TRAINING sessions only) reads the windows around each start press. A line whose
start region the reader gives posterior below `VETO_THR` is pushed DOWN by `VETO_W * 3.0` nats in
the committed decision's start term; nothing is ever pushed up. `VETO_THR` was chosen on the
selection folds (s01_to_s02, s02_to_s01) so the TRUE region is vetoed on at most 2 percent of their
passes, by `u2_useit`, on the one lattice.

It touches the COMMITTED decision only (`night_track`'s start term in the decision decode). The
lock, the drawn path and the render's bounded end-press text do not read it.
"""

from __future__ import annotations

VETO_THR = 0.01        #: u2_useit's plain veto threshold on the ONE lattice, selection folds only
VETO_W = 1.0           #: the arm's weight; the push is VETO_W * u2_useit.VETO_NATS (3.0) nats
A2_WEIGHT = 0.5        #: the shipped A2 start-consistency term's weight, unchanged


def committed_start_terms(tr_s, te_s, st, cache=None) -> dict:
    """{session|stem|pass_id: {line: log term}}: the A2 term merged with the veto, as u2_useit
    builds `a_veto_1.0`'s decision options, for one pairing."""
    from pipeline.constrained.q4_arms import start_terms
    from pipeline.constrained.t1_region import assert_grouped_by_pass
    from pipeline.constrained.u1_adapt import session_rows
    from pipeline.constrained.u2_useit import ADAPT_MODE, fit_reader, merged, term_veto
    cache = {} if cache is None else cache
    a3 = start_terms(tr_s, te_s, st, A2_WEIGHT)
    Xtr, ytr, ktr, _w1, utr, _a1 = session_rows(tr_s, st, ADAPT_MODE, cache)
    Xte, _yte, kte, _w2, ute, _a2 = session_rows(te_s, st, ADAPT_MODE, cache)
    if not len(Xtr) or not len(Xte):
        return dict(a3)
    assert_grouped_by_pass(ktr, utr)
    assert_grouped_by_pass(kte, ute)
    assert not (set(ktr) & set(kte)), "leakage: a pass on both sides of the reader"
    _pred, proba, classes = fit_reader(Xtr, ytr, Xte, False)
    return merged(dict(a3), term_veto(kte, proba, classes, st, VETO_THR, VETO_W))
