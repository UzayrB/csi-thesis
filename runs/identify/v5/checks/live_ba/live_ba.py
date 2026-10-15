"""Before/after check of the live app (identify_engine.replay_session): model, session, recordings, tag -> jsonl + npz."""
import os, sys, json, time
import numpy as np
model, session, nrec, tag = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
out = os.path.dirname(os.path.abspath(__file__))
from pipeline.identify import engine as EN
from pipeline.live import identify_engine as IE
j = os.path.join(out, f"{tag}_{model}_{session}_{nrec}.jsonl")
if os.path.exists(j):
    os.remove(j)
t = time.time()
app = IE.replay_session(session, model=model, device="cpu", jsonl=j, recordings=nrec)
D = app.decisions
np.savez(os.path.join(out, f"{tag}_{model}_{session}_{nrec}.npz"), t0=np.array([d["t0"] for d in D]),
         t_dec=np.array([d["t_dec"] for d in D]), ensemble=np.array([d["ensemble"] for d in D]),
         confidence=np.array([d["confidence"] for d in D]), calib_n=np.array([d["calib_n"] for d in D]),
         top=np.array([d["top"] for d in D]))
print(json.dumps({"tag": tag, "model": model, "session": session, "recordings": nrec, "decisions": len(D),
                  "update_s_n": len(app.e.session.update_s), "pool": len(app.e.session), "seconds": round(time.time() - t, 1)}), flush=True)
