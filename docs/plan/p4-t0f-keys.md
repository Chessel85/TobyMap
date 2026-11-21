# Phase 4 keys (P4-T0f)

Written on 21 November 2026 by Claude Code, for you and for the bookmark and pack manager work items. The command registry cannot hold a command before it has a handler, so each key is added, and docs/design/keymap.csv made again, by the work item that adds its command. These are the keys to use, with the clashes found.

## Keys on Windows, desktop and web

* The bookmark dialog, on the map: Ctrl+Enter.
* Bookmark an item in the Information panel: Ctrl+Enter (the existing panel.bookmark).
* Rename a bookmark that is the current feature: Ctrl+Enter; the core decides by what is current.
* The Bookmarks group: Shift+8.
* The measure start: Ctrl+Shift+M.
* The bookmark manager: Ctrl+Shift+B, as Ctrl+Shift+L is the layers and Ctrl+Shift+V the map views.
* The bookmark list dialog: no key. It opens from the bookmark manager and from the Map menu.
* The pack manager: P, on the map.
* Cut, copy and paste a bookmark that is the current feature: Ctrl+X, Ctrl+C, Ctrl+V.
* Delete a bookmark that is the current feature: Delete, after asking.

## Keys on a Mac

* Cmd in place of Ctrl throughout: Cmd+Enter, Cmd+Shift+B, Cmd+X, Cmd+C, Cmd+V.
* Delete a bookmark: Cmd+Backspace, Apple's key for deleting an item.
* The measure start: Cmd+Shift+M on the desktop; Ctrl+Shift+Y in a browser, as the Mac browser key map already gives Ctrl+Shift+M to the menu, and Cmd+Shift+M is the browser's profile menu.

## Clashes to watch

* Ctrl+Shift+M and Ctrl+Shift+B belong to the browsers too (responsive design mode or the profile menu; the bookmarks bar). A page can usually take them first; the browser tests check this in Chromium, Firefox and Edge. If a browser keeps one, the other choice is Ctrl+Shift+Y for the measure start and Ctrl+Shift+K for the bookmark manager.
* Ctrl+X, Ctrl+C, Ctrl+V and Delete edit text in every text box, the bookmark dialog's Name box among them, and Ctrl+C copies from Details. The shells let a focused text box have these keys first; the core acts only when the focus is the map or the Information panel and the current feature is a bookmark.
* Ctrl+C was dropped in DP113 (no copy of coordinates), and a test checks it is in no key map. DP219 brings it back for bookmarks only; that test changes with it.
* Ctrl+Enter in the bookmark dialog itself can work as OK, as the dialog has the keys while it is open.
* P is only on the map, so the Information panel's first-letter search still has P.
* Shift+8 is found by its place on the keyboard (DP109), as Shift+1 to Shift+7 are.
