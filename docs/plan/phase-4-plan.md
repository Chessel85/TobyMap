# Phase 4 detailed plan: street detail

Version 0.1, 20 November 2026. Written by Claude Code for the product owner (PO).

This plan turns section 7 of "implementation plan.md" (version 0.9) into the work for each task, P4-T1 to P4-T15. It adds the work carried over from Phase 3, and a new task, P4-T14, made from your notes on the Phase 3 tidy-up 2 desktop checklist (docs/checklists/phase-3-tidy-up-2-desktop results.txt, 20 November 2026). It follows the architecture (version 0.11), the requirements catalogue (version 0.19), the user experience description (version 0.23), and your answers up to DP217. The tick list of what is done is docs/plan/phase-4.md.

## How to read this plan

* "The goal" and "Proposals and questions" are the parts most worth your attention. The questions are discussion points DP218 to DP223, added to the discussion points file with this plan.
* "Which model does each work item" says how the Opus and Sonnet labels are chosen, as in Phases 2 and 3.
* "Order of work" says what is done when, and "Heavy runs" lists every time the laptop will be busy for a long while.
* Each task has its own level 2 heading, with the same parts in the same order: requirements, what it needs first, its work items, the tests, and when it is done.
* Each work item, such as P4-T1a, is small enough for one session, and has its own model label.
* The last sections cover the exit checks, your acceptance checklist, closing the phase, risks, and what is left for later phases.

Words follow the glossary. This plan adds five words to it: regional pack, Great Britain pack, pack manager, catalogue and correction rule.

## The goal

Street-level exploration of Great Britain, with packs that join without a seam, a complete pack manager, and bookmarks of your own:

1. With the Great Britain pack installed, you can step along the streets of a town you know and hear each street, park, school ground and bus stop, and every administrative level down to the parish or ward.
2. Moving from Great Britain out to sea, or across to France, nothing is said about missing detail: the world pack simply answers where the Great Britain pack does not reach (PLT-4).
3. The pack manager lists the packs, with their sizes and dates, and installs, updates and removes them, on the desktop and in the web version. A download can be cancelled and carried on later.
4. Ctrl+Enter makes a bookmark, a point with a name, in a bookmark list of your choice. Bookmarks are in the Information panel and on the map, and can be gone to, heard, measured, and saved to a file.
5. As data manager, you can run a build yourself, read its quality report, fix a name by a rule rather than by editing a shape, and publish a pack, all with a screen reader.
6. Your notes on the Phase 3 tidy-up 2 checklist are dealt with first, as P4-T14, so the application you use every day gets better while the long data work goes on.

What Phase 4 does not do: network mode, travelling along roads and driving (Phase 5), grids and touch (Phase 6), and other regions' packs and data on demand (Phase 7). One world rebuild is planned in this phase (P4-T15), not at its start: you decided on 20 November 2026 that Phase 3 closes without one.

## Which model does each work item

The same rules as Phases 2 and 3. Opus is chosen when a work item:

* needs a design decision the documents do not make, or must weigh several approaches
* is geometry where mistakes are subtle, such as containment, shared borders, coasts and matching features between packs
* runs in real time or across threads, such as downloads
* touches the screen reader interfaces, where what NVDA does must be found out, not assumed
* is a heavy pipeline run, or changes the pack format
* measures and improves speed, or publishes anything outside this laptop

Sonnet is chosen when a work item:

* follows a pattern that already exists in the code, such as a new command, template, setting, dialog or Information panel group
* has its behaviour fully written down here, with tests that say exactly what is right
* is documentation, a checklist, a CSV file or a list of keys
* is a second shell copying behaviour the first shell and the core already define

When a Sonnet work item hits something this plan did not foresee, it stops, writes a note in the task list, and the work item is handed to Opus.

In this plan, 76 work items are labelled: 39 Opus and 37 Sonnet. Phase 4 is mostly new data, a new kind of pack, and downloads, so Opus has the larger share again.

## Proposals and questions

Each question is a discussion point with a recommendation. Nothing that depends on an answer is started before you give it.

### DP218: publishing at the end of Phase 3 (DP110)

You asked me to ask again at the end of each phase. Phase 3 is closed without the browser and sighted checklists, and without a new world pack. Recommended: no release now, as the world pack of 20 November lacks the coast stretches and the search changes, and the pack manager that would install it comes in this phase. Ask again at the end of Phase 4, when the world pack is rebuilt and can be published with `mapdata publish`.

### DP219: bookmarks as you described them (DP209 to DP217)

Your answers change the requirements written in P3-T27 (USR-1 to USR-5). This is how I understand them, as one design, for you to confirm before P4-T8 starts:

