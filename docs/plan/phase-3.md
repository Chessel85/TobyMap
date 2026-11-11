# Phase 3 task list

Phase 3 is information, hierarchy and search, with the complete base pack. The tasks are described in "implementation plan.md", section 6, and in detail in phase-3-plan.md, which also raises DP167 to DP174 and splits each task into work items, each labelled Opus or Sonnet. This list shows what is done.

Started on 10 November 2026, after you accepted Phase 2 and answered DP167 to DP174. The plan is version 0.2, with your answers.

## Start of the phase

* [x] P3-T0a Versions: check for newer PySide6 and Pyodide, and upgrade if every test passes. Done on 10 November 2026: PySide6 6.12.0 and Pyodide 314.0.7 are still the latest, so nothing was upgraded.
* [x] P3-T0b The questions left from Phase 2: publishing 0.1.1 (DP110), and DP150. DP167 to DP174 were added to the discussion points file with the plan. Done on 10 November 2026: you chose no release of 0.1.1, so I ask again at the end of Phase 3; and the web voice's half second before a label felt fine, so DP150 needs no change.
* [ ] P3-T0c The key list for Phase 3: docs/plan/phase-3-keys.csv, with the clashes marked (T, O).
  * Made on 10 November 2026 by tools/make_key_list.py, which now takes --phase and writes in the Notes column any proposed key already used where they would meet, or kept by a screen reader or browser (tests/data/forbidden_keys.yaml). 84 lines: 65 commands you have now, and 19 new ones. None of the keys proposed clashes: the world tree is W, as T is the theme, and the new groups are Shift+4 to Shift+8, after the three you know. Waiting for your keys in the "Your key" column.
  * Your keys arrived on 10 November 2026. Most are as proposed. Changes and notes, each settled with the task that adds the command:
    * M switches between stepping and hierarchy mode, in place of 1 and 2 (P3-T6). M was also proposed, and kept by you, for measuring (P3-T7), so one of them needs another key: asked when P3-T6 is done.
    * Ctrl+Shift+W for the Wikipedia article (P3-T5) closes the whole window in Chrome and Firefox, and a page cannot stop it, so it cannot be used in the web version. Ctrl+Shift+W is now in tests/data/forbidden_keys.yaml. Another key asked when P3-T5 is done.
    * Measuring, distance to a found feature, search in the browsers, and the world tree: you want to know more about each first. Each is explained, and its key confirmed, when its task is done.
* [x] P3-T0d Samples for the test pack: Hampshire, the New Forest, Switzerland and its neighbours, the Rhine, the Bay of Biscay, and places with shared names.
  * Done on 10 November 2026. Six samples in tests/samples/osm, read from the planet file of 26 October 2026 by tools/make_phase3_samples.py in under a minute, and the same byte for byte when made again. tests/samples/README.md describes each.
  * In the test pack now: Hampshire and Wiltshire whole, with England and the counties round them; Switzerland, Liechtenstein and the four larger neighbours; and the Rhine from Basel to Schaffhausen.
  * Waiting for the layers of the work items that use them: the New Forest National Park (95% in Hampshire, 5% in Wiltshire), the Bay of Biscay (an area in OpenStreetMap), and places with shared names: two Parises, two Portlands, two Newports, and São Paulo the city and the state.
  * tests/mapcore/test_samples_phase3.py checks where you are in each new sample, that France stays one area from the Channel to the Alps, and that a step north at Rheinfelden crosses the Rhine from Switzerland into Germany.
* [x] P3-T0e The implementation plan, version 0.6. Done on 10 November 2026: the changes are listed at the top of "implementation plan.md", and section 6 now has the start tasks, the carried work, P3-T17 and P3-T18, and national parks moved to Phase 4.
* [x] P3-T0f Four more step sizes, 2.5, 10, 50 and 500 km (DP166). Done on 10 November 2026: the metric step list has 2.5, 10, 50 and 500 km, and the imperial list 400 yards (a quarter of a mile is said as 0.3), 2.5, 10, 50 and 500 miles, so linked Page Up changes the step on every press from 1 km to 1,000 km, and from 1 to 1,000 miles. A saved step still loads, at the nearest size. Three session tests and one window test that expected the old steps now expect the new ones.

