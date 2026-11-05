# Phase 1 checklist: desktop version

This is the third pass of the desktop checklist, for you to work through with NVDA on Windows 11. The web version has its own checklist, docs/checklists/phase-1-web.md.

For each step, write down its number, such as 4.3, and either "works" or what you heard instead. Put your notes in a text file, as you did last time.

The expected words below are what the program says on the world pack, the base pack lite. It has countries and their first-level divisions, but no counties, so you hear "England, United Kingdom", not "Kent" (DP121).

Set Distances to Metric before you start (Settings, Units). The directions below assume metric, except where a step says otherwise.

## The third pass: only what changed

Your second pass found these, and they are fixed in version 0.0.9. You need only do these steps; the rest passed last time.

* Install 0.0.9 over 0.0.8: step 1.1.
* The keys dialog, F1: its first lines are short, and each line is one Down arrow: step 2.1.
* Keys with a symbol are said as a word, such as "Ctrl+Comma": steps 2.1, 2.7 and 2.8.
* The first click after start is as loud as the others: step 3.2, straight after starting TobyMap.
* Coordinates have only the decimal places the step needs, with a setting to always have them all: steps 7.2, 7.3 and 7.3a.
* The zoom keys say only the zoom, and the step keys only the step: section 10.
* In Settings, OK comes before Cancel in the Tab order: step 11.4.
* In Help, The sounds, Space plays the sound as well as Enter: step 12.7.

Three of your notes are new discussion points, for you to answer in the discussion points file:

* DP139: NVDA says "H" before the place after H then Space. This is NVDA's word echo; there is a setting to try.
* DP140: the uneven clicks when holding an arrow key, and making the drawing faster.
* DP141: Enter in the announcement history to go to that place.

Your note to improve the bump sound is yours to do: put your new bump.wav in place of the old one and it is used.

## How to start TobyMap at a place

Many sections start at a given place. Close TobyMap if it is running, press Windows+R, and type the line given, such as:

`%LOCALAPPDATA%\Programs\TobyMap\TobyMap.exe --at 51.2,1.2`

TobyMap keeps your last zoom and step size. Several sections need a step of 25 kilometres: press Shift+Page Up or Shift+Page Down until you hear "step 25 kilometres".

## 1. Install and start (DEL-5, PLT-1, PLT-3)

* 1.1 Run the installer, dist_installer\TobyMap-0.0.9-setup.exe. It installs without asking for administrator rights.
* 1.2 Start TobyMap from the Start menu. It says "TobyMap", the place, then "Press F1 for keys".
* 1.3 Close TobyMap. Unzip dist_installer\TobyMap-0.0.9-portable.zip into a folder of your choice and run TobyMap.exe from it. It does the same as 1.2. Close it.
* 1.4 Leave TobyMap installed for the rest of the checklist. Section 14 uninstalls it at the end.

## 2. Keys and regions (ACC-2, ACC-3, ACC-7)

* 2.1 Press F1 on the map. It lists the map's commands with their keys. The first three lines are short sentences, and one Down arrow moves past each. Settings is listed as "Settings: Ctrl+Comma".
* 2.2 Press F2, F3 and F4 from each region. They go to the map, the Information panel and Details.
* 2.3 Press Shift+F1 to start the key describer. On the map, press Up, Page Up and a key with no command. Each is described and nothing happens.
* 2.4 With the describer still on, press Tab. It is described, and focus stays where it is.
* 2.5 Press F3 to go to the Information panel, then press Down. It is described, and the panel does not move. Do the same in Details with F4.
* 2.6 Press Shift+F1 again to leave the describer. Tab moves between regions again.
* 2.7 Press Alt to reach the menu bar. Tab along its menus. Alt or Escape leaves it. In the Settings menu, Settings has the key Ctrl+Comma.
* 2.8 Open Settings with Ctrl+Comma. It has OK and Cancel buttons, and you can leave with either. On the Keys tab, Settings is "Settings: Ctrl+Comma".
* 2.9 In Settings, change the key of Heading to a free key, press OK, and check the new key works.
* 2.10 Change the key of Heading to Space, which Where am I has. NVDA says "Space is already used by Where am I. Choose another key." Put Heading back to H.

