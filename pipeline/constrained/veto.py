# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: THE SHIPPED COMMITTED-DECISION VETO, a_veto_1.0.

from __future__ import annotations

VETO_THR = 0.01
VETO_W = 1.0
A2_WEIGHT = 0.5


# {session|stem|pass_id: {line: log term}}: the A2 term merged with the veto, as u2_useit builds...
def committed_start_terms(tr_s, te_s, st, cache=None) -> dict:
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
