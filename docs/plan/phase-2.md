# Phase 2 task list

Phase 2 is orientation, layers and sound. The tasks are described in "implementation plan.md", section 5, version 0.5, and in detail in phase-2-plan.md, which also raises DP142 to DP146 and splits each task into work items, each labelled Opus or Sonnet. This list shows what is done.

Started on 5 November 2026, after you accepted Phase 1.

## Start of the phase

* [x] P2-T0a Versions: check for newer PySide6 and Pyodide, and upgrade if every test passes. Done on 5 November 2026: PySide6 6.12.0 and Pyodide 314.0.7 are still the latest, so nothing was upgraded.
* [x] P2-T0b Delete the obsolete Phase 0 code (DP122). Branch p2-t0-remove-phase0. Deleted: mapcore/store/world_sample.py, mapcore/geo/phase0_words.py, mapcore/data/world_110m.json, mapdata/stages/world_sample.py with its world-sample command, and the tests that covered only them (test_phase0_words, test_world_store, test_world_sample). Kept, with the reason: the GlobeGeometry and build_scene code in mapcore/render/globe.py, because spike S2 (mapdata/stages/s2_stage.py) and test_s2_faster still use it. The globe, geodesy tests now use small made-up countries instead of the Natural Earth file.
* [x] P2-T0c The key list: every command, its key now, the key proposed, and a column for the key you want, as a CSV file (DP109). Branch p2-t0-key-list. The file is docs/plan/phase-2-keys.csv, made by tools/make_key_list.py. It has 59 lines, plus a Notes column. You filled in "Your key" and settled the clashes. The one existing command whose key changed, Repeat the last announcement (now Shift+Space), is in the registry. The keys of the new commands go in with each task that adds the command, so no command exists without its behaviour. The key clash test (ACC-4) runs on them then. The script will not overwrite a file that holds your keys unless given --force.

## Tasks

* [x] P2-T14 Holding an arrow key: the clicks never wait for the map to be drawn, then the drawing is made faster (DP140). Branch p2-t14-held-key. Done on 5 November 2026:
  * P2-T14a: the clicks keep their own time. On the desktop, the map is drawn in the background, and a clock of the window's own makes each step and its click at the time the core gives. Qt's own timers keep to Windows' 15.6 ms beat, so the clock is a small thread that sleeps until each step is due. In the web version, the page plays each click on the sound card's own clock at its due time, without waiting for the core. While a key is held, the map is drawn at most 4 times a second (a new setting in the Movement tab), and the Information panel and Details wait for the release. With a stand-in drawing of 200 ms, every click of a 3 second hold is within 10 ms of its due time, on the desktop and in Chromium and Firefox.
  * P2-T14b: each drawing's three parts are timed in the trace. Where the time goes is in docs/plan/p2-t14-drawing-timing.md, made by tools/time_drawing.py and tools/time_drawing_web.py.
  * P2-T14c: the slowest part was choosing the shapes the first time a place is drawn, when the pack tiles are decoded. Two approaches were tried. Decoding all the shapes of a pack tile together was kept: it makes the slowest drawings 3 to 5 times quicker. Reading ahead in the background was not kept, because it did not help the first drawing.
* [ ] P2-T1 Orientations and turning: north-fixed, cardinal facing and free facing, the F key, turning, typing a bearing, and crossing the poles.
  * [x] P2-T1a Stepping in the three orientations (Opus). Done on 5 November 2026. In cardinal and free facing, Up moves forward and Down back, and Left and Right turn. Cardinal facing east or west follows the line of latitude; north or south it follows the meridian and carries on over the pole, facing the other way. Free facing follows the shortest line on the ellipsoid. Moving back keeps facing the same way. Switching orientation never moves you. Going over a pole says "Crossed the North Pole. Now facing south." Turning says the new heading, such as "Facing 5 degrees."; held, it ticks and says the heading on release. Two new settings in the Movement tab: Left and Right turn 5 degrees in free facing, and Ctrl with them 1 degree, from your key list. NAV-3 says 15 degrees, so DP147 asks you which is right.
  * [x] P2-T1b Directions relative to the way you face (Opus). Done on 5 November 2026. In north-fixed, Nearby says compass directions as before. In cardinal and free facing, it says them relative to the way you face, in your bearing format: "ahead", "ahead right", "to your right", "behind left" and so on with compass points; "2 o'clock" with the clock face; "47 degrees to your right" with degrees. One rule, formats.relative_bearing, is used for the words now and for the sound later.
  * [ ] P2-T1c Commands, words and the bearing dialog (Sonnet). Notes for it: the core already has session._turn(sign=1 or -1) for the 90 degree turn and session._turn("fine_turn_deg", sign) for the fine turn, world.next_orientation() for the orientation key, and world.face(bearing) for a typed bearing. Your keys: O, Shift+Left and Shift+Right, Ctrl+Left and Ctrl+Right, Ctrl+B. The arrow keys' labels, "Step north" and so on, need words for the facing orientations. The web page's held-key clicks come from hold_info(), which counts only moves, so a held turn has no clicks in the web version yet.
  * [ ] P2-T1d The same in the web version (Sonnet).
  * [ ] P2-T1e The heading on the map (Sonnet). The core already sends the heading with every drawing.
  * [ ] DP147 answered.
