# Phase 0 task list

Phase 0 is Foundations and spikes. The tasks are described in "implementation plan.md", section 3. This list shows what is done.

## Tasks

* [x] P0-T1 Repository: TobyMap created, with the licence, README, CLAUDE.md, .gitignore, the folder layout, and the design documents in docs/design.
* [x] P0-T2 Continuous integration: Python tests on Windows and macOS, browser tests in Chromium and Firefox, and the licence check.
* [x] P0-T3 Development set-up: requirements files, setup.ps1, and the data folder setting. The PO's local paths file points at drive E:.
* [x] P0-T4 Spike S1, spatial sound. Six engines compared on 1 November, including Synthizer and OpenAL Soft; stereo with pitch scored best. Decided (DP100): stereo with pitch by default and HRTF with pitch as an option, from our own processing; recorded in AD-10. Findings: docs/spikes/S1-spatial-sound.md. The web version by ear, and sound while moving, are tested in Phase 1.
* [x] P0-T5 Spike S2, countries, coastlines and islands. Stage 1 (the UK, France and Spain) complete on 1 November: 22 of 22 coastline places pass, every layer meets exactly after cleaning and simplifying. Findings: docs/spikes/S2-countries-coastlines.md. Discussion point 101 answered: the counties rule and record are built. Stage 2 (Norway and Sweden) complete on 2 November, every check passed. Stage 3 (the 180 degree line and the South Pole) complete on 2 November: 27 of 27 places pass after the confirming run, which took 13.1 minutes with 6 workers, against 75.7 minutes before. Antarctica's area is 1.7% over Wikidata's figure, probably because the ice shelves are counted. Stage 4 (Argentina), added by the PO, is parked. Discussion point 103 (using the laptop's cores) answered and actioned: worker pools for cutting, layer checks, packs and pictures, a memory-aware pool, and --away. The faster algorithms are done. Follow-ups on Fiji's and Kiribati's areas and Russia's 864 km2 done; DP104 answered. Complete on 2 November: stage 1's whole-run comparison and stage 4 (Argentina) moved to Phase 1, task P1-T16, by the PO.
* [x] P0-T6 Spike S3, hosting and browser. Tested on 2 November in Chrome, Firefox and Edge, and in the PO's own Firefox: GitHub Releases is blocked for web pages; Hugging Face works, but each read takes about 0.4 seconds; private storage allows about 10 GB. Nothing was published (the PO's choice). Decided (DP102): packs on GitHub Releases for the desktop and a copy on Hugging Face for the web, downloaded whole into private storage; recorded in AD-9 and PCK-4. Findings: docs/spikes/S3-hosting-browser.md.
* [x] P0-T7 Spike S4, core in Pyodide. Complete on 2 November: the core's pack reader runs unchanged in Chrome and Firefox, reading the S2 stage 2 pack from private storage, 18 of 18 places right. Decoding compact coordinates now uses NumPy, which brought the slowest lookup from 168 ms to 49 ms in the browser (target 150 ms). Start-up about 4 seconds, 16.5 MB download. AD-9 confirmed. Findings: docs/spikes/S4-core-in-browser.md.
* [x] P0-T8 Spike S5, globe, accessible shell and installer. Findings: docs/spikes/S5-globe-shell-installer.md. Five NVDA tests done. Known limitation on the desktop: after Shift+Space or R, NVDA doesn't read the new item until Up then Down (fifth test, 2 November); to be tried again in Phase 1.
* [x] P0-T9 Spike S6, spatial voice. The PO chose Piper with the Alba voice; eSpeak NG ruled out. Piper in the browser done on 2 November: Alba runs in a worker in Chrome and Firefox, with ONNX Runtime Web and eSpeak NG for the phonemes, placed in space with Web Audio. A first visit downloads about 60 MB compressed; the voice is ready about 4 to 5 seconds after it starts loading. Each label takes about 380 ms from request to sound with one thread, 220 ms with four, against 100 ms on the desktop. Discussion point 105 (four threads in the browser) is open. Findings: docs/spikes/S6-spatial-voice.md.
* [x] P0-T10 Comparison with AtMap and AtlasDL: docs/design/lessons-from-atmap.md created from architecture section 15. Lessons from the spikes are added as they are found.
* [ ] P0-T11 Update the architecture from the findings. In progress: version 0.3 on 2 November brings in spikes S1, S3, S5 and S6 so far, and DP86 to DP102. Still to come: spike S2 stages 2 and 3, spike S4, and Piper in the browser (now measured, see P0-T9).

## Notes found while setting up

* Python 3.14, not 3.13. The current Pyodide release is numbered 314 and runs Python 3.14, so desktop, web and the build laptop all use Python 3.14. Architecture section 4.1 was updated in P0-T11.
* PySide6 6.12.0 is the latest release, and is used.
* The data folder on drive E: already had an "output" folder of the PO's from 2025. So mapdata writes only inside a new "tobymap" subfolder of the data folder, and reads the planet and UK files where they are.
* The PO's original "Solution Design" folder stays on the laptop but is not in git. The live copies of the design documents are now in docs/design.
* Spike S5 found that Pyodide's NumPy is 32-bit, so the core uses np.intp for array offsets.
* Firefox and Chrome both support ariaNotify now. Architecture 4.4 was updated in P0-T11.
* The version is 0.0.5 for the S5 test build. A draft of the phase report is in docs/plan/phase-0-report.md.
