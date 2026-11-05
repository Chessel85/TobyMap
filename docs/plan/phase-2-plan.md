# Phase 2 detailed plan: orientation, layers and sound

Version 0.1, 5 November 2026. Written by Claude Code for the product owner (PO).

This plan turns section 5 of "implementation plan.md" (version 0.5) into the work for each task, P2-T1 to P2-T15. It follows the architecture (version 0.5), the requirements catalogue, the user experience description (version 0.6), the Phase 1 report, and your answers up to DP141. The tick list of what is done will be docs/plan/phase-2.md, made when the phase starts.

## How to read this plan

* "The goal" and "Proposals and questions" are the parts most worth your attention. The questions are new discussion points, DP142 to DP146.
* "Which model does each work item" explains the Opus and Sonnet labels used throughout.
* "Order of work" says what is done when, and "Heavy runs" lists every time the laptop will be busy for a long while.
* Each task has its own level 2 heading, with the same parts in the same order: branch, requirements, what it needs first, its work items, the tests, and when it is done.
* Each task is split into work items, such as P2-T1a and P2-T1b. Each work item is small enough to be done in one session, and has its own model label.
* The last sections cover the exit checks, your acceptance checklist, closing the phase, risks, and what is left for Phase 3.

Words follow the glossary. This plan adds seven words to it: orientation, facing orientations, jump, position history, sound scene, beacon and work item.

## The goal

Moving and listening work as designed:

1. You can choose one of three orientations with F: north-fixed, cardinal facing and free facing. You can turn, type a bearing, and step over the North and South Poles.
2. You can go to typed coordinates with G, go back and forward through the places you have been with Backspace and Shift+Backspace, and press Enter on an entry in the announcement history to go back to where it was said.
3. You can switch layers on and off with Shift+L. A layer that is off is gone from the map and from everything you hear.
4. After a large step, the Crossed and passed group in the Information panel lists what the step went over, with a soft earcon when something is added.
5. Sounds come from the direction of what they belong to, relative to the way you face, louder when nearer. Spoken labels come from the same direction, in the Alba voice. The orientation beacon tells you where north is.
6. The graticule, the lines of latitude and longitude and the special lines, is a layer, with its own crossing earcons, off by default.
7. You can choose how much is said automatically, and a short Braille format.
8. A partially sighted user can choose a theme, the fill and the borders, see names on the map, and use a magnifier that follows the map centre.
9. A held arrow key gives evenly spaced clicks, however long the map takes to draw.

What Phase 2 does not do: hierarchy mode, network mode and driving (keys 2 and 3, Phase 3 and Phase 5), look around and the sweep (Phase 3 and Phase 6), search (Phase 3), pins, so the beacon points only at the North Pole until Phase 4, and rivers, roads and railways in the world pack (Phase 3). The world pack's Crossed and passed list holds areas passed over and graticule lines. Rivers, railways and stations are tried on the test pack only.

## Which model does each work item

Every work item is labelled Opus or Sonnet. Both follow the same rules and the same definition of done. The label says which model is the better choice, so the work is done well without paying for more than it needs.

Opus is chosen when a work item:

* needs a design decision the documents do not make, or must weigh several approaches
* is geometry where mistakes are subtle, such as the poles, the 180 degree line and great circles
* runs in real time or across threads, such as sound playback, the held key and the voice
* touches the screen reader or magnifier interfaces, where what NVDA does must be found out, not assumed
* is a heavy pipeline run, or changes the pack format
* measures and improves speed

Sonnet is chosen when a work item:

* follows a pattern that already exists in the code, such as a new command, template, setting or dialog
* has its behaviour fully written down here, with tests that say exactly what is right
* is documentation, a checklist, a CSV file or a list of keys
* is a second shell copying behaviour the first shell and the core already define

When a Sonnet work item hits something this plan did not foresee, it stops and writes a note in the task list, and the work item is handed to Opus, rather than guessing.

In this plan, 47 work items are labelled: 16 Opus and 31 Sonnet.

## Proposals and questions

These are my proposals where the documents leave a choice. Each one is a new discussion point in the discussion points file. None of them holds up the start of the phase.

### DP142: what goes into position history

NAV-10 asks for back and forward through recent places, like a web browser. If every step went into history, Backspace would only undo the last step, which the arrow keys already do.

* Proposal: jumps go into history, steps do not. A jump is going to coordinates, a click on the map, Enter on an announcement history entry, and later a search result or a bookmark. Before each jump, the place you are leaving is kept, with its zoom and step, so Backspace brings you back to exactly where you were, even after stepping about.
* Forward, with Shift+Backspace, goes the other way, and is cleared when you jump somewhere new, as in a browser.
* At least 100 places are kept, and they are kept when TobyMap is closed.

### DP143: what you hear in space in Phase 2

The spatial sound and the spatial voice are built in this phase, but look around, which plays the Nearby list as sound, is Phase 3 (SON-4). Without something else, the only spatial sound in Phase 2 would be the beacon.

