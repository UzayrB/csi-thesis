"""Ground-truth anchor logging, in the same process as the CSI capture.

This is the piece that turns CSI into supervised data. The operator presses
SPACE as a participant crosses a taped line, or as they settle on a grid
cell, and those presses are what tie wall-clock time to floor position.

WHY IT LIVES IN THE CAPTURE PROCESS
-----------------------------------
The anchor log and the CSI stream must share one clock. Running them as two
processes reintroduces exactly the skew the labels are meant to remove: a
50 ms clock offset is 7 cm of position error at walking pace, silently
applied to every window. So this plugs into ``capture_logger``'s existing
consumer list, is dispatched from the same loop, and stamps every press with
the same :func:`time.monotonic` the CSI records use.

The keyboard is read on its own thread and pushes onto a queue, exactly as
the serial readers do. A slow or missed keypress can therefore never stall a
reader thread, which is the property that keeps the capture honest while the
operator is busy.

TWO MODES
---------
* **Mode A, static sweep.** The participant stands still at each of the 25
  cell centres in a shuffled order. Position is constant and known exactly.
* **Mode B, continuous walking.** The participant walks a path; the operator
  marks six anchors per pass, and position between anchors is interpolated.

Mode B runs in two halves with the sweep between them by default. Repeating
walks after a gap is what tests temporal consistency: twenty passes back to
back give the walking data no temporal spread within a session, so a model
can exploit short-term channel stability rather than learning the gait.

REACTION TIME
-------------
Every press carries the operator's reaction time. It is measured by
``pipeline.io.rt_calibration`` and subtracted from every anchor before
interpolation. Mode B refuses to start without it: an assumed bias would
shift every interpolated position in the same direction, which is a
systematic error that no amount of data averages away.

Run it with ``python -m pipeline.io.ground_truth``.
"""

from __future__ import annotations

import argparse
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass, field
from typing import Optional, Sequence, Union

from pipeline.io.anchors import (
    CAN_COLOURS,
    N_ANCHORS,
    Cell,
    CellOrder,
    PathDef,
    SessionPlan,
    build_cell_order,
    build_facing_order,
    build_session,
    facing_cue,
)
from pipeline.io.capture_logger import NodeState
from pipeline.io.parse import CsiRecord
from pipeline.io.rt_calibration import DEFAULT_CONFIG_PATH as RT_CONFIG_PATH
from pipeline.io.rt_calibration import software_version

# --------------------------------------------------------------------------
# Timing constants
# --------------------------------------------------------------------------

#: Seconds recorded at each cell in the static sweep, once the participant is
#: settled and the operator has pressed. Overridable per session with
#: ``--cell-seconds``.
#:
#: Note the fixed discards below are overhead on every cell, so shortening the
#: recording costs proportionally more than it looks: at 20 s the discards are
#: 15 % of each cell, at 10 s they are 30 %. Halving the wall time from 20 s to
#: 10 s therefore cuts usable data by 59 %, not 50 %.
MODE_A_RECORD_S: float = 10.0

#: Discarded from the start of each cell recording: the participant is still
#: settling, and residual motion would be labelled as stillness.
DISCARD_HEAD_S: float = 2.0

#: Discarded from the end: people anticipate the move to the next cell and
#: begin shifting weight before they are told to.
DISCARD_TAIL_S: float = 1.0

#: What remains of each cell recording after both discards, at the default
#: recording length.
USABLE_A_S: float = MODE_A_RECORD_S - DISCARD_HEAD_S - DISCARD_TAIL_S


def usable_seconds(record_s: float = MODE_A_RECORD_S) -> float:
    """Return the usable span for a given cell recording length."""
    return record_s - DISCARD_HEAD_S - DISCARD_TAIL_S

#: Above this implied speed between consecutive anchors, a press was missed:
#: the participant appears to have covered the gap impossibly fast because
#: two anchors were collapsed into one.
MAX_SPEED_MPS: float = 4.0

#: Below this, a press was spurious: two marks too close together in time.
MIN_SPEED_MPS: float = 0.3

#: Keys. The same keys mean the same thing in both modes, deliberately: an
#: operator running a live session with a participant waiting should never
#: have to remember which mode they are in.
KEY_MARK: str = " "
KEY_REDO: str = "x"
KEY_ABORT: str = "q"

#: How often the status line is redrawn. Fast enough for a countdown to look
#: live, slow enough not to flood a terminal.
STATUS_HZ: float = 10.0

#: ANSI erase-to-end-of-line, used so the in-place status line cannot leave
#: fragments of a longer previous line behind it.
_ERASE_LINE: str = "\033[K"


def _ansi_ok() -> bool:
    """Whether stdout is a terminal that should be sent escape sequences."""
    try:
        return bool(sys.stdout.isatty())
    except Exception:  # noqa: BLE001 - a stream without isatty is not a terminal
        return False

#: A node silent for longer than this during a session is probably dead, and
#: the operator needs to know before recording twenty more passes into it.
NODE_SILENT_WARN_S: float = 3.0

#: Reference image opened when each block begins, by step kind. The walking
#: sheet shows the twelve paths and where the six anchors fall; the layout
#: sheet labels all 25 cells and places the nodes, because the prompt names a
#: cell by id and hunting for it on a taped floor is exactly the hesitation
#: that costs time with a participant standing there. Regenerate with
#: ``python tools/make_layout_image.py`` and ``python tools/make_paths_image.py``.
REFERENCE_IMAGES: dict[str, str] = {"walk": "Paths.png", "grid": "Layout.png"}

#: Repo root, where the reference images live.
REPO_ROOT: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

#: Where the VS Code ``code`` CLI lives when it is not on PATH. The app is
#: commonly installed to the home directory on macOS as well as to
#: /Applications, and the CLI is only on PATH if the user ran "Install 'code'
#: command in PATH" from the palette, which most people never do.
VSCODE_CLI_CANDIDATES: tuple[str, ...] = (
    "/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code",
    os.path.expanduser("~/Visual Studio Code.app/Contents/Resources/app/bin/code"),
    os.path.expanduser("~/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code"),
    "/usr/share/code/bin/code",
)


def find_vscode() -> Optional[str]:
    """Return a usable ``code`` CLI, or ``None`` if VS Code cannot be found.

    Returns:
        Path to the CLI.

    Constraints:
        PATH first, then the usual install locations. Checked at call time
        rather than import time so that installing VS Code mid-project does
        not require restarting anything.
    """
    found = shutil.which("code")
    if found:
        return found
    for candidate in VSCODE_CLI_CANDIDATES:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


def reference_open_command(path: str, code_cli: Optional[str] = None) -> list[str]:
    """Return the argv that opens ``path``, preferring VS Code.

    Args:
        path: The image to open.
        code_cli: Path to the ``code`` CLI, or ``None`` to fall back to the
            platform's default handler.

    Returns:
        The command to run.

    Constraints:
        ``--reuse-window`` puts the sheet in a tab of the window already
        open rather than spawning a second one, which is the difference
        between a reference the operator can glance at and a window that
        steals the session's terminal.
    """
    if code_cli:
        return [code_cli, "--reuse-window", path]
    opener = {"darwin": "open", "win32": "start"}.get(sys.platform, "xdg-open")
    return [opener, path]


