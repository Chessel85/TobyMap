"""Packs taken out of use while TobyMap runs: MapSession.remove_packs (P4-T6c, P4-T6d)."""
from mapcore.packs.pack import Pack
from mapcore.packs.source import MemorySource
from mapcore.session import MapSession

HAMPSHIRE = {"lat": 51.2000, "lon": -1.4000, "zoom_m": 5000, "step_m": 100}


class _Closing(MemorySource):
    closed = False

    def close(self):
        self.closed = True


def _session(test_pack):
    source = _Closing(test_pack.read_bytes(), name="test.pack")
    s = MapSession(platform="web", packs=[Pack(source)], saved_state=HAMPSHIRE)
    s.start()
    return s, source


def test_a_removed_pack_is_no_longer_read_and_is_closed(test_pack):
    s, source = _session(test_pack)
    assert "Hampshire" in s.map_label()
    zoom = s.save()["state"]
    r = s.remove_packs(["test.pack"])
    assert r.redraw and r.panel_stale and r.details_stale
    assert s.store.packs == [] and source.closed
    assert s.start_label().startswith("No map pack is installed")
    assert s.save()["state"] == zoom   # the place is kept


def test_a_name_not_in_use_changes_nothing(test_pack):
    s, source = _session(test_pack)
    before = s.store
    r = s.remove_packs(["other.pack"])
    assert not r.redraw and s.store is before and not source.closed
    assert "Hampshire" in s.map_label()
    s.store.close()


def test_a_removed_pack_can_be_added_again(test_pack):
    s, _ = _session(test_pack)
    s.remove_packs(["test.pack"])
    s.add_packs([MemorySource(test_pack.read_bytes(), name="test.pack")])
    assert "Hampshire" in s.map_label()
    s.store.close()
