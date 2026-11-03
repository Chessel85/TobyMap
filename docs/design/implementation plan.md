# Implementation Plan

Version 0.4, 3 November 2026.

## Changes in version 0.4

These changes come from your answers to DP106 to DP108.

* P1-T8: F2 goes to the map, F3 to the Information panel and F4 to Details, from any region, on the desktop and the web (DP106). Shift+Space, D, R and Ctrl+Alt+Space are dropped. Ctrl+Alt+M stays, in the web version only, for the menu bar.
* P1-T16: no time limits. For each slow step of the build, at least two approaches are tried on a small dataset, Belgium, and the fastest is kept. Mainland France is the regression test. Every country is built from the same planet file, and neighbours are checked again after any country is rebuilt (DP107).
* P2-T12: the map display setting for outlines and fill, as recommended (DP108).
* A new task list for the phase: docs/plan/phase-1.md.

## Changes in version 0.3

These changes come from your acceptance of Phase 0 on 3 November. Each is recorded against its requirement in the Phase 0 report.

* P1-T5 and P1-T7: distances in Nearby go to the nearest point of each area, not its label point (INF-3, INF-7). At the Canadian side of Niagara Falls, the USA is under a mile away.
* P1-T8: keys that move to each region from any region (ACC-2, DP106; settled in version 0.4).
* P1-T10 and P1-T11: when a held arrow key is let go, no backlog of places is spoken (ANN-3). On the desktop, the Information panel tells NVDA each item's level, as well as reading the item it moves to (INF-10).
* P1-T16: an agreed approach for building countries, regions and counties quickly (DMT-7, DP107), before the world build.
* P2-T7: the first label from the voice is heard, in the web version too.
* P2-T12: a map display setting for outlines and fill colours (VIS-2, DP108).
* Phase 1's checklist confirms that, on the desktop, Alt or Escape leaves the menu bar, and Tab moves along its menus, as in other Windows programs (ACC-2).

## Changes in version 0.2

* Phase 0 now has six spikes. S2 is the countries, coastlines and islands spike on the UK, France and Spain, then Sweden and Norway, then the antimeridian countries ("architecture thoughts.txt"). S6 compares spatial voices (DP82).
* Phase 0 builds a Windows installer for the empty shell, and the installer is part of every phase after that (AD-20). Mac downloads wait until a Mac tester is found (DP92).
* There is no public preview stage (DP85). Each accepted phase from Phase 1 produces a GitHub release. You decide when to invite others.
* The repository is TobyMap (DP84).
* At the start of every phase, Claude Code checks for newer PySide6 and Pyodide releases and upgrades if the tests pass.
* The pipeline's data folder is a setting, never a fixed drive letter (AD-18).
* Web tests and your web checks use Firefox as well as Chrome.
* Antimeridian tests are added to Phase 1, country units and islands to Phases 3 and 4, and neighbour colours to Phase 2.

This plan is written to be followed by Claude Code, phase by phase, with the product owner (PO) testing at the end of each phase. It builds on "architecture.md" (decisions AD-1 to AD-20), "requirements catalogue.md" version 0.7 and "user experience description.md" version 0.6. The list of things the project produces is in "artefacts.md".

## How to read this plan

* Section 1 gives the working rules that apply to every task.
* Section 2 lists the phases in one place.
* Sections 3 onwards describe each phase. Each phase has a goal, the requirements it delivers, its tasks, its automatic exit checks, and the PO's acceptance gate.
* Each task has an ID, such as P2-T4, so feedback and commits can refer to it.

There are no deadlines (DP37). A phase ends when its gate is passed, not on a date.

---

## 1. Working rules for Claude Code

### 1.1 Before starting a task
* Read the repository's CLAUDE.md, then the design documents for the area being changed.
* At the start of a phase, check for newer releases of PySide6 and Pyodide. Upgrade if the full test suite passes, and note the change in the phase report.
* Read the requirements listed against the task, including their acceptance criteria.
* If a requirement is unclear or seems to conflict with another, add a discussion point to the discussion points file and ask the PO, rather than guessing.

### 1.2 How each task is done
1. Create a branch named after the task, such as "p2-t4-crossed-and-passed".
2. Write or extend the tests first, including acceptance scripts where the task changes what the user hears.
3. Implement the change, keeping all logic in the core (AD-1). Shells only translate keys and responses.
4. Run the whole test suite locally. Continuous integration must pass on Windows, macOS and the web before merging.
5. Update the documentation the task affects: CLAUDE.md, the docs folder, Help, and the key reference if keys changed.
6. Merge to the main branch with a commit message naming the task ID and the requirement IDs.

