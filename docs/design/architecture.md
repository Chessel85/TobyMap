# Architecture and High Level Design

Version 0.2, 31 October 2026, for product owner review.

## Changes in version 0.2

* New section 15: what I learned from your AtMap and AtlasDL projects (DP81), and what this design takes from them.
* New decisions AD-15 to AD-20, from "architecture thoughts.txt":
  * AD-15: countries are cut to the coastline using the OSM land polygons, and a short list of "country units" splits places such as French Guiana from France.
  * AD-16: shared borders are simplified once, edge by edge, so neighbouring areas never get gaps between them.
  * AD-17: the antimeridian is handled explicitly, with its own tests on Fiji, Russia, the USA, Kiribati and Antarctica.
  * AD-18: no drive letter is ever assumed. The pipeline's data folder and the application's pack folder are settings.
  * AD-19: neighbouring areas get different colours, worked out by the pipeline, as AtlasDL did.
  * AD-20: the Windows installer is built from Phase 0. Mac downloads wait until a Mac tester is found.
* New section 6.12 explains how countries, coastlines and islands are built, including the UK's islands and unnamed islands.
* Spike S2 is now the countries and coastlines spike on the UK, France and Spain, followed by Sweden and Norway, then the antimeridian countries.
* New spike S6 compares spatial voices (DP82). Synthizer, which AtMap used, is added to spike S1's candidates.
* Section 4.2: the latest PySide6 release is used, and checked at the start of each phase.
* Section 4.6: eSpeak NG does work on macOS.
* Section 9: hosting now reflects your Cloudflare and Hugging Face accounts (DP83), the repository name TobyMap (DP84) and releases from an early phase (DP85).
* Web tests run in Firefox as well as Chromium, because Firefox is your main browser.
* Section 14 lists the new questions, DP86 to DP92.

This document describes how the application and the data pipeline will be built. It turns the agreed "requirements catalogue.md" (version 0.6), "user experience description.md" (version 0.6) and "data sources.md" (version 0.5) into a technical design. Requirement IDs, such as NAV-3, refer to the requirements catalogue. Decisions are numbered AD-1, AD-2 and so on, so the implementation plan and later discussions can refer to them.

Two companion documents go with this one:

* "implementation plan.md": the phases, tasks and acceptance gates that Claude Code will follow.
* "artefacts.md": the list of everything the project will produce.

Nothing here changes what the user experiences. Where a technical finding affects the experience, it is raised as a new discussion point rather than changed silently.

The product's working name is TobyMap (DP84). Inside the code the neutral names mapcore (the core) and mapdata (the pipeline) are kept, so a later product name only changes what users see.

## How to read this document

Each section has a level 2 heading, and each decision or component has a level 3 heading, so you can move through it with the screen reader heading keys. You do not need to read the technical detail to review it. The parts most worth your attention are:

* Section 1, the summary of key decisions.
* Section 6.12, how countries, coastlines and islands are built.
* Section 12, the risks and the Phase 0 spikes.
* Section 14, the new questions for you.
* Section 15, what I learned from AtMap and AtlasDL.

---

## 1. Summary of key decisions

### AD-1 One Python core shared by desktop and web
All the map logic lives in one Python package, called the map core. It knows nothing about windows, browsers, speakers or screen readers. The desktop application (PySide6) and the web application (Pyodide in the browser) are thin shells around it. This is the RecallScore pattern: "reuse, never copy". It means a feature, and its tests, are written once.

### AD-2 The core is driven by commands and answers with responses
Every key press, menu choice or mouse click becomes a named command, such as "step.forward" or "panel.open.nearby". The core carries it out and returns a response: the text to announce, the earcons to play, the sounds to place in space, and whether the map needs redrawing. Both shells only translate keys into commands and responses into speech, sound and pictures. This is what lets the same acceptance scripts run automatically against the core and manually by you with NVDA.

### AD-3 One command registry is the source of keys, menus and help
Each command is defined once, with its name, default key, region and menu position. The key map, the menu bar, F1 help, the key describer and the "every command has a key or menu entry" test (SCP-2) are all built from that one table.

### AD-4 One feature store and one visibility rule for sight and sound
The visual map and every list draw their features through the same layer catalogue and the same visibility rule (NAV-13). So a feature that is drawn can always be found by a query, and a layer switched off disappears from both (SCP-2, SCP-6).

### AD-5 A custom single-file pack format, read in pieces
Each data pack is one file containing many small compressed pieces (tiles, feature records, relations, search index and grids) plus a directory. The application reads only the pieces it needs. The same reader works on a local file on the desktop, and over the internet with range requests in the browser and for on-demand data (PCK-3). Section 6 explains why this was chosen over SQLite, GeoPackage and PMTiles.

### AD-6 The visual map is drawn by the core, painted by the shells
The core projects features onto the globe (VIS-5) and produces a list of shapes in screen coordinates, each with a style. The desktop paints that list with Qt, and the web paints it on an HTML canvas. Your tilemaker and PMTiles test was considered and not adopted, because a separate tile set could drift from the data the screen reader uses, and web map tiles use a flat projection rather than the globe.

### AD-7 Geodesy on the Earth's ellipsoid, projection only for drawing
Every distance, bearing and step is calculated on the WGS84 ellipsoid using GeographicLib, which is accurate to well under a millimetre. A projection is used only to draw the map and the touch tracing screen (VIS-5).

### AD-8 Relations are worked out by the pipeline, not at run time
Containment, neighbours with shared border lengths, overlaps, the order in which a river passes through areas, the network graph and the search index are all calculated when a pack is built. The application only looks them up. This is what keeps a step under the 150 millisecond target (NFR-1).

### AD-9 The web version runs the core in a background worker
In the browser, Pyodide and the core run in a Web Worker, so the page never freezes and speech is never delayed. The worker reads packs with synchronous range requests and caches them in the browser's private file storage.

### AD-10 Spatial sound and the spatial voice behind one interface
The core works out where each sound is (direction, loudness and muffling, SON-9) without playing it. A sound backend on each platform plays it. The web uses the browser's built-in HRTF. For the desktop, Phase 0 spike S1 chooses between Synthizer (which AtMap used), OpenAL Soft and the project's own HRTF processing. The spatial voice (SON-3) is chosen by spike S6 (DP82). eSpeak NG is the starting candidate.

### AD-11 The graticule is data, not code
Lines of latitude and longitude at every 1 degree, plus the special lines, are written into the base pack by the pipeline. The interval the user chooses filters them. This keeps SCP-7's rule that the graticule is added by configuration alone, with no code specific to it. It costs well under 1 MB.

### AD-12 The pipeline is a staged, cached, configuration-driven command line tool
The data manager tool, called mapdata, runs in stages. Each stage writes its results to drive E: and is skipped next time if its inputs have not changed. All sources, layers, categories, regions and corrections are configuration files. Output is plain lines suited to a screen reader (DMT-2).

### AD-13 Canonical feature identifiers across packs
Every feature has one stable identifier, such as "osm:r62149" for the United Kingdom, used by every pack that mentions it. Where the base pack and a regional pack both describe the same feature, the pipeline matches them, mainly through Wikidata, so a bookmark (USR-2) and a relation always mean the same thing whichever packs are installed.

### AD-14 The most detailed installed pack wins, tile by tile
Each pack declares which tiles of the world it covers in detail. For any place, the application uses the shapes from the most detailed installed pack covering that tile. For example, with the Great Britain pack installed, the United Kingdom's coastline near Southampton comes from OpenStreetMap, not from Natural Earth (DAT-3, PLT-4).

### AD-15 Countries are cut to the coastline with the OSM land polygons
OpenStreetMap country boundaries include territorial waters. Rather than trying to work out which parts of a boundary are at sea, the pipeline keeps only the parts that are on land, by intersecting each area with the OSM land polygons. Those polygons are built every day by the OpenStreetMap project from every coastline in the world, and checked for breaks. A short configuration list of "country units" splits places such as French Guiana from France (DP86). Section 6.12 explains this in full.

### AD-16 Shared borders are simplified once
Where two areas share a border, that border is simplified once and both areas are rebuilt from the simplified version. This is the lesson from AtlasDL: simplifying each area on its own leaves gaps and overlaps between neighbours. The same shared edges also become the border lines used by network mode.

