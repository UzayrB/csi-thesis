"""Item 4a of reports/BRIEF_RESTRUCTURE_CHECK_2026-10-01.md: every tracking code file the restructure changed (base
5782af8, restructure 6769f8c), diffed line by line. A changed line is PATH-ONLY when the old line, translated through
reports/PIPELINE_MOVES_2026-10-01.json (its modules, its file paths and the removed packages' path forms), equals the
new line. Every other changed line is listed for reading.

    python3 runs/dc2_results/restructure_check/diff_check.py

Writes runs/dc2_results/restructure_check/DIFF_CHECK.json.
"""

import difflib
import json
import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
J = os.path.join
BASE, NEW = "5782af8", "6769f8c"
#: identification's files are not tracking's (Uzayr: don't touch Identification's files)
ID_FILES = re.compile(r"^(pipeline/identify/|pipeline/retired/identify/|pipeline/live/identify|tests/test_id|tests/test_identification)")


def git(*a):
    return subprocess.check_output(["git", *a], cwd=ROOT, text=True)


def translations():
    mv = json.load(open(J(ROOT, "reports", "PIPELINE_MOVES_2026-10-01.json"), encoding="utf-8"))
    pairs = []
    for old, new in mv["modules"].items():
        pairs.append((old, new))                                          # pipeline.a.b -> pipeline.c.d
        pairs.append((old.replace(".", "/"), new.replace(".", "/")))      # pipeline/a/b -> pipeline/c/d (with or without .py)
        o, n = old.split("."), new.split(".")
        # the "from pipeline.a import b" form, and the parts form: "pipeline" / "a" / "b.py"
        pairs.append((f"from {'.'.join(o[:-1])} import {o[-1]}", f"from {'.'.join(n[:-1])} import {n[-1]}"))
        pairs.append((" / ".join(f'"{x}"' for x in o[1:-1]) + f' / "{o[-1]}.py"',
                      " / ".join(f'"{x}"' for x in n[1:-1]) + f' / "{n[-1]}.py"'))
    pairs.sort(key=lambda p: -len(p[0]))
    return pairs


def translate(line, pairs):
    for o, n in pairs:
        line = line.replace(o, n)
    return line


def main():
    pairs = translations()
    rows = git("diff", "--name-status", "-M", BASE, NEW).splitlines()
    out = {"base": BASE, "restructure": NEW, "files": {}}
    for r in rows:
        f = r.split("\t")
        st, old, new = f[0], f[1], f[-1]
        if not re.search(r"\.(py|sh)$|Makefile$", new) or st in ("A", "D") or st == "R100" or ID_FILES.match(new) or ID_FILES.match(old):
            continue
        a = git("show", f"{BASE}:{old}").splitlines()
        b = git("show", f"{NEW}:{new}").splitlines()
        other, n_path = [], 0
        sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                continue
            olds, news = a[i1:i2], b[j1:j2]
            if tag == "replace" and len(olds) == len(news) and all(translate(x, pairs) == y for x, y in zip(olds, news)):
                n_path += len(olds)
                continue
            # a re-wrapped import (one statement over a different number of lines): compare the joined text
            jo = re.sub(r"\s+", " ", translate(" ".join(olds), pairs)).strip()
            jn = re.sub(r"\s+", " ", " ".join(news)).strip()
            if jo == jn:
                n_path += max(len(olds), len(news))
                continue
            other.append({"old": olds, "new": news, "at_new_line": j1 + 1})
        out["files"][new] = {"old_path": old, "status": st, "path_lines": n_path, "other": other}
    with open(J(ROOT, "runs", "dc2_results", "restructure_check", "DIFF_CHECK.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    clean = [k for k, v in out["files"].items() if not v["other"]]
    print(f"{len(out['files'])} tracking code files changed; {len(clean)} path-only")
    for k, v in out["files"].items():
        if v["other"]:
            print(f"== {k} ({v['status']}, from {v['old_path']}): {v['path_lines']} path lines, {len(v['other'])} other hunks")
            for h in v["other"]:
                print("   -", h["old"][:4])
                print("   +", h["new"][:4])


if __name__ == "__main__":
    main()
