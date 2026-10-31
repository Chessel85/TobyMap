# Artefacts to be Created

Version 0.2, 31 October 2026, for product owner review.

## Changes in version 0.2

* The repository is TobyMap, public, under the Chessel85 account (DP84). The design documents go into docs/design as Markdown only, without the HTML copies.
* Spike findings now cover six spikes, S1 to S6, and there is a new document comparing the design with AtMap and AtlasDL.
* New configuration: the country units list, and the local paths file that holds the data folder (AD-18).
* The Windows installer is built from Phase 0. The Mac disk image is moved to Later (AD-20).
* Antimeridian test samples and the S2 coastline check places are added to the tests.
* GitHub releases are made from Phase 1 onwards, with no separate preview (DP85).

This is the list of everything the implementation project will produce. It goes with "architecture.md" and "implementation plan.md". Each artefact gives:

* where it lives (a path in the repository, or another place)
* what it is for
* the phase that creates it (later phases extend most of them)
* who owns it: Claude Code (CC) or the product owner (PO)
* the requirements it serves, where that helps

The repository and product are called TobyMap for now (DP84). Inside the code, the neutral names mapcore (the core), mapdata (the pipeline), desktop and web are used, so a later product name only changes what users see.

## How to read this document

Each group of artefacts has a level 2 heading. Each artefact is a list item, with its details as sub-items. Section 1 gives the repository's folder layout, so the paths in the later sections make sense.

---

## 1. Repository layout

The top level of the repository:

* README.md: what the project is, how to install it, and links to the documentation.
* LICENSE: GPL-3.0.
* CLAUDE.md: guidance for Claude Code, pointing to the detailed documents.
* mapcore/: the shared core (AD-1).
* desktop/: the PySide6 desktop shell.
* web/: the browser shell, with the Pyodide bridge.
* mapdata/: the data pipeline and its configuration.
* tools/: the listening test, placeholder sound generator, and other helpers.
* sounds/: the earcon list and credits. The WAV files themselves are kept out of git if they are large, and fetched by the set-up script.
* tests/: all automatic tests, test samples and acceptance scripts.
* docs/: design, developer, user and data manager documentation.
* packaging/: the Windows installer scripts, and later the Mac disk image scripts.
* .github/workflows/: continuous integration.

Inside mapcore/, one sub-package per module in architecture section 5.2: geo, packs, store, layers, world, navigation, describe, panel, relations, search, sound, render, touch, user, commands and session.

Inside mapdata/:

* the command line program
* stages/: one module per build stage (architecture section 8.2)
* config/: the configuration files (section 4 below)

---

## 2. Design and project documents

* Requirements catalogue
  * Where: docs/design/requirements catalogue.md, copied from Solution Design. Only the Markdown files and Discussion points.csv are copied. The HTML exports stay out of the repository (DP84).
  * For: the agreed requirements, traced into tests.
  * Phase: 0, then kept up to date. Owner: CC, with PO agreement.
* User experience description
  * Where: docs/design/user experience description.md.
  * For: how the application behaves.
  * Phase: 0, then kept up to date. Owner: CC, with PO agreement.
* Data sources
  * Where: docs/design/data sources.md.
  * Phase: 0, then kept up to date. Owner: CC. The PO's notes stay at the top.
* High level requirements and target users
  * Where: docs/design/.
  * Phase: 0. Owner: PO. Never rewritten by CC.
* Architecture
  * Where: docs/design/architecture.md.
  * For: the technical design and decisions AD-1 onwards.
  * Phase: 0, updated after the spikes and whenever a decision changes. Owner: CC.
* Implementation plan
  * Where: docs/design/implementation plan.md.
  * Phase: 0. Owner: CC, with PO agreement.
* This artefact list
  * Where: docs/design/artefacts.md.
  * Phase: 0. Owner: CC.
* Discussion points
  * Where: docs/design/Discussion points.csv.
  * For: questions and decisions between CC and the PO, continuing the current numbering.
  * Phase: all. Owner: shared.
