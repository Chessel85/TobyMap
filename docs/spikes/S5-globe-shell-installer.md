# Spike S5 findings: the globe, the accessible window and the installer

Task P0-T8, 31 October 2026. Architecture section 12.6.

## The questions

1. Does the four-region window work well with NVDA, on the desktop and on the web?
2. Can the globe be drawn fast enough?
3. Does the Windows installer work?

## Short answers

* The window: built on both, and every automatic check passes. You tried it with NVDA on the desktop and in Firefox, and it mostly worked. Four problems you found are fixed, and one is still open. See "Results of your NVDA test".
* The globe: yes, with one condition. Each frame must be kept to about 10,000 points, which the planned drawing levels already do (architecture 6.9).
* The installer: yes. It installs, starts, and uninstalls cleanly, without an administrator prompt.

## What was built

### The same window twice

The desktop version (PySide6) and the web version (Firefox or Chrome) both have the four regions from UX section 2:

1. The map: a globe of the world's countries, centred on the current location, with a small cross at the centre.
2. The Information panel: a tree with three groups.
   * Within: the country under the centre, then Earth.
   * Nearby: the eight nearest countries, with distance and direction.
   * Crossed and passed: empty, to test how an empty group sounds.
3. Details: read-only text about the country under the centre, or about the item selected in the tree.
4. The menu bar: Map, Speech and Help menus.

Tab and Shift+Tab move between the four regions and wrap round. Reaching the menu bar with Tab opens the Map menu. Tab again closes it and goes back to the map. DP93 asks whether that feels right.

### One core for both

Everything the two versions say, and every key and menu entry, comes from the shared core:

* the command registry, mapcore/commands/registry.yaml;
* the wording, mapcore/describe/templates.yaml;
* the globe drawing, mapcore/render/globe.py.

The web version runs the same Python core in the browser using Pyodide, in a background worker. Neither shell contains any map logic, wording or key handling of its own (AD-1, AD-2, AD-3).

### The world data

The globe uses Natural Earth's countries at 1:110 million: 177 countries and about 10,000 points. Natural Earth is public domain. A new pipeline command, mapdata world-sample, makes the small file from the Natural Earth download. Real packs replace it in Phase 1.

### The keys

These keys work when the map has focus:

* Arrow keys: turn the globe north, south, west or east, by the current step.
* Page Up and Page Down: zoom out and in. There are five zooms, with steps of 10, 5, 2 and 1 degrees, then half a degree.
* Space: where am I. The country, the coordinates, the zoom and the step.
* C: coordinates only.
* V: the size of the visible map, such as "Visible map: 1,140 by 890 kilometres." At the first zoom it says "Visible map: the whole globe."
* Shift+Space: go to Within in the Information panel.
* R: go to Nearby in the Information panel.
* D: go to Details.
* Ctrl+Space: repeat the last announcement.
* F1: the keys, in a dialog with a Close button. F1 works anywhere.
* Ctrl+Alt+Space: go to the map, from anywhere (DP97).

To reach the menu bar:

* Desktop: Alt, or Alt+M, Alt+S or Alt+H for one menu.
* Web: Ctrl+Alt+M goes to the Map menu, without opening it (DP93).

Menu only:

* Speech, Send a Braille-only message.
* Help, Drawing speed. It reports how long the last frame took and how long start-up took.
* Help, About TobyMap.
* Map, Exit, on the desktop.

A mouse click on the globe moves the centre there and says the country.

Turning stops at the poles in this spike ("North Pole. Sea"). Crossing a pole properly comes with stepping in Phase 1.

## How to try it

### Desktop: install it

1. Run TobyMap-0.0.5-setup.exe from the dist_installer folder in the repository.
2. Windows SmartScreen may say the app is unrecognised, because it is not signed. Choose More info, then Run anyway (DP95).
3. The installer has four standard pages: Welcome, Install location, Installing, and Finished. There is no administrator prompt. It installs into your own Programs folder.
4. On the last page, "Start TobyMap now" is ticked. You can also tick "Put a shortcut on the desktop".
5. Afterwards, TobyMap is in the Start menu. Uninstall it from Settings, Apps, or with "Uninstall TobyMap" in its folder.

There is also a portable zip, TobyMap-0.0.5-portable.zip. Unzip it anywhere and run TobyMap.exe.

### Web: on this laptop

1. In PowerShell, in the repository folder, run: `.venv\Scripts\python.exe tools\serve_web.py`
2. Your default browser opens http://127.0.0.1:8765/index.html. Open the same address in the other browser too.
3. It says "Loading TobyMap" for about 10 seconds, then announces the start.
4. To compare announcement methods (DP94), add `?announcer=live` to the address: http://127.0.0.1:8765/index.html?announcer=live
5. Press Ctrl+C in the PowerShell window to stop.

