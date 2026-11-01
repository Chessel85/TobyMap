# Phase 0 task list

Phase 0 is Foundations and spikes. The tasks are described in "implementation plan.md", section 3. This list shows what is done.

## Tasks

* [x] P0-T1 Repository: TobyMap created, with the licence, README, CLAUDE.md, .gitignore, the folder layout, and the design documents in docs/design.
* [x] P0-T2 Continuous integration: Python tests on Windows and macOS, browser tests in Chromium and Firefox, and the licence check.
* [x] P0-T3 Development set-up: requirements files, setup.ps1, and the data folder setting. The PO's local paths file points at drive E:.
* [ ] P0-T4 Spike S1, spatial sound. In progress: the PO listened to the own HRTF processing on 1 November; Synthizer and OpenAL Soft are being added, with the PO's permission. Draft findings: docs/spikes/S1-spatial-sound.md.
* [ ] P0-T5 Spike S2, countries, coastlines and islands. In progress: stage 1 (the UK, France and Spain) built with mapdata spike-s2-stage1; the run stopped for low memory and resumes when the laptop is idle. Findings: docs/spikes/S2-countries-coastlines.md. Later stages wait for the PO's review.
* [ ] P0-T6 Spike S3, hosting and browser.
* [ ] P0-T7 Spike S4, core in Pyodide.
* [x] P0-T8 Spike S5, globe, accessible shell and installer. Findings: docs/spikes/S5-globe-shell-installer.md. Two NVDA tests done; say current line in Firefox and DP97 still open.
* [ ] P0-T9 Spike S6, spatial voice. In progress: the PO chose Piper with the Alba voice; eSpeak NG ruled out. Piper in the browser waits for DP98 and spike S4. Draft findings: docs/spikes/S6-spatial-voice.md.
* [x] P0-T10 Comparison with AtMap and AtlasDL: docs/design/lessons-from-atmap.md created from architecture section 15. Lessons from the spikes are added as they are found.
* [ ] P0-T11 Update the architecture from the findings.

## Notes found while setting up

* Python 3.14, not 3.13. The current Pyodide release is numbered 314 and runs Python 3.14, so desktop, web and the build laptop all use Python 3.14. Architecture section 4.1 will be updated in P0-T11.
* PySide6 6.12.0 is the latest release, and is used.
* The data folder on drive E: already had an "output" folder of the PO's from 2025. So mapdata writes only inside a new "tobymap" subfolder of the data folder, and reads the planet and UK files where they are.
* The PO's original "Solution Design" folder stays on the laptop but is not in git. The live copies of the design documents are now in docs/design.
* Spike S5 found that Pyodide's NumPy is 32-bit, so the core uses np.intp for array offsets.
* Firefox and Chrome both support ariaNotify now. Architecture 4.4 will be updated in P0-T11.
* The version is 0.0.2 for the S5 test build.
