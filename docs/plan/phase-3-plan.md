# Phase 3 detailed plan: information, hierarchy and search

Version 0.3, 11 November 2026. Written by Claude Code for the product owner (PO).

## Changes in version 0.3

These changes come from the size trial (P3-T1a) and your answer to DP175, 11 November 2026, and from P3-T1b.

* DP175: counties go into the world pack, and the base pack's soft limit is about 400 MB (PCK-1, requirements catalogue version 0.16). P3-T1c is now part of the world build. The sizes in P3-T1l, the exit checks and the risks are measured against 400 MB. The proposals below are kept as they were asked, with 250 MB.
* DP168: the IHO Sea Areas are still non-commercial (CC BY-NC-SA 4.0, checked on 11 November 2026), so the named seas come from Natural Earth's marine areas, as DP168 said for that case. P3-T1b says how.

## Changes in version 0.2

These changes come from your answers to DP167 to DP174, 10 November 2026.

* DP167: counties go into the Western Europe trial. The size report (P3-T1a) estimates the world pack's size from it, and what a larger pack would mean for you: start-up time, the time to the first place said, memory, download time and browser storage. Whether counties go into the world build is decided with you after that report.
* DP168: named seas as recommended.
* DP169: the thresholds are accepted for the trial. The thresholds for the world build are decided with you after the size report.
* DP170: no menu of actions on an item. Enter goes there and Space hears its direction, as now; Ctrl+Enter is kept for bookmarking in Phase 4; the Details region is about the current feature, the one on the map, and is reached with F4 or Tab; Shift and a number go to a group, which is about the current feature. Measuring's key is asked when P3-T7 is done. P3-T4e is now only these keys; LOC-4 and INF-10 in the requirements catalogue are changed to match when P3-T4 is done.
* DP171: the pack manager's test release is a GitHub pre-release.
* DP172: English and the local name only.
* DP173: kept as built: a letter first moves, a number first goes to a place. Nothing to change.
* DP174: the continents as recommended, with Cyprus in Europe, and the continent dividing lines written in the user guide.

This plan turns section 6 of "implementation plan.md" (version 0.5) into the work for each task, P3-T1 to P3-T16, and adds the work carried over from Phase 2 and two tasks from your answer to DP165. It follows the architecture (version 0.10), the requirements catalogue (version 0.15), the user experience description (version 0.20), the Phase 2 report and sweep plans, and your answers up to DP166. The tick list of what is done is docs/plan/phase-3.md.

## How to read this plan

* "The goal" and "Proposals and questions" are the parts most worth your attention. The questions are discussion points DP167 to DP174, all answered on 10 November 2026; the answers are listed at the top.
* "Which model does each work item" explains the Opus and Sonnet labels, as in Phase 2.
* "Order of work" says what is done when, and "Heavy runs" lists every time the laptop will be busy for a long while.
* Each task has its own level 2 heading, with the same parts in the same order: requirements, what it needs first, its work items, the tests, and when it is done.
* Each work item, such as P3-T1a, is small enough for one session, and has its own model label.
* The last sections cover the exit checks, your acceptance checklist, closing the phase, risks, and what is left for Phase 4.

Words follow the glossary. This plan adds nine words to it: tier, continent dividing line, base pack, relationship, search index, fact, current feature, hierarchy mode, item actions and look around. "Relationship" is used for what the pipeline works out between features, such as neighbours, because "relation" already means an OSM relation.

## The goal

The whole world can be explored and questioned at country scale, with the complete base pack:

1. Wherever you are, you hear a name: the country, region and county on land, and the named sea, bay or strait at sea. Continents, mountain ranges, major rivers and lakes, roads, railways, towns and cities are in the pack too.
2. The Information panel has all its groups: Within, Contains, Bordering, Overlapping, Crossing, Nearby, Crossed and passed, and Search. Every list can be sorted, and every item works the same way: Enter goes there, Space hears its direction.
3. The Details region (F4) gives the details of the current feature, with facts such as population and capital, each with its source and date, and a command opens its Wikipedia article.
4. Hierarchy mode, key 2, moves up from Hampshire to England, the United Kingdom, Europe and the World, down into what an area contains, and across to its neighbours, clockwise.
5. You can search by name, with accents and small misspellings ignored, and tell apart places with the same name. You can browse the world as a tree, list every feature of a kind in an area, and build a question such as "rivers crossing Germany".
6. You can measure from where you are to any item or search result, and look around: hear the Nearby group as sound, one item after another.
7. Disputed areas say so, and you can list every disputed and every unclaimed area.
8. The pack manager installs the base pack from where it is published, checks it, and offers it on first run.
9. A sighted helper sees a line with the coordinates, zoom and step under the map, and buttons to move.

What Phase 3 does not do: street detail, national parks, land use and points of interest (Phase 4, the Great Britain pack), pins and bookmarks (Phase 4, so the bookmark action waits), network mode and driving (Phase 5), and grid values and the sweep (Phase 6). Unnamed islands are in the base pack only above a size (DP169); every island, however small, comes with the regional packs.

## Which model does each work item

The same rules as Phase 2. Opus is chosen when a work item:

* needs a design decision the documents do not make, or must weigh several approaches
* is geometry where mistakes are subtle, such as containment, shared borders, the 180 degree line and the poles
* runs in real time or across threads, such as look around and downloads
* touches the screen reader interfaces, where what NVDA does must be found out, not assumed
* is a heavy pipeline run, or changes the pack format
* measures and improves speed, or publishes anything outside this laptop

Sonnet is chosen when a work item:

* follows a pattern that already exists in the code, such as a new command, template, setting, dialog or Information panel group
* has its behaviour fully written down here, with tests that say exactly what is right
* is documentation, a checklist, a CSV file or a list of keys
* is a second shell copying behaviour the first shell and the core already define

When a Sonnet work item hits something this plan did not foresee, it stops, writes a note in the task list, and the work item is handed to Opus.

In this plan, 65 work items are labelled: 30 Opus and 35 Sonnet. Phase 3 has more Opus work than Phase 2 because most of it is new data and geometry.

## Proposals and questions

Each is a discussion point in the discussion points file. You answered all of them on 10 November 2026; "Changes in version 0.2" at the top says what each answer changed. The proposals are kept below as they were asked.

### DP167: counties in the base pack

The base pack lite has countries and regions only. Your Phase 3 gate starts "hierarchy from Hampshire up to the World", and Hampshire is a county. The counties method from Phase 1 (DP101, DP107) works, but has been run only on trial countries.

* Proposal: the base pack has a Counties layer for the whole world, built with the counties record, with its zoom range to 100 km as now. The size trial (P3-T1a) measures what it costs. If the pack would go over 250 MB with everything else, counties are the first thing I suggest moving to the regional packs, and Hampshire's checklist step would wait for Phase 4.

