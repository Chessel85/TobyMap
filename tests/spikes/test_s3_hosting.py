"""Spike S3 helpers: the test file's pattern and range parsing (P0-T6). No network."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "spikes" / "s3"))

import hosting  # noqa: E402


def test_pattern_word_at_each_offset_is_its_index():
    data = hosting.pattern_bytes(0, 16)
    assert data == bytes([0, 0, 0, 0, 1, 0, 0, 0, 2, 0, 0, 0, 3, 0, 0, 0])


@pytest.mark.parametrize("start,length", [(0, 1), (1, 7), (4093, 4096), (2**26 - 5, 5)])
def test_pattern_ranges_agree_with_the_whole(start, length):
    whole = hosting.pattern_bytes(0, start + length)
    assert hosting.pattern_bytes(start, length) == whole[start:]
    assert hosting.matches_pattern(start, whole[start:])
    assert not hosting.matches_pattern(start + 1, whole[start:]) or length < 2


def test_write_test_file(tmp_path):
    path = hosting.write_test_file(tmp_path / "t.bin", size=40 * 1024 * 1024 + 6)
    data = path.read_bytes()
    assert len(data) == 40 * 1024 * 1024 + 6
    assert hosting.matches_pattern(0, data)


@pytest.mark.parametrize("header,expected", [
    ("bytes=0-15", (0, 15)),
    ("bytes=10-", (10, 99)),
    ("bytes=-16", (84, 99)),
    ("bytes=90-200", (90, 99)),
    ("bytes=100-110", None),
    ("bytes=5-2", None),
    ("bytes=-", None),
    ("bytes=0-1,5-6", None),
])
def test_parse_range(header, expected):
    assert hosting.parse_range(header, 100) == expected
