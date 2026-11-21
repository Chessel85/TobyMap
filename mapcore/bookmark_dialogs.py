"""The bookmark manager and the bookmark list dialog (P4-T8e; USR-3, DP219 point 7).

The bookmark manager is for the bookmark lists themselves: new, rename, move up and down, delete, on or off, zoom
range, and Open list, which opens the bookmark list dialog for the chosen list. The bookmark list dialog is for one
list's bookmarks: move up and down, copy or move to another list, delete. Each has a Close button (ACC-7).

Changes take effect and are written at once, as there is no OK; deleting asks first. Every word is here, from the
templates, and the shells only show what is described and press the commands named in each dialog (AD-2, rule 2).
A message is said only where the focus does not tell it: a move says nothing, as the focus is on the moved item.
"""
from __future__ import annotations

from mapcore import bookmark_files
from mapcore.bookmarks import BookmarkFileError
from mapcore.describe import say, words

ASSERTIVE = "assertive"


class BookmarkDialogs:
    """The handlers of the two dialogs, for a MapSession (which owns the bookmarks and writes the file)."""

    def __init__(self, session, response_class):
        self.s = session
        self.Response = response_class
        self._deleting: tuple | None = None   # ("list", the list) or ("bookmark", the bookmark, its list), until answered
        self._saving = None   # the list chosen when Save to a file was pressed, until a line is chosen (P4-T9b)

    def handlers(self) -> dict:
        return {
            "bookmark.manager_open": self.manager_open,
            "bookmark.list_open": self.list_open,
            "bookmark.manager_listing": lambda **a: self.Response(bookmark_manager=self.manager_listing(int(a.get("index", 0)))),
            "bookmark.manager_new": self.new,
            "bookmark.manager_rename": self.rename,
            "bookmark.manager_move": self.move,
            "bookmark.manager_on": self.on,
            "bookmark.manager_zoom": self.zoom,
            "bookmark.manager_delete": self.delete_ask,
            "bookmark.manager_delete_confirm": self.delete,
            "bookmark.manager_save_file": self.save_ask,
            "bookmark.manager_save_chosen": self.save_chosen,
            "bookmark.manager_open_file": self.open_ask,
            "bookmark.manager_file_opened": self.file_opened,
            "bookmark.list_move": self.list_move,
            "bookmark.list_copy": self.list_copy,
            "bookmark.list_move_to": self.list_move_to,
            "bookmark.list_delete": self.list_delete_ask,
            "bookmark.list_delete_confirm": self.list_delete,
        }

    @property
    def lists(self) -> list:
        return self.s.bookmarks.lists

    def _changed(self, r):
        """The file written and the Bookmarks group filled again, once the shell handles the response."""
        r.panel_stale = True
        r.details_stale = True
        return self.s.bookmarks_changed(r)

    def _confirm(self, title: str, text: str, ok: str, submit: str) -> dict:
        return {"kind": "confirm", "title": title, "text": text, "ok": ok, "cancel": say("ui.cancel"), "submit": submit}

    # The bookmark manager -------------------------------------------------------------------------

    def _range_text(self, low, high) -> str:
        units = self.s.settings["units"]
        low = low or 0.0
        if not low and high is None:
            return say("bookmark_manager.range_every")
        if not low:
            return say("bookmark_manager.range_to", high=words.distance_text(high, units))
        if high is None:
            return say("bookmark_manager.range_from", low=words.distance_text(low, units))
        return say("bookmark_manager.range_between", low=words.distance_text(low, units),
                   high=words.distance_text(high, units))

    def _line(self, lst) -> str:
        n = len(lst.bookmarks)
        contents = say("bookmark_manager.contents_none") if n == 0 else (
            say("bookmark_manager.contents_one") if n == 1 else say("bookmark_manager.contents", count=n))
        if not lst.min_zoom_m and lst.max_zoom_m is None:
            return say("bookmark_manager.item", name=lst.name, contents=contents)
        return say("bookmark_manager.item_zoom", name=lst.name, contents=contents,
                   range=self._range_text(lst.min_zoom_m, lst.max_zoom_m))

    def manager_listing(self, current: int = 0) -> dict:
        """The lists as the dialog shows them: each line, whether it is on (its check box), whether it can move up
        or down, and its zoom range for the zoom dialog's boxes."""
        n = len(self.lists)
        return {"current": max(0, min(n - 1, current)), "items": [
            {"label": self._line(l), "name": l.name, "on": l.on, "up": i > 0, "down": i < n - 1,
             "min_zoom_m": l.min_zoom_m or 0.0, "max_zoom_m": l.max_zoom_m}
            for i, l in enumerate(self.lists)]}

    def manager_open(self, **_a):
        units = self.s.settings["units"]
        values = set(self.s.world.zoom_list)
        for l in self.lists:
            values.update(z for z in (l.min_zoom_m, l.max_zoom_m) if z)
        zooms = [{"value": z, "label": words.distance_text(z, units)} for z in sorted(values)]
        keys = ("title", "help", "list", "new", "rename", "open_list", "up", "down", "delete", "zoom", "save_file",
                "open_file", "new_title", "rename_title", "name_label", "name_help", "zoom_title", "min_zoom",
                "max_zoom", "delete_ok")
        w = {k: say(f"bookmark_manager.{k}") for k in keys} | {"ok": say("ui.ok"), "cancel": say("ui.cancel"),
                                                              "close": say("ui.close")}
        return self.Response(dialog={
            "kind": "bookmark_manager", "title": w["title"], "help": w["help"], "words": w,
            "zooms": zooms, "every_zoom": say("bookmark_manager.every_zoom"),
            "lists": self.manager_listing(self.s.bookmarks.last_used),
            "commands": {"new": "bookmark.manager_new", "rename": "bookmark.manager_rename",
                         "move": "bookmark.manager_move", "on": "bookmark.manager_on",
                         "zoom": "bookmark.manager_zoom", "delete": "bookmark.manager_delete",
                         "open_list": "bookmark.list_open", "save_file": "bookmark.manager_save_file",
                         "open_file": "bookmark.manager_open_file", "listing": "bookmark.manager_listing"}})

    def _place(self, index) -> int | None:
        try:
            index = int(index)
        except (TypeError, ValueError):
            return None
        return index if 0 <= index < len(self.lists) else None

    def _list_name(self, text, besides: int | None = None):
        """The typed name, or the words that refuse it."""
        name = " ".join(str(text).split())
        if not name:
            return None, say("bookmark.list_name_empty")
        if self.s.bookmarks._list_name_used(name, besides=besides):
            return None, say("bookmark.list_name_taken", name=name)
        return name, None

    def new(self, text: str = "", **_a):
        """New list: at the end, and the focus goes to it, which tells its name; nothing is said."""
        name, error = self._list_name(text)
        if error:
            return self.Response(error=error)
        li = self.s.bookmarks.new_list(name)
        return self._changed(self.Response(bookmark_manager=self.manager_listing(li)))

    def rename(self, index: int = -1, text: str = "", **_a):
        li = self._place(index)
        if li is None:
            return self.Response().earcon("blocked")
        name, error = self._list_name(text, besides=li)
        if error:
            return self.Response(error=error)
        old = self.lists[li].name
        if name == old:
            return self.Response(bookmark_manager=self.manager_listing(li))
        self.s.bookmarks.rename_list(li, name)
        r = self.Response(bookmark_manager=self.manager_listing(li)).speak(
            say("bookmark_manager.renamed", old=old, name=name), ASSERTIVE)
        return self._changed(r)

    def move(self, index: int = -1, by: int = 0, **_a):
        """Move up or down: the focus is on the moved line, which tells where it is; nothing is said. At either
        end nothing changes (the button is unavailable there)."""
        li = self._place(index)
        by = -1 if int(by) < 0 else 1
        if li is None or not 0 <= li + by < len(self.lists):
            return self.Response()
        li = self.s.bookmarks.move_list(li, by)
        return self._changed(self.Response(bookmark_manager=self.manager_listing(li)))

    def on(self, index: int = -1, on: bool = True, **_a):
        """The check box: the screen reader says on or off itself, so nothing is said."""
        li = self._place(index)
        if li is None:
            return self.Response().earcon("blocked")
        self.s.bookmarks.set_on(li, bool(on))
        return self._changed(self.Response(bookmark_manager=self.manager_listing(li)))

    def zoom(self, index: int = -1, low=0.0, high=None, **_a):
        """OK in the zoom range dialog: the range, as a layer's. A minimum larger than the maximum is refused in the
        layers' words and nothing changes."""
        li = self._place(index)
        if li is None:
            return self.Response().earcon("blocked")
        try:
            low = float(low or 0.0)
            high = None if high in (None, "") else float(high)
        except (TypeError, ValueError):
            return self.Response(error=say("settings.bad_value"))
        if high is not None and low > high:
            return self.Response(error=say("layers.range_error"))
        self.s.bookmarks.set_zoom(li, low, high)
        lst = self.lists[li]
        r = self.Response(bookmark_manager=self.manager_listing(li)).speak(
            say("bookmark_manager.zoom_set", name=lst.name, range=self._range_text(lst.min_zoom_m, lst.max_zoom_m)),
            ASSERTIVE)
        return self._changed(r)

    def delete_ask(self, index: int = -1, **_a):
        """Delete list: a question first, "Delete the list Castles and its 3 bookmarks?", and when it is the only
        list, what happens next (the model starts a new empty "Bookmarks")."""
        li = self._place(index)
        if li is None:
            return self.Response().earcon("blocked")
        lst = self.lists[li]
        n = len(lst.bookmarks)
        text = say("bookmark_manager.delete_question_none", name=lst.name) if n == 0 else (
            say("bookmark_manager.delete_question_one", name=lst.name) if n == 1 else
            say("bookmark_manager.delete_question", name=lst.name, count=n))
        if len(self.lists) == 1:
            text = f"{text} {say('bookmark_manager.delete_last')}"
        self._deleting = ("list", lst)
        return self.Response(dialog=self._confirm(say("bookmark_manager.delete_title"), text,
                                                  say("bookmark_manager.delete_ok"), "bookmark.manager_delete_confirm"))

    def delete(self, **_a):
        kind, lst = (self._deleting or (None, None))[:2]
        self._deleting = None
        li = next((i for i, l in enumerate(self.lists) if l is lst), None) if kind == "list" else None
        if li is None:
            return self.Response().earcon("blocked")
        self.s.bookmarks.delete_list(li)
        r = self.Response(bookmark_manager=self.manager_listing(li)).speak(
            say("bookmark_manager.deleted", name=lst.name), ASSERTIVE)
        return self._changed(r)

    # Saving and opening files (P4-T9b, P4-T9c; USR-5, DP217, DP219) ---------------------------------------------

    _SAVE_CHOICES = (("list", "geojson"), ("list", "gpx"), ("all", "geojson"), ("all", "gpx"))

    def save_ask(self, index: int = -1, **_a):
        """Save to a file: a list to choose from, with Cancel (the "choose" kind, as hierarchy mode's lists): the chosen
        list or all lists, each as GeoJSON or as GPX. The file type is chosen here, not in the Save box, as the web
        version's download has no type to choose."""
        li = self._place(index)
        if li is None:
            return self.Response().earcon("blocked")
        self._saving = self.lists[li]
        names = {"list": self.lists[li].name, "all": say("bookmark_files.all_lists")}
        lines = [say(f"bookmark_files.as_{kind}", what=names[what]) for what, kind in self._SAVE_CHOICES]
        return self.Response(dialog={"kind": "choose", "title": say("bookmark_files.save_title"),
                                     "help": say("bookmark_files.save_help"), "lines": lines, "text": "\n".join(lines),
                                     "go": "bookmark.manager_save_chosen", "current": 0, "cancel": say("ui.cancel")})

    def save_chosen(self, index: int = -1, **_a):
        """A line chosen: the shell is asked to save the file's text, under a suggested name (Response.save_file).
        Nothing of yours changes, so the bookmarks file is not written."""
        chosen, self._saving = self._saving, None
        li = next((i for i, l in enumerate(self.lists) if l is chosen), None)
        try:
            what, kind = self._SAVE_CHOICES[int(index)]
        except (TypeError, ValueError, IndexError):
            what = None
        if li is None or what is None or int(index) < 0:
            return self.Response().earcon("blocked")
        b = self.s.bookmarks
        part = li if what == "list" else None
        said = self.lists[li].name if what == "list" else say("bookmark_files.all_saved")
        extension = bookmark_files.TYPES[kind]["extension"]
        return self.Response(save_file={
            "title": say(f"bookmark_files.save_box_{kind}", what=said),
            "name": bookmark_files.file_name(b, part, extension), "extension": extension,
            "filter": say(f"bookmark_files.filter_{kind}"), "mime": bookmark_files.TYPES[kind]["mime"],
            "text": bookmark_files.file_text(b, part, kind),
            "saved": say(f"bookmark_files.saved_{kind}", what=said), "failed": say("bookmark_files.failed")})

    def open_ask(self, **_a):
        """Open a file: the shell is asked for a file (Response.open_file), and runs bookmark.manager_file_opened with its
        text. GeoJSON or GPX is told from the text, so every bookmark file is offered together."""
        return self.Response(open_file={"title": say("bookmark_files.open_title"),
                                        "filter": say("bookmark_files.open_filter"),
                                        "accept": ".geojson,.json,.gpx", "submit": "bookmark.manager_file_opened"})

    def file_opened(self, text: str = "", file: str = "", **_a):
        """The text of the file chosen in the Open box: its lists after yours, each under a free name, the focus on the
        first of them; or why it is not a bookmark file, and nothing changes (DP217)."""
        try:
            opened = bookmark_files.read(text, file)
        except BookmarkFileError as refused:
            return self.Response().speak(refused.text, ASSERTIVE)
        places = self.s.bookmarks.add_lists(opened.lists)
        made = [self.lists[i] for i in places]
        count = sum(len(l.bookmarks) for l in made)
        if len(made) > 1:
            text = say("bookmark_files.opened_lists", lists=len(made), count=count, names=", ".join(l.name for l in made))
        elif count == 0:
            text = say("bookmark_files.opened_empty", name=made[0].name)
        else:
            text = say("bookmark_files.opened_one" if count == 1 else "bookmark_files.opened", count=count,
                       name=made[0].name)
        if opened.left_out:
            text += " " + (say("bookmark_files.left_out_one") if opened.left_out == 1 else
                           say("bookmark_files.left_out", count=opened.left_out))
        return self._changed(self.Response(bookmark_manager=self.manager_listing(places[0])).speak(text, ASSERTIVE))

    # The bookmark list dialog ---------------------------------------------------------------------

    def list_listing(self, li: int, current: int = 0) -> dict:
        """One list's bookmarks, each with whether it can move up or down, and the other lists a bookmark can go to,
        as {"index", "name"}; with none, Copy and Move are unavailable."""
        marks = self.lists[li].bookmarks
        n = len(marks)
        return {"current": max(0, min(n - 1, current)),
                "items": [{"label": m.name, "up": i > 0, "down": i < n - 1} for i, m in enumerate(marks)],
                "targets": [{"index": i, "name": l.name} for i, l in enumerate(self.lists) if i != li],
                "empty": say("bookmark_list_dialog.empty") if not n else ""}

    def list_open(self, index=None, **_a):
        """The bookmark list dialog for the list at this place, or the list used last (from the Map menu)."""
        li = self._place(index) if index is not None else self.s.bookmarks.last_used
        if li is None:
            li = self.s.bookmarks.last_used
        lst = self.lists[li]
        keys = ("list", "up", "down", "target_label", "no_target", "copy", "move", "delete", "empty")
        w = {k: say(f"bookmark_list_dialog.{k}") for k in keys} | {"close": say("ui.close")}
        title = say("bookmark_list_dialog.title", name=lst.name)
        return self.Response(dialog={
            "kind": "bookmark_list", "title": title, "help": say("bookmark_list_dialog.help"), "words": w,
            "list": li, "lists": self.list_listing(li),
            "commands": {"move": "bookmark.list_move", "copy": "bookmark.list_copy", "move_to": "bookmark.list_move_to",
                         "delete": "bookmark.list_delete"}})

    def _mark(self, list: int, index: int):
        try:
            li, bi = int(list), int(index)
            if li < 0 or bi < 0:
                raise IndexError
            return li, bi, self.lists[li].bookmarks[bi]
        except (TypeError, ValueError, IndexError):
            return None, None, None

    def list_move(self, list: int = -1, index: int = -1, by: int = 0, **_a):
        li, bi, mark = self._mark(list, index)
        by = -1 if int(by) < 0 else 1
        if mark is None or not 0 <= bi + by < len(self.lists[li].bookmarks):
            return self.Response()
        bi = self.s.bookmarks.move(li, bi, by)
        return self._changed(self.Response(bookmark_list=self.list_listing(li, bi)))

    def _target(self, li: int, target):
        try:
            target = int(target)
        except (TypeError, ValueError):
            return None
        return target if 0 <= target < len(self.lists) and target != li else None

    def list_copy(self, list: int = -1, index: int = -1, target: int = -1, **_a):
        """A copy at the end of another list, numbered as the original's name is used (Rome_1), the original staying: the
        focus does not move, so this is said."""
        li, bi, mark = self._mark(list, index)
        target = self._target(li, target) if mark is not None else None
        if target is None:
            return self.Response().earcon("blocked")
        name = self.s.bookmarks.unique_name(mark.name)
        place = self.s.bookmarks.copy_to(li, bi, target)
        self.s.bookmarks.rename(target, place, name)
        text = say("bookmark_list_dialog.copied", name=mark.name, list=self.lists[target].name, copy=name)
        return self._changed(self.Response(bookmark_list=self.list_listing(li, bi)).speak(text, ASSERTIVE))

    def list_move_to(self, list: int = -1, index: int = -1, target: int = -1, **_a):
        """Out of this list onto the end of another: the focus goes to the next bookmark here, so this is said."""
        li, bi, mark = self._mark(list, index)
        target = self._target(li, target) if mark is not None else None
        if target is None:
            return self.Response().earcon("blocked")
        self.s.bookmarks.move_to(li, bi, target)
        text = say("bookmark_list_dialog.moved", name=mark.name, list=self.lists[target].name)
        return self._changed(self.Response(bookmark_list=self.list_listing(li, bi)).speak(text, ASSERTIVE))

    def list_delete_ask(self, list: int = -1, index: int = -1, **_a):
        """Delete: the same question as Delete on a current bookmark asks (P4-T8d)."""
        li, bi, mark = self._mark(list, index)
        if mark is None:
            return self.Response().earcon("blocked")
        self._deleting = ("bookmark", mark, self.lists[li])
        return self.Response(dialog=self._confirm(
            say("bookmark_current.delete_title"),
            say("bookmark_current.delete_question", name=mark.name, list=self.lists[li].name),
            say("bookmark_current.delete_ok"), "bookmark.list_delete_confirm"))

    def list_delete(self, **_a):
        pending, self._deleting = self._deleting, None
        if not pending or pending[0] != "bookmark":
            return self.Response().earcon("blocked")
        _kind, mark, lst = pending
        li = next((i for i, l in enumerate(self.lists) if l is lst), None)
        bi = next((i for i, m in enumerate(lst.bookmarks) if m is mark), None) if li is not None else None
        if bi is None:
            return self.Response().earcon("blocked")
        self.s.bookmarks.delete(li, bi)
        r = self.Response(bookmark_list=self.list_listing(li, bi), redraw=True).speak(
            say("bookmark_current.deleted", name=mark.name), ASSERTIVE)
        return self._changed(r)
