# Phase 1 report: the walking skeleton

Written on 5 November 2026, when you accepted Phase 1. It follows the order in section 1.5 of the implementation plan.

## Where the phase stands

* All 16 tasks, P1-T1 to P1-T16, are done. The list is in docs/plan/phase-1.md.
* You passed every step of the desktop checklist (third pass) and the web checklist (second pass) with version 0.0.9, and accepted the phase on 5 November.
* You chose not to publish a release. I ask again at the end of Phase 2 (DP110). So the version stays 0.0.9, nothing is on GitHub Releases, and the web version is not on GitHub Pages.
* Every discussion point is answered. DP140 and DP141 became Phase 2 tasks P2-T14 and P2-T15.

## What was built

* The core: geodesy, the pack format, the store and "where am I", the world model and north-fixed stepping across the 180 degree line, the wording of every announcement, the command registry and the session, and the map scene.
* The data pipeline: check, fetch and build, with the world's base pack lite: 246 countries, 3,207 first-level divisions and 11 oceans, 125.9 MB, with no gaps.
* The desktop version: the map, the Information panel, Details and the menu bar, settings, your own keys, the key describer, held keys that speak only the last place, your click and bump sounds, and an Information panel whose levels NVDA reads (DP135).
* The web version: the same, running the same core in the browser, with the pack downloaded once and kept.
* The listening test tool, diagnostics, and the Windows installer and portable zip.

## Changes from your last checklist passes

* Keys that are a symbol are said as a word, such as Ctrl+Comma.
* The keys dialog starts with short lines, one Down arrow each.
* Zoom and step keys say only what changed.
* Coordinates have only the decimal places the step needs, with a setting to always have all of them.
* The first click after start is at full volume.
* Desktop: OK before Cancel in the Tab order, and Space plays a sound in The sounds.
* Web: Escape on the menu bar returns to the map, Settings has tabs, Enter is OK, a number is chosen when you tab to it, and The sounds is one list.
* Your new bump.wav is in both versions.

## How to install and run it

* Installer: dist_installer\TobyMap-0.0.9-setup.exe, with the world pack. The portable zip is beside it.
* From the repository: `.venv\Scripts\python.exe -m desktop`, with `--at 51.2,1.2` to start at a place.
* Web: `.venv\Scripts\python.exe tools\serve_web.py --pack E:\osmdata\tobymap\output\world\world.pack`, with `?at=51.2,1.2` in the address to start at a place.

## The automatic checks

* Python tests: all pass on this laptop, 627 of them, including the nine acceptance scripts. Two voice tests can fail when the laptop is busy with the browser tests, and pass on their own.
* Browser tests: all pass in Chromium and Firefox.
* Continuous integration runs the Python tests on Windows and macOS, the browser tests, and the installer, which installs silently, runs the self-test, checks the sounds and uninstalls. The installer job failed on main earlier on 5 November because its data folder was missing; that was fixed in the last commit before this one.
* Step timing on the base pack lite: 95% of steps under 2 ms, against a target of 150 ms.

## Known problems

* NVDA says a letter key before the next announcement if typed words are echoed. Your NVDA setting "Speak typed words: only in edit controls" stops it (DP139).
* Holding an arrow key gives slightly uneven clicks while the map is drawn. Phase 2, P2-T14 (DP140).
* The world pack has not been rebuilt since 4 November, so the West Bank and the Ilemi Triangle still say "Unclaimed" instead of disputed.
* Obsolete Phase 0 code is still in the repository. You agreed it can be deleted (DP122); I do it at the start of Phase 2, so that removing it is checked on its own.

## What was not tested

* A Braille display.
* Installing on a clean computer other than continuous integration's.
* The web version on GitHub Pages, and downloading the 126 MB pack over the internet, since nothing is published.
* macOS by hand. Only continuous integration runs there.

## Next

Phase 2: orientation, layers and sound. At its start I check for newer PySide6 and Pyodide, as the plan says.