* Decision records
  * Where: docs/decisions/, one short file per significant decision made after this architecture.
  * For: recording why, so a later session does not undo a decision. Each record states how it affects screen reader users (SCP-3).
  * Phase: from 0. Owner: CC.
* Spike findings
  * Where: docs/spikes/, one document for each of spikes S1 to S6. The S2 findings describe each test area (the UK, France, Spain, Sweden and Norway, and the antimeridian countries) in words, with pictures for sighted reviewers.
  * For: the evidence behind the technical decisions, written for the PO.
  * Phase: 0. Owner: CC.
* Comparison with AtMap and AtlasDL
  * Where: docs/design/lessons-from-atmap.md, starting from architecture section 15.
  * For: what the earlier projects did, what this design adopts, and what it does differently.
  * Phase: 0. Owner: CC.
* Phase task lists
  * Where: docs/plan/phase-0.md to phase-7.md.
  * For: the tasks of each phase with tick boxes, so any session can see what is done.
  * Phase: each phase. Owner: CC.
* Phase reports
  * Where: docs/plan/phase-N-report.md.
  * For: what was built, how to install it, the checklist, known problems, and what was not tested (implementation plan 1.5).
  * Phase: end of each phase. Owner: CC.
* Feedback log
  * Where: docs/plan/feedback.md.
  * For: the PO's feedback recorded against requirement IDs, with what was done about each item (DEL-4).
  * Phase: from 1. Owner: CC records, PO reviews.
* CLAUDE.md files
  * Where: the repository root, plus web/CLAUDE.md and mapdata/CLAUDE.md.
  * For: the rules Claude Code must follow in each area, as in RecallScore.
  * Phase: 0, then kept up to date. Owner: CC.

---

## 3. Source code

* The core (mapcore)
  * For: all map logic, shared by desktop and web (AD-1).
  * Phase: 1 onwards. Owner: CC. Requirements: most of the catalogue.
* The desktop shell (desktop)
  * For: the PySide6 application, its announcer, its map widget and its audio backend.
  * Phase: 0 (spike), 1 onwards. Owner: CC.
* The web shell (web)
  * For: the browser application: the page modules (key map, focus, announcer, tree, canvas painter, dialogs, menu, audio, pack storage), the worker, and the Python bridge.
  * Phase: 0 (spike), 1 onwards. Owner: CC.
* The pipeline (mapdata)
  * For: building, checking, inspecting and publishing packs (DMT-1 to DMT-7).
  * Phase: 0 (spike), 1 onwards. Owner: CC.
* The listening test tool
  * Where: tools/listening_test/.
  * For: the PO's sound tests, recording results to CSV (SON-1, SON-9).
  * Phase: 0 (demo), 1 (full). Owner: CC.
* The placeholder sound generator
  * Where: tools/make_placeholder_sounds.py.
  * For: simple tones for every earcon until the PO's WAV files arrive (SON-8).
  * Phase: 1. Owner: CC.
* The acceptance checklist generator
  * Where: tools/make_checklists.py.
  * For: turning acceptance scripts into readable checklists for the PO (architecture 11.3).
  * Phase: 1. Owner: CC.
* The web staging script
  * Where: tools/stage_web.py.
  * For: copying the core into the web site for Pyodide, as RecallScore does.
  * Phase: 1. Owner: CC.

---

## 4. Configuration

* Layer definitions
  * Where: mapdata/config/layers/, one file per layer group, such as boundaries, water, transport, places, land use, points of interest, physical and graticule.
  * For: each layer's name, group, features, styles, zoom range, minimum area size, sounds, network role and stop point role (SCP-7).
  * Phase: 1 onwards. Owner: CC proposes defaults, the data manager and PO adjust.
* Sources
  * Where: mapdata/config/sources.yaml.
  * For: each source's address, licence, attribution and refresh interval (DMT-6, DAT-9, DAT-11).
  * Phase: 1. Owner: CC.
* Point of interest categories
  * Where: mapdata/config/poi_categories.yaml.
  * For: the friendly names for OpenStreetMap tags, such as "bus stop".
  * Phase: 4. Owner: CC, extendable by the data manager.
