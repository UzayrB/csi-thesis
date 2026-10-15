# Convenience wrappers. PY defaults to the Anaconda base interpreter; override
# with e.g. `make run PY=python3`.
PY ?= /opt/anaconda3/bin/python3
OUT ?= data
PORT ?=
NODES ?=
RESET ?=          # set to 1 to reboot boards at start and record station MACs
EXPECT ?= 150      # achieved TX rate to gate against; see the Capture Pipeline page in Notion
DURATION ?= 60

.PHONY: help deps test run gate collect inspect identify preflight baseline demo ports

help:
	@echo "make deps      install requirements into the current environment"
	@echo "make ports     list attached receivers"
	@echo "make test      run the test suite"
	@echo "make run       measure for DURATION seconds (default 60), write nothing"
	@echo "make gate      full 10-minute acceptance run, write nothing"
	@echo "make collect   measure and write binary capture into OUT (default data/)"
	@echo "make inspect   check the newest written capture really contains CSI"
	@echo "make identify  say whether a board runs csi_send or csi_recv (read-only)"
	@echo "make preflight identify + a 30 s check. Run before every session."
	@echo "make baseline  baseline capture, operator seated, no participant"
	@echo "make demo      demonstration free-walk: CSI only, NO ground truth, excluded from every split"

deps:
	$(PY) -m pip install -r requirements.txt

ports:
	@ls -1 /dev/cu.usbserial-* 2>/dev/null || echo "no /dev/cu.usbserial-* devices found"

test:
	$(PY) -m pytest tests/ -q

run:
	$(PY) -m pipeline.io.capture_logger --duration $(DURATION) --expect-hz $(EXPECT) $(if $(NODES),--nodes "$(NODES)") $(if $(RESET),--reset)

gate:
	$(PY) -m pipeline.io.capture_logger --duration 600 --expect-hz $(EXPECT) $(if $(NODES),--nodes "$(NODES)") $(if $(RESET),--reset)

collect:
	$(PY) -m pipeline.io.capture_logger --duration $(DURATION) --out $(OUT) --expect-hz $(EXPECT) $(if $(NODES),--nodes "$(NODES)") $(if $(RESET),--reset)

inspect:
	$(PY) -m pipeline.io.inspect_capture $(OUT)

identify:
	$(PY) -m pipeline.io.identify_board $(PORT)

# Everything that must pass before a participant walks in. Sit in the chair
# and stay still: a person MOVING in a link costs 10-20 dB and fails a node
# for a reason that is not a fault, but a person sitting still is part of the
# static channel and belongs in the measurement.
preflight:
	$(PY) -m pipeline.io.identify_board
	@echo ""
	@echo ">>> Sit in the chair and stay still. 30 s check starting."
	@sleep 5
	$(PY) -m pipeline.io.capture_logger --duration 30 --expect-hz $(EXPECT) --reset $(if $(NODES),--nodes "$(NODES)")

# The baseline every session's subtraction needs, which doubles as the
# deployed acceptance run.
#
# NO PARTICIPANT, but the OPERATOR SEATED exactly as during a session. The
# researcher and laptop are part of the static multipath, so a baseline taken
# from a truly empty room differs from the session environment by a whole
# body and leaves that difference as a residual in every window.
#
# BASELINE_S defaults to the 600 s daily run; use 60 for the short one taken
# immediately before each participant.
BASELINE_S ?= 600
baseline:
	@echo ">>> Sit in the chair. No participant. Stay still for $(BASELINE_S) s."
	@sleep 5
	$(PY) -m pipeline.io.capture_logger --duration $(BASELINE_S) --out $(OUT) --expect-hz $(EXPECT) --reset $(if $(NODES),--nodes "$(NODES)")

# The demonstration free-walk. Session 03 only, after the sweep and passes.
# CSI from every receiver, no anchor logger, no labels. The capture starts at
# once; SPACE marks the participant stepping in, a second SPACE marks them
# stepping out and ends the recording (DEMO_SECONDS is only a ceiling). Files
# carry the DEMO infix and every split builder rejects them by name. Any
# video is filmed separately under its own consent and is never used here.
#   make demo P=P01 ROOM=A RXPOS="RX1=2.5,5.5 RX2=-0.5,2.5 RX3=5.5,2.5" NODES="..." [FILMED=1]
P ?=
ROOM ?= A
SESSION ?= 03
RXPOS ?=
FILMED ?=
DEMO_SECONDS ?= 600
demo:
	$(PY) -m pipeline.io.ground_truth --participant $(P) --room $(ROOM) --session $(SESSION) --demo $(if $(FILMED),--filmed) --demo-seconds $(DEMO_SECONDS) $(if $(RXPOS),--rx-positions "$(RXPOS)") $(if $(NODES),--nodes "$(NODES)") --expect-hz $(EXPECT)