### AD-17 The antimeridian is handled explicitly
Shapes that cross the 180 degree line, such as Fiji, Russia, the USA and Kiribati, are stored split at the line, but every calculation that needs the whole shape treats it as one: its area, its centre, its bounding box, its outline when isolated, and distances to it. The edges along the 180 degree line are marked as artificial, so they are never announced as a border or coastline, never drawn as an outline and never "crossed". Each of these has its own tests.

### AD-18 No drive letter is ever assumed
The pipeline's data folder is a setting, given on the command line, in an environment variable or in a local settings file that is not in git. Drive E: is only your laptop's value of that setting. The application's pack folder is also a setting, chosen in the pack manager, with a sensible default in the user's own application data folder.

### AD-19 Neighbouring areas get different colours
The pipeline gives each area a colour number so that no two neighbours in the same layer share a colour, using the neighbour list it already builds. The theme turns the numbers into colours. AtlasDL did this with a graph colouring script, and it helps partially sighted users tell neighbours apart.

### AD-20 The Windows installer comes first
A Windows installer is built from Phase 0 onwards, using PyInstaller and NSIS as RecallScore does. The automatic tests still run on macOS for every change, so nothing Windows-only creeps in (PLT-2), but Mac downloads are not produced until a Mac tester is found.

---

## 2. Context

### 2.1 The parts of the system

* The map application: the end user's product, built twice from one core.
  * The desktop application for Windows, with an installer (PLT-1, AD-20). It is also tested on macOS, with Mac downloads to follow when a tester is found (PLT-2).
  * The web application, released alongside the Windows version (PLT-3).
* The data pipeline (mapdata): a command line tool run by the data manager on your laptop (DMT-7). It turns the sources into packs.
* Pack hosting: GitHub Releases for the packs (PCK-4), and GitHub Pages for the web application.
* The listening test tool: a small standalone program for the Phase 1 sound tests (SON-1).

### 2.2 How the parts connect

1. The pipeline reads the sources from its data folder (drive E: on your laptop) and the internet, and writes packs and a catalogue file.
2. The data manager publishes the packs and catalogue to GitHub Releases.
3. The application downloads the catalogue, then whole packs to install them, or pieces of packs on demand.
4. The user's settings, pins, bookmarks and collections stay on their own computer or in their browser. Nothing is sent anywhere, and the application never asks for the device's location (SCP-1).

---

## 3. Architectural principles

### 3.1 Logic once, shells thin
If both shells would need to calculate something, it goes in the core. The shells never work out wording, directions or which feature comes next. This is the rule that made RecallScore's web version possible without duplicating its logic.

### 3.2 Accessibility is structural
The patterns proven in RecallScore are adopted from the start:

* One announcer per shell: all speech goes through a single queue (ACC-1).
* List and tree items take real keyboard focus. The web version does not use aria-activedescendant, which NVDA stayed silent with in RecallScore's testing.
* Escape is never relied on. Every dialog has a Close or Cancel button (ACC-7).
* The menu is a real menu built from the command registry.
* Speak first, redraw second.

### 3.3 Configuration over code
Layers, point of interest categories, Information panel groups, announcement wording, themes, zoom and step lists, and key bindings are data. The PO expects to change the Information panel after testing (INF-10). Changing its groups or their order should be a one-line change.

### 3.4 Text is a tested product
Every announcement is built from a named template in the core. The acceptance scripts compare the exact text with approved baselines (NFR-5). An unintended wording change fails the build.

### 3.5 No device in tests
Tests never open a window, an audio device or a network connection. The shells accept a stand-in audio engine and a stand-in announcer that record what would have happened, as RecallScore does.

### 3.6 Every change is checked before you see it
There is no human developer (DEL-2). Continuous integration runs every test on Windows and macOS, and the web tests in a headless browser, before a phase reaches you.

---

## 4. Technology choices

Each choice gives the reason and the main alternative considered. Every library listed is compatible with GPL-3.0 (SCP-4).

### 4.1 Language: Python
* Python is the main language (DEL-3). The version is pinned to the one used by the current Pyodide release, so the desktop and web run the same Python (3.13 at the time of writing).
* The core uses only libraries that also work in Pyodide: Shapely 2 (geometry, using GEOS), NumPy, and GeographicLib (geodesy). All three are available in Pyodide.
* Alternative considered: Rust or C++ for the core. Rejected for now, because Python is fast enough with precomputed relations (AD-8) and is far easier for Claude Code to maintain and for tests to cover. If a hot spot is found, it can be moved to a compiled extension later without changing the design.

### 4.2 Desktop user interface: PySide6
* PySide6 (Qt 6, LGPL), always the latest release. Qt's accessibility keeps improving, so at the start of each phase Claude Code checks for a newer PySide6, upgrades, and runs the full test suite. Version 6.8 is the minimum, because it added the accessibility announcements that NVDA receives as UI Automation notifications. RecallScore already relies on this.
* PySide6 brings its own copy of Qt, installed by pip. Your separate Qt download for C++ is not used, so it does not matter how old it is.
* The map is a custom widget that paints the core's shape list (AD-6). The Information panel is a standard tree view, the Details panel a read-only text box, and the menu a standard menu bar.
* Alternative considered: wxPython. Rejected because RecallScore has already proven PySide6 with NVDA.

### 4.3 Web user interface: Pyodide in a worker, plain JavaScript
* The core runs in Pyodide inside a Web Worker (AD-9). A small bridge module returns plain dictionaries and lists, never Python objects, following RecallScore's web_api pattern.
* The page itself is plain JavaScript with no framework: a key map, a focus manager, an announcer, a tree, a canvas painter, dialogs and a menu. These are modelled on RecallScore's web modules.
* The web application is a static site on GitHub Pages, so it costs nothing to host.

### 4.4 Screen reader output
* Desktop on Windows: Qt accessibility announcements, which NVDA and JAWS receive as UI Automation notifications. For Braille-only output of spatial labels (SON-3), the NVDA Controller Client library is used when NVDA is running.
* Desktop on macOS: the same Qt announcements, which VoiceOver receives as accessibility announcements.
* Web: the browser's ariaNotify where available, otherwise two alternating live regions, exactly as in RecallScore.

### 4.5 Sound
* Web: the Web Audio API, which has a built-in HRTF panner, plus a low-pass filter for muffling and reverb for the second distance cue.
* Desktop: three candidates, chosen by spike S1:
  * Synthizer, the 3D audio library with HRTF that AtMap used. It has Python bindings. Spike S1 checks that it is still maintained, that it installs on the Python version we use, and its licence.
  * OpenAL Soft (LGPL), a mature 3D audio library with HRTF, used through a small Python binding.
  * The project's own HRTF processing, using a published HRTF data set and NumPy, played through the sounddevice library (PortAudio). This gives the same sound on desktop and web, at the cost of more code.
* Earcons are WAV files (SON-8). Placeholders are generated by a project script until your files arrive.
* Speakers mode (SON-1) is stereo panning plus pitch, provided by the same backends.

### 4.6 The spatial voice
You asked for a spike before choosing (DP82), so spike S6 compares these by ear:

* eSpeak NG (GPL-3.0). It has a library for the desktop and a WebAssembly build for the browser, so both platforms have the same voice. It is small, fast and familiar to many screen reader users. It works on Windows, macOS and Linux, so it also answers your question about the Mac: yes, eSpeak NG runs on a Mac, and its library would be bundled inside the Mac application.
* Piper, a modern neural voice. It sounds much more natural, but its voices are 20 to 60 MB each and it is slower to start, especially in the browser. Its licence must be checked in the spike, because newer releases changed hands.
* The voices already installed in Windows, such as the ones NVDA can use through SAPI or OneCore. Windows can write their speech into memory instead of to the speakers, and that audio can be placed in space. This would only work on the desktop, so the web version would still need eSpeak NG or Piper (DP90).

In every case, the speech is generated as audio samples and placed in space like any other sound. The screen reader's own voice cannot be used, because it cannot be placed in space (DP46).

