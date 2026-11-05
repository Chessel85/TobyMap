# Phase 1 acceptance checklist

This checklist is made by tools/make_checklists.py from the acceptance scripts in tests/acceptance/scripts, so the words below are the words the automatic tests check. If you change any wording, tell me, and it goes back into the templates and the scripts.

For each part, do the steps in order and say what you heard. Write your answers in a text file or in the discussion points file, with the part's number.

## Part 1: Across the 180 degree line in the Bering Strait, in Chukotka

Requirements: NAV-1, ANN-1, LOC-2.

Start at latitude 66.0, longitude -170.0, with the zoom and step as given in the script file (the test pack).

1. Press Left. You hear: "Providensky urban district, Chukotka Autonomous Okrug, Russia".
2. Press Left. You hear: "Anadyrsky District".
3. Press Left. You hear the tick sound.

## Part 2: Across the Channel from England to France, then out into the Atlantic

Requirements: ANN-1, LOC-2, NAV-1, NAV-2.

Start at latitude 51.2, longitude 1.2, with the zoom and step as given in the script file (the test pack).

1. Press Down. You hear: "North Atlantic Ocean".
2. Press Right. You hear the tick sound.
3. Press Right. You hear: "Pas-de-Calais, Hauts-de-France, France".
4. Press Down. You hear the tick sound.
5. Press Down. You hear the tick sound.
6. Press Down. You hear: "Somme".
7. Press Left. You hear the tick sound.
8. Press Left. You hear: "North Atlantic Ocean".

## Part 3: Across the 180 degree line in Fiji

Requirements: NAV-1, ANN-1, LOC-2.

Start at latitude -16.5, longitude 179.99, with the zoom and step as given in the script file (the test pack).

1. Press Right. You hear the tick sound.
2. Press Right. You hear the tick sound.
3. Press Right. You hear the tick sound.
4. Press Left. You hear the tick sound.
5. Press Left. You hear the tick sound.
6. Press Space. You hear: "Cakaudrove, Northern, Fiji".

## Part 4: Nearby at Niagara Falls, the United States under a mile away

Requirements: INF-3, INF-7, LOC-2.

Start at latitude 43.08, longitude -79.08, with the zoom and step as given in the script file (the test pack).

1. Press Space. You hear: "Niagara Region, Ontario, Canada".
2. Choose the command settings.set with {'field': 'units', 'value': 'imperial'}. Nothing is spoken.
3. Choose the command settings.set with {'field': 'bearing', 'value': 'clock'}. Nothing is spoken.
4. Open the Information panel. The Nearby group has: "United States, 0.3 miles 3 o'clock".

## Part 5: Blocked at the North Pole

Requirements: NAV-1.

Start at latitude 89.9, longitude 0, with the zoom and step as given in the script file (the world pack).

1. Press Up. Nothing is spoken. You hear the blocked sound.
2. Press Up. Nothing is spoken. You hear the blocked sound.

## Part 6: Repeat, history and mute

Requirements: ANN-4, SON-7.

Start at latitude 51.2, longitude 1.2, with the zoom and step as given in the script file (the test pack).

1. Press Down. You hear: "North Atlantic Ocean".
2. Press Space. You hear: "North Atlantic Ocean".
3. Press Ctrl+Space. You hear: "North Atlantic Ocean".
4. Press Ctrl+M. You hear: "Sound muted.".
5. Press Down. No sound plays.
6. Press Ctrl+M. You hear: "Sound on.".
7. Press Down. You hear the tick sound.

## Part 7: Blocked at the South Pole

Requirements: NAV-1.

Start at latitude -89.9, longitude 0, with the zoom and step as given in the script file (the test pack).

1. Press Down. Nothing is spoken. You hear the blocked sound.
2. Press Down. Nothing is spoken. You hear the blocked sound.
3. Press Space. You hear: "Antarctica".

## Part 8: Where am I, the coordinates in both formats, and the heading