* Proposal: bring forward "hear its direction" as an action on the items of Nearby and Crossed and passed. It plays the item's sound from its direction and distance, then says its name as a label in the Alba voice from the same place, such as "France, 34 kilometres". This lets you judge the sound design in this phase, as the acceptance gate asks.
* The key for it is chosen in the key list (see P2-T0c), and is proposed as Ctrl+Enter in the Information panel.
* Look around itself stays in Phase 3.

### DP144: what the verbosity presets say

ACC-5 asks for three presets. Proposal:

* Terse: area changes only, the smallest area that changed and nothing larger; no zoom, step or heading reports after a move; the tick still plays.
* Normal, the default: what Phase 1 does now.
* Detailed: as normal, plus the heading after every step in free facing, and the larger areas that did not change after "where am I".
* Each event can also be switched on or off on its own, whatever the preset: area change, zoom and step changes, heading, and the tick. Changing one switch makes the preset "Custom".

### DP145: the short Braille format

ACC-6 asks for a format that fits a 40-cell display. Proposal:

* The same words, in the same order every time: the new smallest area first, then the larger areas that changed, separated by a space and a slash, with no "in" or "now".
* Types are left out, and common words are shortened in a short list kept in the templates, such as "Is" for Island and "Oc" for Ocean, which you approve.
* On the desktop with NVDA, the short format goes to Braille, and the full one is spoken. In the web version there is only one channel, so the short format is used for both when it is switched on.
* The automatic test checks that 90% of the acceptance scripts' changes fit 40 characters.

### DP146: magnifiers in the web version

ACC-8 asks for the magnifier to follow the map centre after every move. On the desktop, the map tells Windows where its centre is, as a text caret would. A web page can only do this through the browser, which tells the magnifier where the focused element is.

* Proposal: on the desktop, full support, tested with Windows Magnifier. In the web version, a small invisible focus point is moved to the map centre after every move; Windows Magnifier follows it in Chrome and Edge, and probably not in Firefox. What works is written in Help and the release notes.

### Not questions: settled by your earlier answers

* The sound model: stereo with a lower pitch behind is the default, and HRTF with a lower pitch behind is the option (DP100). The user experience description, section 8.2, still says HRTF is the default; I correct it in P2-T6.
* Loudness falls evenly with distance, not with each doubling, and no sound is quieter than the minimum volume (DP137). The logarithmic curve stays as a setting. The core already has both, from Phase 1.
* The lower pitch behind applies to labels and the beacon too (DP137).
* The web voice uses four threads through a small helper script, falling back to one thread (DP105).
* The list of every command with its key, and a column for the key you want, as a CSV file (DP109). It is P2-T0c, at the very start, so your keys are in before the new commands reach the shells.

## Order of work

1. Start of the phase: P2-T0a to P2-T0c. Check the PySide6 and Pyodide versions, delete the obsolete Phase 0 code (DP122), and give you the key list (DP109).
2. P2-T14, the held key, first, as agreed in DP140, so the clicks are even before any spatial sound is added.
3. P2-T1, orientations and turning, then P2-T2, history and going to coordinates, then P2-T15, going back from the announcement history.
4. P2-T3 and P2-T4, layers and the visible rule. At the same time, P2-T10's pipeline work and the world rebuild, a heavy run.
5. P2-T5, crossed and passed.
6. P2-T6, the sound scene, then P2-T7, the voice, P2-T8, the earcons, and P2-T9, the beacon.
7. P2-T11, verbosity and Braille.
8. P2-T12, themes and names on the map, and P2-T13, magnifiers.
9. The installer and web version with the voice, the checklists, the phase report, and your acceptance, with the question about publishing (DP110).

Your answers to DP142 to DP146 and your key list are needed before steps 3, 5, 6 and 7, in that order.

## Heavy runs

Before each one I tell you how long it should take, how many cores it uses and how much memory, as agreed in DP103, and arm a watch for stalls. One heavy run at a time.

* The world pack rebuilt with the graticule and the West Bank and Ilemi Triangle marked disputed (P2-T10). The Phase 1 world build took about 80 minutes with 8 workers. Most of its kept results can be reused, so this should be shorter, but the join stage runs again because its settings changed. I estimate 30 to 90 minutes.
* The world pack built a second time from its kept results, to prove it comes out byte for byte the same (DMT-1): about 25 minutes.
* Small samples for the test pack, read from the planet file with GeoDesk: the River Itchen, a lake and a railway station near Southampton (P2-T10). A few minutes, but it reads the planet file, so nothing else may run then.

## Start of the phase

### P2-T0a Versions (Sonnet)

* Check for newer PySide6 and Pyodide releases. On 5 November the latest were PySide6 6.12.0 and Pyodide 314.0.7.
* If either is newer, upgrade it on a branch, run all the Python and browser tests, and keep the upgrade only if they pass. Note the result in phase-2.md.

### P2-T0b Delete the obsolete Phase 0 code (Sonnet)

