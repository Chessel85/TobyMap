# Requirements Catalogue

Version 0.16, 11 November 2026. Derived from "high level requirements.md" (HLR) and the product owner's responses in "Discussion points.csv" (DP).

## Changes in version 0.16

This change comes from your answer to DP175, 11 November 2026, after the size trial (P3-T1a).

* PCK-1: the base pack's soft limit is about 400 MB, raised from 250 MB, so counties for the whole world go into it.

## Changes in version 0.15

These changes come from your notes on the Phase 2 sweep, 10 November 2026 (tasks P2-T18c, P2-T18g, P2-T18h).

* SCP-7: the names of the two ends of a zoom range are swapped. The maximum zoom is now the closest, the smaller distance, and the minimum zoom the farthest.
* SON-10: the beacon can come from the North Pole, the South Pole, or the equator at 0, 90 east, 180 or 90 west. Near the place chosen it fades out, and you are told.
* PLT-5: Reset all settings, in the Map menu, puts everything back as on a new installation, after asking.

## Changes in version 0.14

This change comes from your answer to DP158 (task P2-T17t).

* NAV-10 is now the location history: the places you stopped at, which Alt+Comma and Alt+Full stop go through, and a list of them, newest first, with Enter to go to one. A place whose areas are all in layers not shown is left out of the list and passed over.
* ANN-4 keeps only the repeat key. The list of everything said, the announcement history, is gone.
* SON-3: a spoken label can be repeated with Shift+Space, as the announcement history is gone.

## Changes in version 0.13

These changes come from your answers to DP159 and DP161 (tasks P2-T17s and P2-T17r).

* ANN-5 and NAV-12: in cardinal and free facing, spoken directions are compass directions in your chosen format, as in north-fixed, unless the new setting asks for directions from the way you face. Then they are in your chosen format with "at your", such as "at your 30 degrees" or "at your north-east". "Behind you" and "to your right" are gone. Sound in space is always from the way you face.
* NAV-8: in cardinal and free facing, Go to takes forward or back and a distance, such as "f 24" or "b 2km 500m".

## Changes in version 0.12

This change comes from your answer to DP163 and your note on desktop checklist 10.6 (task P2-T17p).

* SON-6: each earcon has its own volume, set in the Earcons tab, and there is no volume for all the earcons together.

## Changes in version 0.11

These changes come from your answer to DP160 and your notes on desktop checklist 8.6 (task P2-T17i).

* ANN-7: a layer outside its zoom range is not said, as it is not drawn (DP160). This covers the place said after a step, Where am I, and Within. If every area here is in a layer outside its zoom range, you hear "No data at this zoom level". The size rule (DP80) still applies only to lists, not to what is said.
* SCP-7: an area layer, such as Countries, can have a crossing earcon too. It plays when a step crosses the border of one of its areas.
* SCP-7: the two ends of a layer's zoom range are called the minimum zoom and the maximum zoom. The minimum zoom is the closest.

## Changes in version 0.10

These changes come from your answers to DP106 and DP108.

* ACC-2: F2 goes to the map, F3 to the Information panel and F4 to Details, from any region, on the desktop and the web (DP106). Ctrl+Alt+Space is dropped.
* INF-10: F3 goes to the Information panel, back to the item last focused there. Shift+Space (Within) and R (Nearby) are dropped. Whether the other groups keep their own keys is DP109.
* VIS-2: a map display setting for outlines and fill colours (DP108).
* NAV-3: in free facing, Left and Right turn 5° and Ctrl with them 1°, not 15° (DP147, accepted on 6 November 2026).

## Changes in version 0.9

This change comes from your acceptance of Phase 0.

* ACC-2: on the desktop, Tab in the menu bar moves along the menus, and Alt or Escape leaves it, as in other Windows programs. You said this normal behaviour is fine. In the web version, Tab still leaves the menu bar.

## Changes in version 0.8

This change comes from spike S3 and your answer to DP102.

* PCK-4: packs stay on GitHub Releases, and a copy is published to a TobyMap dataset on Hugging Face for the web version, because browsers cannot read GitHub Releases. Both cost nothing. The web version downloads packs whole into the browser's private storage. Now Agreed.

## Changes in version 0.7

These changes come from "architecture thoughts.txt" and your answers to DP81 to DP85. They add acceptance checks; they do not change what the user experiences.

* DAT-3: new checks for islands, Gibraltar, Ceuta and Melilla, and land borders on shared islands.
* DAT-14 (new): the antimeridian. Countries that cross the 180 degree line are drawn, measured and isolated correctly.
* DMT-7: no drive letter is assumed. Other data managers keep their data wherever they choose.
* DEL-5 (new): a Windows installer from the first release.
* PLT-2: the Mac version is still built and tested automatically, but Mac downloads wait until a Mac tester is found (DP92 asks you to confirm).

## Changes in version 0.6

These changes come from your answer to DP80 (DP78 asked again), and your agreement that look around plays the Nearby list. All discussion points are now answered.

* ANN-7, INF-10: lists that gather many features (Contains, Nearby, look around, Crossed and passed) show only visible features. Lists about one feature's own relationships, or about a search (Within, Bordering, Overlapping, Crossing, Search), always show everything from the layers that are switched on. Now Agreed.
* NAV-13, SCP-7: "visible" now also has a size rule for areas, as well as the zoom range for point and line layers (DP80). A small area, such as a field, is left out of these lists when zoomed out too far to see it. "Where am I" is still never limited.
* SON-4: look around plays the Nearby list in bearing order, so both always cover the same features.
* SON-9: a feature from a Kind 2 list that is beyond the view, such as a bordering country, plays from its true direction at the "beyond range" level (DP80). This is to be tried in the Phase 1 listening test.

## Changes in version 0.5

These changes come from your answers to DP76, DP77 and DP79. DP78 is still open. It is asked again more simply as DP80.

* NAV-13, SON-9: the zoom is a distance, the view radius, so the window size never changes what is heard (DP76). Now Agreed.
* NAV-4, NAV-8: moving to a feature in hierarchy mode, or jumping to an area, zooms to fit it. Backspace restores the old zoom (DP77). Now Agreed.
* NAV-2: when step and zoom are linked, the step is one quarter of the zoom distance, not one tenth (DP79). The keys and lists are Agreed.

## Changes in version 0.4

These changes come from your answers to DP63 to DP75, and your confirmation that switching off a layer removes it from both sight and sound. New questions are DP76 to DP79.

* Zoom and step are now separate (DP65). NAV-2 comes back as Step size. NAV-13 becomes Zoom. An option links the two.
  * Step controls: how far a step moves, where network travel stops, driving speed, and the passed nearby distance.
  * Zoom controls: the map zoom, the hearing range, the Nearby radius, and which layers are visible.
* New term, "visible": a feature is visible when its layer is switched on, the zoom is inside the layer's zoom range, and at least part of the feature is in view. Defined in NAV-13.
* ANN-7 is rewritten (DP66). The location announcement is never filtered by zoom or step: if you are in a field, you hear "Field". Zoom only filters lists, such as Contains, Nearby, and Crossed and passed.
* INF-4: Contains lists only visible features. A feature partly inside counts, with no "partly" label (DP70). The "regroup by county" command is dropped.
* INF-10: every list in the Information panel can be sorted by name, distance or bearing (DP70). Agreed, and open to change after testing (DP64).
* New SCP-7: a layer definition includes its sounds, its zoom range and its role in network mode (DP74).
* SCP-6 is now Agreed: a layer that is off is gone from sight and sound.
* Now Agreed:
  * LOC-4: no separate focus (DP63).
  * NAV-3, NAV-12: the turning keys, and cardinal facing east and west following the line of latitude (DP69).
  * NAV-4: identical boundaries announced once with both types (DP71).
  * NAV-5: travel stops at a junction, a stop point or the step distance (DP68).
  * NAV-14: driving speed in steps per second (DP72).
  * SON-9: distance in sound follows the zoom (DP67).
  * SON-10: the beacon can point at any pin (DP72).
  * VIS-1: a plus-shaped centre cross (DP73).
  * VIS-5: globe projection (DP73).
  * DAT-13: graticule and special lines as a layer (DP74).
* Proposed, with new questions:
  * NAV-13 and SON-9: the zoom is a distance from the centre to the edge of the view, so the window size does not change what is heard (DP76).
  * NAV-4, NAV-8: moving to a feature in hierarchy mode, or jumping to an area, zooms to fit it (DP77).
  * INF-10: which Information panel groups are limited to visible features (DP78).
  * NAV-2, NAV-13: the keys and default lists for zoom and step (DP79).
* DMT-7: the pipeline may use GeoDesk and the GOL files on E:, and all files on E: are kept for now (DP75).

## Changes in version 0.3

These changes come from UXReview.txt and your answers to DP56 to DP62. New questions are DP63 to DP75.

* New SCP-6: layers are shared by sight and sound. A layer switched off disappears from the map and from every announcement and list.
* PLT-4, LOC-6: only data that is present is announced. The "detailed data not installed" message is removed.
* LOC-4: the separate focus is replaced by the current feature, which is always where the user is (proposed, DP63). Search only jumps (NAV-8).
* LOC-6, DAT-4: seas and oceans form a hierarchy, and the user hears the name of the sea or ocean.
* NAV-2 is replaced by the new NAV-13, Scale: one control sets the step size, map zoom, sound range, nearby radius and level of detail (DP65).
* NAV-4: "down" lists the types of feature contained first. "Up" uses all active layers, and the parent must be larger (DP62). Identical boundaries are merged (proposed, DP71).
* NAV-5: line following is merged into network mode, because a line is a simple network. Arrival rules corrected: cardinal facing keeps its direction, and free facing takes the bearing of the last stretch of the line. Travel stops at a junction, a stop point or the step distance (proposed, DP68).
* NAV-7 is withdrawn and merged into NAV-5.
* NAV-12: turning keys work in every movement mode (proposed, DP69).
* New NAV-14, driving. New USR-6, tours (Later).
* ANN-2: the crossed and passed earcon is on by default, the list covers the most recent move only, and the passed nearby distance defaults to 10% of the step (DP58).
* New ANN-7: detail follows scale (proposed, DP66).
* INF-4: contents are grouped by feature type, listing only types present.
* INF-7: Nearby can be sorted by distance or by relative bearing.
* INF-10: the Results list becomes the Information panel, with fixed groups (proposed, DP64).
* SON-6: land and water earcons removed. Earcons added for driving past a point and for crossing lines of latitude and longitude.
* New SON-9: distance in sound is relative to the scale (proposed, DP67). New SON-10: orientation beacon.
* VIS-1: no cursor marker; the map is always centred on the location. New VIS-5: orthographic ("view from space") projection centred on the location (proposed, DP73).
* New DAT-13: graticule and special lines as a layer (proposed, DP74).
* DMT-7: build laptop details confirmed (DP60).