* Regions
  * Where: mapdata/config/regions.yaml.
  * For: pack boundaries, following Geofabrik (PCK-1).
  * Phase: 0 (UK), 4 onwards. Owner: CC.
* Corrections
  * Where: mapdata/config/corrections.yaml.
  * For: the data manager's rename, exclude, reclassify and set-parent rules (DMT-4).
  * Phase: 4. Owner: data manager.
* Continents
  * Where: mapdata/config/continents.yaml.
  * For: the grouping of countries and the dividing lines (DAT-12).
  * Phase: 3. Owner: CC, explained in Help.
* Paths
  * Where: mapdata/config/paths.example.yaml in git, and a local paths.yaml that is not in git.
  * For: the data folder, with the source, working and output folders inside it (DMT-7, AD-18). No drive letter is built in. On the PO's laptop the local file points at drive E:. The --data option and the MAPDATA_ROOT environment variable override it.
  * Phase: 0. Owner: CC writes the example, each data manager sets their own.
* Country units
  * Where: mapdata/config/country_units.yaml.
  * For: the areas that replace a level 2 country in the Countries layer, such as Metropolitan France and French Guiana, each with its sovereign state (architecture 6.12, DP86).
  * Phase: 0 (spike S2), 3 onwards. Owner: CC, reviewed by the PO.
* Command registry
  * Where: mapcore/commands/registry.yaml.
  * For: every command's name, default key, region and menu position (AD-3).
  * Phase: 1. Owner: CC, keys agreed with the PO.
* Information panel groups
  * Where: mapcore/panel/groups.yaml.
  * For: the groups, their order, keys, default sort and whether each is limited to visible features (INF-10). Kept in one place so the PO's changes after testing are quick.
  * Phase: 3. Owner: CC, shaped by PO feedback.
* Announcement templates
  * Where: mapcore/describe/templates.yaml.
  * For: the wording of every announcement, including the concise format (ACC-6).
  * Phase: 1. Owner: CC, wording reviewed by the PO.
* Interface strings
  * Where: mapcore/strings.yaml.
  * For: all menu, dialog and help words in one place, for possible translation later.
  * Phase: 1. Owner: CC.
* Themes
  * Where: mapcore/render/themes.yaml.
  * For: the four themes' colours, checked for contrast (VIS-2).
  * Phase: 1 (standard), 2 (all). Owner: CC.
* Defaults
  * Where: mapcore/defaults.yaml.
  * For: the zoom and step lists, the sound curve settings from the listening test, verbosity presets and other default settings.
  * Phase: 1. Owner: CC, tuned with the PO.

---

## 5. Data products

* Catalogue
  * Where: catalogue.json, published with the packs.
  * For: the list of packs the pack manager offers (PCK-2).
  * Phase: 3. Owner: CC builds, the data manager publishes.
* Base pack lite
  * For: the Phase 1 and 2 world: countries, first-level divisions, seas, oceans and land.
  * Phase: 1. Replaced by the full base pack in Phase 3.
* Spike S2 test packs
  * For: the UK, France, Spain, Sweden and Norway, and the antimeridian countries, built to prove the coastline method (architecture 12.3). Kept in the data folder, not published.
  * Phase: 0. Owner: CC.
* OSM land polygons
  * Where: downloaded into the data folder from osmdata.openstreetmap.de, about 1 GB.
  * For: cutting every land area to the coast (AD-15).
  * Phase: 0. Owner: CC fetches with mapdata fetch.
* Base pack (world)
  * For: worldwide coverage at country scale, at most about 250 MB (DAT-1, PCK-1).
  * Phase: 3, with elevation and depth added in Phase 6. Owner: CC builds, the data manager publishes.
* Great Britain pack
  * For: street-level detail for the UK test region, aiming for 1 GB or less (DAT-2).
  * Phase: 4, with the network added in Phase 5.
* Japan and Kenya packs
  * For: proving worldwide behaviour (DAT-10).
  * Phase: 7.
* Climate grid packs
  * For: rainfall and temperature from CHELSA (DAT-6, PCK-1).
  * Phase: 6.
* Test packs
  * Where: built in continuous integration from tests/samples/, never published.
  * For: fast, repeatable automatic tests (architecture 11.1).
  * Phase: 1 onwards.
