"""Keeping Python's garbage collector from pausing TobyMap (P3-T24a, DP202).

The store keeps millions of small objects for as long as TobyMap runs: the feature records, as
dictionaries and lists, and the pack tiles' entries. Python's full garbage collection looks at
every one of them, and on the world pack it took about a second, during which nothing else ran:
not a key's answer on the desktop, nor anything in the web worker.

settle() moves every object that has lived through a young collection into the collector's
permanent generation (gc.freeze), which full collections leave alone. Objects are still freed as
soon as nothing refers to them, so the tile cache still empties as it should; only rings of
objects that refer to each other, which TobyMap's data does not make, would be kept.
"""
from __future__ import annotations

import gc


def settle() -> None:
    """Collect the young objects, then freeze what is left, so full collections stay short."""
    gc.collect(1)
    gc.freeze()
