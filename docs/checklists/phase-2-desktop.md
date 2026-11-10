# Phase 2 checklist: desktop version, second pass

This is the full Phase 2 desktop checklist, for you to work through with NVDA on Windows 11. Every step says what to do and what you should now hear. The web version has its own checklist, docs/checklists/phase-2-web.md. The parts that need sight, the themes, names on the map and magnifiers, are in docs/checklists/phase-2-sighted.md, for a sighted helper if you have one.

For each step, write down its number, such as 4.3, and either "works" or what you heard instead. Put your notes in a text file, as before.

The expected words below are what the program says on the world pack. It has countries and their first-level divisions, but no counties, so you hear "England, United Kingdom", not "Kent".

## Before you start

* Set Distances to Metric and Directions to Compass with 8 points, in Settings, Units. The words below assume both.
* Make sure the verbosity preset is Normal. Section 14 says how to check it.
* Make sure the orientation is north-fixed. Pressing H says it.

## How to start TobyMap at a place

Close TobyMap if it is running, press Windows+R, and type the line given, such as:

`%LOCALAPPDATA%\Programs\TobyMap\TobyMap.exe --at 51.2,1.2`

TobyMap keeps your last zoom and step size. Page Up and Page Down change the zoom, and Shift+Page Up and Shift+Page Down change the step. Several sections need a zoom and step of 25 kilometres; others give their own.

## 1. Install (DEL-5, PLT-1)

* 1.1 Run dist_installer\TobyMap-0.1.0-setup.exe, dated 8 November. It installs over the earlier 0.1.0 without asking for administrator rights.
* 1.2 Start TobyMap from the Start menu. It says "TobyMap", the place, then "Press F1 for keys".
* 1.3 Open Help, then About TobyMap. The text box has one sentence on each line. Up and Down arrow read it a line at a time: the version, 0.1.0; what TobyMap is; its licence; the Alba voice and its licence; and where the other licences are.
* 1.4 Close the About box with its Close button.

## 2. Orientations and turning (NAV-3, NAV-11, NAV-12)

Start with `--at 51.2,1.2`, zoom and step 25 kilometres. You hear "England, United Kingdom".

* 2.1 Press Shift+Right, then Ctrl+Right. In north-fixed, both do nothing: no words and no sound.
* 2.2 Press O. You hear "Cardinal facing, north."
* 2.3 Press Right. You hear "Facing east." Press Right again: "Facing south." Press Left twice: "Facing east.", then "Facing north."
* 2.4 Press Shift+Right, then Ctrl+Right. In cardinal facing, both do nothing: no words and no sound.
* 2.5 Press Left to face west, then Up. It steps forward, to the west, and ticks or says the place.
* 2.6 Press O. You hear "Free facing, 270 degrees."
* 2.7 Press Right: "Facing 275 degrees." Ctrl+Right: "Facing 276 degrees." Ctrl+Left: "Facing 275 degrees." Left: "Facing 270 degrees."
* 2.8 Press Shift+Right: "Facing 0 degrees." Press Shift+Left: "Facing 270 degrees."
* 2.9 Hold Right for two seconds. It clicks as it turns, and when you let go it says the heading once.
* 2.10 Open Settings, Movement. There are three turning settings: "Free facing: degrees turned by Left and Right", 5; "Free facing: degrees turned by Shift with Left and Right", 90; and "Free facing: degrees turned by Ctrl with Left and Right", 1. Change the Shift one to 45 and press OK. Shift+Right now turns 45 degrees. Put it back to 90.
* 2.11 Press O. You hear "North-fixed." Up steps north again, and Left and Right step west and east.

## 3. Typing a bearing (NAV-12)

Still at the same place, in north-fixed.

* 3.1 Press Ctrl+B. A box opens to type a bearing, with a line saying what you can type.
* 3.2 Type 47 and press Enter. You hear "Free facing, 47 degrees."
* 3.3 Press H. You hear "Facing 47 degrees. Free facing. Stepping. Zoom 25 kilometres, step 25 kilometres."
* 3.4 Press Ctrl+B, type north-east, and press Enter. You hear "Facing 45 degrees."
* 3.5 Press Ctrl+B, type hello, and press Enter. The box stays open and says what it accepts. Press Cancel.
* 3.6 Press O until you hear "North-fixed."

