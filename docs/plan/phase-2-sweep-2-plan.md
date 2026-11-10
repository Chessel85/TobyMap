# Phase 2 sweep 2: plan for your notes

This plan answers your notes from the second Phase 2 sweep, written on 9 November 2026. It covers three results files in docs/checklists:

* phase-2-desktop-results.txt
* phase-2-web-results.txt
* phase-2-visual-results.txt

Each task is called P2-T17 with a letter, and goes on a branch named after it. Each work item says which model should do it, Opus or Sonnet. Tasks that wait for your answer to a discussion point say so. The new discussion points are DP158 to DP165.

## Answers to your direct questions

### Why A does two things on the desktop, and S does nothing (15.1, 16.1)

Found. Your saved settings hold a key choice from an older version: Link step to zoom on A, from before it moved to S. A saved choice beats the built-in key, so A ran both commands, and S ran neither. The web version keeps its settings separately, so it was not affected. As you asked, task P2-T17a fixed this by clearing your saved key choices, with no code change.

### Why Enter on Cancel presses OK (3.5, 5.3, 8.2, 8.6)

Found. On the desktop, every button in a row is told never to take Enter, so Enter always goes to OK, wherever the focus is. Task P2-T17b fixes it.

### Where the lag after an arrow key comes from (2.11, 4.5)

Not known yet. Both the spoken place and the blocked sound are late, so it happens before either is sent, or in both players. One suspect: since P2-T16h, earcons play through the one sound mixer, whose sound card buffer may be large. Task P2-T17e measures each stage first, then reduces it.

### Are graticule lines drawn? (13.5)

Yes, in one thin line colour. The special lines are not yet drawn differently. Task P2-T17v adds that.

### Did you ask before for Enter on an Information panel item to go there? (11.7)

Yes, in your answer to DP155, and INF-10 lists jump as an action on every item. It was not built in Phase 2. Task P2-T17k adds it.

### What goes into the announcement history that is not a place? (7.6)

Everything TobyMap says goes in, not only places. For example: "Beacon on.", "Facing 45 degrees.", the verbosity preset's words, the zoom and step, the spatial voice's labels, and messages such as a key clash. DP158 asks whether to split it into a location history and the announcement history.

## Faults: things that do not work as the checklist says

### P2-T17a Old saved key choices (desktop 15.1 and 16.1; ACC-3, NAV-13)

* Done, 9 November 2026, with no code change, as you asked. Your saved key choices on the desktop were cleared, so every command now has its built-in key. The only saved choice was Link step to zoom on A.
* Why no code change: the key clash check already stops you choosing a key that clashes. This fault came only from a built-in key moving under an old saved choice, which is rare.
* To check: on the desktop, S links step to zoom, and A does only its own command.

### P2-T17b Enter on a button presses that button (desktop 3.5, 5.3, 8.2, 8.6; web 8.6, 10.6; ACC-7)

* Sonnet. On the desktop, a button with the focus takes Enter: Cancel cancels, Settings for this layer opens. Elsewhere in the dialog, Enter still presses OK.
* In the web version, Enter on a check box presses OK and never ticks the box. Only Space ticks it. This is in the layers list and the Settings tabs.
* A test in each shell for every dialog with buttons.
* Done, 9 November 2026, on branch P2-T17b.
* Desktop: every button in a row now takes Enter while it has the focus, as it takes Space. This is in the bearing box, Go to, the layers list, a layer's settings, Settings and the box for changing a key. The Settings for this layer button is no longer a second default, so Enter anywhere else in the layers list still presses OK.
* Web: the cause was not in the page. Pressed in Chromium or Firefox alone, Enter on a check box already pressed OK. With NVDA, the layers list and Settings were read in browse mode, where NVDA turns Enter on a check box into a click, so the page never saw the key. The layers list, a layer's settings and Settings are now marked as an application, as the map is, so NVDA stays in focus mode there and Enter reaches the page.
* To check with NVDA, as only you can: in the web version's layers list and Settings, Enter on a check box presses OK and leaves the box as it was; Enter on Cancel cancels. NVDA may now say "application" as you enter these dialogs. If it does and you dislike it, say so.
* Tests: 9 new desktop tests and 4 new browser tests. Each desktop test failed on the old code, except the two that check Enter in a field still presses OK.