* Branch: p2-t0-remove-phase0.
* As you agreed in DP122: mapcore/store/world_sample.py, the countries geometry in mapcore/render/globe.py, mapcore/geo/phase0_words.py, mapcore/data/world_110m.json, and the tests that cover only them.
* First check what still uses each one, including mapdata/stages/world_sample.py and the spike S2 commands. Anything still used is kept, and listed in the task list with the reason.
* Done when every test passes with them gone, as a change on its own.

### P2-T0c The key list (Sonnet)

* Branch: p2-t0-key-list. Requirements: ACC-3, ACC-4. From DP109.
* A CSV file, docs/plan/phase-2-keys.csv, made by a small script from the command registry, so it can be made again. Its columns: Command, Where it works (the map or anywhere), Phase, Key now, Key proposed, Your key.
* It lists every command now in the registry, and every new Phase 2 command with the key proposed in the user experience description, section 12: F, Shift+Left and Shift+Right, Ctrl+Left and Ctrl+Right, A, G, Backspace and Shift+Backspace, Shift+L, B, and the new ones from this plan: hear its direction (DP143), isolate, the verbosity preset, and the theme.
* It also lists the Information panel group keys from DP109, I, N, O, X and Shift+X, marked as proposed to be dropped, so you can keep any you want.
* It follows the discussion points file's rules: CRLF at the end of each line and no BOM, so it opens cleanly in your editor.
* When you send it back, your keys go into the registry, and the screen reader key clash test (ACC-4) is run on them. Any clash is raised with you before it goes in.

## P2-T14 Holding an arrow key

* Branch: p2-t14-held-key.
* Requirements: ANN-3, NFR-1, VIS-1. From DP140.
* Needs first: nothing.

Work items:

* P2-T14a Clicks keep their own time (Opus). The repeat delay and repeat speed from DP129 already decide when each step is made. Each step, its click and its drawing are separated: the step and the click happen on time from a timer of their own, and the map is drawn afterwards, only if there is time. While a key is held, the map is drawn at most 4 times a second, a setting. When the key is let go, the map is drawn once more, at the final place. Both the desktop and the web version, with the timing rule in the core so they behave alike (rule 2).
* P2-T14b Measure the drawing (Opus). Add timings to the trace for each part of a drawing: choosing the shapes, projecting them, and painting them, on the desktop and the web. Run a held key walk across Europe, the Pacific near Fiji, and Antarctica, at three zooms, and write where the time goes in docs/plan/p2-t14-drawing-timing.md.
* P2-T14c Make the drawing faster (Opus). Try at least two approaches on the slowest part, keep the fastest, and record the times, as for the build speed trials (DP107). Candidates: keeping the projected shapes when the centre moves less than a set amount and only shifting the picture; keeping each drawing tile's projected points until the zoom changes; and painting the land fill once per frame as a single path. Reusing the last picture is allowed only where the picture would look the same (DP140).

Tests first:

* With a stand-in for a slow drawing, 200 ms each, a 3 second held key at 6 steps a second gives clicks within 10 ms of their due times.
* The map is drawn no more than 4 times a second while a key is held, and once after the release.
* After the release, only the final place is spoken (ANN-3, the Phase 1 test, kept).
* A picture drawn from reused shapes matches a fresh drawing, point for point within one pixel.

Done when the tests pass on both versions, and the timing report shows the drawing times before and after.

## P2-T1 Orientations and turning

* Branch: p2-t1-orientations.
* Requirements: NAV-3, NAV-11, NAV-12, SON-2 (the descriptions part), ANN-5, LOC-7.
* Needs first: P2-T0c's key list back from you, or the proposed keys used until it is.

Work items:

* P2-T1a Stepping in the three orientations (Opus). In mapcore/world and mapcore/geo:
  * The world state already holds the orientation and heading. North-fixed stays as it is.
  * Cardinal facing: Up moves forward and Down back. Facing east or west, the move follows the line of latitude, as in north-fixed (DP69). Facing north or south, it follows the meridian and may carry on over the pole: the location comes out on the other side, at the longitude 180 degrees away, and the heading is reversed. Left and Right turn 90 degrees.
  * Free facing: Up and Down follow a great circle on the ellipsoid, with GeographicLib's direct calculation. The heading on arrival is the direction of travel at the end of the step; moving back keeps facing the same way. Left and Right turn by the fine amount, 15 degrees by default.
  * Every move still returns its path, densified to follow the Earth's curve, including over a pole, for Crossed and passed.
  * Turning: Shift+Left and Shift+Right turn 90 degrees in both facing orientations; Ctrl+Left and Ctrl+Right turn by the fine amount in free facing. In north-fixed, turning plays the blocked sound.
  * Switching orientation never moves you (NAV-11). Switching to north-fixed faces north. Switching from free facing to cardinal facing turns to the nearest of north, east, south and west.
