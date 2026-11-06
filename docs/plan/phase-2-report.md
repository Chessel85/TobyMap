# Phase 2 report: orientation, layers and sound

Written on 6 November 2026, when the last Phase 2 task was done, for your acceptance. It follows the order in section 1.5 of the implementation plan.

## Where the phase stands

* Every Phase 2 task is done, except the short Braille format (P2-T11b), which you parked in DP145 until you have a Braille user. The list is in docs/plan/phase-2.md.
* The checklists are ready: docs/checklists/phase-2-desktop.md, phase-2-web.md, and phase-2-sighted.md for a sighted helper.
* The version is 0.1.0. The world pack's writing stage was run again on 6 November 2026, so the pack holds your own crossing sounds and the layers' zoom ranges; all its checks passed. The 0.1.0 installer is built, and its self-test passed.
* Continuous integration runs on the push of these tasks. You see the phase only when it is green.
* Discussion points: DP149 is answered in docs/plan/phase-2.md; DP150 is parked for your testing; DP151 is in the release notes. None is open.

## What was built

* Moving: three orientations, turning, typing a bearing, and stepping over both poles (P2-T1). Going to coordinates, and back and forward through the places you jumped from (P2-T2). Enter in the announcement history goes back to where it was said (P2-T15). Held keys keep even clicks (P2-T14).
* Layers: the layers list, the visible rule with zoom ranges and the size rule, and a layer that is off is gone from what you hear and see (P2-T3, P2-T4). The lines of latitude and longitude and the special lines, built into the world pack, which was built again (P2-T10).
* Crossed and passed, found along each move's path in the background (P2-T5).
* Sound: the sound scene and the players on the desktop and the web (P2-T6), the Alba voice placed in space (P2-T7), every earcon with its switch and your own file (P2-T8), and the beacon (P2-T9).
* Verbosity presets and their switches (P2-T11).
* Themes, the map display setting, Isolate, names on the map and heading-up (P2-T12).
* Magnifier support on the desktop and in the web version (P2-T13).

## How to install and run it

* Desktop: dist_installer\TobyMap-0.1.0-setup.exe, or the portable zip, once built. It installs over 0.0.9.
* Web: `.venv\Scripts\python.exe tools\serve_web.py --pack E:\osmdata\tobymap\output\world\world.pack`, then the address it opens.
* The release notes, docs/release-notes.md, list what changed and the differences between the two versions.

## The automatic checks

* The Python tests: all 968 pass on this laptop, on Windows. One voice timing test failed once in a full run and passed when run again; it passes without the Phase 2 changes too. The acceptance scripts include two new ones for the terse and detailed presets on the Channel crossing.
* The browser tests: all 122 pass in Chromium and Firefox, including the new ones for the presets and the focus point at three window sizes.
* The high contrast themes pass the 7 to 1 contrast check, with every choice of the map display setting (VIS-2).
* The world pack built twice is identical (DMT-1), from P2-T10d.

## Known problems

* The world pack needs its writing stage run again (above).
* One older test, for spike S6's demo with eSpeak, crashed once inside eSpeak during a full run and passed when run again. It is a spike test, not part of TobyMap.
* The 1,000 km drawing on the world pack takes about 120 ms before names, and names add up to about 55 ms. Names are left out while a key is held, so stepping is not slowed.

## What was not tested

* Anything that needs your ears and screen reader: those are the checklists.
* Magnifiers with Windows Magnifier itself, and how the themes and names look: the sighted helper's checklist.
* A real Mac (PLT-2): GitHub's Mac runs the tests, but its clock is not exact enough to judge the held key's timing.

## Next

* Then your checklists, and your feedback against requirement IDs (DEL-4).
* When you accept, I ask whether to publish (DP110).
