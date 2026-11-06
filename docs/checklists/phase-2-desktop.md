# Phase 2 checklist: desktop version

This is the first pass of the Phase 2 desktop checklist, for you to work through with NVDA on Windows 11. The web version has its own checklist, docs/checklists/phase-2-web.md. The parts that need sight, the themes, names on the map and magnifiers, are in docs/checklists/phase-2-sighted.md, for a sighted helper if you have one.

For each step, write down its number, such as 4.3, and either "works" or what you heard instead. Put your notes in a text file, as you did for Phase 1.

The expected words below are what the program says on the world pack. Like Phase 1's, it has countries and their first-level divisions, but no counties, so you hear "England, United Kingdom", not "Kent".

Set Distances to Metric and Directions to Compass with 8 points before you start (Settings, Units). The words below assume both.

## Before you start: the world pack

The world pack needs its writing stage run once more before this checklist, so that it has the layer settings made since it was built: your own sounds for the prime meridian and the equator, and the zoom ranges of the layers. It takes about 26 minutes and reuses everything else. I run it when you say; until then, section 11 plays the ordinary line crossing sound for every line.

## How to start TobyMap at a place

As in Phase 1: close TobyMap if it is running, press Windows+R, and type the line given, such as:

`%LOCALAPPDATA%\Programs\TobyMap\TobyMap.exe --at 51.2,1.2`

TobyMap keeps your last zoom and step size. Several sections need a step of 25 kilometres: press Shift+Page Up or Shift+Page Down until you hear "step 25 kilometres". Others give a zoom or step of their own.

## 1. Install (DEL-5, PLT-1)

* 1.1 Run dist_installer\TobyMap-0.1.0-setup.exe. It installs over 0.0.9 without asking for administrator rights.
* 1.2 Start TobyMap from the Start menu. It says "TobyMap", the place, then "Press F1 for keys".
* 1.3 Help, then About TobyMap. It gives the version, 0.1.0, and names the Alba voice and its licence.

## 2. Orientations and turning (NAV-3, NAV-11, NAV-12)

Start with `--at 51.2,1.2`, zoom and step 25 kilometres. You hear "England, United Kingdom".

* 2.1 Press O. You hear "Cardinal facing, north."
* 2.2 Press Right. You hear "Facing east." Press Right again: "Facing south." Press Shift+Right: "Facing west."
* 2.3 Press Ctrl+Right. The blocked sound plays and nothing is said, because the fine turn is only for free facing.
* 2.4 Press Up. It steps forward, to the west, and ticks.
* 2.5 Press O. You hear "Free facing, 270 degrees."
* 2.6 Press Right: "Facing 275 degrees." Ctrl+Right: "Facing 276 degrees." Ctrl+Left: "Facing 275 degrees." Left: "Facing 270 degrees."
* 2.7 Hold Right for two seconds. It clicks as it turns, and when you let go it says the heading once.
* 2.8 Press O. You hear "North-fixed." Up steps north again, and Left and Right step west and east.
* 2.9 In Settings, Movement, "Free facing: degrees turned by Left and Right" is 5 and "by Ctrl with Left and Right" is 1. Your answer to DP147 asks how this feels; tell me whether a continuous turn while the key is held would be better.

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

* 4.1 Press O for cardinal facing, then Up. You hear "Crossed the North Pole. Now facing south." Up again ticks: you carry on, away from the pole.
* 4.2 Press H. It says you face south, in cardinal facing.
* 4.3 Close TobyMap and start it again with `--at 89.9,0`. Press O twice for free facing, which says "Free facing, 0 degrees.", then Up. You hear "Crossed the North Pole. Now facing 180 degrees."
* 4.4 Start with `--at -89.9,0`. You hear "Antarctica". Press O once for cardinal facing, then Down, which steps back, to the south. You hear "Crossed the South Pole. Now facing south."
* 4.5 Press O until you hear "North-fixed."

## 5. Going to coordinates and back (NAV-8, NAV-10)

Start with `--at 51.2,1.2`. You hear "England, United Kingdom".