### DP168: named seas

You asked for the source with the most named areas (DP115). The base pack lite uses VLIZ's Global Oceans and Seas, which has only the ten ocean regions.

* The IHO Sea Areas from Marine Regions have about 100 named seas, with good edges, but their catalogue record said non-commercial share-alike, which does not fit the ODbL packs. Marine Regions has moved some of its sets to CC-BY since, so I check the licence again on its own pages first.
* Natural Earth's marine areas (public domain) have about 300 named seas, bays, straits and channels, with coarse edges.
* OpenStreetMap has many more named bays and straits, often as a single point, of uneven quality.
* Proposal: IHO Sea Areas for the seas if the licence is now CC-BY 4.0, otherwise Natural Earth's marine areas; then Natural Earth's bays and straits inside them; then OSM's named seas, bays and straits that are only points, so they can be found by search and Nearby (DAT-4). VLIZ's ocean regions stay as the top of the water hierarchy.

### DP169: what else goes in the base pack, and how much

DAT-1 lists what the base pack covers. Each needs a threshold, so the pack stays near 250 MB. Proposal, to be checked by the size trial:

* Rivers: rivers from OSM that have a Wikidata link and are at least 50 km long, joined into whole rivers, checked against Natural Earth's rivers at 1:10 million.
* Lakes: lakes of 10 square kilometres or more, from OSM with their names, checked against HydroLAKES (CC-BY 4.0). The Caspian Sea stays a sea (DP114).
* Roads: motorways and trunk roads. Railways: main lines.
* Towns and cities: every OSM city and town, as places, with population where known. Villages wait for the regional packs.
* Mountains: GMBA mountain ranges (CC-BY 4.0), Natural Earth's physical regions such as deserts and plateaus, and peaks of 1,000 metres or more with a name.
* Islands: every named island, and unnamed islands of 1 square kilometre or more, called "Unnamed island" as you asked in DP87. Smaller unnamed islands are land of their country until the regional packs.
* If the trial shows the pack well under 250 MB, I suggest lowering the thresholds before the world build, and tell you the figures.

### DP170: the item actions

INF-10 lists six actions on every Information panel item. Enter goes there and Space hears its direction already.

* Proposal: the Applications key, or Shift+F10, on an item opens a menu of all its actions, as in any Windows list: Go there, Details, Bordering, Contains, Overlapping, Crossing, Hear its direction, Measure, and in Phase 4 Bookmark. The menu shows the key of each action that has one.
* D on an item gives its details, and M measures to it, as on the map for the current feature.
* "Its own groups" without moving: choosing Bordering on Spain fills the Search group with "Bordering Spain" and its items, and the focus goes there. So the panel never changes what its other groups are about until you move.

### DP171: a test release for the pack manager

The exit checks say the base pack is published to a test release and installed from it. The repository is public, so a test release is visible to anyone.

* Proposal: a GitHub pre-release named "packs-test", marked as a test, holding the base pack and the catalogue, with its copy on the TobyMap dataset on Hugging Face. It is replaced, not added to, each time. Nothing is published until you say yes, and Hugging Face needs you to sign in once to make the access key.
* The other choice: a private test repository of your own, which the web version cannot read without a key.

### DP172: languages of names

ACC-9 asks for names in your preferred language, then the local name, marked with their language.

* Proposal: the base pack keeps each feature's local name, its English name, and its names in the languages with the most names in OSM and Wikidata, up to ten languages, if the size trial says they fit; otherwise English and the local name only. The Speech tab gets "Preferred language for names", listing the languages the installed packs hold.
* In the web version, each name is marked with its language, so a screen reader set to switch voices can. On the desktop, I find out whether NVDA can switch voices from a Qt tree item's language, and report what works.

### DP173: DP157 asked again, more plainly

You asked what problem DP157 solves. Plainly: in Go to, "N51.5 W0.12" can mean two things.

* As built now: a letter first means move. "N51.5 W0.12" moves you 51.5 degrees north and 0.12 degrees west from where you are.
* As before DP154: "N51.5 W0.12" means go to the place at 51.5 north, 0.12 west, which is London.
* So someone who copies coordinates written with the letter first, as some web sites write them, would move instead of going there.
* Option A, keep it as built: a letter first always moves; a number first always goes to a place. Simple to explain, and the user guide says so.
* Option B: a letter joined to its number, "N51.5", goes to a place; a letter, a space, then a number, "n 5", moves. Copied coordinates work, but a missing space changes the meaning.
* My suggestion is A.

### DP174: the continents

DAT-12 asks for continents built from countries, split along lines set in the settings, and DP88 places each distant part in the continent it is on.

* Proposal: seven continents: Africa, Antarctica, Asia, Europe, North America, Oceania and South America. Central America and the Caribbean are in North America, Greenland in North America, and the Pacific islands in Oceania.
* Countries split by a continent dividing line: Russia and Kazakhstan along the Ural Mountains and the Ural River; Turkey at the Bosphorus and the Dardanelles; Egypt at the Suez Canal, so Sinai is in Asia; Georgia and Azerbaijan along the Greater Caucasus watershed; and Indonesia, whose part of New Guinea is in Oceania. Panama is all in North America.
* Distant parts go to the continent they are on (DP88): the Canary Islands, Ceuta and Melilla in Africa, Hawaii in Oceania.
* Cyprus is in Asia by geography and in Europe by politics. I suggest Asia, with a note in Help, but this is your choice.

### Asked again at the start of the phase: publishing (DP110)

You accepted Phase 2 on 10 November. As agreed, I ask whether to publish 0.1.1 as a GitHub release, with the web version on GitHub Pages and the world pack as a data release. This is P3-T0b.

### Not questions: settled by your earlier answers

* Country units: French Guiana and the others are their own entries, with no sovereign states layer (DP86).
* Unnamed islands are called "Unnamed island" (DP87). The size limit in the base pack is in DP169.
* Distant parts of a country go in the continent they are on (DP88).
* Counties come from the counties record, one rule for every country, which the build keeps (DP101).
* The Caspian Sea is a sea; unclaimed land is "Unclaimed" and can be listed (DP114, DP120).
* Land held twice waits for Phase 3 to give both parties equal credit (DP119). P3-T2c does this.
* Tiers for England, Scotland, Wales and Northern Ireland, and controls for sighted users: you said to plan all of it (DP165). They are P3-T17 and P3-T18.
* Always say the place after a step: the recommendation, one switch in the Speech tab (DP162). It is P2-T17q.
* The listening test: eight places at the eight compass points, with a few sound models, and no echo (DP164). It is P2-T17u.
* Linked steps: four more step sizes, 2.5, 10, 50 and 500 km (DP166, option B). Not yet built; it is P3-T0f.
* Bordering, Overlapping, Crossing and Search are not limited by zoom; Contains, Nearby, and Crossed and passed are; Within follows the zoom ranges (DP80, DP160).
* A partly inside feature counts as inside, with no label (DP70). Identical boundaries are said once with both types (DP71). Moving to a feature in hierarchy mode zooms to fit it, and going back restores the zoom (DP77).
* The web version reads packs from Hugging Face, the desktop from GitHub Releases (DP83, DP102, PCK-4).

