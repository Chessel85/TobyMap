"""Installing a pack from the catalogue: the core's part (P4-T6b, PCK-5)."""
import hashlib

import pytest

from mapcore.packs import install
from mapcore.packs.catalogue import CatalogueError, Entry


def entry(data: bytes = b"x" * 1000, **change) -> Entry:
    values = dict(name="world", version="2026.11.1", date="2026-11-20", size=len(data),
                  sha256=hashlib.sha256(data).hexdigest(), url_desktop="https://example.org/world.pack",
                  url_web="https://example.org/w/world.pack", app_versions={"from": "0.1.0"}, title="World")
    values.update(change)
    return Entry(**values)


def test_file_names():
    e = entry()
    assert install.file_name(e) == "world.pack"
    assert install.part_name(e) == "world.pack.part"


@pytest.mark.parametrize("name", ["../evil", "a/b", "a\\b", ".hidden", "", "c:x"])
def test_a_name_that_could_leave_the_folder_is_refused(name):
    e = entry(name=name)
    with pytest.raises(CatalogueError):
        install.file_name(e)
    assert install.refusal(e, "0.1.1")


def test_a_compatible_pack_is_not_refused():
    assert install.refusal(entry(), "0.1.1") is None


def test_an_incompatible_pack_is_refused_with_a_clear_message():
    old = install.refusal(entry(app_versions={"from": "9.0"}), "0.1.1")
    assert old == ("World needs TobyMap 9.0 or later, and this is TobyMap 0.1.1, so it was not downloaded. "
                   "Update TobyMap to use it.")
    new = install.refusal(entry(app_versions={"from": "0.0.1", "before": "0.1"}), "0.1.1")
    assert new == "World was made for versions of TobyMap before 0.1, and this is TobyMap 0.1.1, so it was not downloaded."
    assert install.refusal(entry(), "unknown")


def test_matches_needs_size_and_checksum():
    data = b"abc" * 100
    e = entry(data)
    assert install.matches(e, len(data), hashlib.sha256(data).hexdigest().upper())
    assert not install.matches(e, len(data) - 1, hashlib.sha256(data).hexdigest())
    assert not install.matches(e, len(data), hashlib.sha256(b"other").hexdigest())


def test_progress_is_said_at_most_every_10_percent():
    p = install.Progress(entry(size=1000))
    said = [(done, p.update(done)) for done in range(0, 1001, 7)]
    lines = [w for _d, w in said if w]
    assert lines == [f"Downloading World: {n} percent." for n in range(10, 100, 10)]
    assert p.update(1000) is None


def test_progress_jumping_past_steps_says_only_the_latest():
    p = install.Progress(entry(size=100))
    assert p.update(35) == "Downloading World: 30 percent."
    assert p.update(39) is None
    assert p.update(100) is None
    assert install.Progress(entry(size=0)).update(0) is None


def test_the_words():
    e = entry()
    assert install.done(e) == "World is downloaded and open."
    assert "removed" in install.damaged(e) and "checksum" in install.damaged(e)
    assert "could not be downloaded" in install.failed(e)
    assert install.label(entry(title="")) == "world"