1. A bookmark is always a point, with a name (DP210). On the map, Ctrl+Enter bookmarks where you are. On an item in the Information panel, it bookmarks the item's own point, the point Enter goes to. There are no feature bookmarks, so USR-2 ("feature bookmarks keep working") is withdrawn; the bookmark keeps the name of the current feature only as words, for you to read.
2. Ctrl+Enter opens the bookmark dialog (DP211): a Name box, filled in with the feature's name, numbered if that name is already used (Rome, Rome_1, Rome_2); the current feature and the coordinates, read-only; a Bookmark list box, set to the list used last; a New list button; and OK and Cancel. Two bookmarks may have the same name and the same place.
3. Bookmark lists hold bookmarks in an order you can change (DP212). One list, "Bookmarks", exists at first.
4. Bookmarks are a layer, and each bookmark list can be switched on and off on its own, with its own zoom range, as a list of countries visited and a list of cafes in London need very different ranges (DP213).
5. Your question in DP213: the bookmark's mark on the map. Recommended: always the same size on screen, about 12 pixels, with its name beside it, as a town's dot is now, so it never covers the map at a wide zoom or vanishes at a close one. Its size follows "Label size" in the Display tab, so no new setting is needed.
6. A bookmark can be made the current feature (DP211, point 7). Then Delete deletes it, after asking, Ctrl+Enter renames it, and Ctrl+X, Ctrl+C and Ctrl+V cut, copy and paste it between bookmark lists.
7. Two dialogs (DP213): the bookmark list dialog, for one list's bookmarks (move up and down, copy or move to another list, delete); and the bookmark manager, for the lists themselves (new, rename, move up and down, delete, on or off, zoom range, save to a file, open a file). Both have a Close button.
8. Measuring: "Measure from this", Ctrl+Shift+M, sets a measure start, as DP214. Measuring between two features is scrapped (DP215), and measuring a list as a chain is dropped, as bookmarks are only points (DP216). So USR-4 becomes "measure from a bookmark".
9. Files: TobyMap keeps all your bookmarks in one GeoJSON file of its own, in the settings folder on the desktop and in the browser's private storage on the web; Reset all settings does not touch it (DP209, DP217). You can save one bookmark list or all of them to a GeoJSON file, and open one. Your question in DP209, GPX: yes, GPX can be offered as well, as a second choice when saving and opening, since GPX waypoints are points with names, as bookmarks are. Recommended: GeoJSON and GPX both, GPX saving one waypoint per bookmark and opening waypoints into a new list.

### DP220: mountain ranges cut to the coast

Your note on 14.7: Exmoor overlaps the North Atlantic Ocean and the Bristol Channel. It is not a sliver: the mountain ranges come from GMBA, whose outlines are drawn coarsely and often run a few kilometres out to sea. Recommended: at the next world build (P4-T15), cut every mountain range to the land, as countries are cut to the coast. Then no range overlaps a sea, and "Oceans and seas" leaves Exmoor's Overlapping. A range on several islands keeps each island's part. This reruns the mountain ranges stage and the stages after it, not the planet file.

### DP221: the Sea of the Hebrides in Belfast Lough

From the overnight choices of 20 November, still open. Natural Earth names the IHO's "Inner Seas off the West Coast of Scotland", which take in the North Channel and Belfast Lough, "Sea of the Hebrides". So Space in Belfast Lough says Sea of the Hebrides. Recommended: rename that one marine area to "Inner Seas off the West Coast of Scotland" by a correction rule, P4-T4's first real use, at the world rebuild. The other choice was to say the bay or strait you are in first.

### DP222: speed in the browsers (P3-T20d)

Proposed on 17 November 2026 and still waiting: send a move's answer before the Information panel is refilled, in the web version as the drawing is now, and on the desktop off the window's thread; refill the panel and run Passed over's search in steps, so a key never waits more than one step; and read fewer pack tiles for Nearby. Recommended: yes, in Phase 4, after P4-T3, because a second pack makes every lookup a little heavier and this work is where that cost would show.

### DP223: what the Great Britain pack covers

The plan has always said "the Great Britain pack". Geofabrik's Great Britain extract is England, Scotland and Wales with their islands. Northern Ireland is in Geofabrik's Ireland extract, and the Isle of Man and the Channel Islands are separate. Recommended: Great Britain as Geofabrik draws it, aiming for 1 GB or less (PCK-1). Northern Ireland, the Isle of Man and the Channel Islands follow in Phase 7, when more regions are built, or sooner if you want. The pack is read from the same planet file as the world pack, not from Geofabrik's file, so the two packs' borders meet exactly (DP107, AD-16); Geofabrik gives only the outline.

### Not questions: settled by your earlier answers

* DP196: the NVDA language harness is P4-T10.
* DP197: the pack manager and the publish command are in this phase (P4-T6, P4-T11).
* DP198: territorial waters (P4-T12) and groups of islands (P4-T13) are in this phase.
* DP87: every island, named or not, comes with the regional packs.
* DP206 and your note on 2.2 (a sea and the ocean that holds it both in Nearby): parked, by your choice. Kept under "Left for later phases".
* Your note on 8.3: "along the path" is dropped as an order of Passed over (P4-T14h). Passed over opens "by distance", nearest first.
* Your note on set 12: the map views dialog gets a Save changes button (P4-T14g). To answer your question: yes, Add stores the layers as they are at that moment, and nothing after that changes the view. Save changes is how a view of your own is updated.

## Order of work