## Order of work

1. Start of the phase: P3-T0a to P3-T0f. Versions, the publishing question, the key list, samples for the test pack, the implementation plan's new version, and DP166's step sizes.
2. The carried work items that need no data: P2-T17n, P2-T17q and P2-T17v. P2-T17u when you have time to listen.
3. The data, first on a trial region, Western Europe and the Alps, so each stage is quick to try: P3-T1a (the size trial), then P3-T1b to P3-T1j, P3-T17, P3-T2 and P3-T3, then the search index, P3-T8a.
4. P3-T1k, the writing stage made faster, then the world build, P3-T1l, a heavy run.
5. While the world build runs, the application work on the test pack, which needs no heavy run: P3-T4 (the Information panel), P3-T5 (details) and P3-T6 (hierarchy mode), then P3-T7 (measuring).
6. P3-T8 (search), P3-T9 (the world tree and browsing), P3-T16 (disputed and unclaimed lists), then P3-T10 (the query builder).
7. P3-T11 (look around) and P3-T12 (name languages).
8. P3-T13 (the pack manager) and P3-T14 (quality reports and publishing).
9. P3-T18 (controls for sighted users) and P3-T15 (Help).
10. The installer, the checklists, the phase report, and your acceptance.

Every question is answered. Counties go in (DP175). One decision is still to make with you, before the world build: the thresholds for the world (DP169).

## Heavy runs

Before each one I tell you how long it should take, how many cores it uses and how much memory, as agreed in DP103, and arm a watch for stalls. One heavy run at a time. The planet file is read in its own short-lived process, because GeoDesk keeps about 24 GB mapped until that process ends.

* Samples for the test pack, read from the planet file (P3-T0d): a few minutes, but nothing else may read the planet file then.
* The size trial on Western Europe and the Alps (P3-T1a): about an hour, and repeated after each new layer is tried. Its figures, scaled by area to the whole world, give the estimate for the world build. As agreed for speed trials, the estimate is checked on a region not used to tune it.
* Downloading facts from Wikidata (P3-T2a): not heavy on the laptop, but it runs for some time, in small batches, so as not to overload Wikidata's service. Kept in the data folder, so it is done once.
* The world build (P3-T1l): every new stage on the whole planet, with 3 workers, or 6 if you are away. I estimate it from the trial and tell you before it starts. The Phase 1 build took about 80 minutes; this one reads much more of the planet file and works out the relationships, so it will be several hours.
* The world build a second time from its kept results, to prove it comes out byte for byte the same (DMT-1).

## Start of the phase

### P3-T0a Versions (Sonnet)

* Check for newer PySide6 and Pyodide releases. On 5 November the latest were PySide6 6.12.0 and Pyodide 314.0.7.
* If either is newer, upgrade it, run all the Python and browser tests, and commit the upgrade only if they pass; otherwise put the old version back. Note the result in phase-3.md.

### P3-T0b The questions left from Phase 2 (Sonnet)

* Ask whether to publish 0.1.1 (DP110). If you say yes, the release is done as P3-T14b's first use, with your sign-in for Hugging Face.
* DP167 to DP174 are already in the discussion points file, added with this plan, with DP173 asking DP157 again in plain words.
* DP150, the half second before a label in the web version, was parked for your Phase 2 testing. Ask whether it felt slow; if it did, the change it suggests is a small work item added here.

### P3-T0c The key list (Sonnet)

* docs/plan/phase-3-keys.csv, made by tools/make_key_list.py, with every Phase 3 command and the key proposed in the user experience description, section 12.
* It marks the proposed keys already taken, so you choose: T is the world tree and the next theme; O is Overlapping and the orientation; L is look around, which is free; D details and M measure are free; 1 and 2 are stepping and hierarchy mode; Q is the query builder; Ctrl+F is search.
* The new Information panel groups get Shift and their number from the group list, as Shift+1 to Shift+3 do now (DP156). With all eight groups in the order of INF-10, Nearby would move from Shift+2 to Shift+6. I propose new groups go after the three you know, so your keys do not change: Within, Nearby, Crossed and passed, Contains, Bordering, Overlapping, Crossing, Search.
* Your keys go into the registry with the task that adds each command. The key clash test runs on them then.

### P3-T0d Samples for the test pack (Sonnet)

* Small samples read from the planet file with GeoDesk, kept in tests/samples/osm with the ODbL notice, so every Phase 3 test runs on the test pack, without the data folder: Hampshire and Wiltshire with England; the New Forest National Park, which overlaps them (only for INF-5 and the ambiguous up of NAV-4: national parks come to the real packs in Phase 4); Switzerland and its five neighbours, simplified; a short length of the Rhine; the Bay of Biscay; and a handful of places with shared names, such as two Parises and Sao Paulo.
* Tools/make_phase3_samples.py makes them again, as tools/make_itchen_samples.py does.

### P3-T0e The implementation plan, version 0.6 (Sonnet)

* Adds P3-T17 and P3-T18 from DP165, the carried work items, P3-T0f, and the move of national parks to Phase 4 for the real packs. Lists the changes at the top, as each version does.

### P3-T0f Four more step sizes (Sonnet)

* Add 2.5 km, 10 km, 50 km and 500 km to the step list, and the near imperial sizes to the imperial list, so each zoom from 1 km to 1,000 km has its own step when linked.
* Tests first: Page Up linked, from 1 km to 1,000 km, changes the step on every press; a saved step list from before still loads.

## Carried from Phase 2

These keep their Phase 2 numbers, so the sweep plan and your notes still find them.

### P2-T17n The spatial voice stops at a key press (Sonnet)

* Requirements: SON-3. From desktop checklist 11.2.
* Any key that runs a command stops the Alba voice, so it never talks over NVDA. The core says "stop the voice" in its response to every command, except the ones that start a label; each shell stops it. Both shells.
* Tests first: a label is playing, Down is pressed: the voice stops before the step is said, on the desktop and in Chromium and Firefox.

### P2-T17q Always say the place (Opus)