The web version is not on GitHub Pages yet. That comes in Phase 1.

## What to try with NVDA

Please try each of these in the desktop version, then in Firefox and Chrome.

### Start-up

* You should hear "TobyMap globe. United Kingdom. Press F1 for keys.", with focus on the map.
* In the browsers, NVDA should switch to focus mode on the map by itself, because the map is an application region.

### Turning the globe

* Press Down: "Spain". Right: "France" (Corsica). Keep going and listen.
* Hold an arrow key down. Speech should keep up and say only the latest country, never a backlog (ANN-3).
* Press Space for where am I, and C for coordinates.
* Press Page Down a few times, then turn again. The step gets smaller.
* Press Ctrl+Space to repeat.

### Moving between regions

* Tab: Information panel. Tab: Details. Tab: back to the map. Tab does not reach the menu bar (DP93).
* Shift+Tab goes the other way.
* From the menu bar, or an open menu, Tab goes to the map and Shift+Tab goes to Details.
* Does NVDA say the name of each region as you arrive?

### The Information panel

* From the map, press Shift+Space. You should land on "United Kingdom" inside Within.
* Use the arrow keys: Up and Down, Right to open a group, Left to close it or go to its parent.
* Press R from the map to go straight to Nearby.
* As you move through Nearby, Details changes to the selected country. On the screen, that country turns yellow.
* Does NVDA announce the level, the position, such as "2 of 8", and whether a group is open or closed?

### Details

* Press D from the map. Read it line by line with the arrow keys.

### Braille

* With your Braille display connected, choose Speech, then Send a Braille-only message.
* Desktop: the display should show "TobyMap Braille test: United Kingdom", with nothing spoken.
* Web: a web page cannot send Braille-only messages, so you hear an explanation instead.

### The F1 dialog

* Press F1. Read the list of keys. Tab to Close, and press Enter or Space.
* You should be back on the map. Escape also closes it, but it is never needed.

### Please report

* anything not spoken, spoken twice, cut off or late;
* anything where focus was lost or went somewhere unexpected;
* your answers to DP93 to DP96.

## Results of your NVDA test, 31 October 2026

You tested the desktop version and Firefox with NVDA. You have no Braille display, so the Braille-only message is still untested.

### Worked in both

* The start announcement, with focus on the map.
* Turning, including holding an arrow key: speech kept up.
* Where am I, coordinates, repeat, and zoom.
* The F1 dialog and its Close button.
* Details, read line by line.
* In Firefox, the Information panel announced correctly.

### Found, and fixed since

* On the desktop, arriving on the map said "Map grouping". Firefox said "Map". You preferred to hear just where you are.
  * Fix: the map is now named after the place under the centre, such as "United Kingdom", in both versions.
  * On the desktop it is now a pane, a role NVDA does not announce.
  * The name changes only while the map does not have focus, so turning never makes NVDA say the place twice.
* On the desktop, the menus had no Alt keys.
  * Fix: Alt+M opens Map, Alt+S opens Speech, and Alt+H opens Help.
  * The letters are in the command registry. The web version does not use them, because the browser keeps Alt for its own menus.
* On the desktop, NVDA was silent when moving between closed groups in the Information panel.
  * Cause: Qt 6.12 does not refresh the list of tree items it gives screen readers when a group is closed. The closed group's children stayed in that list, and Qt reported focus on a hidden item.
  * Fix: the window tells Qt to rebuild the list whenever a group opens or closes. A new test reproduces the fault and checks the fix.
* In Firefox, Details possibly started on the bottom line.
  * Fix: the caret is put on the first line whenever Details changes, and before focus arrives. Tests check this for both D and Tab.

### Still open

* Say current line in Firefox. See the second test, below.

### Your answers

* Announcement methods (DP94): you could not tell ariaNotify and the live regions apart. So the web version keeps ariaNotify, with the live regions as the fall-back.

## Results of your second test, 1 November 2026

### Fixes confirmed

* The map is named after the place, on the desktop and in Firefox.
* Alt+M, Alt+S and Alt+H on the desktop.
* NVDA speaks closed groups in the desktop Information panel.

### Found, and fixed since

* On the desktop, with Germany selected, NVDA read some lines of Details twice when arrowing down: sovereign state, population estimate, label point and source.
  * Cause: those lines were too long for the narrow Details box, so each wrapped onto two or more screen lines. NVDA read the whole entry again on each screen line.
  * Fix: Details no longer wraps, so each entry is one line, and the side panel starts wider. A new test checks that every entry for Germany is one line, even in a small window.