## Changes in version 0.2

These changes come from your answers to DP40 to DP55.

* SCP-4: the code licence is GPL-3.0 and the data packs are ODbL (DP40). Now Agreed.
* PLT-1, PLT-2, ACC-4: only Windows with NVDA can be tested from the start. JAWS and VoiceOver acceptance waits until testers are found. The Mac build is still designed and built from day one (DP49, DP54).
* PLT-3: the web version is now a Must, released alongside the Windows desktop version (DP49).
* ACC-4: default keys must also avoid browser keys that a web page cannot override.
* NAV-1, NAV-3, NAV-11 and the new NAV-12: navigation is restructured around three orientation modes (north-fixed, cardinal facing and free facing), cycled with one key (DP41). New questions DP56 and DP57 check that I have understood this correctly.
* NAV-1: a step over a pole is blocked with your blocked sound, and the cursor stays where it was (DP42).
* NAV-4: "up" goes to the one parent that contains the feature. If two parents overlap without one containing the other, a beep and a menu let the user choose (DP52). The lenses idea is dropped.
* NAV-5: how links are described now depends on the orientation mode (DP41).
* ANN-1: when nothing changes, only a tick plays (DP43).
* ANN-2: features crossed are no longer spoken. They go into a silent "crossed and passed" list, which also holds point features passed within a distance the user sets (DP44, DP45).
* SON-1: you will run the early listening test yourself (DP47).
* SON-2, SON-5: what counts as "ahead", and the sweep direction, follow the orientation mode.
* SON-3: spatial labels use the application's own voice. I have chosen the default for the screen reader copy (DP46).
* New SON-8: earcons are sound files that can be replaced, starting with the ones you will supply.
* PCK-1: the base pack has a soft limit of about 400 MB, and other packs aim for 1 GB or less (DP50, DP175).
* PCK-4: packs are hosted on GitHub Releases (DP48). Now Agreed.
* DAT-7: facts show their source and date (DP51).
* New DAT-12: continents are built from groups of countries (DP55).
* New DMT-7: the pipeline runs on your laptop, with large data on the external SSD (DP53).
* DEL-4: Windows 11 with NVDA is the only test environment that can be relied on (DP54).

## How to read this document

Each requirement has its own level 3 heading so you can jump between them with the screen reader heading keys. Each one has these fields:

* Outcome: what a user can do, or what must be true, written as a result rather than a design.
* Source: where it came from. HLR means the high level requirements, DP n means discussion point n.
* Priority: Must, Should, Could, or Later (a future version).
* Status: Agreed (the PO has confirmed it), Proposed (I derived it and it needs PO review), or Open (it depends on an unanswered question, given as DP n).
* Acceptance criteria: checks that show the requirement is met. Numbers marked "proposed" are my suggested targets, and you are welcome to change them.

"The user" means any end user. Where it matters, I name the user type: blind, partially sighted, sighted, or data manager.

The high level requirements document stays the product owner's own statement of intent. This catalogue is the version that will be traced into the implementation plan and its tests.

---

## 1. Scope and principles

### SCP-1 Desktop exploration tool
* Outcome: A user can explore and learn about any part of the world from their computer, including preparing for a visit to a place. The application does not track the user's real position.
* Source: DP1, DP8
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * The application never requests access to device location.
  * There is no turn-by-turn or live guidance feature.

### SCP-2 Equal footing for all users
* Outcome: Blind, partially sighted and sighted users can do the same tasks with the same tool. Anything the visual map shows can also be found out without sight, and anything a non-visual user does can be seen on the visual map.
* Source: HLR, DP23
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * Every command can be reached from the keyboard. A coverage test fails the build if a command has no key binding or menu entry.
  * For every layer drawn on the visual map, the features at the location can be found with a non-visual query.
  * The visual map is always centred on the shared location, shows which way the user faces, and outlines the current feature.

### SCP-3 Non-visual first
* Outcome: When a design choice favours one group over another, the choice that serves blind users is made, unless it makes the tool unusable for the others.
* Source: HLR
* Priority: Must. Status: Agreed.
* Acceptance criteria: Every UX decision record states how it affects screen reader users.

### SCP-4 Free and not for profit
* Outcome: The application and its data packs are free to obtain and use, and the source code is public. The code is licensed under GPL-3.0, so anyone who distributes a modified version must publish its source. The data packs are licensed under ODbL, because they are derived from OpenStreetMap.
* Source: DP5, DP40
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * The repository's LICENSE file is GPL-3.0.
  * Every third-party code library is compatible with GPL-3.0. For example, LGPL, MIT, BSD and Apache-2.0 are compatible. A dependency check in continuous integration fails the build otherwise.
  * Every data pack states that it is licensed under ODbL and credits "© OpenStreetMap contributors", together with the other sources' attributions (DAT-9).

### SCP-5 Explicitly out of scope
* Outcome: Everyone agrees on what will not be built.
* Source: DP1, DP2, DP15, DP17, DP23, DP32, DP34
* Priority: Must. Status: Agreed.
* Not in scope:
  * GPS or live navigation.
  * Mobile phone or tablet apps (a tablet may still serve as a touch surface, see section 10).
  * Shortest-path routing.
  * Natural language queries (possibly a much later version).
  * Users building their own data packs.
  * Editing geometry by hand.
  * Collaboration across more than one computer.

### SCP-6 Layers are shared by sight and sound
* Outcome: Every kind of feature belongs to a layer, such as roads, railway stations, national parks or postcode areas. A user can switch any layer on or off. A layer that is off is hidden from the visual map and is also left out of announcements, hierarchy movement, Nearby, the crossed and passed list and look around. Sighted and blind users therefore always work with the same set of features.
* Source: DP62, UXReview, PO confirmation on 30 October 2026
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * Switching off "Postcode areas" removes them from the map, from the Within group and from the choices offered by hierarchy "up".
  * Switching off a line layer also silences its crossing earcon and removes it from the network types offered in network mode.
  * The layers list is an accessible list of check boxes, reachable from the keyboard and from the menu.
  * Layer choices are saved between sessions (PLT-5).

### SCP-7 What a layer is
* Outcome: Everything about a kind of feature is defined in one place, its layer definition, so sight, sound and movement always treat it the same way. Adding a layer, such as the graticule, needs configuration rather than special code.
* Source: DP74
* Priority: Must. Status: Agreed.
* A layer definition holds:
  * its name, as heard in the layers list, and the group it belongs to, such as Transport or Boundaries
  * which features it contains, chosen by the pipeline
  * how it is drawn on the visual map in each theme
  * its zoom range, from its maximum zoom to its minimum zoom: the zooms at which it is visible and said (NAV-13, DP160). The maximum zoom is the closest, the smaller distance (P2-T18c). For example, motorways are visible at every zoom, and bus stops only when zoomed in to 1 km or closer.
  * for an area layer, its minimum size: how large an area must be, compared with the view, to count as visible (NAV-13, DP80)
  * its sounds: the crossing earcon, played when a step crosses one of its lines, or the border of one of its areas; the sound used for its features in look around and "hear its direction"; and the ding when one is passed while driving
  * whether it is a network type in network mode (NAV-5), and whether its points can be stop points (NAV-6)
* The data manager sets the defaults in the pack configuration. The user can switch a layer on or off, change its sounds, and widen or narrow its zoom range in the layers list.
* Acceptance criteria:
  * The graticule layer (DAT-13) is added by configuration alone, with no code that is specific to it.
  * Changing a layer's crossing earcon in the layers list changes the sound for that layer only.
  * Given a crossing earcon, the Countries layer plays it when a step goes from one country into another, or into or out of the sea beyond every country. A step that leaves a country and comes back into it within the same step plays nothing.

---

## 2. Platform and connectivity

### PLT-1 Windows with NVDA, then JAWS
* Outcome: A blind user on Windows 10 or 11 can use every feature with NVDA, and later with JAWS.
* Source: HLR, DP2, DP54
* Priority: Must for NVDA. Should for JAWS until a JAWS tester is found. Status: Agreed.
* Acceptance criteria:
  * The accessibility acceptance scripts pass with the current NVDA release on Windows 11. The PO runs these at every phase gate.
  * Once a JAWS tester is available, the same scripts pass with the current JAWS release. Until then, the design follows JAWS conventions, but nothing is claimed to be tested with JAWS.

### PLT-2 macOS designed in from the start
* Outcome: A Mac user can use the same feature set with VoiceOver. The Mac version is designed and built from the first release, even though real user testing may come much later.
* Source: HLR, DP2, DP49, DP54
* Priority: Must for the build. Should for VoiceOver acceptance until a Mac tester is found. Status: Agreed.
* Acceptance criteria:
  * Continuous integration builds the desktop application on macOS and runs the automated tests there for every change.
  * Mac downloads are not published until a Mac tester is found (DP92). Windows has an installer from the first release (DEL-5).
  * No feature depends on a Windows-only component unless a Mac equivalent is also built, or the gap is listed in the release notes.
  * Once a VoiceOver tester is available, the accessibility acceptance scripts pass on the current macOS with VoiceOver.

### PLT-3 Web version alongside the Windows version
* Outcome: A user can run the application in a web browser without installing it. Desktop and web share one code base, following the RecallScore (SReader) pattern. The web version is released at the same time as the Windows desktop version, to reach more users and to find testers, including Mac users.
* Source: DP3, DP49
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * The web version passes the accessibility acceptance scripts in current Chrome, Edge and Firefox with NVDA on Windows 11.
  * Safari with VoiceOver is tested once a Mac tester is available.
  * Feature differences from the desktop version are listed in Help and in the release notes. Expected differences are smaller offline storage and no touch tracing in the first web release.

### PLT-4 Online optional, offline capable
* Outcome: A user with data packs installed can work without an internet connection. A user who is online can explore areas they have not installed, possibly with slower responses. Only data that is present is announced: the application never announces that detail is missing.
* Source: DP4, UXReview
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * With the network disconnected, every feature works over the installed packs, apart from opening Wikipedia links.
  * With the network disconnected, moving into an area with no detailed data announces the base data names in the normal way, within the NFR-1 target, with no message about missing data. The application does not hang or crash.
  * The Details panel and the pack manager show which packs cover the location.
  * When online and the area is not installed, detailed data is fetched in the background. If it reveals a new, smaller area under the location, that area is announced when it arrives.

### PLT-5 Persistent settings
* Outcome: The user's settings, key bindings, bookmarks and last position are remembered between sessions.
* Source: Proposed
* Priority: Must. Status: Proposed.
* Acceptance criteria:
  * After restarting, the location, heading, zoom, step size, orientation, movement mode, active layers and all settings are restored.
  * The settings file can be exported and imported.

---

## 3. Accessibility foundations