1. Start of the phase: P4-T0a to P4-T0f.
2. Your notes first: P4-T14, all in the core and the shells, so you can try them on the packs you have. One build of the Western Europe trial at the end of it, for the coast stretches (P4-T14i).
3. Carried from Phase 3: P3-T15 Help, and the two unreliable browser tests. P3-T20d after P4-T3, if DP222 says yes.
4. The data manager's tools, before the Great Britain build, so that build has them: P4-T5 (safety), P4-T4 (correction rules), P4-T11a (quality reports).
5. The regional pipeline, P4-T1, rehearsed on Hampshire and the Isle of Wight, then the Great Britain pack, P4-T2.
6. Combining packs, P4-T3.
7. Bookmarks, P4-T8 and P4-T9, which need only the core and can be done while the Great Britain build runs.
8. Territorial waters (P4-T12), groups of islands (P4-T13) and the mountain ranges cut to the coast (DP220), each rehearsed on the Western Europe trial.
9. The world rebuild, P4-T15, with everything since 20 November.
10. The pack manager, P4-T6, and publishing, P4-T11b, ending with the test release.
11. Robustness and memory, P4-T7, on the world and Great Britain packs together.
12. The NVDA language harness, P4-T10.
13. The checklists, the report, and closing the phase.

## Heavy runs

You are told before each starts, and each runs with the run switch (continue.txt) and a stall watch.

* The Western Europe trial, once at the end of P4-T14, for the coast stretches: about 7 minutes, as only the coast stretches, writing and checks stages rerun.
* The regional rehearsal on Hampshire and the Isle of Wight (P4-T1j): expected under an hour; it gives the figures to estimate the Great Britain build.
* The Great Britain build (P4-T2a): its time is estimated from the rehearsal, before it starts. It reads the planet file once, in its own process.
* Rehearsals of P4-T12, P4-T13 and DP220 on the Western Europe trial: under half an hour each.
* The world rebuild (P4-T15): overnight. It reruns from the mountain ranges, seas and countries stages onwards, not the planet file reading, if the fingerprints say so; checked before it starts.
* The memory measurement with both packs (P4-T7b): an hour, the laptop otherwise idle.

## Start of the phase

### P4-T0a Versions (Sonnet)

Check for newer PySide6 and Pyodide, and upgrade if every test passes. Note the result in the task list.

### P4-T0b The questions (Sonnet)

DP218 to DP223 added to the discussion points file with this plan.

### P4-T0c The implementation plan, version 0.9 (Sonnet)

Done with this plan: section 6 marks Phase 3 closed, section 7 has the start tasks, the carried work, P4-T14 and P4-T15, and P4-T8 and P4-T9 rewritten from your answers to DP209 to DP217.

### P4-T0d The requirements and documents for bookmarks (Sonnet)

After DP219: rewrite USR-1 to USR-5 in the requirements catalogue to match it, withdraw USR-2 if you agree, and update the glossary (bookmark, bookmark list, measure start; feature bookmark, position bookmark and chain removed), the user experience description (sections 6.3 and 9) and the architecture (6.7 and 6.11), which still speak of pins and collections.

### P4-T0e Samples for the test pack (Sonnet)

Street-level samples from the planet file, by the same tool as Phase 3's: the centre of Winchester (streets, footpaths, a park, a school ground, bus stops and crossings, its parishes or wards), part of the New Forest National Park, and the coast at Lymington with its small islands. Each the same byte for byte when made again.

### P4-T0f The key list (Sonnet)

New commands for Phase 4 added to docs/design/keymap.csv by tools/make_key_list.py, with clashes marked: the bookmark dialog (Ctrl+Enter), the Bookmarks group (Shift+8), the measure start (Ctrl+Shift+M), the bookmark manager, the pack manager (P), and cut, copy and paste of a bookmark. For your keys, as before. Mac keys are chosen by me from Apple's conventions.

## P4-T14 Your notes on the Phase 3 tidy-up 2 checklist

* Requirements: LOC-2, ANN-1, ANN-2, INF-1, INF-2, INF-4, INF-5, INF-10, NAV-4, NAV-8, SCP-6, VIS-2, ACC-7. From your results of 20 November 2026, on the Western Europe trial.
* Needs first: nothing, except P4-T14i, which needs the Western Europe trial built again.

Work items:

* P4-T14a Say only what changed when the zoom changes (Opus). Your notes on 1.9 and 1.10. Zooming out so that Hampshire is no longer said, you hear the first area still said, "Zoom 250 kilometres. England", not the whole list. Zooming in so that Hampshire is said again, you hear only "Zoom 100 kilometres. Hampshire". The rule: after a zoom, say the smallest area that was added; if none was added but some went, say the smallest that is left. Space still says the whole place. Approved wording changes in tests/mapcore/test_session.py.
* P4-T14b "Near" after Go to (Sonnet). Your notes on 1.1 and 1.2. Go to (Ctrl+G) says the place as Space does, "Near Winchester. Hampshire, England, ...". Also step 1.6, "Near Hythe": find why a step said a town though the rule is that only Space does, and either make the step follow the rule or, as you found it right, make the rule "Space, Go to, and a step into a new area" and correct the checklist step. Recommended: the second, as you found it helpful.
* P4-T14c How near counts as near, explained (Sonnet). Your note on 1.5. A new section of docs/design/explanation.md: "How TobyMap decides you are near a town". It is not the Nearby group, nor the passed nearby distance: each town has a reach from its population, from 2 to 30 kilometres, and the town nearest for its reach wins.
* P4-T14d The current feature, four faults (Opus). Your notes on 3.3, 6.3, 6.5, 7.4 and 14.1.
  * Space starts with the current feature when it is a line or place you are at, "River Itchen, here. Hampshire, England, ...", as Within lists it first.
  * Enter on a line in any group, such as the A27 in Contains, makes it the current feature, as Enter on an area does. Enter on a crossing point makes its line the current feature: Within then says "M3, here".
  * Shift+Enter on the smallest area here, the first time, says "No current layer. The current feature is the smallest area here, Hampshire.", not "Current layer: Counties".
  * When a zoom changes what Space says, the current feature follows it. At 2,500 kilometres after 25, Bordering is about the United Kingdom, not North Yorkshire.
