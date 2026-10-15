import queue, sys, threading, time
from pipeline.io.ground_truth import KeyReader
how = sys.argv[1]
q, stop = queue.Queue(), threading.Event()
print("READY", flush=True)
if how == "start":                      # as pipeline/live/rig.py run() does today
    kr = KeyReader(q, stop); kr.start()
    t0 = time.time()
    while time.time() - t0 < 2.0 and q.empty(): time.sleep(0.01)
else:                                   # as a context manager (cbreak)
    with KeyReader(q, stop):
        t0 = time.time()
        while time.time() - t0 < 2.0 and q.empty(): time.sleep(0.01)
print("GOT", repr(q.get_nowait().key) if not q.empty() else None, flush=True)
