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
* Done, 10 November 2026, on branch P2-T17i. DP160 was answered (option B), so it is done here too.
* The words: the layer's settings now say "Minimum zoom" and "Maximum zoom", and a wrong range says "The minimum zoom must not be larger than the maximum zoom." Both words are in the glossary, with "crossing sound".
* Why the crossing sound did not play: crossing sounds were looked for only on line layers, such as the graticule. Countries is an area layer, so its sound could never play, although the dialog let you choose one. Now an area layer's crossing sound plays when a step ends in a different area of that layer from the one it started in, such as from England into France, or out to sea. A step that leaves a country and comes back into it within the same step plays nothing. It works for held steps too.
* The label in the dialog is now "Sound when a line or border of this layer is crossed".
* DP160: a layer outside its zoom range is now treated as switched off for what is said: the place after a step, Where am I, Within in the Information panel, and the map's name. If every area here is in a layer outside its range, you hear "No data at this zoom level".
* Zooming in or out finds the place again, so the map's name and Within follow the zoom, but nothing more is said as you zoom. Space says the new place. If you would like the place said when a zoom changes it, say so.
* Note: in the world pack, Counties have a maximum zoom of 100 kilometres, and Regions 1,000 kilometres. So, from today, at a zoom wider than 100 kilometres you no longer hear the county, and wider than 1,000 kilometres you no longer hear the region. You can widen either in the layer's settings.
* The size rule, which leaves small areas out of lists when zoomed out (DP80), still does not change what is said. Only the zoom range does, as DP160 asked.
* Requirements catalogue version 0.11 (ANN-7, SCP-7, INF-10) and user experience description version 0.13 (sections 4.4, 6 and 8) say all this.
* To check with NVDA, as only you can: desktop 8.6 and web 8.6. Open a layer's settings: you hear "Minimum zoom" and "Maximum zoom". Give Countries a crossing sound and step from Kent into France: it plays. Give Regions a maximum zoom of 100 kilometres, zoom out to 250 kilometres and press Space: you hear "United Kingdom", with no England (and no Kent, as Counties stop at 100 kilometres).
* Tests: 9 new core tests. 6 failed on the old code; the other 3 check what must stay the same, such as no sound for a step inside one country. 4 core tests, 2 desktop tests, 1 browser test and the Bering Strait acceptance script were changed for the new words or the new rule. The Bering script now starts at a 100 kilometre zoom, so its districts are still said.

### P2-T17j Page Up with the step linked, in the web version (web 16.2; NAV-13)

* Sonnet. With the step linked to the zoom, Page Up changes only the zoom in the web version. It should change both, as on the desktop.
* A browser test.
* Your note on the desktop (16.2), that once only the zoom was said, is checked by the same test on the desktop.
* Done, 10 November 2026, on branch P2-T17j.
* The cause was not in the web version. With the step linked, the step is the size in the step list nearest to a quarter of the zoom. The step list has gaps, so some neighbouring zooms share a step. Your checklist starts at a zoom of 25 kilometres with the step at 5 kilometres. Page Up goes to 50 kilometres, and a quarter of that, 12.5 kilometres, is still nearest to 5 kilometres. So the step stayed the same, and only the zoom was said. The desktop does the same, which explains your desktop note: it depends on the zoom you start from.
* The fix: with the step linked, Page Up and Page Down always say the zoom and the step, as NAV-2 asks, even when the step has not changed. The step keys do the same. The fix is in the core, so it covers both versions.
* Whether every zoom should have its own step when linked is DP166.
* To check with NVDA, as only you can: web 16.2 and desktop 16.2. From a zoom of 25 kilometres, press S, then Page Up: you hear "Zoom 50 kilometres, step 5 kilometres." Page Up again: "Zoom 100 kilometres, step 25 kilometres."
* Tests: 2 new core tests, 1 new desktop test and 1 new browser test. Each failed on the old code.

## Changes you asked for

### P2-T17k The Information panel (desktop 10.4, 10.5, 11.5, 11.7; INF-10)

