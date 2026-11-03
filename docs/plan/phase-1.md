# Phase 1 task list

Phase 1 is the walking skeleton. The tasks are described in "implementation plan.md", section 4, version 0.4, and in detail in phase-1-plan.md, which also raises DP110 to DP114. This list shows what is done.

Started on 3 November 2026, after the PO accepted Phase 0.

## Tasks

* [x] P1-T1 Core geodesy: distance, bearing, stepping, the poles, the 180 degree line, and formatting. Done 3 November on branch p1-t1-geodesy; macOS is confirmed by continuous integration when it is pushed.
* [x] P1-T2 Pack format version 1: the writer and reader, the byte source, the manifest, checksums and version checks. Done 3 November on branch p1-t2-pack-format. Its format number is 2. The spike format, 1, was dropped at your request: the spike S2 stages, their comparison program and the spike S4 timings now use format 2, and mapdata inspect reads only format 2. The specification is docs/developer/pack-format.md. The browser tests read a pack in Pyodide in Chromium and Firefox; macOS is confirmed by continuous integration when it is pushed.
* [x] P1-T3 Pipeline skeleton: check, fetch and build commands, configuration, stage caching, progress, summary and log. Done 3 November on branch p1-t3-pipeline. The test pack is built from about 4 MB of samples in tests/samples, in 4 seconds, and continuous integration builds it on every push. Also added: the run switch, so every build reads continue.txt before each stage, stops cleanly on "no", and with --wait-for-yes carries on by itself on "yes". Of spike S2's code, only the pack writer is a pipeline stage so far; reading the planet file, cutting to the land and the checks become stages in P1-T16 and P1-T4, as they are rebuilt for the world. Stage results are kept as plain JSON and WKB files rather than GeoParquet, which would need a large new library. VLIZ's oceans hold only 10 ocean regions, not the named seas, so DP115 asks where those should come from. The guide is docs/data-manager/guide.md, with docs/data-manager/configuration.md.
* [ ] P1-T4 Base pack "lite": countries, first-level divisions, oceans and seas, and land, with no gaps (LOC-6).
* [ ] P1-T5 Store and "where am I": point queries, the pack tile cache, and the nearest point of an area for Nearby (INF-3, INF-7).
* [ ] P1-T6 World model and stepping, north-fixed.
* [ ] P1-T7 Describe: announcements, coordinates, heading, repeat and history. Nearby measured to each area's nearest point, with the Niagara Falls test.
* [ ] P1-T8 Command registry and session: F1 help, the key describer, remapping, clash tests, and F2, F3 and F4 to the regions (DP106).
* [ ] P1-T9 Map scene: the projection, the shape list, the centre cross, the heading arrow and the current outline.
* [ ] P1-T10 Desktop shell: the four regions, settings, and the stand-in audio. No backlog of speech after a held key (ANN-3), and the panel's levels read by NVDA (INF-10).
* [ ] P1-T11 Web shell: the same, in the browser, with the held key test.
* [ ] P1-T12 Earcons.
* [ ] P1-T13 Listening test tool.
* [ ] P1-T14 Packaging: the installer, the portable zip, the web version on GitHub Pages, and the first GitHub release when the phase is accepted.
* [ ] P1-T15 Diagnostics: the test trace and "copy diagnostics".
* [ ] P1-T16 Carried over from spike S2: build speed first (DP107), then stage 1's comparison, stage 4 (Argentina), areas held twice (DP104), inland water in the area check, and the wider overlap check. In progress on branch p1-t16-build-speed. The counties step's trials are done (3 November): of four methods, gap-land is the fastest. Mainland France's counties take 2.2 minutes, against more than 15 with spike S2's method, and give the same counties. The whole Belgium stage takes 18 seconds, with no step slow enough for its own trials. Argentina, which the method was not tuned on, took 2.3 to 2.5 minutes for 5.1 times France's land, well inside its share, with the same counties as nearby-gap. Argentina's counties showed that the counties rule misses level 5 (DP116). The trials are written up in the S2 findings, "Phase 1: build speed trials". Mainland France's regression run is dropped at the PO's request, because France was used to develop the method.

## Suggested order

1. P1-T1 and P1-T2, the core's geodesy and pack format, which everything else uses.
2. P1-T3, the pipeline skeleton.
3. P1-T16's build speed work, on Belgium, with mainland France as the regression test (DP107). The PO is told before any heavy run.
4. P1-T4, the base pack, built with the faster methods.
5. P1-T5 to P1-T9, the core's store, stepping, wording, keys and map scene.
6. P1-T10 and P1-T11, the two shells, then P1-T12 and P1-T13, the sounds and the listening test.
7. P1-T15, diagnostics, then P1-T14, packaging, last.
8. The rest of P1-T16, such as stage 4, when the laptop can be left for heavy runs.

## Notes at the start of the phase

* PySide6 6.12.0 and Pyodide 314.0.7 are still the latest releases, checked on 3 November, so nothing is upgraded.
* Discussion points 106 to 108 are answered and built into the plan. DP109, whether the Information panel's groups keep their own keys, is open; it holds nothing up in Phase 1.
