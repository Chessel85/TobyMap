# Phase 1 report: the walking skeleton

Written on 4 November 2026, while you were away. This is a progress report, not the final phase report: nothing is committed, continuous integration has not run, and you have not tried it. It follows the order in section 1.5 of the implementation plan.

## Where the phase stands

* Tasks P1-T1 to P1-T6 and P1-T16 were done before. In this session I did P1-T7 to P1-T13 and P1-T15, and most of P1-T14. The list is in docs/plan/phase-1.md.
* Nothing is committed or pushed. Everything is in the working tree of the main branch. Commit, push and merge happen when you ask.
* The version is still 0.0.7. It becomes 0.1.0 when you accept the phase.
* Six new discussion points, 121 to 126, are open.

## What was built

* The describing code: what is said after a step, Space, C, H, repeat and history, and units and direction formats as settings. Nearby is measured to each area's nearest point.
* The command registry with the Phase 1 keys, and the session on the store and the world state. F1 for the focused region, Shift+F1 the key describer, F2, F3 and F4 to the regions, key changing with a warning that names the command that has the key. Copying the coordinates was dropped, as you answered in DP113.
* The map scene from the pack, with the zoom as a distance, and seams along the 180 degree line and the South Pole that are never outlined.
* The desktop shell: four regions, a panel that is changed in place, dialogs with Close or OK and Cancel buttons, settings kept and restored, held key behaviour, mouse, wheel, pinch and drag, a Settings menu, and the sounds.
* The web shell: the same, with the pack downloaded once into the browser's private storage, settings in the browser, and Web Audio for the earcons.
* Seven placeholder earcons, with a setting for your own files on the desktop.
* The distance curve in the core, the stereo and head-related processing on the desktop, and the listening test tool with a web version of blocks 1 and 3, a results file and an analysis.
* The test trace and Copy diagnostics.
* Packaging: the earcons and an optional base pack in the installer, a self-test option for the installed program, continuous integration steps that install, test and uninstall, a GitHub Pages workflow that runs only by hand, updated notices, and docs/release-notes.md.

## How to install and run it

* Run from the repository: `.venv\Scripts\python.exe -m desktop`. Put the base pack lite, world.pack, in `%APPDATA%\TobyMap\packs`, or run `-m desktop --pack E:\osmdata\tobymap\output\world\world.pack`.
* Installer: `.\packaging\build.ps1 -Pack E:\osmdata\tobymap\output\world\world.pack` makes the installer and the portable zip in dist_installer with the pack inside. I built the installer without a pack on this laptop, and the program inside it opened a test pack and started its window.
* Web: `.venv\Scripts\python.exe tools\serve_web.py`. For a pack, put it in web\packs with a packs.json beside it; the browser tests do this for the test pack.
* Listening test: `.venv\Scripts\python.exe -m tools.listening_test --name yourname`. Then `.venv\Scripts\python.exe -m tools.listening_test.analyse docs\spikes\listening-test\*.csv`.
* Checklist: docs/checklists/phase-1.md. Remake it with `tools\make_checklists.py`.

## The automatic checks, and their results

* Python tests: all pass, 600 or so, including the nine acceptance scripts (the North Pole one runs on the world pack here).
* Browser tests: all pass in Chromium and Firefox, including the held key test, F2 to F4, the tree's levels, and an axe-core check of the page, which found no serious problems.
* Step timing on the base pack lite, a walk of 1,000 steps of 1 km to 1,000 km: median 0.1 ms, 95th percentile 2 ms, slowest 8 ms, against a target of 150 ms for 95%. It is in docs/plan/p1-walk-timing.md. The walk is from a cache that fills as it goes; the first lookup in a new place took up to about 75 ms in P1-T5.
* Start-up to the first announcement on the world pack: 0.6 seconds, with no window shown.
* Map frames on the world pack, once the pack tiles are cached: 1 to 70 ms to work out. Points: 8 to about 24,000 (DP125).
* The licence check passes. Shapely was added to requirements.txt, since the store uses it. axe-core (MPL-2.0) is fetched for the browser tests only and never distributed.
* Not run: macOS, because it needs continuous integration, and the installer step in continuous integration.

## Known problems and things I could not do

* I cannot hear or use NVDA. Everything about how things sound and read is on your checklist: the level NVDA says for panel items, whether it reads the item F3 lands on, Braille, whether the tick and blocked sounds are right, and the listening test.
* The held key behaviour is tested with key events, not with NVDA. If NVDA still falls behind, the test trace (Help, Copy diagnostics) shows where.
* The acceptance scripts use places in the small test pack. On the base pack lite, Kent is only "England, United Kingdom" (DP121).
* Block 5 of the listening test needs the Piper voice in voices/piper. It is there on this laptop, and the block loads it for about 5 seconds when it starts. Elsewhere the block is skipped with a spoken message.
* The widest map views have about 24,000 points (DP125).
* Your own sound files work only on the desktop (DP123).
* Obsolete Phase 0 code is still in the repository, because I may not delete files without asking (DP122).
* The world pack has not been rebuilt, so the West Bank and the Ilemi Triangle still say "Unclaimed".
* The architecture document was not updated for the new modules; the explanation document has two new sections, and the glossary has new words.

## What was not tested

* NVDA on the desktop, and in Firefox and Chrome.
* A Braille display.
* Installing on a clean computer. Continuous integration does it on its first run.
* The web version on GitHub Pages, and downloading a 126 MB pack over the internet.
* The listening test with real ears.

## Your acceptance

Not yet. When you have tried the checklist, put your comments in the discussion points file or a text file, against the requirement IDs. When you accept, I ask whether you want to publish (DP110), bump the version to 0.1.0, and make the release.