## 4. Over the poles (NAV-1, NAV-3)

Start with `--at 89.9,0`, step 25 kilometres. You hear "Arctic Ocean".

* 4.1 Press O for cardinal facing, then Up. You hear "Crossed the North Pole. Now facing south." Up again: you carry on, away from the pole.
* 4.2 Press H. It says you face south, in cardinal facing.
* 4.3 Close TobyMap and start it again with `--at 89.9,0`. Press O twice for free facing, which says "Free facing, 0 degrees.", then Up. You hear "Crossed the North Pole. Now facing 180 degrees."
* 4.4 Start with `--at -89.9,0`. You hear "Antarctica". Press O until you hear "Cardinal facing, north.", then Down, which steps back, to the south. You hear "Crossed the South Pole. Now facing south."
* 4.5 Press O until you hear "North-fixed."

## 5. Going to coordinates (NAV-8)

Start with `--at 51.2,1.2`. You hear "England, United Kingdom".

* 5.1 Press Ctrl+G. A box opens, titled "Go to coordinates", with the field "Enter latitude and longitude:" and no other text.
* 5.2 Type 48.85, 2.35 and press Enter. You hear "Ile-de-France, France", and only that: not the place you left.
* 5.3 Press Ctrl+G, type 91, 0 and press Enter. The box stays open and says those are not coordinates, with examples, and that latitude is up to 90 degrees and longitude up to 180. Press Cancel.
* 5.4 Press Ctrl+G and type 48.85N 2.35E. You stay in Paris: "Ile-de-France, France".
* 5.5 Degrees, minutes and seconds use the letters D, M and S, in either case. Press Ctrl+G and type 48d 51m N, 2d 21m E. You hear "Ile-de-France, France".
* 5.6 One number sets the latitude and keeps your longitude. Start again with `--at 51.2,1.2`. Press Ctrl+G and type 48.85. You hear "Normandy, France".
* 5.7 A comma then a number sets the longitude and keeps your latitude. Press Ctrl+G and type , 2.35 (a comma, a space, then 2.35). You hear "Ile-de-France, France".
* 5.8 A direction then degrees moves you by that much. Press Ctrl+G and type south 2 east 3. You hear "Bourgogne – Franche-Comté, France".
* 5.9 Press Ctrl+G and type n 2. You are 2 degrees further north: "Grand Est, France". Letters work as well as words.
* 5.10 Press Ctrl+G and type north 90. You stop at the North Pole and hear "Arctic Ocean". Press Alt+Comma to come back.
* 5.11 Forward and back (P2-T17r). Press Ctrl+G and type f 50. A message box says "Forward and back work in cardinal and free facing." Press OK, then Cancel. Press O for cardinal facing, facing north. Press Ctrl+G and type f 100: you move 100 kilometres north and hear the new place. Press Ctrl+G and type b100km: you are back where you were, still facing north. Try F2mi500yds too: 2 miles and 500 yards forward. Press Shift+O for north-fixed.

## 6. Going back and forward through your places (NAV-10)

Start with `--at 51.2,1.2`, step 25 kilometres. You hear "England, United Kingdom".

* 6.1 Press Ctrl+G and go to 48.85, 2.35. You hear "Ile-de-France, France".
* 6.2 Press Right once. It ticks or says a place.
* 6.3 Press Alt+Comma. You are back where you were before that step, in Paris, with the same zoom and step. The place is said.
* 6.4 Press Alt+Comma again. You hear "England, United Kingdom": back to before the jump.
* 6.5 Press Alt+Full stop twice: first Paris, then the place after the step. Press it once more: the blocked sound, as there is nowhere further forward.
* 6.6 Hold Right for about three seconds and let go. Press Alt+Comma once. You are back where the hold started, in one press.
* 6.7 Press Alt+Full stop: you go forward to where the hold ended. Now press O twice for free facing, and Right to turn: a turn adds no place. Press Alt+Comma: you go back to where the hold started, as in 6.6. Press O to return to north-fixed.
* 6.8 Open Settings, Movement. "Clear the places on start" is off. Switch it on and press OK. Close TobyMap and start it again with `--at 51.2,1.2`. Press Alt+Comma: the blocked sound, as there are no places yet. Switch the setting off again.
* 6.9 With the setting off, close TobyMap after a few steps and jumps, and start it again. Alt+Comma goes back through the places from last time.
* 6.10 Click on the map, if you can, or skip this step. A click is a jump, so Alt+Comma comes back from it.