* 5.1 Press Ctrl+G. A box opens for coordinates, with examples.
* 5.2 Type 48.8566, 2.3522 and press Enter. You hear "Ile-de-France, France".
* 5.3 Press Ctrl+G, type 91, 0 and press Enter. The box stays open and says latitude is up to 90 degrees. Press Cancel.
* 5.4 Try other forms if you like, such as 48.85N 2.35E, or 48°51′N 2°21′E. Each goes to Paris.
* 5.5 Press Alt+Comma. You hear "England, United Kingdom": back to where you were before the jump, with the same zoom and step.
* 5.6 Press Alt+Full stop. You hear "Ile-de-France, France". Press it again: the blocked sound, as there is nowhere further forward.
* 5.7 Click on the map, if you can, or skip this step. A click is a jump, so Alt+Comma comes back from it.

## 6. Enter in the announcement history (ANN-4, DP141)

Start with `--at 51.2,1.2`.

* 6.1 Press Down. You hear "North Atlantic Ocean".
* 6.2 Press Ctrl+G and go to 48.85, 2.35. You hear "Ile-de-France, France".
* 6.3 Press Ctrl+Shift+Space. The announcement history opens, newest first, with a line saying what Enter does.
* 6.4 Move to "North Atlantic Ocean" and press Enter. The history closes and you hear "North Atlantic Ocean": you are back where it was said.
* 6.5 Press Alt+Comma. You are back in Paris.
* 6.6 Open the history again, move to an entry with no place, such as a message from Help, and press Enter. You hear "No place for this entry." and the list stays open. Close it with its Close button.

## 7. Layers (SCP-6, SCP-7)

Start with `--at 51.2,1.2`.

* 7.1 Press Ctrl+Shift+L. The layers list opens: the groups Boundaries, Water and Graticule, each with its layers and a check box for each.
* 7.2 Move to Regions and press Space to switch it off. Press OK.
* 7.3 Press Space on the map. You hear "United Kingdom": England is gone, because it is a region.
* 7.4 Switch Countries off too. Space now says "Every layer here is switched off".
* 7.5 Switch both back on. Open the layers list on a layer and press "Settings for this layer": its closest zoom, farthest zoom and crossing sound. Cancel goes back to the list.

## 8. Crossed and passed (ANN-2, DP148)

Start with `--at 49.7,5.3`. Set the zoom to 1,000 kilometres and the step to 100 kilometres. You hear "Wallonia, Belgium".

* 8.1 Press Right. You hear "Rhineland-Palatinate, Germany", and then a soft earcon: something was added to Crossed and passed. Nothing about it is spoken.
* 8.2 Press Shift+5. Focus goes to Crossed and passed in the Information panel. It lists "Luxembourg, passed over, 15 kilometres west" and "Moselle condominium, passed over, 15 kilometres west".
* 8.3 Press F2 to go back to the map. Hold Right for a few steps and let go. Shift+5 lists everything the whole held run went over, not only the last step.
* 8.4 Press Ctrl+G and jump somewhere. Crossed and passed is empty: a jump has no path.
* 8.5 In Settings, Earcons, switch "Something added: play it" off. Take a large step: the earcon is silent. Switch it back on.

## 9. Hear its direction (SON-3, DP143)

Start with `--at 51.2,1.2`, zoom 100 kilometres. Use headphones if you can.

* 9.1 Press F3, and go down to Nearby. The first items are "North Atlantic Ocean, 11 kilometres south" and "France, 45 kilometres south-east".
* 9.2 On North Atlantic Ocean, press Space. The item's direction sound plays from behind you, lower in pitch, then the Alba voice says "North Atlantic Ocean, 11 kilometres" from the same place.
* 9.3 On France, press Space. It comes from behind and to the right.
* 9.4 Press O for cardinal facing, then Shift+Right twice to face south. Go back to the panel and press Space on North Atlantic Ocean. It is now ahead of you, at normal pitch. Press O until north-fixed.
* 9.5 On a group heading, such as Within, Space says "Hear its direction works on an item of Nearby or Crossed and passed."
* 9.6 Each label is in the announcement history, and in NVDA's Braille viewer without being spoken. In Settings, Sound, switch on "Also speak spatial labels through the screen reader": NVDA now speaks each label as well.
* 9.7 In Settings, Sound, change the spatial voice's volume and speed, and try again.

## 10. The orientation beacon (SON-10, SON-2)

Start with `--at 51.2,1.2`. Headphones help.

