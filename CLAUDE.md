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
* `high level requirements.md` and `target users.md` belong to the PO. Never rewrite them.

Current progress is in `docs/plan/phase-N.md`. Spike findings are in `docs/spikes/`.

## Commands

Windows, Python 3.14 (the version the current Pyodide runs), in `.venv`:

```powershell
.\setup.ps1 -Pipeline -Build                 # one-off set-up: venv, packages, browsers, licence check
.venv\Scripts\python.exe -m pytest --ignore=tests/web                  # Python tests
.venv\Scripts\python.exe -m pytest tests/web --browser chromium --browser firefox   # browser tests
.venv\Scripts\python.exe tools\check_licences.py                       # licence check (SCP-4)
.venv\Scripts\python.exe -m mapdata status                             # where the data folder is
```

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