* P4-T14e The focus after Enter (Sonnet). Your note on 3.3. After Enter on an item, the Information panel's focus goes to the heading of the group it was in, as the group is filled again for the new place and its items change. In every group, in both shells.
* P4-T14f Fewer messages that only confirm (Opus). Your notes on 11.3, 11.4, 12 and 14.3, and your general rule: a message that only confirms what you did is not said when the new focus says enough. First, the rule is written into the user experience description's general principles. Then every template is read against it. Taken out at least: "Opening the Wikipedia article for ...", "Left and Right now go round ...", "X is now called Y", and "Added the X view. OK uses it.". A message that tells you something you cannot hear otherwise stays, such as "Cancel brings it back" after a delete, or a count. You get the list of what was taken out and what was kept, with the reason for each kept one, before the change is committed.
* P4-T14g The map views dialog (Opus). Your notes on set 12.
  * Rename and Delete cannot be pressed while Political or Physical is chosen, but Tab still reaches them and NVDA says they are unavailable. Qt skips a disabled button when tabbing, so on the desktop the buttons stay in the Tab order and are marked unavailable to NVDA; in the web version, aria-disabled. The messages for pressing them on a built-in view go.
  * A Save changes button: it can be pressed only when a view of your own is chosen and the layers differ from what the view holds. It saves the layers as they are now into that view.
* P4-T14h Passed over without "along the path" (Sonnet). Your note on 8.3. The order is dropped; Passed over opens "by distance", nearest first, and Ctrl+S offers by distance, by name and by bearing. Glossary, user experience description section 6, and the checklist steps changed to match.
* P4-T14i England's coast (Opus). Your note on 5.6. Three things look wrong in Bordering England's Coast: one stretch "from Wales to Scotland, North Atlantic Ocean, 4,070 kilometres", which runs round from the Severn by Land's End and the Channel to the Tweed and is named after one sea; and two short stretches with the same neighbour at both ends, 3.3 kilometres with Wales and 17 kilometres with Scotland. Find out why on the Western Europe trial: a stretch probably takes the sea of most of its length, and small breaks at the estuaries of the Dee and the Tweed make the short ones. Proposed: split a stretch where its sea changes, so England's south coast reads as stretches on the Bristol Channel, the Celtic Sea, the English Channel and the North Sea; and join a stretch with the same neighbour at both ends under 20 kilometres to the stretch beside it. You see the new list before it is built into the world pack.
* P4-T14j Ceuta not said as an exclave (Opus). Your note on 13.3. It worked on the world pack on 20 November, so find what differs in the Western Europe trial, and fix it in the core or the build.
* P4-T14k Sark (Opus). Your note on 6.7. Search finds Sark only as a region of Guernsey, and Within was odd after going there. Find whether OpenStreetMap's island of Sark is missing from the islands layer or from the search index, and what Within listed. Fixed here if the cause is in the core; if it is the data, with P4-T13.
* P4-T14l Your questions on Exmoor (Sonnet). Your note on 14.7. Answered in the task list: whether "1 percent of Exmoor" is rounded up from less (the rule is: under 1 percent is said "less than 1 percent", so 1 percent means at least 0.5 rounded to 1, which the work item checks against the exact share); and why it reaches the sea, which is GMBA's coarse outline (DP220).
* P4-T14m The checklist itself (Sonnet). Steps 1.6 and 5.6 corrected, as your notes say they were poorly written. Sets 10 and 18, which you did not test, are kept for the Phase 4 checklist.

Tests first: zoom out and in at Winchester say "England" and "Hampshire" only; Go to Winchester says "Near Winchester"; Enter on a line item makes it the current feature, and Within lists it first; Shift+Enter on the smallest area says no current layer; after Enter, the focus is on the group's heading, desktop and web; Rename is unavailable on Political and Save changes saves the layers into a view of your own; Passed over has no "along the path".

Done when: every note above is fixed or answered, the full Python suite and the browser tests pass, and the checklist steps are changed to match.

## Carried from Phase 3

* P3-T15 Help (Sonnet): the user guide, the key reference made from docs/design/keymap.csv, the glossary, and the data sources page (DAT-9). The arrow keys in hierarchy mode are added to F1. Done after P4-T14, so Help describes the application as it is.
* P3-T20d Speed in the browsers (Opus): as DP222, if you agree, after P4-T3.
* The two unreliable browser tests (Sonnet): test_enter_on_a_layer_check_box_presses_ok_and_never_ticks_it, which sometimes says "Nothing to go to" as the Enter closing the Layers dialog reaches the map, and the Firefox test test_the_helper_script_isolates_the_page_and_the_pack_still_downloads.
* P3-T22 The web and sighted checklists: you chose not to do them at the end of Phase 3. They are folded into Phase 4's web and sighted checklists, which cover Phase 3's changes too.
* Known faults kept from Phase 3: the British Isles' rough Natural Earth outline makes Cornwall, Essex and the Isle of Wight "overlap" it at 99 percent; Washington state is stored only as "state of washington" in search. Both are looked at in P4-T13 and P4-T15.

