# Phase 0 report: foundations and spikes

Draft of 2 November 2026. This report is not finished, because three tasks are still open. Sections that wait for them say so. When they are done, the report is completed, continuous integration is checked, and the phase comes to you for acceptance.

## Where the phase stands

### Done

* P0-T1 Repository: TobyMap on GitHub, public, with the design documents in docs/design.
* P0-T2 Continuous integration: Python tests on Windows and macOS, browser tests in Chromium and Firefox, the licence check, and the Windows installer, on every push.
* P0-T3 Development set-up: setup.ps1, the requirements files, and the data folder setting.
* P0-T4 Spike S1, spatial sound. Decided (DP100).
* P0-T6 Spike S3, hosting and the browser. Decided (DP102).
* P0-T8 Spike S5, the globe, the accessible shell and the installer. Five NVDA tests done.
* P0-T10 Comparison with AtMap and AtlasDL: docs/design/lessons-from-atmap.md.

### Still open

* P0-T5 Spike S2, countries, coastlines and islands. Stage 1, the UK, France and Spain, is done. Stage 2, Sweden and Norway, and stage 3, the countries that cross the 180 degree line and Antarctica, need the laptop to be free for the heavy builds. Your DP101 answer, the record of each country's county levels, goes into the pipeline with them.
* P0-T7 Spike S4, the core in the browser. It times "where am I" and a step on the S2 pack in the web version, so it also needs the laptop to be free.
* P0-T9 Spike S6, the spatial voice. You chose Piper with the Alba voice. Piper in the browser is tried during spike S4.
* P0-T11 Update the architecture. Version 0.3 brings in everything decided so far. The rest follows S2, S4 and S6.

## What was built

### The shell, in two versions

* A desktop window (PySide6) and a web page (Pyodide in a worker), built from one shared core.
* Both have the four regions: the map, the Information panel, Details and the menu bar.
* The map is a globe of the world's countries, from Natural Earth, which turns with the arrow keys and announces the country under its centre.
* Every key and menu item comes from the core's command registry, and every word spoken comes from the core's wording file. Neither shell has its own.

### The Windows installer

* TobyMap-0.0.5-setup.exe, about 40 MB, which installs for you only, with no administrator prompt (DP95).
* A portable zip, TobyMap-0.0.5-portable.zip.
* Both are built by continuous integration on every push.

### The spike tools

* S1: the sound demo, tools\spikes\s1\demo.py, with six engines and a listening quiz.
* S2: the build command, mapdata spike-s2-stage1, and mapdata inspect, which says what is at a point in a pack.
* S3: the hosting and storage test page, tools\spikes\s3\run.py.
* S6: the voice demo, tools\spikes\s6\demo.py.

### The decisions

The findings for each spike are in docs/spikes. In short:

* Sound (S1): stereo with pitch by default, and HRTF with pitch as an option, from TobyMap's own processing.
* Hosting (S3): packs on GitHub Releases for the desktop, and a copy on Hugging Face for the web, downloaded whole into the browser's private storage.
* The shell (S5): the four-region pattern and the installer work. Each frame of the map must be kept to about 10,000 points.
* The voice (S6): Piper, with the Alba voice.
* Countries and coastlines (S2): stage 1 passed every check on the UK, France and Spain. The full results come with stages 2 and 3.

## How to install it

### The desktop version

1. Run TobyMap-0.0.5-setup.exe from the dist_installer folder in the repository.
2. Windows SmartScreen may say the app is unrecognised, because it is not signed. Choose More info, then Run anyway.
3. The installer has four pages: Welcome, Install location, Installing, and Finished. On the last page, "Start TobyMap now" is ticked.
4. TobyMap is then in the Start menu.

### The web version, on this laptop

1. In PowerShell, in the repository folder, run: `.venv\Scripts\python.exe tools\serve_web.py`
2. Firefox, or your default browser, opens http://127.0.0.1:8765/index.html.
3. It says "Loading TobyMap" for about 10 seconds, then announces the start.
4. Press Ctrl+C in the PowerShell window to stop.

The web version goes on GitHub Pages in Phase 1.

## Acceptance checklist

Run each part with NVDA, on the desktop version and then in Firefox. For each item, the expected result is given. Note anything that differs.

This checklist covers the shell and the installer. Checks for the S2 packs and spike S4 are added when those tasks are done.

### 1. Installing

1. Install with TobyMap-0.0.5-setup.exe. Expected: no administrator prompt, and TobyMap starts at the end.
2. Find TobyMap in the Start menu. Expected: it is there, with "Uninstall TobyMap" beside it in its folder.

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
6. Desktop: after Shift+Space or R, NVDA may not read the item until you press Up then Down. This is the known limitation below, not a new problem.

### 6. Details and help

1. From the map, press D. Expected: Details, starting at its first line. Arrow down. Expected: each line read once.
2. Press F1. Expected: the list of keys. Tab to Close and press Enter. Expected: back on the map.

### 7. Braille

1. With your Braille display connected, choose Speech, then Send a Braille-only message.
2. Desktop: expected "TobyMap Braille test: United Kingdom" on the display, with nothing spoken.
3. Firefox: expected a spoken explanation that a web page can't send Braille-only messages.

### 8. Uninstalling

1. Uninstall TobyMap from Settings, Apps. Expected: it is removed from the Start menu and from the list of apps.

## Known problems

* Desktop: after R or Shift+Space, NVDA doesn't read the item the Information panel has moved to until you press Up then Down. Qt keeps an out-of-date list of the panel's items for screen readers. In Phase 1 the panel's items are changed in place instead of being rebuilt.
* Natural Earth at this scale puts French Guiana inside France, and is coarse at coasts. The S2 countries replace it.
* Shapes that cross the edge of the globe are squashed onto the edge. Very large shapes near the edge may look odd.
* Distances in Nearby are measured on a sphere, to each country's label point. The ellipsoid comes with stepping in Phase 1.
* The desktop doesn't yet tell screen magnifiers where the centre of the map is (ACC-8).
* The web version takes about 10 seconds to start the first time. Spike S4 looks at this.
* Piper's first label took about 5 seconds. It is to be made silently at start-up in Phase 1.

## What was not tested

* Chrome and Edge with NVDA. The automatic tests run in Chromium and Firefox, and spike S3 also ran in Edge.
* A Braille display with TobyMap.
* JAWS and Narrator.
* The macOS version. Its automatic tests run on every push, but nobody has opened it.
* The web version of the sound demo, by ear.
* Publishing to GitHub Releases or Hugging Face. Nothing has been published yet, as you chose.
* Still to come in this phase: the S2 stages 2 and 3, spike S4, and Piper in the browser.

## Automatic exit checks

* Continuous integration was green on 2 November for spike S3: the Python tests on Windows and macOS, the browser tests in Chromium and Firefox, and the Windows installer.
* The licence check passes, for 43 packages.
* These are checked again on the final build, before the phase comes to you.