* Pack contents that travel with every pack
  * The manifest, with checksum, version range, coverage and source dates (PCK-5, DAT-11).
  * The attribution file and the ODbL notice (DAT-9, SCP-4).
  * The layer definitions (SCP-7).
* Quality reports
  * Where: the output folder, next to each built pack.
  * For: text and CSV reports of repairs, unnamed features, coverage gaps, slivers of land given to neighbours, countries with far-apart parts, relations that failed to build, antimeridian checks, size by layer and differences from the last release (DMT-3).
  * Phase: 3 onwards.
* Pipeline working files
  * Where: the working folder inside the data folder (drive E: on the PO's laptop).
  * For: cached stage results, so rebuilds are quick (AD-12). They can be deleted at any time and rebuilt, but only with the PO's agreement (DP75).

---

## 6. Sound and voice assets

* Earcon files
  * Where: sounds/, one WAV file per event, with the file names listed in Help (SON-8).
  * For: tick, blocked, crossed and passed, ding, no data, hierarchy beep, crossing earcons, and the beacon.
  * Phase: 1 (placeholders), replaced as the PO's files arrive. Owner: PO supplies, CC installs.
* Sound credits
  * Where: sounds/CREDITS.md.
  * For: the source and licence of every bundled sound (SON-8).
  * Phase: 1. Owner: CC.
* Spatial voice
  * For: the voice chosen in spike S6 (SON-3, DP82): eSpeak NG, Piper or a Windows voice, with what the web version needs.
  * Phase: 0 (spike), 2. Owner: CC, chosen by the PO.
* HRTF data set, if spike S1 chooses the project's own HRTF processing
  * For: the measured head response used to place sounds in space, with its licence recorded.
  * Phase: 1 or 2. Owner: CC.

---

## 7. Builds and releases

* Windows installer and portable zip
  * Where: packaging/ for the scripts (PyInstaller specification and NSIS installer script, as in RecallScore), and GitHub Releases for the results.
  * For: installing and uninstalling the desktop application (DEL-5, AD-20).
  * Phase: 0 (the empty shell, spike S5), released from Phase 1 at every accepted phase. Owner: CC.
* macOS disk image
  * Where: GitHub Releases, built in continuous integration, unsigned, with opening instructions (PLT-2).
  * Phase: Later, once a Mac tester is found (AD-20, DP92). Owner: CC.
* Web application
  * Where: GitHub Pages.
  * Phase: 1 onwards. Owner: CC.
* Release notes
  * Where: each GitHub release, and docs/release-notes.md.
  * For: what changed, which screen readers and platforms it was tested with (DEL-4), and the differences between desktop and web (PLT-3).
  * Phase: each release. Owner: CC.
* Third-party notices
  * Where: packaging/THIRD_PARTY_NOTICES.txt, also shown in Help.
  * For: every library, voice, sound and data set with its licence (SCP-4).
  * Phase: 1 onwards. Owner: CC.
* Continuous integration workflows
  * Where: .github/workflows/.
  * For: tests on Windows and macOS, web tests, the licence check, test pack builds, and release builds (NFR-5, DEL-1).
  * Phase: 0 onwards. Owner: CC.

---

## 8. Tests

* Unit and geometry tests
  * Where: tests/core/ and tests/geo/.
  * Phase: 1 onwards. Owner: CC.
* Acceptance scripts
  * Where: tests/acceptance/, one file per script, each tied to requirement IDs.
  * For: the automatic announcement tests and the PO's checklists (architecture 11.3).
  * Phase: 1 onwards. Owner: CC writes, PO approves the wording.
* Announcement baselines
  * Where: tests/acceptance/approved/.
  * For: the exact approved text of every announcement in the scripts (NFR-5).
  * Phase: 1 onwards. Owner: CC, changes approved by the PO.
* PO acceptance checklists
  * Where: docs/checklists/phase-N.md, generated from the acceptance scripts.
  * For: what the PO tests with NVDA at each gate.
  * Phase: 1 onwards. Owner: CC generates, PO runs.
* Desktop interface tests
  * Where: tests/desktop/.
  * Phase: 1 onwards. Owner: CC.
* Web tests
  * Where: tests/web/, run with Playwright.
  * Phase: 1 onwards. Owner: CC.
* Pipeline tests and samples
  * Where: tests/mapdata/ and tests/samples/.
  * For: each build stage on small samples, the repeatability test (DMT-1), and the source data for the test packs, including small samples across the antimeridian (Fiji and Chukotka) and around the South Pole.
* Coastline check places
  * Where: tests/acceptance/coastline_places.yaml.
  * For: the points from spike S2 that must be in the sea or on the right island, such as 2 km off Brittany, Skye, Gibraltar, Ceuta and Llívia (DAT-3, DAT-14).
  * Phase: 0, kept and extended. Owner: CC, PO may add places.
  * Phase: 1 onwards. Owner: CC.
* Coverage test place list
  * Where: tests/acceptance/coverage_places.yaml.
  * For: sample places worldwide that must resolve to the expected names with only the base pack (DAT-1).
  * Phase: 3. Owner: CC, PO may add places.
* Performance benchmarks
  * Where: tests/performance/.
  * For: step timing, start-up time and memory against NFR-1 to NFR-3.
  * Phase: 1 onwards. Owner: CC.
* Command coverage and key clash tests
  * For: every command has a key or menu entry (SCP-2), and no default key clashes with screen reader or browser keys (ACC-4).
  * Phase: 1. Owner: CC.
* Listening test results
  * Where: docs/spikes/listening-test/, the CSV files and the analysis.
  * For: the evidence for the sound settings (SON-1, SON-9).
  * Phase: 1, repeated if the sound design changes. Owner: PO produces, CC analyses.

---

## 9. User documentation

* In-application Help
  * For: the user guide, organised by task, with headings for screen reader navigation.
  * Phase: 1 (start), 3 (substantial), each phase after. Owner: CC.
* Key reference
  * For: every command and its key, built from the command registry, so it is always correct (ACC-3).
  * Phase: 1. Owner: CC.
* Glossary
  * For: plain explanations of bearing, great circle, orientation, zoom, step, visible, layer, administrative level and grid layer (UX section 15).
  * Phase: 3. Owner: CC.
* Data sources page
  * For: every source, its licence and its date (DAT-9).
  * Phase: 3. Owner: CC.
* Earcon list
  * For: the name and file of every earcon, so users can replace them (SON-8).
  * Phase: 2. Owner: CC.
* Guided tour and practice mode scripts
  * For: first use (UX section 15).
  * Phase: 6. Owner: CC, reviewed by the PO.
* Desktop and web differences
  * For: what the web version cannot do, such as touch tracing in the first release, and a different spatial voice if DP90 allows it (PLT-3).
  * Phase: 1 onwards. Owner: CC.

---

## 10. Data manager documentation

* Pipeline guide
  * Where: docs/data-manager/guide.md.
  * For: how to check, fetch, build, report, inspect and publish, written for a screen reader user (DMT-2).
  * Phase: 1 (start), 4 (complete). Owner: CC.
* Configuration reference
  * Where: docs/data-manager/configuration.md.
  * For: every configuration file and setting, with examples.
  * Phase: 1 onwards. Owner: CC.
* Publishing procedure
  * Where: docs/data-manager/publishing.md.
  * For: releasing packs and the catalogue, including the web copy if DP83 requires one.
  * Phase: 3. Owner: CC.

---

## 11. Developer documentation

* Core architecture notes
  * Where: docs/developer/, one document per area: core, packs and store, sound, rendering, web bridge, and testing.
  * For: the detail Claude Code needs before changing each area, as in RecallScore's docs folder.
  * Phase: 1 onwards. Owner: CC.
* Pack format specification
  * Where: docs/developer/pack-format.md.
  * For: the exact layout of a pack file, its keys and its version history (AD-5).
  * Phase: 1. Owner: CC.
* Set-up guide
  * Where: docs/developer/setup.md.
  * For: installing the tools on the PO's laptop, setting the data folder, and what is kept out of git.
  * Phase: 0. Owner: CC.