* Requirements: ACC-5, ANN-1. As you accepted in DP162.
* A new switch in the Speech tab, "Say the place after every step, even when it has not changed", off at first, outside the presets, so changing it never makes the preset Custom. With it on and nothing changed: terse says the smallest area; normal, the smallest area and its country; detailed, the whole place. A held key still clicks, and only the last place is said on the release (ANN-3).
* Opus, because it changes what the describer says after every step and must not slow it (NFR-1).
* Tests first: each preset with the switch on, a step inside Kent; the switch does not make the preset Custom; a held key says one place.

### P2-T17u A listening test for sound in space and the voice (Opus)

* Requirements: SON-1, SON-2, SON-3, SON-9. As you answered in DP164.
* Eight places, one at each of the eight compass points, played with each of a few sound models in turn: stereo with pitch, as now; HRTF with pitch; stereo with twice the lower pitch behind; stereo with more muffling behind. Each sound is followed by its name in the Alba voice from the same place. No echo.
* Built from tools/listening_test, with no window, on your own headphones. It writes what was played and what you heard into a CSV file, as Phase 1's did, and I analyse it and propose the settings.
* You run it; I don't.

### P2-T17v The map for sighted users (Opus)

* Requirements: VIS-1, VIS-2, DAT-13.
* As you asked, 10 November 2026: the task is limited to making the special lines stand out on the map, with the outline setting below and the fix for the line across France.
* P2-T17v-a: the special lines (the equator, the prime meridian, the tropics, the polar circles and the date line) drawn thicker and in their own colour, in every theme, keeping 7 to 1 in the high contrast themes. As you suggested, it is a setting of the layer: the special lines are already a layer of their own, and a new layer setting, line_style: special, is stored in the pack with the layer. The map draws any layer with it thicker, in the theme's special line colour, on top of the plain lines, so nothing in the map knows the special lines (SCP-7). The world pack is written again to carry it; only the stage "writing the pack" runs.
* The colours: standard, dark purple; high contrast dark, light green (7.25 to 1 against the darkest land); high contrast light, dark red; colour-blind safe, dark purple.
* P3-T1b gives its named seas, bays and straits the types sea, bay and strait, which the outline setting knows.
* P2-T17v-b, the red line, found: it is the current outline of the North Atlantic Ocean. Where the North Atlantic meets the Arctic Ocean, its edge runs from Norway past Shetland and the Faroes to Iceland, across open water. A new setting in the Map display tab, "Outline the current area", with four choices:
  1. Always, as now. This is the setting at first.
  2. Not for the oceans, the top of the water hierarchy.
  3. Never for oceans and seas. Until the named seas come in P3-T1b, this is the same as choice 2.
  4. Never.
  VIS-1 is changed to say the current area is outlined as this setting chooses.
* P2-T17v-c, the straight line across France, found and fixed: it ran along 45 degrees north, the edge of a pack tile, at the 1,000 km zoom. A tile edge is never outlined (AD-17), but where the last real point before it was less than a pixel away, that point was merged into the next and the long edge along the tile edge was outlined. Such a point is now always kept. Tested, and checked in a picture of France before and after.

## P3-T1 The complete base pack

* Requirements: DAT-1, DAT-4, DAT-5, DAT-12, LOC-6, PCK-1, DMT-1, DMT-7.
* Needs first: P3-T0d for the tests; DP167, DP168, DP169 and DP174 for the world build.

Every new layer follows the same pattern as the graticule: its layer file in mapdata/config/layers, its source in sources.yaml after the licence check (rule 7) and in "data sources.md", a stage of its own with its fingerprint, and its zoom range from Shortbread with the reason in docs/data-manager/configuration.md. No code in the application is written for any one layer (SCP-7).

Work items:

* P3-T1a The size trial (Opus). A trial pack, mapdata/config/packs/trial-western-europe.yaml, covering Western Europe and the Alps, with counties (DP167), built with each new layer as it is added. For each layer: its features, points, and its share of the pack in MB, scaled by area to the whole world, and the time each stage took. Then the estimated size of the world pack, and how far it is from 250 MB. Then what a larger pack means for you, measured on the trial pack and a padded copy of the world's estimated size, on the desktop and in Chromium and Firefox: the start-up time, the time to the first place said, the memory used, the download time at 10 and 50 megabits a second, and the browser storage it needs. Written as docs/plan/p3-t1-size-report.md. You decide with me, from it, whether counties go in and the thresholds for the world build.
* P3-T1b Named seas, bays and straits (Opus). As DP168 decides: Natural Earth's marine areas, as the IHO Sea Areas are still non-commercial. A new layer, "Seas, bays and straits", below the oceans. The new sea areas are cut to the land, as the oceans are. A sea that is only a point is a place in the Seas layer, findable by search and Nearby, but not said as where you are (DAT-4). The VLIZ ocean regions stay the top of the water hierarchy.
* P3-T1c Counties for the whole world (Opus). In the trial first (DP167), then in the world build, as you agreed in DP175. The counties record names level 5 where a country's real counties are there, such as Argentina's departments and Tunisia's delegations (size report, "What the trial found about counties"). The counties stage runs for every country, writing the counties record as it goes, with "worked out" against each country, and listing every gap it filled in the quality report (DP101). A corrected entry is never overwritten. The trial countries' records from Phase 1 are kept.
* P3-T1d Islands (Opus). Named islands from OSM, as areas cut to the land polygons, in an Islands layer. Unnamed islands of 1 square kilometre or more (DP169), called "Unnamed island". An island shared by two countries, such as Märket, is one island in both. Small islands are left out of the wide drawing levels, as now (architecture 6.9).
* P3-T1e Continents (Opus). As DP174: seven continents, Cyprus in Europe. A stage builds each continent from its countries' land, split along the continent dividing lines in mapdata/config/continents.yaml, with distant parts placed by where they are (DP88). Tested: Russia west of the Urals is in Europe and east in Asia; Istanbul's European side is in Europe; Tenerife is in Africa; there is no land in no continent, and no land in two.
* P3-T1f Mountain ranges, physical regions and peaks (Sonnet). GMBA Mountain Inventory version 2, with its own hierarchy of ranges kept as containment; Natural Earth's physical regions; and peaks as places with their elevation. Tested: a point in the Alps has the Alps in Within (DAT-5).
* P3-T1g Rivers (Opus). OSM river ways joined into whole rivers by name and Wikidata link, with their direction from source to mouth kept for Phase 5. A river with branches, such as a delta, is one feature with several parts. Checked against Natural Earth's rivers: every Natural Earth river over 500 km has a match. The fall-back, if joining OSM rivers worldwide is too slow or too unreliable, is Natural Earth's rivers with their Wikidata links, and I tell you.
* P3-T1h Lakes (Sonnet). OSM lakes over the size in DP169, cut where they cross a border, with names, checked against HydroLAKES for missing large lakes. Each lake is in the Water hierarchy, so "where am I" on Lake Geneva says the lake.
* P3-T1i Roads and railways (Sonnet). Motorways and trunk roads, and main railway lines, as lines with their names and numbers, such as "M3". Ways of one road are joined into one feature per road and country, so the road's record is not thousands of short lines.
* P3-T1j Towns and cities (Sonnet). OSM cities and towns as places, with population from OSM, later replaced by Wikidata's with its date (P3-T2). Each has the areas it is in, for search's descriptions.
* P3-T1k The writing stage made faster (Opus). In the Phase 2 rebuild, about 11 of the writing's 26 minutes ran on one core with no progress line. Try at least two approaches, such as spreading the drawing levels over the workers and writing pack tiles as they are made, and keep the fastest that gives the same pack, byte for byte. A progress line at least every minute (DMT-2). Results written in the size report.
* P3-T1l The world build (Opus). A heavy run, announced first. Then: the build twice check (DMT-1), the no gaps check (LOC-6), the coverage check of sample places worldwide (DAT-1), the 180 degree line checks, and the size against about 400 MB (PCK-1, DP175). The pack's report written for you. The base pack lite is kept until the new pack passes.

