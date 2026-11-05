"""Starting the desktop application."""
from __future__ import annotations

import argparse
import sys
import time


def main(argv: list[str] | None = None) -> int:
    started = time.perf_counter()
    parser = argparse.ArgumentParser(prog="desktop")
    parser.add_argument("--pack", help="a pack file, or a folder of packs, to use instead of your packs folder")
    parser.add_argument("--out", help="with --self-test, write the result to this file (the program has no console)")
    parser.add_argument("--self-test", action="store_true",
                        help="open the packs, announce where you are, print it and exit (the installer's check)")
    args, rest = parser.parse_known_args(argv if argv is not None else sys.argv[1:])

    from PySide6.QtWidgets import QApplication

    from desktop import storage
    from desktop.window import MainWindow

    app = QApplication.instance() or QApplication([sys.argv[0], *rest])
    app.setApplicationName("TobyMap")
    if args.pack:
        import os

        os.environ[storage.PACK_ENV] = args.pack
    if args.self_test:
        return self_test(args.out)
    window = MainWindow()
    window.session.startup_took((time.perf_counter() - started) * 1000)
    window.show()
    return app.exec()


def self_test(out: str | None = None) -> int:
    """Open the packs and ask "where am I", without a window (P1-T14: the installer's self-test).
    The result goes to a file when asked, because the installed program has no console."""
    from desktop import storage
    from desktop.sounds import SOUNDS
    from mapcore.session import MapSession

    lines: list[str] = []
    packs = storage.find_packs()
    code = 0
    if not packs:
        lines.append("No pack found.")
        code = 1
    else:
        session = MapSession(platform="desktop", packs=packs)
        lines.append(session.start().announcements[0]["text"])
        lines.append(session.run("where.am_i").announcements[0]["text"])
        lines.append("Sounds: " + ", ".join(sorted(p.name for p in SOUNDS.glob("*.wav"))))
    text = "\n".join(lines) + "\n"
    if out:
        from pathlib import Path

        Path(out).write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return code