### P2-T17c The place is said twice after a jump (desktop 5.2, 5.4, 7.4; web 5.2, 8.2)

* Opus. After Go to, or Enter in the history, the place is said by the jump and again when the focus comes back to the map. It should be said once.
* In the web version, closing the layers list said "United Kingdom" when every layer here was off. What is said as a dialog closes must come after the dialog's changes are made.
* Tests in both shells that a jump, and closing a dialog, say the place once.
* Done, 9 November 2026, in the same working copy as P2-T17b, not yet committed.
* The cause: NVDA reads the map's name as the focus comes back to it from a dialog, and the map's name is the place. The jump's announcement said the place as well, so you heard it twice.
* Now, in both shells, what a dialog's answer says becomes the map's name just before the dialog closes, and is not spoken as well. So Go to, Enter in the history and the bearing box are each heard once, as the focus arrives. They still go into the announcement history.
* If the answer says nothing, as after Cancel or the layers list, the map's name is the place after the dialog's changes. In the web version, the layers list now makes its changes before it closes, not after, so it no longer says the old place.
* Leaving the map names it after the place again, as before.
* Settings is unchanged: it never moves you, and its messages are still spoken.
* The rule is now in the user experience description, section 2, version 0.12.
* To check with NVDA, as only you can: desktop 5.2, 5.4 and 7.4, and web 5.2 and 8.2, each say the place once. In the web version, switch off Countries and Regions and press OK: you hear what Space then says, not "United Kingdom".
* Tests: 5 new desktop tests and 2 new browser tests, and 5 browser tests changed, which counted the place spoken a second time. The desktop tests for Go to, the history and the bearing failed on the old code.

### P2-T17d "Press F1 for keys" is never said at the start (desktop 1.2, web 1.2)

* Sonnet. Find why it is lost, probably cut off by the place, and make it heard in both shells.
* Done, 9 November 2026, in the same working copy as P2-T17b and P2-T17c, not yet committed.
* The cause, the same in both shells: the start was spoken, and then the focus arrived on the map. NVDA reads the map's name as the focus arrives, and that name was only the place, so the rest of the start was cut off. On the desktop, the start was spoken even before the window was shown.
* Now, as with a dialog in P2-T17c, the start is not spoken. The map's name, as the focus first arrives, is the place and then "Press F1 for keys", such as "Kent, England, United Kingdom. Press F1 for keys." NVDA says the window's title, TobyMap, before it. Leaving the map names it after the place, as ever.
* The start still goes into the announcement history, in full, with TobyMap at the front.
* With no pack installed, the map's name at the start is the message that says so.
* The words are in the core's templates, as start_label, and the rule is in the user experience description, section 2.
* To check with NVDA, as only you can: desktop 1.2 and web 1.2. You should hear TobyMap, the place, then "Press F1 for keys". In the web version, TobyMap comes from the page's title. If you hear TobyMap twice, or not at all, say so.
* Tests: 1 new core test; the start tests in both shells now check the map's name, and failed on the old code. The browser tests that counted the start as spoken now count from nothing.

### P2-T17e The lag after an arrow key (desktop 2.11, 4.5; NFR-1)

* Opus. Measure, on the world pack, the time from the key to each stage: the core's answer, the speech handed to NVDA, and the sound reaching the sound card. The test trace already records the first two.
* Reduce whatever is slow. If it is the mixer's buffer, ask the sound card for a smaller one.
* Report the times before and after, in plain words, in docs/plan.
* Done, 10 November 2026, on branch P2-T17e. The times are in docs/plan/p2-t17e-lag-timing.md.
* The cause of the late sounds: TobyMap used MME, Windows' oldest route to the sound card, which held each sound back about 105 ms. The desktop now uses WASAPI, shared, which holds it about 24 ms. If WASAPI will not open, the old route is used.
* The core answered in under 20 ms, and the speech was handed to the screen reader within 16 ms of the key. As you asked, nothing is changed for NVDA alone.
* To check with NVDA, as only you can: desktop 2.11 and 4.5. The blocked sound and the clicks should come sooner.
* Tests: 4 new desktop tests, with a stand-in for the sound library, so no sound device is opened. Three failed on the old code.

### P2-T17f Space on a group heading (desktop 11.6; SON-3)

