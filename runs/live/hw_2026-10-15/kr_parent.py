import os, pty, sys, time, select
for how in ("start", "with"):
    pid, fd = pty.fork()
    if pid == 0:
        os.execvpe("/opt/anaconda3/bin/python3", ["python3", sys.argv[1], how], dict(os.environ, PYTHONPATH="."))
    buf = b""
    while b"READY" not in buf:
        buf += os.read(fd, 1024)
    time.sleep(0.3)
    os.write(fd, b" ")                   # one SPACE, no Enter
    t_end = time.time() + 4
    while time.time() < t_end and b"GOT" not in buf:
        r, _, _ = select.select([fd], [], [], 0.2)
        if r:
            try: buf += os.read(fd, 1024)
            except OSError: break
    os.waitpid(pid, 0)
    line = [l for l in buf.decode(errors="replace").splitlines() if "GOT" in l]
    print(f"KeyReader via {how!r}: {line[0].strip() if line else 'no result'}")