* Sonnet. Each group heading says how many items it holds, such as "Nearby, 5 items".
* Sonnet. Within items show the distance and direction to the area's centre, as Nearby items do (DP155).
* Sonnet. Enter on an item jumps there: to a point, or to an area's centre (DP155, INF-10).
* Sonnet. Ctrl+G, and Ctrl+B for a bearing, work from the Information panel and Details. After the jump, the focus stays where it was, on the first item of the same group.
* Done, 10 November 2026, in the same working copy as P2-T17j, not yet committed.
* Group headings: "Within, 3 items", "Nearby, 1 item", "Crossed and passed, no items". Go to Within, Shift+1, keeps the plain name.
* Within items: "England, centre 140 kilometres west". The word "centre" is there because Nearby's distances are to the nearest point, and Within's to the centre of the area's bounding box, as in DP155.
* Enter on an item goes there, as a jump, so Alt+comma comes back. A point goes to the point, an area to its centre, and a line to the place its item is about. The new place is said, and the focus stays in the panel, on the first item of the same group. Enter on a group heading says "Go there works on an item, not on a group." In the web version, Enter on a group heading used to open or close it; it now does the same as the desktop. Right and Left still open and close a group.
* Ctrl+G and Ctrl+B now work from the map, the panel and Details. After the box closes, the focus goes back where it was. After Go to, in the panel, it is on the first item of the same group; after a bearing, on the same item, whose words change with the facing. Cancel goes back to the same item.
* What the answer says, such as the new place, is spoken after the focus arrives, not as the map's name, because the focus is not the map. Both shells now move the focus before speaking whenever the focus goes to the panel or Details, so the screen reader's reading of the item does not cut off the place.
* The user experience description is now version 0.14, and section 6.3 says that Enter goes there in Phase 2. The full list of actions on an item, from INF-10, is still for later.
* To check with NVDA, as only you can: desktop and web 10.4, 10.5, 11.5 and 11.7. In particular, after Enter on an item and after Go to from the panel, whether you hear both the item and the new place, and in which order.
* Tests: 14 new core tests, 7 new desktop tests and 4 new browser tests. Older tests that check the panel's words were updated to the new words.

### P2-T17l Shift goes the other way (desktop 4.4, other thoughts)

* Sonnet. Every key that goes round a list goes back with Shift: Shift+O for orientation and Shift+A for the verbosity preset. Shift+T already does this for themes.
* The key list and the key clash test are updated.
* The rule goes into the user experience description, so every new cycling key follows it.
* Done, 10 November 2026, in the same working copy as P2-T17j and P2-T17k, not yet committed.
* Shift+O goes back through the orientations: from north-fixed to free facing, then cardinal facing, then north-fixed. Shift+A goes back through the verbosity presets: from normal to terse, then detailed. From Custom, A goes to terse, as before, and Shift+A to detailed. Both are in the menus beside O and A, and in F1's list.
* A test checks that each key that goes round a list, O, A and T, has its Shift partner in the same region and menu. The test that no key is used twice where it could clash passes with the two new keys. Neither is on the list of screen reader and browser keys.
* The key list, docs/plan/phase-2-keys.csv, has a line for each new key, and one for Go there, Enter, from P2-T17k. Type a bearing and Go to coordinates now say they work anywhere. Your own column is unchanged.
* The user experience description is now version 0.15, with the rule in section 12. It also now says O for the orientation, not F, as built.
* To check with NVDA, as only you can: desktop and web, Shift+O and Shift+A on the map, each three times, and that they come back to where you started.
* Tests: 7 new core tests and 1 new desktop test. Each failed on the old code.

### P2-T17m Home and End in number boxes (desktop 12.4)

* Sonnet. In every number box, in both shells, Home sets the largest value and End the smallest, as you asked.
* A test goes through every number box in Settings and the layer settings, so none is missed.
* Done, 10 November 2026, in the same working copy as P2-T17j, P2-T17k and P2-T17l, not yet committed.
* Home sets the largest value and End the smallest, in every number box in Settings, in both versions. The value is then chosen, so typing replaces it.
* The layer settings have no number boxes: the minimum and maximum zoom are lists to choose from, where Home and End go to the first and last choice, as in any list.
* The test found a second fault, on the desktop. "Orientation beacon: seconds between each sound" goes from 0.5 to 5, but its box took only whole numbers, so 0.5 showed as 0 and could not be chosen. It now goes in steps of 0.5 in both versions: 0.5, 1, 1.5 and so on. A new test checks that every number setting fits its step.
* To check with NVDA, as only you can: desktop and web 12.4. In Settings, Sound, on "Orientation beacon: volume, in percent", Home gives 100 and End gives 0. On "Orientation beacon: seconds between each sound", End gives 0.5, and Up from there gives 1.
* Tests: 1 new core test, 1 new desktop test and 1 new browser test, each going through every number box. Each failed on the old code. The P2-T17l tests were not run in full, as you asked.

### P2-T17n The spatial voice stops at a key press (desktop 11.2; SON-3)

