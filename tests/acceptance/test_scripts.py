"""Run every acceptance script (P1-T7). The North Pole script needs the world pack and is skipped without it."""
import pytest

from tests.acceptance import runner
from tests.world_pack import world_pack_path

SCRIPTS = runner.load_all()


@pytest.mark.parametrize("name, script", SCRIPTS, ids=[n for n, _ in SCRIPTS])
def test_script(name, script, test_pack):
    packs = {"test": test_pack}
    if script["pack"] == "world":
        world = world_pack_path()
        if world is None:
            pytest.skip("the world pack is not built on this computer")
        packs["world"] = world
    assert runner.run_script(script, packs) == []