### 4.7 Data pipeline tools
The pipeline runs only on the build laptop, so it can use heavier libraries than the application:

* pyosmium for reading OpenStreetMap files.
* GeoDesk for Python, for fast queries on the GOL files on drive E: (subject to the licence check in spike S2). AtlasDL already used GeoDesk's C++ library and its query language on these files, which shows it works with the planet file.
* GDAL through pyogrio, for shapefiles and GeoPackages such as Natural Earth, VLIZ and GMBA.
* rasterio, for the GEBCO and CHELSA grids.
* Shapely, GeoPandas and PyArrow, with GeoParquet as the format for working files.
* DuckDB with its spatial extension, where large joins are easier in SQL.
* Wikidata facts are fetched through the Wikidata API in batches and cached on drive E:, rather than downloading the whole Wikidata dump of over 100 GB.

### 4.8 Packaging and continuous integration
* GitHub repository with GitHub Actions (DEL-1).
* Tests run on Windows and macOS for every change, and the web tests run with Playwright in headless Chromium and Firefox (NFR-5). Firefox is your main browser, and NVDA works particularly well with it, so it is tested as fully as Chromium.
* A licence check fails the build if any dependency is not GPL-compatible (SCP-4).
* Windows: PyInstaller and an NSIS installer, as in RecallScore, built from Phase 0 (AD-20). A portable zip is also offered.
* macOS: no downloads at first (AD-20). When a Mac tester is found, a PyInstaller application bundle in a disk image will be built in continuous integration. It will not be signed, because signing costs money, so the release notes will explain how to open it.
* Web: built and published to GitHub Pages by continuous integration.

---

## 5. Components of the application

### 5.1 The layers of the application

From the bottom up:

1. Packs: reading pack files from any source.
2. Store: one view of all installed packs, and the queries on them.
3. World model: the location, heading, zoom, step, orientation, movement mode and current feature.
4. Behaviour: navigation, description, the Information panel, relations, search, sound scene and map scene.
5. Session: the single entry point that runs commands and returns responses.
6. Shells: desktop and web.

Each layer only calls the layers below it.

### 5.2 Core modules

The core Python package is called mapcore. Its modules are:

* geo: geodesy, including distance, bearing, moving a given distance in a given direction, great circles, following a line of latitude, crossing a pole, and the local projections used for quick distance checks. It also formats units, bearings, coordinates and clock faces (ANN-5, LOC-1).
* packs: the byte source interface (local file, range requests, browser cache), the pack archive reader, the catalogue, checksums, version checks (PCK-5) and the tile cache.
* store: the feature store. It answers "what is at this point", "what features of these layers are in this area at this zoom", "get this feature", "get its relations", "get the network near here", "search" and "sample this grid". It merges installed packs using canonical identifiers and tile coverage (AD-13, AD-14).
* layers: the layer catalogue, combining the pack's layer definitions with the user's own changes (SCP-7), and the visibility rule (NAV-13).
* world: the world state and the position history (NAV-10).
* navigation: stepping (NAV-1, NAV-3), hierarchy (NAV-4), network (NAV-5, NAV-6), jumping (NAV-8), driving (NAV-14) and the orientation rules (NAV-11, NAV-12). Each move returns a move result: where it went, the path it followed, and the new heading.
* describe: change detection (ANN-1), the announcement templates, verbosity (ACC-5), the concise Braille format (ACC-6) and the announcement history (ANN-4).
* panel: the Information panel groups (INF-10). Each group is a provider registered in one table, with its name, key, default sort order and whether it is limited to visible features.
* relations: the relation queries: within, contains, bordering, overlapping, crossing, nearby, distance and bearing, and distance along a line (LOC-3, INF-2 to INF-8, INF-12).
* search: name matching and the structured query builder (SRB-1 to SRB-4, INF-9).
* sound: the sound scene. It works out, for each sound, its direction relative to "ahead", its loudness, its muffling and its spoken label (SON-1 to SON-10). It never touches an audio device.
* render: the map scene. It applies the globe projection (VIS-5), chooses the drawing detail for the zoom, and produces the list of shapes and labels with their styles and themes (VIS-1 to VIS-3).
* touch: the touch tracing scene (TCH-1 to TCH-3), using the same projection.
* user: pins, bookmarks, collections, settings, and GeoJSON import and export (USR-1 to USR-5, PLT-5).
* commands: the command registry (AD-3).
* session: the map session, the one object the shells talk to.

### 5.3 The map session
The shells call the session with a command and its arguments. The session returns a response containing:

* announcements, each marked urgent or polite, and with a language where a name needs one (ACC-9)
* earcons to play
* spatial sounds to play, each with its direction, loudness, muffling and optional spoken label
* whether the map must be redrawn
* whether the Information panel is out of date
* dialogs to open, such as the ambiguous "up" menu in hierarchy mode (NAV-4)
* follow-up work that can run in the background, such as building the crossed and passed list

### 5.4 What happens after a key press

Using a step in stepping mode as the example:

1. The shell turns the key into the command "step.forward" (AD-3).
2. Navigation calculates the new position and the path of the step on the ellipsoid.
3. The store finds every area at the new position, from all active layers, whatever the zoom (ANN-7).
4. Describe compares this with the areas at the old position and builds the announcement: the new smallest area, then any larger areas that changed, or just the tick (ANN-1).
5. The session returns the response. The shell speaks it at once. This is the step that must finish within 150 ms (NFR-1).
6. The shell then asks the map to redraw (VIS-1, within 100 ms).
7. In the background, the core builds the crossed and passed list along the step's path, and plays its earcon if something was added (ANN-2). This never delays step 5.
8. If keys arrive faster than they can be handled, only the latest position is announced (ANN-3).

### 5.5 Desktop shell
* Main window with the four regions: map, Information panel, Details and menu bar (UX section 2).
* The map widget paints the shape list and turns keys and mouse actions into commands. It tells Windows where the centre of the map is, so magnifiers follow it (ACC-8).
* Speech goes through one announcer, attached to a real widget, as RecallScore found was necessary.
* Background work, such as the crossed and passed list, filling a panel group, downloading and fetching nearby tiles in advance, runs in a thread pool. Results come back to the user interface thread.
* The audio backend chosen by spike S1.
* Settings and personal data are stored as JSON files in the user's application data folder.

### 5.6 Web shell
* The page holds the same four regions. The map is a canvas. The Information panel is a tree with real focus on its items. The menu is a real menu.
* The worker holds Pyodide, the core and the pack readers. It reads packs with synchronous range requests, which are allowed in workers, and stores downloaded pieces in the browser's private file system (OPFS), so they work offline.
* The page and the worker exchange small messages. Shape lists are passed as numeric arrays, which cross between worker and page without copying.
* Sound uses Web Audio on the page. The spatial voice chosen in spike S6 runs in WebAssembly.
* Settings and personal data are stored in the browser.

### 5.7 Threading and responsiveness
* Desktop: movement runs on the user interface thread, because it is fast and its order matters. Everything slower runs in the background and never holds a lock that movement needs. Decoded tiles are never changed once loaded, so background threads can read them safely.
* Web: the worker handles one message at a time. A queue in the page sends only the latest movement when keys arrive faster than the worker can answer (ANN-3).

---

## 6. Data architecture

### 6.1 Why a custom pack format

The pack format must:

* work offline from a local file on the desktop
* work in the browser, where a 1 GB file cannot be loaded into memory
* support reading pieces over the internet for on-demand data (PCK-3)
* be read by the same code on both platforms
* hold vector features, relations, a network graph, a search index and grids

The options considered:

* SQLite or GeoPackage: excellent on the desktop. In the browser, Python's SQLite module in Pyodide can only open a database held in memory, so a 1 GB regional pack would not fit. Rejected as the shipping format. SQLite is still used inside the pipeline where convenient.
* PMTiles with vector tiles: designed for reading pieces over the internet, and proven by your tilemaker test. But vector tiles store simplified, tile-clipped shapes for drawing, not exact shapes, relations, a network graph or a search index. We would still need a second format for those, and two formats could drift apart. Rejected, although the pack format borrows its idea of one file with a directory.
* A custom archive (chosen): one file with a header, a directory of named pieces, and the pieces themselves, each compressed with zlib. Shapes are stored as WKB, which Shapely reads very quickly. Attributes are compact JSON. It needs only the Python standard library, Shapely and NumPy, and can be read piece by piece from a disk or over the internet.