Tests first:

* On the test pack: the samples' seas, lakes, rivers and places appear in the right layers, with no code written for any layer.
* The coverage check: a new file, tests/acceptance/base_places.yaml, of at least 100 places worldwide with the names expected, including a sea, a bay, a strait, a lake, a mountain range, an island and an unnamed island, on every continent, both sides of the 180 degree line, and both polar regions.
* "Where am I" in the Bay of Biscay says the Bay of Biscay, and Within lists it, then the North Atlantic Ocean (DAT-4, LOC-6).
* Every stage gives the same output twice from the same inputs.

## P3-T17 Tiers, and constituent countries

* Requirements: NAV-4, LOC-2, LOC-3, VIS-1. From DP165, part 1.
* Needs first: P3-T1c.

Work items:

* P3-T17a (Opus). Each area gets a tier as well as its OSM level, set in the counties record, or a record beside it for the tiers above counties. England, Scotland, Wales and Northern Ireland are "constituent countries of the United Kingdom", a tier between country and county. The Regions layer is renamed "Regions and constituent countries". Ranking for "where am I" and the order of Within use the tier, so Hampshire, England, United Kingdom reads in the right order everywhere.
* The sighted notes said Regions made the map of north-west Europe confusing. To keep layers shared by sight and sound (SCP-6), the layer stays on and said; instead, the map display setting gets "Draw the borders of regions", off at first, as the borders setting from DP108 does for all borders. You and the sighted helper can try it either way.

Tests first: in Hampshire, Within lists Hampshire, England, United Kingdom, Europe; England's details say "constituent country of the United Kingdom"; Brittany's say "region of France"; with region borders off, the map draws none and "where am I" still says the region.

## P3-T2 Facts, Wikipedia links and disputed areas

* Requirements: DAT-7, DAT-8, ANN-6, INF-1, DAT-9.
* Needs first: P3-T1's layers on the trial pack.

Work items:

* P3-T2a The Wikidata stage (Opus). For every feature with a Wikidata link, its facts are fetched from Wikidata's query service in batches, with a plain client name and no personal details, and kept in the data folder with the date fetched, so a rebuild does not fetch again (DMT-1). Wikidata is CC0, added to sources.yaml and "data sources.md". The facts: population with its date, area, capital, elevation for peaks, length for rivers, the English Wikipedia article's title, and the official name. A feature without a Wikidata link is matched by name and place only where exactly one match is found, and each match is listed in the quality report.
* P3-T2b Facts in the pack (Opus). The feature record gains facts, each with its source and date, and the Wikipedia title (architecture 6.4). A new format number, 4, with format 3 packs still read; docs/developer/pack-format.md updated. The core gives the facts to the details (P3-T5).
* P3-T2c Disputed areas (Opus). Natural Earth's breakaway and disputed areas (public domain) are matched to the pack's areas. A disputed area is said with "disputed", and its details name the source and its view (ANN-6, DAT-8). The 15 places held twice in OSM (DP119), such as Crimea and Abyei, become disputed areas of their own, each listing both countries as claimants with equal credit, instead of being given to one. The West Bank and the Ilemi Triangle keep their disputed mark.

Tests first: France's facts include area, population and capital, each with source and date (INF-1); at least 95% of countries and 80% of cities over 100,000 people have a population and a Wikipedia link (DAT-7); in Crimea, "where am I" says "Crimea, disputed", and its details name Russia and Ukraine as claimants.

## P3-T3 Relationships in the pipeline

* Requirements: AD-8, NAV-4, INF-2, INF-4, INF-5, INF-6, DAT-4, LOC-3.
* Needs first: P3-T1b to P3-T1j on the trial pack.

Each work item works only on features near each other, through a spatial index, never on a whole layer at once, which was spike S2's lesson.

Work items:

* P3-T3a Containment (Opus). For each feature, the areas that contain it fully and those it is partly inside, from every layer, with parents of parents, so the ambiguous "up" is quick to find (NAV-4). Identical boundaries, within a small tolerance set in the settings, are stored as "same as", not as a parent (DP71). Areas that share an edge, such as Hampshire inside England, use the shared edges from the writing stage, so a shared border is never read as partly outside.
* P3-T3b Neighbours and overlaps (Opus). Neighbours in each layer, with the length of each shared border on the ellipsoid, and areas that nearly touch, within a distance set in the settings, with the distance between them (INF-2). Overlaps across layers, with the share of each area covered (INF-5).
* P3-T3c Crossings (Opus). For each line, the areas it passes through in order from its start, or from its source for a river (INF-6). For each area, the lines crossing it or along its border.
* P3-T3d The water hierarchy (Opus). Oceans contain seas, seas contain seas, seas contain bays and straits, by the share of each one's area inside the other, and lakes are within the land areas around them (DAT-4, LOC-6).
* P3-T3e Storing them (Opus). Relationships in buckets by identifier (architecture 6.2, 6.5), counts by type for each area, for the world tree and the reports, and the pack's size impact in the size report.

Tests first, on the test pack:

* Switzerland has exactly five neighbours, France, Germany, Austria, Liechtenstein and Italy, each with its shared border length within 2% of Wikipedia's (INF-2).
* Hampshire's parents are England and the United Kingdom, with no ambiguity; a point in the New Forest has two parents, Hampshire and the New Forest National Park, neither inside the other.
* The New Forest National Park overlaps Hampshire and Wiltshire, with a share for each (INF-5).
* The Rhine's countries in order from its source (INF-6).
* The Bay of Biscay's parents are the North Atlantic Ocean, then the Atlantic Ocean (DAT-4).
* Built twice, the relationships are identical (DMT-1).