* P2-T1b Directions relative to the way you face (Opus). Every direction the core gives, in Nearby and later lists, is relative to "ahead" in the facing orientations: "ahead", "to your right", "behind", or the clock face, in your bearing format (ANN-5, SON-2). North-fixed keeps compass directions. One function does this, so sound, Nearby and later look around use the same rule.
* P2-T1c Commands, words and the bearing dialog (Sonnet). In the registry: F (cycle orientation), the four turning keys, and A (type a bearing). In the templates: "North-fixed", "Cardinal facing, east", "Free facing, 47 degrees", "Crossed the North Pole. Now facing south", and the heading in H, such as "Facing 47 degrees. Free facing. Stepping." The bearing dialog: an edit box that takes degrees, or a compass point such as "NE"; an error that says what is accepted; OK and Cancel (ACC-7). Typing a bearing in north-fixed or cardinal facing switches to free facing, and says so. Help and F1 updated.
* P2-T1d The same in the web version (Sonnet). The bearing dialog in the web shell, with the same words from the core, and the browser tests for F, the turning keys and A.
* P2-T1e The heading on the map (Sonnet). The heading arrow at the centre points the way you face. Heading-up rotation waits for the themes, P2-T12.

Tests first:

* NAV-3: from 80 north 0 east, facing 0 degrees in free facing, forward 2,000 km arrives at about 82 north 180 east, facing 180 degrees, within 0.01 degrees.
* Cardinal facing north at 89.9 north, a 50 km step crosses the North Pole, arrives on the far meridian facing south, and says so. The same at the South Pole.
* Cardinal facing east follows the line of latitude, the same as north-fixed east.
* Switching from free facing at 47 degrees to cardinal facing faces east, and says so; switching orientation never changes the location.
* NAV-12: a feature at 90 degrees is "east" in north-fixed, and "ahead" or "12 o'clock" facing 90 degrees in either facing orientation.
* Turning in north-fixed plays the blocked sound and says nothing.
* New acceptance scripts: cycling the orientations; crossing the North Pole in cardinal facing and in free facing.

Done when the tests pass on both versions and the new wording is in the approved files.

## P2-T2 Position history and going to coordinates

* Branch: p2-t2-history-jump.
* Requirements: NAV-8 (coordinates), NAV-10.
* Needs first: P2-T1, and your answer to DP142.

Work items:

* P2-T2a Reading coordinates (Sonnet). A function in mapcore/geo that reads every format in NAV-8, "51.5, -0.12", "51.5N 0.12W" and "51°30′N 0°07′W", and the near variants people type: spaces instead of commas, an apostrophe and a quotation mark instead of the prime signs, "S" and "W" for negative, and seconds with decimals. It refuses anything out of range, or that could be read two ways, and the error from the templates lists the accepted formats.
* P2-T2b Jumping and history in the core (Sonnet). A jump moves the location without a step and gives the normal announcement. Jumping to coordinates keeps the zoom (NAV-8). Position history as DP142 decides: before each jump the place, zoom and step are kept; Backspace goes back and restores the zoom (DP77); Shift+Backspace goes forward; at least 100 places, saved with your settings. Going back with nothing to go back to plays the blocked sound. A click on the map counts as a jump.
* P2-T2c The G dialog in both shells (Sonnet). An edit box with its label, OK and Cancel, and the error read out if what was typed can't be read. The browser tests check it in Chromium and Firefox.

Tests first:

* Each NAV-8 format, and each variant above, gives the same place within a metre; "91, 0" and "51.5 W 0.12 N" are refused with the message.
* Jump, step three times, Backspace: back at the place before the jump, with its zoom.
* Back then forward returns to the jump's place; a new jump clears forward.
* 101 jumps keep the last 100.
* An acceptance script: G to Niagara Falls, then Backspace back. This also lets your checklist start anywhere, which DP133 asked for.

## P2-T15 Going back to a place from the announcement history

* Branch: p2-t15-history-enter.
* Requirements: ANN-4, NAV-8. From DP141.
* Needs first: P2-T2.

Work items:

* P2-T15a (Sonnet). Each announcement history entry keeps the place, zoom and step it was said at. Enter on an entry closes the dialog and jumps there, with P2-T2's jump, so Backspace comes back. Entries said before this change, or with no place, such as a Help message, say "No place for this entry" and do nothing. The dialog's Help line says what Enter does. Both shells.

Tests first: step twice, open the history, Enter on the first step's entry: back there, with the zoom it had, and Backspace returns.

## P2-T3 Layer catalogue

* Branch: p2-t3-layers.
* Requirements: SCP-6, SCP-7.
* Needs first: nothing, but P2-T10's world rebuild adds the graticule layer to it.

Work items:

* P2-T3a Layers in the core (Opus). A layer catalogue in mapcore, made from the pack manifest's layer definitions (architecture 6.2), with your changes on top: on or off, the zoom range, and the crossing earcon. Your changes are saved by layer identifier, so they survive a pack rebuild. Every part of the core that finds features asks the catalogue first: "where am I", change detection, Nearby, the map scene, and from P2-T5 Crossed and passed. A layer that is off is gone from all of them (SCP-6).
  * If every layer at a point is off, "where am I" says "Every layer here is switched off" instead of nothing, so you are never left in silence (LOC-6). The templates hold the words.
