# Phase 1 detailed plan: the walking skeleton

Version 0.1, 3 November 2026. Written by Claude Code for the product owner (PO).

This plan turns section 4 of "implementation plan.md" (version 0.4) into the work for each task, P1-T1 to P1-T16. It follows the architecture (version 0.5), the requirements catalogue (version 0.10), the user experience description (version 0.6), and your answers up to DP108. The tick list of what is done stays in docs/plan/phase-1.md.

## How to read this plan

* "The goal" and "Proposals and questions" are the parts most worth your attention. The questions are new discussion points, DP110 to DP114.
* "Order of work" says what is done when, and "Heavy runs" lists every time the laptop will be busy for a long while.
* Each task has its own level 2 heading, with the same parts in the same order: branch, requirements, what it needs first, what is built, the tests, and when it is done.
* The last sections cover the exit checks, your acceptance checklist, closing the phase, risks, and what is left for Phase 2.

Words follow the glossary. This plan adds five words to it: base pack lite, test pack, drawing level, drawing tile and acceptance script.

## The goal

The whole chain works end to end, at its simplest:

1. The pipeline builds a world pack, the base pack lite, with countries, first-level divisions, oceans and seas, cut to the real coast.
2. The desktop version, installed with the installer, and the web version, in Firefox, both open that pack.
3. You step around the world with the arrow keys in the north-fixed orientation, and hear where you are, what changed, and the tick when nothing changed.
4. You ask where you are, the coordinates and the heading, change zoom and step, and use F1, the key describer, and F2, F3 and F4.
5. The map shows the globe from the same pack, centred on you, with the current country or region outlined.
6. You run the full listening test, and I propose the sound settings from it.

What Phase 1 does not do: turning and the facing orientations, layers you can switch off, crossed and passed, the spatial voice, and spatial sound while moving all come in Phase 2. The Information panel has only two groups, Within and Nearby. The other groups come in Phase 3.

## Proposals and questions

These are my proposals where the documents leave a choice. Each one that needs your decision is a new discussion point in the discussion points file. None of them holds up the early tasks.

### DP110: publishing at the end of the phase

* The phase ends with the first public release (implementation plan 1.5): the installer and portable zip on GitHub Releases, the web version on GitHub Pages, and the base pack lite as a data release, with a copy on Hugging Face for the web (AD-9).
* Proposal: nothing is published until you accept the phase. Your acceptance testing uses an installer built on this laptop and the web version served from this laptop, as in Phase 0. When you accept, I ask you once more, then publish all three together.
* Hugging Face needs you to sign in once on this laptop, for example with `! huggingface-cli login`. I would ask you at that point.

### DP111: earcon files in git

* Rule 10 says sounds are never committed. The placeholder earcons are made by a script, so they need no committing.
* Your own earcons will be small WAV files, a few kilobytes each. Proposal: commit your earcons in a sounds folder, with their source and licence in sounds/CREDITS.md, as an exception for small earcon files only. Voices and other large sounds stay out of git.

### DP112: how detailed the base pack lite is

* Full OSM detail is far too large for the world: spike S2's packs were 38 to 72 MB for just a few countries.
* Proposal: shapes are simplified to about 100 metres. That keeps a point 2 km off Brittany in the sea, keeps the USA under a mile from the Canadian side of Niagara Falls, and keeps small places such as Llívia and Gibraltar. I try 50, 100 and 250 metres on the S2 countries first, and report the size and the check places for each.
* The countries, regions and seas aim for 80 MB or less, leaving the rest of the 250 MB (PCK-1) for what Phase 3 adds.
* If OSM's countries don't fit, or the world build fails, the fall-back is Natural Earth at 1:10 million (DP89). I would ask you before using it.

### DP113: keys not in the draft keyboard map

These commands are Must requirements in Phase 1 but have no key in the user experience description, section 12. Proposals:

* Ctrl+C, in the map: copy the coordinates (LOC-1). Nothing is selected in the map, so copying has no other meaning there.
* Shift+F1: key describer on and off (ACC-3). When it is on, each key says what it would do, without doing it.
* Copy diagnostics (section 10.3 of the architecture): in the Help menu only, with no key.

All are tested with NVDA in both versions before they are fixed, as for every key.

### DP114: places the data gives no name

LOC-6 says no place is ever unnamed. Two kinds of place may have no name in the base pack lite:

* Land in no country that is too big to give to a neighbour, such as Bir Tawil between Egypt and Sudan. Proposal: a short list in the build's settings names each one, such as "Bir Tawil, unclaimed land". The build stops if it finds one not on the list.
* Water that the land polygons treat as sea, but which is in no VLIZ sea, such as the Caspian Sea. Proposal: it takes its name from Natural Earth's lakes, and the build stops if any such water is still unnamed.

Where a country has nothing at level 4, its first-level divisions are filled from level 3 then level 5, the same rule as the counties (DP101), and the build keeps a record of the levels it used. Where nothing fills a gap, you hear only the country, with no region.

### Not a question: what the Information panel holds