## Carried from Phase 2

* [x] P2-T17n The spatial voice stops at a key press. Done: the core sets Response.stop_voice on every response without a label; both shells stop the voice first. Tests: core, desktop, Chromium and Firefox.
* [x] P2-T17q Always say the place (DP162). Done on 10 November 2026: a new switch at the end of the Speech tab, "Say the place after every step, even when it has not changed", off at first and outside the presets, so it never makes the preset Custom. With it on, a step that changed nothing says the place instead of the tick: terse "Kent", normal "Kent, United Kingdom", detailed "Kent, England, United Kingdom". At sea, with no country, normal says the sea alone. "Say nothing, only the tick" still only ticks. A held key still clicks, and only the place where you let go is said. Both shells show it with no change of their own, as the Speech tab comes from the core. The user experience description is version 0.21 (section 3.1). Tests: 12 new core tests and 1 changed.
* [x] P2-T17u The listening test for sound in space and the voice (DP164). You ran it on 10 November 2026; the findings are in docs/spikes/listening-test/compass-findings.md.
  * Every one of your 32 answers was within one compass point, and none mixed up front and back, in any model. Right exactly: as now 7 of 8, HRTF 5 of 8, twice the lower pitch 8 of 8, more muffling 8 of 8. How easy: as now 4, HRTF 2, twice the lower pitch 2, more muffling 3, out of 5. The voice 3 out of 5 in every model.
  * Proposed: keep stereo with a lower pitch behind, as now. One answer in eight is chance, and you found it the easiest. HRTF stays a choice in Settings, but not the first.
  * Built on 10 November 2026: tools/listening_test/compass.py. It runs in the command window, with no window of its own, on your headphones, facing north. Run it with: .venv\Scripts\python.exe -m tools.listening_test.compass
  * Four blocks of eight, one block for each sound model: stereo with a lower pitch behind, as now; HRTF with a lower pitch behind; stereo with twice the lower pitch behind (the sound 6 semitones lower instead of 3, the voice 3 instead of 1.5); and stereo with more muffling behind. No echo.
  * Each of the eight compass points once in each block, in a mixed order. Each is the item's direction sound, then a name and "30 kilometres" in the Alba voice from the same place, as Hear its direction plays them. The names are only labels, and move to new compass points in each block, so a name never gives its direction away.
  * You type the compass point, such as n, ne or south west, and Enter. 0 if you can't tell, r to hear it again, q to stop. Before the first block, d plays all eight points in order. After each block, two ratings from 1 to 5: how easy it was to tell where, and how clear the voice was. About 15 minutes.
  * --rate sets the voice's speed in percent, as in your settings, for example --rate 200.
  * Your answers are saved after each one, in docs/spikes/listening-test, in a file starting "compass". When you have run it, tell me, and I write the findings with --analyse and propose the settings.
  * Tests: 27 new, in tests/mapcore/test_listening_compass.py, with a stand-in voice and no sound device. Also checked with the real Alba voice: each sound and its name take about 2.4 seconds, made in about 130 ms.
* [x] P2-T17v The map for sighted users: the special lines made to stand out, and a setting for when the current area is outlined. The line across France is fixed (P2-T17v-c).
  * The special lines: a new layer setting, line_style: special, in mapdata/config/layers/graticule.yaml and in the pack. A special layer's lines are drawn thicker, in the theme's special line colour, on top of the other lines. Both versions, as the core makes the drawing.
  * The world pack written again on 10 November 2026 to carry it: only "writing the pack" ran, in 34 minutes, and the checks.
  * Outline the current area: a new setting in the Display tab, with always (at first), not for the oceans, never for oceans and seas, and never.
  * The line across France: an edge along a pack tile edge was outlined when the point before it was merged away. Such a point is now kept.
  * Found on the way, not changed: at 0 degrees north and 0 degrees east, the North Atlantic has a small square of its own, about 1 degree across, which is outlined when the North Atlantic is the current area. It is in the ocean data from VLIZ, or in how it is cut; to look at with P3-T1b.
  * To check: switch on the special lines in the layers list (Shift+L), in each theme; and try each choice of "Outline the current area" in the North Sea.
  * Tests: 18 new in tests/mapcore/test_map_for_sighted_users.py, and 1 in tests/mapcore/test_scene.py.