## P4-T5 Pipeline safety in full

* Requirements: DMT-7, DMT-2.
* Needs first: nothing.

Work items:

* P4-T5a What is there already (Sonnet). The created files list, the run switch and `mapdata check` already do much of DMT-7. Check each acceptance criterion of DMT-7 against them, and list what is missing in the task list.
* P4-T5b The space estimate (Sonnet). Before a build starts, each stage's space needed is estimated from the pack's area and the figures of the last builds (the size trial and the world build), and the build stops with a clear message if the data folder has too little free space.
* P4-T5c The data folder check (Sonnet). If the data folder's drive is not connected, the build says so and stops before any work, naming the setting that points to it.

Tests first: a build with too little space stops before its first stage; a data folder that does not exist stops the build with the message.

## P4-T4 Corrections by rule

* Requirements: DMT-4, DMT-3.
* Needs first: P4-T5.

Work items:

* P4-T4a The rules file (Opus). A correction rules file in mapdata/config, read by a stage early in the build, with four kinds of rule: rename a feature, leave it out, change its layer or kind, and set its parent. Each rule names the feature by its identifier, such as osm:r62149, and gives its reason. A rule that changes is part of the stages' fingerprints, so only the stages after it rerun.
* P4-T4b The first rules (Sonnet). DP221's Sea of the Hebrides, if you agree, and any wrong name found in P4-T14. Each listed in the quality report.

Tests first: a rule renaming a feature in the test pack's settings changes its name in the pack and appears in the quality report; a rule for an identifier that is not in the data is reported, not silently ignored.

## P4-T11 Quality reports and the publish command

P3-T14's work items, moved to Phase 4 by DP197.

* Requirements: DMT-3, DMT-5, PCK-4, DMT-6.
* Needs first: P4-T4 for the corrections in the report; DP171 for the test release.

Work items:

* P4-T11a Quality reports (Sonnet). Every build writes a text report and CSV files, in plain lines a screen reader reads well: repaired shapes, features without names, gaps in coverage, gaps filled by the counties record, matches made by name for Wikidata, the correction rules applied, size by layer, and the differences from the last build, by feature and by layer (DMT-3).
* P4-T11b The publish command (Opus). `mapdata publish <pack>` puts the pack, its checksum and the updated catalogue on a GitHub release and its copy on Hugging Face, checks the two are identical, and checks every file is under 2 GiB (PCK-4). It asks before each upload and stops if anything differs. Nothing is published without your yes; the first use needs your Hugging Face sign-in. Done after P4-T6, so the pack manager can install what it publishes.

Tests first: the report lists a feature renamed in the test pack's settings; the publish command, with stand-ins for GitHub and Hugging Face, refuses a pack over 2 GiB and a mismatched copy.

## P4-T1 The regional pipeline

* Requirements: DAT-2, DAT-3 (detailed coastlines), PCK-1 (regional packs), DMT-1, DMT-7, LOC-6.
* Needs first: P4-T0e, P4-T5, P4-T4, P4-T11a.

Work items:

* P4-T1a A regional pack's settings (Opus). A pack settings file for a region, mapdata/config/packs/great-britain.yaml, with its outline from Geofabrik's boundary file. The region is read from the same planet file as the world pack (DP107), cut by its outline. The pack lists the pack tiles it covers in detail, so the core knows where it answers (AD-14). A small rehearsal region, Hampshire and the Isle of Wight, has its own settings file.
* P4-T1b Every administrative level (Opus). Below the counties: districts, then parishes, wards or communities, as OpenStreetMap holds them in each country, recorded in the tiers record. Each cut to the land polygons, slivers given to neighbours, and simplified on shared edges across every level, so a parish and its district meet exactly (AD-16).
* P4-T1c Every island and every lake (Opus). Islands, named or not, of any size, said "Unnamed island" where they have no name (DP87); lakes and ponds of any size. Small ones are left out of the drawing at wide zooms by the size rule, as now.
* P4-T1d Roads and paths (Opus). Every road, street, track and footpath, named or not, with its number, kind and name. A street in several pieces is joined by its name within a town. The OpenStreetMap way identifiers are kept for the network graph of Phase 5.
* P4-T1e Land use, parks, public spaces, school grounds and national parks (Sonnet). From OpenStreetMap's land use, leisure, amenity and boundary tags, with Shortbread as the check of which tags go in each layer (data sources). National parks moved here from Phase 3.
* P4-T1f Points of interest (Opus). Bus stops, crossings, post boxes, benches and bins, shops, cafes, pubs, places of worship, and the like, each given a friendly category in a category table (mapdata/config/poi_categories.yaml), with its words in the templates. You get the category table as a CSV to review before it is final.
* P4-T1g Rivers and streams at full detail (Opus). Every waterway, joined into rivers and streams as P3-T1g does, with the sections in order.
* P4-T1h Matching to the world pack (Opus). The world pack's identifier register (architecture 6.7): a regional feature is matched to a world feature by Wikidata identifier, then by name, kind and overlap. A matched feature keeps the world pack's identifier, with its own kept as an alias, so Hampshire is one feature whichever pack answers.
* P4-T1i Layers, zoom ranges, sounds and map views (Sonnet). Layer definitions for every new layer, with zoom ranges from Shortbread, earcons, and their place in the Political and Physical views' drawing order (DP198). Colours checked for contrast in every theme (VIS-2).
* P4-T1j The rehearsal (Opus). Build Hampshire and the Isle of Wight, time each stage and measure the size by layer, and estimate the Great Britain pack's time and size from them. A short report for you, with the estimate, before P4-T2 starts.

