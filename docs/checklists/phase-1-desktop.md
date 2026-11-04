# Phase 1 checklist: desktop version only

This is for you to work through with NVDA on Windows 11. It covers the desktop version only. The web version, and the web steps in docs/checklists/phase-1.md, wait until later.

For each step, tick it if it is as described. If not, write down what you heard or saw, with the step's number such as 4.3. Put your notes in a text file or in the discussion points file.

The expected words come from the approved wording in the acceptance scripts. If a step does not match, say so and I will check whether the words or the program are wrong.

## 0. Before you start

* [ ] 0.1 Check the program has the Phase 1 keys. Start it (step 1.2), then press F2, F3 and F4. If nothing moves between regions, stop and tell me.
* [ ] 0.2 Make sure NVDA is running, and that NVDA's Braille viewer is open if you have no display (NVDA menu, Tools, Braille viewer).

## 1. Install and start (DEL-5, PLT-1, PLT-3)

* [ ] 1.1 Build the installer with the world pack: `.\packaging\build.ps1 -Pack E:\osmdata\tobymap\output\world\world.pack`. The result is in dist_installer.
* [ ] 1.2 Run the installer, then start TobyMap. It says where you start, then "Press F1 for keys".
* [ ] 1.3 Close TobyMap and start the portable zip from dist_installer instead. It does the same.
* [ ] 1.4 Uninstall TobyMap from Windows Settings. It goes cleanly.

Until the installer is rebuilt, you can run from the repository: `.venv\Scripts\python.exe -m desktop --pack E:\osmdata\tobymap\output\world\world.pack`.

## 2. Keys and regions (ACC-2, ACC-3, ACC-7)

* [ ] 2.1 Press F1 on the map. It lists the map's commands with their keys.
* [ ] 2.2 Press Shift+F1 to start the key describer. Press Up, Page Up, and a key with no command. Each is described and nothing is carried out. Press Shift+F1 again to leave it.
* [ ] 2.3 Press F2, F3 and F4 from each region. They go to the map, the Information panel and Details.
* [ ] 2.4 Press Alt to reach the menu bar. Tab along its menus. Alt or Escape leaves it.
* [ ] 2.5 Open Settings with Ctrl+Comma. It has OK and Cancel buttons, and you can leave with either.
* [ ] 2.6 Change the key of Heading to one that is free. Then try a key that is taken. You are told which command has it.

## 3. Stepping across the Channel (NAV-1, NAV-2, LOC-2, ANN-1)

Start at latitude 51.2, longitude 1.2, off the Kent coast.

* [ ] 3.1 Press Down. You hear: "North Atlantic Ocean".
* [ ] 3.2 Press Right. You hear the tick sound (nothing changed).
* [ ] 3.3 Press Right. You hear: "Pas-de-Calais, Hauts-de-France, France".
* [ ] 3.4 Press Down twice. You hear the tick each time.
* [ ] 3.5 Press Down. You hear: "Somme".
* [ ] 3.6 Press Left twice. The first is a tick. The second is "North Atlantic Ocean".

On the world pack the wording can differ from the test pack. Tell me what you hear.

## 4. Across the 180 degree line in Fiji (NAV-1)

Start at latitude -16.5, longitude 179.99.

* [ ] 4.1 Press Right three times, then Left twice. You never get stuck or jump across the world.
* [ ] 4.2 Press Space. You hear the name of a division in Fiji, such as "Cakaudrove, Northern, Fiji".

## 5. Across the 180 degree line in the Bering Strait (NAV-1, LOC-2)

Start at latitude 66.0, longitude -170.0.

* [ ] 5.1 Press Left. You hear a district in Chukotka, Russia.
* [ ] 5.2 Press Left again, and again. You cross into the sea or another district without a jump.

## 6. The poles (NAV-1)

* [ ] 6.1 Start at latitude 89.9, longitude 0. Press Up twice. You hear the blocked sound each time, and nothing is spoken.
* [ ] 6.2 Start at latitude -89.9, longitude 0. Press Down twice. Blocked each time. Press Space. You hear: "Antarctica".

## 7. Where am I, coordinates and heading (LOC-1, LOC-2, LOC-7, ANN-5)

Start at latitude 51.2, longitude 1.2.

