"""AD-1: the core is shared and imports nothing from the shells or Qt."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_core_does_not_import_qt_or_shells():
    # In a subprocess: this test session may already have PySide6 loaded.
    code = (
        "import sys, mapcore\n"
        "bad = [m for m in sys.modules if m.split('.')[0] in ('PySide6', 'desktop', 'shiboken6')]\n"
        "print(','.join(bad))\n"
    )
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, check=True)
    assert out.stdout.strip() == ""


def test_core_source_never_names_a_shell():
    for path in (ROOT / "mapcore").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "import PySide6" not in text and "from PySide6" not in text, path.name
        assert "from desktop" not in text and "import desktop" not in text, path.name


def test_version_is_read():
    import mapcore

    assert mapcore.version()[0].isdigit()