Tests first, on the test pack's street samples: the centre of Winchester has its streets, its park and its school ground; a bus stop is said with its category; every point in the sample has a parish or ward; a parish and its district meet with no gap; Hampshire from the street samples has the world pack's identifier.

## P4-T2 The Great Britain pack

* Requirements: DAT-2, DAT-3, PCK-1, DMT-1, DMT-7, NFR-1.
* Needs first: P4-T1, DP223.
* The PO, 26 November 2026, after the rehearsal: build England only, not all of Great Britain; keep unnamed land use (named by its use); before the build, change the stages that load every feature so no process goes over the memory aim. The work items below read "England" for "Great Britain".

Work items:

* P4-T2a The build (Opus). The Great Britain pack built from the planet file on the data folder, with the run switch and a stall watch, three workers, or six with --away.
* P4-T2b Size and splitting (Opus). The size by layer from the quality report. If the pack is over 1 GB, a proposal to you for splitting it, such as England, Scotland and Wales, before it is split.
* P4-T2c Checks (Sonnet). The street-level acceptance scripts for the UK test area (DAT-2); the coastline checks of spike S2 on the Great Britain pack; Skye in Highland and the Isle of Wight in its own county (DAT-3); built twice, identical (DMT-1); step timing against NFR-1.

## P4-T3 Combining packs

* Requirements: PLT-4, PCK-2, LOC-6, AD-14, architecture 6.8.
* Needs first: P4-T1h and a regional pack, the rehearsal's at first.

Work items:

* P4-T3a Several packs open together (Opus). The core opens every pack in the packs folder. For each pack tile, the most detailed pack that covers it answers where am I, drawing and Nearby. Where none does, the world pack answers, and nothing is said about missing detail (PLT-4).
* P4-T3b Features and relationships merged (Opus). Records and relationships from all packs merged by identifier and alias, so Within, Contains and Bordering give one Hampshire, not two, and a feature only in the regional pack, such as a parish, sits under the world pack's county.
* P4-T3c Search across packs (Opus). One search over every pack's search index, with a feature in two packs listed once.
* P4-T3d The web version with two packs (Opus). The worker opens both, and the memory is measured in Chromium and Firefox.
* P4-T3e At the edge of the pack (Sonnet). Acceptance scripts: step from Dover out into the Channel and on to Calais, and from Carlisle into Scotland, hearing only places, with no silence and no message about detail; the same feature from either side of the edge is the same feature.

Tests first: with the test pack and a small regional test pack together, a point in the regional pack's tiles is answered by it, a point outside by the world pack; Hampshire is listed once in Within; a search for Winchester gives one result.

## P4-T8 Bookmarks

* Requirements: USR-1, USR-3, SCP-6, SON-10, ACC-7, PLT-5, as rewritten in P4-T0d after DP219.
* Needs first: DP219, P4-T0d, P4-T0f.

Work items:

* P4-T8a The bookmarks file (Opus). One GeoJSON file of all bookmark lists, in the settings folder on the desktop and in the browser's private storage on the web, written safely so a crash never loses it. Reset all settings does not touch it. Each bookmark: its name, its point, the current feature's name when it was made, and a note.
* P4-T8b The bookmark dialog (Sonnet). Ctrl+Enter, on the map or on an item, as DP219 point 2: the Name box filled and numbered, the feature and coordinates read-only, the bookmark list box set to the list used last, New list, OK and Cancel. Both shells.
* P4-T8c The Bookmarks group (Sonnet). In the Information panel, on Shift+8: each bookmark list is a heading with its count, and its bookmarks under it, each with its distance and direction. Enter goes there, Space hears its direction, Shift+M measures to it, and Ctrl+S sorts by list order, name, distance or bearing, starting with list order.
* P4-T8d A bookmark as the current feature (Opus). Enter on a bookmark makes it the current feature. Then Delete deletes it, after asking; Ctrl+Enter opens the dialog to rename it; and Ctrl+X, Ctrl+C and Ctrl+V cut, copy and paste it into another bookmark list (DP211, point 7).
* P4-T8e The two dialogs (Sonnet). The bookmark list dialog and the bookmark manager, as DP219 point 7, each with a Close button (ACC-7). Both shells.
* P4-T8f On the map (Opus). Bookmarks as a layer: a mark the same size on screen with its name beside it (DP219 point 5), each bookmark list on or off, with its own zoom range. The layer on or off hides them from the map and from every announcement (SCP-6).
* P4-T8g The beacon from a bookmark (Sonnet). The beacon's source can be any bookmark (SON-10).

Tests first: Ctrl+Enter on the map at Winchester, then OK, makes "Winchester" in Bookmarks at that point; a second makes "Winchester_1"; Cancel makes nothing; the file is unchanged by Reset all settings; a bookmark list switched off is gone from the map and the group; Delete asks, and Cancel keeps it.

