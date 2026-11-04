# TobyMap release notes

## Version 0.1.0, Phase 1: the walking skeleton (not yet released)

This is the first version you step around the world with. The version number is 0.1.0 only when you accept the phase; until then the build says 0.0.7.

### What changed

* You start at a place and step north, south, east and west with the arrow keys. Each step is announced by the smallest area you are in and the larger areas that changed, or ticks if nothing changed (ANN-1).
* Stepping crosses the 180 degree line and is blocked at the poles with a sound and no speech (NAV-1).
* Page Up and Page Down change the zoom, and Shift with them changes the step. "Link step to zoom" is in the Map menu.
* Space says where you are, C the coordinates, H the heading, V the size of the visible map.
* Ctrl+Space repeats the last announcement, and Ctrl+Shift+Space lists the history, at least the last 50.
* F1 lists the commands for the region you are in. Shift+F1 is the key describer. F2, F3 and F4 go to the map, the Information panel and Details from anywhere. F3 returns to the item you last had.
* The Information panel has Within (the areas you are in, smallest first) and Nearby (the nearest points of the areas around you, with distance and direction).
* Ctrl+comma opens Settings: units, direction format, coordinate format, movement, sound and display, and your own keys. A key already in use is refused, naming the command that has it.
* Ctrl+M mutes the application's own sounds.
* Holding an arrow key moves you without speech; when you let go only the final place is spoken (ANN-3).
* Copying the coordinates was left out, as you asked (DP113).
* Help, Copy diagnostics puts the last five minutes of what the application did, with times, on the clipboard.

### What was tested, and with what

Automatic tests: Python on Windows (and macOS in continuous integration), browser tests in Chromium and Firefox, an installer self-test in continuous integration.

Not tested by me, because it needs your ears and screen reader: NVDA on the desktop and in Firefox and Chrome, the Braille display, and how the tick and blocked sounds feel. Those are the checklist in docs/checklists/phase-1.md.

### Differences between the desktop and the web version (PLT-3)

* The desktop opens the map pack from your TobyMap folder in the application data folder. The web version downloads it once into the browser's private storage, announcing progress at most every 10 seconds.
* Braille-only messages need NVDA on the desktop. In a browser the screen reader shows speech in Braille as well.
* Your own sound files for the tick and blocked sounds work on the desktop. The web version plays the default sounds.
* The menu bar is reached with Alt on the desktop and with Ctrl+Alt+M in a browser.
* Settings are kept in a file on the desktop and in the browser's own storage on the web, and can be exported and imported in both.

### Known problems

See docs/plan/phase-1-report.md.