### ACC-1 Speech and Braille through the screen reader
* Outcome: All text output reaches the user through their own screen reader, so it can be spoken and shown on a Braille display. The only exception is the optional spatialised spoken labels described in SON-3.
* Source: HLR, DP10
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * Every announcement in the acceptance scripts appears in the NVDA speech viewer.
  * Every announcement also appears on a Braille display, whether real or NVDA's Braille viewer.

### ACC-2 Complete keyboard operation
* Outcome: A user can do everything with the keyboard alone and never gets trapped.
* Source: HLR, DP13
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * Tab and Shift+Tab move through the map, the Information panel and Details, and focus always lands somewhere that is spoken. F2 goes to the map, F3 to the Information panel and F4 to Details, from any region, on the desktop and the web (DP106). The menu bar is reached with Alt on the desktop and Ctrl+Alt+M in the web version (DP93). In the web version, Tab leaves it. On the desktop, Tab moves along the menus and Alt or Escape leaves the menu bar, as in other Windows programs (PO, Phase 0 acceptance).
  * The map region works in application (focus) mode, so arrow keys reach the application rather than the screen reader's browse mode.

### ACC-3 Remappable keys and key help
* Outcome: A user can find out what any key does, see every command available in the current context, and change the key bindings.
* Source: DP13
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * F1 lists the commands for the focused region, each with its key.
  * A "key describer" mode speaks what each pressed key would do without doing it.
  * Assigning a key that is already in use warns the user and names the existing command.

### ACC-4 No clashes with screen reader keys
* Outcome: The default key bindings do not collide with common NVDA, JAWS or VoiceOver commands.
* Source: DP13, DP49, DP54
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * No default binding uses the NVDA key or the JAWS Insert key as a modifier.
  * No default binding uses the VoiceOver Control+Option combination, Escape (in the web version), Alt on its own, or F10.
  * No default binding uses a browser key that a web page cannot override. Examples are Ctrl+T, Ctrl+N, Ctrl+W, and Ctrl+1 to Ctrl+9.
  * Each default binding is tested with NVDA in both the desktop and web versions. Bindings are checked against the published JAWS and VoiceOver key lists, and tested with those screen readers once testers are available.

### ACC-5 Verbosity control
* Outcome: A user can choose how much is spoken automatically, both overall and for each kind of event.
* Source: DP14
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * Three presets are available: terse, normal and detailed.
  * Each kind of automatic announcement can be switched on or off: area change, zoom and step changes, heading, and no change. Crossed and passed features are never spoken automatically (ANN-2).

### ACC-6 Braille-friendly concise output
* Outcome: A Braille user can choose a concise output format that fits well on a 40-cell display.
* Source: DP10
* Priority: Should. Status: Agreed (to be refined with Braille users).
* Acceptance criteria:
  * In concise mode, the location change announcement in the acceptance scripts is no longer than 40 characters in at least 90% of cases (proposed).
  * Fields always appear in the same order.

### ACC-7 Standard accessible controls
* Outcome: Every part of the application outside the map works like a normal accessible application.
* Source: Proposed
* Priority: Must. Status: Proposed.
* Acceptance criteria:
  * Dialogs, lists and trees use native or correctly roled controls with labels.
  * Every dialog has a Close or Cancel button.
  * The non-map interface meets WCAG 2.2 level AA.

### ACC-8 Works with magnifiers
* Outcome: A partially sighted user can use Windows Magnifier, ZoomText or macOS Zoom, and the magnified view follows the location as it moves.
* Source: DP22
* Priority: Should. Status: Proposed.
* Acceptance criteria:
  * With Windows Magnifier set to follow the keyboard focus, the centre of the map stays inside the magnified view after every move.

### ACC-9 Language of names
* Outcome: The interface is in English. Each feature name is given in the user's preferred language when available, and otherwise in the local name. Names are marked with their language so a screen reader can switch voice if the user has set it up to.
* Source: DP9
* Priority: Must for English and the fall-back. Should for the language markup. Status: Agreed.
* Acceptance criteria:
  * With English chosen, Germany is announced as "Germany", and a place with no English name is announced by its local name.
  * In the web version, names carry a lang attribute.

---

## 4. Location model

### LOC-1 Exact position always available
* Outcome: A user can always find out the exact latitude and longitude of the location, in the format they choose.
* Source: DP7, DP12
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * A single key speaks the coordinates, in either decimal degrees (5 decimal places, about 1 m) or degrees, minutes and seconds.
  * The coordinates can be copied to the clipboard.

### LOC-2 Location described by the smallest containing area
* Outcome: While moving, the user's location is described by the smallest named area under the location.
* Source: DP12
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * Example: the location is in a lake, inside a field, inside a county, inside a national park, inside a country. The location is announced as the lake.
  * Ties between areas of equal rank are broken by smallest area.

### LOC-3 Full containment list on demand
* Outcome: A user can hear and browse every area that contains the location, from smallest to largest, in the Within group of the Information panel, and act on any of them.
* Source: DP12, HLR
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * For the lake example, the list contains, in order: lake, field, county, national park, country, continent.
  * The list is a navigable list. Every item offers the usual actions (INF-10).

### LOC-4 The current feature
* Outcome: There is one current location and no separate focus. The current feature is what the user is on: the smallest area under the location when stepping, the feature last moved to in hierarchy mode, or the junction or link in network mode. A user can find out about any other feature, without moving, from its item in the Information panel (INF-10).
* Source: DP12, UXReview, DP63
* Priority: Must. Status: Agreed (replaces the earlier "focus separate from cursor", DP63).
* Acceptance criteria:
  * Choosing "details" or "bordering" on an Information panel item answers about that item and does not move the location.
  * Choosing "jump" on an item moves the location there and makes it the current feature.
  * Every answer states which feature it is about.

### LOC-5 Plain-language position
* Outcome: A user who finds latitude and longitude hard to picture can hear a plain description of where they are. Examples: "north-west France", or "12 km south-east of Southampton city centre".
* Source: DP7 (PO said that lat/long is the only known way of giving position)
* Priority: Should. Status: Proposed.
* Acceptance criteria:
  * The description gives the position within the containing country or region, using a 3 by 3 grid such as "north-west" or "central".
  * It also gives the distance and compass direction from the nearest notable settlement.

### LOC-6 Somewhere is always somewhere
* Outcome: Every point on Earth has a meaningful name, including mid-ocean, Antarctica and unclaimed land. At sea, the user hears the name of the sea or ocean. Water is a hierarchy like land: oceans contain seas, seas can contain other seas, and seas contain gulfs, bays, straits and channels.
* Source: Proposed, UXReview
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * At 30° N 40° W, the location is announced as the North Atlantic Ocean.
  * In the Bay of Biscay, the Within group lists the Bay of Biscay, then the North Atlantic Ocean, then the Atlantic Ocean.
  * At 80° S 30° E, the location is announced as Antarctica.
  * No location is ever announced as blank or "unknown". The fall-back is the ocean or continent name.

### LOC-7 The location has a heading
* Outcome: The location has a heading in degrees, which is the direction the user is facing. In the north-fixed orientation it is always north. In the facing orientations it is used for movement, for describing directions, and for sound (NAV-12).
* Source: DP11, DP19, DP41
* Priority: Must. Status: Agreed.
* Acceptance criteria: The heading can be queried, and it is shown on the visual map as an arrow at the centre.

---

## 5. Navigation

### NAV-1 Stepping in the north-fixed orientation
* Outcome: In the north-fixed orientation (NAV-12), a user can move north, east, south or west by the step size (NAV-2) using the arrow keys.
* Source: DP11 method 1, DP42
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * Up moves north along the meridian by the step size, and Down moves south.
  * Right and Left move east and west along the line of latitude by the step size.
  * Moving east past 180° continues seamlessly from 180° W.
  * If a north or south step would reach or pass over a pole, the blocked sound plays (SON-8) and the location does not move. Nothing is spoken at normal verbosity.

### NAV-2 Step size
* Outcome: A user can choose how far each move goes, from a few metres to a thousand kilometres, independently of the zoom (NAV-13). This lets them move in small steps while hearing about a wide area, or take large steps while zoomed in. It is like a sighted user clicking either close to the centre of the map or far from it.
* Source: DP11, DP65
* Priority: Must. Status: Agreed.
* The step size sets:
  * how far one step moves in stepping mode (NAV-1, NAV-3)
  * the furthest that one move travels along a link in network mode (NAV-5)
  * the unit of driving speed, in steps per second (NAV-14)
  * the default passed nearby distance, 10% of the step (ANN-2)
* Acceptance criteria:
  * The available step sizes are 10 m, 25 m, 50 m, 100 m, 250 m, 500 m, 1 km, 5 km, 25 km, 100 km, 250 km and 1000 km (DP79). The list can be edited in settings.
  * One pair of keys makes the step larger or smaller, and announces it, for example "Step 250 metres". The zoom does not change.
  * Option: "link step to zoom", off by default. When it is on, changing the zoom sets the step to one quarter of the zoom distance, rounded to the nearest step in the list, and changing the step sets the zoom to four steps, rounded to the nearest zoom in the list (DP79). Both are announced, for example "Zoom 1 kilometre, step 250 metres".
  * Imperial equivalents are used when imperial units are selected.

### NAV-3 Stepping in the facing orientations: turn and move forward
* Outcome: In the cardinal facing and free facing orientations (NAV-12), a user turns to face a direction and then moves forward or back by the step size. Both orientations can move over the poles.
* Source: DP11 methods 2 and 3, DP41, DP69
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * Cardinal facing: in stepping mode, Left and Right turn by 90°, so the user always faces north, east, south or west.
  * Cardinal facing (DP69): moving east or west follows the line of latitude, as in north-fixed. Moving north or south follows the meridian and carries on over the pole, after which the user faces the opposite way.
  * Free facing: in stepping mode, Left and Right turn by a fine amount that can be set (default 5°, DP147), and Ctrl with Left and Right by a finer amount that can be set (default 1°). Shift with Left and Right turn by a large amount that can be set (default 90°), as in NAV-12. Held, the keys repeat, so 5° a step gives about 30° a second.
  * Free facing: moving forward follows the shortest path over the globe (a great circle). Afterwards, the heading is the direction of travel on arrival. From 80° N 0° E, facing 0°, moving forward 2000 km arrives at about 82° N 180° E, and the heading becomes 180°. This is checked to within 0.01°.
  * The new heading is announced after crossing a pole.

