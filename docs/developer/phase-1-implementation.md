# Phase 1 implementation notes

What was built in P1-T7 to P1-T15, where it is, and why. The design stays in docs/design; this file says how the code now stands. Words follow docs/design/glossary.md.

## The core (mapcore)

* `session.py`: the one object both shells talk to (AD-2). `MapSession` holds the store, the world state, the settings and the announcement history.
  * `run(name, **args)` carries out a command and returns a `Response`: announcements, earcons, and flags saying what to refresh, where focus goes, a dialog to open, or an action.
  * `press(key, region)` looks the key up in the registry, with the user's changed keys, and runs it. In the key describer it describes the key and runs nothing. It returns None for a key that is not ours.
  * `run_many` carries out commands that arrived together and describes only the last (ANN-3).
  * Held keys: `run(..., held=True)` moves without looking anything up or speaking; `release()` describes the place where the hold ended, against the last place described.
  * `scene`, `panel`, `details`, `settings_schema`, `key_table`, `earcon_file`, `save` give the shells everything they draw or show. `save()` is the settings, changed keys and the world state (PLT-5).
* `describe/`: `describer.py` (what changed, place text, heading report, Nearby labels), `words.py` (distances, bearings, coordinates and areas as words), `templates.yaml` (every word, 3.4) and `earcons.yaml` (the seven earcons and their files).
* `settings.py` and `settings.yaml`: the settings dialog as data, with checked values. The desktop and the web version both build their dialog from it.
* `commands/registry.yaml` and `registry.py`: every command once. New: `held`, `toggle`, key overrides, `command_for_key` and `clash`.
* `render/scene.py`: the map scene from the pack (see explanation.md, "How the map picture is chosen"). The zoom is a distance across the smaller side of the window (DP76).
* `sound/curve.py`: the distance curve (SON-9), settings in `defaults.yaml`.
* `diagnostics.py`: the test trace report and the shells' timing (P1-T15).

## The desktop (desktop)

* `window.py`: the four regions. One application-wide key filter sends every key to `session.press`, and handles auto-repeat and key release for the held key. The panel (`QTreeWidget`) is updated in place.
* `dialogs.py`: text, list (history), key capture and settings dialogs; each has a Close, OK or Cancel button.
* `sounds.py`: plays the earcons with `QSoundEffect`, loaded in advance; the user's own file if set, else the default; `RecordingSounds` for tests. Since P2-T16h, the earcons go through the spatial sound player's mixer instead (`desktop/audio/player.py`).
* `storage.py`: settings in `%APPDATA%\TobyMap\settings.json`, packs in `%APPDATA%\TobyMap\packs` (or `TOBYMAP_PACKS`, or `--pack`).
* `audio/spatial.py`: stereo with a lower pitch behind, and head-related sound (MIT KEMAR), moved from spike S1. `audio/voice.py`: Piper with the Alba voice for spoken labels.
* `app.py`: `--pack`, and `--self-test --out FILE` for the installer's check.

## The web (web)

* `worker.js` opens the packs listed in `packs/packs.json`: downloaded once into private storage (OPFS) with progress at most every 10 seconds, read through a synchronous handle; held in memory where private storage is unavailable.
* `bridge.py` is conversion only: handles to a byte source, responses to JavaScript, arrays to bytes.
* `main.js` handles keys from the registry the core sends, joins queued moves, the held key (`event.repeat` and key up), the mouse, the dialogs built from the core's schema, and the sounds (`sounds.js`, Web Audio). Settings are kept in `localStorage`.
* `tree.js` updates in place and goes to an item by id for F3. `menu.js` can be rebuilt after a key changes and shows toggles.

## Tests

* `tests/acceptance/scripts/*.yaml`: acceptance scripts (key presses and the exact words), run by `tests/acceptance/test_scripts.py`. `tools/make_checklists.py` makes docs/checklists/phase-1.md from them.
* `tests/data/forbidden_keys.yaml`: keys no default may use (ACC-4).
* `tests/performance/test_walk.py`: the 1,000-step walk on the world pack (skipped without it).
* `tests/world_pack.py`: finds the world pack on this computer.
* Browser tests serve the test pack as the site's pack (`tests/web/conftest.py`). axe-core is fetched with `tools/fetch_vendor.py --axe`; the test skips without it.

## Tools

* `tools/make_placeholder_sounds.py`: the seven placeholder earcons (never overwrites).
* `tools/listening_test`: the listening test (`model.py` trials and results, `run.py` the flow, `app.py` the window, `analyse.py` the findings, `web/` blocks 1 and 3 in a browser).

## Packaging and delivery

* `packaging/build.ps1 [-Pack world.pack]`; the spec includes the sounds, Shapely and QtMultimedia. CI installs silently, runs the self-test, uninstalls and checks the folder is empty.
* `.github/workflows/pages.yml`: GitHub Pages, run by hand only, until DP110 is answered.
* `docs/release-notes.md`, `packaging/THIRD_PARTY_NOTICES.txt`.

## Decisions made while building

* Copying the coordinates was dropped (DP113 answer).
* Shapely was added to the runtime requirements, since the store uses it.
* Nothing is spoken while a key is held; the first press is announced at once.
* The widest map views have about 24,000 points (DP125).
* Settings menu opened with Alt+T (DP126).
* Own sound files: desktop only (DP123). Since P2-T8, the web version has them too, kept in the browser's storage (web/js/own_sounds.js).