* [ ] P2-T2 Position history and going to coordinates, in every NAV-8 format (DP142).
* [ ] P2-T15 Going back to a place from the announcement history, with Enter (DP141).
* [ ] P2-T3 Layer catalogue: the layers list (Shift+L), and a layer that is off is gone from sight and sound.
  * [x] P2-T3a Layers in the core (Opus). Done on 5 November 2026. The layer catalogue, mapcore/layers, is made from the layer definitions in the packs, with your changes on top, kept with the settings by layer id. A layer that is off is gone from "where am I", the announcement after a move, Nearby, the mouse and the map. Where every layer at a point is off, you hear "Every layer here is switched off". The layer files now say each layer's group, geometry, whether it starts on, its zoom range, its minimum size and its sounds (docs/data-manager/configuration.md). These go only into the pack's writing, so the world rebuild keeps the areas it has already made: checked against the kept results on drive E, the first three stages are reused and only the writing and the checks run.
  * [ ] P2-T3b The layers dialog on the desktop (Sonnet). Notes for it: session.layer_list() gives the groups and layers, and the command layers.set, with layer, field and value, changes one thing. Your key is Ctrl+Shift+L.
  * [ ] P2-T3c The layers dialog in the web version (Sonnet).
* [ ] P2-T4 The visible rule: zoom ranges, the area size rule, and the view.
* [ ] P2-T10 Graticule and special lines, written into the world pack, and the world rebuild.
  * [x] P2-T10a Line features in packs and the store (Opus). Done on 5 November 2026. Pack format 3 adds tile entries for lines and points; format 2 packs, such as the Phase 1 world pack, still open. The pipeline cuts lines and points into pack tiles and drawing tiles. The store leaves them out of "where am I", finds them in Nearby, and has crossed_lines(path), which lists the lines a step's path crosses in order, across the 180 degree line and over a pole. The map draws lines, and points as small round markers, on the desktop and the web. docs/developer/pack-format.md is version 3.
  * [x] P2-T10b The graticule stage (Sonnet). Done on 5 November 2026: stage graticule, layers graticule and special-lines in mapdata/config/layers/graticule.yaml, source naturalearth-geographic-lines, all in the world pack's settings (not yet built; P2-T10d). Notes for it: write each line with its points at most 1 degree apart, because the map draws straight between points; a line across the 180 degree line is stored as its two sides; give the layer geometry: line and switched_on: false in its layer file.
  * [ ] P2-T10c Samples for the test pack (Sonnet).
  * [ ] P2-T10d The world rebuild (Opus). After P2-T10b. Only the writing and the checks should run, so it should take well under the 30 to 90 minutes first estimated.
    * Before the build, two things from P2-T10b to do first. One: run `mapdata fetch naturalearth-geographic-lines`, then run the real date line through the graticule stage and check that it runs pole to pole, has its two sides at 180 degrees, has no gap over 1 degree, and that the feature is found by its name (the code looks for "date line" in the name fields; it has only been tested on a made-up file). Two: adding the graticule layers to the world pack changes every stage's fingerprint, because fingerprints include all the pack's layers, so the build may rerun every stage and not only the writing. Check this with a dry look at the fingerprints, and if it is so, change the fingerprint to leave out layers a stage does not use, before the heavy run.
  * [ ] P2-T10e Interval and crossing sounds (Sonnet).
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
