# Phase 2 task list

Phase 2 is orientation, layers and sound. The tasks are described in "implementation plan.md", section 5, version 0.5, and in detail in phase-2-plan.md, which also raises DP142 to DP146 and splits each task into work items, each labelled Opus or Sonnet. This list shows what is done.

Not started yet. The plan was written on 5 November 2026, after you accepted Phase 1.

## Start of the phase

* [x] P2-T0a Versions: check for newer PySide6 and Pyodide, and upgrade if every test passes. Done on 5 November 2026: PySide6 6.12.0 and Pyodide 314.0.7 are still the latest, so nothing was upgraded.
* [x] P2-T0b Delete the obsolete Phase 0 code (DP122). Branch p2-t0-remove-phase0. Deleted: mapcore/store/world_sample.py, mapcore/geo/phase0_words.py, mapcore/data/world_110m.json, mapdata/stages/world_sample.py with its world-sample command, and the tests that covered only them (test_phase0_words, test_world_store, test_world_sample). Kept, with the reason: the GlobeGeometry and build_scene code in mapcore/render/globe.py, because spike S2 (mapdata/stages/s2_stage.py) and test_s2_faster still use it. The globe, geodesy tests now use small made-up countries instead of the Natural Earth file.
* [ ] P2-T0c The key list: every command, its key now, the key proposed, and a column for the key you want, as a CSV file (DP109).

## Tasks

* [ ] P2-T14 Holding an arrow key: the clicks never wait for the map to be drawn, then the drawing is made faster (DP140).
* [ ] P2-T1 Orientations and turning: north-fixed, cardinal facing and free facing, the F key, turning, typing a bearing, and crossing the poles.
* [ ] P2-T2 Position history and going to coordinates, in every NAV-8 format (DP142).
* [ ] P2-T15 Going back to a place from the announcement history, with Enter (DP141).
* [ ] P2-T3 Layer catalogue: the layers list (Shift+L), and a layer that is off is gone from sight and sound.
* [ ] P2-T4 The visible rule: zoom ranges, the area size rule, and the view.
* [ ] P2-T10 Graticule and special lines, written into the world pack, and the world rebuild.
* [ ] P2-T5 Crossed and passed: along the step's path, in the background, with its earcon and its group in the Information panel.
* [ ] P2-T6 Sound scene and sound players: directions relative to the orientation, loudness, the lower pitch behind, and beyond the view.
* [ ] P2-T7 Spatial voice: labels in the Alba voice placed in space, on the desktop and the web, with history and Braille (DP143).
* [ ] P2-T8 Earcons in full: every event, each switchable, separate volumes, and your own files in the web version (DP123).
* [ ] P2-T9 Orientation beacon, to the North Pole, fading near the pole.
* [ ] P2-T11 Verbosity presets and per-event switches, and the short Braille format (DP144, DP145).
* [ ] P2-T12 Themes, the map display setting (DP108), isolate, names on the map, and heading-up.
* [ ] P2-T13 Magnifier support (DP146).

## Closing the phase

* [ ] The checklists for the desktop and the web, made from the acceptance scripts.
* [ ] The phase report, docs/plan/phase-2-report.md.
* [ ] Your acceptance, and the question about publishing (DP110).

## Suggested order

1. P2-T0a to P2-T0c.
2. P2-T14.
3. P2-T1, P2-T2, then P2-T15.
4. P2-T3 and P2-T4, with P2-T10's pipeline work and the world rebuild alongside.
5. P2-T5.
6. P2-T6, then P2-T7, P2-T8 and P2-T9.
7. P2-T11.
8. P2-T12 and P2-T13.
9. Closing the phase.