* 10.1 Press B. You hear "Beacon on." A soft tone repeats about once a second, straight ahead: the North Pole is north.
* 10.2 Press O for cardinal facing, then Right to face east. The beacon moves to your left. Right again, facing south: it is behind you, lower in pitch.
* 10.3 Press O until north-fixed. In Settings, Sound, change "Orientation beacon: seconds between each sound" to 2, and its volume to 50. It slows and is quieter.
* 10.4 Press B. You hear "Beacon off." and it stops.
* 10.5 Start with `--at 89.5,0` and press B. You hear "Beacon on, but silent near the North Pole." Step south with a 25 kilometre step until you hear "Beacon back on."

## 11. The graticule and its crossing sounds (DAT-13, SCP-7)

Start with `--at 0.5,-0.5`, zoom 1,000 kilometres, step 100 kilometres. You hear "North Atlantic Ocean".

* 11.1 Press Ctrl+Shift+L and switch on the layers of lines of latitude and longitude and of special lines. Press OK.
* 11.2 Press Right. You cross the prime meridian: after the world pack is written again, your meridianCrossed sound plays.
* 11.3 Press Down. You hear "South Atlantic Ocean" and cross the equator: your equatorCrossed sound plays.
* 11.4 In Settings, Layers, the interval of the lines is 10 degrees. Change it to 1 degree, and step again: a line crossing sound plays at every degree.
* 11.5 Switch the two layers off again in the layers list.

## 12. Holding an arrow key (ANN-3, DP140)

Start with `--at 51.2,1.2`, step 25 kilometres.

* 12.1 Hold Right for three seconds. After half a second, the clicks come evenly, about 6 a second, however long the map takes to draw. When you let go, only the last place is spoken.
* 12.2 Do the same with Beacon on and with the graticule on. The clicks are still even.

## 13. How much is said: the verbosity presets (ACC-5, DP144)

Start with `--at 51.2,1.2`, zoom and step 25 kilometres.

* 13.1 Press A. You hear "Detailed. The whole place is said when an area changes, and the heading after each step in free facing." Press A again: "Terse. Only the smallest area that changed is said." Again: "Normal. Every area that changed is said, and the zoom, the step and the heading."
* 13.2 Normal first. Start with `--at 49.9,2.3`, step 100 kilometres. You hear "Hauts-de-France, France". Press Left. You hear "Normandy": only what changed.
* 13.3 Press A once, for detailed. Start again at 49.9,2.3 and press Left. You hear "Normandy, France": the whole place. Press O twice for free facing and press Up: the heading is said after the place, or alone if no area changed. Press O for north-fixed.
* 13.4 Press A for terse. Start with `--at 51.2,1.2`, step 25 kilometres, and do Down, Right, Right. At the third you hear only "Hauts-de-France", where normal says "Hauts-de-France, France". Page Up only ticks: the zoom is not said, but H still says it.
* 13.5 Press A for normal. Open Settings, Speech. The preset is first, then its four switches. Change one: when you press OK, the preset is Custom. Choose Normal again.
* 13.6 Your answer to DP144 asked to review how friendly this is. Tell me what you think, including whether A is a good key, and whether it should work in the Information panel too.

## 14. Earcons (SON-6, SON-7, SON-8, DP123)

* 14.1 Open Settings, Earcons. At the top is the earcon volume. Then, for each earcon, "play it" and "your own sound file".
* 14.2 Set the earcon volume to 30 and step about: the tick is quieter. Put it back to 100.
* 14.3 Switch "Tick: play it" off. A step that changes nothing is silent. Switch it back on.
* 14.4 On "Tick: your own sound file", press Choose file, and choose a WAV file of your own. Press OK and step: your sound plays. Press Use the default to go back.
* 14.5 Choose a file that is not a WAV sound, such as a text file renamed to .wav. You are told it could not be read, and the sound is not changed.
* 14.6 Press Ctrl+M. Everything is silent: earcons, the beacon and the voice. Press Ctrl+M again.

## 15. The sound design as a whole

Now that the sound in space is built on your choices in DP100 and DP137, tell me how it feels: the lower pitch behind, the loudness with distance, the minimum volume, stereo against HRTF (Settings, Sound), and anything else. These notes go against SON-1, SON-2 and SON-9.

## Finishing

When you have been through it, send me your notes. If you accept the desktop version, and the web version passes its own checklist, I ask you about publishing (DP110). That completes Phase 2.