* Sonnet. Any key that runs a command stops the Alba voice, so it never talks over NVDA. Both shells.

### P2-T17o The bearing and Go to boxes (desktop 3.5, 5.3; NAV-8, NAV-12)

* Sonnet. The bearing box's label is only "Enter a bearing in degrees, or a compass direction:".
* A wrong entry opens a message box with an OK button, such as: "hello is not a valid bearing. Enter a value in degrees in the range 0 to 360. Or enter a compass direction such as north or SW." Go to does the same, with its own words. After OK, you are back in the box with your text.
* The words go in the core's templates, so both shells say the same.
* Done, 10 November 2026, on branch P2-T17o.
* The bearing box's label is now "Enter a bearing in degrees, or a compass direction:", with no help line. Go to's label is unchanged, "Enter latitude and longitude:".
* A wrong entry opens a message box with one OK button, titled as the box it came from: "Type a bearing" or "Go to coordinates". The words are not changed in the box any more.
* Bearing: "hello is not a valid bearing. Enter a value in degrees in the range 0 to 360. Or enter a compass direction such as north or SW."
* Go to: "hello is not a valid entry. Enter latitude and then longitude, such as 51.5, -0.12 or 51d 30m N, 0d 7m W. Latitude is up to 90 degrees and longitude up to 180. Or enter one of them alone to keep the other. Or enter a direction and degrees to move, such as north 5."
* If nothing was typed, the first sentence is "No bearing was entered." or "Nothing was entered." instead.
* After OK, or Enter, the focus is back in the field with your text, all of it chosen, so typing replaces it. Press End to correct it instead.
* The words are not spoken as well, because NVDA reads the message box as it opens. On the desktop it is a Windows message box, with the warning sound Windows gives it, if any. In the web version it is marked as an alert dialog, which NVDA reads the same way.
* The user experience description is now version 0.16 (section 2), and "message box" is in the glossary.
* To check with NVDA, as only you can: desktop and web 3.5 and 5.3. Type hello and press Enter: you hear the message box's title and words, and the OK button. Press Enter: you are back in the box, on hello. In the web version, if NVDA reads the words twice, or not at all, say so.
* Tests: 1 new core test and the two core tests for the boxes' words changed; 2 new desktop tests and 2 new browser tests, one each for the bearing and Go to. Three older desktop and browser tests were changed from words in the box to the message box. All Python tests pass, and the browser tests for the two boxes pass in Chromium and Firefox.

### P2-T17p The Earcons tab, made simpler (desktop 10.6, 17; SON-6, SON-7, SON-8)

* Opus. The tab has the earcon volume at the top, as now, then one list of every earcon, each with a check box to play it or not.
* Below the list, one set of controls for the earcon chosen in the list: its own volume, its file (empty means the default), a Browse button, and a "Set to default" button.
* Each earcon having its own volume is new. DP163 asks how it works with the volume at the top.
* Both shells. Then sections 17 of both checklists can be tested.
* Done, 10 November 2026, on branch P2-T17o, as you asked, with your answer to DP163.
* The tab is now one list, "Earcons", of every earcon, each with a check box. Space ticks it, Enter presses OK. Below the list are the controls for the earcon chosen in it: "Tick: volume, in percent", "Tick: your own sound file", Choose file and Use the default. Their names change with the earcon chosen, so NVDA always says which earcon they are for. Each earcon keeps its own changes until OK or Cancel.
* As you answered in DP163, there is no volume for all the earcons any more. Each earcon has its own, 100 percent at first. If you had set the old volume, each earcon now starts at that value, so nothing is louder than before. An earcon's volume also applies when it is placed in space, such as the item's direction sound.
* In the web version, each earcon in the list takes the focus itself, as the Information panel's items do. NVDA should say "checked" or "not checked" on each.

#### Your question in DP163: the beacon

No, I was not mixing up the two, but my words did not make the difference clear. There are two different sounds:

* The item's direction sound: played from an item's direction before its name, when you press Space on an item in the Information panel. It is an ordinary earcon, so it is in the list, with its check box, volume and file. It is now in the glossary under that name.
* The orientation beacon: the repeating sound from the North Pole, switched with B. It was in the old Earcons tab for its own file only, with its switch and volume in the Sound tab. That was why I asked about it.

As it had to be treated differently from every other earcon, I took it out of the list. Its own file is now in the Sound tab, after "Orientation beacon: seconds between each sound", so all its settings are together and every item in the Earcons list works the same way. If you would rather have it in the list, say so.