Two refinements are tested in spike S2:

* Compact coordinates. WKB stores each coordinate as an 8-byte number. Storing them as whole numbers of ten-millionths of a degree (about 1 cm, the same precision OpenStreetMap uses), with each point stored as the difference from the one before, usually makes shapes three to four times smaller after compression. This matters for coastlines with millions of points, such as the UK's. It is adopted if S2 shows the saving is worth it.
* Packs in parts. A pack may be published as several numbered part files, each under a size limit, which the reader joins together. This lets a pack be hosted where single files are limited in size, such as GitHub Pages or Cloudflare Pages (section 9.2).

AtMap's experience supports this choice. Its single Spatialite database worked well on the desktop, but needed the Spatialite and PROJ libraries installed alongside, which made the install large and fragile, and it could not have worked in a browser.

### 6.2 Inside a pack

A pack contains these kinds of piece, each named by a key:

* Manifest: the pack's identifier, version, date, coverage, the application versions it works with, its sources with their licences and dates, and a checksum (PCK-5, DAT-9, DAT-11).
* Attribution text (DAT-9) and the ODbL licence notice (SCP-4).
* Layer definitions (SCP-7).
* Feature records, grouped into buckets by identifier.
* Geometry tiles: exact shapes, cut into tile pieces, used for "what is at this point" and for distances.
* Drawing tiles: simplified shapes for each zoom tier, used for drawing and for the visible lists.
* Relations, grouped into buckets by identifier.
* Network tiles: junctions and links.
* Search shards.
* Grid tiles, for grid layers.

### 6.3 Tiles
* The world is divided into a grid of latitude and longitude tiles that divides by four at each level, like a quadtree.
* Each feature's exact shape is cut into pieces at a tile level suited to its size, so a point test reads only a few small pieces, even for a large country.
* A tile that lies completely inside a large area, such as a tile in the middle of the Pacific Ocean or of Russia, stores just a "fully covered by" note instead of a shape.
* Shapes are split at the antimeridian by the pipeline, and the polar caps are handled explicitly. This is what lets east and west wrap seamlessly (NAV-1) and lets steps cross the poles (NAV-3). Section 6.13 lists what else the antimeridian affects (AD-17).
* A tile with nothing in it, such as most of the open ocean in a regional pack, is not stored at all.

### 6.4 Feature records
Each feature record holds:

* its canonical identifier (AD-13) and its source
* its layer and its type, in plain words, such as "county" or "unitary authority"
* its names, by language, and the alternative names (ACC-9, INF-1)
* its rank, used to choose the smallest area for "where am I" (LOC-2)
* its area or length, its bounding box, and its width, used by the size rule (NAV-13, DP80). The area is measured on the ellipsoid, and the bounding box understands the antimeridian, so Fiji's box runs from 177 degrees east to 178 degrees west, not round the whole world (AD-17).
* its colour number, different from every neighbour in its layer (AD-19)
* a representative point inside it, used when hierarchy mode moves to it (NAV-4)
* the identifiers of the areas that contain it fully, and of those it is partly inside, used by Within, Contains and "up"
* any boundaries it shares exactly with another feature, so the two can be announced once (NAV-4, DP71)
* facts with their source and date, such as population, capital, elevation, the Wikidata identifier and the Wikipedia article title (DAT-7)
* a disputed flag with the source's view, where the source gives one (ANN-6, DAT-8)

### 6.5 Relations stored by the pipeline
* Within and parents: the containment hierarchy, including the parents of parents, which is what makes the ambiguous "up" quick to detect (NAV-4).
* Bordering: neighbours with the shared border length, and areas that nearly touch with the distance between them (INF-2).
* Overlapping: areas that overlap, with the percentage of each covered (INF-5).
* Crossing: for each area, the lines crossing it or forming its border. For each line, the areas it passes through in order from its start, or from its source for rivers (INF-6).
* Counts by type of the features inside each area. These are not used for the visible lists, which depend on the zoom, but they make the world tree (SRB-3) and the pack quality reports quick.

### 6.6 The network graph
* Junctions and links for every network type: roads, paths, railways, waterways, coastlines, borders, and the graticule (NAV-5, DAT-13).
* Junctions are where a choice exists: three or more links meet, or a line ends. Points where only the name changes, or where a line just bends, are marked so that travel passes through them.
* Each link stores its name, layer, length, shape, the junctions at each end, and for rivers, which way is downstream.
* Stop points, such as bus stops and bridges, are attached to links with their distance along the link (NAV-6).
* Borders are built from the shared edges of neighbouring areas at each administrative level, so their junctions are tripoints.
* Links that cross from one pack's coverage into another's join at the same OpenStreetMap node identifiers, so travel continues seamlessly between packs.

### 6.7 Canonical identifiers
* Features keep their source identifier as their canonical identifier: "osm:r62149" for an OpenStreetMap relation, "ne:admin0:FRA" for Natural Earth, "vliz:…" for seas.
* The base pack publishes an identifier register. When a regional pack is built, its features are matched to base features by Wikidata identifier, and failing that by name, type and overlap. A matched feature keeps the base identifier, with the regional identifier recorded as an alias.
* Bookmarks store the canonical identifier and the aliases, so they keep working when packs are updated (USR-2).

### 6.8 Combining installed packs
* Each pack lists the tiles it covers in detail.
* For each tile, the application uses the geometry from the most detailed installed pack that covers it (AD-14).
* Feature records and relations from all installed packs are merged by canonical identifier.
* Where no detailed pack covers a place, the base pack answers, and nothing is said about missing detail (PLT-4).
* The base pack covers every point on Earth with land or sea. The pipeline checks this with a "no gaps" test, which is what guarantees that a place is never announced as unknown (LOC-6).

### 6.9 Drawing detail
* Shapes are stored at several levels of simplification, matched to the zoom list (NAV-13).
* The drawing level for a zoom is chosen so that simplification is never visible on screen.
* At each drawing level, parts of an area that are too small to pass the size rule at that level, such as tiny islands, are left out of the drawing shape. This is what keeps the UK fast to draw at country zoom despite its thousands of islands (section 6.12).
* Simplification is done on shared edges, never on whole areas (AD-16):
  1. Every area boundary in a layer group is broken into edges. An edge runs between two points where three or more areas meet, or where a boundary meets the coast. An edge is shared by every area that uses it, at every level: the edge between Hampshire and Dorset is also part of the edge between South East and South West England.
  2. Each edge is simplified once for each drawing level.
  3. Every area is rebuilt from its simplified edges.
  Neighbours therefore always meet exactly, with no gaps or overlaps, at every level. Shapely's coverage simplification does this for one layer. Spike S2 tests whether it is enough, or whether our own edge builder is needed so that different administrative levels also match each other.
* Exact shapes are always used for "where am I", distances and crossings, so announcements never depend on drawing detail.

### 6.10 The catalogue
* One small file, catalogue.json, lists every published pack: name, version, date, size, checksum, download address, coverage, dependencies, compatible application versions, and the dates of its sources.
* The pack manager reads it to offer installs and updates (PCK-2).

### 6.11 Personal data
* Settings, key bindings, layer choices, pins, bookmarks, collections and position history are stored as JSON, separately from packs (PLT-5, USR-1 to USR-3).
* Collections export to and import from GeoJSON (USR-5).
* The folder where packs are installed is a setting (AD-18). Packs can be large, so the pack manager says how much space is free in that folder and lets the user move it, for example to another drive.

### 6.12 Countries, coastlines and islands
This section answers "architecture thoughts.txt". You found this the hardest part of AtlasDL, so it is the first thing spike S2 tests.

#### The problem
OpenStreetMap's country boundaries (administrative level 2) include territorial waters, usually 12 nautical miles out to sea. Lower levels vary: some follow the low water line, some go out to sea. Standing 2 km off the Brittany coast, a user must hear that they are at sea, not in France (DAT-3).