def open_reference_image(kind: str, root: str = REPO_ROOT) -> Optional[str]:
    """Open the reference sheet for a block, in VS Code where available.

    Args:
        kind: ``"walk"`` or ``"grid"``.
        root: Directory the images live in.

    Returns:
        The path opened, or ``None`` if there was nothing to open.

    Constraints:
        Best effort and never fatal. A missing image, a machine with no
        viewer, or a failed launch must not interrupt a session that has a
        participant standing in the room: the images are a convenience, and
        the status line already carries everything needed to run the session
        without them. Launched detached so it cannot block the dispatch loop.
    """
    name = REFERENCE_IMAGES.get(kind)
    if not name:
        return None
    path = os.path.join(root, name)
    if not os.path.exists(path):
        return None
    try:
        subprocess.Popen(
            reference_open_command(path, find_vscode()),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception:  # noqa: BLE001 - a viewer that will not start is not a session failure
        return None
    return path


def open_reference_images(first_kind: str, root: str = REPO_ROOT) -> list[str]:
    """Open both reference sheets up front, before capture starts.

    Args:
        first_kind: ``"walk"`` or ``"grid"``, whichever block runs first.
        root: Directory the images live in.

    Returns:
        The paths opened, in the order they were opened.

    Constraints:
        Opening a file in the editor moves keyboard focus out of the
        integrated terminal, so doing it at a block boundary would send the
        next SPACE into a text buffer instead of marking an anchor. Both
        sheets are therefore opened once, here, BEFORE the capture loop and
        before the operator clicks back into the terminal to start. Block
        changes then only name the tab to look at.

        The first block's sheet is opened last so it is the tab left in
        front.
    """
    order = ["grid", "walk"] if first_kind == "walk" else ["walk", "grid"]
    opened: list[str] = []
    for i, kind in enumerate(order):
        path = open_reference_image(kind, root)
        if path:
            opened.append(path)
            if i + 1 < len(order):
                # Let the editor settle so tab order is what we asked for.
                time.sleep(0.4)
    return opened

#: Participant identifiers must match this. Codes only, never names: the
#: dataset and its sidecars are the permanent record.
PARTICIPANT_CODE_RE = re.compile(r"^[A-Za-z0-9_-]{1,8}$")

#: Bounds within which a node may sit, in metres. Wider than the 0-5 m grid
#: because receivers stand at or just outside its edges, but tight enough to
#: catch a coordinate typed in centimetres or with the axes swapped.
NODE_MIN_M: float = -2.0
NODE_MAX_M: float = 7.0

#: Twice the area of the triangle formed by the three receivers, below which
#: they are treated as collinear. Three receivers on a line cannot separate a
#: position from its mirror image across that line, so the geometry carries a
#: front/back ambiguity no model can resolve. 1.0 corresponds to a triangle of
#: area 0.5 m^2 in a 25 m^2 room, which is close enough to a line to matter.
COLLINEAR_AREA_THRESHOLD: float = 1.0


# --------------------------------------------------------------------------
# Reaction-time bias
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class RtBias:
    """The measured operator reaction time.

    Attributes:
        bias_s: Mean signed latency, subtracted from every anchor timestamp.
        sd_s: Residual spread, the per-anchor uncertainty to report.
        source: Path the calibration was read from.
        measured_at: Timestamp string from the calibration run.
    """

    bias_s: float
    sd_s: float
    source: str
    measured_at: str


def load_rt_bias(path: str = RT_CONFIG_PATH) -> RtBias:
    """Load the operator's measured reaction-time bias.

    Args:
        path: Path to the calibration written by
            ``pipeline.io.rt_calibration``.

    Returns:
        The :class:`RtBias`.

    Raises:
        FileNotFoundError: If the calibration is missing, with instructions
            for producing one.
        ValueError: If it is present but malformed.

    Constraints:
        Never falls back to a default. The bias is subtracted from every
        anchor, so a guessed value would shift every interpolated position
        in the dataset in one direction: a systematic error that does not
        average out and cannot be detected after the fact.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"No reaction-time calibration at {path}.\n"
            f"Run:  python -m pipeline.io.rt_calibration\n"
            f"The bias must be measured, never assumed: it is subtracted from every "
            f"anchor, so guessing it shifts every position label the same way."
        )
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)
    try:
        return RtBias(
            bias_s=float(doc["bias_s"]),
            sd_s=float(doc["sd_s"]),
            source=path,
            measured_at=str(doc.get("timestamp", "unknown")),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"{path} is not a valid calibration: {exc}") from exc


# --------------------------------------------------------------------------
# Keyboard capture
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class KeyEvent:
    """One keypress, stamped on the same clocks as the CSI records.

    Attributes:
        key: The character pressed, lower-cased.
        t_mono: Monotonic time, used for every interval and interpolation.
        t_host: Wall-clock time, for correlating with the capture files.
    """

    key: str
    t_mono: float
    t_host: float


class KeyReader(threading.Thread):
    """Read single keypresses without blocking anything else.

    The terminal is put into cbreak mode so keys arrive without a newline,
    and ``select`` is used so the thread wakes regularly enough to notice a
    stop request. Presses are timestamped the instant they are read, before
    any queueing or rendering, so display work cannot inflate a latency.
    """

    def __init__(self, out_queue: "queue.Queue[KeyEvent]", stop_event: threading.Event) -> None:
        """Create the reader.

        Args:
            out_queue: Queue that receives :class:`KeyEvent` objects.
            stop_event: Set to ask the thread to finish.
        """
        super().__init__(name="key-reader", daemon=True)
        self.queue = out_queue
        self.stop_event = stop_event
        self.enabled = sys.stdin.isatty()
        self._fd: Optional[int] = None
        self._saved = None

    def __enter__(self) -> "KeyReader":
        """Put the terminal into cbreak mode and start reading."""
        if self.enabled:
            import termios
            import tty

            self._fd = sys.stdin.fileno()
            self._saved = termios.tcgetattr(self._fd)
            tty.setcbreak(self._fd)
            self.start()
        return self

    def __exit__(self, *exc: object) -> None:
        """Stop reading and always restore the terminal."""
        self.stop_event.set()
        self.restore()

    def restore(self) -> None:
        """Restore the terminal mode, tolerating an already-restored state."""
        if self._fd is not None and self._saved is not None:
            try:
                import termios

                termios.tcsetattr(self._fd, termios.TCSADRAIN, self._saved)
            except Exception:  # noqa: BLE001 - never let cleanup mask a real error
                pass
            self._saved = None

    def run(self) -> None:
        """Push keypresses onto the queue until asked to stop.

        Constraints:
            Never blocks indefinitely and never raises. A key that arrives
            while a consumer is busy simply waits in the queue; nothing here
            can stall a serial reader.
        """
        import select

        while not self.stop_event.is_set():
            try:
                ready, _, _ = select.select([sys.stdin], [], [], 0.05)
                if not ready:
                    continue
                ch = sys.stdin.read(1)
                if not ch:
                    continue
                self.queue.put_nowait(KeyEvent(ch.lower(), time.monotonic(), time.time()))
            except Exception:  # noqa: BLE001 - a bad read must not kill the session
                time.sleep(0.05)


# --------------------------------------------------------------------------
# Records
# --------------------------------------------------------------------------


@dataclass
class PassRecord:
    """One walking pass, as written to the sidecar.

    Attributes:
        pass_id: Index of this pass within the session, from 1.
        participant_code: Participant identifier. A code, never a name.
        session_id: Session identifier.
        room: Room identifier.
        path_name: Which path was walked, e.g. ``"C_rev"``.
        direction: Compass code for the direction of travel.
        t_start: Monotonic time the pass opened.
        t_end: Monotonic time the pass closed.
        anchor_times: Raw press times, uncorrected for reaction time. The
            correction is applied at labelling time so the raw record stays
            auditable and a re-calibration can be applied retrospectively.
        anchor_coords: The ``(x, y)`` metre coordinates crossed.
        flagged: Whether validation raised a concern.
        flags: Human-readable reasons, empty if the pass was clean.
        notes: Operator notes.
    """

    pass_id: int
    participant_code: str
    session_id: str
    room: str
    path_name: str
    direction: str
    t_start: float
    t_end: float
    anchor_times: list[float]
    anchor_coords: list[list[float]]
    flagged: bool
    flags: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class CellRecord:
    """One static-sweep cell, as written to the sidecar.

    Attributes:
        cell_index: Order within the sweep, from 1.
        participant_code: Participant identifier. A code, never a name.
        session_id: Session identifier.
        room: Room identifier.
        cell_id: Cell identifier, e.g. ``"c3r2"``.
        cell_centre_xy: The cell centre in metres, which is the position for
            the whole usable span.
        facing: Compass facing the participant was asked to hold.
        facing_cup: The cup colour that facing corresponds to, as the
            operator said it aloud.
        t_press: Monotonic time the operator confirmed the participant was
            settled.
        t_start: Start of the usable span, ``t_press + discard_head_s``.
        t_end: End of the usable span.
        discard_head_s: Seconds discarded at the start, for settling.
        discard_tail_s: Seconds discarded at the end, for anticipation.
        flagged: Whether anything about this cell needs review.
        flags: Human-readable reasons.
        notes: Operator notes.
    """

    cell_index: int
    participant_code: str
    session_id: str
    room: str
    cell_id: str
    cell_centre_xy: list[float]
    facing: str
    facing_cup: str
    t_press: float
    t_start: float
    t_end: float
    discard_head_s: float
    discard_tail_s: float
    flagged: bool
    flags: list[str] = field(default_factory=list)
    notes: str = ""


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------


def validate_pass(
    anchor_times: Sequence[float],
    anchor_coords: Sequence[tuple[float, float]],
) -> tuple[bool, list[str]]:
    """Check a completed pass for missed or spurious presses.

    Args:
        anchor_times: Press times in order.
        anchor_coords: The anchor coordinates in metres, same length.

    Returns:
        A tuple of (whether the pass is flagged, the reasons).

    Constraints:
        Run immediately after a pass closes, so the operator can repeat it
        while the participant is still standing there. A flagged pass is
        still written, never silently dropped: whether to keep it is a
        decision for analysis time, with the reason recorded.
    """
    flags: list[str] = []

    if len(anchor_times) != N_ANCHORS:
        flags.append(f"closed with {len(anchor_times)} anchors, expected {N_ANCHORS}")
        return True, flags

    for i in range(len(anchor_times) - 1):
        dt = anchor_times[i + 1] - anchor_times[i]
        ax, ay = anchor_coords[i]
        bx, by = anchor_coords[i + 1]
        dist = ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5
        if dt <= 0:
            flags.append(f"anchors {i + 1}->{i + 2} out of order (dt={dt:.3f}s)")
            continue
        speed = dist / dt
        if speed > MAX_SPEED_MPS:
            flags.append(
                f"anchors {i + 1}->{i + 2}: {speed:.1f} m/s implies a MISSED press"
            )
        elif speed < MIN_SPEED_MPS:
            flags.append(
                f"anchors {i + 1}->{i + 2}: {speed:.2f} m/s implies a SPURIOUS press"
            )

    return bool(flags), flags


# --------------------------------------------------------------------------
# Interpolation
# --------------------------------------------------------------------------


def interpolate_position(
    t: float,
    anchor_times: Sequence[float],
    anchor_coords: Sequence[tuple[float, float]],
    bias_s: float,
) -> Optional[tuple[float, float]]:
    """Interpolate position at a time within one pass.

    Args:
        t: Monotonic time to label, normally a window midpoint.
        anchor_times: Raw press times, uncorrected.
        anchor_coords: Anchor coordinates in metres.
        bias_s: Measured operator reaction time, subtracted from every
            anchor before anything else happens.

    Returns:
        The interpolated ``(x, y)``, or ``None`` if ``t`` falls outside the
        anchored span.

    Constraints:
        * The bias is subtracted from EVERY anchor before interpolation.
        * NEVER extrapolates. Before the first anchor the participant is
          still entering the grid and after the last they are leaving, so a
          position there would be invented. Those windows are excluded from
          tracking training rather than guessed at.
    """
    if len(anchor_times) < 2 or len(anchor_times) != len(anchor_coords):
        return None

    times = [ta - bias_s for ta in anchor_times]
    if t < times[0] or t > times[-1]:
        return None

    for i in range(len(times) - 1):
        t0, t1 = times[i], times[i + 1]
        if t0 <= t <= t1:
            if t1 == t0:
                return tuple(anchor_coords[i])  # type: ignore[return-value]
            f = (t - t0) / (t1 - t0)
            x0, y0 = anchor_coords[i]
            x1, y1 = anchor_coords[i + 1]
            return (x0 + f * (x1 - x0), y0 + f * (y1 - y0))
    return None


def label_time(
    t: float,
    passes: Sequence[PassRecord],
    bias_s: float,
) -> Optional[tuple[float, float]]:
    """Label one time from a whole session's passes.

    Args:
        t: Monotonic time to label.
        passes: Every pass recorded in the session.
        bias_s: Measured operator reaction time.

    Returns:
        The interpolated ``(x, y)``, or ``None``.

    Constraints:
        Returns ``None`` for times between passes. The participant is
        walking back to the start then, off any defined path, so those
        windows carry no usable position and must be excluded rather than
        attributed to the nearest pass.
    """
    for p in passes:
        coords = [(c[0], c[1]) for c in p.anchor_coords]
        pos = interpolate_position(t, p.anchor_times, coords, bias_s)
        if pos is not None:
            return pos
    return None


def label_time_static(t: float, cells: Sequence[CellRecord]) -> Optional[tuple[float, float]]:
    """Label one time from a static sweep.

    Args:
        t: Monotonic time to label.
        cells: Every cell recorded in the sweep.

    Returns:
        The cell centre if ``t`` falls in a usable span, else ``None``.

    Constraints:
        Only the usable span counts, so the settling and anticipation
        windows at each end are excluded. No reaction-time correction is
        applied: the press marks the start of a recording interval rather
        than a moving object crossing a line, and the discard head already
        absorbs any operator latency many times over.
    """
    for c in cells:
        if c.t_start <= t <= c.t_end:
            return (c.cell_centre_xy[0], c.cell_centre_xy[1])
    return None


# --------------------------------------------------------------------------
# Session layout on disk
# --------------------------------------------------------------------------


def parse_positions(spec: str) -> dict[str, tuple[float, float]]:
    """Parse a node-position specification.

    Args:
        spec: Whitespace-separated ``NAME=x,y`` entries in metres, e.g.
            ``"RX1=2.5,5.5 RX2=-0.5,2.5 RX3=5.5,2.5"``. Commas separate the
            two coordinates; whitespace separates the nodes.

    Returns:
        Mapping of node id to ``(x, y)`` in metres.

    Raises:
        ValueError: If an entry is malformed, a name repeats, a coordinate
            is not a number, or a position lies outside
            :data:`NODE_MIN_M` to :data:`NODE_MAX_M`. Bounds catch the two
            common slips: coordinates entered in centimetres, and x and y
            transposed.
    """
    out: dict[str, tuple[float, float]] = {}
    for chunk in spec.split():
        if "=" not in chunk:
            raise ValueError(f"position entry {chunk!r} is not NAME=x,y")
        name, coords = chunk.split("=", 1)
        name = name.strip()
        if not name:
            raise ValueError(f"position entry {chunk!r} has an empty name")
        if name in out:
            raise ValueError(f"position for {name!r} given twice")
        parts = coords.split(",")
        if len(parts) != 2:
            raise ValueError(f"position for {name!r} must be x,y, got {coords!r}")
        try:
            x, y = float(parts[0]), float(parts[1])
        except ValueError as exc:
            raise ValueError(f"position for {name!r} is not numeric: {coords!r}") from exc
        for axis, v in (("x", x), ("y", y)):
            if not (NODE_MIN_M <= v <= NODE_MAX_M):
                raise ValueError(
                    f"{name} {axis}={v} is outside {NODE_MIN_M} to {NODE_MAX_M} m. "
                    f"Coordinates are in metres in the grid frame, with (0,0) at the "
                    f"bottom-left corner of the taped area."
                )
        out[name] = (x, y)
    if not out:
        raise ValueError("no positions given")
    return out


def check_geometry(rx_positions: dict[str, tuple[float, float]]) -> list[str]:
    """Report geometric problems with a receiver layout.

    Args:
        rx_positions: Node id to ``(x, y)`` in metres.

    Returns:
        Human-readable warnings; empty if the layout looks sound.

    Constraints:
        Warnings, not errors. A degenerate layout is sometimes deliberate,
        and refusing to record would be worse than recording with the
        problem written down. But the operator is told at start-up, because
        both faults below are invisible in the data and only surface as
        unexplained position error months later.
    """
    warnings: list[str] = []
    names = sorted(rx_positions)

    seen: dict[tuple[float, float], str] = {}
    for n in names:
        p = rx_positions[n]
        if p in seen:
            warnings.append(
                f"{seen[p]} and {n} are at the same point {p}. Co-located receivers "
                f"give near-identical views of one path and carry no position "
                f"information beyond a single receiver."
            )
        seen[p] = n

    if len(names) == 3:
        (x1, y1), (x2, y2), (x3, y3) = (rx_positions[n] for n in names)
        area2 = abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
        if area2 < COLLINEAR_AREA_THRESHOLD:
            warnings.append(
                f"{', '.join(names)} are nearly collinear (triangle area "
                f"{area2 / 2:.2f} m^2). Positions mirrored across that line are "
                f"indistinguishable, so the layout carries a front/back ambiguity "
                f"no model can resolve."
            )
    return warnings


def validate_participant_code(code: str) -> str:
    """Check a participant code and return it.

    Args:
        code: The proposed identifier.

    Returns:
        The code unchanged.

    Raises:
        ValueError: If it does not look like a code. Names must never reach
            the dataset: the sidecars are a permanent record and are
            committed, shared and archived alongside the captures.
    """
    if not PARTICIPANT_CODE_RE.match(code):
        raise ValueError(
            f"participant code {code!r} must be 1-8 characters of letters, digits, "
            f"hyphen or underscore, e.g. P01. Never use a name."
        )
    return code


def session_paths(
    root: str,
    room: str,
    session_id: str,
    participant_code: str,
    mode: str,
    test: bool = False,
    demo: bool = False,
) -> tuple[str, str]:
    """Build the directory and filename stem for one capture.

    Args:
        root: Data root, normally ``data``.
        room: Room identifier, e.g. ``A``.
        session_id: Session number or name, e.g. ``01``.
        participant_code: Participant code.
        mode: ``"grid"`` for the static sweep, ``"walk"`` for the passes,
            ``"free"`` for the demonstration free-walk.
        test: Whether this is a held-out test session.
        demo: Whether this is the demonstration recording. Adds the
            ``DEMO`` infix, which every split builder rejects by name.

    Returns:
        A tuple of (directory, filename stem). The stem carries a ``TEST``
        infix when ``test`` is set.

    Constraints:
        The infix is applied at the moment of capture and files are never
        renamed afterwards. A test session decided retrospectively is not a
        test session: the split must be fixed before anyone has seen the
        data, which is the same reason splits happen before preprocessing.
    """
    if mode not in ("grid", "walk", "free"):
        raise ValueError(f"mode must be 'grid', 'walk' or 'free', not {mode!r}")
    if demo and test:
        raise ValueError("a recording cannot be both DEMO and TEST: the demo is excluded "
                         "from every split, the test split is one of them")
    if demo and mode != "free":
        raise ValueError("the demo recording is free-walk only; it carries no labels")
    directory = os.path.join(root, f"room_{room}", f"session_{session_id}")
    infix = "DEMO_" if demo else ("TEST_" if test else "")
    stem = f"participant_{participant_code}_{infix}{mode}"
    return directory, stem


# --------------------------------------------------------------------------
# Session configuration and sidecar
# --------------------------------------------------------------------------


@dataclass
class SessionConfig:
    """Everything about a session that is not derivable from the data.

    Attributes:
        participant_code: Participant identifier. A code, never a name.
        room: Room identifier.
        session_id: Session identifier.
        test: Whether this is a held-out test session.
        clothing: Description of what the participant is wearing. Clothing
            changes the radio cross-section, so it belongs in the record.
        footwear: Footwear description, which changes gait.
        height_cm: Participant height in centimetres. Body size sets the
            scale of the reflecting surface and the stride length, so it is
            the first covariate to check an identity result against: a model
            separating tall from short is not recognising gait.
        weight_kg: Participant weight in kilograms, for the same reason.
        chair_position: Where the researcher sat. A stationary human is part
            of the static multipath and must be reproducible.
        rx_positions: Node id to ``(x, y)`` in metres in the grid frame. The
            geometry the 2D position head depends on: without it two sessions
            with different layouts are indistinguishable in the record, and
            neither can be reproduced.
        tx_position: Transmitter ``(x, y)`` in metres, or ``None``. The links
            are bistatic, so the transmitter's position shapes every one of
            them just as the receivers' do.
        baseline_path: Path to this session's empty-room baseline capture.
        notes: Free-text operator notes.
        data_root: Root directory for captures.
        demo: Whether this is the demonstration free-walk recording, which
            carries no ground truth and is excluded from every split.
        filmed: Whether a video was recorded alongside the demo, so it is
            auditable which recordings have footage. The video is filmed
            separately under its own consent, is not synchronised to the
            CSI clock, and is never a source of labels.
    """

    participant_code: str
    room: str
    session_id: str
    test: bool = False
    clothing: str = ""
    footwear: str = ""
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    chair_position: str = ""
    rx_positions: Optional[dict[str, tuple[float, float]]] = None
    tx_position: Optional[tuple[float, float]] = None
    baseline_path: str = ""
    notes: str = ""
    data_root: str = "data"
    demo: bool = False
    filmed: bool = False


def build_sidecar(
    config: SessionConfig,
    bias: RtBias,
    plan: SessionPlan,
    cell_order: CellOrder,
    node_macs: dict[str, Optional[str]],
    passes: Sequence[PassRecord],
    cells: Sequence[CellRecord],
    mode_order: str,
    started_at: float,
    record_s: float = MODE_A_RECORD_S,
    facing_seed: Optional[int] = None,
) -> dict:
    """Assemble the ``.gt.json`` document.

    Args:
        config: Session configuration.
        bias: The reaction-time calibration in force.
        plan: The shuffled walking order and its seed.
        cell_order: The shuffled cell order and its seed.
        node_macs: Node id to station MAC, so the recording is tied to
            physical boards rather than to port names.
        passes: Completed walking passes.
        cells: Completed sweep cells.
        mode_order: How the blocks were arranged.
        started_at: Wall-clock start of the session.
        record_s: Seconds recorded at each sweep cell.
        facing_seed: Seed that produced the per-cell facing order.

    Returns:
        The document, ready to serialise.

    Constraints:
        Every field here is required. A capture whose seeds, bias or node
        mapping were not recorded cannot be reproduced or audited, and the
        uncertainty attached to its labels cannot be justified.
    """
    return {
        "participant_code": config.participant_code,
        "room": config.room,
        "session_id": config.session_id,
        "test_session": config.test,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(started_at)),
        "started_at_epoch": started_at,
        "software_version": software_version(),
        "session_seed": plan.seed,
        "cell_order_seed": cell_order.seed,
        "reaction_time": {
            "bias_s": bias.bias_s,
            "sd_s": bias.sd_s,
            "source": bias.source,
            "measured_at": bias.measured_at,
            "applied": "subtracted from every anchor timestamp at labelling time",
        },
        "node_macs": node_macs,
        "path_order": [p.name for p in plan.paths],
        "cell_order": [c.cell_id for c in cell_order.cells],
        "facing_seed": facing_seed,
        "facing_cups": dict(CAN_COLOURS),
        "facings": [c.facing for c in cells],
        "mode_order": mode_order,
        "timing": {
            "mode_a_record_s": record_s,
            "discard_head_s": DISCARD_HEAD_S,
            "discard_tail_s": DISCARD_TAIL_S,
            "usable_a_s": usable_seconds(record_s),
        },
        "validation": {
            "max_speed_mps": MAX_SPEED_MPS,
            "min_speed_mps": MIN_SPEED_MPS,
        },
        "participant": {
            "clothing": config.clothing,
            "footwear": config.footwear,
            "height_cm": config.height_cm,
            "weight_kg": config.weight_kg,
        },
        "geometry": {
            "rx_positions_m": (
                {n: [p[0], p[1]] for n, p in config.rx_positions.items()}
                if config.rx_positions
                else None
            ),
            "tx_position_m": list(config.tx_position) if config.tx_position else None,
            "frame": "metres, (0,0) at the bottom-left corner of the taped grid, x=col, y=row",
            "warnings": check_geometry(config.rx_positions) if config.rx_positions else [],
        },
        "researcher_chair_position": config.chair_position,
        "baseline_capture": config.baseline_path,
        "notes": config.notes,
        "passes": [asdict(p) for p in passes],
        "cells": [asdict(c) for c in cells],
        "n_passes": len(passes),
        "n_cells": len(cells),
        "n_flagged": sum(1 for p in passes if p.flagged) + sum(1 for c in cells if c.flagged),
    }


#: Written into every demo sidecar, verbatim, so the exclusion is stated in
#: the file itself and not only in the code that enforces it.
DEMO_REASON: str = "demonstration only, excluded from all training and evaluation"


def write_demo_sidecar(
    config: SessionConfig,
    node_macs: dict[str, Optional[str]],
    out_dir: str,
    stem: str,
    started_at: float,
    duration_s: float,
    markers: Optional[dict] = None,
    script: Optional[Sequence[str]] = None,
    ended_by: str = "ceiling",
) -> str:
    """Write the sidecar for a demonstration free-walk recording.

    Args:
        config: Session configuration; ``demo`` must be set.
        node_macs: Node id to station MAC.
        out_dir: Directory the sidecar is written to.
        stem: Filename stem shared with the CSI files.
        started_at: Wall-clock start.
        duration_s: Seconds captured.
        markers: The operator's two spacebar presses, in and out, on the
            CSI clocks, from :meth:`DemoClock.markers`. For aligning a
            video; never a position label.
        script: The steps the participant was asked to perform.
        ended_by: ``"spacebar"``, ``"ceiling"`` or ``"no spacebar press"``.

    Returns:
        Path to the sidecar.

    Constraints:
        There are no position labels of any kind, and the document says so:
        ``mode`` is ``"demo"``, ``position_labels`` is null, ``passes`` and
        ``cells`` are empty, and ``reason`` carries :data:`DEMO_REASON`. The
        rig geometry is recorded because a demonstration overlay needs to
        draw the rig; it is not a label.
    """
    if not config.demo:
        raise ValueError("write_demo_sidecar is for demo recordings only")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{stem}.gt.json")
    doc = {
        "mode": "demo",
        "reason": DEMO_REASON,
        "position_labels": None,
        "markers": markers,
        "markers_note": (
            "operator spacebar presses marking when the participant stepped in and out, on the "
            "same clocks as the CSI records; for aligning a video, never a position label"
        ),
        "script": list(script) if script else None,
        "ended_by": ended_by,
        "filmed": bool(config.filmed),
        "video_note": (
            "any video was filmed separately under its own consent, is not synchronised "
            "to the CSI clock, and is never a source of position labels"
        ),
        "participant_code": config.participant_code,
        "room": config.room,
        "session_id": config.session_id,
        "test_session": False,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(started_at)),
        "started_at_epoch": started_at,
        "duration_s": duration_s,
        "software_version": software_version(),
        "node_macs": node_macs,
        "geometry": {
            "rx_positions_m": (
                {n: [p[0], p[1]] for n, p in config.rx_positions.items()} if config.rx_positions else None
            ),
            "tx_position_m": list(config.tx_position) if config.tx_position else None,
            "frame": "metres, (0,0) at the bottom-left corner of the taped grid, x=col, y=row",
        },
        "participant": {
            "clothing": config.clothing,
            "footwear": config.footwear,
            "height_cm": config.height_cm,
            "weight_kg": config.weight_kg,
        },
        "researcher_chair_position": config.chair_position,
        "baseline_capture": config.baseline_path,
        "notes": config.notes,
        "passes": [],
        "cells": [],
        "n_passes": 0,
        "n_cells": 0,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, sort_keys=True, default=str)
    return path


# --------------------------------------------------------------------------
# Session steps
# --------------------------------------------------------------------------


@dataclass
class PassStep:
    """One walking pass to be recorded."""

    path: PathDef
    pass_id: int


@dataclass
class CellStep:
    """One sweep cell to be recorded.

    Attributes:
        cell: Which cell.
        cell_index: Order within the sweep, from 1.
        facing: Which cup the participant is asked to face, N/E/S/W. A
            person is not radially symmetric, so orientation changes the
            reflection independently of position; randomising it stops
            facing acting as a hidden position cue.
    """

    cell: Cell
    cell_index: int
    facing: str = "N"


Step = Union[PassStep, CellStep]


def build_steps(
    plan: SessionPlan,
    cell_order: CellOrder,
    split: bool = True,
    facings: Optional[Sequence[str]] = None,
) -> tuple[list[Step], str]:
    """Order the session's passes and cells.

    Args:
        plan: The shuffled walking order.
        cell_order: The shuffled cell order.
        split: Whether to run the walking passes in two halves with the
            sweep between them.
        facings: One facing per cell, in visit order. Defaults to all north,
            which is only appropriate for tests.

    Returns:
        A tuple of (the ordered steps, a description of the arrangement).

    Constraints:
        Splitting is the default. Twenty passes run back to back give the
        walking data no temporal spread within a session, so short-term
        channel stability alone can carry a model. Separating the repeats
        by the length of the sweep, roughly ten minutes, costs no extra
        session time and tests temporal consistency instead.
    """
    passes = [PassStep(path=p, pass_id=i + 1) for i, p in enumerate(plan.paths)]
    f = list(facings) if facings is not None else ["N"] * len(cell_order.cells)
    cells = [
        CellStep(cell=c, cell_index=i + 1, facing=f[i])
        for i, c in enumerate(cell_order.cells)
    ]

    if not split:
        return [*passes, *cells], "walk_then_grid"

    half = len(passes) // 2
    return [*passes[:half], *cells, *passes[half:]], "walk_half, grid, walk_half"


# --------------------------------------------------------------------------
# The live session
# --------------------------------------------------------------------------


def _dist_to_segment(p: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
    """Distance from point ``p`` to the segment ``a``-``b``."""
    ax_, ay_ = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax_, by - ay_
    if dx == 0 and dy == 0:
        return ((px - ax_) ** 2 + (py - ay_) ** 2) ** 0.5
    t = max(0.0, min(1.0, ((px - ax_) * dx + (py - ay_) * dy) / (dx * dx + dy * dy)))
    return ((px - (ax_ + t * dx)) ** 2 + (py - (ay_ + t * dy)) ** 2) ** 0.5


#: A node closer than this to a path's run-in or run-out is standing on it.
POT_ON_LINE_M: float = 0.35


def nodes_on_run(path: PathDef, nodes: dict[str, tuple[float, float]]) -> tuple[list[str], list[str]]:
    """Which nodes stand on a path's run-in and run-out.

    Args:
        path: The path about to be walked.
        nodes: Node id to ``(x, y)`` in metres, the recorded rig positions.

    Returns:
        Two lists of node ids: those on the run-in (start to anchor 1) and
        those on the run-out (anchor 6 to end).

    Constraints:
        Computed from the positions the session records, not from a
        hard-coded layout, so the warning is right for whatever rig is
        actually in the room. Paths A and B run straight through the wall
        midpoints, where the nodes stand; C, D and E clear them by a metre.
    """
    run_in = (path.start_xy, path.anchors[0])
    run_out = (path.anchors[-1], path.end_xy)
    on_in = [n for n, xy in nodes.items() if _dist_to_segment(xy, *run_in) < POT_ON_LINE_M]
    on_out = [n for n, xy in nodes.items() if _dist_to_segment(xy, *run_out) < POT_ON_LINE_M]
    return on_in, on_out


class GroundTruthSession:
    """Drives a live ground-truth session as a capture consumer.

    Implements the consumer protocol used by ``capture_logger``: it receives
    every CSI record for health monitoring, is ticked from the dispatch loop
    to advance its state machine and redraw, and writes its sidecar on close.
    """

    #: This consumer draws an in-place status line, so ``run_capture`` must
    #: not tick it while it is printing its own start-up report: a bare
    #: carriage return would land in the middle of that text and mangle both.
    owns_terminal: bool = True

    def __init__(
        self,
        steps: Sequence[Step],
        config: SessionConfig,
        bias: RtBias,
        plan: SessionPlan,
        cell_order: CellOrder,
        mode_order: str,
        out_dir: str,
        stem: str,
        key_queue: "queue.Queue[KeyEvent]",
        node_states: Optional[dict[str, NodeState]] = None,
        record_s: float = MODE_A_RECORD_S,
        show_images: bool = True,
    ) -> None:
        """Create a session.

        Args:
            steps: The ordered passes and cells to record.
            config: Session configuration.
            bias: The reaction-time calibration in force.
            plan: The shuffled walking order, for the sidecar.
            cell_order: The shuffled cell order, for the sidecar.
            mode_order: Description of the block arrangement.
            out_dir: Directory the sidecar is written to.
            stem: Filename stem shared with the CSI files.
            key_queue: Queue fed by :class:`KeyReader`.
            node_states: Per-node capture state, used to report station MACs
                in the sidecar.
            record_s: Seconds recorded at each sweep cell.
            show_images: Open the reference sheet when each block begins.
        facing_seed: Seed that produced the per-cell facing order.
        """
        self.steps = list(steps)
        self.config = config
        self.bias = bias
        self.plan = plan
        self.cell_order = cell_order
        self.mode_order = mode_order
        self.facing_seed: Optional[int] = None
        self.out_dir = out_dir
        self.stem = stem
        self.keys = key_queue
        self.record_s = record_s
        # Not `node_states or {}`: the caller passes an empty dict that the
        # capture fills in later, and an empty dict is falsy, so `or` would
        # quietly substitute a different one and the sidecar would record no
        # station MACs at all.
        self.node_states = node_states if node_states is not None else {}

        self.show_images = show_images

        self.idx = 0
        self.finished = False
        self.aborted = False
        self.started_at = time.time()
        self.passes: list[PassRecord] = []
        self.cells: list[CellRecord] = []

        # Per-step state.
        self._anchor_times: list[float] = []
        self._t_press: Optional[float] = None
        self._step_open = False

        # Which block kind has been announced, so the banner fires once per
        # block rather than once per step, and which step index has had its
        # placement printed, so that fires once per step and again after a
        # redo (which moves the index backwards).
        self._announced: Optional[str] = None
        self._announced_idx: Optional[int] = None

        # The step just closed, and which list its record went into, so `x`
        # pressed before the next step is engaged redoes the one that was
        # actually just recorded rather than the one coming up. Cleared the
        # moment the operator engages the next step.
        self._redo_prev: Optional[tuple[str, int]] = None

        # Health.
        self._counts: dict[str, int] = {}
        self._last_seen: dict[str, float] = {}
        self._last_status = 0.0
        self._status_len = 0

    # -- consumer protocol -------------------------------------------------

    def handle(self, record: CsiRecord) -> None:
        """Note that a node is alive. Ground truth does not use CSI content."""
        self._counts[record.node_id] = self._counts.get(record.node_id, 0) + 1
        self._last_seen[record.node_id] = record.t_mono

    def tick(self, now: float) -> None:
        """Advance the state machine and redraw.

        Args:
            now: Current monotonic time.

        Constraints:
            Does all of its work without blocking: key handling is a
            non-blocking queue drain and rendering is a single line. The
            dispatch loop that calls this also feeds the writer, so anything
            slow here would delay persistence for every node.
        """
        if self.finished:
            return

        while True:
            try:
                ev = self.keys.get_nowait()
            except queue.Empty:
                break
            self._on_key(ev)
            if self.finished:
                return

        step = self._current()
        if step is not None:
            kind = "grid" if isinstance(step, CellStep) else "walk"
            if kind != self._announced:
                self._announce_block(kind)
            if self.idx != self._announced_idx:
                self._announce_step(step)
                self._announced_idx = self.idx

        if isinstance(step, CellStep) and self._step_open and self._t_press is not None:
            if now >= self._t_press + self.record_s:
                self._close_cell(step)

        if now - self._last_status >= 1.0 / STATUS_HZ:
            self._last_status = now
            self._render(now)

    def close(self) -> None:
        """Write the sidecar, then print a summary.

        Constraints:
            The sidecar is written FIRST, before anything touches the
            terminal. When the process is shutting down because its
            terminal went away, every write to stdout can raise, and a
            summary line that raised before the file was written would lose
            the session's only copy of the anchor times. The file is the
            deliverable; the summary is a courtesy, and it is allowed to
            fail.
        """
        path = self.write_sidecar()
        try:
            self._clear_status()
            flagged = sum(1 for p in self.passes if p.flagged) + sum(1 for c in self.cells if c.flagged)
            print()
            print("=" * 72)
            print(f"SESSION {'ABORTED' if self.aborted else 'COMPLETE'}")
            print(f"  passes recorded : {len(self.passes)} of {sum(1 for s in self.steps if isinstance(s, PassStep))}")
            print(f"  cells recorded  : {len(self.cells)} of {sum(1 for s in self.steps if isinstance(s, CellStep))}")
            print(f"  flagged         : {flagged}")
            print(f"  ground truth    : {path}")
            print("=" * 72)
        except OSError:
            # stdout is gone (terminal closed). The sidecar is already on
            # disk, which is the only thing that matters now.
            pass

    # -- state machine -----------------------------------------------------

    def _current(self) -> Optional[Step]:
        """Return the step being recorded, or ``None`` when the session ends."""
        return self.steps[self.idx] if self.idx < len(self.steps) else None

    def _announce_block(self, kind: str) -> None:
        """Mark the change of mode loudly, and open that block's reference sheet.

        Args:
            kind: ``"walk"`` or ``"grid"``.

        Constraints:
            Fires once per block, not once per step. The two modes ask
            completely different things of the operator and of the
            participant, and the only thing distinguishing them mid-session
            was the first word of a status line that redraws ten times a
            second. Switching from marking six crossings per pass to timing
            25 static dwells is worth interrupting the scroll for.
        """
        n_pass = sum(1 for s in self.steps if isinstance(s, PassStep))
        n_cell = sum(1 for s in self.steps if isinstance(s, CellStep))
        remaining = sum(
            1
            for s in self.steps[self.idx :]
            if isinstance(s, CellStep if kind == "grid" else PassStep)
        )

        if kind == "grid":
            head = f"STATIC MODE  -  sweep, {remaining} of {n_cell} cells to go"
            body = [
                "Walk them to the cell named, wait until they are settled and still,",
                f"then SPACE. {self.record_s:.0f}s records itself and it advances on its own.",
            ]
        else:
            head = f"WALKING MODE  -  {remaining} of {n_pass} passes to go"
            body = [
                "There is NO start press. You call \"go\", they walk it on their own,",
                "from 1.5 m OUTSIDE the tape, straight through, and out the far side.",
                f"Your only job is {N_ANCHORS} presses: SPACE the instant their TORSO -- not the",
                "leading foot -- crosses each taped line. The pass closes itself on the 6th.",
            ]

        self._log("")
        self._log("=" * 72)
        self._log(f"  >>  {head}")
        for line in body:
            self._log(f"      {line}")
        if self.show_images:
            sheet = REFERENCE_IMAGES.get(kind)
            if sheet:
                self._log(f"      reference: the {sheet} tab")
        self._log("=" * 72)
        self._announced = kind

    def _announce_step(self, step: Step) -> None:
        """Print where to put the participant before a pass, once per pass.

        Args:
            step: The step now current.

        Constraints:
            Only walking needs this. The path's start and end are OUTSIDE
            the taped grid on purpose, so the walker is already at a steady
            pace before anchor 1 and does not decelerate before anchor 6 --
            starting or stopping on the grid is the most common way to ruin
            a pass, and the coordinates are the only unambiguous way to say
            where "outside" is for this particular path.

            It goes in the scrolling log rather than the status line because
            the status line is redrawn in place with a carriage return: once
            it is long enough to wrap, the redraw only returns to the start
            of the last screen row and the display comes apart.
        """
        if not isinstance(step, PassStep):
            return
        sx, sy = step.path.start_xy
        ex, ey = step.path.end_xy
        nodes: dict[str, tuple[float, float]] = dict(self.config.rx_positions or {})
        if self.config.tx_position is not None:
            nodes["TX"] = self.config.tx_position
        on_in, on_out = nodes_on_run(step.path, nodes)

        self._log("")
        self._log(f"pass {step.pass_id}  {step.path.name}  {step.path.cue}")
        self._log(f"    START 1.5 m outside the tape at ({sx:g}, {sy:g}) m, facing {step.path.direction}")
        if on_in:
            self._log(f"    the {'/'.join(on_in)} pot is on this line: stand them BESIDE it, not in front of it")
        self._log(f"    walk straight through and out to ({ex:g}, {ey:g}) m, 1 m past the last line")
        if on_out:
            self._log(f"    the {'/'.join(on_out)} pot is at the far end: aim past it, do not slow before line 6")

    def _advance(self) -> None:
        """Move to the next step, finishing the session at the end."""
        self.idx += 1
        self._anchor_times = []
        self._t_press = None
        self._step_open = False
        if self.idx >= len(self.steps):
            self.finished = True

    def _on_key(self, ev: KeyEvent) -> None:
        """Apply one keypress to the current step."""
        step = self._current()
        if step is None:
            self.finished = True
            return

        if ev.key == KEY_ABORT:
            self._log("aborted by operator")
            self.aborted = True
            self.finished = True
            return

        if ev.key == KEY_REDO:
            if self._redo_prev is not None and not self._step_open and not self._anchor_times:
                self._redo_previous()
                return
            self._anchor_times = []
            self._t_press = None
            self._step_open = False
            self._log(f"redo: {self._describe(step)} restarted, partial marks discarded")
            return

        if ev.key != KEY_MARK:
            return

        if isinstance(step, PassStep):
            self._anchor_times.append(ev.t_mono)
            n = len(self._anchor_times)
            if n == 1:
                self._step_open = True
                self._redo_prev = None
            self._log(f"  anchor {n}/{N_ANCHORS} at ({step.path.anchors[n - 1][0]:g}, {step.path.anchors[n - 1][1]:g})")
            if n >= N_ANCHORS:
                self._close_pass(step)
        else:
            if not self._step_open:
                self._t_press = ev.t_mono
                self._step_open = True
                self._redo_prev = None
                self._log(f"  recording {self.record_s:.0f}s at {step.cell.cell_id} facing {CAN_COLOURS[step.facing]}")

    def _redo_previous(self) -> None:
        """Throw away the step that just closed and record it again.

        Constraints:
            This is the redo the operator actually needs. A pass closes
            itself on the sixth anchor and a cell closes itself on a timer,
            so by the time anything is visibly wrong the session has already
            moved on, and ``x`` would otherwise restart the step that has not
            started yet. Only reachable while the next step is still
            untouched, so it can never silently discard work in progress.

            The discarded record is removed from the session entirely. That
            is the difference between this and a flag: a flagged pass is kept
            with its reason for an analysis-time judgement, whereas a redo is
            the operator saying this recording is not of the thing it claims
            to be, and keeping it would put a mislabelled example in the
            dataset.
        """
        if self._redo_prev is None:
            return
        kind, idx = self._redo_prev
        records = self.passes if kind == "pass" else self.cells
        dropped = records.pop() if records else None
        self.idx = idx
        self._anchor_times = []
        self._t_press = None
        self._step_open = False
        self._redo_prev = None

        step = self._current()
        label = self._describe(step) if step is not None else f"{kind} {idx}"
        was = ", flagged" if getattr(dropped, "flagged", False) else ""
        self._log(f"redo: {label} discarded{was} and reopened; record it again")

    def _close_pass(self, step: PassStep) -> None:
        """Validate and store a completed pass, then advance."""
        coords = [(x, y) for x, y in step.path.anchors]
        flagged, flags = validate_pass(self._anchor_times, coords)
        rec = PassRecord(
            pass_id=step.pass_id,
            participant_code=self.config.participant_code,
            session_id=self.config.session_id,
            room=self.config.room,
            path_name=step.path.name,
            direction=step.path.direction,
            t_start=self._anchor_times[0],
            t_end=self._anchor_times[-1],
            anchor_times=list(self._anchor_times),
            anchor_coords=[[x, y] for x, y in coords],
            flagged=flagged,
            flags=flags,
        )
        self.passes.append(rec)

        span = rec.t_end - rec.t_start
        if flagged:
            self._log(f"PASS {step.pass_id} {step.path.name} FLAGGED ({span:.1f}s):")
            for f in flags:
                self._log(f"    ! {f}")
            self._log(f"    press '{KEY_REDO}' now to repeat this pass, or just start the next one")
        else:
            self._log(f"pass {step.pass_id} {step.path.name} ok, {span:.1f}s   ('{KEY_REDO}' to redo it)")
        self._redo_prev = ("pass", self.idx)
        self._advance()

    def _close_cell(self, step: CellStep) -> None:
        """Store a completed cell recording, then advance."""
        assert self._t_press is not None
        rec = CellRecord(
            cell_index=step.cell_index,
            participant_code=self.config.participant_code,
            session_id=self.config.session_id,
            room=self.config.room,
            cell_id=step.cell.cell_id,
            cell_centre_xy=[step.cell.centre_xy[0], step.cell.centre_xy[1]],
            facing=step.facing,
            facing_cup=CAN_COLOURS[step.facing],
            t_press=self._t_press,
            t_start=self._t_press + DISCARD_HEAD_S,
            t_end=self._t_press + self.record_s - DISCARD_TAIL_S,
            discard_head_s=DISCARD_HEAD_S,
            discard_tail_s=DISCARD_TAIL_S,
            flagged=False,
        )
        self.cells.append(rec)
        self._log(
            f"cell {step.cell_index}/25 {step.cell.cell_id} facing {CAN_COLOURS[step.facing]} done, "
            f"{usable_seconds(self.record_s):.0f}s usable   ('{KEY_REDO}' to redo it)"
        )
        self._redo_prev = ("cell", self.idx)
        self._advance()

    # -- output ------------------------------------------------------------

    def write_sidecar(self) -> str:
        """Write the ``.gt.json`` document beside the CSI files."""
        os.makedirs(self.out_dir, exist_ok=True)
        path = os.path.join(self.out_dir, f"{self.stem}.gt.json")
        doc = build_sidecar(
            config=self.config,
            bias=self.bias,
            plan=self.plan,
            cell_order=self.cell_order,
            node_macs={n: st.sta_mac for n, st in self.node_states.items()},
            passes=self.passes,
            cells=self.cells,
            mode_order=self.mode_order,
            started_at=self.started_at,
            record_s=self.record_s,
            facing_seed=self.facing_seed,
        )
        doc["aborted"] = self.aborted
        with open(path, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2, sort_keys=True, default=str)
        return path

    # -- display -----------------------------------------------------------

    def _describe(self, step: Step) -> str:
        """Return a short label for a step."""
        if isinstance(step, PassStep):
            return f"pass {step.pass_id} {step.path.name}"
        return f"cell {step.cell_index} {step.cell.cell_id}"

    def _clear_status(self) -> None:
        """Erase the in-place status line before printing anything else."""
        if self._status_len:
            if _ansi_ok():
                sys.stdout.write("\r" + _ERASE_LINE)
            else:
                sys.stdout.write("\r" + " " * self._status_len + "\r")
            sys.stdout.flush()
            self._status_len = 0

    def _log(self, text: str) -> None:
        """Print a permanent line above the status line."""
        self._clear_status()
        print(text, flush=True)

    def _health(self, now: float) -> str:
        """Return a compact capture-health indicator.

        A node that has gone quiet is called out, because discovering it
        after twenty passes means recording them all again.
        """
        if not self._last_seen:
            return "no CSI yet"
        dead = [n for n, t in self._last_seen.items() if now - t > NODE_SILENT_WARN_S]
        if dead:
            return "!! SILENT: " + ",".join(sorted(dead))
        return " ".join(f"{n}:{c}" for n, c in sorted(self._counts.items()))

    def _render(self, now: float) -> None:
        """Redraw the single-line status display."""
        step = self._current()
        if step is None:
            return

        n_pass = sum(1 for s in self.steps if isinstance(s, PassStep))
        n_cell = sum(1 for s in self.steps if isinstance(s, CellStep))

        if isinstance(step, PassStep):
            marked = len(self._anchor_times)
            nxt = min(marked + 1, N_ANCHORS)
            ax, ay = step.path.anchors[nxt - 1]
            if marked == 0:
                cue = f"| SAY GO. then SPACE on TORSO at line 1/{N_ANCHORS} ({ax:g},{ay:g})"
            else:
                cue = f"| marked {marked}/{N_ANCHORS} -> next TORSO at line {nxt}/{N_ANCHORS} ({ax:g},{ay:g})"
            body = f"WALK  pass {step.pass_id}/{n_pass}  {step.path.name}  {step.path.cue}  {cue}"
        else:
            x, y = step.cell.centre_xy
            cup = CAN_COLOURS[step.facing]
            if self._step_open and self._t_press is not None:
                left = max(0.0, self._t_press + self.record_s - now)
                body = (
                    f"GRID  cell {step.cell_index}/{n_cell}  {step.cell.cell_id} "
                    f"({x:.1f}, {y:.1f}) m  face {cup}  | RECORDING {left:4.1f}s"
                )
            else:
                body = (
                    f"GRID  cell {step.cell_index}/{n_cell}  {step.cell.cell_id} "
                    f"({x:.1f}, {y:.1f}) m  | {facing_cue(step.facing)}, then SPACE"
                )

        line = f"{body}   [{self._health(now)}]"
        # Erase to end of line rather than padding to the previous width, so
        # a shorter line cannot leave the tail of a longer one behind and
        # anything printed over the top is cleared rather than merged. Falls
        # back to padding when stdout is not a terminal, since a redirected
        # log would otherwise collect the escape sequences as literal text.
        if _ansi_ok():
            sys.stdout.write("\r" + _ERASE_LINE + line)
        else:
            sys.stdout.write("\r" + line + " " * max(0, self._status_len - len(line)))
        sys.stdout.flush()
        self._status_len = len(line)


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    p = argparse.ArgumentParser(
        prog="python -m pipeline.io.ground_truth",
        description="Record ground-truth anchors alongside a CSI capture, in one process.",
    )
    p.add_argument("--participant", required=True, help="participant CODE, never a name, e.g. P01")
    p.add_argument("--room", required=True, help="room identifier, e.g. A")
    p.add_argument("--session", required=True, help="session identifier, e.g. 01")
    p.add_argument("--test", action="store_true", help="held-out test session; adds the TEST infix at capture time")
    p.add_argument("--demo", action="store_true", help="demonstration free-walk: CSI only, NO ground truth, DEMO infix, excluded from every split. Session 03 only unless --force")
    p.add_argument("--filmed", action="store_true", help="with --demo: a video was filmed separately; recorded as a boolean for audit only")
    p.add_argument("--force", action="store_true", help="allow --demo on a session other than 03")
    p.add_argument("--demo-seconds", type=float, default=600.0, metavar="S", help="ceiling on the demo recording; it normally ends on the second spacebar press (default: 600)")
    p.add_argument("--mode", choices=("both", "walk", "grid"), default="both", help="which blocks to run (default: both)")
    p.add_argument("--cell-seconds", type=float, default=MODE_A_RECORD_S, metavar="S", help=f"seconds recorded at each sweep cell (default: {MODE_A_RECORD_S:.0f}; {DISCARD_HEAD_S:.0f}s and {DISCARD_TAIL_S:.0f}s are then discarded)")
    p.add_argument("--contiguous", action="store_true", help="run the walking passes back to back instead of split around the sweep")
    p.add_argument("--seed", type=int, default=None, help="path-order seed (default: random, recorded in the sidecar)")
    p.add_argument("--facing-seed", type=int, default=None, help="seed for the per-cell facing order (default: random, recorded in the sidecar)")
    p.add_argument("--cell-seed", type=int, default=None, help="cell-order seed (default: random, recorded in the sidecar)")
    p.add_argument("--data-root", default="data", help="data root (default: data)")
    p.add_argument("--clothing", default="", help="what the participant is wearing")
    p.add_argument("--footwear", default="", help="participant footwear")
    p.add_argument("--height-cm", type=float, default=None, metavar="CM", help="participant height in cm; required for a live capture")
    p.add_argument("--weight-kg", type=float, default=None, metavar="KG", help="participant weight in kg; required for a live capture")
    p.add_argument("--chair", default="", help="researcher chair position")
    p.add_argument("--rx-positions", default=None, metavar="SPEC", help='receiver positions in metres, e.g. "RX1=2.5,5.5 RX2=-0.5,2.5 RX3=5.5,2.5". Required for a live capture: the 2D position head depends on this geometry and it is recorded nowhere else.')
    p.add_argument("--tx-position", default=None, metavar="X,Y", help='transmitter position in metres, e.g. "2.5,-0.5"')
    p.add_argument("--baseline", default="", help="path to this session's empty-room baseline capture")
    p.add_argument("--notes", default="", help="operator notes")
    p.add_argument("--nodes", default=None, help='receiver mapping, e.g. "RX1=/dev/cu.usbserial-3,..."')
    p.add_argument("--expect-hz", type=float, default=150.0, help="achieved transmit rate, for the capture gates")
    p.add_argument("--baud", type=int, default=921600, help="receiver console baud")
    p.add_argument("--no-images", action="store_true", help="do not open the walking/sweep reference sheet when a block begins")
    p.add_argument("--dry-run", action="store_true", help="plan the session and print it without capturing")
    p.add_argument("--redo", action="store_true", help="overwrite an existing recording with the same name; without it the tool refuses to start")
    return p


def existing_recording(out_dir: str, stem: str) -> list[str]:
    """Files an earlier recording of this participant, session and mode left behind.

    The tool writes to fixed per-participant filenames, so a second run under
    the same name silently replaces the first. On 11 September 2026 that cost
    a complete session (PA2, session 03, 07:39): overwritten at 08:34 by a
    rerun that then aborted, with no copy anywhere. Starting on top of an
    existing recording is now refused unless ``--redo`` says it is meant.
    """
    if not os.path.isdir(out_dir):
        return []
    return sorted(f for f in os.listdir(out_dir) if f == f"{stem}.gt.json" or f == f"{stem}_run.json"
                  or (f.startswith(f"{stem}_RX") and f.endswith(".bin")))


def refuse_overwrite(out_dir: str, stem: str, redo: bool) -> bool:
    """Print the refusal and return True if a recording exists and ``redo`` is not set."""
    existing = existing_recording(out_dir, stem)
    if not existing or redo:
        return False
    print("=" * 72)
    print(f"REFUSING TO START: a recording named {stem} already exists in {out_dir}:")
    for f in existing:
        print(f"    {f}")
    print("  Starting would overwrite it in place and nothing could recover it.")
    print("  If this is a deliberate re-record, run the same command with --redo.")
    print("=" * 72)
    return True


#: The demo is recorded in the held-out test session only, after the sweep
#: and passes, so that it never competes with labelled time.
DEMO_SESSION: str = "03"

#: What the participant does, the same for everyone so the demos differ only
#: in who is walking. Tracking reads a cell from a person standing still for
#: a few seconds and identification reads walking, so the walk alternates
#: the two. The capture is already running before the first spacebar press,
#: so the seconds before it are the empty-room lead-in.
DEMO_SCRIPT: tuple[str, ...] = (
    "Wait outside the tape, at the bottom of the grid, until I say go.",
    "GO: step over the tape (I press space) and walk straight up column 3 to the top edge at normal pace.",
    "Turn right, walk to the top-right cell (5,5), stand still facing the camera and count five.",
    "Walk diagonally down to the bottom-left cell (1,1), stand still facing the camera, count five.",
    "Walk to the centre cell (3,3), stand still facing the camera, count five.",
    "Walk to the bottom-right cell (5,1), stand still facing the camera, count five.",
    "Walk row 3 from the right edge to the left edge at normal pace.",
    "Step out over the tape on the left (I press space) and stay out.",
)


class DemoClock:
    """Marks the participant's entry and exit from two spacebar presses.

    A consumer in the capture loop: the CSI runs from the moment the capture
    starts, the first space marks the participant stepping in, the second
    marks them stepping out and ends the recording. Both presses are
    stamped by :class:`KeyReader` on the CSI clocks. They are markers for
    aligning a video, not ground truth: no position is recorded anywhere.
    """

    owns_terminal: bool = True

    def __init__(self, keys: "queue.Queue[KeyEvent]", enabled: bool, ceiling_s: float) -> None:
        self.keys = keys
        self.enabled = enabled
        self.ceiling_s = ceiling_s
        self.start: Optional[KeyEvent] = None
        self.end: Optional[KeyEvent] = None
        self.finished = False
        self._prompted = False
        self._last_line = ""

    def handle(self, record: CsiRecord) -> None:  # noqa: D401 - protocol method
        """Records are written by the capture; nothing to do here."""

    def _say(self, line: str, newline: bool = False) -> None:
        pad = max(0, len(self._last_line) - len(line))
        sys.stdout.write("\r" + line + " " * pad + ("\n" if newline else ""))
        sys.stdout.flush()
        self._last_line = "" if newline else line

    def tick(self, now: float) -> None:
        if not self._prompted:
            self._prompted = True
            if self.enabled:
                self._say("Recording. Press SPACE when they step in; press SPACE again when they step out.", newline=True)
            else:
                self._say(f"Recording without a keyboard (stdin is not a terminal): runs for the {self.ceiling_s:.0f} s ceiling.", newline=True)
        while True:
            try:
                ev = self.keys.get_nowait()
            except queue.Empty:
                break
            if ev.key != " ":
                continue
            if self.start is None:
                self.start = ev
                self._say(f"IN   at {time.strftime('%H:%M:%S', time.localtime(ev.t_host))}  -  walking. Press SPACE when they step out.", newline=True)
            elif self.end is None:
                self.end = ev
                self.finished = True
                self._say(f"OUT  at {time.strftime('%H:%M:%S', time.localtime(ev.t_host))}  -  {ev.t_mono - self.start.t_mono:.1f} s in the grid. Stopping.", newline=True)
        if self.start is not None and self.end is None:
            self._say(f"  in the grid for {now - self.start.t_mono:6.1f} s   (SPACE = out)")

    def close(self) -> None:
        if self._last_line:
            self._say("", newline=True)

    def markers(self) -> Optional[dict]:
        if self.start is None:
            return None
        out = {"in_mono": self.start.t_mono, "in_epoch": self.start.t_host}
        if self.end is not None:
            out.update({"out_mono": self.end.t_mono, "out_epoch": self.end.t_host,
                        "in_grid_s": round(self.end.t_mono - self.start.t_mono, 3)})
        return out


def _run_demo(args: argparse.Namespace, code: str) -> int:
    """Record the demonstration free-walk: CSI only, no ground truth.

    Constraints:
        * Refuses ``--test`` on the same command, and any session other
          than :data:`DEMO_SESSION` unless ``--force`` is given.
        * Starts NO anchor logger. The only keys it reads are two spacebar
          presses, in and out, stamped as markers for aligning a video;
          there is no cell prompt, no anchor, no position label of any kind.
        * Names the files with the ``DEMO`` infix at capture time, which
          every split builder rejects before any split is constructed.
        * Runs identically whether or not a camera is rolling; ``--filmed``
          only records a boolean for audit.
    """
    from pipeline.io.capture_logger import resolve_nodes, run_capture

    if args.test:
        print("error: --demo and --test cannot be combined. The demo is excluded from every split;")
        print("       the test split is one of them.")
        return 2
    if str(args.session) != DEMO_SESSION and not args.force:
        print(f"error: the demo recording belongs to session {DEMO_SESSION} (the held-out test session),")
        print(f"       after the sweep and passes. Pass --force to record it in session {args.session}.")
        return 2

    rx_positions: Optional[dict[str, tuple[float, float]]] = None
    tx_position: Optional[tuple[float, float]] = None
    try:
        if args.rx_positions:
            rx_positions = parse_positions(args.rx_positions)
        if args.tx_position:
            tx_position = parse_positions(f"TX={args.tx_position}")["TX"]
    except ValueError as exc:
        print(f"error: {exc}")
        return 2

    out_dir, stem = session_paths(args.data_root, args.room, args.session, code, "free", test=False, demo=True)
    if not args.dry_run and refuse_overwrite(out_dir, stem, args.redo):
        return 2
    config = SessionConfig(
        participant_code=code, room=args.room, session_id=args.session, test=False,
        clothing=args.clothing, footwear=args.footwear,
        height_cm=args.height_cm, weight_kg=args.weight_kg, chair_position=args.chair,
        rx_positions=rx_positions, tx_position=tx_position, baseline_path=args.baseline,
        notes=args.notes, data_root=args.data_root, demo=True, filmed=bool(args.filmed),
    )

    print("=" * 72)
    print("DEMONSTRATION RECORDING  -  CSI ONLY  -  NO GROUND TRUTH")
    print(f"  participant {code}   room {args.room}   session {args.session}   filmed={config.filmed}")
    print(f"  files: {out_dir}/{stem}_RX*.bin  +  {stem}.gt.json")
    print(f"  {DEMO_REASON}")
    print("-" * 72)
    print("  The script (read it to them first):")
    for i, step in enumerate(DEMO_SCRIPT, 1):
        print(f"   {i}. {step}")
    print("-" * 72)
    print(f"  The capture starts now and runs until the second SPACE, or {args.demo_seconds:.0f} s.")
    print("=" * 72)

    if args.dry_run:
        return 0

    try:
        nodes = resolve_nodes(args.nodes)
    except ValueError as exc:
        print(f"error: {exc}")
        return 2
    if not nodes:
        print("No receivers found.")
        return 1

    node_states: dict[str, NodeState] = {}
    key_queue: "queue.Queue[KeyEvent]" = queue.Queue()
    key_stop = threading.Event()
    reader = KeyReader(key_queue, key_stop)
    clock = DemoClock(key_queue, enabled=reader.enabled, ceiling_s=args.demo_seconds)
    started_at = time.time()
    try:
        with reader:
            rc = run_capture(
                nodes=nodes, baud=args.baud, duration=args.demo_seconds, out_dir=out_dir, interval=1.0,
                run_config={"ground_truth": False, "demo": True, "participant_code": code,
                            "room": args.room, "session_id": args.session, "filmed": config.filmed,
                            "reason": DEMO_REASON},
                expect_tx_hz=args.expect_hz, reset=True,
                extra_consumers=[clock], stop_when=lambda: clock.finished,
                writer_prefix=f"{stem}_", timestamped_subdir=False, states_out=node_states,
            )
    finally:
        reader.restore()
    ended_by = "spacebar" if clock.finished else ("ceiling" if clock.start is not None else "no spacebar press")
    path = write_demo_sidecar(config, {n: st.sta_mac for n, st in node_states.items()},
                              out_dir, stem, started_at, time.time() - started_at,
                              markers=clock.markers(), script=DEMO_SCRIPT, ended_by=ended_by)
    print(f"\nDemo sidecar: {path}   (mode=demo, position_labels=null, filmed={config.filmed}, ended by {ended_by})")
    if clock.start is None:
        print("  WARNING: no spacebar press was recorded, so there is no in/out marker for the video.")
    return rc


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Entry point for ``python -m pipeline.io.ground_truth``."""
    import random

    from pipeline.io.capture_logger import resolve_nodes, run_capture

    args = build_arg_parser().parse_args(argv)

    try:
        code = validate_participant_code(args.participant)
    except ValueError as exc:
        print(f"error: {exc}")
        return 2

    if args.demo:
        return _run_demo(args, code)

    needs_bias = args.mode in ("both", "walk")
    try:
        bias = load_rt_bias()
    except FileNotFoundError as exc:
        if needs_bias:
            print(f"error: {exc}")
            return 2
        bias = RtBias(bias_s=0.0, sd_s=0.0, source="none", measured_at="n/a")
    except ValueError as exc:
        print(f"error: {exc}")
        return 2

    rx_positions: Optional[dict[str, tuple[float, float]]] = None
    tx_position: Optional[tuple[float, float]] = None
    try:
        if args.rx_positions:
            rx_positions = parse_positions(args.rx_positions)
        if args.tx_position:
            tx_position = parse_positions(f"TX={args.tx_position}")["TX"]
    except ValueError as exc:
        print(f"error: {exc}")
        return 2

    if rx_positions is None and not args.dry_run:
        print(
            "error: --rx-positions is required for a live capture.\n"
            "  The 2D position head is trained on where the receivers were, and that\n"
            "  geometry is recorded nowhere else: a session captured without it cannot\n"
            "  be used for tracking and cannot be reproduced.\n"
            '  Example: --rx-positions "RX1=2.5,5.5 RX2=-0.5,2.5 RX3=5.5,2.5"'
        )
        return 2

    if not args.dry_run:
        missing = [n for n, v in (("--height-cm", args.height_cm), ("--weight-kg", args.weight_kg)) if v is None]
        if missing:
            print(
                f"error: {' and '.join(missing)} required for a live capture.\n"
                "  Body size sets both the scale of the reflecting surface and the stride\n"
                "  length, so it is the first covariate an identity result must be checked\n"
                "  against: a model separating tall from short is not recognising gait.\n"
                "  Ask once, at consent, with the clothing and footwear.\n"
                "  Example: --height-cm 178 --weight-kg 72"
            )
            return 2
        for name, value, lo, hi in (
            ("--height-cm", args.height_cm, 100.0, 230.0),
            ("--weight-kg", args.weight_kg, 30.0, 250.0),
        ):
            if not lo <= value <= hi:
                print(f"error: {name} {value:g} is outside {lo:g}-{hi:g}. Check the units.")
                return 2

    seed = args.seed if args.seed is not None else random.randrange(1 << 30)
    cell_seed = args.cell_seed if args.cell_seed is not None else random.randrange(1 << 30)
    facing_seed = args.facing_seed if args.facing_seed is not None else random.randrange(1 << 30)
    plan = build_session(seed)
    cell_order = build_cell_order(cell_seed)
    facings = build_facing_order(facing_seed, len(cell_order.cells))

    steps, mode_order = build_steps(plan, cell_order, split=not args.contiguous, facings=facings)
    if args.mode == "walk":
        steps = [s for s in steps if isinstance(s, PassStep)]
        mode_order = "walk_only"
    elif args.mode == "grid":
        steps = [s for s in steps if isinstance(s, CellStep)]
        mode_order = "grid_only"

    file_mode = "walk" if args.mode == "walk" else ("grid" if args.mode == "grid" else "walk")
    out_dir, stem = session_paths(args.data_root, args.room, args.session, code, file_mode, args.test)
    if not args.dry_run and refuse_overwrite(out_dir, stem, args.redo):
        return 2

    config = SessionConfig(
        participant_code=code,
        room=args.room,
        session_id=args.session,
        test=args.test,
        clothing=args.clothing,
        footwear=args.footwear,
        height_cm=args.height_cm,
        weight_kg=args.weight_kg,
        chair_position=args.chair,
        rx_positions=rx_positions,
        tx_position=tx_position,
        baseline_path=args.baseline,
        notes=args.notes,
        data_root=args.data_root,
    )

    print(f"participant {code}   room {args.room}   session {args.session}" + ("   TEST" if args.test else ""))
    print(f"reaction-time bias {bias.bias_s:+.4f}s (sd {bias.sd_s:.4f}s) from {bias.source}")
    print(f"path seed {seed}, cell seed {cell_seed}, facing seed {facing_seed}, order: {mode_order}")
    print("facing cups: " + ", ".join(f"{d}={c}" for d, c in CAN_COLOURS.items()))
    print(f"{len(steps)} steps -> {out_dir}/{stem}.*")
    if rx_positions:
        print("receivers: " + "  ".join(f"{n}({p[0]:g},{p[1]:g})" for n, p in sorted(rx_positions.items())))
        for w in check_geometry(rx_positions):
            print(f"  WARNING: {w}")
    if tx_position:
        print(f"transmitter: ({tx_position[0]:g}, {tx_position[1]:g})")

    if args.dry_run:
        print()
        for i, s in enumerate(steps, 1):
            if isinstance(s, PassStep):
                print(f"  {i:3d}  WALK  {s.path.name:<7} {s.path.cue}")
            else:
                print(f"  {i:3d}  GRID  {s.cell.cell_id:<7} centre ({s.cell.centre_xy[0]:.1f}, {s.cell.centre_xy[1]:.1f}) m   {facing_cue(s.facing)}")
        return 0

    try:
        nodes = resolve_nodes(args.nodes)
    except ValueError as exc:
        print(f"error: {exc}")
        return 2
    if not nodes:
        print("No receivers found. Ground truth without CSI would be pointless.")
        return 1

    key_queue: "queue.Queue[KeyEvent]" = queue.Queue()
    key_stop = threading.Event()
    node_states: dict[str, NodeState] = {}

    session = GroundTruthSession(
        steps=steps,
        config=config,
        bias=bias,
        plan=plan,
        cell_order=cell_order,
        mode_order=mode_order,
        out_dir=out_dir,
        stem=stem,
        key_queue=key_queue,
        node_states=node_states,
        record_s=args.cell_seconds,
        show_images=not args.no_images,
    )
    session.facing_seed = facing_seed

    print()
    if not args.no_images and steps:
        first_kind = "grid" if isinstance(steps[0], CellStep) else "walk"
        opened = open_reference_images(first_kind)
        if opened:
            print("Reference sheets opened: " + ", ".join(os.path.basename(p) for p in opened))
            print("They are opened NOW, before capture, because opening a file moves keyboard")
            print("focus out of the terminal. CLICK BACK INTO THIS TERMINAL before you start;")
            print("nothing will steal focus again for the rest of the session.")
            print()

    print(f"SPACE = mark    {KEY_REDO} = redo this step    {KEY_ABORT} = abort")
    print("Starting capture ...")
    print()

    reader = KeyReader(key_queue, key_stop)
    try:
        with reader:
            rc = run_capture(
                nodes=nodes,
                baud=args.baud,
                duration=None,
                out_dir=out_dir,
                interval=1.0,
                quiet_monitor=True,  # the session owns the terminal; rates still measured
                run_config={
                    "ground_truth": True,
                    "participant_code": code,
                    "room": args.room,
                    "session_id": args.session,
                    "test": args.test,
                },
                expect_tx_hz=args.expect_hz,
                reset=True,
                extra_consumers=[session],
                stop_when=lambda: session.finished,
                writer_prefix=f"{stem}_",
                timestamped_subdir=False,
                states_out=node_states,
            )
    finally:
        reader.restore()
        # A session that did not reach its last step was cut short, by
        # Ctrl+C, a signal, or an error. Say so in the sidecar rather than
        # letting a partial file read as a complete one: `make inspect`
        # reports an aborted session as a run to redo.
        if not session.finished:
            session.aborted = True
        # The session owns the ONLY copy of the anchor times: they live in
        # memory until close() writes the .gt.json. Closing here, in the
        # finally, is what guarantees they survive an abort, an exception or
        # a capture that never started. Without this the run produces CSI
        # with no labels, which is unusable and unrecoverable once the
        # process exits.
        session.close()

    return rc


if __name__ == "__main__":
    sys.exit(main())