* Documents: the user experience description is now version 0.17 (sections 8.4 and 8.6), and the requirements catalogue version 0.12 (SON-6). Section 17 and step 10.6 of both checklists are rewritten for the new tab.
* To check with NVDA, as only you can: section 17 and step 10.6 of both checklists.
* Tests: 4 new core tests and 3 changed; 7 new desktop tests and 6 changed; 4 new browser tests and 3 changed. The desktop and browser tests that go through every setting now include the Earcons tab's list and its volume box.

### P2-T17q Always say the place (desktop 15; ACC-5)

* Opus. A Speech setting to say the place after every step instead of the tick. Waits for DP162, on what each preset says.

### P2-T17r Forward and back in Go to (desktop 5.10; NAV-8)

* Sonnet. "f" or "forward" and a number moves you forward, "b" or "back" backward, in cardinal and free facing only. In north-fixed it says these work only in the facing orientations. Waits for DP161, on the units.
* Done, 10 November 2026, with your answer to DP161, in the same working copy as P2-T17p, on branch P2-T17o, not yet committed.
* A number alone is in your own distance unit: kilometres in metric, miles in imperial, nautical miles in nautical. So "F24" is forward 24 kilometres in metric.
* Units can be typed instead, one or more, with or without spaces: km, mi, m and yds, as you listed. The words work too, such as kilometres, miles, metres and yards, and "yd". "F24mi240yds" is 24 miles and 240 yards, "B24km50m" and "B24.05km" are both back 24 kilometres and 50 metres. A unit used twice, such as "f 2km 3km", or a number with no unit after one with a unit, such as "f 24 km 3", is not read, and the message box opens.
* The move goes the way you face, exactly as Up and Down do. Back keeps you facing the same way. In cardinal facing east or west, it follows the line of latitude. Over a pole you come out facing the other way, and hear "Crossed the North Pole. Now facing south." before the place.
* It is a jump, so Alt+comma comes back, and the zoom and step stay.
* In north-fixed, a message box says "Forward and back work in cardinal and free facing. Press O to change the orientation, or enter where to go." After OK you are back in the box with your text.
* Go to's message for a wrong entry now ends: "In cardinal or free facing, enter f or b and a distance to move forward or back, such as f 24 or b 2 km 500 m."
* North, south, east and west are still in degrees, as before. Your answer was about F and B only. If you want units after north and the others too, say so.
* Requirements catalogue version 0.13 (NAV-8) and user experience description version 0.18 (section 5.7) say this. Step 5.11 is new in both checklists.
* To check with NVDA, as only you can: step 5.11 of both checklists.
* Tests: 25 new core tests for what is read and refused, and 4 for the move: north-fixed refused, forward and back in free facing, back in miles in cardinal facing, and over the North Pole. The test for Go to's message has the new last sentence.

### P2-T17s Directions in cardinal and free facing (desktop 11.4; ANN-5)

* Sonnet. Waits for DP159: whether to keep "behind you" and "to your right", or say directions in your chosen format.
* Done, 10 November 2026, with your answer to DP159 (option C), in the same working copy as P2-T17p and P2-T17r, not yet committed.
* A new setting in the Units tab, after Directions: "In cardinal and free facing, give directions from the way you face". It is off at first.
* Off: every direction in words is a compass direction in your chosen format, measured from north, in every orientation. This is a change: until now, cardinal and free facing always said "ahead right" and the like.
* On, in cardinal and free facing: the direction is measured from the way you face, in your chosen format, with "at your", as you asked. For example, "Manchester, 1.5 miles at your north-east", "Berlin, 25 kilometres at your 30 degrees", "at your 2 o'clock". Rounded degrees say "at about your 50 degrees". So "at your north" is ahead, "at your east" is to your right, and "at your south" is behind you.
* "Ahead", "behind", "to your right" and the other old words are gone.
* This covers Nearby, Within and Crossed and passed in the Information panel. The spatial voice says only the name and distance, so it is unchanged. Sound in space is always from the way you face, whatever the setting.
* In north-fixed the setting does nothing.
* Requirements catalogue version 0.13 (ANN-5, NAV-12) and user experience description version 0.18 (section 5.1) say this. Step 11.4 of both checklists now tries the setting.
* To check with NVDA, as only you can: step 11.4 of both checklists, and that the setting's name is clear to you.
* Tests: the 15 tests of each format's words were rewritten for "at your", and 3 new tests: the setting's place and default, that only the setting and a facing orientation measure from the way you face, and that the Information panel keeps compass directions when the setting is off and uses "at your" when it is on. The browser tests for Settings and Go to pass in Chromium and Firefox.

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
