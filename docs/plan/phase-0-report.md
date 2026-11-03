# Phase 0 report: foundations and spikes

Written on 3 November 2026. Every Phase 0 task is done, and continuous integration passed on main. You accepted the phase on 3 November. Your comments, and where each one goes, are in the last section, "Your acceptance".

This report follows the definition of done for a phase, in section 1.5 of the implementation plan. It has six parts: where the phase stands, what was built, how to install and run it, the acceptance checklist, known problems, and what was not tested. The words used, such as pack, lookup and label, are explained in docs/design/glossary.md.

## Where the phase stands

* All eleven tasks, P0-T1 to P0-T11, are done and ticked in docs/plan/phase-0.md.
* All six spikes have findings in docs/spikes, and each question has an answer.
* Discussion points 84 to 105 are all answered. None is open.
* The architecture is at version 0.4, with the results of every spike.
* The automatic exit checks pass. They are listed near the end of this report.
* You accepted the phase on 3 November.

Some work was moved to Phase 1 on purpose, at your request:

* Task P1-T16 takes the rest of spike S2: a faster counties step, stage 1's whole run and comparison, stage 4 (Argentina), and three improvements to the build's checks.
* Four threads for the voice in the browser are tried in Phase 2 (DP105).

## What was built

### P0-T1 to P0-T3: the repository, continuous integration and set-up

* The TobyMap repository on GitHub, public, under GPL-3.0, with the design documents in docs/design.
* Continuous integration runs on every push. It runs the Python tests on Windows and macOS, the browser tests in Chromium and Firefox, the licence check, and builds the Windows installer.
* setup.ps1 sets up the laptop in one command. The data folder is a setting, which on your laptop points at drive E:.

### P0-T4: spike S1, spatial sound

* A sound demo with six engines and a listening quiz: tools\spikes\s1\demo.py.
* Decided (DP100): stereo with pitch by default, and HRTF with pitch as an option, from TobyMap's own sound processing.
* Findings: docs/spikes/S1-spatial-sound.md.

### P0-T5: spike S2, countries, coastlines and islands

This was the main question of the phase: can TobyMap build countries, coasts and islands correctly from OpenStreetMap?

* The build command, mapdata spike-s2, and mapdata inspect, which says what is at a point in a pack.
* Stage 1, the UK, France and Spain, on 1 November: 22 of 22 check places right. Every layer's neighbours meet exactly after cleaning and simplifying.
* Stage 2, Norway and Sweden, on 2 November: every check passed. Norway's land is within 0.1% of Wikidata's figure, and Sweden's within 0.6%.
* Stage 3, the 180 degree line and the South Pole, on 2 November: 27 of 27 check places right, in Fiji, Russia, the USA, Kiribati and Antarctica. The South Pole is in Antarctica.
* Packs with compact coordinates are about 4.6 times smaller. A lookup took about 13 ms at the median, and at most 59 ms, on the desktop.
* After DP103, the build uses several of the laptop's cores. Stage 3 went from 75.7 minutes to 13.1.
* Findings, with descriptions of the pictures: docs/spikes/S2-countries-coastlines.md.

### P0-T6: spike S3, hosting and the browser

* A test page for hosting and storage, tried in Chrome, Firefox and Edge: tools\spikes\s3\run.py.
* Decided (DP102): packs go on GitHub Releases for the desktop, with a copy on Hugging Face for the web. The web version downloads a pack whole into the browser's private storage.
* Nothing was published, as you chose.
* Findings: docs/spikes/S3-hosting-browser.md.

### P0-T7: spike S4, the core in the browser

* A test page and runner: tools\spikes\s4\run.py.
* The core's pack reader runs unchanged in Chrome and Firefox. It reads the Norway and Sweden pack from private storage, and was right at all 18 check places.
* Decoding compact coordinates now uses NumPy. The slowest "where am I" in the browser went from 168 ms to 49 ms. The target is 150 ms (NFR-1).
* Start-up takes about 4 seconds. A first visit downloads 16.5 MB.
* Findings: docs/spikes/S4-core-in-browser.md.

### P0-T8: spike S5, the globe, the accessible shell and the installer

* A desktop window (PySide6) and a web page (Pyodide in a worker), built from one shared core.
* Both have the four regions: the map, the Information panel, Details and the menu bar.
* The map is a globe of the world's countries, from Natural Earth. It turns with the arrow keys and announces the country under its centre.
* Every key and menu item comes from the core's command registry, and every word spoken comes from the core's wording file. Neither shell has its own.
* The Windows installer installs for you only, with no administrator prompt (DP95). There is also a portable zip.
* You ran five NVDA tests during the spike.
* Findings: docs/spikes/S5-globe-shell-installer.md.

