"""The pack manager and the offer of the world pack at the first start (P4-T6d; PCK-2, PCK-4, PCK-5, ACC-7).

P opens a list of the packs in the catalogue: each one's name, size, date and state, with Install, Update, Remove and
Close. The shell fetches the catalogue's text from the address in the dialog (the core never touches the network) and
hands it back with packs.manager_listing; the core builds every line and says which buttons can act. Install and
Update answer with `install`, the catalogue entry for the shell to download (the shells' downloads are P4-T6b and
P4-T6c); Remove asks first, takes the pack out of use and answers with `remove_files`, the file names for the shell to
delete. Every word is from the templates (rule 4).
"""
from __future__ import annotations

from mapcore import version
from mapcore.describe import say
from mapcore.packs import catalogue as cat
from mapcore.packs import install

ASSERTIVE = "assertive"
WORLD = "world"


class PackManager:
    """The handlers of the pack manager, for a MapSession (which owns the store of open packs)."""

    def __init__(self, session, response_class):
        self.s = session
        self.Response = response_class
        self.catalogue: cat.Catalogue | None = None   # the last list the shell handed over
        self.note = ""                               # why the list is not shown, or ""
        self._lines: list[dict] = []                 # the lines as last shown, for the buttons' indexes
        self._removing: str | None = None            # the file to remove, until answered

    def handlers(self) -> dict:
        return {
            "packs.manager_open": self.open,
            "packs.manager_listing": self.listing,
            "packs.manager_install": self.install,
            "packs.manager_update": self.update,
            "packs.manager_remove": self.remove_ask,
            "packs.manager_remove_confirm": self.remove,
            "packs.first_run": self.first_run,
            "packs.first_run_download": self.first_run_download,
        }

    # What is installed ----------------------------------------------------------------------------

    def installed(self) -> dict:
        """The name of each open pack (from its manifest) and its version."""
        return {p.manifest["name"]: p.manifest["version"] for p in self.s.store.packs if p.manifest.get("name")}

    def has_world(self) -> bool:
        return WORLD in self.installed()

    def urls(self) -> dict:
        d = self.s.defaults.get("packs", {})
        return {"desktop": d.get("catalogue_url_desktop", ""), "web": d.get("catalogue_url_web", "")}

    # The lines -------------------------------------------------------------------------------------

    def _take(self, text, failed: bool) -> None:
        """A catalogue's text from the shell, or the news that it could not be fetched."""
        if text is None and not failed:
            return
        self.note = ""
        if failed or not text:
            self.catalogue = None
            self.note = say("pack_manager.unreadable")
            return
        try:
            self.catalogue = cat.parse(text)
        except cat.CatalogueError as e:
            self.catalogue = None
            self.note = e.message

    def _items(self) -> list[dict]:
        have = self.installed()
        files = {p.manifest.get("name"): p for p in self.s.store.packs}
        items, seen = [], set()
        for e in (self.catalogue.entries if self.catalogue else ()):
            state = self.catalogue.state(e, have, version())
            seen.add(e.name)
            pack = files.get(e.name)
            words = say({cat.INSTALLED: "packs.state_installed", cat.NOT_INSTALLED: "packs.state_not_installed",
                         cat.UPDATE: "packs.state_update"}[state])
            items.append({
                "label": say("pack_manager.item", name=install.label(e), size=install._megabytes(e.size, True),
                             date=e.date, state=words),
                "name": e.name, "state": state, "entry": e.to_dict(),
                "file": pack.name if pack is not None else None,
                "install": state == cat.NOT_INSTALLED, "update": state == cat.UPDATE, "remove": pack is not None})
        for name, pack in files.items():   # packs in use that the catalogue does not list
            if name in seen:
                continue
            items.append({"label": say("pack_manager.item_local", name=name,
                                       date=str(pack.manifest.get("built", "")), state=say("packs.state_installed")),
                          "name": name, "state": cat.INSTALLED, "entry": None, "file": pack.name,
                          "install": False, "update": False, "remove": True})
        return items

    def _listing(self, current: int = 0) -> dict:
        self._lines = self._items()
        n = len(self._lines)
        return {"items": self._lines, "current": max(0, min(n - 1, current)), "note": self.note,
                "none": say("pack_manager.none") if not n else ""}

    def open(self, **_a):
        keys = ("title", "help", "list", "install", "update", "remove", "loading")
        w = {k: say(f"pack_manager.{k}") for k in keys} | {"close": say("ui.close")}
        self.note = ""
        return self.Response(dialog={
            "kind": "pack_manager", "title": w["title"], "help": w["help"], "words": w,
            "catalogue_urls": self.urls(), "lines": self._listing(),
            "commands": {"listing": "packs.manager_listing", "install": "packs.manager_install",
                         "update": "packs.manager_update", "remove": "packs.manager_remove"}})

    def listing(self, text=None, failed: bool = False, index: int = 0, unset: bool = False, **_a):
        """The lines again. With the catalogue's text, from the shell; failed when it could not be fetched; unset
        when this version has no address for it yet."""
        if unset:
            self.catalogue, self.note = None, say("pack_manager.not_listed")
        else:
            self._take(text, bool(failed))
        r = self.Response(pack_manager=self._listing(int(index)))
        if self.note:
            r.speak(self.note, ASSERTIVE)
        return r

    # The buttons -------------------------------------------------------------------------------------

    def _chosen(self, index):
        try:
            index = int(index)
        except (TypeError, ValueError):
            index = -1
        if 0 <= index < len(self._lines):
            return self._lines[index]
        return None

    def _download(self, item, update: bool):
        entry = cat.Entry.from_dict(item["entry"])
        refused = install.refusal(entry, version())
        if refused:
            return self.Response().speak(refused, ASSERTIVE)
        return self.Response(install={"entry": item["entry"], "update": update})

    def install(self, index: int = -1, **_a):
        item = self._chosen(index)
        if item is None:
            return self.Response().speak(say("pack_manager.nothing_chosen"), ASSERTIVE)
        if item["entry"] is None or not item["install"]:
            return self.Response().speak(say("pack_manager.not_installable", name=item["name"]), ASSERTIVE)
        return self._download(item, False)

    def update(self, index: int = -1, **_a):
        item = self._chosen(index)
        if item is None:
            return self.Response().speak(say("pack_manager.nothing_chosen"), ASSERTIVE)
        if not item["update"]:
            return self.Response().speak(say("pack_manager.not_updatable", name=item["name"]), ASSERTIVE)
        return self._download(item, True)

    def remove_ask(self, index: int = -1, **_a):
        item = self._chosen(index)
        if item is None:
            return self.Response().speak(say("pack_manager.nothing_chosen"), ASSERTIVE)
        if not item["remove"]:
            return self.Response().speak(say("pack_manager.not_installed", name=item["name"]), ASSERTIVE)
        self._removing = item["file"]
        name = item["name"]
        return self.Response(dialog={
            "kind": "confirm", "title": say("pack_manager.remove_title", name=name),
            "text": say("pack_manager.remove_question", name=name), "ok": say("pack_manager.remove_ok"),
            "cancel": say("ui.cancel"), "submit": "packs.manager_remove_confirm"})

    def remove(self, **_a):
        """The pack taken out of use and closed; the shell deletes its file."""
        file, self._removing = self._removing, None
        if file is None:
            return self.Response()
        pack = next((p for p in self.s.store.packs if p.name == file), None)
        name = pack.manifest.get("name", file) if pack is not None else file
        listed = self.catalogue.get(name) if self.catalogue else None
        name = install.label(listed) if listed is not None else name   # as the list shows it
        r = self.s.remove_packs([file])
        r.remove_files = [file]
        r.pack_manager = self._listing()
        return r.speak(say("pack_manager.removed", name=name), ASSERTIVE)

    # The first start --------------------------------------------------------------------------------

    def first_run(self, text=None, failed: bool = False, unset: bool = False, **_a):
        """The offer of the world pack, once the shell has the catalogue's text (or could not fetch it)."""
        if self.has_world():
            return self.Response()
        if unset:
            return self.Response().speak(say("pack_manager.first_run_not_listed"), ASSERTIVE)
        self._take(text, bool(failed))
        if self.catalogue is None:
            return self.Response().speak(say("pack_manager.first_run_unreadable"), ASSERTIVE)
        entry = self.catalogue.get(WORLD)
        if entry is None:
            return self.Response().speak(say("pack_manager.first_run_missing"), ASSERTIVE)
        refused = install.refusal(entry, version())
        if refused:
            return self.Response().speak(refused, ASSERTIVE)
        return self.Response(dialog={
            "kind": "confirm", "title": say("pack_manager.first_run_title"),
            "text": say("pack_manager.first_run", size=install._megabytes(entry.size, True)),
            "ok": say("pack_manager.first_run_ok"), "cancel": say("pack_manager.first_run_cancel"),
            "submit": "packs.first_run_download"})

    def first_run_download(self, **_a):
        entry = self.catalogue.get(WORLD) if self.catalogue else None
        if entry is None or self.has_world():
            return self.Response()
        return self.Response(install={"entry": entry.to_dict(), "update": False})