* P2-T3b The layers dialog on the desktop (Sonnet). Shift+L opens a list with a check box for each layer, grouped as in the layer definitions, such as Boundaries and Water. Space switches a layer. A Settings button for the selected layer opens its zoom range and crossing earcon. OK and Cancel. The same list is the Layers tab of Settings.
* P2-T3c The layers dialog in the web version (Sonnet), with the same contents from the core, and the browser tests.

Tests first:

* With Regions off, stepping from Kent to Sussex says nothing about the region, and the map draws no region borders; with it on again, both come back.
* With Oceans and seas off, a point in the Atlantic says "Every layer here is switched off".
* A layer switched off stays off after the application restarts, and after the pack is rebuilt.
* The graticule layer, from P2-T10, appears in the list with no code written for it (SCP-7).
* Changing one layer's crossing earcon changes the sound for that layer only (SCP-7).

## P2-T4 The visible rule

* Branch: p2-t4-visible-rule.
* Requirements: NAV-13, SCP-7, ANN-7, DP80.
* Needs first: P2-T3.

Work items:

* P2-T4a The rule in the core (Opus). One function decides whether a feature is visible (architecture 7.4): its layer is on, the zoom is within the layer's zoom range, an area is at least the layer's minimum size (2% of the zoom distance by default), and it is at least partly within the view, the circle round you whose radius is the zoom. The first three tests cost almost nothing; the last uses the drawing tiles and the local projection, with an exact check only near the edge. It handles the 180 degree line and the poles.
* P2-T4b Using it (Sonnet). The map scene draws only visible features. Nearby lists only visible features, and later look around and Crossed and passed use the layer and zoom parts, as DP80 agreed. "Where am I" is never limited (ANN-7). Default zoom ranges for each layer in the layer files, starting from the Shortbread schema (data sources, version 0.7), with the reason for each in docs/data-manager/configuration.md.

Tests first:

* At a 10 km zoom in Kent, France is not in Nearby; at 100 km it is.
* At a 5,000 km zoom, Luxembourg is too small to be visible, and still named by "where am I" when you stand in it.
* A feature across the 180 degree line is in view from both sides.
* The rule takes under 5 ms for a whole frame on the world pack on the desktop; the web figure is recorded.

## P2-T10 Graticule and special lines

* Branch: p2-t10-graticule.
* Requirements: DAT-13, SCP-7, SON-6, AD-11.
* Needs first: P2-T3a, for the layer definition. It can start alongside P2-T1.

Work items:

* P2-T10a Line features in packs and the store (Opus). The world pack so far holds only areas. Check that the pack format, the store and the map scene handle line and point features, as the format document says; add what is missing, with a new format number if the format changes, and update docs/developer/pack-format.md. The store can find the lines near a path, for Crossed and passed.
* P2-T10b The graticule stage (Sonnet). A pipeline stage that writes lines of latitude and longitude every 1 degree, each marked with the intervals it belongs to, such as 5, 10 and 15, so your interval setting is only a filter. The special lines: the equator, the prime meridian, the 180 degree meridian, the tropics and the polar circles, each a named line with its own crossing earcon in the layer definition, all off by default. The international date line, which is not straight, comes from Natural Earth's geographic lines (public domain), added to sources.yaml after the licence check (rule 7) and to "data sources.md". The tropics and polar circles use their values for the pack's build year, written in the settings.
* P2-T10c Samples for the test pack (Sonnet). Small samples read from the planet file with GeoDesk, kept in tests/samples/osm with the ODbL notice: the River Itchen through Southampton, a small lake near it, and a railway station, with their layers in the test pack's settings. These are for ANN-2's acceptance tests only; the world pack gets rivers and railways in Phase 3.
* P2-T10d The world rebuild (Opus). A heavy run, announced first. The world pack with the graticule layer, and with the West Bank and the Ilemi Triangle marked disputed, as fixed on 4 November but not yet built. Then the build twice check (DMT-1), the no gaps check, and the size against 250 MB. The pack's report written for you.
* P2-T10e Interval and crossing sounds (Sonnet). The graticule interval setting, 1, 5, 10, 15 or 30 degrees (DAT-13), in the Layers tab. Crossing a graticule line with its earcon on plays it, through the layer's crossing earcon, with no code specific to the graticule.

Tests first:

* Stepping across 0 degrees longitude with the layer on lists "Prime meridian, crossed" in Crossed and passed, and plays its earcon if switched on (DAT-13).
* With the interval at 10 degrees, a step across 5 degrees east lists nothing, and across 10 degrees east lists "10 degrees east".
* The international date line and the 180 degree meridian are separate lines.
* The graticule adds less than 1 MB to the world pack (AD-11).

## P2-T5 Crossed and passed

* Branch: p2-t5-crossed-passed.
* Requirements: ANN-2, ANN-7, SCP-6, SON-6, NFR-1.
* Needs first: P2-T1a for paths over the poles, P2-T4, and P2-T10a.