## 7. The location history (NAV-10, DP158)

Start with `--at 51.2,1.2`.

* 7.1 Press Down. You hear "North Atlantic Ocean".
* 7.2 Press Ctrl+G and go to 48.85, 2.35. You hear "Ile-de-France, France".
* 7.3 Press Ctrl+Shift+Space. The location history opens, with a line saying what Enter does. It holds only places, newest first, and you are on the first: "Here: Ile-de-France, France", then "North Atlantic Ocean", then "England, United Kingdom".
* 7.4 Move to "North Atlantic Ocean" and press Enter. The history closes and you hear "North Atlantic Ocean", and only that.
* 7.5 Press Alt+Full stop. You are back in Paris: Enter went back as Alt+Comma does, so the way forward is kept.
* 7.6 Press Ctrl+Shift+Space again: you are on "Here: Ile-de-France, France". Close it with its Close button.
* 7.7 Press Ctrl+Shift+L, switch off "Oceans and seas" in the Water group, and press OK. Open the location history: "North Atlantic Ocean" is not in it. Close it, and press Alt+Comma: you hear "England, United Kingdom", passing over the place at sea.
* 7.8 Switch "Oceans and seas" on again. Open the location history: "North Atlantic Ocean" is back in it. Close it with its Close button.

## 8. Layers (SCP-6, SCP-7)

Start with `--at 51.2,1.2`.

* 8.1 Press Ctrl+Shift+L. The layers list opens: the groups Boundaries, Water and Graticule, each with its layers and a check box for each. Graticule has "Lines of latitude and longitude" and "Special lines: equator, prime meridian, tropics, polar circles and date line", both off.
* 8.2 Move to Regions and press Space to switch it off. Press Enter: it presses OK, and the list closes.
* 8.3 Press Space on the map. You hear "United Kingdom": England is gone, because it is a region.
* 8.4 Open the list again and switch Countries off too. Press OK. Space now says "Every layer here is switched off".
* 8.5 Switch both back on. In the list, Space ticks a box and Enter presses OK, wherever you are in the list.
* 8.6 Open the list, move to a layer and press "Settings for this layer": its closest zoom, farthest zoom and crossing sound. Enter there presses that OK and goes back to the list. Cancel goes back to the list too.

## 9. The Information panel's groups (INF-10)

Start with `--at 51.2,1.2`, zoom 100 kilometres.

* 9.1 On the map, press Shift+1. Focus goes to Within in the Information panel.
* 9.2 Press Shift+2. Focus goes to Nearby.
* 9.3 Press Shift+3. Focus goes to Crossed and passed.
* 9.4 The same three keys work from inside the Information panel and from Details.
* 9.5 Press F1 on the map. The list of keys has "Go to Within: Shift+1", "Go to Nearby: Shift+2" and "Go to Crossed and passed: Shift+3".
* 9.6 Press F2 to go back to the map.

## 10. Crossed and passed (ANN-2, DP148)

Start with `--at 49.7,5.3`. Set the zoom to 1,000 kilometres and the step to 100 kilometres. You hear "Wallonia, Belgium".

* 10.1 Press Right. You hear "Rhineland-Palatinate, Germany", and then a soft earcon: something was added to Crossed and passed. Nothing about it is spoken.
* 10.2 Press Shift+3. Focus goes to Crossed and passed. It lists "Luxembourg, passed over, 15 kilometres west" and "Moselle condominium, passed over, 15 kilometres west".
* 10.3 Press Shift+2 for Nearby. On the first item, press Space. The distance the voice says is the same as the distance in the item's words.
* 10.4 Press F2 to go back to the map. Hold Right for a few steps and let go. Shift+3 lists everything the whole held run went over, not only the last step.
* 10.5 Press Ctrl+G and jump somewhere. Crossed and passed is empty: a jump has no path.
* 10.6 In Settings, Earcons, go down the list to "Something added" and press Space, so it is not checked. Press Enter for OK. Take a large step: the earcon is silent. Check it again.

## 11. Hear its direction (SON-3, DP143)