The Information panel keeps Within and Nearby in Phase 1, from one group table, so Phase 3 adds the others in one place (INF-10). DP109, about the groups' own keys, can wait: none of those groups exists until Phase 3.

## Order of work

The order in docs/plan/phase-1.md stands, with one change: the core tasks don't wait for the world build. They use a small test pack, built in continuous integration from samples in the repository (architecture 11.1). So the core and the shells move forward while the heavy runs of P1-T16 and P1-T4 happen when you can leave the laptop.

1. P1-T1, geodesy, and P1-T2, the pack format.
2. P1-T3, the pipeline skeleton, ending with the test pack.
3. P1-T16's first part, build speed: the Belgium trials, then mainland France as the regression test. In between heavy runs, work carries on with step 5.
4. P1-T4, the base pack lite: the detail trials (DP112), one continent timed, then the world.
5. P1-T5 to P1-T9, the core's store, stepping, wording, keys and map scene, on the test pack.
6. P1-T10 and P1-T11, the two shells, then P1-T12, earcons, and P1-T13, the listening test.
7. P1-T15, diagnostics, then P1-T14, packaging.
8. The rest of P1-T16: stage 1's whole run and comparison, and stage 4, Argentina.
9. The phase report and your acceptance.

## Heavy runs

Before each one I tell you how long it should take, how many cores it uses and how much memory, as agreed in DP103. One heavy run at a time, and nothing else reads the planet file meanwhile.

* The new planet file: downloading 95.6 GB, which uses the internet connection for some hours but little else, then `gol build`, which keeps the processor and disk busy for some hours.
* Belgium: reading it from the planet file, then each speed trial. Each trial should take minutes, not hours.
* Mainland France, the regression test, after each change kept from the trials: about 10 to 20 minutes.
* The detail trials for DP112, on the S2 countries already built: short.
* One continent, Europe, timed, so the world's time can be estimated (architecture 8.6).
* The world build of the base pack lite: hours, probably with --away and 6 workers, possibly over more than one night. It can stop and carry on.
* The world build again, from its cached steps, to prove the pack comes out byte for byte the same (DMT-1).
* Stage 1's whole run and comparison: about 20 to 30 minutes.
* Stage 4, Argentina: about 15 minutes.

## P1-T1 Core geodesy

* Branch: p1-t1-geodesy.
* Requirements: NAV-1, LOC-1, ANN-5, INF-3, DAT-14.
* Needs first: nothing.

What is built, in mapcore/geo:

* GeographicLib is added to the core (MIT licence, pure Python, so it runs in Pyodide). The licence check is run first (rule 7). If Pyodide doesn't provide it, it is staged with the core like our own files.
* Distance and bearing on the WGS84 ellipsoid (AD-7), replacing the Phase 0 sphere.
* Moving a distance north or south along a meridian, and east or west along a line of latitude (architecture 7.1). A move that would reach or pass a pole is refused, so the caller can play the blocked sound.
* Each move also returns its path, with extra points so it follows the Earth's curve. Phase 2's crossed and passed list uses it.
* Wrapping across the 180 degree line: longitudes, bounding boxes and centres that understand the line (AD-17), and area on the ellipsoid.
* A local projection centred on the location, for quick nearest-point work in P1-T5.
* Formatting, as numbers and words, with no wording of its own: distances in metric, imperial, and nautical miles at sea; bearings as exact degrees, rounded to 5 or 10 degrees, clock face, and 4, 8, 16 or 32 compass points; coordinates in decimal degrees to 5 places, or degrees, minutes and seconds. The words themselves come from the templates (P1-T7).

Tests first, in tests/mapcore:

* London to Paris is 344 km plus or minus 1, bearing 148 degrees plus or minus 1 (INF-3).
* Each ANN-5 example for 47 degrees, including 32 points giving north-east.
* A step east from 179.9 degrees east lands at 179.9 degrees west or so, in Fiji and in the Bering Strait.
* A step north that would pass the North Pole is refused, and so is one south past the South Pole.
* Fiji's bounding box is about 7 degrees wide, not nearly 360, and its centre is in Fiji.
* Every array of positions uses NumPy's own index type, which a test already guards.

Done when the tests pass on Windows, macOS and in the browser tests, and the S2 pipeline's own geodesy uses the same functions.

## P1-T2 Pack format version 1

* Branch: p1-t2-pack-format.
* Requirements: PCK-5, DAT-9, NFR-4 (detection only), and the format for PCK-1.
* Needs first: nothing. It builds on the spike S2 format in mapcore/packs/archive.py.

What is built, in mapcore/packs:

* The byte source interface: read some bytes at a position, and the size. A file source for the desktop, a memory source for tests, and the browser's private storage in the worker (P1-T11). Range requests over the internet come later (PCK-3).
* The records of a pack (architecture 6.2), each compressed:
  * the manifest: the pack's name, version, build date (from the sources' dates, not the clock), coverage, the range of application versions it works with, its sources with their licences and dates, its layers, its tile levels and drawing levels, and how coordinates are stored;
  * the attribution text and the ODbL notice (DAT-9);
  * the layer definitions (SCP-7), with each layer's name, style and default zoom range;
  * feature records, in groups by identifier, holding what architecture 6.4 lists for Phase 1: identifier, source, layer, type in words, names, rank, area, bounding box, width, colour number, a point on its land, and its parents;
  * pack tiles of exact shapes, as in the spike, split at 4,000 points per shape and 20,000 per pack tile (AD-5);
  * drawing tiles: simplified shapes for each drawing level (architecture 6.9).