### 1.3 Rules that are never broken
* No logic is copied between the desktop and web shells. If both need it, it moves into the core.
* Every command is defined in the command registry. No shell adds its own key handler for a command.
* No announcement text is written in a shell. It comes from the core's templates.
* Tests never open a window, an audio device or a network connection.
* Escape is never required. Every dialog has a Close or Cancel button.
* No dependency is added without checking that its licence is compatible with GPL-3.0.
* Nothing in the data folder (drive E: on the PO's laptop) is deleted or overwritten unless the pipeline created it. The PO is asked before anything else is deleted (DP75).
* No drive letter or personal folder is written into the code or the shared configuration (AD-18).
* Large binary files, such as packs, sound sources and voices, are never committed to the repository.

### 1.4 Definition of done for a task
* The tests for its requirements pass, and the announcement baselines are approved.
* Continuous integration is green on all three targets.
* The documentation is updated.
* The task is ticked off in the phase's task list in the repository.

### 1.5 Definition of done for a phase
* Every task is done.
* The automatic exit checks pass.
* A phase report is written for the PO: what was built, how to install it, the acceptance checklist, known problems, and what was not tested.
* From Phase 1, the accepted build is published as a GitHub release, with the Windows installer, the portable zip and release notes, and the web version is updated (DP85).
* The PO has run the acceptance checklist with NVDA and accepted the phase, or the problems found are fixed and checked again.
* PO feedback is recorded against requirement IDs (DEL-4).

### 1.6 How the PO gives feedback
* Free-form text files, or new rows in the discussion points file, as now.
* A "copy diagnostics" trace from the application (architecture section 10.3) can be pasted into the feedback, from Phase 1 onwards.

---

## 2. The phases at a glance

* Phase 0: Foundations and spikes. Set up the repository and the installer, and answer the six technical questions, above all how to build countries, coastlines and islands.
* Phase 1: Walking skeleton. Step around a simple world in both desktop and web, hear where you are, see the globe, and run the listening test.
* Phase 2: Orientation, layers and sound. The three orientations, turning, layers, earcons, spatial sound, the beacon, and the crossed and passed list.
* Phase 3: Information, hierarchy and search, with the complete worldwide base pack.
* Phase 4: Street detail. The Great Britain pack, combining packs, the full pack manager, and pins, bookmarks and collections.
* Phase 5: Network mode and driving.
* Phase 6: Touch, grids and finishing touches.
* Phase 7: Worldwide readiness and version 1.0. Contrasting regions, on-demand data, hardening and release.
* Later: tours, maritime zones and other Later or Could items.

---

## 3. Phase 0: Foundations and spikes

### Goal
A working repository with continuous integration and a Windows installer, and the answers to the technical questions that the rest of the design depends on. The countries and coastlines spike (S2) is the largest and most important, because this is where your earlier work got stuck.

### Requirements delivered
DEL-1, DEL-3, SCP-4 (licence and dependency check), NFR-5 (skeleton), and the spikes for DAT-3, PCK-1, PCK-4, SON-1, SON-3 and DMT-7.

### Tasks
* P0-T1 Repository: create the public GitHub repository TobyMap under the Chessel85 account (DP84), with the GPL-3.0 LICENSE, README, .gitignore (packs, sounds, voices and local paths files excluded), CLAUDE.md, and the folder layout in "artefacts.md". Copy the design documents into docs/design as Markdown, together with Discussion points.csv. The HTML copies are not added.
* P0-T2 Continuous integration: GitHub Actions running pytest on Windows and macOS, Playwright in headless Chromium and Firefox, and the dependency licence check. A placeholder test on each target proves it works.
* P0-T3 Development set-up: requirements files for runtime, development, pipeline and build, using the latest PySide6, and a one-command set-up script for your laptop. The pipeline's data folder is a setting (AD-18). Your laptop's local paths file points it at drive E:.
* P0-T4 Spike S1, spatial sound (architecture 12.2). A small demo with Synthizer, OpenAL Soft, the project's own HRTF processing, and Web Audio in Firefox and Chrome. Write the findings.
* P0-T5 Spike S2, countries, coastlines and islands (architecture 12.3 and 6.12). Download the OSM land polygons to the data folder. Check GeoDesk's licence. Build and check the UK, France and Spain, then Sweden and Norway, then Fiji, Russia, the USA, Kiribati and Antarctica, each as a small pack in the custom format. Measure time, memory, disk and size, with and without compact coordinates. Write the findings, with pictures of the results described in words.
* P0-T6 Spike S3, hosting and browser (architecture 12.4). Test reading pieces of a release file from a browser worker in Firefox, Chrome and Edge, and the browser storage limits. Test Hugging Face, then Cloudflare Pages, if needed. Write the findings.
* P0-T7 Spike S4, core in Pyodide (architecture 12.5). Time "where am I" and a step on the S2 pack in a Pyodide worker. Measure start-up time and download size. Write the findings.
* P0-T8 Spike S5, globe, accessible shell and installer (architecture 12.6). Build the empty four-region shell on desktop and web, with a turning globe. Test announcements, Braille-only output and tree focus with NVDA. Package the desktop shell as a Windows installer. Write the findings.
* P0-T9 Spike S6, spatial voice (architecture 12.7). A demo of eSpeak NG, Piper and the Windows voices speaking from a direction, plus the web candidates. Write the findings.
* P0-T10 Comparison with AtMap and AtlasDL: copy section 15 of the architecture into docs/design, and add any further lessons found while doing the spikes.
* P0-T11 Update the architecture document from the findings, listing the changes at the top, and raise any decisions for you as discussion points.

### Suggested order
1. P0-T1 to P0-T3, so everything else has a home.
2. P0-T8 (S5) and P0-T4 (S1), which are quick and give you something to try early.
3. P0-T5 (S2), the longest. P0-T9 (S6) and P0-T6 (S3) can be done while you review the S2 stages.
4. P0-T7 (S4), which needs the S2 pack.
5. P0-T10 and P0-T11.

### Automatic exit checks
* Continuous integration is green on Windows, macOS and the web, in both Chromium and Firefox.
* The licence check runs and passes.
* The S2 checks listed in architecture 12.3 pass, or each failure is explained in the findings with a proposed fix.

### PO acceptance gate
* Listen to the S1 demo and say which desktop sound you prefer.
* Listen to the S6 demo and choose a voice.
* Install the S5 shell with its installer, and try it and the web version with NVDA: Tab around the regions, hear announcements, and turn the globe.
* Review the S2 findings for the UK, France and Spain before the later S2 stages go ahead, then the rest.
* Read the six findings documents and answer any new discussion points.

---

## 4. Phase 1: Walking skeleton

### Goal
The whole chain works end to end, at its simplest. A basic pack is built by the pipeline, installed, and explored by stepping in the north-fixed orientation, in both the desktop and web versions. The PO runs the full listening test.

### Requirements delivered
SCP-1, SCP-2 (coverage test), PLT-1, PLT-2 and PLT-3 (builds), PLT-5, ACC-1, ACC-2, ACC-3, ACC-4, ACC-7, LOC-1, LOC-2, LOC-6, LOC-7, NAV-1, NAV-2, NAV-9, NAV-13, ANN-1, ANN-3, ANN-4, ANN-5, VIS-1, VIS-4, VIS-5, SON-1, SON-7, SON-8, SON-9 (curve), DMT-1, DMT-2, DMT-6, DAT-3 (base coastline), DAT-9, DAT-14, PCK-5, DEL-5.

### Tasks
* P1-T1 Core geodesy (geo): distance, bearing, stepping along meridians and lines of latitude, blocking at the poles, the antimeridian, and the formatting of units, bearings and coordinates. Tests include NAV-1, INF-3's London to Paris check, and the antimeridian checks in architecture 6.13: stepping across the 180 degree line in Fiji and the Bering Strait, wrap-aware bounding boxes and centres, and area on the ellipsoid.
* P1-T2 Pack format version 1 (packs): the archive writer and reader, the byte source interface (local file first), the manifest, checksums and version checks.
* P1-T3 Pipeline skeleton (mapdata): check, fetch and build commands, configuration files for sources, layers and paths, stage caching, plain-line progress, the end summary and the log file. The licence check stops a build with an unlicensed source.
* P1-T4 Base pack "lite": countries and first-level divisions (from Natural Earth or OSM, as decided in DP89 after spike S2), VLIZ oceans and seas, and land, tiled and written as a pack, with shared-edge simplification (AD-16). The no-gaps test proves every point has a name (LOC-6).
* P1-T5 Store and "where am I": point queries, ranking by smallest area, and the tile cache. The nearest point of an area to the location, for Nearby's distances (INF-3, INF-7).
* P1-T6 World model and stepping: the location, zoom and step lists, step size and zoom keys, link step to zoom, and north-fixed stepping.
* P1-T7 Describe: change detection, templates, "where am I", coordinates, heading information (H), repeat and history, and the tick when nothing changes. Units and bearing formats in settings. Nearby gives each area's distance and bearing to its nearest point, not to its label point: at the Canadian side of Niagara Falls (43.08 north, 79.08 west), the USA is under 1 mile away (INF-3, INF-7, PO's Phase 0 feedback).
* P1-T8 Command registry and session: commands, default keys, F1 help, the key describer, key remapping with clash warnings, the coverage test and the screen reader key clash test. Keys that move straight to each region from any region, on the desktop and the web (DP106, ACC-2): F2 to the map, F3 to the Information panel, back to the item last focused there (the first item of Within the first time), and F4 to Details. Shift+Space, D, R and Ctrl+Alt+Space are dropped. Ctrl+Alt+M stays, in the web version only, for the menu bar. The browser tests check that Firefox and Chrome let the page have F2, F3 and F4; F3 is "find again" in browsers.
* P1-T9 Map scene: the orthographic projection, the shape list, the centre cross, the heading arrow and the outline of the current feature. Click to move and wheel to zoom. Fiji and Russia draw as single shapes across the 180 degree line.
* P1-T10 Desktop shell: the four regions, the announcer, the map widget painting the shape list, the menu built from the registry, the settings dialog, saved settings, and a stand-in audio backend that plays earcon WAVs. From the PO's Phase 0 feedback:
  * When a held arrow key is let go, only the latest place is spoken, with no backlog of earlier ones (ANN-3). A test holds a key for 2 seconds, lets go, and checks that nothing but the final place is spoken after the release. The same test runs in the web version (P1-T11).
  * The Information panel tells NVDA each item's level, such as "level 2", and NVDA reads the item the panel moves to after F3 without pressing Up then Down (INF-10). Its items are changed in place, not rebuilt.