#### Which administrative level, and how we know territorial waters are gone
* The Countries layer is built from administrative level 2, with the changes in the country units list below.
* We do not need to know whether a boundary includes territorial waters. Every land area is intersected with the OSM land polygons, which contain only land. Whatever water a boundary includes, whether territorial waters, an estuary or a bay, is removed. Where a boundary already follows the coast, nothing changes.
* The same applies at every level: England, Hampshire and Southampton are all cut the same way, so they line up with each other and with the coast.
* The land polygons are produced every day by the OpenStreetMap project's OSMCoastline program from every coastline in the world. It joins the pieces, closes small breaks and reports errors. That is why this avoids the problem AtlasDL hit at Gibraltar, where Spain's coastline stops at the Gibraltar border. We never need a country's coastline to join up. We only ask "which parts of Spain's area are land", and Gibraltar is not in Spain's area to begin with.
* The land polygons are downloaded from osmdata.openstreetmap.de, about 1 GB, under ODbL. They are not on drive E: yet.

#### Slivers and gaps
* Where a boundary runs a little inland of the coastline, a thin strip of land can end up in no country. The pipeline finds land that is in no country. A small strip is given to the country it touches along the longest edge, and listed in the quality report. A large one stops the build for a correction rule (DMT-4).
* The no-gaps test then confirms every point on Earth is in a land area or a sea (LOC-6).

#### Country units
OpenStreetMap's level 2 follows sovereignty, so France's area includes French Guiana, Guadeloupe, Martinique, Réunion and Mayotte. Most people, including you, call French Guiana "French Guiana", not "France".

* A short configuration list of country units says which areas replace a level 2 country in the Countries layer. For France: Metropolitan France (OSM level 3, named "France") plus each overseas region as its own entry. AtlasDL did the same with its "Metropolitan France" and "is in France" filters.
* Each unit records its sovereign state as a fact, so French Guiana's details say "overseas region of France".
* The list is checked against Natural Earth's "map units", which already make these splits. The quality report lists every country whose parts are more than 1000 km apart, so nothing is missed. Expected cases include the Netherlands, Norway (Svalbard), Denmark (Greenland and the Faroe Islands), Portugal, the USA and New Zealand.
* Optionally, a Sovereign States layer, switched off by default, keeps the whole of France as one area (DP86).
* Ceuta and Melilla stay part of Spain, because they are Spain, not territories with their own identity. Spain's area simply has parts in Africa. Which continent they are placed in is DP88.
* Gibraltar is its own entry in the Countries layer, with the United Kingdom as its sovereign state.

#### Islands
The UK has thousands of islands. Each one is part of the land polygons, so it becomes part of whichever areas cover it. Their cost is handled in four ways:

* Point queries stay fast. Exact shapes are cut into small tiles (section 6.3), so "where am I" on Skye reads one or two small pieces, however many islands the UK has.
* Drawing stays fast at low zoom. At each drawing level, islands too small to pass the size rule are left out of the drawing shape (section 6.9). At world zoom the UK is drawn from a few dozen islands. Zoomed in to 1 km, every islet is there, but only the tiles in view are read.
* The pack stays small. Each island is stored once, exactly, in compact coordinates (section 6.1), and the drawing levels hold only the islands big enough for them.
* Islands stay accurate at high zoom, because "where am I", distances and crossings always use the exact shapes.

Named islands:

* Named islands come from OSM place=island and place=islet. Where OSM has only a point with the name, the pipeline gives it the shape of the land polygon part it sits on. AtlasDL's island matching did the same.
* They form an Islands layer, so Skye is announced as "Skye, island" and listed in Contains for Highland.
* Named island groups, such as the Isles of Scilly (place=archipelago), are a later improvement.

Unnamed islands: by default they are simply land, so on one you hear the county and country. Alternatively, unnamed islands above a minimum size could become features announced as "unnamed island" (DP87).

#### Borders and coasts
* Once countries are cut to the land, a shared edge between two countries is a land border, and an edge against the sea is coast.
* Maritime boundaries, such as the one between France and the UK in the Channel, are no longer part of any country, so France and the UK are not "bordering". Bordering lists them as nearly touching, 33 km apart (INF-2). Maritime boundaries return with the optional maritime layer (DAT-3).
* An island shared between countries needs no special handling. Its land is simply in two countries, with a land border across it. This covers Ireland, Usedom (Germany and Poland), Saint Martin (France and the Netherlands), Hispaniola, Timor, Borneo, New Guinea, Märket (Sweden and Finland), and the islands shared by Sweden and Norway, where your earlier work stopped.

#### Test areas, in order
1. The UK: islands, unnamed islands, and the four countries inside it.
2. France: land borders, coast, Metropolitan France and the overseas regions.
3. Spain: the Balearic and Canary Islands, Ceuta and Melilla, Gibraltar, Andorra, and Llívia, a small part of Spain entirely surrounded by France.
4. Then Sweden and Norway, for shared islands and a very complex coast.
5. Then the antimeridian countries (section 6.13).

The checks for each are listed in spike S2 (section 12.3).

### 6.13 The antimeridian
The line at 180 degrees east and west runs through Fiji, Russia's far east, the USA's Aleutian Islands and Kiribati. Antarctica contains the South Pole. OpenStreetMap stores such shapes split at the line. The design handles them as follows (AD-17):

* Storage: shapes are split at the line and every piece is a valid shape.
* Artificial edges: edges along the 180 degree line are marked, and never announced as a border or coastline, drawn as an outline, crossed, or used in network mode.
* Area: measured on the ellipsoid from all the pieces, and compared with Wikidata's figure in the quality report.
* Bounding box and centre: worked out across the line, so Fiji's centre is in Fiji, not in the Atlantic. The centre is used when hierarchy mode or a search jumps to it.
* Isolated drawing (VIS-2) and shape tracing (TCH-1): the drawing is centred on the feature's own centre, so Fiji appears as one compact group of islands, not split to the two edges of the screen.
* Globe drawing: the orthographic projection has no edge at 180 degrees, so pieces either side join seamlessly.
* Moving: stepping, distances and "where am I" across the line are covered by tests in Phase 1.

Tests use Fiji, Russia, the USA, Kiribati and Antarctica, both in spike S2 and permanently in the test suite.

---

## 7. Key algorithms

### 7.1 Stepping
* North-fixed: north and south steps follow the meridian. East and west steps follow the line of latitude, so the change in longitude is the step divided by the radius of that line of latitude. A step that would reach or pass a pole is refused with the blocked sound (NAV-1).
* Cardinal facing: as north-fixed for east and west. North and south steps follow the meridian and may cross the pole, after which the heading is reversed and announced (NAV-3).
* Free facing: the step is a great circle on the ellipsoid, using GeographicLib's direct calculation. The heading on arrival is the direction of travel at the end of the step, which meets NAV-3's 0.01 degree test.
* Every step also returns its path as a line, densified so that it follows the curve of the Earth, for the crossed and passed list.

### 7.2 Where am I
1. Find the tile at the location in the most detailed installed pack.
2. Read its pieces and "fully covered by" notes.
3. Keep every area whose shape contains the point, from every active layer, whatever the zoom (ANN-7).
4. Order them by rank and then by size (LOC-2). The first is the smallest area.

With tiles cached, this takes a few milliseconds.

### 7.3 Change detection
The list of areas at the new position is compared with the list at the old one. The announcement names the new smallest area if it changed, then the larger areas that changed, from smallest to largest (ANN-1). Areas that share a boundary exactly are announced once with both types (DP71).

### 7.4 The visible rule
A feature is visible (NAV-13) when:

* its layer is on
* the zoom is within its layer's zoom range
* for an area, its stored width is at least its layer's minimum size, by default 2% of the zoom distance
* it is at least partly within the view, which is the circle on the Earth's surface whose radius is the zoom distance

The first three tests use only the layer definition and the feature record, so they cost almost nothing. The last uses the drawing tiles at that zoom and a quick local projection, then a precise check for features near the edge.

### 7.5 Crossed and passed
1. Take the step's path from the move result.
2. Read the line, area and point features along it, from layers whose zoom range includes the current zoom. The "in view" test does not apply, because a long step can reach beyond the view (ANN-2).
3. Lines that cross the path are "crossed". Areas the path enters and leaves within the step, not containing either end, are "passed over". Points within the passed nearby distance of the path are "passed", with their closest distance and their bearing from the new position.
4. This runs in the background after the announcement.