### NAV-4 Hierarchy mode
* Outcome: A user can move through the world as a nested hierarchy: world, continent, country, subdivision and so on, and the same for oceans and seas. They can go up to the parent, down into the features contained, and across to neighbours that border, touch or overlap.
* Source: DP11, DP52, DP62, DP70, DP71, UXReview
* Priority: Must. Status: Agreed.
* The rule for "up":
  * Every active layer takes part (SCP-6). There is no fixed list of hierarchy categories.
  * The parents of a feature are the larger areas that fully contain it. The next parent up is the smallest of them, provided all the other parents also contain it.
  * The choice is ambiguous only when two parents each contain the feature but neither contains the other. An example is a field inside both a county and a national park, where the park crosses the county boundary.
  * When it is ambiguous, a short beep plays and a menu lists the choices. The user picks one, or cancels and stays where they are.
  * An area with exactly the same boundary as the current feature is not a parent. The two are announced once, with both types, for example "Isle of Wight, county and unitary authority" (DP71). The pipeline detects identical boundaries within a small tolerance. How well this works will be reviewed in testing.
  * The Within group (LOC-3) always shows every parent.
* The rule for "down":
  * Down first lists the types of visible feature inside the current feature (NAV-13), each with a count, for example "Counties 92, National parks 15". Points, lines and areas are all included.
  * Only types that are actually present and visible are listed. If Kent contains no national park, "National parks" is not listed under Kent.
  * Choosing a type lists its features. Choosing a feature moves into it.
  * This is the same list as the Contains group (INF-4).
* Zoom (DP77): moving to a feature in hierarchy mode zooms the view to fit that feature. Without this, "down" from the United Kingdom at a 1 km zoom would list only what is within 1 km.
* Acceptance criteria:
  * From Hampshire, "up" goes to England, then the United Kingdom, then Europe, then the World, with no menu, when only administrative layers are active.
  * From a field inside both Hampshire and the New Forest National Park, "up" beeps and offers "Hampshire" and "New Forest National Park".
  * "Down" from France lists types including "Regions", and choosing it lists France's regions.
  * "Down" from a county with no national park does not list "National parks".
  * "Down" from the United Kingdom, zoomed to fit it, does not list bus stops, because bus stops are not visible at that zoom.
  * "Neighbours" of France includes Spain, Belgium, Germany and the others it borders, and the user can move straight to any of them. Neighbours are ordered clockwise starting from ahead, and their directions are described in the current orientation (NAV-12).

### NAV-5 Network mode: junction to junction, along any line
* Outcome: A user can travel along any network or line: roads, paths, railways, waterways, coastlines, borders, and lines of latitude and longitude. A single line, such as an island's coast, is a simple network. Standing at a junction, the user can hear every link leading away: its name, direction, length, and where it leads. They can then travel along any of them.
* Source: DP11 method 4, DP41, DP57, DP68, UXReview
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * Pressing the network mode key again cycles the network type, and the type is announced. The network types offered are the active line layers marked as network types (SCP-7).
  * On entering network mode, the location snaps to the nearest point on the nearest line of the chosen type, or to a junction if one is close, and the distance moved is announced.
  * At a test junction where three roads meet, three links are listed.
  * On borders, junctions are points where three or more borders meet. Going round Germany stops at each tripoint.
  * In north-fixed, each link's direction is given relative to north in the user's chosen format, for example: "Spring Road, north-east, 140 metres, to junction with Catherines Close". After travelling a link, the user faces north.
  * In cardinal facing, directions are given relative to the cardinal direction the user faces. After travelling a link, the user still faces the same cardinal direction as before.
  * In free facing, directions are given relative to the way the user faces. After travelling a link, the user faces the bearing of the last stretch of the line before the junction. A road leaving north and arriving heading east leaves the user facing east.
  * Rivers are described as upstream or downstream as well as by direction.
  * Travel along a link stops at whichever comes first: the next junction, the next stop point (NAV-6), or the step distance (NAV-2) (DP68).
  * Junctions that are just a bend in the same line, with only two links of the same name, are skipped.
  * Following the River Thames downstream from its source announces the counties it enters, in order, and ends with "Mouth of the River Thames, North Sea".

### NAV-6 Network mode: stop at points of interest
* Outcome: When travelling along a link, a user can choose to stop at points of interest along the way, such as bus stops, crossings, bridges and stations.
* Source: DP11 method 5
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * With stopping switched on, travelling a link that has a bus stop stops at the bus stop and announces "Bus stop, <name>, 60 metres along Spring Road".
  * The categories that cause a stop can be chosen.

### NAV-7 Follow a line (merged into NAV-5)
* This requirement is merged into NAV-5. A line is a simple network, so following a river, coast or border works the same way as travelling a road network (UXReview).

### NAV-8 Jump
* Outcome: A user can jump to a search result, a bookmark, any item in the Information panel, or coordinates they type in. Choosing a search result always jumps; there is no "focus only" option.
* Source: DP11, UXReview
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * Jumping to an area zooms the view to fit it. Jumping to a point or to coordinates keeps the current zoom. Going back (NAV-10) restores the previous zoom as well as the previous position (DP77).
  * All of these coordinate formats are accepted: "51.5, -0.12", "51.5N 0.12W" and "51°30′N 0°07′W".
  * Input that cannot be read gives an error saying which formats are accepted.
  * In cardinal and free facing, "f" or "forward" and a distance moves forward, and "b" or "back" moves back, along the way the user faces. A number alone is in the user's distance unit: kilometres, miles, or nautical miles. Units may be typed instead, one or more of km, mi, m and yds: "F24mi240yds" is 24 miles and 240 yards, "B24.05km" is back 24 kilometres and 50 metres. In north-fixed, Go to says "Forward and back work in cardinal and free facing." (DP161).
  * Pressing Enter on a search result moves the location there and announces it.

### NAV-9 Mouse and pointer
* Outcome: A sighted or partially sighted user can click the visual map to move the shared location there. The map then re-centres on it. The new location is announced exactly as if it had been reached by keyboard.
* Source: DP11, DP23
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * A click moves the location and triggers the normal announcement.
  * Hover announcements are off by default and can be switched on.

### NAV-10 Location history
* Outcome: A user can go back and forward through places they have recently been, like browser back and forward, and pick one from a list.
* Source: Proposed, DP142, DP158
* Priority: Should. Status: Agreed.
* Acceptance criteria:
  * After a jump, "back" returns to the previous position.
  * Every step, jump, Go to and click adds a place; holding an arrow key adds one, where the hold started; going back or forward adds none (DP142).
  * At least the last 1,000 positions are kept.
  * A setting, "Clear the places on start", off at first, starts each run with no places.
  * The location history lists the same places, newest first, with where you are now marked and chosen as it opens. It holds places only, not other announcements (DP158).
  * Enter on a place goes there as going back or forward would, adding no place.
  * A place whose areas are all in layers not shown, switched off or outside their zoom range, is left out of the list, and back and forward pass over it. It is kept, and comes back if the layer is shown again (DP158, DP160).

### NAV-11 One location, many modes
* Outcome: All movement modes and orientations share one location, so switching never moves the user.
* Source: DP11, DP41
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * Switching movement mode or orientation announces the new name and leaves the location where it is.
  * Switching to north-fixed sets the heading to north. Switching from free facing to cardinal facing turns the user to the nearest of north, east, south or west, and announces it.
  * Exception: entering network mode snaps the location to the nearest line or junction and announces the distance moved.

### NAV-12 Three orientation modes
* Outcome: A user chooses how they are oriented, and this decides how the arrow keys move, how directions are described and where sounds appear. One key cycles through the three orientations. They apply to every movement mode. The user can turn in every movement mode.
* Source: DP11, DP41, DP56, DP69, UXReview
* Priority: Must. Status: Agreed.
* The three orientations are:
  * North-fixed: the user always faces north. In stepping mode, the arrow keys move north, east, south and west. Directions are given relative to north, in the user's chosen format (ANN-5).
  * Cardinal facing: the user faces north, east, south or west, and turns in 90° steps. Directions are given as in north-fixed, or from the way they face if the user chooses (ANN-5, DP159).
  * Free facing (free roaming): the user can face any bearing. Directions are given as in cardinal facing.
* The movement modes that combine with them are stepping, hierarchy and network.
* Turning (DP69):
  * Shift+Left and Shift+Right turn by the large amount in free facing (default 90°, a setting), in every movement mode.
  * Ctrl+Left and Ctrl+Right turn by the fine amount in free facing, in every movement mode.
  * In stepping mode, in cardinal facing, Shift and Ctrl with Left and Right do nothing and make no sound, because Left and Right already turn 90° (PO notes on the Phase 2 checklist, 2.2 and 2.3). In network mode, where Left and Right choose links, Shift with Left and Right will turn 90° in cardinal facing.
  * A command lets the user type an exact bearing, which switches to free facing if needed.
  * In north-fixed, Shift and Ctrl with Left and Right do nothing and make no sound.
* Acceptance criteria:
  * A single key cycles north-fixed, cardinal facing, free facing, then back to north-fixed. Each change is announced, for example "Free facing, 47 degrees".
  * A feature at a bearing of 90° from the location is described as "east" in north-fixed. With the user facing 90° in either facing orientation, it is described as "ahead" (or "12 o'clock" in clock face format).
  * In network mode in cardinal facing, Shift+Right turns from north to east without moving or changing the selected link.

### NAV-13 Zoom
* Outcome: One control sets how much of the world the user is looking at and listening to, from a street to a whole hemisphere. The zoom is shared by sight and sound. It is separate from the step size (NAV-2), unless the user links them.
* Source: DP11, UXReview, DP65, DP67, DP70
* Priority: Must. Status: Agreed.
* The zoom sets:
  * the zoom of the visual map
  * the hearing range (SON-9)
  * the Nearby search radius (INF-7) and the range of look around (SON-4)
  * which features are visible, and so which appear in Contains, Nearby, and Crossed and passed (ANN-7)
* The zoom is given as a distance, the view radius. "Zoom 5 kilometres" means that everything within 5 km of the location is in view and in hearing range. Changing the size of the window never changes what is in view or in hearing range (DP76).
* The visual map has a fixed scale for each zoom, as on paper: the zoom distance is always drawn the same distance from the centre, so a bigger window shows more map round the edges, beyond the view radius (DP138). V says how much map the window shows.
* In imperial units the zoom and step lists have their own round sizes, in yards and miles. Switching units moves to the nearest size in the other list (DP136).
* A feature is visible when all of these are true:
  * its layer is switched on (SCP-6)
  * the zoom is inside its layer's zoom range (SCP-7)
  * at least part of it is within the view radius
  * for an area, it is large enough to see at this zoom: its width is at least its layer's minimum size, by default 2% of the zoom distance (proposed, DP80). At a 5 km zoom, a 50 m pond is not visible, but a 200 m lake is.