## P3-T4 The Information panel

* Requirements: INF-10, INF-2, INF-4, INF-5, INF-6, LOC-3, LOC-4, ANN-7.
* Needs first: P3-T3 on the test pack.

Work items:

* P3-T4a The groups and the current feature (Opus). The group table in the core holds all eight groups, in the order you choose in the key list, with each group's default sort and whether the zoom limits it (INF-10, DP80, DP160). Each group is filled only when opened, so a step never waits for it (NFR-1). The current feature is kept by the session (LOC-4): the smallest area when stepping, the feature last moved to in hierarchy mode, and Contains, Bordering, Overlapping and Crossing say which feature they are about in their heading, such as "Bordering France, 8 items".
* P3-T4b Contains (Sonnet). The types of visible feature inside the current feature, each with a count, such as "Regions 13", and the features of each type below it (INF-4). Only types with something visible. A feature partly inside counts as inside, with no label (DP70).
* P3-T4c Bordering, Overlapping and Crossing (Sonnet). From the stored relationships: each neighbour with its shared border length, or the distance for one that nearly touches; each overlapping area with its share; each line crossing, or for a line, the areas it passes through in order. Not limited by zoom (DP80).
* P3-T4d Sorting and typing to jump (Sonnet). Ctrl+S in the panel cycles name, distance and bearing clockwise from ahead, with Within's natural order as its default, and says "Sorted by distance". Typing the start of a name jumps to it, in both shells.
* P3-T4e The keys on an item (Sonnet). As DP170: no menu of actions. Enter goes there and Space hears its direction, on every item of every group, as now. Ctrl+Enter on an item says "Bookmarks come in Phase 4." until bookmarks are built. Shift and a number go to a group, which is about the current feature, so to see Spain's neighbours you go to Spain first. LOC-4 and INF-10 in the requirements catalogue, and section 6.3 of the user experience description, are changed to say this.
* P3-T4f The selected item on the map (Sonnet). The item focused in the panel is outlined on the map in the theme's highlight colour, keeping 7 to 1 in the high contrast themes.

Tests first:

* Contains for Wales, zoomed to fit, lists types with counts, and each opens to its features (INF-4).
* With a 5 km zoom, Contains for the United Kingdom lists only what is within 5 km (INF-4).
* Bordering for Switzerland lists the five, sorted by bearing at first.
* Each group's default sort, and Ctrl+S's cycle and words, on the desktop and in Chromium and Firefox.
* Enter and Space work on an item of every group; Ctrl+Enter says bookmarks come in Phase 4.
* A step's time is unchanged with all eight groups (NFR-1).

## P3-T5 Details and Wikipedia

* Requirements: INF-1, LOC-4, DAT-7, DAT-9.
* Needs first: P3-T2b.

Work items:

* P3-T5a The details (Sonnet). The Details region, reached with F4 or Tab, is about the current feature, the one on the map (DP170), and is filled when you go there. The details: name and other names, type and tier, area or length, population, capital, elevation, parents, disputed and the source's view, the data source and its licence, each fact with its source and date. All words from the templates. Every answer says which feature it is about (LOC-4).
* P3-T5b Open in Wikipedia (Sonnet). A command in the Details region opens the article in your browser: the desktop through Qt, the web version in a new browser tab. With no article, it says "No Wikipedia article for France." Tests check the address asked for, without opening anything (rule 5).

Tests first: France's details include area, population and capital (INF-1); a disputed area's details name its source; a feature from a CC-BY source names it.

## P3-T6 Hierarchy mode

* Requirements: NAV-4, NAV-8, NAV-10, LOC-4, NAV-11, SON-6.
* Needs first: P3-T3, P3-T4a.

Work items:

* P3-T6a Up, down and across in the core (Opus). Key 2 enters hierarchy mode, key 1 goes back to stepping, and neither moves you (NAV-11). The current feature starts as the smallest area where you are.
  * Up goes to the parent, from layers shown only. If two parents contain the feature and neither contains the other, the ambiguous up earcon plays, and a menu offers the choices, or Cancel to stay.
  * Down lists the types of visible feature inside, with counts, then their features; choosing one moves into it. This is the same list as Contains.
  * Left and Right go to the neighbours, clockwise from ahead, each said with its direction in your format and its shared border, such as "Spain, borders to the south-west, shared border 623 kilometres".
  * Moving to a feature goes to its representative point and zooms to fit it, and says the zoom (DP77). Each move is a jump, so Alt+comma comes back with the zoom as it was.
* P3-T6b The shells (Sonnet). The ambiguous menu and the down lists as standard menus or lists with Cancel (ACC-7), in both shells, and the H key saying the movement mode.

Tests first, on the test pack:

* From Hampshire, up goes to England, the United Kingdom, Europe and the World, with no menu (NAV-4).
* From a point in the New Forest, up plays the earcon and offers Hampshire and the New Forest National Park.
* Down from France lists Regions, and choosing it lists the regions; down from a county with no national park does not list national parks.
* Neighbours of France include Spain, Belgium and Germany, in clockwise order from ahead in each orientation.
* Up from the United Kingdom zooms to fit Europe; Alt+comma returns to the United Kingdom's zoom.

## P3-T7 Measuring

* Requirements: INF-3, INF-8.
* Needs first: P3-T4; the search part needs P3-T8b.

Work items:

* P3-T7a (Sonnet). Its key is asked of you first, as DP170 said. It measures from where you are to the item focused in the panel, or to a search result: the distance along the ellipsoid and the bearing in your format, to the nearest point by default or to the centre if you choose in the Units tab. Inside an area, measuring to it gives the distance to its border (INF-3). "Distance to", a command, opens search and measures to the result without moving (INF-8). Both shells.

Tests first: central London to central Paris is 344 km plus or minus 1, bearing 148 degrees plus or minus 1 (INF-3); measuring to Tokyo from search does not move you (INF-8); in Kent, measuring to Kent gives the distance to its border.

## P3-T8 Search

* Requirements: SRB-1, SRB-2, NAV-8, ACC-9.
* Needs first: P3-T1 and P3-T2 on the trial pack.

Work items:

* P3-T8a The search index in the pipeline (Opus). The English name, the local name and the other names OSM gives in those two (DP172), with accents removed and letters in lower case, in groups of three letters for small misspellings (architecture 7.9). Each feature has an importance from its population, tier and how many Wikipedia languages have it, and a description that tells it apart from others of the same name, such as "Paris, Île-de-France, France". The index is in search records, read only for the first three letters typed, so a search never reads the whole index. Offsets are np.intp, as NumPy in Pyodide is 32-bit.
* P3-T8b Searching in the core (Opus). Matches ranked by how well they match, then importance. Results within 1 second on the desktop (SRB-1); the web figure recorded, and if it is slow, the reasons and a fix. Memory in the browser measured.
* P3-T8c The search dialog (Sonnet). Ctrl+F opens a search field; results appear in a list below as you type, after a short pause, and Down moves into them. Enter jumps: an area zooms to fit, a place keeps the zoom (NAV-8). The results also go into the Search group. Cancel closes it (ACC-7). Both shells.
* P3-T8d Narrowing the search (Sonnet). A choice beside the field: everywhere, inside the current feature, near where you are, or one layer (SRB-2).

Tests first:

* "Sao Paulo" finds São Paulo, and Enter goes there (SRB-1).
* "Paris" lists "Paris, Île-de-France, France" before "Paris, Texas, United States".
* "Pariss" and "londn" find Paris and London.
* "High Street" inside the current feature only finds those inside it (SRB-2, on the test pack's samples).
* A search on the world pack takes under 1 second on the desktop.

## P3-T9 The world tree and browsing by category

* Requirements: SRB-3, SRB-4.
* Needs first: P3-T3e, P3-T8c.

Work items:

* P3-T9a The world tree (Sonnet). The key from your key list opens the world as a tree: World, continents, countries, then their regions and counties, built from the stored containment, read only as each branch is opened. It uses the Information panel's own tree code, so NVDA says the level and position, such as "level 3, 5 of 44" (SRB-3). Enter jumps to the item. Both shells.
* P3-T9b Browse by category (Sonnet). A command, on the map and in the panel, for the current feature: choose a layer, such as Lakes, and every lake in the area goes into the Search group, not limited by zoom (SRB-4).

Tests first: the tree's levels and positions as NVDA would read them, from the core; Europe's countries listed in the tree; "Lakes in Switzerland" lists Lake Geneva.

## P3-T16 Lists of disputed and unclaimed areas

* Requirements: ANN-6, DAT-8, LOC-6. From DP119 and DP120.
* Needs first: P3-T2c, P3-T9b.

Work items:

* P3-T16a (Sonnet). Two entries in the world tree, "Disputed areas" and "Unclaimed areas", and the same two as categories to browse and words to search for, such as "disputed". Disputed areas: the 15 places held twice in OSM, Natural Earth's disputed areas, the West Bank and the Ilemi Triangle. Unclaimed areas: Bir Tawil, the small islands in no country, and any other land in no country. Each item gives its claimants or "no claimant".

Tests first: Crimea, the West Bank and the Ilemi Triangle are in Disputed areas; Bir Tawil is in Unclaimed areas; searching "disputed" lists them.

## P3-T10 The query builder

* Requirements: INF-9.
* Needs first: P3-T3, P3-T8b.

Work items:

* P3-T10a Queries in the core (Opus). Three parts: find (a layer), the relationship (inside, crossing, bordering, or within a distance of), and of what (the current feature, a search result, or later a bookmark). Each is answered from the stored relationships, never by searching every shape; "within a distance of" uses the pack tiles near the feature. The answer goes into the Search group, with a heading such as "Rivers crossing Germany, 24 items". No field names from the data appear (INF-9).
* P3-T10b The form (Sonnet). Q opens three lists and OK and Cancel, in both shells. A distance field appears only for "within a distance of".

Tests first: rivers crossing Germany include the Rhine and the Danube; towns within 10 km of the current feature on the test pack; a query with nothing found says so.

## P3-T11 Look around

* Requirements: SON-4, SON-3, SON-2, SCP-7, NAV-13.
* Needs first: P3-T4a.

Work items:

* P3-T11a The scan (Opus). L plays the Nearby group, in bearing order clockwise from ahead, at most 12 items: each item's layer sound from its direction, then its name and distance in the Alba voice from the same place, then the next. Every item played is in Nearby (SON-4). Any key stops it (P2-T17n). While an item plays, Enter goes to it (INF-10). The core gives the order and each sound's place; each shell plays them one after another on its own sound player. Opus, because it runs in real time against two sound players.
* P3-T11b Layer sounds (Sonnet). A placeholder sound for each layer that has none, such as water, towns and mountains, so items can be told apart by sound, made by tools/make_placeholder_sounds.py. Each can be changed in the layer's settings (SCP-7). You can send your own.

Tests first: the items played are Nearby's first 12 in bearing order; a key stops the scan; Enter during an item goes to that item; only visible features are played.

## P3-T12 Languages of names

* Requirements: ACC-9.
* Needs first: P3-T8a.

Work items:

* P3-T12a Names in the core (Sonnet). The packs hold only the English and the local name (DP172). A setting, "Names: English where there is one, or always the local name", English at first. Everywhere a name is said or shown uses the same function.
* P3-T12b Marking the language (Opus). In the web version, each name has its lang attribute. On the desktop, find out whether NVDA follows a language given by a Qt item, and use it if so; what works is written in Help.

Tests first: with English, Germany is "Germany"; with the local name chosen, "Deutschland"; a place with no English name is said by its local name; in Chromium and Firefox, names carry their lang attribute.

## P3-T13 The pack manager, first version

* Requirements: PCK-2 (first version), PCK-4, PCK-5, DAT-9.
* Needs first: P3-T14b for the real test release; DP171.

Work items:

* P3-T13a The catalogue in the core (Sonnet). catalogue.json read and checked (architecture 6.10): each pack's name, version, date, size, checksum, where it is downloaded from, for the desktop and for the web, and the application versions it works with. The installed packs and their state: installed, not installed, or update available.
* P3-T13b Downloading on the desktop (Opus). On its own thread, in the packs folder (a setting, AD-18), with progress said at most every 10 percent, the checksum checked after, and a damaged download removed and said (PCK-5). The tests use a stand-in for the internet, so no test makes a network connection (rule 5).
* P3-T13c Downloading in the web version (Opus). The pack downloaded whole into the browser's private storage from Hugging Face, while records are read by range requests until it is complete (PCK-4, spike S3). The storage limit checked first, with what is left said. Tested against the local test server in Chromium and Firefox.
* P3-T13d The dialog and first run (Sonnet). P opens the pack manager: a list of each pack's name, size, date and state, with Install, Remove and Close. On first run with no base pack, TobyMap says what it needs and its size, and offers to download it. Both shells. Updates, cancel and resume are Phase 4.

Tests first: a damaged download is found and removed; an incompatible pack is refused with a clear message (PCK-5); installing from the stand-in catalogue puts the pack in the folder and opens it; the web version reads records while a pack is still downloading.

## P3-T14 Quality reports and publishing

* Requirements: DMT-3, DMT-5, PCK-4, DMT-6.
* Needs first: P3-T1; DP171 for publishing.

Work items:

* P3-T14a Quality reports (Sonnet). Every build writes a text report and CSV files, in plain lines a screen reader reads well: repaired shapes, features without names, gaps in coverage, gaps filled by the counties record, matches made by name for Wikidata, size by layer, and the differences from the last build, by feature and by layer (DMT-3).
* P3-T14b The publish command (Opus). `mapdata publish <pack>` puts the pack, its checksum and the updated catalogue on a GitHub release and its copy on Hugging Face, checks the two are identical, and checks every file is under 2 GiB (PCK-4). It asks before each upload and stops if anything differs. Nothing is published without your yes; the first use needs your Hugging Face sign-in.

Tests first: the report lists a feature renamed in the test pack's settings; the publish command, with stand-ins for GitHub and Hugging Face, refuses a pack over 2 GiB and a mismatched copy.

## P3-T18 Controls for sighted users

* Requirements: VIS-1, SCP-2, ACC-2. From DP165, part 2.
* Needs first: nothing.

Work items:

* P3-T18a The status line (Sonnet). A line under the map with the latitude and longitude, zoom, step and facing, updated after every move, from the core's words. It is not in the Tab order and not a live region, so NVDA never reads it by itself.
* P3-T18b Move and zoom buttons (Sonnet). A row of buttons: the four moves, zoom in and out, step larger and smaller. They send the same commands as the keys (AD-3), and are not in the Tab order. A setting in the Display tab hides both, for anyone who does not want them. Both shells.

Tests first: the line says the same as C and H after a step; a button sends its command; neither is reached by Tab; NVDA's reading of the map is unchanged, in Chromium and Firefox.

## P3-T15 Help

* Requirements: DAT-9, ACC-3, SCP-3.
* Needs first: the other tasks, as Help describes them.

Work items:

* P3-T15a The user guide and the key reference (Sonnet). In Help, in both shells: the user guide, covering everything to Phase 3, with headings for each section; the key reference made from the registry, so it is never out of date; the user glossary (UX section 15); and how the continents are divided, with each continent dividing line and where Cyprus and the distant parts of countries go (DAT-12, DP174). Go to's formats, including that a letter first moves and a number first goes to a place (DP173).
* P3-T15b About data (Sonnet). Every source in the installed packs, with its licence and date, from each pack's manifest (DAT-9).

Tests first: every command in the registry is in the key reference; every source in the base pack is in About data.

## The automatic exit checks

From the implementation plan, section 6, and how each is met:

* The Phase 3 acceptance scripts pass on Windows, macOS and the web, including the coverage check of sample places worldwide (DAT-1), Switzerland's five neighbours (INF-2), "Sao Paulo" (SRB-1) and the Bay of Biscay's hierarchy (DAT-4). Also new: Hampshire up to the World, the New Forest's ambiguous up, Contains for Wales, Paris's ranking, London to Paris, Russia and Turkey across two continents, the Alps, the Rhine's countries in order, and France's details.
* The base pack's size is reported against about 400 MB (DP175).
* The base pack is published to the test release and installed from it by the pack manager (DP171).
* Also checked, though not new exit checks: step timing still meets 150 ms for 95% of steps on the base pack (NFR-1); search within 1 second on the desktop; the base pack built twice is identical (DMT-1); the installer installs, starts and uninstalls cleanly in continuous integration.

## Your acceptance checklist

The checklists, docs/checklists/phase-3-desktop.md and phase-3-web.md, are made from the acceptance scripts, as in Phase 2. They will cover:

1. Installing the new version, and the base pack from the pack manager; opening the web version in Firefox.
2. The coverage: a sea, a bay, a strait, a lake, a mountain range and an island, by Go to.
3. Hierarchy mode from Hampshire up to the World, and down into France.
4. The neighbours of Switzerland, in hierarchy mode and in Bordering.
5. Every Information panel group, sorting with Ctrl+S, and typing to jump.
6. Enter and Space on items of every group, the Details region, measuring, and Wikipedia.
7. Search: Sao Paulo, Paris, a misspelling, and narrowing to the current area.
8. The world tree, and listing lakes in a country.
9. The query builder: rivers crossing Germany.
10. Look around, and stopping it.
11. Disputed and unclaimed areas: Crimea, and the two lists.
12. Names in another language.
13. Saying the place after every step (P2-T17q), the voice stopping at a key (P2-T17n), and the four new step sizes.
14. The listening test (P2-T17u), if not already done.

A short checklist for a sighted helper covers the special lines, the selected item on the map, region borders, and the status line and buttons.

## Closing the phase

* The phase report, docs/plan/phase-3-report.md (Sonnet): what was built, how to install it, the checklists, known problems, and what was not tested.
* Continuous integration green on every job before you see it.
* Your feedback recorded against requirement IDs (DEL-4).
* I ask whether to publish, as agreed in DP110. If you agree, the release with the installer, the portable zip and the release notes, the web version on GitHub Pages, and the base pack published with P3-T14b (Opus).

## Risks

* The base pack may not fit about 400 MB with counties, roads and towns (DP175). The size trial shows this before the world build, and you decide with me what goes in (DP169). It is a soft limit, so I ask you before cutting anything you asked for.
* The world build reads much more of the planet file and does far more work than before. Each new stage is tried on the trial region first, the build can stop and carry on with the run switch, and a stall watch runs throughout.
* Joining OSM rivers worldwide is hard: names change, rivers branch and parts are missing. The fall-back is Natural Earth's rivers.
* Wikidata's query service limits how much each client asks for. The stage asks in small batches, waits when told to, and keeps what it has, so a stopped fetch carries on.
* The search index and the relationships make the pack, and the web version's memory, larger. Both are read in records, only as needed; the browser's memory is measured in P3-T8b.
* Identical boundaries within a tolerance (DP71) may join two areas that are not the same, or miss two that are. The quality report lists every pair found, for checking.
* Downloading a pack of 200 MB or more in the web version meets the browser's storage limit, which spike S3 measured. If a browser refuses, the pack manager says so and suggests another browser.
* NVDA may not switch voices from a language given on the desktop (P3-T12b). If not, it is written in Help.
* Hugging Face publishing needs your sign-in once, which only you can do.

## Left for Phase 4

* Street detail, and the Great Britain pack, with national parks, land use and points of interest.
* Every island, named or not, at every zoom (DP87), with the regional packs.
* Pins, bookmarks and collections, and the bookmark action on items.
* The pack manager's updates, and cancelling and resuming downloads.
* Corrections by rule in the pipeline (DMT-4).