* P1-T11 Web shell: the same regions and behaviour, including the held key test (ANN-3), with the core in a Pyodide worker, the key map, focus manager, announcer, canvas painter, menu and dialogs. The pack is loaded from the site for now.
* P1-T12 Earcons: the sound folder, placeholder tones generated by a script, the PO's tick and blocked sounds when supplied, and custom file settings.
* P1-T13 Listening test tool: plays a sound from a random direction and distance, records the answer in a CSV, and includes the "beyond the view" sound and the fixed tone alternative (SON-9, DP80). It uses the backend chosen in S1, and a web version if S1 shows the sounds differ.
* P1-T14 Packaging: the Windows installer and portable zip, extended from the Phase 0 shell installer, and the web version on GitHub Pages. The first GitHub release is made when Phase 1 is accepted. No Mac download yet (AD-20).
* P1-T15 Diagnostics: the test trace and "copy diagnostics" command (architecture 10.3).
* P1-T16 Carried over from spike S2 (docs/spikes/S2-countries-coastlines.md), moved here by the PO on 2 November:
  * Make the counties step faster (DP101), then finish stage 1's whole run (the UK, France and Spain) and compare it with the 1 November results, using `mapdata spike-s2-compare`.
  * Stage 4, Argentina: Tierra del Fuego shared with Chile, the Andes border, the undecided border on the Southern Patagonian Ice Field, and the Falkland Islands. Parked by the PO; its settings are ready.
  * Areas held twice in one layer, such as Sevastopol, handled as agreed in DP104.
  * The area check takes away the inland water mapped in OSM before comparing with Wikidata, and reports the water separately.
  * The overlap check also finds one area wholly inside another.
  * Done first, before the world build, as agreed in DP107 (DMT-7):
    * Every country is built from the same planet file, so neighbours never come from OSM data of different dates. A new planet file rebuilds every country.
    * Each country is built and kept on its own, so a change to the build's settings or code for one country rebuilds only that country. After any country is rebuilt, the check that neighbours meet exactly (AD-16) runs again on its borders, and a neighbour whose border no longer matches is rebuilt too.
    * Each step works only on the parts near the area it is working on, never on a whole country or a whole gap at once.
    * The planet file is read once, in its own short-lived process.
    * There are no time limits. For each slow step, starting with the counties step, at least two approaches are tried, more where there are other sensible ones, and the fastest that gives the right result is kept. The work stays spread over cores (DP103), but the aim is a faster method, not more cores.
    * The trials use a small dataset, so each one is quick: Belgium, which has counties at levels 6, 7 and 8. Mainland France, without its overseas territories, is the regression test: it must give the same results as on 1 November.
    * Each trial's times and results are written in the findings, so the PO can see which approach was chosen and why.