* Tab no longer goes to the menu bar, as you asked in DP93. It moves round the map, the Information panel and Details.
  * The desktop reaches the menu bar with Alt.
  * The web version has Ctrl+Alt+M, which goes to the Map menu without opening it. Its key is in the command registry, for the web only.
  * Tab leaves the menu bar or an open menu for the map, so Escape is still never needed.

### Still open

* Say current line, NVDA+Up arrow, is silent in Firefox in the Information panel and in Details, in focus mode. It works on the desktop.
  * The cause is not known, and I cannot test with NVDA myself.
  * A small test page, tools\spikes\s5\say_line.html, shows two versions of Details and two of the tree. Open it straight from File Explorer in Firefox, with no server needed. Pressing NVDA+Up on each one will show which version Firefox reads.
  * Details 1 and Tree 1 are as in TobyMap now. Details 2 is a text box that refuses typing but is not marked read-only to Firefox. Tree 2 has each item's words directly inside it.
* A key to go to the map from anywhere (DP97).

## Results from the automatic checks

### Desktop

* 27 desktop tests run the window offscreen with a recording announcer. They cover:
  * the start announcement;
  * Tab round all four regions, and back;
  * arrow keys in the map turning the globe;
  * arrow keys in the tree leaving the globe alone;
  * Shift+Space, R and D;
  * the menus coming from the registry;
  * the Braille-only message, and the spoken fallback when NVDA is not found;
  * the F1 dialog and its Close button;
  * mouse clicks;
  * painting speed.
* The built TobyMap.exe started and kept running. It used 64 MB of memory.

### Web

* 13 browser tests pass, each run in both Chromium and Firefox. They cover:
  * the start announcement;
  * the globe being painted;
  * Tab round the four regions;
  * real keyboard focus on tree items, with no aria-activedescendant;
  * Details;
  * the menu bar and its Tab behaviour;
  * the F1 dialog;
  * mouse clicks;
  * ten rapid key presses all being carried out, with only the last spoken;
  * the live region fallback.

### Speed

The time to work out the globe, and then to paint it, at 1200 by 900 pixels, as the median of ten frames on this laptop:

* Natural Earth 1:110 million, whole globe, about 8,600 points drawn: 4 ms to work out, 39 ms to paint on the desktop.
* The same, zoomed in 16 times, about 800 points: 3 ms and 6 ms.
* Natural Earth 1:50 million, whole globe, about 80,000 points: 16 ms and 330 ms.
* Natural Earth 1:10 million, whole globe, about 440,000 points: 69 ms and 1.6 seconds.
* In the browser, at 1:110 million: 6 to 12 ms to work out. Painting took 4 to 5 ms in Chromium and about 45 ms in Firefox. Firefox in the tests has no graphics card, so it is probably faster on your screen.
* Finding the country under the centre takes well under 1 ms.

What this means:

* Working out the globe in NumPy is fast, even in the browser.
* Painting is the slow part, and its time grows with the number of points.
* The 100 ms redraw target (VIS-1) is met when a frame has about 10,000 points or fewer.
* The drawing levels in architecture 6.9 are therefore essential, not optional. Each zoom must use the level that keeps the frame to about that size.

### Start-up of the web version

* It downloads about 17 MB the first time: Pyodide, NumPy and PyYAML.
* Start-up took 9 to 10 seconds in both browsers, measured by the application itself.
* Spike S4 looks at reducing this (DP96).

### The installer

* The installer is 40 MB. The portable zip is 59 MB. Installed, it takes 140 MB.
* A silent install into a test folder, then an uninstall, worked as follows:
  * the install created the program, the Start menu shortcut and the Add or Remove Programs entry;
  * the uninstall removed all three;
  * the uninstall kept a file that had been added to the folder, as intended.
* Continuous integration now builds the installer and zip on every push. They can be downloaded from the run's Artifacts section on GitHub.

## Things found along the way

* NumPy in the browser is 32-bit. The first web run failed because the globe used 64-bit numbers for its positions in arrays. The fix is in the core, and a test now guards it. This is an early lesson for spike S4: any core code that indexes arrays must use NumPy's own index type.
* Both Firefox and Chrome now support ariaNotify, a newer way for a page to speak through the screen reader. Architecture 4.4 assumed Firefox would need live regions. Both are in the code, and DP94 asks you to compare them.
* Held keys: the first web version dropped arrow presses that arrived while the core was busy. That broke ANN-3, which says every move is made and only the last is spoken. Now waiting moves are joined and all carried out, and only the last place is spoken. The joining is in the core, so it is tested once.
* The 180 degree line was drawn as a line across Antarctica. Natural Earth splits shapes there. The core now marks those edges as artificial, so they are filled but never outlined (AD-17).
* Making Qt points one at a time from NumPy was the slowest part of painting. Converting to a plain list first cut desktop painting by about a quarter.
* One web start-up in about 30 timed out during testing and could not be repeated. The likely cause is the test script checking too early, but it is noted in case it happens to you.