* Acceptance criteria:
  * The available zooms are 100 m, 250 m, 500 m, 1 km, 2.5 km, 5 km, 10 km, 25 km, 50 km, 100 km, 250 km, 500 km, 1000 km, 2500 km and 10,000 km (DP79). At 10,000 km the whole hemisphere is in view. The list can be edited in settings.
  * One pair of keys zooms in and out, and announces it, for example "Zoom 5 kilometres". The step size does not change unless it is linked (NAV-2).
  * Zooming the visual map with the mouse wheel or a pinch changes the zoom to the nearest value in the list, and the new zoom is announced.
  * With the zoom at 5 km, a feature 4 km away is heard and is in view whether the window is maximised or half the width of the screen.
  * Imperial equivalents are used when imperial units are selected.

### NAV-14 Driving
* Outcome: A user can move continuously instead of in steps, at a speed they choose, in network mode or stepping mode.
* Source: UXReview, DP72
* Priority: Should. Status: Agreed.
* Acceptance criteria:
  * One key starts driving, and any movement key stops it.
  * Speed is set in steps per second, so it follows the step size (NAV-2), not the zoom.
  * In network mode, driving follows the current link through bends and name-only junctions, and stops at the next junction where a choice is needed.
  * In stepping mode, driving goes ahead along the heading as a great circle, or in north-fixed in the direction of the last arrow key.
  * Area changes are announced as usual. Passing a point of interest within the passed nearby distance plays a ding and adds it to the crossed and passed list.
  * Speech never falls behind: if area changes come faster than they can be spoken, only the latest is spoken (ANN-3).

---

## 6. Announcements

### ANN-1 Announce what changed
* Outcome: After a move, the user hears only what has changed.
* Source: DP14, DP43
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * Moving from a lake into the field around it announces the field.
  * Moving into an adjacent field in a different county announces the new field's name and the new county.
  * Changed parent areas are listed from smallest to largest.
  * When a step changes nothing, only the soft tick sound plays (SON-8). At detailed verbosity, the area name is also repeated.
  * There is no special earcon for crossing a border or the coast, because the new name makes it clear.

### ANN-2 Crossed and passed list
* Outcome: After each move, the user can open a list of what the move jumped over or passed close to. Nothing in it is spoken automatically, but an earcon says that something was added.
* Source: DP44, DP45, DP58
* Priority: Must. Status: Agreed.
* The list holds:
  * line features crossed, such as rivers, roads, railways and borders
  * areas passed over completely, entered and left within the same step, such as a small lake
  * point features that the path of the step passed within the "passed nearby" distance, such as a railway station, each with its closest distance and the bearing to it from the new position
* Settings:
  * The "passed nearby" distance defaults to 10% of the step size. The user can change the percentage or set a fixed distance.
  * Only layers that are switched on (SCP-6), and whose zoom range includes the current zoom (ANN-7), are included. The step's path can reach beyond the view, so the "in view" part of the visible rule does not apply here.
  * The earcon for "something was added" is on by default and can be switched off.
* Acceptance criteria:
  * A 1 km step across the River Itchen lists "River Itchen, crossed" and plays the earcon. Nothing about it is spoken.
  * With a 5 km step and the default setting, a step whose path passes 300 metres from a railway station lists that station with "closest 300 metres". A path passing 800 metres away does not.
  * A 5 km step over a small lake lists the lake as "passed over".
  * The list covers the most recent move only.
  * Building the list never delays the location announcement (NFR-1).

### ANN-3 Fast key repeat
* Outcome: When the user holds down or rapidly presses a movement key, speech does not fall behind. Only the latest position is spoken.
* Source: Proposed
* Priority: Must. Status: Proposed.
* Acceptance criteria: After 10 rapid moves, speech for the earlier moves is interrupted, and the final position is spoken within the latency target in NFR-1.

### ANN-4 Repeat
* Outcome: A user can repeat the last announcement.
* Source: Proposed, DP158
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * A single key repeats the last announcement.
  * There is no list of past announcements. The places you have been are in the location history (NAV-10, DP158).

### ANN-5 Units and direction formats
* Outcome: A user can choose how distances and directions are spoken.
* Source: DP7
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * Distances can be metric or imperial. Nautical miles are an extra option for sea.
  * Bearings can be given as exact degrees, rounded degrees (to 5° or 10°), clock face, or compass points (4, 8, 16 or 32 points).
  * For a bearing of 47°:
    * exact gives "47 degrees"
    * rounded to 10° gives "about 50 degrees"
    * clock face gives "2 o'clock"
    * 8 or 16 points gives "north-east"
    * 32 points gives "north-east" (the range 39.4° to 50.6°)
  * In every orientation, directions are measured from north by default. A setting, "In cardinal and free facing, give directions from the way you face", off at first, measures them from the user's heading in the facing orientations instead, in the same format with "at your": "Berlin, 25 kilometres at your 30 degrees", "Manchester, 1.5 miles at your north-east", "at your 2 o'clock" (DP159). Sound in space is always placed from the way the user faces (SON-2).

### ANN-6 Disputed areas
* Outcome: When the data source marks an area or border as disputed, the user is told so.
* Source: DP28
* Priority: Should. Status: Agreed.
* Acceptance criteria: Entering an area flagged as disputed adds "disputed" to the announcement, and the details name the source's view.

### ANN-7 Detail follows zoom, but where you are is always told
* Outcome: Lists that gather many features show only what is visible at the current zoom, so a continent-wide view is not flooded with bus stops. What is said about where you are follows the layers' zoom ranges, so what you hear always matches what is drawn (DP160).
* Source: UXReview, DP66, DP70, DP160
* Priority: Must. Status: Agreed (DP78, DP80, DP160).
* Acceptance criteria:
  * The location announcement (ANN-1), "where am I" and the Within group use every layer that is switched on and inside its zoom range (DP160). The step never changes them, and nor does the size rule. With Regions given a minimum zoom of 100 km, at a 250 km zoom you hear "Kent, United Kingdom", not "Kent, England, United Kingdom".
  * If there are areas here, but every one is in a layer outside its zoom range, "No data at this zoom level" is said. If every one is in a layer that is switched off, "Every layer here is switched off" is said, as before (LOC-6).
  * Contains, Nearby, look around, and Crossed and passed include only features whose layer is visible at the current zoom (NAV-13). For example, with default layer settings, motorways appear at every zoom, and bus stops only at 1 km zoom or closer.
  * Within, Bordering, Overlapping, Crossing and Search are about the current feature's own relationships, or about what the user asked for, so they use every active layer, whatever the zoom (DP80).
  * At the United Kingdom zoomed to fit, Contains does not offer bus stops, so the application never has to list tens of thousands of them.

---

## 7. Information and queries

### INF-1 Feature details
* Outcome: A user can get the details of the current feature, or of any item in the Information panel.
* Source: HLR, DP31
* Priority: Must. Status: Agreed.
* Details include, where known:
  * name and alternative names
  * type
  * area or length
  * population
  * elevation or depth
  * parent areas
  * data source and licence
  * a link to Wikipedia
* Acceptance criteria:
  * The details for France include the area, population and capital.
  * A command opens the Wikipedia article in the default browser, which needs a connection.

### INF-2 Neighbours of an area
* Outcome: A user can list the areas that border the current area. For each one they hear the length of the shared border, or, if it does not touch, the distance and bearing to the nearest point.
* Source: HLR
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * The neighbours of Switzerland are listed as 5 countries: France, Germany, Austria, Liechtenstein and Italy, each with its shared border length.

### INF-3 Distance and bearing between things
* Outcome: A user can get the distance and bearing from the location, or from the current feature, to any other feature. The measurement goes to the nearest point of that feature, or to its centre if the user prefers.
* Source: HLR
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * The distance from central London (51.507, -0.128) to central Paris (48.857, 2.352) is given as 344 km ± 1 km, bearing 148° ± 1°. Distances are measured along the Earth's surface (geodesic).
  * When the location is inside an area, "distance to its border" gives the nearest point on that area's own boundary.

### INF-4 What is inside, and what is this inside
* Outcome: A user can find out what a feature contains, grouped by type with counts, and then list the features of each type. They can also find out which areas contain a feature.
* Source: HLR, UXReview, DP70
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * "Contains" for Wales, zoomed to fit Wales, gives counts by type, such as "National parks 3, Principal areas 22, …", and each type opens as a list.
  * Only features that are visible (NAV-13) are listed and counted. Only types with at least one visible feature are listed.
  * Points, lines and areas are all included, for example railway stations and rivers.
  * A feature partly inside counts as inside, and is not marked as partly inside. The New Forest National Park is listed under Hampshire.
  * Each list can be sorted by name, distance or bearing (INF-10). Typing the start of a name jumps to it.
  * With the zoom at 5 km, the railway stations listed for the United Kingdom are only those within 5 km of the location.

### INF-5 Overlapping areas
* Outcome: A user can find areas that overlap the current area, and how much of it each one covers.
* Source: HLR
* Priority: Must. Status: Agreed.
* Acceptance criteria: The New Forest National Park is reported as overlapping Hampshire and Wiltshire, with a percentage for each.

### INF-6 Line features in relation to areas
* Outcome: For a line feature, the user can hear its length, start and end, the areas it passes through in order, and what it crosses. For an area, they can list the line features crossing it or forming part of its border.
* Source: HLR
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * The River Rhine lists the countries it passes through, in order from its source.
  * Each country in that list offers the usual actions (INF-10).

### INF-7 What is nearby
* Outcome: A user can list the nearest features of the active layers around the location, each with its distance and bearing, sorted nearest first or by relative bearing clockwise from ahead.
* Source: HLR
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * The 20 nearest bus stops are returned within 1 second (proposed), sorted by distance.
  * Switching to bearing order lists the same items clockwise from ahead, relative to the current orientation.
  * Only visible features are listed (NAV-13), so the search covers the view radius. If nothing is visible, the user is told "Nothing nearby in view", and a command widens the search beyond the view.

### INF-8 Far-away features
* Outcome: A user can relate the location or current feature to a feature that is not nearby, found by search or bookmark.
* Source: HLR
* Priority: Must. Status: Agreed.
* Acceptance criteria: Choosing "distance to…" and searching for "Tokyo" gives the distance and bearing from the location, without moving.

### INF-9 Friendly structured queries
* Outcome: A user can ask compound questions through a guided form, without needing to know how the data is stored. For example: "rivers that flow through Germany", or "schools within 1 km of here".
* Source: DP15
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * The form has three parts: what (a layer), relation (within, crossing, bordering, near) and reference (the current feature, a searched feature or a bookmark).
  * The answer goes into the Search group of the Information panel.
  * No database field names appear anywhere in the interface.

### INF-10 The Information panel
* Outcome: Information about where the user is lives in one panel, grouped by relationship. Every item in it can be acted on in the same way.
* Source: UXReview, DP64, DP70
* Priority: Must. Status: Agreed. The PO expects to change this area after testing, so it should be easy to change.
* The groups are:
  * Within (LOC-3)
  * Contains (INF-4)
  * Bordering (INF-2)
  * Overlapping (INF-5)
  * Crossing (INF-6)
  * Nearby (INF-7)
  * Crossed and passed (ANN-2)
  * Search (SRB-1, INF-9)