### Automatic exit checks
* The Phase 1 acceptance scripts pass on Windows, macOS and the web.
* The step announcement is ready within 150 ms for 95% of steps on the desktop on the base pack lite (NFR-1), and the web figure is recorded.
* Building the base pack lite twice gives an identical file (DMT-1).
* The antimeridian tests pass.
* The installer installs, starts and uninstalls cleanly on a Windows test machine in continuous integration.

### PO acceptance gate
* Install the desktop version with the installer, then open the web version in Firefox.
* Follow the Phase 1 checklist with NVDA: step across the Channel from England to France and out into the Atlantic, step across the 180 degree line in Fiji, change zoom and step, ask "where am I", coordinates and heading, and use F1 and the key describer.
* Run the full listening test. Claude Code analyses the CSV and proposes the sound settings, including the distance curve and the "beyond the view" sound.

---

## 5. Phase 2: Orientation, layers and sound

### Goal
Moving and listening work as designed: three orientations, turning, poles, history, layers shared by sight and sound, and the sound design built on the listening test results.

### Requirements delivered
NAV-3, NAV-8 (coordinates), NAV-10, NAV-11, NAV-12, SCP-6, SCP-7, ANN-2, ANN-7, ACC-5, ACC-6, ACC-8, SON-2, SON-3, SON-6, SON-10, DAT-13, VIS-2, VIS-3.