* Sonnet. On the desktop, Space on a group heading repeats the last announcement instead of saying "Hear its direction works on an item, not on a group." The web version is right. Find why and fix it, with a test.
* Done, 10 November 2026, on branch P2-T17f.
* The cause was in the core, not the desktop. A group heading has no item, so the core kept the item last focused, which F3 goes back to. Space then used that item, so you heard it again. Its label goes only to Braille on the desktop, so it seemed like a repeat of the last announcement.
* Now the core notes when a heading has the focus, and Space there says "Hear its direction works on an item, not on a group." F3 still goes back to the item last focused.
* The web version sends the same thing for a heading, so it had the same fault after Space on an item. It passed your test probably because no item had been heard first. The fix is in the core, so it covers both.
* To check with NVDA, as only you can: desktop 11.6, after pressing Space on an item first. The same in the web version.
* Tests: 1 new core test and 1 new desktop test. Both failed on the old code.

### P2-T17g "Grouping" in Settings (desktop 2.10; ACC-1)

* Sonnet. Tab from the tab control lands on something NVDA calls "grouping" before the first setting. Tab should go straight to the first setting, in every tab.
* Done, 10 November 2026, on branch P2-T17f, with P2-T17f.
* The cause: each tab's settings sit in a scroll area, added in P2-T8 because the Earcons tab is taller than the dialog. The scroll area had no name and took the focus before the first setting, so NVDA called it "grouping". It no longer takes the focus, and it still scrolls to the setting that has it.
* Also: when the eight tabs do not fit across the dialog, Qt shows two arrows to scroll the tabs, and Tab could stop on them. They no longer take the focus. Left and Right on the tabs still go to every tab.
* To check with NVDA, as only you can: desktop 2.10. In each tab, Tab from the tab control goes straight to the first setting.
* Tests: 1 new desktop test, going through every tab. It failed on the old code.

### P2-T17h The layers list as a tree (desktop 8.1, web 8.6; SCP-6)

* Opus. Desktop: collapsing Boundaries leaves a blank line where NVDA says nothing, and collapsing Water too makes NVDA silent. Use what fixed the Information panel's tree (DP135).
* Web: the groups cannot be collapsed. Make them collapse with Left and Right, as in the Information panel.
* Both: Space ticks, Enter presses OK.

### P2-T17i Layer settings (desktop 8.6; SCP-7)

* Sonnet. Rename "closest zoom" and "farthest zoom" to "minimum zoom" and "maximum zoom", as you asked. As zoom is in kilometres, the minimum is the closest. The glossary gets both words first.
* Opus. The crossing sound you gave Countries did not play. Find out why, and fix it.
* Whether a zoom range changes what is said, as you expected with England, waits for DP160.

### P2-T17j Page Up with the step linked, in the web version (web 16.2; NAV-13)

* Sonnet. With the step linked to the zoom, Page Up changes only the zoom in the web version. It should change both, as on the desktop.
* A browser test.
* Your note on the desktop (16.2), that once only the zoom was said, is checked by the same test on the desktop.

## Changes you asked for

### P2-T17k The Information panel (desktop 10.4, 10.5, 11.5, 11.7; INF-10)

* Sonnet. Each group heading says how many items it holds, such as "Nearby, 5 items".
* Sonnet. Within items show the distance and direction to the area's centre, as Nearby items do (DP155).
* Sonnet. Enter on an item jumps there: to a point, or to an area's centre (DP155, INF-10).
* Sonnet. Ctrl+G, and Ctrl+B for a bearing, work from the Information panel and Details. After the jump, the focus stays where it was, on the first item of the same group.

### P2-T17l Shift goes the other way (desktop 4.4, other thoughts)

* Sonnet. Every key that goes round a list goes back with Shift: Shift+O for orientation and Shift+A for the verbosity preset. Shift+T already does this for themes.
* The key list and the key clash test are updated.
* The rule goes into the user experience description, so every new cycling key follows it.

### P2-T17m Home and End in number boxes (desktop 12.4)

* Sonnet. In every number box, in both shells, Home sets the largest value and End the smallest, as you asked.
* A test goes through every number box in Settings and the layer settings, so none is missed.

### P2-T17n The spatial voice stops at a key press (desktop 11.2; SON-3)

* Sonnet. Any key that runs a command stops the Alba voice, so it never talks over NVDA. Both shells.

### P2-T17o The bearing and Go to boxes (desktop 3.5, 5.3; NAV-8, NAV-12)

