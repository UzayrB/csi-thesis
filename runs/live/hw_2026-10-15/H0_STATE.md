# H0: state (15 Oct 2026, 09:55:06)

- **git HEAD:** baddef1f222f1273c4ccc4a5909cb715b9c3b598 (pipeline/ and tests/ clean in the working tree).
- **Tracking (read from pipeline/live/final_model.py):** MODEL_CELLS["final"] = {"03": "f05_A3", "B2": "f05_B2"} (zeroshot
  {"B2": "z05_B2"}); DISPLAY_PROFILE = "clean_1s_r0" (prior flatten_0.50, prior_f 0.5, shift_w 1.0, head offset 1.0 s,
  switch arm A, theta 2.0, at most 1 switch, final 1.0 m, radius None); semi mode (one SPACE per walk); CPU (force_cpu).
- **Identification (read from pipeline/live/identify_engine.py):** deployment_model() = deploy_all5_v5 (engine v5;
  ENGINE_VERSION 4 in engine.py is the extraction's version, v5 extracts as v4); EXTRACT_MODE_V5 = "staged" with
  EXTRACT_WORKERS_STAGED = 4; rig_device() = mps for an engine v5 manifest.
- **Quiet:** 09:53:58 load 2.06 1.85 1.94, 65 % free; no Python, LaTeX or ffmpeg process (only VS Code helpers).
- **Pre-flight without a baseline** (`python3 -m pipeline.live preflight`, 09:54:06): ALL ok, rc 0 (H0_preflight.txt).
- **Boards at 09:51 and 09:54:** RX1 68:09:47:4c:ef:b4 on /dev/cu.usbserial-3 and RX3 20:50:0d:30:5f:80 on
  /dev/cu.usbserial-0001 (receivers, csi_recv). RX2 20:50:0d:1a:28:74 not enumerated on USB (two CP2102 bridges only).
  The TX is on power only, not on USB (Uzayr, 09:54: "TX doesnt need to be connected, it is on power").
- **LaTeX holds:** none (Uzayr, 09:54: "no latex holds"); both Editors told.