### Tasks
* P2-T1 Orientations and turning: north-fixed, cardinal facing and free facing, the F key, turning keys, typing a bearing, great circle steps, crossing the poles, and the heading after each move.
* P2-T2 Position history and jump to coordinates, accepting all the formats in NAV-8.
* P2-T3 Layer catalogue: layer definitions from the pack, the user's changes, the layers list dialog (Shift+L), and saving choices. A layer that is off disappears from the map and from every announcement.
* P2-T4 The visible rule: zoom ranges and the area size rule, used by the map scene and ready for the lists. Default zoom ranges start from the Shortbread schema (data sources, version 0.7).
* P2-T5 Crossed and passed: along the step's path, in the background, with its earcon and its list in a simple first version of the Information panel.
* P2-T6 Sound scene and audio backends: directions relative to the orientation, loudness from the tuned curve, muffling behind, the beyond-the-view level, and speakers mode.
* P2-T7 Spatial voice: labels spoken by the voice chosen in spike S6 and placed in space, with history, Braille-only output on NVDA, and the setting to also speak them through the screen reader. The first label must be heard: in the S6 web page in Firefox, the PO may have missed the first one, so the sound output is started, and a silent label made, before the first real label, on both the desktop and the web.
* P2-T8 Earcons in full: every event in SON-6, each switchable, with separate volumes and master mute.
* P2-T9 Orientation beacon, to the North Pole by default, fading near the pole.
* P2-T10 Graticule and special lines: written into the base pack at 1 degree, with the interval set by the user, and crossing earcons in the layer definitions (AD-11).
* P2-T11 Verbosity presets and per-event switches, and the concise Braille format.
* P2-T12 Themes: standard, high contrast dark, high contrast light and colour-blind safe, with label size and the heading-up option. Neighbouring areas use different colours from the pipeline's colour numbers (AD-19). Contrast checked automatically. Isolating Fiji shows one compact shape (VIS-2, AD-17). A map display setting, as agreed in DP108: fill as different colours for neighbours (the default), one colour for all, or no fill (outlines only); borders on or off; and a choice of colour for the fill, the borders and the current outline. The current feature's outline is always shown, and the high contrast themes keep the 7:1 check.
* P2-T13 Magnifier support: the map centre reported to the system so magnifiers follow it.

### Automatic exit checks
* The Phase 2 acceptance scripts pass on all three targets, including NAV-3's 0.01 degree test and the pole crossings.
* The high contrast themes pass the 7 to 1 contrast check.