## P4-T9 Measuring from a bookmark, and bookmark files

* Requirements: USR-4 and USR-5, as rewritten in P4-T0d; INF-3.
* Needs first: P4-T8.

Work items:

* P4-T9a The measure start (Sonnet). Ctrl+Shift+M on any item or bookmark makes it the measure start, "Measuring from Winchester". Shift+M then measures from it, not from where you are. Ctrl+Shift+M on the map puts the start back to where you are (DP214).
* P4-T9b Saving and opening GeoJSON (Opus). One bookmark list, or all, saved as a GeoJSON file that opens in QGIS with each bookmark at its place under its name. A file whose list name is already used keeps both, the one opened called "Castles 2"; a file that is not a bookmark file is said to be so, and nothing changes (DP217).
* P4-T9c GPX, if DP219 agrees (Sonnet). Saving a list as GPX waypoints, and opening a GPX file's waypoints into a new bookmark list.
* P4-T9d Both shells (Sonnet). The desktop's standard Save and Open boxes; the web version's download and file chooser. A list saved on the desktop and opened on the web gives the same names, notes and order, and the other way round.

Tests first: measuring from a bookmark gives the same figures as GeographicLib within 1 metre; a list saved and opened again is identical; a plain JSON file that is not a bookmark file changes nothing.

## P4-T12 Territorial waters

* Requirements: DAT-15, DAT-3.
* Needs first: nothing; rehearsed on the Western Europe trial, then in P4-T15.

Work items:

* P4-T12a The stage (Opus). The sea part of each OpenStreetMap country area, which the build now cuts off at the coast, kept as a layer of its own, "Territorial waters", named such as "French territorial waters".
* P4-T12b Said and drawn (Sonnet). The layer's definition: said in Within at sea, drawn a lighter blue than the open sea in each theme, and off by a switch like any layer. Standing 5 kilometres off Brittany, you hear the sea first, and Within lists France's territorial waters.

## P4-T13 Groups of islands

* Requirements: DAT-1, DAT-3, LOC-3. From DP198.
* Needs first: P4-T14k's finding on Sark.

Work items:

* P4-T13a The source (Opus). Natural Earth's physical regions have no Channel Islands. Look at OpenStreetMap's archipelagos (place=archipelago) and Wikidata's island groups, with their licences, and report which gives the Channel Islands, the Isles of Scilly, the Hebrides, the Orkney and Shetland Islands, and the Balearics, with outlines good enough to say "you are in". The British Isles' rough outline (the known fault) is looked at in the same report.
* P4-T13b The stage (Opus). Groups of islands as a layer, each group's outline made from its islands, rehearsed on the Western Europe trial. Sark is an island in the Channel Islands, as well as part of Guernsey.

## P4-T15 The world pack rebuilt

* Requirements: PCK-1, DMT-1, DAT-3, DAT-15, and everything since the world build of 20 November.
* Needs first: P4-T4, P4-T11a, P4-T12, P4-T13, DP220, DP221, P4-T1h's identifier register, P4-T14i.

Work items:

* P4-T15a Fingerprints first (Sonnet). List which stages will rerun and why, and estimate the time. You are told before it starts.
* P4-T15b The build (Opus). Overnight, with the run switch and a stall watch. It brings the world pack up to date with the coast stretches (P3-T30b), search importance (P3-T33a), the islands stored for each sea (P3-T32g), territorial waters, groups of islands, mountain ranges cut to the coast, the correction rules and the identifier register.
* P4-T15c Checks (Sonnet). Every check passes; size against about 400 MB; built twice, identical (DMT-1); the quality report read for surprises, with a short note to you.

## P4-T6 The pack manager

P3-T13's work items, moved here by DP197, with the rest of PCK-2.

* Requirements: PCK-2, PCK-4, PCK-5, DAT-9, NFR-4.
* Needs first: P4-T11b for the real test release; DP171.

Work items:

* P4-T6a The catalogue in the core (Sonnet). catalogue.json read and checked (architecture 6.10): each pack's name, version, date, size, checksum, where it is downloaded from for the desktop and for the web, and the application versions it works with. Each pack's state: installed, not installed, or update available.
* P4-T6b Downloading on the desktop (Opus). On its own thread, into the packs folder (a setting, AD-18), with progress said at most every 10 percent, the checksum checked after, and a damaged download removed and said (PCK-5). The tests use a stand-in for the internet, so no test makes a network connection.
* P4-T6c Downloading in the web version (Opus). The pack downloaded whole into the browser's private storage from Hugging Face, while records are read by range requests until it is complete (PCK-4, spike S3). The storage limit checked first, with what is left said. Tested against the local test server in Chromium and Firefox.
* P4-T6d The dialog and first run (Sonnet). P opens the pack manager: a list of each pack's name, size, date and state, with Install, Remove, Update and Close. On first run with no world pack, TobyMap says what it needs and its size, and offers to download it. Both shells.
* P4-T6e Updates (Sonnet). A newer pack in the catalogue is offered when TobyMap starts, once, and in the pack manager.
* P4-T6f Cancel and resume (Opus). A download can be cancelled, and carries on from where it stopped next time, by range requests, on the desktop and the web.
* P4-T6g The packs folder (Sonnet). The pack manager says the free space in the packs folder, and the folder can be moved to another drive.
* P4-T6h The test release (Opus). The world pack published by `mapdata publish` to a GitHub pre-release and Hugging Face (DP171), after asking you, and installed from there by the pack manager on the desktop and in Firefox.