## 3. Stepping across the Channel (NAV-1, NAV-2, LOC-2, ANN-1)

Start with `--at 51.2,1.2`, and set the step to 25 kilometres.

* 3.1 Press Down. You hear: "North Atlantic Ocean".
* 3.2 Press Right. You hear the click (nothing changed). This is the first click since TobyMap started, and it is as loud as the later ones.
* 3.3 Press Right. You hear: "Hauts-de-France, France".
* 3.4 Press Down three times. A click each time.
* 3.5 Press Left. A click. Press Left again. You hear: "North Atlantic Ocean".

## 4. Across the 180 degree line in Fiji (NAV-1)

Start with `--at -16.5,179.99`, step 25 kilometres.

* 4.1 Press Space. You hear: "Northern, Fiji".
* 4.2 Press Right. You hear: "South Pacific Ocean".
* 4.3 Press Right twice, then Left twice. A click each time. You never get stuck or jump across the world.

## 5. Across the 180 degree line in the Bering Strait (NAV-1, LOC-2)

Start with `--at 66.0,-170.0`, step 25 kilometres.

* 5.1 Press Space. You hear: "North Pacific Ocean".
* 5.2 Press Left. You hear: "Chukotka Autonomous Okrug, Russia".
* 5.3 Press Left three more times. A click each time, with no jump.

## 6. The poles (NAV-1)

Step 25 kilometres for both.

* 6.1 Start with `--at 89.9,0`. Press Up twice. You hear the bump each time, and nothing is spoken.
* 6.2 Start with `--at -89.9,0`. Press Down twice. The bump each time. Press Space. You hear: "Antarctica".

## 7. Where am I, coordinates, heading and size (LOC-1, LOC-2, LOC-7, ANN-5)

Start with `--at 51.2,1.2`. Set the zoom to 5 kilometres and the step to 100 metres, with Page Up and Page Down for the zoom and Shift with them for the step.

* 7.1 Press Space. You hear: "England, United Kingdom".
* 7.2 Press C. You hear: "51.2000 degrees north, 1.2000 degrees east". With a step of 100 metres, four decimal places are enough. Set the step to 25 kilometres and press C: "51.2 degrees north, 1.2 degrees east". Set the step back to 100 metres.
* 7.3 In Settings, Units, set Coordinates to "Degrees, minutes and seconds", press OK, and press C. You hear: "51 degrees 12 minutes 0 seconds north, 1 degrees 12 minutes 0 seconds east". Seconds are whole unless the step is under about 30 metres. Set it back to decimal degrees.
* 7.3a In Settings, Units, set "Decimal places in coordinates" to "Always 5, or a tenth of a second", press OK, and press C. You hear: "51.20000 degrees north, 1.20000 degrees east". Set it back to "Fit the step size".
* 7.4 Press H. You hear: "Facing north. North-fixed. Stepping. Zoom 5 kilometres, step 100 metres."
* 7.5 Press V. You hear the visible map's width and height, such as "Visible map: 13 kilometres wide by 10 kilometres high." The numbers depend on the size of the window.
* 7.6 Maximise the window (Windows+Up) and press V again. The numbers are larger. Restore it (Windows+Down) and they go back.
* 7.7 In Settings, set Distances to Imperial and press OK. Press H. You hear: "Facing north. North-fixed. Stepping. Zoom 2.5 miles, step 100 yards."
* 7.8 Press Page Up and Page Down a few times, and Shift+Page Up and Shift+Page Down. Every size is a round number, such as 5 miles, 10 miles, 250 yards or half a mile. Tell me any that are not.
* 7.9 Set Distances back to Metric.

## 8. Nearby at Niagara Falls (INF-3, INF-7)

Start with `--at 43.08,-79.08`. In Settings, set Distances to Imperial and Directions to Clock face.

* 8.1 Press Space. You hear: "Ontario, Canada".
* 8.2 Press F3, then Down until you reach Nearby, and press Right to open it. Its first item is "United States, 0.3 miles 3 o'clock", then "New York, 0.3 miles 3 o'clock".
* 8.3 Set Distances back to Metric and Directions back to your usual choice.

## 9. The Information panel's levels (INF-10, DP135)

Start with `--at 51.2,1.2`.