* A check number for every record, so a damaged record is found when it is read (NFR-4), and a checksum for the whole file, kept beside it and later in the catalogue (PCK-5).
* Version checks: a pack made for other application versions is refused with a clear message from the templates (PCK-5). The spike packs are recognised; mapdata inspect still reads them, and the application refuses them politely.
* The specification, docs/developer/pack-format.md.

Tests first:

* Writing then reading every kind of record gives back what was written.
* A pack with one damaged byte reports which record is damaged, and the rest can still be read.
* A pack for a later application version is refused with the approved message.
* The same input written twice gives identical bytes (DMT-1).
* Reading uses only the byte source, so the same reader runs in the browser tests.

Done when the tests pass everywhere and the format document is written.

## P1-T3 Pipeline skeleton

* Branch: p1-t3-pipeline.
* Requirements: DMT-1, DMT-2, DMT-6, DMT-7 (in part), DAT-9.
* Needs first: P1-T2.

What is built, in mapdata:

* `mapdata check`: says whether the data folder can be reached and stops before any work if it can't (DMT-7); reports free space in its folders; lists the planet file and the land polygons with their dates, and warns if their dates are far apart.
* `mapdata fetch`: downloads a source named in the sources file, or reuses a local copy, one plain line per source and a summary.
* `mapdata build <pack>`: runs the stages named in the pack's settings file.
* Settings files: mapdata/config/sources.yaml (address, licence, attribution, refresh interval), mapdata/config/layers/ (one file per group of layers), and mapdata/config/packs/ (one file per pack). A source with no licence stops the build and says which (DMT-6).
* Stage caching (architecture 8.3): each stage's results are kept in the working folder, named by a fingerprint of its inputs, settings and code version, and a stage is skipped if nothing changed.
* Plain progress lines, at most one every 10 seconds, a summary at the end, and the full log in a text file beside the pack (DMT-2). Errors name the source, the feature, and what to do next.
* A record of every file the pipeline creates, so it never deletes or overwrites anything else (DMT-7).
* `mapdata inspect` gains: the manifest, one feature by identifier, and what is at a point, all in plain lines.
* The spike S2 code is moved into proper stages one at a time, with its tests kept passing. The spike commands stay until P1-T16 is finished.
* The test pack: tests/samples/ holds small samples, built into a pack in continuous integration (architecture 11.1). Natural Earth's world, VLIZ's oceans for the Atlantic, and small OSM-based samples, from spike S2's cached shapes, for: England, France and the Channel; the Isle of Wight and the Solent; Fiji either side of the 180 degree line; the Bering Strait; Antarctica near the South Pole; and Niagara Falls. The OSM samples carry the ODbL notice. Together they stay under a few megabytes.

Tests first:

* A source with no licence stops the build with a message naming it.
* A second build with nothing changed skips every stage.
* Progress lines are never closer than 10 seconds apart.
* The test pack built twice is identical, byte for byte (DMT-1).
* No path in the code or the shared settings has a drive letter (AD-18), and nothing is written outside the data folder's tobymap folder.

Done when continuous integration builds the test pack on every push, and the data manager's guide is started in docs/data-manager/guide.md, with the configuration reference in docs/data-manager/configuration.md.

## P1-T16 Carried over from spike S2

