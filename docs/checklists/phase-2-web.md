# Phase 2 checklist: web version

This is for you to work through with NVDA in Firefox, then the main steps again in Chrome or Edge. The desktop version has its own checklist, docs/checklists/phase-2-desktop.md. The parts that need sight are in docs/checklists/phase-2-sighted.md.

For each step, write down its number, such as 4.3, and either "works" or what you heard instead. Put your notes in a text file.

The web version uses the same world pack as the desktop, so the expected words are the same. Most sections below are the desktop checklist's sections done in the browser: do the steps there, with the differences listed here. The web version runs on this computer until you agree to publish (DP110).

## How to start the web version

* Open a terminal in the repository folder and run:

  `.venv\Scripts\python.exe tools\serve_web.py --pack E:\osmdata\tobymap\output\world\world.pack`

* It opens the web version in your default browser, at http://127.0.0.1:8765/index.html. Leave the terminal open while you test. Ctrl+C in the terminal stops it.
* To start at a place, add it to the address after a question mark, such as `http://127.0.0.1:8765/index.html?at=51.2,1.2`. Type it in the address bar (Alt+D or Ctrl+L) and press Enter.
* The map is an application to NVDA, so NVDA should switch to focus mode by itself. If arrow keys move NVDA's browse cursor instead of the map, press NVDA+Space.
* Set Distances to Metric and Directions to Compass with 8 points first, in Settings, Units.

## 1. First visit (DEL-1, PLT-2)

* 1.1 Open the address in Firefox. On the first visit of this version, the page reloads itself once, quickly. That makes it cross-origin isolated, so the voice can use four threads.
* 1.2 You hear "TobyMap", the place, then "Press F1 for keys".
* 1.3 On the map, press Tab and Shift+Tab: focus moves between the map, the Information panel and Details as before. Coming back to the map, NVDA says the place.

## 2. The same as the desktop

Do these sections of the desktop checklist, in Firefox. The keys and the words are the same.

* 2.1 Section 2, orientations and turning.
* 2.2 Section 3, typing a bearing.
* 2.3 Section 4, over the poles. Use `?at=89.9,0` and `?at=-89.9,0` in the address instead of --at.
* 2.4 Section 5, going to coordinates and back. Alt+Comma and Alt+Full stop work in Firefox; if your browser takes either key for itself, tell me.
* 2.5 Section 6, Enter in the announcement history.
* 2.6 Section 7, layers. The layer settings replace the list in the same dialog, and Cancel goes back to the list.
* 2.7 Section 8, Crossed and passed.
* 2.8 Section 10, the beacon.
* 2.9 Section 11, the graticule and its crossing sounds.
* 2.10 Section 12, holding an arrow key: the clicks are even in the browser too.
* 2.11 Section 13, the verbosity presets. In the web version Settings has a Speech tab, between Movement and Layers.

## 3. Hear its direction in the browser (SON-3, DP143, DP150, DP151)

Start with `?at=51.2,1.2`, zoom 100 kilometres. Use headphones if you can.

* 3.1 Do steps 9.1 to 9.5 of the desktop checklist. The first label after the page opens can take a few seconds, while the voice loads; after that, a short name takes about a fifth of a second and a name with its distance about half a second.
* 3.2 DP150 asks whether half a second is too slow. You parked it for this test: tell me how it feels.
* 3.3 A browser cannot send text to Braille without speaking it. So in the web version a label reaches NVDA, and your Braille display, only with "Also speak spatial labels through the screen reader" on, in Settings, Sound. Switch it on, and press Space on an item: NVDA speaks the label as well. As you agreed in DP151, it stays off at first, and the release notes tell a Braille user to switch it on.
* 3.4 Add `?threads=1` to the address and reload. The voice uses one thread: a label takes about a second. Remove it again.

## 4. Earcons and your own files in the browser (SON-8, DP123)

* 4.1 Open Settings, Earcons. It is the same as on the desktop.
* 4.2 On "Tick: your own sound file", press Choose file and choose a WAV file of your own. Press OK and step: your sound plays.
* 4.3 Reload the page with F5. Your sound still plays: it is kept in the browser.
* 4.4 Press Use the default, then OK. The default tick plays again.
* 4.5 Choose a file that is not a WAV sound. You are told it could not be read, and nothing is kept.

## 5. The sound design in the browser

Tell me whether the sound in space feels the same as on the desktop: direction, the lower pitch behind, loudness with distance, and HRTF if you try it.

## 6. Chrome or Edge

* 6.1 Open the same address in Chrome or Edge, and do sections 1 and 3, and steps 2.1 and 2.7.

## Finishing

When you have been through it, send me your notes, with the desktop's. If you accept both, I ask you about publishing (DP110).