* The actions on every item are:
  * jump
  * details
  * its own groups, such as its Bordering or Contains, without moving
  * play its direction as sound
  * measure from the location
  * bookmark
* Acceptance criteria:
  * The panel is an accessible tree view, with level and position announced.
  * F3 goes to the panel from any region, back to the item last focused there, or to the first item of Within the first time (DP106).
  * Groups are filled when opened, so movement is never slowed by them (NFR-1).
  * The selected item is highlighted on the visual map.
  * Every list can be sorted by name, by distance, or by bearing clockwise from ahead. One key cycles the sort order and announces it. Within also offers its natural order, smallest to largest, which is its default. Nearby defaults to distance, Bordering to bearing, and the others to name.
  * Contains, Nearby, and Crossed and passed show only visible features (ANN-7). Within follows the layers' zoom ranges, as the place does (DP160). Bordering, Overlapping, Crossing and Search are not limited by zoom (DP80).
  * The groups, their order and their sorting are set in one place in the code, so they can be changed easily after testing.

### INF-11 Grid values
* Outcome: A user can get the value of a grid layer at the location, such as elevation, depth, rainfall or temperature, with units.
* Source: HLR, DP31
* Priority: Should. Status: Agreed.
* Acceptance criteria: At the summit of Ben Nevis, the elevation is given within the accuracy of the dataset (proposed within 50 m).

### INF-12 Distance along a line or route
* Outcome: A user can measure the distance along a single, unambiguous line between two points, and along a chain of their own pins. This uses no shortest-path routing.
* Source: DP16, DP17
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * Marking two points on the same road and asking "distance along road" gives the length along that road.
  * If the two points are not on one continuous line, the user is told so.

---

## 8. Search and browse

### SRB-1 Search by name
* Outcome: A user can find features by name, even with misspellings, missing accents or other-language names, and can tell apart places that share a name.
* Source: HLR
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * Searching "Sao Paulo" finds São Paulo, and pressing Enter jumps there.
  * "Paris" lists "Paris, Île-de-France, France" before "Paris, Texas, United States".
  * Results appear within 1 second (proposed).

### SRB-2 Narrow the search
* Outcome: A user can limit a search to the current area, near the location, or one layer.
* Source: Proposed
* Priority: Must. Status: Proposed.
* Acceptance criteria: "High Street", limited to Southampton, returns only matches inside Southampton.

### SRB-3 Browse the hierarchy
* Outcome: A user can browse the world as an expandable tree (world, continent, country and so on) and jump to any item.
* Source: HLR, DP11
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * The tree is an accessible tree view. Its level and position are announced by the screen reader, for example "level 3, 5 of 44".

### SRB-4 Browse by category
* Outcome: A user can list every feature of a category within an area, such as "national parks in the United Kingdom" or "lakes in Finland".
* Source: HLR
* Priority: Must. Status: Agreed.
* Acceptance criteria: The answer appears in the Search group of the Information panel (INF-10).

---

## 9. Sonification

### SON-1 Hearing direction and distance
* Outcome: A user can hear where a feature is in relation to them through spatial sound. Direction is heard as the sound's position. Distance is heard through loudness and a second cue, scaled as in SON-9.
* Source: HLR, DP18, DP47
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * Spatial sound (HRTF) on headphones is the default. A "speakers" option uses stereo panning plus pitch instead.
  * In blind listening tests, users identify the direction of a sound to within 45° in at least 80% of trials (proposed).
  * This is checked first in a standalone listening test in Phase 1, with the PO as the tester, before the rest of the sound design is built on it. The test records the direction played and the direction heard, so the results can be analysed.

### SON-2 Sound orientation follows the orientation mode
* Outcome: What counts as "ahead" in the sound matches the orientation the user has chosen (NAV-12).
* Source: DP19, DP41
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * In north-fixed, north is straight ahead, whatever the movement mode.
  * In cardinal facing and free facing, the direction the user faces is ahead. When following a road or line in free facing, that is the direction of travel.
  * A sound at a bearing of 90° is heard to the right in north-fixed. While facing 90° in either facing orientation, it is heard straight ahead.

### SON-3 Spoken labels from the same direction
* Outcome: When a sound plays from a direction, its spoken label, such as "Berlin", comes from the same direction.
* Source: DP39, DP46
* Priority: Should. Status: Agreed. The defaults below are the architect's decision under DP46 and remain open to change.
* Acceptance criteria:
  * The label is spoken by a voice built into the application, rendered into the spatial audio. The screen reader's voice cannot be positioned in space.
  * By default, the screen reader does not speak the label as well, so the user does not hear it twice. Shift+Space repeats the label (ANN-4). Where the screen reader allows Braille-only output, as NVDA does on the desktop, the label is also sent to the Braille display.
  * A setting, "also speak spatial labels through the screen reader", is off by default.
  * The built-in voice's speed and volume can be set separately from the screen reader's.

### SON-4 Look around
* Outcome: A user can "look around": hear the Nearby list (INF-7) played as sound, one feature after another, each from its own direction. Nearby is the features as text. Look around is the same features heard in space.
* Source: HLR, PO agreement on 30 October 2026
* Priority: Should. Status: Agreed.
* Acceptance criteria:
  * The scan plays the Nearby list in bearing order, clockwise from ahead, and plays at most 12 items (proposed).
  * Every feature played is in the Nearby list, and the first 12 of Nearby in bearing order are the ones played.
  * Only visible features are played (NAV-13), each with its layer's sound (SCP-7).
  * The scan can be interrupted, and each item can be acted on as it plays (INF-10).

### SON-5 Grid values as pitch
* Outcome: While moving, a user hears the value of a grid layer as pitch. They can also ask for a sweep that plays values one after another along a line.
* Source: DP20
* Priority: Should. Status: Agreed.
* Acceptance criteria:
  * Higher values give a higher pitch, with the scale set to the layer's range.
  * A sweep can go left to right, top to bottom, or along the heading, across the visible map, over a chosen distance, or between two points.
  * Left, right, top and bottom follow the orientation (NAV-12). In north-fixed, left to right means west to east. In a facing orientation, it runs from the user's left to their right.

### SON-6 Earcons
* Outcome: Short distinctive sounds tell the user about events without speech.
* Source: Proposed, DP58, UXReview
* Priority: Should. Status: Agreed.
* Events with an earcon:
  * step with nothing changed (the soft tick)
  * something added to the crossed and passed list (on by default)
  * passing a point of interest while driving (the ding, NAV-14)
  * blocked, for example at a pole, or turning in north-fixed
  * no data, for example no lines of the chosen network type nearby
  * ambiguous "up" in hierarchy mode (the beep in NAV-4)
  * crossing a line of a line layer, where the layer has a crossing earcon (SCP-7). For example, the graticule layer (DAT-13) has crossing earcons for lines of latitude and longitude at a set interval, and one each for the equator, the prime meridian, the antimeridian, the tropics and the polar circles. They are off by default.
* Crossing earcons belong to the layer definition (SCP-7), so any line layer can have one, such as "play a sound when I cross a railway".
* There are no earcons for crossing a border or moving between land and water by default, because the new name makes these clear.
* Acceptance criteria: Each earcon can be switched off individually and has its own volume, separate from speech (DP163).

### SON-7 Sound must not get in the way of speech
* Outcome: Sound never delays or blocks screen reader speech.
* Source: Proposed
* Priority: Must. Status: Proposed.
* Acceptance criteria:
  * Earcons and spatial sounds play at the same time as speech.
  * A master mute key silences all application sound immediately.

### SON-8 Earcons are replaceable sound files
* Outcome: Every earcon is a sound file that can be replaced. The PO supplies all the earcon sounds (DP61). Until each one arrives, a simple placeholder tone generated by the project is used.
* Source: DP42, DP43
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * Earcons are stored as WAV files in a sound folder, with one file for each event, and the file names are listed in Help.
  * A user can point any earcon at their own WAV file in settings. If the file cannot be played, the default sound is used and the user is told.
  * Every bundled sound has its source and licence recorded, as for data (DAT-9).

### SON-9 Distance is scaled to the zoom
* Outcome: How loud a sound is depends on its distance compared with the current zoom, so the distance cue works equally well for a street and for a continent. Whatever is in view is within hearing range. The step size has no effect on it.
* Source: UXReview, DP65, DP67
* Priority: Must. Status: Agreed. The loudness falls in a straight line to the edge of the view, and never below a minimum volume, which is also the level beyond the view. The other model, equally quieter for each doubling, is kept as a setting (DP137).
* Acceptance criteria:
  * The hearing range is the zoom's view radius (NAV-13).
  * Within the range, loudness falls with the logarithm of distance: from full loudness at one twentieth of the range or closer, each doubling of distance is about equally quieter, down to quiet at the edge of the range (proposed).
  * Beyond the range, sounds play at the quietest level with the second distance cue at full strength. This applies to items in Within, Bordering, Overlapping, Crossing and Search that are out of view, such as a bordering country while zoomed in to a street. Their direction is always true, the sound says "beyond the view", and the spoken label gives the real distance (proposed, DP80, to be tried in the Phase 1 listening test).
  * A feature halfway to the edge of the view sounds the same at every zoom. At a 1 km zoom, a feature 500 m away sounds the same as a feature 500 km away does at a 1000 km zoom.
  * Resizing the window does not change what is heard (DP76).

### SON-10 Orientation beacon
* Outcome: A user can switch on a soft repeating sound that always comes from the North Pole, so they can feel which way they face. While driving along a curving line, the beacon's movement conveys the shape of the line.
* Source: UXReview, DP72
* Priority: Should. Status: Agreed.
* Acceptance criteria:
  * One key switches the beacon on and off.
  * Facing east, the beacon is heard to the left. Facing south, it is heard behind.
  * Within 100 km of the place it comes from the beacon fades out, and the user is told why.
  * Until pins come, it can come from the North Pole, the South Pole, or the equator at 0 degrees east, 90 degrees east, 180 degrees or 90 degrees west (P2-T18g).
  * The beacon can point at any pin instead, such as "home". The North Pole is the default. The target is chosen in settings or from a pin's actions.
  * Proposed: when the beacon points at a pin, it fades out within one step of the pin and says "Arrived at home".

---

## 10. Tactile exploration (touch)

### TCH-1 Trace a shape
* Outcome: A blind user can explore the shape of an area by touch. The area is shown on its own, filling the touch screen. A sound tells the user whether their finger is inside the area, outside it, or on its edge.
* Source: HLR, DP21
* Priority: Should (built early rather than left to last). Status: Agreed.
* Acceptance criteria:
  * The inside of the area gives a high tone, the outside a low tone, and the edge a distinct click.
  * Feedback reaches the ears within 50 ms of the finger moving (proposed).
  * On starting, the user hears the scale and orientation, for example: "France, north at top, screen width about 1000 km".

