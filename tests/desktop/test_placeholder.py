"""Placeholder desktop test: PySide6 imports and a widget can be built offscreen (P0-T2)."""
from PySide6.QtWidgets import QApplication, QLabel


def test_widget_builds_offscreen():
    app = QApplication.instance() or QApplication([])
    label = QLabel("TobyMap")
    label.setAccessibleName("TobyMap")
    assert label.accessibleName() == "TobyMap"
    assert app.platformName() == "offscreen"