* 9.1 Press F3. NVDA reads the first item in Within, "England", with "level 2", without you pressing Up then Down.
* 9.2 Press Down. "United Kingdom", level 2.
* 9.3 Press Down. "Nearby", level 1.
* 9.4 Press Right to open Nearby, then Down. Its first item, level 2.
* 9.5 Press Left. You go back to "Nearby", level 1. Press Left again. Nearby closes. Tell me what NVDA says, and whether it says "collapsed".
* 9.6 Press Up until you reach "Within", level 1. Each item is read once, with its level.

## 10. Zoom and step (NAV-2, NAV-13, LOC-7)

Start with `--at 51.2,1.2`. Set the zoom to 5 kilometres and the step to 100 metres.

* 10.1 Press Page Down. You hear: "Zoom 2.5 kilometres." Only the zoom is said, because only the zoom changed.
* 10.2 Press Page Up. You hear: "Zoom 5 kilometres."
* 10.3 Press Shift+Page Up. You hear: "Step 250 metres."
* 10.4 Press Shift+Page Down. You hear: "Step 100 metres."
* 10.5 From the Map menu, choose Link step to zoom. You hear: "Step linked to zoom. Zoom 5 kilometres, step 1 kilometre."
* 10.6 Press Page Down. You hear: "Zoom 2.5 kilometres, step 500 metres." Both are said, because linked, both changed.
* 10.7 Choose Link step to zoom again. You hear: "Step no longer linked to zoom. Zoom 2.5 kilometres, step 500 metres."

## 11. Held keys (ANN-3, DP129)

Start with `--at 51.2,1.2`, step 25 kilometres.

* 11.1 Tap Right quickly once. Exactly one step is taken. Tap it slowly a few times. Still one step per press.
* 11.2 Hold Right for two seconds and let go. After half a second you hear a click for each step, about 6 a second. When you let go, only the last place is spoken, with no queue of earlier places.
* 11.3 In Settings, Movement, change "Holding an arrow key: wait before repeating" to 1000 and "steps a second" to 3. Press OK and hold Right again. It waits longer and steps more slowly. Put both back to 500 and 6.
* 11.4 Open Settings and press Tab until you reach the buttons. They come in the order OK, Cancel, Export settings, Import settings. Enter in a field is OK.

## 12. Repeat, history, mute and sounds (ANN-4, SON-7, SON-8)

* 12.1 Press Down, then Space. The place is spoken both times.
* 12.2 Press Ctrl+Space. The last announcement is repeated.
* 12.3 Press Ctrl+Shift+Space. The history of announcements opens. Close it with its Close button.
* 12.4 Press Ctrl+M. You hear: "Sound muted." Step to where nothing changes. No click plays.
* 12.5 Press Ctrl+M again. You hear: "Sound on." The click comes back.
* 12.6 The click is your click.wav and the bump is your bump.wav.
* 12.7 Open Help, then The sounds. Choose Tick in the list and press Enter, Space, or the Play button. You hear your click each time. Do the same for Blocked, and you hear your bump. Enter and Space do not close the dialog; the Close button does.

## 13. Settings kept, the map window, help (PLT-5, VIS-1, VIS-4)

* 13.1 Change the units, step to somewhere new, close TobyMap and start it from the Start menu, without --at. Your settings and place are back.
* 13.2 With sight, or a helper: the globe shows, with a centre cross, a heading arrow and the current area's outline.
* 13.3 Click on the map. The location moves there and the place is spoken.
* 13.4 Help, then About TobyMap. It gives the version, 0.0.9.
* 13.5 Help, then Copy diagnostics. Paste into a text file. It has a test trace.
* 13.6 If you have time: Speech, then Send a Braille-only message. It shows in NVDA's Braille viewer (NVDA menu, Tools, Braille viewer) and is not spoken.

## 14. Uninstall (DEL-5)

* 14.1 Uninstall TobyMap from Windows Settings, Apps. It goes cleanly, and TobyMap is gone from the Start menu.

## Finishing

When you have been through it, send me your notes. If you accept the desktop version, and the web version passes its own checklist, I ask whether to publish (DP110), raise the version to 0.1.0 and make the first release. That completes Phase 1.
