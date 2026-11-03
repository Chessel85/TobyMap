"""The build log's heartbeat: a quiet log means a fault, not a long step (DMT-2)."""
import time

from mapdata.pipeline.progress import Progress


def test_a_still_running_line_names_the_last_step(tmp_path):
    p = Progress(say=lambda t: None)
    p.open_log(tmp_path / "log.txt")
    p.line("Cut 49 areas into grid squares.")
    assert not p.beat_once(every=300)          # not quiet for long enough
    p.last_logged = time.monotonic() - 400
    assert p.beat_once(every=300)
    assert p.beat_once(every=300)              # a beat does not count as a new line, so it beats again
    assert p.last_text == "Cut 49 areas into grid squares."
    p.close()
    lines = (tmp_path / "log.txt").read_text(encoding="utf-8").splitlines()
    assert "Still running, 7 minutes since the last line, which was: Cut 49 areas into grid squares." in lines[-1]


def test_the_heartbeat_thread_stops_with_the_log(tmp_path):
    p = Progress(say=lambda t: None)
    p.open_log(tmp_path / "log.txt")
    p.start_heartbeat(every=300)
    p.close()
    p._beat.join(timeout=5)
    assert not p._beat.is_alive()