### P0-T9: spike S6, the spatial voice

* A voice demo on the desktop: tools\spikes\s6\demo.py.
* You chose Piper with the Alba voice. eSpeak NG was ruled out.
* Piper also runs in the browser, in Chrome and Firefox, placed in space with Web Audio: tools\spikes\s6\web_run.py.
* In the browser, a first visit downloads about 60 MB, and the voice is ready about 4 to 5 seconds after it starts loading. Each label takes about 380 ms from request to sound, against 100 ms on the desktop.
* Findings: docs/spikes/S6-spatial-voice.md.

### P0-T10 and P0-T11: lessons and the architecture

* Lessons from AtMap and AtlasDL: docs/design/lessons-from-atmap.md.
* The architecture is at version 0.4. The changes in each version are listed at its top.

### Changes made while writing this report

* The version is now 0.0.7, so the build you test is exactly what is on main. Version 0.0.6 is skipped: it was the experiment in spike S5 that was undone.
* mapdata inspect now says south and west, rather than giving a minus sign with north and east. For example, the South Pole is "90.0 south, 0.0 east", not "-90.0 north".

## How to install and run it

### The desktop version

1. Run TobyMap-0.0.7-setup.exe, in the dist_installer folder of the repository.
2. Windows SmartScreen may say the app is unrecognised, because it is not signed. Choose More info, then Run anyway.
3. The installer has four pages: Welcome, Install location, Installing, and Finished. On the last page, "Start TobyMap now" is ticked.
4. TobyMap is then in the Start menu.

If you still have version 0.0.5 installed, the new version installs over it.

### The web version, on this laptop

1. In PowerShell, in the repository folder, run: `.venv\Scripts\python.exe tools\serve_web.py`
2. Your default browser opens http://127.0.0.1:8765. To use Firefox instead, paste that address into Firefox.
3. It says "Loading TobyMap" for about 10 seconds, then announces the start.
4. Press Ctrl+C in the PowerShell window to stop it.

The web version goes on GitHub Pages in Phase 1.

### The spike packs

The packs from spike S2 are in the data folder, not in the repository:

* Norway and Sweden: E:\osmdata\tobymap\output\s2-stage2\s2-stage2-compact.pack
* The 180 degree line and the South Pole: E:\osmdata\tobymap\output\s2-stage3\s2-stage3-compact.pack

Each folder also has the build's report, report.txt.

## Acceptance checklist

Each item says what to do, then what to expect. Note anything that is different. If you can, give the requirement ID or the checklist number with each note, so your feedback can be recorded against the requirements (DEL-4).

Parts 1 to 8 are on the desktop version, then in Firefox. Parts 9 to 11 are done once.

### 1. Installing

1. Install with TobyMap-0.0.7-setup.exe. Expected: no administrator prompt, and TobyMap starts at the end.
2. Find TobyMap in the Start menu. Expected: it is there, with "Uninstall TobyMap" beside it in its folder.
3. In TobyMap, open the Help menu and choose About TobyMap. Expected: version 0.0.7.

### 2. Starting

1. Start TobyMap. Expected: "TobyMap globe. United Kingdom. Press F1 for keys.", with focus on the map.
2. In Firefox: NVDA switches to focus mode on the map by itself.

### 3. Turning the globe

1. Press Down. Expected: "Spain".
2. Press Right, and keep going. Expected: each country is announced as it comes under the centre.
3. Hold an arrow key down for a few seconds. Expected: speech keeps up and says only the latest country.
4. Press Page Down twice, then turn again. Expected: the step is smaller.
5. Press Space. Expected: the country, the coordinates, the zoom and the step.
6. Press C. Expected: the coordinates only.
7. Press V. Expected: the size of the visible map, such as "Visible map: 1,140 by 890 kilometres", or "the whole globe" at the first zoom.
8. Press Ctrl+Space. Expected: the last announcement again.

### 4. Moving between regions

1. Press Tab, then Tab again, then Tab again. Expected: the Information panel, then Details, then the map. Tab never reaches the menu bar.
2. Press Shift+Tab. Expected: the same, the other way round.
3. From Details, press Ctrl+Alt+Space. Expected: focus goes to the map, and NVDA reads the place.
4. Desktop: press Alt. Expected: the menu bar. Press Tab. Expected: back on the map.
5. Firefox: press Ctrl+Alt+M. Expected: the Map menu, not opened. Press Tab. Expected: back on the map.

### 5. The Information panel

