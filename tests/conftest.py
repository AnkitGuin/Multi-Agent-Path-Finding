"""Make the project root importable and provide shared fixtures.

Placing this file at the project root is what puts ``/…​/mapf`` on ``sys.path``
under pytest's default "prepend" import mode, so the tests can do
``from environment.grid import GridMap`` exactly like the scripts do.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
