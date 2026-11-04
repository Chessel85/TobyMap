"""The test trace and the copied diagnostics (P1-T15)."""
from mapcore import diagnostics
from mapcore.session import MapSession


def test_the_trace_keeps_only_its_time_limit():
    now = 10_000.0
    trace = [{"command": "old", "ms": 1, "at": now - 600}, {"command": "new", "ms": 1, "at": now - 10}]
    assert [e["command"] for e in diagnostics.recent(trace, now=now)] == ["new"]


def test_the_report_is_plain_lines_in_the_order_things_happened(test_pack):
    s = MapSession(packs=[test_pack], saved_state={"lat": 51.2, "lon": 1.2, "zoom_m": 25000, "step_m": 25000})
    s.start()
    s.press("Down")
    s.press("Space")
    text = diagnostics.report(s)
    lines = text.splitlines()
    assert lines[0].startswith("TobyMap ") and "Pack test" in text and "units=metric" in text
    events = [ln for ln in lines if ln.startswith("+")]
    assert [ln.split()[1] for ln in events] == ["move.south", "where.am_i"]
    assert 'said: North Atlantic Ocean' in events[0] and "|" not in text.split("Events")[0]
    assert all("\t" not in ln for ln in lines)


def test_shell_times_are_added_to_the_latest_event(test_pack):
    s = MapSession(packs=[test_pack], saved_state={"lat": 51.2, "lon": 1.2})
    s.start()
    import time

    pressed = time.time() - 0.01
    s.press("Space")
    diagnostics.add_shell(s, key_pressed_at=pressed, handed_over_at=time.time() + 0.001)
    ev = s.trace[-1]
    assert ev["key_to_start_ms"] >= 0 and ev["handed_to_screen_reader_ms"] >= 0
    assert "handed to screen reader" in diagnostics.line(ev, ev["at"])


def test_copy_diagnostics_gives_a_dialog_with_the_text_to_copy(test_pack):
    s = MapSession(packs=[test_pack], saved_state={"lat": 51.2, "lon": 1.2})
    s.start()
    r = s.run("diagnostics.copy")
    assert r.dialog["copy"] == r.dialog["text"] and "Location 51.20000" in r.dialog["text"]
