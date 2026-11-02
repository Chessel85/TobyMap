# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project

TobyMap (local folder `Mapping`, GitHub repository `Chessel85/TobyMap`) is an accessible map for blind and partially sighted people. You step around the world and hear where you are, with spatial sound, a screen reader and Braille. It has a desktop version (PySide6) and a web version (Pyodide in a browser worker), built from one shared Python core.

The product owner (PO) is blind and uses NVDA on Windows 11. There is no human developer. Everything written for the PO, including docs, reports, findings and command output, must suit a screen reader: real headings, short lists, no tables where a list will do, and no meaning carried only by layout or colour.

## Read before changing anything

The detail lives in `docs/design/`:

* `requirements catalogue.md`: the requirement IDs (such as NAV-1), with acceptance criteria. This is the authority.
* `user experience description.md`: how the application behaves.
* `architecture.md`: the technical design and decisions AD-1 onwards. Read the relevant section before touching an area.
* `implementation plan.md`: phases, tasks (such as P0-T5), working rules, and the definitions of done.
* `artefacts.md`: what goes where in this repository.
* `data sources.md`: every data source and its licence.
* `Discussion points.csv`: questions between Claude Code and the PO (see below).
* `glossary.md`: the meaning of each word used in reports, findings, documents and answers to the PO. Follow it for everything written for the PO, including text that code prints into build reports. Never use "piece", "box" or "tile" on their own. If a new idea needs a word, add it to the glossary first.
* `explanation.md`: plain-language explanations of how parts of TobyMap work, one section per topic. When the PO asks how something works, the answer usually belongs here as a new section.
* `high level requirements.md` and `target users.md` belong to the PO. Never rewrite them.

Current progress is in `docs/plan/phase-N.md`. Spike findings are in `docs/spikes/`.

## Where things are in the code

* `mapcore/session.py`: the one object both shells talk to. Commands in, responses out (AD-2).
* `mapcore/commands/registry.yaml`: every command, its key, region and menu (AD-3).
* `mapcore/describe/templates.yaml`: every word the application says or shows, including region names (3.4). The approved wording is held in `tests/mapcore/test_session.py`.
* `mapcore/render/globe.py`: the orthographic globe and the shape list the shells paint (AD-6).
* `mapcore/store/world_sample.py` and `mapcore/data/world_110m.json`: the Natural Earth stand-in for packs, until Phase 1.
* `desktop/`: the PySide6 shell. `web/`: the browser shell, its worker and `bridge.py`.
* NumPy in Pyodide is 32-bit. Use `np.intp` for any array of offsets or indexes, never `np.int64`.

## Commands

Windows, Python 3.14 (the version the current Pyodide runs), in `.venv`:

```powershell
.\setup.ps1 -Pipeline -Build                 # one-off set-up: venv, packages, browsers, licence check
.venv\Scripts\python.exe -m pytest --ignore=tests/web                  # Python tests
.venv\Scripts\python.exe -m pytest tests/web --browser chromium --browser firefox   # browser tests
.venv\Scripts\python.exe tools\check_licences.py                       # licence check (SCP-4)
.venv\Scripts\python.exe -m mapdata status                             # where the data folder is
.venv\Scripts\python.exe tools\fetch_vendor.py                         # Pyodide (web) and NVDA Controller Client (desktop), not in git
.venv\Scripts\python.exe -m desktop                                    # run the desktop application
.venv\Scripts\python.exe tools\serve_web.py                            # stage the core and serve the web version locally
.\packaging\build.ps1                                                  # Windows installer and portable zip, into dist_installer
.venv\Scripts\python.exe -m mapdata fetch land-polygons                # download a source into <data>/tobymap/downloads
.venv\Scripts\python.exe -m mapdata spike-s2-stage1                    # spike S2 stage 1 build and report, into <data>/tobymap/output
.venv\Scripts\python.exe -m mapdata inspect <pack> <lat> <lon>         # what is at a point in a pack
.venv\Scripts\python.exe tools\spikes\s1\demo.py                       # spike S1 sound demo (requirements-spikes.txt)
.venv\Scripts\python.exe tools\spikes\s6\demo.py                       # spike S6 voice demo (requirements-spikes.txt)
.venv\Scripts\python.exe tools\spikes\s3\run.py                          # spike S3 hosting and storage tests in Chromium, Firefox, Edge (--serve for your own browser)
```

The browser tests stage the core into `web/py` themselves and need Pyodide in `web/vendor`. Each test starts Pyodide afresh, so they take about five minutes.

Continuous integration (`.github/workflows/ci.yml`) runs the Python tests on Windows and macOS, and the browser tests in Chromium and Firefox, on every push.

## Rules that are never broken

These come from implementation plan section 1.3 and the architecture:

1. **The core (`mapcore/`) never imports PySide6, `desktop`, or anything that cannot run in Pyodide.** This is guarded by `tests/mapcore/test_core_rules.py`, which runs in a subprocess.
2. **No logic is copied between the desktop and web shells.** If both need it, it goes in the core (AD-1).
3. **Every command is defined in the command registry**, and no shell adds its own key handler for a command (AD-3).
4. **No announcement text is written in a shell.** It comes from the core's templates (3.4).
5. **Tests never open a window, an audio device or a network connection.** `tests/conftest.py` forces `QT_QPA_PLATFORM=offscreen`. The only exception is the browser tests, which talk to a local server.
6. **Escape is never required.** Every dialog has a Close or Cancel button (ACC-7).
7. **No dependency is added without a licence check.** Run `tools/check_licences.py`. Code is GPL-3.0, so licences must be compatible. Packs are ODbL.
8. **No drive letter or personal folder goes in code or shared configuration** (AD-18). The data folder comes from `--data`, `MAPDATA_ROOT`, or `mapdata/config/paths.yaml`, which is local and not in git.
9. **The data folder is shared with the PO's own files** (drive E: on the PO's laptop). mapdata reads source files there but writes only inside its own `tobymap` subfolder. Never delete or overwrite anything else in the data folder. Ask the PO first (DP75).
10. **Large binary files, such as packs, OSM extracts, sounds and voices, are never committed.** See `.gitignore`.

## Discussion points

`docs/design/Discussion points.csv` has 8 columns: ID (a plain number), Category, Question, Why, Suggestion, Priority, PO Response, Status.

* Records end with CRLF, line breaks inside fields are LF, and there is no BOM.
* Python's `csv.writer(f, lineterminator='\r\n')` round-trips it byte for byte.
* New points get the Status "Open" and continue the numbering.
* The PO answers in the PO Response column, and points are then marked "PO responded".

## Working method

* Each task has an ID, such as P0-T5. Name branches and commits after it, and list the requirement IDs in the commit message.
* Write the tests first where the task changes behaviour.
* The PO sees a phase only after continuous integration is green.
* The PO gives feedback in text files or in the discussion points file.
* Bash heredocs containing quotes break in this environment. Write scripts to a scratch file first, then run them.

## Git

* Commit and push when the PO asks.
* Never force-push, and never use `reset --hard` or delete files you did not create, without asking first.
