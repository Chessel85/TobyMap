# TobyMap release notes

## Version 0.1.0, Phase 2: orientation, layers and sound (for your acceptance)

This version adds turning and facing, going to places and back, layers, the sound in space with the Alba voice, the beacon, the verbosity presets, and themes and names on the map for sighted users. The detail of each task is in docs/plan/phase-2.md.

### What changed

* Three orientations, with O: north-fixed, cardinal facing and free facing. In the facing orientations, Left and Right turn, Shift with them 90 degrees, and Ctrl with them a fine turn in free facing. Ctrl+B types a bearing. Steps carry on over both poles, and say so (NAV-3, NAV-11, NAV-12).
* In the facing orientations, Nearby says directions relative to the way you face, such as "ahead right" (NAV-12).
* Ctrl+G goes to typed coordinates, in many forms. Alt+Comma and Alt+Full stop go back and forward through the places you jumped from, with their zoom and step (NAV-8, NAV-10).
* Enter on an entry of the announcement history goes back to where it was said (DP141).
* The layers list, Ctrl+Shift+L, switches layers on and off; a layer that is off is gone from what you hear and see. Each layer has a zoom range and a smallest size (SCP-6, SCP-7, NAV-13).
* Crossed and passed, in the Information panel, lists what the last move went over, with a soft earcon; Shift+5 goes to it (ANN-2).
* Holding an arrow key gives even clicks, whatever the map is doing (DP140).
* Sound in space: Space on an item of Nearby or Crossed and passed plays its sound from its direction, then its name in the Alba voice from the same place. Sounds behind you are lower in pitch. Stereo, or HRTF for headphones (SON-1, SON-2, SON-3, DP143).
* B switches on the orientation beacon, a soft tone from the North Pole (SON-10).
* The lines of latitude and longitude and the special lines are layers, off at first, with crossing sounds, including yours for the prime meridian and the equator (DAT-13).
* Every earcon has its own switch and your own file, and there is an earcon volume. In the web version your own files are kept in the browser (SON-6, SON-7, SON-8, DP123).
* How much is said: terse, normal and detailed, with A on the map, and four switches in the new Speech tab of Settings (ACC-5, DP144).
* For sighted and partially sighted users: four themes, with T and Shift+T; the map display setting; Isolate, Ctrl+I; names on the map with a label size; heading-up; and magnifiers follow the map centre (VIS-2, VIS-3, VIS-5, ACC-8).

### Differences between the desktop and the web version (PLT-3)

* Spatial labels: on the desktop, each label goes to your Braille display without being spoken. A browser cannot do that, so in the web version a label reaches the screen reader, and Braille, only when "Also speak spatial labels through the screen reader" is on, in Settings, Sound. If you use Braille in the web version, switch it on (DP151).
* The spatial voice takes about 60 milliseconds to start a label on the desktop, and in the web version about a fifth of a second for a short name and half a second for a name with its distance (DP150).
* The first visit to the web version reloads the page once, to let the voice use four threads.
* Magnifiers: on the desktop, the map holds an invisible text cursor at its centre. In the web version, the map's focus point is at its centre; how far a magnifier follows it depends on the browser.

### Known problems

* The world pack needs its writing stage run again, about 26 minutes, to hold the layer settings made since it was built: your crossing sounds for the prime meridian and the equator, and the layers' zoom ranges.
* Whether magnifiers follow the map centre has been tested only by the automatic tests, not with Windows Magnifier itself.

## Version 0.0.9, Phase 1: the walking skeleton (accepted, not released)

This is the first version you step around the world with. You accepted Phase 1 on 5 November 2026 and chose not to publish it. The first release is asked about again at the end of Phase 2 (DP110), and it will carry these notes with Phase 2's.

### What changed

* You start at a place and step north, south, east and west with the arrow keys. Each step is announced by the smallest area you are in and the larger areas that changed, or ticks if nothing changed (ANN-1).
* Stepping crosses the 180 degree line and is blocked at the poles with a sound and no speech (NAV-1).
* Page Up and Page Down change the zoom, and Shift with them changes the step; only the one that changed is said. "Link step to zoom" is in the Map menu.
* Space says where you are, C the coordinates, H the heading, V the size of the visible map. The coordinates have only the decimal places the step needs, or always all of them, as you choose in Settings.
* Ctrl+Space repeats the last announcement, and Ctrl+Shift+Space lists the history, at least the last 50.
* F1 lists the commands for the region you are in. Shift+F1 is the key describer. F2, F3 and F4 go to the map, the Information panel and Details from anywhere. F3 returns to the item you last had.
* The Information panel has Within (the areas you are in, smallest first) and Nearby (the nearest points of the areas around you, with distance and direction).
* Ctrl+comma opens Settings: units, direction format, coordinate format, movement, sound and display, and your own keys. A key already in use is refused, naming the command that has it. Keys that are a symbol are said as a word, such as Ctrl+Comma. In the web version, Settings has a tab for each group, as on the desktop.
* Ctrl+M mutes the application's own sounds.
* Holding an arrow key moves you without speech; when you let go only the final place is spoken (ANN-3).
* Copying the coordinates was left out, as you asked (DP113).
* Help, Copy diagnostics puts the last five minutes of what the application did, with times, on the clipboard.

### What was tested, and with what

Automatic tests: Python on Windows (and macOS in continuous integration), browser tests in Chromium and Firefox, an installer self-test in continuous integration.

Not tested by me, because it needs your ears and screen reader: NVDA on the desktop and in Firefox and Chrome, the Braille display, and how the tick and blocked sounds feel. Those are the checklists in docs/checklists/phase-1-desktop.md and phase-1-web.md, which you passed on 5 November 2026 with version 0.0.9.

### Differences between the desktop and the web version (PLT-3)

* The desktop opens the map pack from your TobyMap folder in the application data folder. The web version downloads it once into the browser's private storage, announcing progress at most every 10 seconds.
* Braille-only messages need NVDA on the desktop. In a browser the screen reader shows speech in Braille as well.
* Your own sound files for the tick and blocked sounds work on the desktop. The web version plays the default sounds.
* The menu bar is reached with Alt on the desktop and with Ctrl+Alt+M in a browser.
* Settings are kept in a file on the desktop and in the browser's own storage on the web, and can be exported and imported in both.

### Known problems

See docs/plan/phase-1-report.md.