### 7.6 Hierarchy
* Up: the parents come from the stored containment, limited to active layers. If every parent contains the smallest parent, it is the next one up. Otherwise the choice is ambiguous, and a menu is offered with the beep (NAV-4).
* Down: the visible features in view whose containing or partly-containing list includes the current feature, grouped by type with counts. Moving to a feature zooms to fit it, so these lists are meaningful (DP77).
* Neighbours: stored, with directions worked out from the location to each neighbour's nearest point, ordered clockwise from ahead.

### 7.7 Network travel
* Entering network mode snaps to the nearest point on the nearest link of the chosen type, or to a junction if one is close (NAV-5).
* Travel follows the link until the next junction where a choice exists, the next stop point if stopping is on, or the step distance, whichever comes first (DP68).
* The heading on arrival follows the orientation rules in NAV-5.

### 7.8 Sound scene
* The direction of a sound is the bearing to the feature minus the bearing that counts as "ahead" in the current orientation (SON-2).
* Loudness follows SON-9: full at one twentieth of the zoom distance or closer, falling evenly with each doubling of distance, to quiet at the edge of the view. Beyond the view, the quietest level with the second cue at full strength.
* Sounds behind the listener are muffled slightly, to reduce front and back confusion.
* The curve's numbers are settings, tuned in the listening test.

### 7.9 Search
* The pipeline builds the index from every name in every language, with accents removed and letters folded to lower case.
* Fuzzy matching uses groups of three letters, which catches common misspellings.
* Results are ranked by a stored importance score based on population, administrative level and how widely the feature appears in Wikipedia. Each result carries a precomputed description that tells places apart, such as "Paris, Île-de-France, France" (SRB-1).

### 7.10 The globe
* The orthographic projection is calculated with NumPy for all the points of a frame at once. Points on the far side of the globe are clipped.
* At street zoom the view is so small that it looks flat (VIS-5).
* The optional heading-up rotation is a rotation of the finished shape list.

---

## 8. The data pipeline

### 8.1 Commands
The commands follow the UX description, section 16:

* mapdata check: confirms the data folder is reachable (on your laptop, drive E:), reports free space and estimates whether a build fits (DMT-7).
* mapdata fetch: downloads sources, or reuses local copies such as the planet files in the data folder.
* mapdata build: builds a pack.
* mapdata report: writes the quality reports (DMT-3).
* mapdata inspect: answers questions about a built pack in plain text, such as "what is at this point" or "show this feature", so a blind data manager can check a pack without a map.
* mapdata publish: uploads packs and the updated catalogue (DMT-5).

### 8.2 Build stages
1. Extract: cut the region from the planet or a regional file, using osmium or GeoDesk.
2. Filter: keep only the tags the layer definitions ask for. The rules are in one configuration file, not chained command lines.
3. Load other sources: Natural Earth, VLIZ, GMBA, HydroLAKES, GEBCO and CHELSA.
4. Repair: fix invalid shapes and record each repair (DMT-3).
5. Clip: cut land areas to the land polygons, so coastlines are real, apply the country units list, and give small slivers of land to their neighbour (DAT-3, section 6.12).
6. Assemble: join river pieces into whole rivers, link wide river areas to their lines, and build multi-part boundaries.
7. Identify: assign canonical identifiers and match base features (AD-13).
8. Enrich: add Wikidata facts, with source and date (DAT-7).
9. Correct: apply the data manager's rules to rename, exclude, reclassify or set a parent (DMT-4).
10. Continents: build continents from groups of countries, split along the configured dividing lines (DAT-12).
11. Relations: containment, identical boundaries, neighbours, overlaps and crossings, and the colour numbers (AD-19).
12. Network: build the junction and link graph and attach stop points.
13. Generalise: break boundaries into shared edges, simplify each edge once per drawing level, rebuild the areas, drop parts too small for each level, and calculate each area's width (AD-16, section 6.9).
14. Index: build the search index.
15. Grids: cut grids into tiles at each resolution.
16. Write: write the pack, its manifest, its attribution and its checksum.
17. Validate: run the coverage test (DAT-1), the no-gaps test (LOC-6), the antimeridian checks (section 6.13), the size budget (PCK-1) and the licence check (DMT-6).

### 8.3 Caching and repeatability
* Each stage writes GeoParquet files to the working folder, named by a fingerprint of its inputs and configuration. If the fingerprint has not changed, the stage is skipped.
* Building the same configuration twice from the same sources gives the same pack, byte for byte (DMT-1). Sorting is fixed and timestamps come from the source dates, not the clock.

### 8.4 Configuration files
* sources: every source, with its address, licence, attribution text and refresh interval. A source with no licence stops the build (DMT-6, DAT-11).
* layers: one file per layer group, holding the layer definitions (SCP-7).
* point of interest categories, with friendly names.
* regions: the pack boundaries, following Geofabrik.
* corrections: the data manager's rules (DMT-4).
* continents: the dividing lines (DAT-12).
* paths: the data folder, with the source, working and output folders inside it, none of which defaults to drive C: for large data (DMT-7). There is no built-in drive letter (AD-18). The data folder is given by, in order: the --data option on the command line, the MAPDATA_ROOT environment variable, or a local paths file that is not in git. If none is set, mapdata stops and explains how to set it.
* country units: the areas that replace a level 2 country in the Countries layer, such as French Guiana (section 6.12).

### 8.5 Safety
* The pipeline keeps a record of every file it creates and never deletes or overwrites any other file (DMT-7). The planet files on E: are never touched.
* Before a build, it estimates the space needed and stops with a clear message if there is not enough.
* Progress is printed as plain lines at each stage, no more than one every 10 seconds. A summary is printed at the end, and full logs go to a text file (DMT-2).

---

## 9. Delivery and hosting

### 9.1 Where things live
* Source code, issues and continuous integration: one public GitHub repository, TobyMap, under your GitHub account Chessel85 (DP84). The design documents live in its docs/design folder, as Markdown only. The HTML copies are not added.
* Application releases: GitHub Releases, tagged by application version. Releases are made from an early phase, whenever a phase is accepted (DP85). There is no separate preview stage. You decide when to invite other people to try it.
* Packs: GitHub Releases, in separate data releases tagged by date, such as "packs-2027-01" (PCK-4).
* Web application: GitHub Pages, built from the repository.

### 9.2 A risk for the web version
GitHub release downloads redirect to a separate download server. Browsers only allow a web page to read a file from another server if that server permits it. I believe GitHub's download server does not permit this, which would stop the web version reading packs straight from GitHub Releases. The desktop is not affected, because these browser rules do not apply to it.

Spike S3 tests this first. If it fails, the fall-back options, in order of preference, are:

1. A Hugging Face dataset repository. You already have an account (DP83). It is free, needs no card, permits browser access and partial downloads, and allows large files.
2. Cloudflare Pages, using your free Cloudflare account. It needs no card, but each file is limited to 25 MB, so packs would be published in parts (section 6.1).
3. GitHub Pages, which does permit browser access, for the base pack only. Its site limit of about 1 GB rules it out for regional packs.

Cloudflare R2 is not considered unless you decide to add a card to your Cloudflare account, which you said you have not done.

The packs would still be published to GitHub Releases for the desktop, with a copy at the fall-back for the web.

### 9.3 Browser storage
Browsers limit how much a site can store, often to a share of free disk space. The pack manager reports how much space is left (UX section 14). Spike S3 measures what Firefox, Chrome and Edge allow. Firefox comes first, because it is your main browser.

---

## 10. Cross-cutting concerns

### 10.1 Performance budget for a step
The target is 150 ms from key press to the screen reader (NFR-1). The planned budget on the desktop:

* turning the key into a command: under 1 ms
* the geodesy of the step: under 1 ms
* "where am I" with cached tiles: under 20 ms, or under 80 ms if a tile must be read from disk
* change detection and wording: under 5 ms
* handing the text to the screen reader: a few ms