Start with `--at 51.2,1.2`, zoom 100 kilometres. Use headphones if you can.

* 11.1 Press Shift+2 for Nearby. The first items are "North Atlantic Ocean, 11 kilometres south" and "France, 45 kilometres south-east".
* 11.2 On North Atlantic Ocean, press Space. The item's direction sound plays from behind you, lower in pitch, then the Alba voice says "North Atlantic Ocean, 11 kilometres" from the same place. The voice behind you is a little lower, but at its ordinary speed.
* 11.3 On France, press Space. It comes from behind and to the right.
* 11.4 Press F2, then O for cardinal facing, then Right twice to face south. Press Shift+2 and Space on North Atlantic Ocean. It is now ahead of you, at normal pitch, but its words still give a compass direction, such as south: directions in words are from north at first (P2-T17s, DP159). In Settings, Units, tick "In cardinal and free facing, give directions from the way you face" and press OK. Space on North Atlantic Ocean again: its words now give the direction from the way you face, such as "at your north", that is, ahead. Untick the setting again. Press F2, and O until north-fixed.
* 11.5 Press Shift+1 for Within. On England, press Space. Its sound plays from the centre of England, and the voice says "England" and the distance to that centre.
* 11.6 On a group heading, such as Within, Space says "Hear its direction works on an item, not on a group."
* 11.7 Each label is in NVDA's Braille viewer without being spoken, and Shift+Space repeats it.
* 11.8 In Settings, Sound, switch on "Also speak spatial labels through the screen reader". Press Space on an item: NVDA now speaks the label as well as the Alba voice. Switch it off again: NVDA is silent and only the Alba voice speaks.
* 11.9 In Settings, Sound, set "Spatial voice: speed, in percent" to 500. Press Space on an item: the label is about five times as fast as at 100, at the same pitch. Try 200 and 300 too, then set it as you like it.
* 11.10 Change "Spatial voice: volume, in percent" and try again: the voice is louder or quieter.

## 12. The orientation beacon (SON-10, SON-2)

Start with `--at 51.2,1.2`. Headphones help.

* 12.1 Press B. You hear "Beacon on." A soft, low whump repeats once a second, straight ahead: the North Pole is north.
* 12.2 Press O for cardinal facing, then Right to face east. The beacon moves to your left. Right again, facing south: it is behind you, lower in pitch.
* 12.3 The beat stays even, never missing or delaying a beat, while you press O to change orientation, turn, hold Right to turn for a few seconds, and step about. Each change is heard from the next beat.
* 12.4 Press O until north-fixed. In Settings, Sound, change "Orientation beacon: seconds between each sound" to 2, and "Orientation beacon: volume, in percent" to 50. It slows and is quieter. Put them back to 1 and 100.
* 12.5 Press B. You hear "Beacon off." and it stops.
* 12.6 Start with `--at 89.5,0` and press B. You hear "Beacon on, but silent near the North Pole." Step south with a 25 kilometre step until you hear "Beacon back on."
* 12.7 Press B to switch it off.

## 13. The graticule and its crossing sounds (DAT-13, SCP-7)

Start with `--at 0.5,-0.5`, zoom 1,000 kilometres, step 100 kilometres. You hear "North Atlantic Ocean".

* 13.1 Press Ctrl+Shift+L, go to the Graticule group, and switch on "Lines of latitude and longitude" and "Special lines". Press OK.
* 13.2 Press Right. You cross the prime meridian: your meridianCrossed sound plays.
* 13.3 Press Down. You hear "South Atlantic Ocean" and cross the equator: your equatorCrossed sound plays.
* 13.4 Open Settings, Layers. The interval of the lines is 10 degrees. Change it to 1 degree, press OK, and step again: the line crossing sound plays at every degree crossed.
* 13.5 Put the interval back to 10, and switch the two layers off again in the layers list.

## 14. Holding an arrow key (ANN-3, DP140)

Start with `--at 51.2,1.2`, step 25 kilometres.

* 14.1 Hold Right for three seconds. After half a second, the clicks come evenly, about 6 a second, however long the map takes to draw. Each click is clean, with no swish or hiss.
* 14.2 Let go. There is no extra click as you let go: the last click is the last step's. Only the last place is spoken.
* 14.3 Do the same with the beacon on, and with the graticule on. The clicks are still even, and the beacon keeps its beat.

