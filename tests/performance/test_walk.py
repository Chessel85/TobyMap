"""NFR-1: a walk of 1,000 steps round the world on the base pack lite (P1-T7 exit check).

Skipped where the world pack is not built. The result is printed and also written
to docs/plan/p1-walk-timing.md when TOBYMAP_WRITE_TIMING is set.
"""
import os
import statistics
import time
from pathlib import Path

import pytest

from mapcore.session import MapSession
from tests.world_pack import world_pack_path


def test_a_thousand_steps_round_the_world():
    pack = world_pack_path()
    if pack is None:
        pytest.skip("the world pack is not built on this computer")
    s = MapSession(packs=[pack], saved_state={"lat": 20.0, "lon": -170.0, "zoom_m": 250_000, "step_m": 1_000_000})
    s.start()
    import random

    rng = random.Random(1)   # the same walk every time: random directions and step sizes, so little is cached
    times = []
    for _ in range(1000):
        name = rng.choice(["move.east", "move.west", "move.north", "move.south"])
        s.world.step_index = rng.randrange(6, len(s.world.step_list))   # 1 km to 1,000 km: nearly every step lands somewhere new
        start = time.perf_counter()
        s.run(name)
        times.append((time.perf_counter() - start) * 1000)
    times.sort()
    median, p95, slowest = statistics.median(times), times[int(len(times) * 0.95)], times[-1]
    text = (f"1,000 steps on the base pack lite: median {median:.1f} ms, 95th percentile {p95:.1f} ms, "
            f"slowest {slowest:.1f} ms (target: 95% within 150 ms).")
    print(text)
    if os.environ.get("TOBYMAP_WRITE_TIMING"):
        Path(__file__).resolve().parents[2].joinpath("docs", "plan", "p1-walk-timing.md").write_text(
            "# Step timing on the base pack lite\n\n" + text + "\n", encoding="utf-8")
    assert p95 <= 150
