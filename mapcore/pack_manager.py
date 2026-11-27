"""The pack manager and the offer of the world pack at the first start (P4-T6d; PCK-2, PCK-4, PCK-5, ACC-7).

P opens a list of the packs in the catalogue: each one's name, size, date and state, with Install, Update, Remove and
Close. The shell fetches the catalogue's text from the address in the dialog (the core never touches the network) and
hands it back with packs.manager_listing; the core builds every line and says which buttons can act. Install and
Update answer with `install`, the catalogue entry for the shell to download (the shells' downloads are P4-T6b and
P4-T6c); Remove asks first, takes the pack out of use and answers with `remove_files`, the file names for the shell to
delete. Every word is from the templates (rule 4).

Cancel and resume (P4-T6f): the shell hands each listing the packs it is downloading now and the .part files it holds
(their records and sizes); a pack downloading has Cancel download, which answers with `cancel_download`, its name,
for the shell to stop it, keeping its .part file; a pack partly downloaded says how much, and Install or Update
carries on from there.
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
        self.declined: dict = {}                     # pack name -> the newest version offered, kept in the saved state
        self._offered = None                         # the entry offered at start, until answered
        self.downloading: list = []                  # the packs the shell is downloading now, by name (P4-T6f)
        self.parts: dict = {}                        # name -> {"record", "size"}: the .part files the shell holds
        self.free: int | None = None                 # bytes free for packs, as the shell measured them (P4-T6g)
        self.folder: str = ""                        # the packs folder (desktop only), as the shell names it

    def keep(self, earlier: "PackManager") -> None:
        """What a session made afresh keeps from the one before (add_packs, remove_packs): the list and the shell's
        downloads."""
        self.catalogue = earlier.catalogue
        self.downloading, self.parts = list(earlier.downloading), dict(earlier.parts)
        self.free, self.folder = earlier.free, earlier.folder

    def handlers(self) -> dict:
        return {
            "packs.manager_open": self.open,
            "packs.manager_listing": self.listing,
            "packs.manager_install": self.install,
            "packs.manager_update": self.update,
            "packs.manager_remove": self.remove_ask,
            "packs.manager_remove_confirm": self.remove,
            "packs.manager_cancel": self.cancel,
            "packs.manager_move": self.move,
            "packs.manager_moved": self.moved,
            "packs.first_run": self.first_run,
            "packs.first_run_download": self.first_run_download,
            "packs.update_offer": self.update_offer,
            "packs.update_offer_update": self.update_offer_update,
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
            downloading = e.name in self.downloading
            held = install.part_held(e, self.parts) if state != cat.INSTALLED else 0
            if downloading:
                words = say("packs.state_downloading")
            elif held:
                words = say("packs.state_partial", state=words, percent=install.percent(e, held))
            items.append({
                "label": say("pack_manager.item", name=install.label(e), size=install._megabytes(e.size, True),
                             date=e.date, state=words),
                "name": e.name, "state": state, "entry": e.to_dict(),
                "file": pack.name if pack is not None else None,
                "install": state == cat.NOT_INSTALLED and not downloading,
                "update": state == cat.UPDATE and not downloading, "remove": pack is not None and not downloading,
                "cancel": downloading, "held": held})
        for name, pack in files.items():   # packs in use that the catalogue does not list
            if name in seen:
                continue
            items.append({"label": say("pack_manager.item_local", name=name,
                                       date=str(pack.manifest.get("built", "")), state=say("packs.state_installed")),
                          "name": name, "state": cat.INSTALLED, "entry": None, "file": pack.name,
                          "install": False, "update": False, "remove": True, "cancel": False, "held": 0})
        return items

    def _listing(self, current: int = 0) -> dict:
        self._lines = self._items()
        n = len(self._lines)
        return {"items": self._lines, "current": max(0, min(n - 1, current)), "note": self.note,
                "none": say("pack_manager.none") if not n else "", "space": self.space()}

    # The packs folder and its free space (P4-T6g, PCK-4, AD-18) -----------------------------------

    @staticmethod
    def size_words(size: int) -> str:
        """A size for people: gigabytes with one decimal from 1 GB up, else whole megabytes (rounded down)."""
        size = max(int(size), 0)
        if size >= 1_000_000_000:
            return say("pack_manager.gigabytes", n=f"{size / 1_000_000_000:.1f}")
        return say("pack_manager.megabytes", n=size // 1_000_000)

    def can_move(self) -> bool:
        return self.s.platform == "desktop"

    def space(self) -> str:
        """The folder's free space in words: the desktop names the folder, the browser has none."""
        known = self.free is not None
        if self.can_move():
            if not self.folder:
                return ""
            if known:
                return say("pack_manager.space_folder", folder=self.folder, free=self.size_words(self.free))
            return say("pack_manager.space_folder_unknown", folder=self.folder)
        return say("pack_manager.space_browser", free=self.size_words(self.free)) if known else ""

    def move(self, folder=None, free=None, need=0, problem=None, **_a):
        """Move packs folder (desktop). The shell has chosen the folder and measured it: free space there, the bytes to
        move, and a problem code when it cannot be used (same, inside, unwritable, clash, busy). The core says why not,
        or answers move_packs for the shell to carry out and report with packs.manager_moved."""
        if not self.can_move():
            return self.Response().speak(say("pack_manager.move_not_here"), ASSERTIVE)
        folder = str(folder or "")
        if not folder:
            return self.Response()
        if problem in ("same", "inside", "unwritable", "clash", "busy"):
            return self.Response().speak(say(f"pack_manager.move_{problem}", folder=folder), ASSERTIVE)
        need = max(int(need or 0), 0)
        if free is not None and int(free) < need:
            return self.Response().speak(say("pack_manager.move_no_room", folder=folder, need=self.size_words(need),
                                             left=self.size_words(free)), ASSERTIVE)
        return self.Response(move_packs={"folder": folder})

    def moved(self, folder=None, ok: bool = True, **_a):
        """The shell's report: the packs are in the new folder, or are back where they were."""
        folder = str(folder or "")
        if ok:
            self.folder = folder
            return self.Response().speak(say("pack_manager.moved", folder=folder), ASSERTIVE)
        return self.Response().speak(say("pack_manager.move_failed", folder=folder), ASSERTIVE)

    def open(self, **_a):
        keys = ("title", "help", "list", "install", "update", "remove", "cancel", "loading", "move", "move_choose")
        w = {k: say(f"pack_manager.{k}") for k in keys} | {"close": say("ui.close")}
        self.note = ""
        return self.Response(dialog={
            "kind": "pack_manager", "title": w["title"], "help": w["help"], "words": w,
            "catalogue_urls": self.urls(), "lines": self._listing(), "can_move": self.can_move(),
            "commands": {"listing": "packs.manager_listing", "install": "packs.manager_install",
                         "update": "packs.manager_update", "remove": "packs.manager_remove",
                         "cancel": "packs.manager_cancel", "move": "packs.manager_move",
                         "moved": "packs.manager_moved"}})

    def listing(self, text=None, failed: bool = False, index: int = 0, unset: bool = False, downloading=None,
                parts=None, **a):
        """The lines again. With the catalogue's text, from the shell; failed when it could not be fetched; unset
        when this version has no address for it yet. downloading (names) and parts (name -> {"record", "size"})
        are the shell's downloads and .part files now (P4-T6f); left out, the last ones given are kept."""
        if downloading is not None:
            self.downloading = [str(n) for n in downloading]
        if isinstance(parts, dict):
            self.parts = dict(parts)
        if "free" in a:   # the space left for packs and the folder, as the shell measured them (P4-T6g)
            free = a["free"]
            self.free = int(free) if isinstance(free, (int, float)) and free >= 0 else None
        if a.get("folder"):
            self.folder = str(a["folder"])
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

    def cancel(self, index: int = -1, **_a):
        """Cancel download (P4-T6f): the shell stops the download and keeps what has come, to carry on next time."""
        item = self._chosen(index)
        if item is None:
            return self.Response().speak(say("pack_manager.nothing_chosen"), ASSERTIVE)
        if not item.get("cancel"):
            return self.Response().speak(say("pack_manager.not_downloading", name=item["name"]), ASSERTIVE)
        entry = cat.Entry.from_dict(item["entry"])
        self.downloading = [n for n in self.downloading if n != entry.name]
        r = self.Response(cancel_download=entry.name)
        return r.speak(install.cancelled(entry), ASSERTIVE)

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

    # A newer pack at the start (P4-T6e) ------------------------------------------------------------

    def update_offer(self, text=None, **_a):
        """Once the shell has read the catalogue at start: a question about the first installed pack with a newer
        version this TobyMap can use, unless that version, or a newer one, was offered before. Asking counts as
        offering, so it is not repeated after Not now. Silent when the catalogue cannot be read."""
        if not text:
            return self.Response()
        try:
            catalogue = cat.parse(text)
        except cat.CatalogueError:
            return self.Response()
        self.catalogue = catalogue
        have = self.installed()
        for e in catalogue.entries:
            if catalogue.state(e, have, version()) != cat.UPDATE:
                continue
            seen = self.declined.get(e.name)
            if seen is not None and (cat._order(seen) or ()) >= (cat._order(e.version) or ()):
                continue
            self.declined[e.name] = e.version
            self._offered = e
            return self.Response(dialog={
                "kind": "confirm", "title": say("pack_manager.update_offer_title", name=install.label(e)),
                "text": say("pack_manager.update_offer", name=install.label(e), version=e.version,
                            size=install._megabytes(e.size, True), have=have[e.name]),
                "ok": say("pack_manager.update_offer_ok"), "cancel": say("pack_manager.update_offer_cancel"),
                "submit": "packs.update_offer_update"})
        return self.Response()

    def update_offer_update(self, **_a):
        entry, self._offered = self._offered, None
        if entry is None:
            return self.Response()
        return self.Response(install={"entry": entry.to_dict(), "update": True})

    def first_run_download(self, **_a):
        entry = self.catalogue.get(WORLD) if self.catalogue else None
        if entry is None or self.has_world():
            return self.Response()
        return self.Response(install={"entry": entry.to_dict(), "update": False})