### PO acceptance gate
* Follow the Phase 2 checklist: cycle the orientations, cross the North Pole in cardinal and free facing, switch layers off and confirm they vanish from sound, take large steps and open the crossed and passed list, use the beacon, and hear the graticule earcons.
* Give feedback on the sound design, now that it is built on your listening test.

---

## 6. Phase 3: Information, hierarchy and search

### Goal
The whole world can be explored and questioned at country scale, using the complete base pack.

### Requirements delivered
LOC-3, LOC-4, NAV-4, NAV-8 (in full), INF-1 to INF-10, SRB-1 to SRB-4, SON-4, ANN-6, ACC-9, DAT-1, DAT-4, DAT-5, DAT-7, DAT-8, DAT-12, PCK-1 (base pack), PCK-2 (first version), PCK-4, DMT-3, DMT-5.

### Tasks
* P3-T1 Complete base pack: the country units list (French Guiana and the others, DP86), named islands, continents built from countries and split along configured lines (including distant parts, DP88), GMBA mountain ranges, Natural Earth physical regions, major rivers, lakes over 10 square kilometres, major roads and railways, populated places, peaks, bays and straits, and the water hierarchy (DAT-1, DAT-4, DAT-5, DAT-12). Size checked against the 250 MB soft limit.
* P3-T2 Wikidata facts with source and date, and Wikipedia links (DAT-7). Disputed areas from Natural Earth (ANN-6, DAT-8).
* P3-T3 Relations in the pipeline: containment, parents of parents, identical boundaries, neighbours with shared lengths, overlaps, and crossings in order.
* P3-T4 Information panel: the groups registered in one table, filled when opened, sortable with Ctrl+S, typing to jump, and the item actions (INF-10). Within, Contains, Bordering, Overlapping, Crossing, Nearby, Crossed and passed, and Search.
* P3-T5 Details panel and the D key, with the Wikipedia command (INF-1).
* P3-T6 Hierarchy mode: up with the ambiguous menu and beep, down by type with counts, neighbours clockwise, zoom to fit, and Backspace restoring the zoom (NAV-4, DP77).
* P3-T7 Measuring: distance and bearing to any item, to the nearest point or the centre, and to a feature found by search (INF-3, INF-8).
* P3-T8 Search: the index in the pipeline, fuzzy and accent-free matching, ranking and descriptions, filters, and jumping (SRB-1, SRB-2, NAV-8).
* P3-T9 World tree (T) and browse by category (SRB-3, SRB-4).
* P3-T10 Query builder (Q) (INF-9).
* P3-T11 Look around and "hear its direction" (SON-4).
* P3-T12 Name languages: preferred language, fall-back to the local name, and language marking (ACC-9).
* P3-T13 Pack manager first version: the catalogue, install, remove, checksum checks, and the first-run offer of the base pack. Packs downloaded from GitHub Releases, or the fall-back chosen in DP83 for the web.
* P3-T14 Pipeline quality reports and the publish command (DMT-3, DMT-5).
* P3-T15 Help: the user guide, the key reference, the glossary and the data sources page (DAT-9).

### Automatic exit checks
* The Phase 3 acceptance scripts pass, including the coverage test of sample places worldwide (DAT-1), Switzerland's five neighbours (INF-2), "Sao Paulo" (SRB-1), and the Bay of Biscay hierarchy (DAT-4).
* The base pack's size is reported against 250 MB.
* The base pack is published to a test release and installed from it by the pack manager.

### PO acceptance gate
* Follow the Phase 3 checklist: hierarchy from Hampshire up to the World, down into France, neighbours of Switzerland, the Information panel groups and sorting, search, the world tree, the query builder and look around.

---

## 7. Phase 4: Street detail

### Goal
Street-level exploration of Great Britain, with packs combining seamlessly, a complete pack manager, and personal content.

### Requirements delivered
DAT-2, DAT-3 (detailed coastlines), PLT-4, PCK-1 (regional packs), PCK-2 (complete), DMT-4, DMT-7 (complete), NFR-3, NFR-4, USR-1 to USR-5.