Pyodide is typically two to three times slower than desktop Python, so the web budget is tighter. Spike S4 measures it. Tiles around the location are read in advance in the background, so a step rarely waits for the disk.

### 10.2 Robustness
* A pack whose checksum fails, or whose pieces cannot be read, is reported and set aside. The application carries on with the other packs (NFR-4).
* An incompatible pack is refused with a clear message (PCK-5).

### 10.3 Diagnostics for testing
Because you test by ear, the application can record a test trace: every key, every announcement, every earcon and the time each took. A "copy diagnostics" command puts the last few minutes of the trace on the clipboard, so you can paste it into your feedback. This should make reported problems much quicker to reproduce.

### 10.4 Privacy
The application never asks for the device's location, sends no usage data, and only contacts the internet to download packs and catalogue files, or when you open a Wikipedia link (SCP-1, PLT-4).

### 10.5 Languages
The interface is in English, with all its words held in one strings table, so it could be translated later. Names follow the user's preferred language, falling back to the local name, and are marked with their language (ACC-9).

### 10.6 Licences
* The code is GPL-3.0 and the packs are ODbL (SCP-4).
* A third-party notices file lists every library, sound, voice and data set with its licence.
* Every bundled sound records its source and licence (SON-8).

---

## 11. Testing architecture

### 11.1 Test packs
A tiny test pack is built in continuous integration from small checked-in samples: a simplified world, a small detailed area such as the Isle of Wight, and small samples that cross the antimeridian (parts of Fiji and Chukotka) or contain a pole (part of Antarctica). Tests are therefore fast, always give the same results, and never need drive E:.

### 11.2 Kinds of test
* Unit tests for the core.
* Geometry tests: stepping, poles, the antimeridian (section 6.13), great circles and distances, checked against GeographicLib and the figures in the requirements, such as London to Paris (INF-3).
* Announcement baselines: the acceptance scripts are run against the session, and the exact text is compared with approved files (NFR-5).
* Desktop interface tests with pytest-qt, with no window shown and no audio device opened.
* Web tests with Playwright in headless Chromium and Firefox: the key map, focus, the accessibility tree and the announcer queue.
* Performance tests: timed steps on a reference pack, failing if the 95th percentile is over budget.
* Pipeline tests on small samples, including the repeatability test (DMT-1).
* The command coverage test (SCP-2) and the default key clash test (ACC-4).

### 11.3 Acceptance scripts
Each acceptance script is a small file listing key presses and the expected announcements, tied to requirement IDs. The same file produces:

* an automatic test that runs on every change
* a readable checklist for you to follow with NVDA at the phase gate, with headings for each step

So the automatic tests and your manual tests always check the same thing.

### 11.4 The listening test
The listening test tool plays sounds from random directions and distances, asks you which direction you heard, and records the direction played and the direction heard in a CSV file (SON-1). Claude Code analyses the results and tunes the sound settings from them.

---

## 12. Risks and Phase 0 spikes

### 12.1 The main risks
* Countries, coastlines and islands may be harder than expected, as you found with AtlasDL. Handled by spike S2, which starts with the UK, France and Spain before anything else is built on it.
* Web hosting of packs may be blocked by browser rules (section 9.2). Handled by spike S3, with fall-backs.
* Pyodide may be too slow or use too much memory for the 150 ms target. Handled by spike S4. Fall-back: the web version keeps more in memory, or accepts a slightly longer target that you agree.
* HRTF on the desktop may sound different from the browser. Handled by spike S1.
* No built-in voice may be pleasant enough. Handled by spike S6.
* The base pack may not fit 250 MB with the detail wanted. Measured in spike S2 and in Phase 3, then discussed with you (PCK-1).
* OpenStreetMap data is untidy, for example rivers in many pieces, boundaries that almost match, and whole relations that fail to build (AtlasDL found Russia broken in one planet file). Handled by the quality reports and correction rules, starting in spike S2. A relation that fails to build is reported, and the last good version or the Natural Earth shape is used instead, so one broken country never stops a build.
* The macOS version cannot be tested by a person yet (PLT-2). Handled by automatic tests on macOS in continuous integration.
* GeoDesk's licence is not yet confirmed. Checked in spike S2. If it does not fit, the pipeline uses osmium and the .osm.pbf files only, which is slower but works.
* No human developer. Handled by strong tests, short phases, and the CLAUDE.md and design documents kept up to date in the repository.

