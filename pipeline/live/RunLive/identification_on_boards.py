# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: Starts identification on the boards in its own process, with the receivers' MAC addresses from...

from __future__ import annotations

import sys


# Function main.
def main(argv=None) -> int:
    import pipeline.constrained.RunLive.receiver_macs as NO
    import pipeline.live.RunLive.identification_app as IE
    from pipeline.live.RunLive.main import board_macs
    NO.room_a_macs = lambda _root=None: board_macs()
    return IE.main(["rig"] + list(sys.argv[1:] if argv is None else argv))


if __name__ == "__main__":
    sys.exit(main())