Work items:

* P2-T5a The search along the path (Opus). As architecture 7.5: after the step is announced, in the background, take the step's path and find, from layers that are on and whose zoom range includes the zoom, the lines it crosses, the areas it enters and leaves within the step without either end being in them, and the points within the passed nearby distance. Each item has its closest distance and its bearing from the new position, relative to the way you face. On the desktop it runs on a worker thread; in the web version, in the core's worker between key presses. A new step cancels an unfinished search. It works across the 180 degree line and over the poles.
* P2-T5b The group and its settings (Sonnet). Crossed and passed as a group in the Information panel, from the group table (INF-10), holding the most recent move only. The "something added" earcon, on by default, with its own switch. The passed nearby distance: 10% of the step by default, or a percentage or a fixed distance, in the Movement tab. Nothing in the list is ever spoken by itself (ANN-2).

Tests first, on the test pack:

* A 1 km step across the River Itchen lists "River Itchen, crossed" and plays the earcon, with nothing spoken.
* With a 5 km step, a path 300 metres from the station lists it with "closest 300 metres"; a path 800 metres away does not.
* A 5 km step over the small lake lists it as "passed over".
* On the world pack, a 100 km step across Luxembourg lists Luxembourg as passed over.
* The list is replaced after each move.
* The location announcement's time is the same with the search on and off, within 5 ms (NFR-1).

## P2-T6 Sound scene and sound players

* Branch: p2-t6-sound-scene.
* Requirements: SON-1, SON-2, SON-9, SON-7, AD-10.
* Needs first: P2-T1b.

Work items:

* P2-T6a The sound scene in the core (Opus). In mapcore/sound: for each sound to play, the core works out its direction relative to "ahead" in the current orientation (SON-2), its loudness from the distance curve (linear by default, as you chose in DP137, with the minimum volume), whether it is behind you (a lower pitch, about three semitones, and slight muffling), and whether it is beyond the hearing range (the minimum volume, muffled, or the fixed tone if that setting is chosen, DP80). The core says what to play and how; it plays nothing (AD-10). The two sound modes, stereo with pitch (the default) and HRTF with pitch, are a setting.
* P2-T6b The desktop sound player (Opus). desktop/audio, built from the spike S1 and listening test code: NumPy and sounddevice, equal-power panning or the MIT KEMAR responses, the pitch change and the muffling, with several sounds able to play at once, each on its own volume. It starts quickly enough that a sound plays within 50 ms (NFR-1). If no sound device is found, it says so once and carries on silent.
* P2-T6c The web sound player (Sonnet). The same in Web Audio: the stereo panner or the HRTF panner, the pitch change, and a low-pass filter for muffling, following P2-T6a's numbers, so both versions place a sound the same way. Built from the spike S1 web demo.
* P2-T6d Settings and the user experience description (Sonnet). The Sound tab: the sound mode, the curve (linear or logarithmic), the minimum volume, and beyond the view as quiet and muffled or a fixed tone. Section 8.2 of the user experience description corrected to say stereo with pitch is the default (DP100).

Tests first, with no sound device opened:

* SON-2: a sound at 90 degrees is to the right in north-fixed, and straight ahead facing 90 degrees in either facing orientation.
* A sound at half the hearing range has the same loudness at every zoom.
* No sound is ever quieter than the minimum volume; beyond the range, it is at the minimum and muffled.
* A sound behind has the lower pitch in both modes.
* The desktop and web players turn the same scene into the same pan, pitch and filter values.

## P2-T7 Spatial voice

* Branch: p2-t7-spatial-voice.
* Requirements: SON-3, ANN-4, ACC-1, AD-10.
* Needs first: P2-T6, and your answer to DP143.

Work items:

* P2-T7a The voice on the desktop (Opus). Piper with the Alba voice, from the listening test code in desktop/audio/voice.py, moved into the application. Piper is moved from the spike requirements into the runtime requirements, after the licence check (rule 7). The voice is loaded in the background while TobyMap starts, about 8 seconds. Each label is made into sound in memory, then placed by the sound scene like any other sound, with the lower pitch behind (DP137). If a new label is asked for before the last is finished, the old one stops (ANN-3). The sound output is started, and a silent label made, before the first real label, so the first one is heard (P2-T7 in the implementation plan).
* P2-T7b The voice in the web version (Opus). A worker of its own beside the core's worker, with phonemizer.js and ONNX Runtime Web, as in spike S6, fetched by tools/fetch_vendor.py. Four threads through the helper script that turns on cross-origin isolation (coi-serviceworker, MIT, after the licence check), falling back to one thread if the script causes trouble with NVDA or with downloading the pack (DP105). The same warm-up so the first name is heard.
* P2-T7c "Hear its direction", history and Braille (Sonnet). The item action from DP143 on Nearby and Crossed and passed: the layer's sound, then the name and distance in the voice, from the item's direction. Each label goes into the announcement history. On the desktop with NVDA, it is also sent to Braille without speech. The setting "also speak spatial labels through the screen reader", off by default. The voice's own speed and volume.
* P2-T7d Packaging the voice (Sonnet). The voice in the Windows installer and portable zip, about 75 MB more, and in the web version's files. Alba's CC-BY 4.0 credit in About and the third-party notices.