### 12.2 Spike S1: spatial sound
* Question: which desktop sound backend?
* Method: a small program that plays sounds from chosen directions and distances with each desktop candidate (Synthizer, OpenAL Soft and the project's own HRTF processing) and with Web Audio in Firefox and Chrome. For Synthizer, also check that it is still maintained, that it installs on our Python version, and its licence.
* You listen and give your impressions of direction, front and back, and distance. DP91 asks about your experience with Synthizer in AtMap.
* It decides AD-10, and confirms the plan for the full listening test in Phase 1.

### 12.3 Spike S2: countries, coastlines and islands
* Question: can the pipeline build accurate land-only countries and their divisions, with islands, shared borders and the antimeridian, quickly enough on your laptop, and how big are the results?
* Method, in stages. Each stage builds a small pack in the AD-5 format and is checked with "mapdata inspect" and a picture of the result before the next stage starts:
  1. The UK, France and Spain, from the GOL files and the OSM land polygons, at administrative levels 2, 4 and 6, with the Islands layer.
  2. Sweden and Norway.
  3. Fiji, Russia, the USA, Kiribati and Antarctica.
* Checks:
  * Points just offshore are in the sea, for example 2 km off Brittany, in the Solent, and between Gibraltar and Ceuta.
  * Points on islands are in the right country and county, for example Skye, the Isle of Wight, Mallorca, Corsica and Tenerife.
  * Gibraltar, Andorra and Llívia are correct, and Ceuta and Melilla are part of Spain.
  * French Guiana is its own entry, with France as its sovereign state.
  * The no-gaps test passes, and slivers of land are reported.
  * Neighbours meet exactly at every drawing level, with no gaps or overlaps, including between administrative levels.
  * Shared islands are split correctly between Sweden and Norway.
  * For each antimeridian country: it draws correctly on the globe, its area is within 1% of Wikidata's figure, its isolated drawing is one compact shape, its centre is on the country, and no border or coast is announced along the 180 degree line.
  * The UK's islands: how many there are, named and unnamed, how many are kept at each drawing level, and how long the UK takes to draw at world, country and 1 km zoom.
* Also measured: time, memory, disk use and pack size, with and without compact coordinates (section 6.1). GeoDesk's licence is checked.
* It settles the detail of AD-15 and AD-16, whether GeoDesk is used and whether compact coordinates are used, and gives real sizes for PCK-1. It also answers DP89: whether the base pack's countries come from OSM.

### 12.4 Spike S3: hosting and the browser
* Question: can a web page read pieces of a file from GitHub Releases, and how much can a browser store?
* Method: publish a test file to a release on the TobyMap repository, then read pieces of it from a worker with synchronous requests in Firefox, Chrome and Edge. Test the browser's private file storage limits. If GitHub Releases fails, test Hugging Face, then Cloudflare Pages with a pack in parts.
* It decides the web hosting (DP83).

### 12.5 Spike S4: the core in Pyodide
* Question: is the core fast enough in the browser?
* Method: run Shapely, NumPy and GeographicLib in a Pyodide worker. Read the S2 pack's tiles and time "where am I" and a step, in Firefox and Chrome. Measure start-up time and download size.
* It confirms AD-9 and the web performance target.

### 12.6 Spike S5: the globe, the accessible shell and the installer
* Question: does the four-region window work well with NVDA, can the globe be drawn fast enough, and does the installer work?
* Method: an empty desktop window using the latest PySide6, and a web page, each with the map, the Information panel tree, Details and the menu, plus a globe drawn from Natural Earth countries that turns as you press the arrow keys. Check focus, announcements (including Braille-only through the NVDA Controller Client) and tree navigation with NVDA, using Firefox and Chrome for the web page. Package the desktop window as a Windows installer (AD-20).
* You install it, and try both versions with NVDA.
* It confirms AD-6, AD-20 and the shell patterns.

### 12.7 Spike S6: the spatial voice
* Question: which built-in voice speaks the spatial labels (SON-3, DP82)?
* Method: a small program that speaks the same place names, such as "Berlin", "Bay of Biscay" and "Llívia", from chosen directions, using eSpeak NG, Piper and the Windows voices (section 4.6), plus the web candidates in Firefox. Measure the delay from request to sound, and the download size of each.
* You listen and choose. If you prefer a Windows voice on the desktop, DP90 asks whether the web version may use a different voice.
* It decides the voice for AD-10.

### 12.8 What each spike produces
A short findings document for each, written for you, in the repository's docs/spikes folder, with a recommendation. Where a finding changes a decision here, this document is updated and the change is listed at the top.

---

## 13. Traceability: which component meets which requirements

* commands and the shells: SCP-2, ACC-2, ACC-3, ACC-4, ACC-7
* describe and the announcers: ACC-1, ACC-5, ACC-6, ACC-9, ANN-1, ANN-3, ANN-4, ANN-5, ANN-6, ANN-7
* geo: LOC-1, LOC-7, NAV-1, NAV-3, INF-3, ANN-5
* store and packs: LOC-2, LOC-6, PLT-4, PCK-1 to PCK-5, NFR-1, NFR-4
* layers: SCP-6, SCP-7, NAV-13, DAT-13
* world and navigation: LOC-4, NAV-1 to NAV-14
* relations and panel: LOC-3, INF-1 to INF-10, INF-12
* search: SRB-1 to SRB-4, INF-9
* sound and the audio backends: SON-1 to SON-10
* render and the map widgets: VIS-1 to VIS-5, NAV-9, ACC-8
* touch: TCH-1 to TCH-4
* user: USR-1 to USR-6, PLT-5
* grids in store, sound and describe: INF-11, SON-5, DAT-6
* mapdata: DAT-1 to DAT-13, DMT-1 to DMT-7
* continuous integration and testing: NFR-5, DEL-1, PLT-1, PLT-2, PLT-3
* the phase plan: DEL-2, DEL-4

---

## 14. Questions for you

### Answered since version 0.1
* DP81: yes, I may read AtMap and AtlasDL. Section 15 is the result.
* DP82: a spike decides the voice. This is now spike S6.
* DP83: you have free Cloudflare and Hugging Face accounts, with no card on Cloudflare. Section 9.2 now uses Hugging Face first, then Cloudflare Pages, and drops Cloudflare R2.
* DP84: the repository is TobyMap, public, with the design documents in Markdown only.
* DP85: no preview stage. Releases are made from an early phase, and you decide when to involve others.

### New questions
These are added to "Discussion points.csv" as DP86 to DP92.

* DP86: Country units. French Guiana and the other overseas regions become their own entries in the Countries layer, with France as their sovereign state. Should there also be a Sovereign States layer, off by default, with the whole of France as one area?
* DP87: Unnamed islands. Should unnamed islands above a minimum size, such as 1 hectare, be announced as "unnamed island", or should they simply be land?
* DP88: Continents for distant parts. Should the Canary Islands, Ceuta and Melilla be in Africa, French Guiana in South America, and Hawaii in Oceania, so a country can appear under two continents, as Russia does?
* DP89: Should the base pack's countries and first-level divisions come from OSM, cut to the coast and simplified, instead of Natural Earth, if spike S2 shows they fit the size budget?
* DP90: If a Windows voice is preferred in spike S6, is it acceptable for the web version to use a different voice?
* DP91: What was your experience of Synthizer's direction and distance in AtMap?
* DP92: macOS. Is it acceptable to keep the automatic tests running on macOS, but produce no Mac downloads until a Mac tester is found?

---

## 15. Lessons from AtMap and AtlasDL

You allowed me to read your C++ and Qt projects (DP81). This section records what they did, what worked, what was hard, and what this design takes from them. Nothing here changes the agreed user experience.

### 15.1 What AtMap is
* A Windows desktop application in C++ with Qt 6, version 1.0.1, released as an installer.
* Its map data is one Spatialite database, land.db, about 70 MB, built by AtlasDL. It holds about 5,900 areas and 7,300 points, mostly from Natural Earth at the most detailed scale, plus Marine Regions oceans and seas.
* The window has a compass pane with movement buttons, a location label, and an information pane with tabs such as bordering countries and what is on the map. F6 moves between panes. Speech uses Qt's accessibility announcements.
* Moving is by arrow keys with a step size from 1 m to 1000 km, changed with plus and minus.
* Bordering and contains lists are precomputed into tables by AtlasDL, not worked out while the application runs.
* Each area stores the zoom level at which it becomes big enough to draw, and another for its label.
* Sound uses the Synthizer library, with HRTF sources, a linear distance model, sound types chosen per layer in a settings file, and a beacon.
* The map projection uses the PROJ library.

### 15.2 What AtlasDL is
* A command-line program in C++ with Qt that builds land.db.
* It is driven by schedule files: plain text lists of steps, such as which OSM tags to fetch, which layer to put them in, and which processing step to run next. It reads the planet file with GeoDesk's C++ library and query language.
* For coastlines, it tried to cut each country's boundary with the OSM coastline ways, by finding where the coastline meets the boundary and splicing the coastline in. The notes record this breaking at Gibraltar, where Spain's coastline is interrupted, and the code was still being tried on one country at a time (Finland).
* It fetched Metropolitan France and the French overseas regions separately, and fetched Russia separately, because Russia failed to build from one planet file.
* Islands were fetched as a separate layer and attached to countries through the territorial waters around them.
* Simplification was done on OSM ways, not on whole areas, so neighbours stayed joined. Several simplification levels were stored, and each area was given a zoom band by its size.
* Neighbours were found for areas in the same layer and across layers, such as countries and seas. A Python script gave neighbouring countries different colours.

### 15.3 What this design adopts
* Precomputed relations, as in AtMap's bordering and contains tables (AD-8).
* Simplification on shared edges, not whole areas (AD-16). This is your lesson, and it now applies across administrative levels as well.
* Several drawing levels, with small areas left out of the levels where they are too small (section 6.9). AtMap's zoom bands did this with fixed screen sizes. This design uses the zoom distance instead, so the window size does not matter (DP76).
* Configuration-driven builds. AtlasDL's schedule files become mapdata's configuration files (AD-12).
* Metropolitan France and the overseas regions as separate entries, now as the country units list (section 6.12).
* Islands named from place=island and matched to the land shapes they sit on.
* Neighbour colouring (AD-19).
* GeoDesk and the GOL files on drive E:, already proven by AtlasDL.
* Synthizer as a candidate in spike S1, and the beacon and per-layer sounds, which the requirements already include.
* The F6 movement between regions, which the agreed design already uses.
* A Windows installer from the start (AD-20).

### 15.4 What this design does differently, and why
* Coastlines come from the OSM land polygons, not by splicing coastline ways into each country (AD-15). The land polygons are already joined and checked for the whole world every day, so a break such as Gibraltar's cannot stop a country being built.
* There is no territorial waters layer as a by-product. Water is simply removed, and maritime zones are an optional layer from a dedicated source later (DAT-3).
* There is no Spatialite or PROJ. Both had to be installed alongside AtMap, and neither can run in a browser. The pack format needs only Python, Shapely and NumPy (AD-5), and the globe projection is a few lines of NumPy (section 7.10).
* Geometry is tiled, so even the UK's islands cost only the tiles in view (section 6.3). AtMap clipped areas to the view with a database query each time it drew.
* The Information panel is one tree with groups, rather than tabs (INF-10). This was agreed in the user experience description.
* Areas in the pipeline are processed as whole shapes with Shapely and GEOS, rather than by tracking individual OSM nodes and ways, which is where much of AtlasDL's complexity came from.
* A relation that fails to build, such as Russia's, is reported and replaced by the last good version or Natural Earth's shape, so it never stops a build.

### 15.5 Things to keep in mind
* AtMap's land.db shows that the Natural Earth world at country scale fits comfortably in about 70 MB, including indexes. That supports the 250 MB budget for the base pack (PCK-1).
* AtMap's documentation says it needs about 6 GB of disk space because its maps were not optimised. Packs are designed to avoid that.