1. From the map, press Shift+Space. Expected: focus on "United Kingdom" inside Within.
2. Press R. Expected: focus in Nearby.
3. Arrow through Nearby. Expected: each country, with its level and position, such as "2 of 8". Details changes to match.
4. Press Left and Right on a group. Expected: it closes and opens, and NVDA says so.
5. In Firefox, press NVDA+Up arrow on an item, and on the group Within. Expected: NVDA reads the line.
6. Desktop: after Shift+Space or R, NVDA may not read the item until you press Up then Down. This is the known problem listed below, not a new one.

### 6. Details and help

1. From the map, press D. Expected: Details, starting at its first line. Arrow down. Expected: each line is read once.
2. Press F1. Expected: the list of keys. Tab to Close and press Enter. Expected: back on the map.

### 7. Braille

1. With your Braille display connected, open the Speech menu and choose Send a Braille-only message.
2. Desktop: expected "TobyMap Braille test: United Kingdom" on the display, with nothing spoken.
3. Firefox: expected a spoken explanation that a web page can't send Braille-only messages.

### 8. Uninstalling

Do this last, after the Firefox run if you like.

1. Uninstall TobyMap from Settings, Apps. Expected: it is removed from the Start menu and from the list of apps.

### 9. The spike S2 packs

These are run in PowerShell, in the repository folder. Each command says what areas are at a point, smallest first. Expected answers are given.

1. Lofoten in Norway:
   `.venv\Scripts\python.exe -m mapdata inspect E:\osmdata\tobymap\output\s2-stage2\s2-stage2-compact.pack 68.234 14.568`
   Expected: Vågan, a county; Nordland, a region; Norway, the country.
2. Taveuni in Fiji, just east of the 180 degree line:
   `.venv\Scripts\python.exe -m mapdata inspect E:\osmdata\tobymap\output\s2-stage3\s2-stage3-compact.pack -16.84 -179.995`
   Expected: "At 16.84 south, 179.995 west", then Cakaudrove, Northern and Fiji.
3. Little Diomede, in the Bering Strait:
   `.venv\Scripts\python.exe -m mapdata inspect E:\osmdata\tobymap\output\s2-stage3\s2-stage3-compact.pack 65.755 -168.93`
   Expected: Unorganized Borough, Alaska and United States.
4. The South Pole:
   `.venv\Scripts\python.exe -m mapdata inspect E:\osmdata\tobymap\output\s2-stage3\s2-stage3-compact.pack -90 0`
   Expected: "At 90.0 south, 0.0 east", then Antarctica.
5. Try any other places you know in Norway, Sweden, Fiji, Russia, the USA, Kiribati or Antarctica. A point in the sea says "sea, no land area".

### 10. Piper in the browser

Use headphones. This is the one part of the voice not yet heard by ear.

1. In PowerShell, run: `.venv\Scripts\python.exe tools\spikes\s6\web_run.py --serve`
2. Paste the address it prints into Firefox.
3. Press "Load the voice", and wait until the page says the voice is ready. Expected: about 5 seconds.
4. Under "Eight place names from eight directions", press each button. Expected: the Alba voice says each name from its direction, after a short delay.
5. Press Ctrl+C in the PowerShell window to stop.

### 11. Reading the findings

1. Read the findings for S2, S4 and S6 in docs/spikes, which you have not yet read in full since 2 November.
2. Expected: nothing in them needs a new decision. Any question you have goes in the discussion points file as a new row.

## Known problems

### In the shell

* Desktop: after R or Shift+Space, NVDA doesn't read the item the Information panel has moved to until you press Up then Down. Qt keeps an out-of-date list of the panel's items for screen readers. In Phase 1 the panel's items are changed in place instead of being rebuilt.
* The globe uses Natural Earth until Phase 1. At this scale it puts French Guiana inside France, and its coasts are coarse. The S2 build replaces it.
* Shapes that cross the edge of the globe are squashed onto the edge. Very large shapes near the edge may look odd. You confirmed this is as it should be.
* Distances in Nearby are measured on a sphere, to each country's label point. The ellipsoid comes with stepping in Phase 1.
* The desktop doesn't yet tell screen magnifiers where the centre of the map is (ACC-8).
* The web version takes about 10 seconds to start the first time.

### In the voice

* On the desktop, Piper's first label took about 5 seconds. In Phase 1, a first label is made silently at start-up.
* In the browser, each label takes about 380 ms with one thread. Four threads bring it to about 220 ms, tried in Phase 2 (DP105).

### In the S2 build

These are explained in the S2 findings, and those still to do are in task P1-T16.