* [ ] 7.1 Press Space. You hear the place, such as "Kent, England, United Kingdom". On the base pack lite it may say only "England, United Kingdom" (DP121).
* [ ] 7.2 Press C. You hear: "51.20000 degrees north, 1.20000 degrees east".
* [ ] 7.3 Open Settings, change Coordinates to degrees, minutes and seconds, press OK, and press C. You hear: "51 degrees 12 minutes 0.0 seconds north, 1 degrees 12 minutes 0.0 seconds east".
* [ ] 7.4 Press H. You hear: "Facing north. North-fixed. Stepping. Zoom 5 kilometres, step 250 metres."
* [ ] 7.5 In Settings, change Units to imperial, press OK, and press H. You hear miles and yards: "Zoom 3.1 miles, step 270 yards."
* [ ] 7.6 Press V. You hear the size of the visible map.

## 8. Nearby at Niagara Falls (INF-3, INF-7)

Start at latitude 43.08, longitude -79.08. Set Units to imperial and Direction to clock.

* [ ] 8.1 Press Space. You hear: "Niagara Region, Ontario, Canada".
* [ ] 8.2 Press F3. In the Nearby group there is "United States, 0.3 miles 3 o'clock".

## 9. Zoom and step (NAV-2, NAV-13, LOC-7)

Start at latitude 51.2, longitude 1.2. These words are from the test pack's zoom and step lists. Tell me if yours differ.

* [ ] 9.1 Press Page Down. You hear: "Zoom 2.5 kilometres, step 100 metres."
* [ ] 9.2 Press Page Up. You hear: "Zoom 5 kilometres, step 100 metres."
* [ ] 9.3 Press Shift+Page Up. You hear: "Zoom 5 kilometres, step 250 metres."
* [ ] 9.4 Press Shift+Page Down. You hear: "Zoom 5 kilometres, step 100 metres."
* [ ] 9.5 From the menu, choose Link step to zoom. You hear: "Step linked to zoom. Zoom 5 kilometres, step 1 kilometre."
* [ ] 9.6 Press Page Down. You hear: "Zoom 2.5 kilometres, step 500 metres."
* [ ] 9.7 Choose Link step to zoom again. You hear: "Step no longer linked to zoom."

## 10. Repeat, history and mute (ANN-4, SON-7)

* [ ] 10.1 Press Down, then Space. The place is spoken both times.
* [ ] 10.2 Press Ctrl+Space. The last announcement is repeated.
* [ ] 10.3 Press Ctrl+Shift+Space. The history of announcements opens or is read.
* [ ] 10.4 Press Ctrl+M. You hear: "Sound muted." Step. No tick plays.
* [ ] 10.5 Press Ctrl+M again. You hear: "Sound on." Step. The tick comes back.

## 11. Held keys (ANN-3)

* [ ] 11.1 Hold Right for two seconds and let go. Only the last place is spoken, with no queue of earlier places, and it cuts off anything still being said.

## 12. The Information panel (INF-10)

* [ ] 12.1 Press F3. NVDA says the item and its level, such as "level 2", and reads the item without you pressing Up then Down.
* [ ] 12.2 Move through the panel with Up and Down. Each item is read once, with its level.

## 13. Settings kept (PLT-5)

* [ ] 13.1 Change the units, step to somewhere new, close TobyMap and open it again. Your settings and place are back.

## 14. Sounds (SON-7, SON-8)

* [ ] 14.1 Open Help, then The sounds. The earcons and their file names are listed.
* [ ] 14.2 The tick and the blocked sound are clearly different from each other, and neither is annoying when repeated.

## 15. The map window (VIS-1, VIS-4, VIS-5)

For this you need sight, or a helper.

* [ ] 15.1 The globe shows, with a centre cross, a heading arrow and the current area's outline.
* [ ] 15.2 Click on the map. The location moves there and the place is spoken.
* [ ] 15.3 Use the mouse wheel. The zoom changes and is spoken.
* [ ] 15.4 Fiji and Russia draw as single shapes across the 180 degree line.

## 16. Braille (ACC-1)

* [ ] 16.1 Every announcement above also shows on your Braille display or in NVDA's Braille viewer.
* [ ] 16.2 Choose Speech, then Send a Braille-only message. It shows in Braille and is not spoken.

## 17. Help and diagnostics (PLT-5)

* [ ] 17.1 Help, then About TobyMap. It gives the version.
* [ ] 17.2 Help, then Copy diagnostics. Paste into a text file. It has a test trace.

## 18. The listening test (SON-1, SON-9)

* [ ] 18.1 Run `.venv\Scripts\python.exe -m tools.listening_test --name yourname`. Work through all the blocks.
* [ ] 18.2 Send me the results file in docs\spikes\listening-test. I will analyse it and propose the sound settings.

## Finishing

* [ ] 19.1 Write your comments against the step numbers.
* [ ] 19.2 When you accept, I ask whether to publish (DP110), bump the version to 0.1.0 and make the release. Still to do before then: the installer with the world pack, the continuous integration installer run, and the Pages deployment (P1-T14).
