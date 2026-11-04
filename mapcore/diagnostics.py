"""The test trace and "copy diagnostics" (P1-T15, architecture 10.3).

The core keeps every command, announcement and earcon with the time each took.
The shells add when the key was pressed and when the text reached the screen
reader, by calling Trace.add_shell(). Nothing leaves the computer unless the
user pastes it (SCP-1, architecture 10.4).
"""
from __future__ import annotations

import time

import mapcore

TRACE_SECONDS = 300.0   # the last few minutes


def recent(trace: list[dict], seconds: float = TRACE_SECONDS, now: float | None = None) -> list[dict]:
    """Only the events inside the time limit, oldest first."""
    now = time.time() if now is None else now
    return [e for e in trace if now - e["at"] <= seconds]


def line(event: dict, origin: float) -> str:
    parts = [f"+{event['at'] - origin:.3f}s", event["command"], f"{event['ms']:.1f} ms"]
    if event.get("spoken"):
        parts.append("said: " + " | ".join(event["spoken"]))
    if event.get("earcons"):
        parts.append("earcons: " + ", ".join(event["earcons"]))
    for key in ("key_to_start_ms", "handed_to_screen_reader_ms"):
        if key in event:
            parts.append(f"{key.removesuffix('_ms').replace('_', ' ')}: {event[key]:.1f} ms")
    return "  ".join(parts)


def add_shell(session, key_pressed_at: float | None = None, handed_over_at: float | None = None) -> None:
    """The shell reports times (seconds on the same clock as the core's) for the latest event."""
    if not session.trace:
        return
    event = session.trace[-1]
    started = event["at"] - event["ms"] / 1000
    if key_pressed_at is not None:
        event["key_to_start_ms"] = max(0.0, (started - key_pressed_at) * 1000)
    if handed_over_at is not None:
        event["handed_to_screen_reader_ms"] = max(0.0, (handed_over_at - started) * 1000)


def report(session, now: float | None = None) -> str:
    """Plain lines, one per event, in the order things happened, ready to paste (P1-T15)."""
    events = recent(session.trace, now=now)
    out = [f"TobyMap {mapcore.version()} on {session.platform}"]
    for pack in session.store.packs:
        m = pack.manifest
        out.append(f"Pack {m['name']} version {m.get('version', '')} built {m.get('built', '')}")
    s = session.world
    out.append(f"Location {s.lat:.5f}, {s.lon:.5f}; zoom {s.zoom_m:g} m; step {s.step_m:g} m; linked {s.link}")
    out.append("Settings " + ", ".join(f"{k}={v}" for k, v in sorted(session.settings.values.items())))
    if session.settings.keys:
        out.append("Changed keys " + ", ".join(f"{k}={v}" for k, v in sorted(session.settings.keys.items())))
    out.append(f"Events in the last {int(TRACE_SECONDS // 60)} minutes: {len(events)}")
    if events:
        origin = events[0]["at"]
        out += [line(e, origin) for e in events]
    return "\n".join(out)