### TCH-2 Trace a line
* Outcome: A blind user can trace a line feature by touch, hearing a tone while their finger is on the line.
* Source: HLR, DP21
* Priority: Should. Status: Agreed.
* Acceptance criteria: The tone sounds while the finger is within a tolerance of the line, adjustable with a default of 3 mm (proposed). The tone changes when the finger passes a named point on the line.

### TCH-3 Room to add more touch tools
* Outcome: New touch exploration modes can be added one at a time without reworking the application.
* Source: DP21
* Priority: Should. Status: Agreed.
* Acceptance criteria: A second mode, such as relief as pitch (grid values under the finger), is added using the same framework.

### TCH-4 Working alongside the screen reader
* Outcome: The user can switch between the screen reader's own touch handling and the application's touch exploration, and is told how.
* Source: Proposed
* Priority: Should. Status: Proposed.
* Acceptance criteria: Entering touch exploration tells the user how to pass touch through to the application. On Windows with NVDA this means turning off NVDA touch interaction with NVDA+Alt+T.

---

## 11. Visual map

### VIS-1 A standard graphical map
* Outcome: A sighted user sees a familiar map of the same data. The map is always centred on the shared location, with a heading arrow at the centre and the current feature outlined. There is no separate cursor marker.
* Source: HLR, DP23
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * Every non-visual move updates the visual map within 100 ms (proposed).
  * After every move, the location is at the centre of the map.
  * A small plus-shaped cross marks the exact centre, so a sighted helper can see the precise point. It is on by default and can be switched off (DP73).
  * The current area is outlined as the setting "Outline the current area" chooses: always (at first), not for the oceans, never for oceans and seas, or never. An ocean's outline can run across open water, such as the North Atlantic's edge from Norway to Iceland (PO, 10 November 2026, P2-T17v).
  * The special lines (the equator, the prime meridian, the tropics, the polar circles and the date line) are drawn thicker than the other lines and in a colour of their own, in every theme (P2-T17v, DAT-13).

### VIS-2 Themes and isolation
* Outcome: A partially sighted user can choose a high contrast or colour-blind safe theme, show or hide layers, and isolate a single feature.
* Source: DP22
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * The themes provided are standard, high contrast dark, high contrast light, and colour-blind safe.
  * Every text and outline colour in the high contrast themes has a contrast ratio of at least 7:1.
  * "Isolate" shows only the current feature and its outline.
  * A map display setting chooses the fill (different colours for neighbours, the default; one colour for all; or none, for outlines only), whether borders are drawn, and the colours of the fill, the borders and the current outline. The current feature's outline is always shown (DP108).

### VIS-3 Zoom and labels
* Outcome: A partially sighted user can enlarge the map and labels using the zoom (NAV-13), the label size setting, or their own magnifier software.
* Source: DP22
* Priority: Must. Status: Agreed.
* Acceptance criteria: Labels scale with zoom, and the label size setting allows at least 200%.

### VIS-4 Standard pointer controls
* Outcome: A sighted user can pan and zoom with the mouse, trackpad or touch, as in any map application.
* Source: Proposed
* Priority: Must. Status: Proposed.
* Acceptance criteria: Clicking moves the location, and the scroll wheel and pinch change the zoom (NAV-13). Dragging turns the globe and moves the location with it.

### VIS-5 Globe projection
* Outcome: The visual map looks like the Earth viewed from space (an orthographic projection), centred on the current location. Nowhere is stretched, and crossing a pole looks natural. At street scale it looks like an ordinary flat map. Non-visual features never depend on a projection, because all distances and bearings are calculated on the Earth's surface.
* Source: UXReview, DP73
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * At a 10,000 km zoom, the map shows the globe as a ball centred on the location.
  * Stepping over the North Pole in free facing keeps the map smooth, with no jump or tear.
  * An option rotates the map so that the heading is at the top in the facing orientations. North-up is the default.
  * Touch tracing (TCH-1) uses the same projection, centred on the traced feature.

---

## 12. Personal content

### USR-1 Pins
* Outcome: A user can drop named pins at locations and add notes to them.
* Source: DP16
* Priority: Must. Status: Agreed.
* Acceptance criteria: Pins persist between sessions and appear on the visual map.

### USR-2 Feature bookmarks
* Outcome: A user can bookmark any feature, such as a country, river or bus stop, not just a location.
* Source: DP16
* Priority: Must. Status: Agreed.
* Acceptance criteria: A bookmarked feature can be jumped to and its details shown even after the data packs are updated, matched by its stable identifier.

### USR-3 Collections
* Outcome: A user can group pins and bookmarks into named, ordered collections, such as "countries I have visited" or "walk to the station".
* Source: DP16
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * Collections can be created, renamed, reordered and deleted.
  * Each collection can be browsed as a group in the Information panel.

### USR-4 Measure a chain of pins
* Outcome: A user can get the distance between the first and last pin of a collection, and the total length of the path through all of them in order.
* Source: DP16
* Priority: Must. Status: Agreed.
* Acceptance criteria: For three pins A, B and C, both the A to C straight-line distance and the A to B to C total are reported.

### USR-5 Share by file
* Outcome: A user can export collections to a file and import a file from someone else.
* Source: DP16
* Priority: Should. Status: Agreed.
* Acceptance criteria: The export is a standard GeoJSON file that opens in QGIS. Importing it back produces the same collection.

### USR-6 Tours
* Outcome: A user can play a collection as a tour. The application drives (NAV-14) from one item to the next, pausing at each to announce it.
* Source: UXReview
* Priority: Later. Status: Proposed.
* Acceptance criteria: Playing a collection of three pins drives to each in order and announces each one on arrival.

---

## 13. Data content

### DAT-1 Worldwide base coverage
* Outcome: Every user, with only the base pack installed, can explore the whole world at country scale.
* Source: DP24
* Priority: Must. Status: Agreed.
* The base pack covers:
  * oceans and seas
  * continents
  * countries and first-level subdivisions
  * major physical features
  * major rivers and lakes
  * major roads and railways
  * cities and towns
* Acceptance criteria: The coverage test, a fixed list of sample places worldwide, all resolve to the expected names with only the base pack installed.

### DAT-2 Regional detail
* Outcome: With a regional pack installed, a user can explore at street level.
* Source: HLR, DP24
* Priority: Must. Status: Agreed.
* A regional pack covers:
  * all administrative levels
  * all roads and paths
  * land use
  * parks and public spaces
  * school grounds
  * points of interest such as bus stops, crossings, bins and amenities
* Acceptance criteria: The street-level acceptance scripts pass for the UK test region and for a second, contrasting test region (see DAT-10).

### DAT-3 Accurate coastlines
* Outcome: Country and other land areas follow the real coastline, so a user standing offshore is told they are at sea, not in the country. Territorial waters and economic zones are an optional extra layer.
* Source: data sources.md, DP29
* Priority: Must for the coastline. Could for the maritime layer. Status: Agreed.
* Acceptance criteria:
  * A point 2 km off the coast of Brittany is announced as sea (the Bay of Biscay or the Celtic Sea), not as France.
  * With the maritime layer switched on, it is also described as "within French territorial waters".
  * Points on islands are in the right country and division, for example Skye (Highland, Scotland), the Isle of Wight, Mallorca and Tenerife.
  * A point in Gibraltar is in Gibraltar, not Spain. Points in Ceuta and Melilla are in Spain.
  * An island shared between countries, such as Ireland or Usedom, is split between them by a land border, and each part is in the right country.
  * France and the United Kingdom are not listed as bordering each other, because they share no land border. They are listed as nearly touching (INF-2).
  * Neighbouring areas meet exactly at every zoom, with no visible gaps or overlaps between them.

### DAT-4 Named seas and marine features
* Outcome: Oceans, seas, bays, straits, gulfs and channels are named and can be navigated like land areas. They form a hierarchy: oceans contain seas, seas can contain other seas, and seas contain smaller marine features.
* Source: HLR, data sources.md, UXReview
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * The neighbours of the North Sea include the Skagerrak, the Norwegian Sea, and the English Channel or the Strait of Dover, depending on how the source divides them.
  * Hierarchy "up" from the Bay of Biscay goes to the North Atlantic Ocean, then the Atlantic Ocean.
  * Marine features that exist in the source only as a point, with no area, are still findable by search and Nearby.

### DAT-5 Physical regions
* Outcome: Mountain ranges, deserts, plateaus and other physical regions are present as areas, along with peaks as points.
* Source: HLR
* Priority: Must. Status: Agreed.
* Acceptance criteria: The Alps are announced when the location is in the Alps, and the containment list includes them.

### DAT-6 Grid layers
* Outcome: At least elevation and depth are available worldwide, then precipitation and temperature.
* Source: DP31
* Priority: Should. Status: Agreed.
* Acceptance criteria: Each grid layer records its source, resolution, units and date.

### DAT-7 Feature facts
* Outcome: Features carry useful facts where available: population, area, elevation, and Wikipedia and Wikidata links.
* Source: DP31, DP51
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * At least 95% of countries and 80% of cities over 100,000 people have a population figure and a Wikipedia link (proposed).
  * Each fact states its source and date, for example "Population 67 million (Wikidata, 2024)". Wikidata and Wikipedia are acceptable sources.

### DAT-8 Disputed territory follows the source
* Outcome: Disputed borders follow the policy of the data source used, and the user can find out which source and policy applies.
* Source: DP28
* Priority: Must. Status: Agreed.
* Acceptance criteria: The details of a disputed area name the source and flag it as disputed.

### DAT-9 Attribution
* Outcome: Every data source is credited as its licence requires, both in the application and in the downloaded packs.
* Source: HLR, DP30
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * "About data" lists every source, its licence and its date.
  * Feature details name their source.
  * Each pack contains an attribution file.

### DAT-10 Generic worldwide behaviour
* Outcome: Nothing in the application or the data pipeline assumes the UK. Any region can be built and tested.
* Source: DP25
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * The regression suite runs on the UK plus at least two contrasting regions (proposed: Japan and Kenya).
  * Japan tests non-Latin names and different administrative levels. Kenya tests sparser mapping and a different road classification.

### DAT-11 Freshness for each dataset
* Outcome: Each dataset is refreshed on its own schedule, and the user can see how old the data is.
* Source: DP26
* Priority: Should. Status: Agreed.
* Acceptance criteria:
  * The pipeline configuration holds a refresh interval for each source.
  * Pack details show the date of each source's data.