## 15. How much is said: the verbosity presets (ACC-5, DP144)

Start with `--at 51.2,1.2`, zoom and step 25 kilometres.

* 15.1 Press A. You hear "Detailed. The whole place is said when an area changes, and the heading after each step in free facing." Press A again: "Terse. Only the smallest area that changed is said." Again: "Normal. Every area that changed is said, and the zoom, the step and the heading."
* 15.2 Normal first. Start with `--at 49.9,2.3`, step 100 kilometres. You hear "Hauts-de-France, France". Press Left. You hear "Normandy": only what changed.
* 15.3 Press A once, for detailed. Start again at 49.9,2.3 and press Left. You hear "Normandy, France": the whole place. Press O twice for free facing and press Up: the heading is said after the place, or alone if no area changed. Press O for north-fixed.
* 15.4 Press A for terse. Start with `--at 51.2,1.2`, step 25 kilometres, and do Down, Right, Right. At the third you hear only "Hauts-de-France", where normal says "Hauts-de-France, France". Page Up only ticks: the zoom is not said, but H still says it.
* 15.5 Press A for normal. Open Settings, Speech. The preset is first, then its four switches. Change one: when you press OK, the preset is Custom. Choose Normal again.
* 15.6 Press F3 to go to the Information panel, and press A. The verbosity does not change, and the step is not linked to the zoom: in the panel, a letter goes to the next item starting with it. If you hear anything about the zoom or the step, tell me exactly what.

## 16. Link step to zoom (NAV-13)

Start with `--at 51.2,1.2`.

* 16.1 On the map, press S. You hear "Step linked to zoom.", then the zoom and step.
* 16.2 Press Page Up. The zoom and the step both change, and both are said.
* 16.3 Press S again. You hear "Step no longer linked to zoom.", then the zoom and step. Page Up now changes only the zoom.
* 16.4 Press F3 and press S in the Information panel. It goes to the next item starting with S, if there is one, and does not link the step.
* 16.5 The Map menu has "Link step to zoom", with S.

## 17. Earcons (SON-6, SON-7, SON-8, DP123, DP163)

* 17.1 Open Settings, Earcons. Tab from the tabs goes to the list, "Earcons". Each earcon in it is a check box, all checked: Tick, Blocked, Something added and so on. The orientation beacon is not in it. There is no volume for all the earcons.
* 17.2 Tab on from the list: "Tick: volume, in percent", 100, then "Tick: your own sound file", empty, then Choose file and Use the default, each for the tick. Shift+Tab back to the list, Down to Blocked, and Tab again: each control now says Blocked.
* 17.3 On Tick in the list, set "Tick: volume, in percent" to 30. Press OK and step about: the tick is quieter, and the blocked sound is not. Put it back to 100.
* 17.4 On Tick in the list, press Space: it is not checked. Press Enter for OK. A step that changes nothing is silent. Check it again.
* 17.5 On "Tick: your own sound file", press Choose file, and choose a WAV file of your own. Press OK and step: your sound plays, the same in both ears.
* 17.6 Open Settings, Earcons again, and press Use the default for the tick, and press OK. Step once: only the default tick plays, with nothing of your own sound before it.
* 17.7 Choose a file that is not a WAV sound, such as a text file renamed to .wav. When the file dialog closes, NVDA reads a message under the field: the file "could not be read as a WAV sound file, so the sound is not changed." The message goes when you choose another earcon in the list.
* 17.8 In Settings, Sound, after "Orientation beacon: seconds between each sound", is "Orientation beacon: your own sound file", with its own Choose file and Use the default.
* 17.9 Press Ctrl+M. Everything is silent: earcons, the beacon and the voice. Press Ctrl+M again and sound comes back.

## 18. The sound design as a whole

Tell me how the sound in space feels now: the lower pitch behind, the voice behind you, the loudness with distance, the minimum volume, stereo against HRTF (Settings, Sound), the beacon's new sound, the clicks, and anything else. These notes go against SON-1, SON-2, SON-9 and SON-10.

## Finishing

When you have been through it, send me your notes. If you accept the desktop version, and the web version passes its own checklist, I ask you about publishing (DP110). That completes Phase 2.