### Tasks
* P4-T1 Full OpenStreetMap pipeline for a region, built on the spike S2 method: all administrative levels cut to the land polygons, slivers given to neighbours, named islands (and unnamed islands if DP87 says so), shared-edge simplification across levels, roads and paths, land use, parks and public spaces, school grounds, points of interest with friendly categories, river assembly, and matching to base identifiers.
* P4-T2 Great Britain pack built from drive E:, aiming for 1 GB or less, split if it is larger.
* P4-T3 Combining packs: tile coverage and the most detailed pack wins, merging records and relations by identifier, and the no-missing-detail rule (PLT-4).
* P4-T4 Correction rules in the pipeline, listed in the quality report (DMT-4).
* P4-T5 Pipeline safety in full: the disk space estimate, the data folder check, and the record of files created (DMT-7).
* P4-T6 Pack manager complete: updates offered, downloads cancelled and resumed, and browser storage reported in the web version.
* P4-T7 Robustness: corrupt packs detected and set aside (NFR-4). Memory checked against 2 GB with the base and Great Britain packs (NFR-3).
* P4-T8 Pins, feature bookmarks and collections, shown in the Information panel and on the map (USR-1 to USR-3).
* P4-T9 Measuring a chain of pins (USR-4) and GeoJSON export and import (USR-5).

### Automatic exit checks
* The street-level acceptance scripts pass for the UK test area (DAT-2).
* A point 2 km off the Brittany coast is announced as sea (DAT-3). The S2 coastline checks pass on the Great Britain pack.
* A bookmark still resolves after the pack is rebuilt (USR-2).
* Step timing meets NFR-1 on the Great Britain pack.

### PO acceptance gate
* Install the Great Britain pack. Follow the Phase 4 checklist: explore streets around a familiar place, move between areas covered and not covered by the pack, drop pins, bookmark features, build a collection and measure it, and export it.
* Run the pipeline yourself as data manager, following the guide: check, build a small region, read the quality report.

---

## 8. Phase 5: Network mode and driving

### Goal
Travel along any line or network, stop at points of interest, and drive.

### Requirements delivered
NAV-5, NAV-6, NAV-14, INF-12.

### Tasks
* P5-T1 Network graph in the pipeline: roads, paths, railways, waterways with their direction, coastlines, borders with tripoints, and the graticule. Stop points attached to links. Links joined across packs.
* P5-T2 Network mode: entering and snapping, cycling the network type, choosing links with Left and Right, travelling, stopping rules, and the heading on arrival in each orientation (NAV-5).
* P5-T3 Stopping at points of interest, with chosen categories (NAV-6).
* P5-T4 Rivers described as upstream and downstream, and following the Thames to the sea.
* P5-T5 Distance along a line between two points or pins (INF-12).
* P5-T6 Driving in network and stepping modes: speed in steps per second, the ding for points passed, the beacon swinging on bends, and speech that never falls behind (NAV-14).

### Automatic exit checks
* The Phase 5 acceptance scripts pass: the three-road junction, round Germany by tripoints, the Thames to the North Sea, the bus stop stop, and arrival headings in each orientation.

### PO acceptance gate
* Follow the Phase 5 checklist: walk familiar streets junction to junction, follow a river and a coastline, go round a country's border, and drive along a road with the beacon on.

---

## 9. Phase 6: Touch, grids and finishing touches

### Goal
Touch exploration, grid layers heard as pitch, and the remaining Should items.

### Requirements delivered
TCH-1 to TCH-4, INF-11, SON-5, DAT-6, LOC-5, PCK-1 (grid packs).

### Tasks
* P6-T1 Touch framework and shape tracing, with the scale announcement and the NVDA touch hand-over message (TCH-1, TCH-3, TCH-4). Desktop first.
* P6-T2 Line tracing, with the tone changing at named points (TCH-2).
* P6-T3 Grids in the pipeline: GEBCO elevation and depth in the base pack, and CHELSA climate as separate grid packs (DAT-6, PCK-1).
* P6-T4 Grid values with V, pitch while moving, and the sweep (INF-11, SON-5).
* P6-T5 Relief as pitch under the finger, the second touch mode, proving TCH-3.
* P6-T6 Plain-language position, Shift+C (LOC-5).
* P6-T7 Guided tour and practice mode (UX section 15).

### Automatic exit checks
* The Phase 6 acceptance scripts pass, including Ben Nevis's elevation within 50 m (INF-11).
* Touch feedback latency is measured against 50 ms.

### PO acceptance gate
* Trace the outline of a country and a river on a touch screen, hear elevation as pitch while stepping, run a sweep, and try the guided tour.

---

## 10. Phase 7: Worldwide readiness and version 1.0