* Branch: p1-t16-build-speed for the speed work; p1-t16-stage-checks for the rest.
* Requirements: DMT-7, DAT-3, DAT-14, ANN-6 (the dispute is kept for Phase 3's details).
* Needs first: P1-T3.

### Part 1, before the world build (DP107)

A newer planet file, asked for by the PO on 3 November, so the planet and the land polygons have close dates:

* The planet files on drive E: are from October 2025, but the land polygons were downloaded on 31 October 2026. The newest planet file is dated 26 October 2026, 95.6 GB.
* It is downloaded into the data folder's tobymap\downloads folder, with its checksum checked, and turned into a GeoDesk library with `gol build` and `--waynode-ids`, as for the existing ones. The library will be about 140 GB. Together they need about 235 GB of the 743 GB free.
* The existing planet files are kept and never touched.
* Mainland France's regression test still uses the October 2025 planet file, so any difference is from the method, not from a year of OSM edits. Belgium's trials, the base pack lite and stage 4 use the new one.

The way countries are built and kept:

* The planet file is read once, in its own short-lived process, and every country is built from that same read. A new planet file rebuilds every country.
* Each country is built and kept on its own in the working folder, under a fingerprint of the planet file, its settings and the code. A change for one country rebuilds only that country.
* After a country is rebuilt, the check that neighbours meet exactly (AD-16) runs again on its borders. A neighbour whose border no longer matches is rebuilt too.
* Each step works only on the parts near what it is working on, found through a spatial index, never on a whole country or a whole gap at once.

The speed trials:

* Belgium is the trial dataset, with counties at levels 6, 7 and 8.
* Each slow step is timed first, then at least two approaches are tried, and the fastest that gives the right result is kept. The work stays spread over cores, but the aim is a faster method, not more cores.
* The counties step comes first. Approaches to try:
  1. Finding which level 7 and 8 areas are outside every level 6 area by testing a point on each one's land against level 6, which is quick, and measuring only the few that cross a level 6 border.
  2. Measuring each area only against the parts of the gap near it, after dropping strips of the gap under a set size, as the S2 findings suggest.
  3. Working one region at a time, so a gap is never the whole country's.
* Then the other slow steps from stage 3: checking that neighbours meet, finding land in no division, and writing packs. Each gets its own trials if it is still slow on Belgium.
* Mainland France, without its overseas territories, is the regression test: after each change that is kept, it must give the same results as on 1 November, checked with the comparison program.
* Every trial's times and results go into the S2 findings, in a new section "Phase 1: build speed trials", so you can see which approach was chosen and why.

Also before the world build, because the base pack lite needs them:

* Areas held twice in one layer, such as Sevastopol (DP104): the build lists them, keeps the one in the country whose outline holds it, marks it disputed, and keeps the other's name and country for its details.
* The area check takes away the inland water mapped in OSM before comparing a country's land with Wikidata's figure, and reports the water separately. Countries whose difference is explained, such as Fiji, are listed in the settings with the reason.
* The overlap check also finds one area wholly inside another.
* The globe check looks only at edges near the 180 degree line, so Alaska's straight border is no longer flagged.

### Part 2, when the laptop can be left

* Stage 1 again, the UK, France and Spain: the whole run, compared with 1 November using `mapdata spike-s2-compare`.
* Stage 4, Argentina: Tierra del Fuego shared with Chile, the Andes border, the undecided border on the Southern Patagonian Ice Field, and the Falkland Islands. Bolivia's and the Falklands' names are checked against OSM first.
* Antarctica: which definition Wikidata's area uses, its own expected figure, and the cause of the 78 km of edge along the 180 degree line on one side only.

Done when the trials are written up, mainland France matches 1 November, the four checks above are in the build with tests, and stage 1's comparison and stage 4 are reported.

## P1-T4 Base pack lite

* Branch: p1-t4-base-lite.
* Requirements: LOC-6, DAT-3 (the base coastline), DAT-14, DAT-9, DMT-1, PCK-1 (measured), AD-16, AD-19.
* Needs first: P1-T3 and part 1 of P1-T16.

The layers:

* Countries: OSM level 2, with the country units list (French Guiana and the others) and Gibraltar on its own, cut to the land.
* Regions: the first-level divisions, OSM level 4, with gaps filled as in DP114.
* Oceans and seas: VLIZ Global Oceans and Seas (CC-BY 4.0), with the land taken away, and any sea next to the coast that VLIZ leaves out given to the nearest sea.
* Land: the OSM land polygons, used to cut everything else, and as the fall-back for land in no country (DP114).

What the build does, country by country as P1-T16 sets up:

* Repairs open outlines and invalid shapes (AD-15), and lists each repair.
* Cuts to the land, cleans each layer as one coverage, simplifies the regions once at the base detail (DP112), and makes the countries by joining their regions, so the two levels meet exactly (AD-16).
* Works out each area's colour number, so no neighbours share one (AD-19), its width, its area on the ellipsoid, its bounding box across the 180 degree line, and a point on its land (architecture 6.13).
* Writes the drawing levels, leaving out parts too small to see at each, so each frame stays near 10,000 points (architecture 6.9).
* Writes the pack in the P1-T2 format, with its attribution and checksum.

The checks, written to the build's report:

* No gaps: a grid of points over the whole Earth, every quarter of a degree, plus every S2 check place: each one has a name (LOC-6). 30 north 40 west is the North Atlantic Ocean, and 80 south 30 east is Antarctica.
* The S2 check places from all three stages, at base detail. A place that needs full detail, such as a rock in the Solent, is marked as a check for regional packs instead, with the reason.
* The antimeridian checks for Fiji, Russia, the USA, Kiribati and Antarctica (DAT-14), with the area check from P1-T16.
* The size of each layer, against the target in DP112.
* Built twice, from its cached steps, the pack is identical (DMT-1).

The order:

1. The detail trials for DP112, on the S2 countries already built.
2. Europe, timed, so the world's time can be estimated. I tell you the estimate before the world build.
3. The world.

Done when the pack passes its checks, its report is written for you, and its size is reported against 250 MB. If OSM's countries don't fit, DP112's fall-back is raised with you before anything changes.

## P1-T5 Store and "where am I"

* Branch: p1-t5-store.
* Requirements: LOC-2, LOC-6, INF-3, INF-7 (Phase 1 part), NFR-1, NFR-4.
* Needs first: P1-T1, P1-T2 and the test pack.

What is built, in mapcore/store:

* One store over the installed packs. Phase 1 has one pack, but the store is written so Phase 4 can add pack tile coverage and the most detailed pack wins (AD-14).
* "What is at this point": every area at the point from every layer, whatever the zoom (ANN-7), ordered by rank, then smallest first (LOC-2).
* The pack tile cache: decoded shapes kept in memory, up to a size limit, with the pack tiles around the location read in advance in the background (architecture 10.1).
* Feature records by identifier.
* Nearest point (INF-3, INF-7): for the location and a radius, each area within the radius with its nearest point, its distance and its bearing. Candidates come from bounding boxes, the nearest point is found with the local projection from P1-T1, and the final distance and bearing are measured on the ellipsoid. Exact shapes are used for areas within about 50 km; drawing shapes for areas further away, where the difference is far smaller than the distance.
* A damaged record is reported, and the store carries on without it (NFR-4).

Tests first:

* At 43.08 north 79.08 west, on the Canadian side of Niagara Falls, the USA is under 1 mile away, to its nearest point (PO's Phase 0 feedback).
* The test pack's places give the right areas, in the right order, including either side of the 180 degree line and at the South Pole.
* Nearby for the 20 nearest areas comes back within 1 second (INF-7).
* A lookup with the pack tile cache filled takes a few milliseconds; the time with nothing cached is recorded.

Done when the tests pass in the desktop and browser tests.

## P1-T6 World model and stepping

* Branch: p1-t6-stepping.
* Requirements: NAV-1, NAV-2, NAV-13 (the zoom list and keys), LOC-7, ANN-3, PLT-5 (the location part).
* Needs first: P1-T1 and P1-T5.

What is built, in mapcore/world and mapcore/navigation:

* The world state: location, heading (always north in Phase 1), zoom, step, the link between them, orientation and movement mode, kept ready for Phase 2.
* The zoom list from 100 m to 10,000 km and the step list from 10 m to 1000 km (NAV-2, NAV-13), from mapcore/defaults.yaml, so settings can change them.
* Zoom keys and step keys. "Link step to zoom", off by default: when it is on, changing one sets the other, a step of a quarter of the zoom (NAV-2).
* North-fixed stepping: Up and Down along the meridian, Left and Right along the line of latitude, wrapping across the 180 degree line, and blocked at the poles with the blocked sound and nothing spoken (NAV-1).
* Each move returns where it went, its path and the heading on arrival.
* When moves arrive faster than they can be handled, they are joined and all carried out, and only the last place is described (ANN-3). This joining is in the core already, from spike S5, and is kept.
* The world state can be saved and restored, so the shells bring back the last place, zoom and step on restart (PLT-5).

Tests first: every NAV-1 and NAV-2 example, including the pole and the 180 degree line, the link both ways, and ten joined moves describing only the last place.

## P1-T7 Describe

* Branch: p1-t7-describe.
* Requirements: ANN-1, ANN-4, ANN-5, LOC-1, LOC-2, LOC-7, INF-3, INF-7, NFR-5.
* Needs first: P1-T5 and P1-T6.

What is built, in mapcore/describe:

* Change detection (ANN-1): after a move, the new smallest area if it changed, then any larger areas that changed, from smallest to largest. If nothing changed, only the tick.
* Space, "where am I": the smallest area and its parents. With countries and regions only, that is, for example, "England, United Kingdom".
* C, the coordinates, in the chosen format (LOC-1), and Ctrl+C to copy them (DP113).
* H, the heading, orientation, movement mode, zoom and step, for example "Facing north. North-fixed. Stepping. Zoom 5 kilometres, step 250 metres." (LOC-7).
* Zoom and step announcements, such as "Zoom 1 kilometre, step 250 metres" when linked.
* Repeat (Ctrl+Space) and the announcement history (Ctrl+Shift+Space), holding at least the last 50 (ANN-4).
* Units and bearing formats as settings (ANN-5).
* Nearby's items: each area with its distance and bearing to its nearest point, in the chosen units and bearing format.
* Every word comes from mapcore/describe/templates.yaml, and menu, dialog and help words from mapcore/strings.yaml (architecture 3.4).
* Acceptance scripts, in tests/acceptance: each is a small file of key presses and the expected announcements, tied to requirement IDs. The same file runs as an automatic test, and tools/make_checklists.py turns it into your checklist, docs/checklists/phase-1.md (architecture 11.3). The approved wording is kept in tests/acceptance/approved.

The first acceptance scripts:

* Across the Channel from England to France, then out into the Atlantic.
* Across the 180 degree line in Fiji, and in the Bering Strait.
* Blocked at the North Pole.
* Zoom and step changes, linked and not.
* Where am I, coordinates in both formats, and heading.
* Nearby at Niagara Falls.

Done when the scripts pass against the test pack, and you have approved the wording through the checklist. Any wording you change goes back into the templates and the approved files.

## P1-T8 Command registry and session

* Branch: p1-t8-commands.
* Requirements: SCP-2, ACC-2, ACC-3, ACC-4, ACC-7, NAV-1, NAV-2, NAV-13, SON-7.
* Needs first: P1-T6 and P1-T7.

What is built, in mapcore/commands and mapcore/session.py:

* The Phase 1 commands, each defined once in the registry (AD-3):
  * Arrow keys: step north, south, west and east.
  * Page Up and Page Down: zoom out and in. Shift+Page Up and Shift+Page Down: larger and smaller step. "Link step to zoom" in the menu.
  * Space, C, Ctrl+C, H, V, Ctrl+Space and Ctrl+Shift+Space.
  * F1: the commands for the focused region, each with its key (ACC-3). Shift+F1: the key describer (DP113).
  * F2 to the map, F3 to the Information panel, and F4 to Details, from any region (DP106). F3 goes back to the item last focused there, or to Within's first item the first time. Which item that was is kept by the core, so both shells behave alike.
  * Ctrl+Alt+M, web only, to the menu bar.
  * Ctrl+comma: settings. Ctrl+M: mute all of TobyMap's sound (SON-7).
  * Help menu: keys, about, about data (DAT-9), and copy diagnostics.
* Dropped: Shift+Space, D, R and Ctrl+Alt+Space (DP106), and the Phase 0 globe-turning commands.
* Key remapping: assigning a key that is in use warns you and names the command that has it (ACC-3). Your keys are saved with your settings.

Tests first:

* Coverage (SCP-2): every command has a key or a menu entry.
* Screen reader keys (ACC-4): no default key uses the NVDA or JAWS key as a modifier, Control+Option, Escape in the web version, Alt alone, F10, or a browser key a page can't override, such as Ctrl+T, Ctrl+N, Ctrl+W, or Ctrl+1 to Ctrl+9. The list of forbidden keys is a file in the tests.
* Browser tests in Firefox and Chromium: the page receives F1, F2, F3 and F4, and stops the browser using them. F3 is "find again" in browsers, so this matters.
* Remapping to a key in use gives the warning with the other command's name.

## P1-T9 Map scene

* Branch: p1-t9-map-scene.
* Requirements: VIS-1, VIS-4, VIS-5, NAV-9, NAV-13, SCP-2, DAT-14, INF-10 (the highlight).
* Needs first: P1-T5 and P1-T6.

What is built, in mapcore/render:

* The globe from the pack's drawing tiles, with the drawing level chosen for the zoom, so a frame stays near 10,000 points (VIS-1, 100 ms).
* Each area filled by its colour number, so neighbours differ (AD-19), with a thin outline. The current area has a thicker outline, and the item selected in the Information panel is highlighted.
* The centre cross, which can be switched off (VIS-1), and the heading arrow at the centre (LOC-7).
* Artificial edges are filled but never outlined, so Fiji and Russia draw whole across the 180 degree line (AD-17).
* Mouse and touch: a click moves the location there and gives the normal announcement (NAV-9); the wheel and a pinch change the zoom to the nearest in the list, and it is announced (NAV-13); dragging turns the globe and moves the location with it (VIS-4). Announcements when the mouse hovers are off by default, with a setting to turn them on.
* The zoom is a distance, so a smaller window draws smaller but shows and hears the same area (DP76).
* Every layer drawn is a layer that "where am I" uses, so nothing is drawn that can't be found without sight (SCP-2).

Tests first: the number of points in a frame at each zoom, Fiji and Chukotka with no outline along the line, a click giving the same announcement as stepping there, and the area in view staying the same when the window size changes.

## P1-T10 Desktop shell

* Branch: p1-t10-desktop.
* Requirements: ACC-1, ACC-2, ACC-3, ACC-7, ANN-3, INF-10, PLT-1, PLT-2, PLT-5, SCP-1, NFR-1, NFR-2.
* Needs first: P1-T7 to P1-T9.

What is built, in desktop:

* The four regions, as in the user experience description, section 2: the map, the Information panel, Details and the menu bar. Tab moves round the first three; Alt goes to the menu bar, where Tab moves along the menus and Alt or Escape leaves it.
* The announcer, one queue for all speech (ACC-1).
* The map widget, painting the core's shape list.
* The menu bar, built from the registry.
* The Information panel, with Within and Nearby:
  * NVDA is told each item's level, such as "level 2" (INF-10).
  * Items are changed in place, never rebuilt, so NVDA reads the item F3 moves to without Up then Down (the Phase 0 known problem).
* Details: the current area's name, type, its parents and its source (DAT-9).
* The settings dialog, with tabs for units, movement, sound, display and keys. What is in it comes from the core, so the web version shows the same. It has OK and Cancel buttons (ACC-7). Settings are saved as JSON in your own application data folder, can be exported and imported (PLT-5), and the last place, zoom and step come back on restart.
* The history dialog, the key help, and "about data", each with a Close button.
* A stand-in sound player that plays the earcon WAV files, with mute. Spatial sound comes in Phase 2.
* The pack folder is a setting, by default in your application data folder (AD-18).
* No backlog after a held key (ANN-3): while an arrow key is held, the moves are all made but speech is held back; when the key is let go, only the latest place is spoken, and it interrupts anything the screen reader was still saying.

Tests first, with no window shown and no sound played:

* Holding an arrow key for 2 seconds, then letting go: after the release, nothing but the final place is spoken.
* The panel's items report their levels, and keep their identity when refreshed.
* F2, F3 and F4 from each region land where they should.
* Every dialog has a Close or Cancel button.
* Settings saved, then the application started again, gives the same settings and place.
* Nothing in the code asks for the computer's location (SCP-1).
* Start-up to the first announcement is timed against 10 seconds (NFR-2), and a step from key press to announcement against 150 ms (NFR-1).

## P1-T11 Web shell

* Branch: p1-t11-web.
* Requirements: PLT-3, ACC-1, ACC-2, ACC-7, ANN-3, INF-10, PLT-5, SCP-1, NFR-1.
* Needs first: P1-T10, so the two shells are built from the same core answers.

What is built, in web:

* The same four regions and behaviour, with the core in a Pyodide worker (AD-9): the key map, focus, the announcer (ariaNotify, with live regions as the fall-back), the canvas painter, the menu, and the settings, history, key help and "about data" dialogs, each with a Close button.
* The pack is loaded from the site for now. On the first visit it is downloaded whole into the browser's private storage, with progress announced at most every 10 seconds, and read from there afterwards.
* Settings are kept in the browser, and can be exported to a file and imported.
* Earcons play through Web Audio.
* The held key behaviour (ANN-3), using the browser's own signal for a repeated key and the key's release.
* The tree builds each item with its words inside it, as Firefox needs (spike S5), and tells the screen reader each item's level.

Tests first, in Chromium and Firefox:

* The held key test, as on the desktop.
* F2, F3 and F4, and Ctrl+Alt+M to the menu bar.
* The tree's levels and real focus on its items.
* An automatic accessibility check of the page with axe-core (MPL-2.0, a test tool only, after the licence check), as a first check against WCAG 2.2 AA (ACC-7).
* Nothing in the page asks for the location (SCP-1).
* The time of "where am I" and of a step, recorded for the web figure in the exit checks.

## P1-T12 Earcons

* Branch: p1-t12-earcons.
* Requirements: SON-7, SON-8, NFR-1 (earcons within 50 ms).
* Needs first: P1-T10 and P1-T11 for playing them.

What is built:

* tools/make_placeholder_sounds.py makes a short, distinct tone for every earcon event in SON-6, into the sounds folder. Phase 1 uses two: the tick and the blocked sound. The others are ready for Phase 2.
* Your own tick and blocked sounds replace the placeholders when you send them (DP111).
* sounds/CREDITS.md records each sound's source and licence (SON-8).
* A setting for each earcon to use your own WAV file. If the file can't be played, the default plays and you are told (SON-8).
* The earcons and their file names are listed in Help (SON-8).
* Earcons play at the same time as speech, never before or after it (SON-7), and start within 50 ms (NFR-1).

## P1-T13 Listening test tool

* Branch: p1-t13-listening-test.
* Requirements: SON-1, SON-9 (the curve).
* Needs first: P1-T12.

What is built, in tools/listening_test:

* The distance curve goes into the core, in mapcore/sound, as settings (SON-9): full loudness at one twentieth of the zoom or closer, each doubling of distance equally quieter, quiet at the edge, and the "beyond the view" level. Phase 2's sound scene uses the same code.
* The desktop sound processing from spike S1 moves into desktop/audio: stereo with pitch, and HRTF with pitch (AD-10).
* The tool is a small accessible window. Space plays a sound from a random direction and distance. You answer the direction by typing a clock hour, 1 to 12, then Enter, and the distance from 1, very near, to 5, beyond the view. R plays it again, and 0 means "can't tell". It has a Close button.
* The test is in blocks, each with its own instructions spoken at the start:
  1. Stereo with pitch, the default.
  2. HRTF with pitch.
  3. Beyond the view: the quiet, muffled sound against the fixed tone alternative (SON-9, DP80).
  4. A short block with a sound playing while your position steps past it, then you say where it ended (sound while moving).
  5. A short block of Piper labels, such as "Berlin", from behind: no pitch change, a lower pitch, or a short tone before the label. This tries how the pitch cue works with speech (AD-10).
* Every answer is written to a CSV file in docs/spikes/listening-test, with the direction and distance played and heard.
* A short web version of blocks 1 and 3, in Firefox, so the browser's sound can be compared with the desktop's by ear, which spike S1 didn't do.
* An analysis script: the share of answers within 45 degrees (the target is 80%), front and back confusions, how well the distance answers follow the distance played, and how often "beyond the view" was recognised. It writes its findings for you, with the settings I propose.

## P1-T15 Diagnostics

* Branch: p1-t15-diagnostics.
* Requirements: the architecture's section 10.3; it helps DEL-4.
* Needs first: P1-T10 and P1-T11.

What is built:

* A test trace in the core: every command, every announcement, every earcon, and the time each took. The shells add when the key was pressed and when the text was handed to the screen reader.
* "Copy diagnostics", in the Help menu: the last few minutes of the trace go on the clipboard as plain lines, one per event, ready to paste into your feedback. It also gives the version, the pack and the settings.
* Nothing in the trace leaves the computer unless you paste it (SCP-1, section 10.4).

Tests first: the trace keeps only its time limit, and the copied text is plain lines in the order things happened.

## P1-T14 Packaging

* Branch: p1-t14-packaging.
* Requirements: DEL-5, PLT-1, PLT-2, PLT-3, SCP-4.
* Needs first: every other task, apart from part 2 of P1-T16.

What is built:

* The Windows installer and portable zip, extended from Phase 0's: the application, the earcons, and the base pack lite. Installed for the current user, with no administrator prompt (DP95).
* In continuous integration on Windows: the installer is built, installed silently, started in a self-test that opens the test pack and asks "where am I", then uninstalled, and the folder checked empty.
* The web version: a GitHub Pages workflow, ready but not switched on until DP110 is answered and the phase is accepted.
* The third-party notices updated, with GeographicLib, VLIZ, OSM, Natural Earth and the sounds (SCP-4).
* Release notes, docs/release-notes.md: what changed, what was tested with which screen readers and browsers (DEL-4), and the differences between the desktop and web versions (PLT-3), which also go in Help.
* The version becomes 0.1.0 for the build you accept. The first GitHub release is made then.
* macOS keeps its automatic tests on every push, with no download (AD-20, PLT-2).

## The automatic exit checks

From the implementation plan, section 4, and how each is met:

* The Phase 1 acceptance scripts pass on Windows, macOS and the web: they run in continuous integration against the test pack, and on this laptop against the base pack lite.
* The step announcement is ready within 150 ms for 95% of steps on the desktop, on the base pack lite (NFR-1): tests/performance runs a walk of 1,000 steps round the world and reports the median, the 95th percentile and the slowest. The web figure is recorded from the same walk in Firefox and Chrome.
* Building the base pack lite twice gives an identical file (DMT-1): checked on the world build from its cached steps, and on the test pack on every push.
* The antimeridian tests pass, in the core, the store, the map scene and the acceptance scripts.
* The installer installs, starts and uninstalls cleanly on a Windows machine in continuous integration.

## Your acceptance checklist

The checklist, docs/checklists/phase-1.md, is made from the acceptance scripts, with headings for each part. It will cover:

1. Installing the desktop version with the installer, and opening the web version in Firefox.
2. Stepping across the Channel from England to France, then out into the Atlantic.
3. Stepping across the 180 degree line in Fiji.
4. Being blocked at the North Pole: the blocked sound, nothing spoken.
5. Changing the zoom and the step, with and without "link step to zoom".
6. Where am I, the coordinates in both formats, copying them, and the heading.
7. F1, the key describer, and changing a key, including the warning when it is taken.
8. F2, F3 and F4 from each region. On the desktop, Alt and Escape leaving the menu bar, and Tab moving along its menus.
9. Holding an arrow key and letting go: only the last place is spoken (ANN-3).
10. The Information panel: NVDA says each item's level, and reads the item F3 lands on (INF-10).
11. Nearby at Niagara Falls: the USA under a mile away.
12. Repeat and history, the tick and blocked sounds, and mute.
13. Settings kept after closing and opening again.
14. Braille: the announcements on your display or NVDA's Braille viewer (ACC-1).
15. The full listening test.

The same parts are tried in Chrome as well as Firefox if you have time, since Chrome with NVDA was not tested in Phase 0.

## Closing the phase

* The phase report, docs/plan/phase-1-report.md: what was built, how to install it, the checklist, known problems, and what was not tested (implementation plan 1.5).
* Continuous integration green on every job before you see it.
* Your feedback recorded against requirement IDs (DEL-4).
* When you accept: the GitHub release with the installer, the portable zip and the release notes; the web version on GitHub Pages; and the base pack lite as a data release with its Hugging Face copy, as DP110 decides.
* The listening test analysis, and the sound settings it proposes, ready for Phase 2.

## Risks

* The world build may be slow, or need more memory than the laptop has. The timing run on Europe comes first, every step can stop and carry on, and nothing is started without telling you.
* The base pack lite may be too big at the detail wanted. DP112's trials measure it before the world build, and Natural Earth is the fall-back.
* VLIZ's file may need a form filled in to download it. If so, I ask you to download it into the data folder's tobymap downloads folder, and the build reads it from there.
* Holding back speech during a held key depends on how NVDA treats Qt's announcements. If the automatic test passes but NVDA still falls behind, the trace from P1-T15 shows where, and the fix is tried again before the checklist.
* F3 in browsers: if a browser won't give it up to the page, the browser tests will show it, and I would raise it with you before choosing another key.
* GeographicLib in Pyodide: if it isn't provided, it is staged with the core, as it is pure Python.

## Left for Phase 2

* Orientations, turning, and stepping over the poles.
* Layers you can switch off, and the full visible rule.
* Crossed and passed, using the paths each move already returns.
* Spatial sound, the spatial voice, the beacon, and all the earcons in use, tuned from the listening test.
* Verbosity, and the concise Braille format.
* The themes, and the map display setting for outlines and fill (DP108).