Tests first: a damaged download is found and removed; an incompatible pack is refused with a clear message (PCK-5); installing from the stand-in catalogue puts the pack in the folder and opens it; a cancelled download resumes; the web version reads records while a pack is still downloading.

## P4-T7 Robustness and memory

* Requirements: NFR-3, NFR-4.
* Needs first: P4-T2, P4-T3.

Work items:

* P4-T7a A damaged pack set aside (Sonnet). A pack that fails its checks at start-up is said, moved out of use, and TobyMap keeps running with the others (NFR-4).
* P4-T7b Memory with two packs (Opus). Memory on the desktop with the world and Great Britain packs, over a set walk, held under 2 GB (NFR-3); the same walk in Chromium and Firefox, recorded. If over, the pack tile cache's size is the first thing tried.

## P4-T10 Languages of names on the desktop

* Requirements: ACC-9. From DP196.
* Needs first: nothing; best done near the end, when you have time to listen.

Work items:

* P4-T10a The harness (Opus). A small tool that sends speech to NVDA through its Controller Client with each name's language marked, to find out with you whether NVDA switches voices for it.
* P4-T10b If it works (Opus). With NVDA running and Names set to "Always the local name", what TobyMap says goes that way, with the languages marked. If it does not, Help says so.

## The automatic exit checks

From the implementation plan, section 7, and how each is met:

* The street-level acceptance scripts pass for the UK test area (DAT-2): P4-T2c.
* A point 2 km off the Brittany coast is announced as sea (DAT-3), and the S2 coastline checks pass on the Great Britain pack: P4-T2c.
* Step timing meets NFR-1 on the Great Britain pack: P4-T2c.
* The world pack is published to a test release and installed from it by the pack manager (DP197): P4-T6h.
* New: a bookmark made on the desktop and opened on the web goes to the same place (USR-5), replacing "a bookmark still resolves after the pack is rebuilt", as bookmarks are now points (DP219).
* Also: built twice, identical, for both packs (DMT-1); memory under 2 GB with both packs (NFR-3); the installer installs, starts and uninstalls cleanly in continuous integration.

## Your acceptance checklist

docs/checklists/phase-4-desktop.md, phase-4-web.md and phase-4-sighted.md, made from the acceptance scripts. They will cover:

1. Installing the new version, and installing the world and Great Britain packs with the pack manager; cancelling a download and carrying it on.
2. Streets around a place you know, at a close zoom: streets, parks, school grounds, bus stops and parishes.
3. Moving from the Great Britain pack's area out to sea and across to France, hearing nothing about detail.
4. Making bookmarks with Ctrl+Enter, into two bookmark lists; the Bookmarks group; going to one, hearing it, measuring from it; the bookmark manager; a list switched off.
5. Saving a bookmark list to a file and opening it in the web version.
6. Territorial waters off Brittany, and the Channel Islands as a group.
7. Your notes from Phase 3 (P4-T14), and sets 10 and 18 of the tidy-up 2 checklist, which you did not test.
8. The NVDA language harness, if P4-T10 shows it works.
9. As data manager, following the guide: check, build the rehearsal region, read its quality report, and add a correction rule.

The sighted checklist covers the new layers' colours, the bookmark marks, territorial waters, and what Phase 3's sighted checklist held.

## Closing the phase

* The phase report, docs/plan/phase-4-report.md (Sonnet): what was built, how to install it, the checklists, known problems, and what was not tested.
* Continuous integration green on every job before you see it.
* Your feedback recorded against requirement IDs (DEL-4).
* I ask whether to publish (DP110, DP218). If you agree, the release with the installer, the portable zip and the release notes, the web version on GitHub Pages, and the packs by `mapdata publish`.

## Risks

* The Great Britain pack may be over 1 GB with every footpath and point of interest. The rehearsal (P4-T1j) estimates it before the build, and splitting is proposed to you, not done without asking.
* Matching regional features to the world pack's by name and overlap may join two features that are not the same, or miss two that are. The quality report lists every match made by name, for checking.
* Two packs open together cost memory, and most in the browser. P4-T7b measures it; the browser's storage limit for packs of 200 MB or more is checked before a download starts (P4-T6c).
* Hugging Face needs your sign-in once, for the first publish.
* Points of interest have thousands of tags. The category table starts small, with the categories you hear most, and grows from your notes.
* The world rebuild may rerun more stages than expected if a fingerprint changes. P4-T15a lists them before it starts.

## Left for later phases

* Network mode, travelling along streets and rivers, and driving: Phase 5.
* Northern Ireland, the Isle of Man and the Channel Islands as detailed packs, unless DP223 says sooner; Japan and Kenya: Phase 7.
* A sea and the ocean that holds it both listed in Nearby, and the rest of DP206: parked by you.
* The speed review, P7-T4a, which keeps the slow items found in Phase 3: the visible rule at 5,000 kilometres over North America, shared borders on long country borders, and Down from Europe.
* Tours of a bookmark list (USR-6): Later.
