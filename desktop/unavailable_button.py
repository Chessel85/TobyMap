"""A button that can be unavailable yet stays in the Tab order (P4-T14g; ACC-7).

Qt skips a disabled button when tabbing, so a screen reader user never learns the
button is there. This button stays enabled for Qt, so Tab still reaches it, but
while it is unavailable:

* screen readers are told it is disabled, so NVDA says "unavailable" with its name;
* pressing it, by Space, Enter, the mouse or a screen reader's default action, does
  nothing and says nothing;
* it is drawn in the greyed text of a disabled button.

The accessibility is the module's own QAccessibleWidget, given by a factory, as in
desktop/panel_tree.py and desktop/map_widget.py. Its state is Qt's own for the
button, with "disabled" added while it is unavailable, and its name is the
button's text. When the button becomes available or unavailable, screen readers
are sent the change.
"""
from __future__ import annotations

from PySide6.QtGui import QAccessible, QAccessibleActionInterface, QAccessibleStateChangeEvent, QPalette
from PySide6.QtWidgets import QAccessibleWidget, QPushButton


class UnavailableButton(QPushButton):
    """A push button with `set_available`. Connect with `on_press`, which runs only while it is available."""

    def __init__(self, text: str = "", parent=None):
        install_accessible_factory()
        super().__init__(text, parent)
        self.available = True

    def on_press(self, handler) -> None:
        self.clicked.connect(lambda _checked=False: handler() if self.available else None)

    def set_available(self, available: bool) -> None:
        available = bool(available)
        if available == self.available:
            return
        self.available = available
        if available:
            self.setPalette(QPalette())   # back to the palette it inherits
        else:
            palette = self.palette()
            grey = palette.color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText)
            for group in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive):
                palette.setColor(group, QPalette.ColorRole.ButtonText, grey)
            self.setPalette(palette)
        if QAccessible.isActive():
            changed = QAccessible.State()
            changed.disabled = True
            QAccessible.updateAccessibility(QAccessibleStateChangeEvent(self, changed))


class UnavailableButtonAccessible(QAccessibleWidget):
    """The button to screen readers: a button, disabled while it is unavailable, still focusable."""

    def __init__(self, button: UnavailableButton):
        super().__init__(button, QAccessible.Role.Button)
        self.button = button

    def role(self):
        return QAccessible.Role.Button

    def state(self):
        s = super().state()
        if not self.button.available:
            s.disabled = True
        return s

    def text(self, kind):
        if kind == QAccessible.Text.Name:
            return self.button.accessibleName() or self.button.text().replace("&&", "\0").replace("&", "").replace("\0", "&")
        return super().text(kind)

    def actionNames(self):
        names = list(super().actionNames())
        if self.button.available:
            names.insert(0, QAccessibleActionInterface.pressAction())
        return names

    def doAction(self, name):
        if name == QAccessibleActionInterface.pressAction():
            if self.button.available:
                self.button.click()
            return
        super().doAction(name)


def _accessible_factory(_key, obj):
    if isinstance(obj, UnavailableButton):
        iface = getattr(obj, "_unavailable_accessible", None)
        if iface is None:
            # Kept on the button: Python must keep the object alive while Qt uses it.
            iface = obj._unavailable_accessible = UnavailableButtonAccessible(obj)
        return iface
    return None


_factory_installed = False


def install_accessible_factory() -> None:
    global _factory_installed
    if not _factory_installed:
        QAccessible.installFactory(_accessible_factory)
        _factory_installed = True