## Tasks

* [ ] P3-T1 The complete base pack: the size trial, named seas, counties, islands, continents, mountains, rivers, lakes, roads, railways, towns, a faster writing stage, and the world build.
  * [x] P3-T1a The size trial, first round, with counties. Done on the night of 10 to 11 November 2026: docs/plan/p3-t1-size-report.md. Counties for the whole world add about 170 MB (likely 135 to 210), so the world pack would be about 295 MB; start-up, memory and the first place said hardly change, on the desktop and in both browsers. Checked on 7 more regions. Your decision on counties is DP175. The run switch now pauses on anything but yes. Tests: 4 new in tests/mapdata/test_grid.py, 1 new and 2 changed in tests/mapdata/test_pipeline.py.
  * [x] P3-T1b Named seas, bays and straits. Done on 11 November 2026, in the trial: the IHO Sea Areas are still non-commercial, so the seas are Natural Earth's marine areas, a new layer "Seas, bays and straits" below the oceans; and OpenStreetMap's named seas, bays and straits are a new layer of places, "Bays and straits, as places", read by a new stage, osm-places. North of Santander you hear "Bay of Biscay, North Atlantic Ocean". All 49 check places pass, 19 of them new sea places. About 30 to 40 MB for the world. The results are in docs/plan/p3-t1-size-report.md. DP175 is done too: PCK-1's soft limit is about 400 MB (requirements catalogue version 0.16, phase 3 plan version 0.3). Tests: 5 new in tests/mapdata/test_grid.py, 3 in the new tests/mapdata/test_osm_places.py, 1 new in tests/mapcore/test_samples_phase3.py, and 5 changed for the new layer.
  * [x] P3-T1c Counties for the whole world. Done on 11 November 2026, in the trial: the planet read sets each country's county areas aside on disk and sorts them a country at a time, so the world build needs no whole-world cover test. Western Europe: 23.7 MB, 3,990 counties, all 49 check places pass, and France now has counties. South America: 9.3 MB, 3,293 counties. A county sharing an id with a region now gets the ending "#as-county". The world build will reread the planet (about 16 minutes), as the counties record changed. Tests: 10 new in tests/mapdata/test_counties_world.py. The results are in docs/plan/p3-t1-size-report.md.
  * Still to look at: the small square of the North Atlantic at 0 degrees north and 0 east, found in P2-T17v, needs the world build to check.
* [ ] P3-T17 Tiers, and constituent countries (DP165).
* [ ] P3-T2 Facts from Wikidata, Wikipedia links, and disputed areas.
* [ ] P3-T3 Relationships in the pipeline: containment, neighbours, overlaps, crossings, and the water hierarchy.
* [ ] P3-T4 The Information panel: all eight groups, sorting, typing to jump, and the item actions.
* [ ] P3-T5 Details and Wikipedia.
* [ ] P3-T6 Hierarchy mode.
* [ ] P3-T7 Measuring.
* [ ] P3-T8 Search.
* [ ] P3-T9 The world tree and browsing by category.
* [ ] P3-T16 Lists of disputed and unclaimed areas.
* [ ] P3-T10 The query builder.
* [ ] P3-T11 Look around.
* [ ] P3-T12 Languages of names.
* [ ] P3-T13 The pack manager, first version.
* [ ] P3-T14 Quality reports and publishing.
* [ ] P3-T18 Controls for sighted users (DP165).
* [ ] P3-T15 Help.

## Closing the phase

* [ ] The checklists for the desktop, the web and a sighted helper.
* [ ] The phase report, docs/plan/phase-3-report.md.
* [ ] Your acceptance.
* [ ] The question about publishing (DP110).