Tests first:

* With a stand-in voice, a label asked for at 90 degrees is placed at 90 degrees, with the lower pitch if behind.
* A second label stops the first.
* Each label is in the history, and in the Braille-only output on the desktop.
* With "also speak" on, the screen reader also gets the label.
* The browser tests check the voice worker starts in Chromium and Firefox, with four threads and with one, and that the page still downloads and reads the pack with the helper script on.
* Time from asking to sound is recorded: about 100 ms is expected on the desktop and 220 ms in the browser with four threads.

## P2-T8 Earcons in full

* Branch: p2-t8-earcons.
* Requirements: SON-6, SON-7, SON-8.
* Needs first: P2-T6.

Work items:

* P2-T8a (Sonnet). Every event in mapcore/describe/earcons.yaml plays where it should: the tick, blocked, something added, no data, ambiguous up (ready for Phase 3), line crossed, and the ding (ready for Phase 5). Each can be switched off on its own. Separate volumes for earcons, the voice and the beacon, and the master mute, Ctrl+M, silences them all. Your own earcons replace the placeholders as you send them (DP61, DP128). In The sounds in Help, each sound can be played.
* P2-T8b Your own sound files in the web version (Sonnet). As DP123 asked: every earcon plays in the web version with no set-up. To use your own, a Choose file button for each earcon reads a WAV file you pick, keeps it in the browser's storage, and uses it from then on, with a Use the default button.

Tests first: each event plays its earcon, and none when switched off; mute silences earcons, the voice and the beacon; an unreadable file falls back to the default with a message (SON-8).

## P2-T9 Orientation beacon

* Branch: p2-t9-beacon.
* Requirements: SON-10, SON-2.
* Needs first: P2-T6.

Work items:

* P2-T9a (Sonnet). B switches the beacon on and off, and says which. It is a soft sound repeated about once a second, a setting, from the direction of the North Pole relative to the way you face, through the sound scene, with the lower pitch when behind. Within 100 km of the North Pole it fades out, and you are told "Beacon off near the North Pole". It comes back when you move further away. The target setting is there with only the North Pole for now; pins are added in Phase 4. A placeholder sound until you choose one.

Tests first: facing east the beacon is to the left, facing south it is behind (SON-10); in north-fixed it is straight ahead; 50 km from the pole it is silent and the message is given once.

## P2-T11 Verbosity and the short Braille format

* Branch: p2-t11-verbosity.
* Requirements: ACC-5, ACC-6, ANN-1.
* Needs first: your answers to DP144 and DP145.

Work items:

* P2-T11a Presets and switches (Sonnet). Terse, normal and detailed, as DP144 decides, and a switch for each automatic announcement: area change, zoom and step changes, heading, and the tick. In the Speech tab, and a key to cycle the presets if you give it one in the key list. Crossed and passed is never spoken (ANN-2).
* P2-T11b The short Braille format (Sonnet). As DP145 decides, made from the templates, with fields always in the same order. On the desktop, sent to Braille through NVDA while the full words are spoken; in the web version, used for both.

Tests first:

* Each preset gives the expected words on the Channel crossing script.
* In the short format, at least 90% of the acceptance scripts' area changes fit 40 characters (ACC-6).

## P2-T12 Themes, the map display and names on the map

* Branch: p2-t12-themes.
* Requirements: VIS-2, VIS-3, VIS-1, AD-17, AD-19, DP108.
* Needs first: P2-T4.

Work items:

* P2-T12a The themes (Sonnet). Standard, high contrast dark, high contrast light, and colour-blind safe, in mapcore/render/themes.yaml. Each has seven land colours, so neighbours still differ (AD-19). A test works out the contrast ratio of every text and outline colour against what it is drawn on, and the high contrast themes must reach 7 to 1 (VIS-2). The colour-blind safe colours are checked with a simulation of the three common kinds of colour blindness, so neighbouring colours still differ.
* P2-T12b The map display setting (Sonnet). As agreed in DP108: the fill as different colours for neighbours (the default), one colour for all, or none; borders on or off; and the colours of the fill, the borders and the current outline. The current feature's outline is always drawn, and the high contrast themes keep the 7 to 1 check with every choice.
* P2-T12c Isolate (Sonnet). A command that shows only the current feature and its outline, and again to show everything. Isolating Fiji shows one compact shape, across the 180 degree line (AD-17).
* P2-T12d Names on the map (Opus). The map has no names yet. The core chooses where to put each visible area's name, inside the area where there is room, never overlapping another name, with larger areas first, and gives the shells the text, its place and its size. Names scale with the zoom, and the label size setting goes up to at least 200% (VIS-3). Every name drawn is one that "where am I" can say (SCP-2).
* P2-T12e Heading-up (Sonnet). The setting that turns the globe so the way you face is up, in the facing orientations.

