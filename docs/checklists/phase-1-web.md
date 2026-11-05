# Phase 1 checklist: web version

This is for you to work through with NVDA in Firefox, then the main steps again in Chrome or Edge. It covers the web version only. The desktop version has its own checklist, docs/checklists/phase-1-desktop.md.

For each step, write down its number, such as 4.3, and either "works" or what you heard instead. Put your notes in a text file.

The web version runs on this computer for now. It goes on GitHub Pages only when you agree to publish (DP110). It uses the same world pack as the desktop, so the expected words are the same: "England, United Kingdom", with no counties (DP121).

## The second pass: only what changed

Your first pass found these, and they are fixed. You need only do these steps, in Firefox; the rest passed. The changes from the desktop's second pass are in the web version too, so also do section 7 (only what changed is said) and step 5.2 (fewer decimal places).

* Escape on the menu bar goes back to the map: step 2.4.
* Settings has tabs, one page for each group, like the desktop: step 2.6.
* Enter in a settings field is OK, and closes Settings: step 2.6.
* Tabbing into a number chooses the whole number, so typing replaces it: step 8.3.
* The sounds in Help are one list: Tab moves from the list to Play, then Close. Enter or Space plays: step 9.5.

## How to start the web version

* Open a terminal in the repository folder and run:

  `.venv\Scripts\python.exe tools\serve_web.py --pack E:\osmdata\tobymap\output\world\world.pack`

* It opens the web version in your default browser, at http://127.0.0.1:8765/index.html. Leave the terminal open while you test. Ctrl+C in the terminal stops it.
* To start at a place, add it to the address after a question mark, such as:

  `http://127.0.0.1:8765/index.html?at=51.2,1.2`

  Type it in the address bar (Alt+D or Ctrl+L) and press Enter.
* The map is an application to NVDA, so NVDA should switch to focus mode by itself. If arrow keys move NVDA's browse cursor instead of the map, press NVDA+Space.
* Several sections need a step of 25 kilometres: press Shift+Page Up or Shift+Page Down until you hear "step 25 kilometres". Your zoom and step are kept between visits.

## 1. First visit and loading (DEL-1, PLT-2)

* 1.1 Open the address in Firefox. A loading message is shown while the program starts.
* 1.2 On the first visit, you hear "Downloading the map for the first time. It is kept in this browser, so this happens once." Then, if it takes long enough, the percentage at most every 10 seconds.
* 1.3 When it is ready, you hear "TobyMap", the place, then "Press F1 for keys".
* 1.4 Reload the page with F5. The map is not downloaded again, and it starts faster.

## 2. Keys and regions (ACC-2, ACC-3, ACC-7)

* 2.1 Press F1 on the map. It lists the map's commands with their keys. Close it with its Close button.
* 2.2 Press F2, F3 and F4 from each region. They go to the map, the Information panel and Details.
* 2.3 Tab and Shift+Tab move between the map, the Information panel and Details.
* 2.4 Press Ctrl+Alt+M. You reach the menu bar, on Map. Left and Right move along the menus, and Down opens one. Escape in an open menu closes it, back to the menu bar. Escape on the menu bar goes back to the map.
* 2.5 Press Shift+F1 to start the key describer. Press Up, Page Up and a key with no command. Each is described and nothing happens. Press Tab: it is described and focus stays. Press Shift+F1 again to leave.
* 2.6 Open Settings with Ctrl+Comma, or from the Settings menu if the browser takes Ctrl+Comma. You are on a tab list: Units, Movement, Sound, Display and Keys. Left and Right move between the tabs, and Tab goes into the page. Only the chosen page is in the Tab order. There are OK and Cancel buttons, and you can leave with either. Change Distances on the Units page and press Enter: Settings closes, and the change is kept. Put it back.
* 2.7 In Settings, on the Keys tab, the commands are one list. Choose Heading, then the Change key button (or Enter on the list), and change the key to Space. You hear "Space is already used by Where am I. Choose another key." Leave it as H.

## 3. Stepping across the Channel (NAV-1, LOC-2, ANN-1)

Start with `?at=51.2,1.2`, step 25 kilometres.

* 3.1 Press Down. You hear: "North Atlantic Ocean".
* 3.2 Press Right. You hear the click (nothing changed).
* 3.3 Press Right. You hear: "Hauts-de-France, France".
* 3.4 Press Down three times. A click each time.
* 3.5 Press Left. A click. Press Left again. You hear: "North Atlantic Ocean".

## 4. The 180 degree line and the poles (NAV-1)

Step 25 kilometres throughout.

