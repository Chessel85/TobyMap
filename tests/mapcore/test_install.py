"""Installing a pack from the catalogue: the core's part (P4-T6b, PCK-5)."""
import hashlib
import json

import pytest

from mapcore.packs import install
from mapcore.packs.catalogue import CatalogueError, Entry
from mapcore.packs.source import DownloadingSource, MemorySource


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


# The web version (P4-T6c, PCK-4) ------------------------------------------------------------------------------

def test_a_pack_that_fits_or_space_not_known_is_not_refused():
    e = entry(b"x" * 5_000_000)
    assert install.no_room(e, None) is None
    assert install.no_room(e, 5_000_000) is None
    assert install.no_room(e, 9_000_000_000) is None


def test_a_pack_too_big_for_the_space_left_is_refused_saying_what_is_left():
    e = entry(b"x" * 5_000_001)
    assert install.no_room(e, 2_999_999) == (
        "World needs 6 megabytes, and this browser has 2 megabytes left for TobyMap, so it was not downloaded. "
        "Free some space, then try again.")
    assert "has 0 megabytes left" in install.no_room(e, -10)


def test_a_download_hashes_and_says_its_progress_as_the_bytes_come():
    data = bytes(range(256)) * 40
    d = install.Download(entry(data))
    said = [d.add(data[i:i + 1024]) for i in range(0, len(data), 1024)]
    assert [s for s in said if s] == [f"Downloading World: {p} percent." for p in range(10, 100, 10)]
    assert d.end() == (True, "World is downloaded and open.")


def test_a_download_that_does_not_match_is_damaged():
    data = b"x" * 1000
    d = install.Download(entry(data))
    d.add(b"y" * 1000)
    ok, text = d.end()
    assert not ok and text == install.damaged(entry(data))
    short = install.Download(entry(data))
    short.add(data[:999])
    assert short.end()[0] is False


class _Counting(MemorySource):
    def __init__(self, data):
        super().__init__(data)
        self.reads = 0

    def read(self, offset, length):
        self.reads += 1
        return super().read(offset, length)


def test_a_downloading_pack_reads_what_is_stored_from_there_and_the_rest_by_range_requests():
    data = bytes(range(256)) * 4
    remote, stored = _Counting(data), _Counting(data[:100] + bytes(len(data) - 100))
    source = DownloadingSource(len(data), "world.pack", remote, stored)
    assert source.size == len(data) and source.name == "world.pack" and not source.complete
    assert source.read(0, 10) == data[:10] and remote.reads == 1   # nothing is stored yet
    source.have = 100
    assert source.read(0, 100) == data[:100] and stored.reads == 1
    assert source.read(90, 20) == data[90:110] and remote.reads == 2   # partly stored: from the internet
    source.stored_as(None)   # being moved into place
    assert source.read(0, 10) == data[:10] and remote.reads == 3 and stored.reads == 1
    finished = _Counting(data)
    source.stored_as(finished)
    assert source.complete
    assert source.read(1000, 24) == data[1000:] and finished.reads == 1 and remote.reads == 3


def test_a_downloading_pack_opens_and_reads_records_before_it_is_stored(test_pack):
    from mapcore.packs.pack import Pack

    data = test_pack.read_bytes()
    remote = _Counting(data)
    pack = Pack(DownloadingSource(len(data), "test.pack", remote, MemorySource(b"")))
    assert pack.name == "test.pack" and remote.reads > 0


# Cancel and resume (P4-T6f, PCK-5) ----------------------------------------------------------------------------

def test_a_part_carries_on_only_when_its_record_is_for_this_very_version():
    e = entry(b"x" * 1000)
    record = install.part_record(e)
    assert install.record_name(e) == "world.pack.part.json"
    assert install.resume_from(e, record, 400) == 400
    assert install.resume_from(e, json.loads(record), 400) == 400
    assert install.resume_from(e, None, 400) == 0                       # no record: started again
    assert install.resume_from(e, "not json", 400) == 0
    assert install.resume_from(e, install.part_record(entry(b"y" * 1000, version="2026.11.2")), 400) == 0
    assert install.resume_from(e, install.part_record(entry(b"y" * 1000)), 400) == 0   # another checksum
    assert install.resume_from(e, record, 0) == 0
    assert install.resume_from(e, record, 1000) == 0                    # whole, or more: it was not the pack
    assert install.resume_from(e, record, 1500) == 0


def test_the_reply_says_whether_the_part_is_carried_on_or_started_again():
    assert install.reply_start(400, 206) == 400
    assert install.reply_start(400, 200) == 0       # the server ignored the range: the whole file comes again
    assert install.reply_start(0, 200) == 0
    assert install.reply_start(400, 416) is None
    assert install.reply_start(0, 404) is None


def test_a_download_that_carries_on_hashes_the_whole_file_and_says_only_what_is_new():
    data = bytes(range(256)) * 40
    e = entry(data)
    held = len(data) * 45 // 100
    d = install.Download(e)
    for i in range(0, held, 300):
        d.held(data[i:min(i + 300, held)])
    assert d.received == held
    said = [d.add(data[i:i + 1024]) for i in range(held, len(data), 1024)]
    assert [s for s in said if s] == [f"Downloading World: {p} percent." for p in range(50, 100, 10)]
    assert d.end() == (True, "World is downloaded and open.")
    d.restart()
    assert d.received == 0 and not d.too_long
    d.add(data + b"!")
    assert d.too_long


def test_the_cancel_and_carry_on_words():
    e = entry(b"x" * 1000)
    assert install.cancelled(e) == ("The download of World is cancelled. Install or Update it again to carry on "
                                    "from where it stopped.")
    assert install.carrying_on(e, 456) == "Carrying on downloading World from 45 percent."
    assert install.part_held(e, {"world": {"record": install.part_record(e), "size": 300}}) == 300
    assert install.part_held(e, {"other": {"record": install.part_record(e), "size": 300}}) == 0
    assert install.part_held(e, None) == 0