Requirements: LOC-1, LOC-2, LOC-7, ANN-5.

Start at latitude 51.2, longitude 1.2, with the zoom and step as given in the script file (the test pack).

1. Press Space. You hear: "Kent, England, United Kingdom".
2. Press C. You hear: "51.20000 degrees north, 1.20000 degrees east".
3. Choose the command settings.set with {'field': 'coordinates', 'value': 'dms'}. Nothing is spoken.
4. Press C. You hear: "51 degrees 12 minutes 0.0 seconds north, 1 degrees 12 minutes 0.0 seconds east".
5. Press H. You hear: "Facing north. North-fixed. Stepping. Zoom 5 kilometres, step 250 metres.".
6. Choose the command settings.set with {'field': 'units', 'value': 'imperial'}. Nothing is spoken.
7. Press H. You hear: "Facing north. North-fixed. Stepping. Zoom 2.5 miles, step 250 yards.".

## Part 9: Zoom and step changes, linked and not

Requirements: NAV-2, NAV-13, LOC-7.

Start at latitude 51.2, longitude 1.2, with the zoom and step as given in the script file (the test pack).

1. Press Page Down. You hear: "Zoom 2.5 kilometres, step 100 metres.".
2. Press Page Up. You hear: "Zoom 5 kilometres, step 100 metres.".
3. Press Shift+Page Up. You hear: "Zoom 5 kilometres, step 250 metres.".
4. Press Shift+Page Down. You hear: "Zoom 5 kilometres, step 100 metres.".
5. Choose the command step.link. You hear: "Step linked to zoom. Zoom 5 kilometres, step 1 kilometre.".
6. Press Page Down. You hear: "Zoom 2.5 kilometres, step 500 metres.".
7. Press Shift+Page Up. You hear: "Zoom 5 kilometres, step 1 kilometre.".
8. Choose the command step.link. You hear: "Step no longer linked to zoom. Zoom 5 kilometres, step 1 kilometre.".
9. Press Page Down. You hear: "Zoom 2.5 kilometres, step 1 kilometre.".

## Part 10: Installing and opening

Requirements: DEL-5, PLT-1, PLT-3.

1. Install the desktop version with the installer, and start it. It says where you start, then 'Press F1 for keys'.
2. Open the web version in Firefox. It says the same.

## Part 11: Keys and regions

Requirements: ACC-3, ACC-7, NAV-1.

1. Press F1 on the map. It lists the commands for the map with their keys.
2. Press Shift+F1, then Up, Page Up and a key with no command. Each is described and nothing is carried out. Press Shift+F1 again.
3. Press F2, F3 and F4 from each region. They go to the map, the Information panel and Details.
4. Change the key of Heading to one that is free. Then try one that is taken. You are told which command has it.
5. On the desktop, press Alt to reach the menu bar, Tab along its menus, and Alt or Escape to leave. On the web, Ctrl+Alt+M reaches the menu bar.

## Part 12: Held keys

Requirements: ANN-3.

1. Hold the Right arrow for two seconds and let go. Only the last place is spoken, and it interrupts anything still being said.

## Part 13: The Information panel

Requirements: INF-10.

1. Press F3. NVDA says the item and its level, and reads the item without pressing Up then Down.

## Part 14: Settings and sound

Requirements: PLT-5, SON-7, SON-8.

1. Open Settings with Ctrl+comma. It has OK and Cancel buttons. Change the units, close TobyMap, open it again. Your settings and place are back.
2. Press Ctrl+M to mute, move, and press it again. The tick and blocked sounds stop and come back.
3. Open Help, then The sounds. The earcons and their file names are listed.

## Part 15: Braille

Requirements: ACC-1.

1. Read the announcements on your Braille display or in NVDA's Braille viewer.

## Part 16: Listening test

Requirements: SON-1, SON-9.

1. Run the full listening test (tools/listening_test) and send me the results file.