* Sonnet. The bearing box's label is only "Enter a bearing in degrees, or a compass direction:".
* A wrong entry opens a message box with an OK button, such as: "hello is not a valid bearing. Enter a value in degrees in the range 0 to 360. Or enter a compass direction such as north or SW." Go to does the same, with its own words. After OK, you are back in the box with your text.
* The words go in the core's templates, so both shells say the same.

### P2-T17p The Earcons tab, made simpler (desktop 10.6, 17; SON-6, SON-7, SON-8)

* Opus. The tab has the earcon volume at the top, as now, then one list of every earcon, each with a check box to play it or not.
* Below the list, one set of controls for the earcon chosen in the list: its own volume, its file (empty means the default), a Browse button, and a "Set to default" button.
* Each earcon having its own volume is new. DP163 asks how it works with the volume at the top.
* Both shells. Then sections 17 of both checklists can be tested.

### P2-T17q Always say the place (desktop 15; ACC-5)

* Opus. A Speech setting to say the place after every step instead of the tick. Waits for DP162, on what each preset says.

### P2-T17r Forward and back in Go to (desktop 5.10; NAV-8)

* Sonnet. "f" or "forward" and a number moves you forward, "b" or "back" backward, in cardinal and free facing only. In north-fixed it says these work only in the facing orientations. Waits for DP161, on the units.

### P2-T17s Directions in cardinal and free facing (desktop 11.4; ANN-5)

* Sonnet. Waits for DP159: whether to keep "behind you" and "to your right", or say directions in your chosen format.

### P2-T17t The announcement history and a location history (desktop 7.6; ANN-4, NAV-10)

* Opus. Waits for DP158, on the name, what goes in, and places in hidden layers.

### P2-T17u A listening test for sound in space and the voice (desktop 11.2, 18; SON-1, SON-2, SON-3, SON-9)

* Opus. A listening test like Phase 0's spikes S1 and S6, using tools/listening_test where it fits. It plays the same places, such as the North Atlantic to the south, with each option in turn, so you can compare them and choose.
* DP164 asks which options you want in it. My list: stereo with pitch, HRTF, how much lower the pitch is behind, how muffled sounds are behind, the voice behind at a lower pitch or not, a short sound before the voice or not, and an echo for "behind".
* It needs no window and uses your own headphones. You run it; I don't.

### P2-T17v The map for sighted users (visual notes; VIS-1, DAT-13)

* Opus. Draw the special lines (equator, prime meridian, tropics, polar circles, date line) thicker or in their own colour, in every theme, keeping 7 to 1 in high contrast.
* Opus. Find the straight horizontal line across France and the thick red line that zigzags and jumps from Sweden to Shetland. My guess for the red line: it is the current outline, drawn round a sea area such as the North Sea, whose edge runs from Shetland to Norway. If so, the current outline of a sea area may need a different look, or none. I will check with screenshots before changing anything.

## Left for Phase 3

* Regions and counties (visual notes). England, Scotland, Wales and Northern Ireland are regions in OSM, but not the same tier as French regions. DP165 asks how you want this, with Phase 3's hierarchy.
* Controls for sighted users: buttons to move, and a line showing the coordinates, zoom and step (other thoughts). Raised as part of DP165, to be planned with Phase 3.

## Still to test

* Section 17 of both checklists, after P2-T17p.
* Section 19 of the web checklist, Chrome or Edge, not done yet.
* Section 18 of the desktop checklist, after the listening test.
* DP157, from the last round, is still open: whether a letter before a number, such as "N51.5 W0.12", means a direction to move in.

## Order of work

1. Faults first: P2-T17b, P2-T17c, P2-T17d, P2-T17f, P2-T17g, P2-T17j. These are small, and you hit them on every test.
2. The lag, P2-T17e.
3. The layers list and its settings: P2-T17h, P2-T17i.
4. The changes: P2-T17o, P2-T17k, P2-T17l, P2-T17m, P2-T17n, then P2-T17p.
5. The tasks that wait for your answers, as each answer comes: P2-T17q, P2-T17r, P2-T17s, P2-T17t.
6. The listening test, P2-T17u, and the map for sighted users, P2-T17v.
7. Version 0.1.2: continuous integration green, a new installer, and a third sweep checklist covering only what changed.
