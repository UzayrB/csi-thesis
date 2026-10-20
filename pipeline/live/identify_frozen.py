# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: The identification board run of the public build: identify_engine rig with the receivers' MACs from...

from __future__ import annotations

import sys


# Function main.
def main(argv=None) -> int:
    import pipeline.constrained.nodes as NO
    import pipeline.live.identify_engine as IE
    from pipeline.live.frozen_model import board_macs
    NO.room_a_macs = lambda _root=None: board_macs()
    return IE.main(["rig", "--mode", "identify"] + list(sys.argv[1:] if argv is None else argv))


if __name__ == "__main__":
    sys.exit(main())