Tests first: the contrast checks; neighbours never share a colour in any theme; Fiji isolated is one shape; no two names overlap in a frame of Europe at three zooms; at 200% the names are twice the size and still do not overlap.

## P2-T13 Magnifier support

* Branch: p2-t13-magnifier.
* Requirements: ACC-8.
* Needs first: P2-T12, and your answer to DP146.

Work items:

* P2-T13a The desktop (Opus). The map widget tells Windows where its centre is after every move, as a text caret or focus rectangle does, so Windows Magnifier set to follow the keyboard focus or the text cursor keeps the centre in view. Found out with Windows Magnifier itself, and with Microsoft's Accessibility Insights to read what the map reports.
* P2-T13b The web version (Sonnet). As DP146 decides: a small focus point moved to the map centre, with what works in each browser written in Help.

Tests first: the rectangle the map reports contains the map centre after a step, a click and a jump, at three window sizes.

## The automatic exit checks

From the implementation plan, section 5, and how each is met:

* The Phase 2 acceptance scripts pass on Windows, macOS and the web, including NAV-3's 0.01 degree test and the pole crossings. New scripts: orientations, turning, both pole crossings, going to coordinates and back, layers off and on, Crossed and passed on the test pack, the graticule, the presets, and Enter in the announcement history.
* The high contrast themes pass the 7 to 1 contrast check.
* Also checked, though not new exit checks: step timing still meets 150 ms for 95% of steps on the world pack (NFR-1), with the sound scene, the voice and Crossed and passed all on; the world pack built twice is identical (DMT-1); the installer, now with the voice, installs, starts and uninstalls cleanly in continuous integration.

## Your acceptance checklist

The checklists, docs/checklists/phase-2-desktop.md and phase-2-web.md, are made from the acceptance scripts, as in Phase 1. They will cover:

1. Installing the new version, and opening the web version in Firefox.
2. Going to typed coordinates with G, and back with Backspace.
3. Cycling the orientations with F, and turning in each.
4. Crossing the North Pole in cardinal facing and in free facing.
5. Switching layers off with Shift+L, and hearing that they are gone from what is said and drawn.
6. Taking large steps, then opening Crossed and passed with F3, and hearing its earcon.
7. Hear its direction on Nearby items: the sound and the label from the same place, ahead, to the side and behind (DP143).
8. The beacon in each orientation, and fading near the North Pole.
9. The graticule's crossing earcons, switched on, and the interval.
10. Holding an arrow key: even clicks, and only the last place spoken.
11. Enter in the announcement history going back to a place.
12. The verbosity presets and the short Braille format.
13. Your earcons and their switches and volumes; in the web version, choosing your own file.
14. Your feedback on the sound design as a whole, now that it is built on your choices in DP100 and DP137.

Steps on the themes, names and magnifier are in a separate short checklist for a sighted helper, if you have one, since they need sight to judge. Their automatic tests run either way.

## Closing the phase

* The phase report, docs/plan/phase-2-report.md (Sonnet): what was built, how to install it, the checklists, known problems, and what was not tested.
* Continuous integration green on every job before you see it.
* Your feedback recorded against requirement IDs (DEL-4).
* As agreed in DP110, I ask whether to publish. If you agree: the GitHub release with the installer, the portable zip and the release notes, the web version on GitHub Pages, and the world pack as a data release with its Hugging Face copy (Opus, as it is the first publication and has a sign-in step).

## Risks

* The held key: if the clicks are still uneven once drawing is out of the way, the cause is elsewhere, such as speech or Windows' own key repeat. The trace from P2-T14b shows where.
* Several sounds at once on the desktop may crackle if the sound processing is too slow. The player mixes in blocks, and P2-T6b measures the time each block takes.
* The helper script for four voice threads might upset NVDA or the pack download in the web version. The fall-back is one thread, about 380 ms a label.
* The voice adds about 75 MB to the installer and about 60 MB to the web version's first visit.
* Names on the map are new and may be slow on the widest views. They are left out while a key is held, and drawn when it is let go.
* Magnifiers in Firefox may not follow a web page's focus point. If so, it is written in Help, and Chrome or Edge is suggested for magnifier users.
* The world rebuild could find new faults, as the first world build did. It can stop and carry on, and the Phase 1 pack is kept until the new one passes its checks.
* The colour-blind safe theme needs seven colours that differ for every kind of colour blindness, which is hard. If seven can't be found, the theme uses fewer colours and draws borders thicker, and I tell you.

## Left for Phase 3

* Hierarchy mode, with the keys 1 and 2, and the movement mode part of H.
* Look around, which uses the sound scene and the voice built here.
* Rivers, lakes, roads, railways and places in the world pack, so Crossed and passed has more than areas and the graticule outside the test pack.
* The other Information panel groups.
* Named seas (DP115).
