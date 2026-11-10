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
* [ ] P3-T0f Four more step sizes, 2.5, 10, 50 and 500 km (DP166).

## Carried from Phase 2

* [ ] P2-T17n The spatial voice stops at a key press.
* [ ] P2-T17q Always say the place (DP162).
* [ ] P2-T17u The listening test for sound in space and the voice (DP164). You run it.
* [ ] P2-T17v The map for sighted users: the special lines, and the lines across France and from Sweden to Shetland.

## Tasks

* [ ] P3-T1 The complete base pack: the size trial, named seas, counties, islands, continents, mountains, rivers, lakes, roads, railways, towns, a faster writing stage, and the world build.
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