* The counties step is slow for France, so stage 1's whole run with the new methods has not been finished or compared with 1 November.
* Antarctica's area is 1.7% over Wikidata's figure, so it fails the 1% check. The ice shelves are counted as land, and Wikidata's figure probably leaves some out. The world build needs its own figure for Antarctica.
* Kiribati's and Fiji's areas are over Wikidata's, because lagoons, lakes and wetlands inside the coast count as land. Taking away the water mapped in OSM brings them to 2.3% and 1.6% over.
* OSM holds Sevastopol twice, as Ukraine's and as Russia's. The build keeps one, as agreed in DP104, from Phase 1.
* Antarctica has 78 km of artificial edge along the 180 degree line on one side only. Its cause is not found.
* The globe check flagged Alaska's long straight border with Canada as a fault. The check should look only near the 180 degree line.
* Stage 4, Argentina, is parked.

## What was not tested

* Chrome and Edge with NVDA. The automatic tests run in Chromium and Firefox, and spike S3 also ran in Edge.
* A Braille display with TobyMap, until you run part 7.
* JAWS and Narrator.
* The macOS version. Its automatic tests run on every push, but nobody has opened it.
* The web version of the sound demo, by ear. Sound while moving is tested in Phase 1.
* Piper in the browser, by ear, until you run part 10. Its timings are measured automatically.
* Publishing to GitHub Releases or Hugging Face. Nothing has been published yet, as you chose.
* A slower computer or a phone. Every timing in this phase is from this laptop.
* In spike S4, only the lookup was timed in the browser, on the Norway and Sweden pack. Describing the place and drawing the map were not timed with it.
* The S2 build on the whole world. Phase 0 built three groups of countries. The whole world comes in Phase 1 and Phase 3.

## Automatic exit checks

Section 3 of the implementation plan lists three.

1. Continuous integration is green on Windows, macOS and the web, in Chromium and Firefox. Passed on main on 2 November (run 41538045166), with the Windows installer. It is run again on this report's branch before merging.
2. The licence check runs and passes: 43 packages, on 3 November.
3. The S2 checks in architecture 12.3 pass, or each failure is explained in the findings with a proposed fix. All place checks pass, in all three stages. The area checks for Antarctica, Fiji and Kiribati fail; each is explained in the S2 findings, and the fixes are in P1-T16.

## Your acceptance, 3 November

You accepted Phase 0 and asked to move on to Phase 1. Your comments are below, each with its requirement ID (DEL-4) and where it goes. The implementation plan is now version 0.3.

### Needs work in Phase 1

* Holding an arrow key, then letting go, speaks a whole series of places (ANN-3). Only the latest place should be spoken. Added to P1-T10 and P1-T11, with a test that holds a key and checks what is spoken after it is released.
* The Information panel tells NVDA that every item is level 1 (INF-10). It should give each item's level. Added to P1-T10, with the fix for the item not being read after R or Shift+Space.
* D goes to Details from the map, but not from the Information panel, where a letter moves to the next item starting with that letter (ACC-2). You want keys that move between regions from any region. Added to P1-T8, and discussion point 106 suggests the keys.
* Distances in Nearby should go to the nearest point of each country, not its label point (INF-3, INF-7). At the Canadian side of Niagara Falls, the USA should be under a mile away, not hundreds. Added to P1-T5 and P1-T7, with Niagara Falls as a test.
* Building country and county shapes must be faster, with an agreed approach (DMT-7). Added to P1-T16, and discussion point 107 suggests the approach and time limits.

### Needs work in Phase 2

You asked for these in the Phase 1 plan, but the parts they belong to are built in Phase 2, so they are recorded there.

* The first word from Piper in Firefox may not be heard; after that the voice is fine. The voice is built into TobyMap in P2-T7, which now makes sure the first label is heard.
* Whether shapes are outlined, and what colours fill them, could be a display setting: for example outlines only, or the same colour for every country (VIS-2). The themes are built in P2-T12, and discussion point 108 suggests the setting. On the map now, each country is filled with one of a few colours, chosen so neighbours differ, with a thin outline; the country under the centre has a thicker outline.

### No change needed

* Desktop, part 4.4: from the menu bar, Tab moves along the menus, Map, Speech and Help, and Escape leaves it. You said this is normal desktop behaviour and fine (ACC-2). Alt also leaves the menu bar in Windows programs, so Escape is not the only way (ACC-7). Phase 1's checklist confirms this.
* Shapes near the edge of the globe look squashed, as the Earth does from space (VIS-5). That is as it should be.
* Piper's Alba voice in Firefox is fine (part 10).
* You are happy with the S2, S4 and S6 findings (part 11).