### DAT-12 Continents
* Outcome: Continents exist as areas, so the hierarchy has a top level below the World. They are built by grouping countries, and countries that span two continents are split along conventional lines.
* Source: DP55
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * Russia west of the Urals is in Europe, and Russia east of the Urals is in Asia. Turkey west of the Bosphorus is in Europe.
  * The dividing lines used are set in configuration and explained in Help.

### DAT-13 Graticule and special lines
* Outcome: Lines of latitude and longitude, and the special lines (the equator, the tropics, the polar circles, the prime meridian and the antimeridian), are available as a layer. They can be shown on the map, listed when crossed, followed in network mode, and given crossing earcons (SON-6). Like every layer, it is defined by configuration, including its sounds (SCP-7).
* Source: UXReview, DP74
* Priority: Should. Status: Agreed.
* Acceptance criteria:
  * The latitude and longitude interval can be set, for example every 1°, 5°, 10° or 15°.
  * Stepping across 0° longitude with the layer on lists "Prime meridian, crossed" and, if switched on, plays its earcon.
  * The international date line is offered as well as the 180° meridian, because the date line is not straight.

---

## 14. Data packs and delivery

### DAT-14 The antimeridian
* Outcome: Countries and other features that cross the 180 degree line, such as Fiji, Russia, the USA and Kiribati, behave like any other feature.
* Source: architecture thoughts.txt
* Priority: Must. Status: Proposed.
* Acceptance criteria:
  * Fiji, Russia, the USA and Kiribati draw correctly on the globe, with no line or gap at 180 degrees.
  * Their areas are within 1% of the Wikidata figures.
  * Isolating Fiji (VIS-2) shows one compact group of islands, not two halves at opposite edges.
  * Jumping to Fiji arrives in Fiji, not at 0 degrees longitude.
  * No border, coastline or crossing is announced along the 180 degree line itself, unless the user has the antimeridian graticule line switched on (DAT-13).

### PCK-1 Pack sizes
* Outcome: A user can get started with a modest download, and add detail without very large downloads.
* Source: HLR, DP24, DP50, DP175
* Priority: Must. Status: Agreed (the cutting of regions and the separate grid packs are Proposed, see DP59).
* Acceptance criteria:
  * The base pack is about 400 MB or less. This is a soft limit. It was 250 MB until DP175, when the size trial showed counties for the whole world add about 170 MB, and the PO judged them worth the larger first download. If the base pack turns out too coarse or too thin at this size, the limit is reviewed with the PO.
  * Regional packs aim to be 1 GB or less each. This is also a soft limit.
  * Proposed: regional packs follow Geofabrik's extract boundaries, which are countries split into sub-regions for large countries. A region that would exceed 1 GB is split further.
  * Proposed: the detailed grid layers, such as climate and higher-resolution elevation, are separate optional grid packs. The base pack carries only coarse elevation and depth.

### PCK-2 Pre-built regional packs
* Outcome: A user can see the available packs with their sizes and dates, and can install, update or remove them.
* Source: DP24, DP34
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * The pack manager is an accessible list showing name, size, date and installed status.
  * Updates are offered when a newer pack is published.
  * A download can be cancelled and resumed.

### PCK-3 Data on demand when online
* Outcome: A user who is online can explore an area without installing its pack first.
* Source: DP4
* Priority: Should. Status: Agreed.
* Acceptance criteria: Moving into an area that is not installed, while online, gives a detailed announcement within 3 seconds on a typical home broadband connection (proposed).

### PCK-4 Zero-cost hosting on GitHub, with a copy for the web
* Outcome: Packs are hosted and downloaded at no cost to the project, using GitHub Releases on the project repository. Browsers cannot read GitHub Releases, so the web version uses a copy of each pack on a TobyMap dataset on Hugging Face (spike S3, DP102). Other hosting is considered only if user demand needs it.
* Source: DP27, DP48, DP83, DP102
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * Every published file is under GitHub's 2 GiB limit per file.
  * The hosting has no recurring charges.
  * The pipeline publishes each pack to both places, and the two copies are identical.
  * GitHub release downloads serve ranges of a file, for the desktop's on-demand data (PCK-3). Confirmed by spike S3.
  * The web version downloads each pack whole into the browser's private storage and reads it from there. While a pack is downloading, it reads records with range requests from Hugging Face.

### PCK-5 Trustworthy packs
* Outcome: A user never ends up with a corrupt or mismatched pack.
* Source: Proposed
* Priority: Must. Status: Proposed.
* Acceptance criteria:
  * Every pack has a checksum, which is verified after download.
  * Each pack declares the range of application versions it works with, and the application refuses an incompatible pack with a clear message.

---

## 15. Data manager tool

### DMT-1 Repeatable, configuration-driven pipeline
* Outcome: A data manager can rebuild any pack from its sources with a single command. Configuration files say which sources, regions and layers to use.
* Source: DP32
* Priority: Must. Status: Agreed.
* Acceptance criteria: Building the same configuration twice from the same source files gives the same data.

### DMT-2 Screen reader friendly command line
* Outcome: A blind, technical data manager can run, follow and diagnose the pipeline with a screen reader.
* Source: DP32, DP33
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * There are no animated progress bars. Progress is reported in plain lines at milestones, no more than one line every 10 seconds.
  * A summary is printed at the end, and full logs go to a text file.
  * Errors name the source, the feature and the next action to take.

### DMT-3 Quality reports
* Outcome: A data manager can judge the quality of a build without looking at a map.
* Source: Proposed
* Priority: Must. Status: Proposed.
* Acceptance criteria: Every build writes text and CSV reports covering:
  * invalid geometries that were repaired
  * features without names
  * gaps in coverage
  * size by layer
  * differences from the previous release

### DMT-4 Corrections by rule
* Outcome: A data manager can fix data problems without editing geometry. Rules in configuration can rename features, exclude them, reclassify them or set their parent.
* Source: DP32
* Priority: Should. Status: Proposed.
* Acceptance criteria: A rule that renames a feature appears in the next build and is listed in the quality report.

### DMT-5 Publish
* Outcome: A data manager can publish packs and their manifest to the hosting location with a single command.
* Source: Proposed
* Priority: Must. Status: Proposed.
* Acceptance criteria: After publishing, the application's pack manager lists the new versions.

### DMT-6 Licences carried through
* Outcome: Licence and attribution details are carried automatically from each source into every pack.
* Source: DP30
* Priority: Must. Status: Proposed.
* Acceptance criteria: A build fails if any source in the configuration has no licence recorded.

### DMT-7 Runs on the PO's laptop
* Outcome: The pipeline runs on the PO's Windows 11 laptop (32 GB of memory, Intel Core i7-1185G7 with 4 cores and 8 threads). Large source files and working files go on the external SSD, drive E:, so the nearly full C: drive is used only for small builds. Existing data on E:, such as the OSM planet file, is reused where it is recent enough.
* Source: DP53, DP60, DP75
* Priority: Must. Status: Agreed.
* The existing files in E:\osmdata are kept for now. If space on E: becomes a problem, the PO is asked again before anything is deleted (DP75).
* The pipeline may use GeoDesk and the GOL files on E: where they are faster than working from the .osm.pbf files, subject to a licence check in the pipeline spike (DP75).
* Acceptance criteria:
  * The folders for source data, working files and output are set in configuration, and none of them defaults to C: for large data.
  * No drive letter is assumed anywhere. Another data manager can keep the data on any drive or folder by setting one data folder, on the command line, in an environment variable or in a local settings file.
  * The pipeline never deletes or overwrites a file it did not create.
  * Before a build starts, the pipeline estimates the disk space it needs. If there is not enough free space, it stops with a clear message.
  * If drive E: is not connected, the pipeline says so and stops before doing any work.
  * Country-sized builds complete within 32 GB of memory. Whole-planet steps are limited to filtering and extracting, which work from disk.
  * Free GitHub build servers run only the tests and small sample builds.

---

## 16. Non-functional requirements

### NFR-1 Responsiveness
* Outcome: Movement feels immediate.
* Priority: Must. Status: Proposed.
* Acceptance criteria:
  * On a mid-range laptop (proposed reference: 4 cores, 8 GB of RAM, SSD), the announcement after a step is handed to the screen reader within 150 ms of the key press, for 95% of steps, with the data installed locally.
  * Earcons start within 50 ms.

### NFR-2 Start-up
* Outcome: The application is ready to use quickly.
* Priority: Should. Status: Proposed.
* Acceptance criteria: The first announcement comes within 10 seconds of launch with the base pack installed.

### NFR-3 Resource use
* Outcome: The application runs comfortably alongside a screen reader on an ordinary computer.
* Priority: Should. Status: Proposed.
* Acceptance criteria: Memory use stays under 2 GB in normal use with the base pack plus one country pack installed.

### NFR-4 Robustness
* Outcome: Bad or missing data never crashes the application.
* Priority: Must. Status: Proposed.
* Acceptance criteria: A corrupted pack is detected and reported, and the application keeps running with the remaining packs.

### NFR-5 Automated testing
* Outcome: Changes made by Claude Code are checked automatically before the PO tests them.
* Source: DP35, DP38
* Priority: Must. Status: Agreed.
* Acceptance criteria:
  * Continuous integration on GitHub runs unit, geometry and announcement-text tests on Windows and macOS for every change.
  * The web version's tests run in a headless browser in continuous integration for every change (DP49).
  * The announcement text for the acceptance scripts is compared against approved baselines.

---

## 17. Delivery

### DEL-1 GitHub repository with continuous integration
* Source: DP38. Priority: Must. Status: Agreed.

### DEL-2 Phased delivery with PO acceptance gates
* Outcome: Each phase ends with PO testing against this catalogue before the next phase starts. There is no human developer.
* Source: DP35, DP37
* Priority: Must. Status: Agreed.

### DEL-3 Python preferred unless another language clearly earns its place
* Source: DP36. Priority: Should. Status: Agreed.

### DEL-4 User testing panel
* Outcome: The PO tests every phase on Windows 11 with NVDA. This is the only test environment that can be relied on. Willing blind and sighted friends try out phases when they can. JAWS and VoiceOver testers are sought once early versions are available.
* Source: DP6, DP47, DP49, DP54
* Priority: Should. Status: Agreed.
* Acceptance criteria:
  * Feedback is recorded against requirement IDs.
  * Release notes state which screen readers and platforms a release has actually been tested with.

### DEL-5 Windows installer
* Outcome: A Windows user installs the application with a standard installer, and can uninstall it cleanly. A portable zip is also offered. RecallScore's installer is the model.
* Source: architecture thoughts.txt
* Priority: Must. Status: Proposed.
* Acceptance criteria:
  * Every release from the first one includes a Windows installer, and the screen reader can complete every installer page.
  * The installer lets the user choose where to install. The pack folder can be chosen separately in the pack manager (PCK-2).
  * Uninstalling removes the application, but asks before removing installed packs and personal data.
