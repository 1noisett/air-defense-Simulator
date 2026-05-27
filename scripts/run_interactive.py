"""Entry point: launch the interactive air-defense simulator window."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from visualization.interactive import InteractiveSimulator

if __name__ == "__main__":
    InteractiveSimulator().show()