### Goal
Prove that nothing assumes the UK, add on-demand data, harden everything, and release version 1.0 of the desktop and web versions together.

### Requirements delivered
DAT-10, DAT-11, PCK-3, PLT-4 (on demand), NFR-1 to NFR-4 (verified), DEL-4, and readiness for PLT-1 (JAWS) and PLT-2 (VoiceOver).

### Tasks
* P7-T1 Japan and Kenya packs, and the regression suite on all three regions (DAT-10).
* P7-T2 On-demand data: fetching pack pieces when online, announcing a new smaller area when it arrives (PCK-3, PLT-4).
* P7-T3 Freshness: refresh intervals for each source, and source dates shown in pack details (DAT-11). A fresh UK extract and planet file are downloaded before release (data sources, "what this means").
* P7-T4 Performance and memory hardening against NFR-1 to NFR-3 on all targets.
* P7-T5 Checking default keys against the published JAWS and VoiceOver key lists, and preparing test scripts for future JAWS and Mac testers (ACC-4, PLT-1, PLT-2).
* P7-T6 Release notes stating what was tested with which screen readers and platforms (DEL-4), and the differences between desktop and web (PLT-3).
* P7-T7 Version 1.0 release: the Windows installer, the web site, and published packs. A Mac disk image is added if a Mac tester has been found (DP92).

### Automatic exit checks
* Every Must requirement has a passing automatic test or a PO-accepted manual check.
* The regression suite passes on the UK, Japan and Kenya.

### PO acceptance gate
* The full acceptance checklist on the release candidate, desktop and web.
* Agreement to release version 1.0.

---

## 11. Later

These are recorded so they are not lost. They are not planned yet.

* USR-6 Tours.
* DAT-3 maritime zones layer (Could).
* Undersea feature names from the GEBCO gazetteer (Could).
* A natural neural voice option, such as Piper (DP82).
* Higher resolution elevation packs, once a licence is confirmed.
* JAWS and VoiceOver acceptance, once testers are found.
* Mac downloads (a disk image), once a Mac tester is found (AD-20, DP92).
* Named island groups, such as the Isles of Scilly (architecture 6.12).
* A Sovereign States layer, if DP86 does not include it earlier.
* Touch tracing in the web version.

---

## 12. Traceability check

Every requirement in the catalogue is assigned to a phase:

* Phase 0: DEL-1, DEL-3, SCP-4.
* Phase 1: SCP-1, SCP-2, PLT-1, PLT-2, PLT-3, PLT-5, ACC-1, ACC-2, ACC-3, ACC-4, ACC-7, LOC-1, LOC-2, LOC-6, LOC-7, NAV-1, NAV-2, NAV-9, NAV-13, ANN-1, ANN-3, ANN-4, ANN-5, VIS-1, VIS-4, VIS-5, SON-1, SON-7, SON-8, SON-9, DMT-1, DMT-2, DMT-6, DAT-9, DAT-14, PCK-5, DEL-5.
* Phase 2: NAV-3, NAV-10, NAV-11, NAV-12, SCP-6, SCP-7, ANN-2, ANN-7, ACC-5, ACC-6, ACC-8, SON-2, SON-3, SON-6, SON-10, DAT-13, VIS-2, VIS-3.
* Phase 3: LOC-3, LOC-4, NAV-4, NAV-8, INF-1 to INF-10, SRB-1 to SRB-4, SON-4, ANN-6, ACC-9, DAT-1, DAT-4, DAT-5, DAT-7, DAT-8, DAT-12, PCK-2, PCK-4, DMT-3, DMT-5.
* Phase 4: DAT-2, DAT-3, PLT-4, PCK-1, DMT-4, DMT-7, NFR-3, NFR-4, USR-1 to USR-5.
* Phase 5: NAV-5, NAV-6, NAV-14, INF-12.
* Phase 6: TCH-1 to TCH-4, INF-11, SON-5, DAT-6, LOC-5.
* Phase 7: DAT-10, DAT-11, PCK-3, NFR-1, NFR-2, DEL-4.
* Every phase: SCP-3, SCP-5, NFR-5, DEL-2.
* Later: USR-6.
* NAV-7 is withdrawn (merged into NAV-5).

Some requirements are started in one phase and completed in a later one, such as PCK-1 and DAT-3. They are listed above under the phase that completes them, and named in the earlier phase's "requirements delivered" with what part is delivered.