* 4.1 Start with `?at=-16.5,179.99`. Press Space: "Northern, Fiji". Press Right: "South Pacific Ocean". Press Right twice and Left twice: a click each time, with no jump.
* 4.2 Start with `?at=66.0,-170.0`. Press Space: "North Pacific Ocean". Press Left: "Chukotka Autonomous Okrug, Russia".
* 4.3 Start with `?at=89.9,0`. Press Up twice. The bump each time, and nothing is spoken.
* 4.4 Start with `?at=-89.9,0`. Press Down twice: the bump each time. Press Space: "Antarctica".

## 5. Where am I, coordinates, heading and size (LOC-1, LOC-7, ANN-5)

Start with `?at=51.2,1.2`. Set the zoom to 5 kilometres and the step to 100 metres.

* 5.1 Press Space. You hear: "England, United Kingdom".
* 5.2 Press C. You hear: "51.2000 degrees north, 1.2000 degrees east". With a step of 100 metres, four decimal places are enough.
* 5.3 Press H. You hear: "Facing north. North-fixed. Stepping. Zoom 5 kilometres, step 100 metres."
* 5.4 Press V. You hear the visible map's width and height, such as "Visible map: 13 kilometres wide by 10 kilometres high." The numbers depend on the size of the browser window.
* 5.5 In Settings, set Distances to Imperial. Press H. You hear: "Facing north. North-fixed. Stepping. Zoom 2.5 miles, step 100 yards." Set it back to Metric.

## 6. Nearby at Niagara Falls and the panel's levels (INF-3, INF-7, INF-10)

Start with `?at=43.08,-79.08`. In Settings, set Distances to Imperial and Directions to Clock face.

* 6.1 Press Space. You hear: "Ontario, Canada".
* 6.2 Press F3. NVDA reads "Ontario" in Within, with level 2.
* 6.3 Press Down until you reach "Nearby". NVDA says level 1, and that it is collapsed.
* 6.4 Press Right to open it. NVDA says expanded. Press Down: "United States, 0.3 miles 3 o'clock", level 2.
* 6.5 Press Left twice: back to Nearby, then Nearby closes.
* 6.6 Set Distances back to Metric and Directions back to your usual choice.

## 7. Zoom and step (NAV-2, NAV-13)

Start with `?at=51.2,1.2`, zoom 5 kilometres, step 100 metres.

* 7.1 Press Page Down. You hear: "Zoom 2.5 kilometres."
* 7.2 Press Page Up. You hear: "Zoom 5 kilometres."
* 7.3 Press Shift+Page Up. You hear: "Step 250 metres."
* 7.4 Press Shift+Page Down. You hear: "Step 100 metres."

## 8. Held keys (ANN-3, DP129)

Start with `?at=51.2,1.2`, step 25 kilometres.

* 8.1 Tap Right quickly once. Exactly one step is taken.
* 8.2 Hold Right for two seconds and let go. After half a second there is a click for each step. When you let go, only the last place is spoken, with no queue of earlier places.
* 8.3 Open Settings, go to the Movement tab, and Tab to "wait before repeating". The number is chosen as you arrive, so typing 1000 gives 1000, not 5001000. Cancel.

## 9. Repeat, history, mute and sounds (ANN-4, SON-7, SON-8)

* 9.1 Press Ctrl+Space. The last announcement is repeated.
* 9.2 Press Ctrl+Shift+Space. The history of announcements opens. Close it with its Close button.
* 9.3 Press Ctrl+M. You hear: "Sound muted." No click plays on a step. Press Ctrl+M again: "Sound on."
* 9.4 The click and the bump are your click.wav and bump.wav, the same as on the desktop.
* 9.5 Open Help, then The sounds. You are on a list of the sounds. Press Enter on Tick, then Down and Space on Blocked. You hear your two sounds. Tab goes to Play, then Close.

## 10. Settings kept and help (PLT-5)

* 10.1 Change the units and step somewhere new. Close the tab, then open http://127.0.0.1:8765/index.html again, without ?at. Your settings and place are back.
* 10.2 Help, then About TobyMap. It gives the version, 0.0.9.
* 10.3 Help, then Copy diagnostics. Paste into a text file. It has a test trace.

## 11. The second browser (PLT-2)

* 11.1 Open the same address in Chrome or Edge. The map downloads once for this browser.
* 11.2 Repeat steps 3.1 to 3.5, 6.2 to 6.4, and 8.2. Tell me anything that differs from Firefox.

## Finishing

When you have been through it, stop the server with Ctrl+C in its terminal, and send me your notes.