## Known problems

* Natural Earth at this scale puts French Guiana inside France and is coarse at coasts. Spike S2 deals with countries properly.
* The horizon is handled simply: shapes that go over the edge of the globe are squashed onto the edge. It looks right in the pictures checked, but very large shapes near the edge may look odd. Phase 1 can use exact clipping if needed.
* Distances in Nearby use a sphere rather than the WGS84 ellipsoid (AD-7), and are measured to each country's label point. The ellipsoid comes with stepping in Phase 1.
* The desktop does not yet tell screen magnifiers where the centre of the map is (ACC-8).
* The installed program is 140 MB. Qt files the shell does not use could be trimmed later.

## What was not tested

* Chrome with NVDA. You tested the desktop version and Firefox.
* A Braille display. The desktop code checks NVDA is running before sending, but no display was connected.
* The fixes listed under "Found, and fixed since" have not yet been heard with NVDA.
* JAWS, Narrator and Microsoft Edge.
* The macOS desktop version. Its automatic tests run in continuous integration, but nobody has opened it.
* An install into the normal Programs folder through the installer's pages. Only the silent install into a test folder was tried.

## Recommendation

* Keep the design: the core draws and the shells paint (AD-6), and the PyInstaller and NSIS installer comes first (AD-20).
* Keep the four-region shell pattern, subject to your NVDA test and DP93.
* Phase 1 must deliver the drawing levels of architecture 6.9 before larger data goes on the globe.
* Use NumPy's own index type throughout the core.
* The architecture changes, ariaNotify in Firefox and the drawing-level budget, go into P0-T11.

## Results of your third test, 1 November 2026

### Fixes confirmed

* Details reads each entry once on the desktop.
* Tab goes round the map, the Information panel and Details only.
* Alt reaches the desktop menu bar, and Ctrl+Alt+M the web one.
* Tab leaves the menu bar for the map.

### Say current line in Firefox

* With the test page, say current line worked in both versions of Details, but in only the second version of the tree, where each item's words are directly inside it.
* Fix: the web tree is now built that way. A group item is also named with aria-label, so that its name is just "Within", not all its items' words. A test checks this.
* Still to confirm with NVDA: say current line on a group item, such as Within, in TobyMap itself.

### Added since

* V says the size of the visible map, as you asked: across and up and down through the centre, along the Earth's surface. It follows the window's size. You chose V for the visible map, and Z for the grid value, which the draft keyboard map had on V (DP99).
* Ctrl+Alt+Space goes to the map from anywhere, in both versions (DP97). It is also in the Map menu, as "Go to the map". It says nothing itself, because NVDA reads the map's name, the place, on arrival.

### After your fourth test, 1 November

* Ctrl+Alt+G opened Firefox on your laptop, so going to the map is now Ctrl+Alt+Space, as you suggested. No Windows shortcut on your laptop uses Ctrl+Alt+G, so another program must be catching it.
* Shift+Space and R no longer reached the Information panel for you. I could not make this happen in Firefox or Chromium, so it may have been Ctrl+Alt+G opening a Firefox window and taking your later keys. Waiting for you to try again.

### After your fifth test, 2 November

* On the desktop, Shift+Space and R did move focus to the panel, because Tab then went on to Details. But NVDA+Up still said "United Kingdom" after R, until you pressed Up then Down.
* Cause 1: each time the panel is rebuilt, Qt 6.12 keeps its accessible list of the tree's items from before the rebuild. So the second time, every item NVDA could ask about was empty. The earlier fix refreshed that list only when a group was opened or closed.
* Cause 2: when focus moves into the tree with the item already chosen, Qt doesn't tell screen readers which item has focus. It only does that when the item changes while the tree has focus, as when arrowing.
* Tried in version 0.0.6: refreshing the list after every rebuild, then sending the screen reader the same "this item has focus" message that arrowing sends. It didn't fix the fault, and NVDA then reported every item in the tree as level 1, losing the level 2 of the items inside each group. The level matters, so the change was undone, and the program is back to version 0.0.5.
* Also tried and rejected: choosing the item after focus arrives. Qt first picks "Within", which NVDA would start to read.

### Known limitation, desktop

* After R or Shift+Space, NVDA doesn't read the item the panel has moved to. Pressing Up then Down makes NVDA read it.
* The hierarchy levels are reported correctly, and that is kept.
* Idea for Phase 1: change the panel's items in place instead of clearing and rebuilding the tree, so Qt's list of items for screen readers never goes out of date.
