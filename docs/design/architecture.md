# Architecture and High Level Design

Version 0.6, 5 November 2026. Updated for P2-T14, the held key (DP140).

## Changes in version 0.6

* Section 5.7: a held key's steps and clicks keep their own time and never wait for the map to be drawn. On the desktop the map is drawn in the background; in the web version the page plays each click on the sound card's clock. While a key is held the map is drawn at most 4 times a second, and the Information panel waits for the release.
* Section 7.10: a drawing decodes all the shapes of a pack tile together, and keeps them with the pack tile.

## Changes in version 0.5

* Section 5.5: F2 goes to the map, F3 to the Information panel and F4 to Details, from any region (DP106). Ctrl+Alt+Space is dropped.
* Section 8: the build's approach for speed, as agreed in DP107: one planet file for every country, each country kept on its own with its neighbours checked again after a rebuild, and at least two approaches tried on Belgium for each slow step, with mainland France as the regression test (implementation plan, P1-T16).
* Section 14: DP106 to DP108 answered, and DP109 asked.

## Changes in version 0.4

This version brings in the rest of the Phase 0 spikes: spike S2 stages 2 and 3, spike S4, and Piper in the browser (the last part of spike S6), with your answers to DP103 to DP105. Every spike has now reported.

* AD-5 and section 6.1: compact coordinates are kept, because they make packs 4.5 to 4.9 times smaller. Pack tiles are also split when their tile entries hold more than 20,000 points, so no lookup reads one huge pack tile (spike S2).
* AD-9, sections 4.3 and 10.1: the core runs unchanged in a Pyodide worker. After decoding compact coordinates with NumPy, the slowest lookup took 49 ms in Chrome and 34 ms in Firefox, well within the 150 ms target. The web version loads Shapely too (spike S4).
* AD-15, AD-16 and section 6.12: the method that worked for the UK, France, Spain, Norway, Sweden and the 180 degree line countries: cut to the land, clean each layer, then simplify it as one coverage. A check that every outline is closed, after Russia's was found open. Country units need a sea gap test, because the 1,000 km rule misses Svalbard.
* AD-17 and section 6.13: confirmed on Fiji, Russia, the USA, Kiribati and Antarctica, 27 of 27 check places. Outlines that go round the South Pole are extended to it. Jumping to a country uses a point on its land, not the middle of its bounding box.
* Section 4.6: Piper in the browser works in Chrome and Firefox, with ONNX Runtime Web and eSpeak NG for the phonemes. A label takes about 380 ms from request to sound with one thread, or 220 ms with four, against 100 ms on the desktop. The web version uses four threads, as you agreed (DP105). The voice's slow first label was the busy laptop: measured again, it takes about 100 ms.
* Section 4.7: GeoDesk is used (LGPL-3.0). The planet file is read in its own short-lived process.
* Section 6.12: areas that one layer holds twice, such as Sevastopol, are handled as you agreed (DP104).
* Section 8.2: the build repairs open outlines, and the area check against Wikidata takes away inland water first.
* Section 8.6: the cores, tested on stage 3: 13.1 minutes instead of 75.7 (DP103).
* Section 12: the results of spikes S2, S4 and S6, and the risks they settle.
* Section 14: DP103 to DP105 are answered. There are no new questions in this version.

## Changes in version 0.3

This version brings in what spikes S1, S3, S5 and S6 decided, and your answers to DP86 to DP102. Spike S2 (stages 2 and 3), spike S4 and Piper in the browser are not finished. Their results come in a later version, before Phase 0 closes.

* AD-9 and sections 5.6 and 9.1 to 9.3: packs stay on GitHub Releases for the desktop, and the web version uses a copy on Hugging Face, downloaded whole into the browser's private storage (spike S3, DP102). Each site may store about 10 GB.
* AD-10 and sections 4.5 and 5.5: two sound modes from TobyMap's own processing, stereo with pitch by default and HRTF with pitch as an option. Synthizer and OpenAL Soft are not used (spike S1, DP100).
* AD-10 and section 4.6: the spatial voice is Piper, with the Alba voice by default, on the desktop and in the browser. eSpeak NG and the Windows voices are ruled out (spike S6, DP90, DP98).
* Section 4.1: Python 3.14, the version the current Pyodide runs. NumPy in the browser is 32-bit, so the core uses NumPy's own index type.
* Section 4.2: PySide6 6.12.0.
* Section 4.3: the web version downloads about 17 MB and starts in about 9 to 10 seconds (DP96). The Piper voice loads after the map is ready (DP98).
* Section 4.4: the web version uses ariaNotify, which Firefox and Chrome both support, with live regions as the fall-back (DP94).
* Section 4.8: the installer installs for the current user, with no administrator prompt (DP95), and is built on every push.
* Section 5.5: the desktop keys between regions (DP93, DP97), and a known limitation with NVDA in the Information panel.
* Section 5.7: held keys are all carried out, and only the last place is spoken.
* Section 6.9: a frame must be kept to about 10,000 points to be drawn within 100 ms (spike S5).
* Section 6.12: your answers on country units (DP86), unnamed islands (DP87), continents (DP88) and the counties layer (DP101).
* Section 12: the results of spikes S1, S3, S5 and S6 so far, and the risks they settle.
* Section 14: DP86 to DP102 are answered. There are no new questions in this version.
* The words used in this document follow the glossary, docs/design/glossary.md. Older sections that say "piece" are brought into line as they are edited.

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
Each data pack is one file containing many small compressed records (pack tiles, feature records, relations, search index and grids) plus a directory. The application reads only the records it needs. The same reader works on a local file on the desktop, and over the internet with range requests in the browser and for on-demand data (PCK-3). Section 6 explains why this was chosen over SQLite, GeoPackage and PMTiles.

Confirmed by spikes S2 and S4 (2 November 2026):

* Compact coordinates are used. They make packs 4.5 to 4.9 times smaller: the UK, France and Spain in 38.4 MB instead of 172.3 MB, and Norway and Sweden in 72.0 MB instead of 350.4 MB.
* A pack tile is split when its tile entries together hold more than 20,000 points, as well as when one shape in it has more than 4,000. Without that, one of Norway's pack tiles held 332 municipalities and a lookup took 744 ms. With it, lookups took about 20 ms on the desktop.
* Compact coordinates are decoded with NumPy, all of a shape at once, which is about 4.5 times faster than one number at a time (spike S4).
* The reader takes a byte source: a file on the desktop, the browser's private storage, or range requests while a pack downloads.

### AD-6 The visual map is drawn by the core, painted by the shells
The core projects features onto the globe (VIS-5) and produces a list of shapes in screen coordinates, each with a style. The desktop paints that list with Qt, and the web paints it on an HTML canvas. Your tilemaker and PMTiles test was considered and not adopted, because a separate tile set could drift from the data the screen reader uses, and web map tiles use a flat projection rather than the globe.

### AD-7 Geodesy on the Earth's ellipsoid, projection only for drawing
Every distance, bearing and step is calculated on the WGS84 ellipsoid using GeographicLib, which is accurate to well under a millimetre. A projection is used only to draw the map and the touch tracing screen (VIS-5).

### AD-8 Relations are worked out by the pipeline, not at run time
Containment, neighbours with shared border lengths, overlaps, the order in which a river passes through areas, the network graph and the search index are all calculated when a pack is built. The application only looks them up. This is what keeps a step under the 150 millisecond target (NFR-1).

### AD-9 The web version runs the core in a background worker
In the browser, Pyodide and the core run in a Web Worker, so the page never freezes and speech is never delayed. The worker reads packs with synchronous range requests and caches them in the browser's private file storage.

Decided by spike S3 (DP102, 2 November 2026):

* The web version reads its packs from a copy on a TobyMap dataset on your Hugging Face account. Browsers block web pages from reading GitHub Releases, so the desktop keeps using GitHub Releases and the pipeline publishes to both.
* Each read from Hugging Face takes about 0.4 seconds, so the web version does not read records one at a time while stepping. It downloads each pack whole into private storage, and reads records from there, as fast as on the desktop. While a pack is downloading, it uses range requests so the map can be used straight away.
* When you install your first pack beyond the base pack, the web version asks the browser to keep its storage. Firefox's prompt for this works with NVDA.

Full detail is in docs/spikes/S3-hosting-browser.md.

Confirmed by spike S4 (2 November 2026): the core's pack reader runs unchanged in a Pyodide worker in Chrome and Firefox, reading spike S2's Norway and Sweden pack from private storage, with the right answer at all 18 check places. The slowest "where am I" took 49 ms in Chrome and 34 ms in Firefox, and steps with a pack tile cache took 1 ms or less at the median. The browser is about three times slower than the desktop, but within the 150 ms target (NFR-1). Full detail is in docs/spikes/S4-core-in-browser.md.

### AD-10 Spatial sound and the spatial voice behind one interface
The core works out where each sound is (direction, loudness and muffling, SON-9) without playing it. A sound backend on each platform plays it. The spatial voice (SON-3) is Piper, with the Alba voice by default, on the desktop and in the browser (spike S6, DP90, DP98). Its speech is made as sound in memory and placed like any other sound. In the browser the voice runs in a worker of its own (section 4.6).

Decided by spike S1 (DP100, 1 November 2026): two sound modes, both from the project's own processing, with no outside sound library.

* Stereo with pitch, the default: equal-power panning, with sounds behind the user about three semitones lower.
* HRTF with pitch, an option: the MIT KEMAR responses, with the same lower pitch behind.

Without the pitch cue, every HRTF tried, including Synthizer's and OpenAL Soft's, left sounds behind unclear to the PO. On the desktop the sounds are shaped with NumPy and played through sounddevice. The web version does the same with Web Audio: a stereo panner, or its HRTF panner, with the same pitch change. How the pitch cue works with spoken labels, whose own pitch should not change, is tried in Phase 1. Full detail is in docs/spikes/S1-spatial-sound.md.

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

Confirmed by spike S2 on the UK, France, Spain, Norway, Sweden, Fiji, Russia, the USA, Kiribati and Antarctica: 22 of 22, 18 of 18 and 27 of 27 check places passed in its three stages, including points just offshore, on islands, and either side of the 180 degree line. Two additions came from it:

* Every outline is checked to be closed. In the planet file of November 2025, Russia's had an 11 km open end in Crimea, and without a repair Russia had no mainland and Moscow was not in it, with no error. A gap shorter than half a degree is closed with a straight line and listed in the quality report; a longer one stops the build for a correction rule.
* The land polygons stop short of the South Pole, and OSM's outline of Antarctica stops at 85.05 degrees south. The build adds the land south of that, and extends any outline that goes all the way round the pole down to it.

### AD-16 Shared borders are simplified once
Where two areas share a border, that border is simplified once and both areas are rebuilt from the simplified version. This is the lesson from AtlasDL: simplifying each area on its own leaves gaps and overlaps between neighbours. The same shared edges also become the border lines used by network mode.

Confirmed by spike S2: cutting to the land leaves tiny gaps and overlaps where borders meet the coast, and OSM's own borders sometimes overlap. So each layer is cleaned as one coverage first (GEOS, through Shapely), which gives each overlap to the neighbour with the longer shared border, then simplified as one coverage. Every layer in all three stages then met exactly, before and after simplifying. To make the levels match each other too, only the finest level is simplified, and each coarser level is made by joining its simplified parts.

### AD-17 The antimeridian is handled explicitly
Shapes that cross the 180 degree line, such as Fiji, Russia, the USA and Kiribati, are stored split at the line, but every calculation that needs the whole shape treats it as one: its area, its centre, its bounding box, its outline when isolated, and distances to it. The edges along the 180 degree line are marked as artificial, so they are never announced as a border or coastline, never drawn as an outline and never "crossed". Each of these has its own tests.

Confirmed by spike S2's stage 3: the bounding boxes and centres are right across the line, the artificial edges on each side match exactly for Russia and Fiji, and the globe draws Fiji, Chukotka and Antarctica whole, with no stray lines.

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
* Python is the main language (DEL-3). The version is pinned to the one used by the current Pyodide release, so the desktop and web run the same Python. That is Python 3.14, which the current Pyodide release (numbered 314) runs, on the desktop, in the browser and on the build laptop.
* NumPy in Pyodide is 32-bit. Spike S5's first web run failed because the globe used 64-bit numbers for positions in arrays. The core always uses NumPy's own index type (np.intp) for array positions, and a test guards this.
* The core uses only libraries that also work in Pyodide: Shapely 2 (geometry, using GEOS), NumPy, and GeographicLib (geodesy). All three are available in Pyodide.
* Alternative considered: Rust or C++ for the core. Rejected for now, because Python is fast enough with precomputed relations (AD-8) and is far easier for Claude Code to maintain and for tests to cover. If a hot spot is found, it can be moved to a compiled extension later without changing the design.

### 4.2 Desktop user interface: PySide6
* PySide6 (Qt 6, LGPL), always the latest release, which is 6.12.0 in Phase 0. Qt's accessibility keeps improving, so at the start of each phase Claude Code checks for a newer PySide6, upgrades, and runs the full test suite. Version 6.8 is the minimum, because it added the accessibility announcements that NVDA receives as UI Automation notifications. RecallScore already relies on this.
* PySide6 brings its own copy of Qt, installed by pip. Your separate Qt download for C++ is not used, so it does not matter how old it is.
* The map is a custom widget that paints the core's shape list (AD-6). The Information panel is a standard tree view, the Details panel a read-only text box, and the menu a standard menu bar.
* Alternative considered: wxPython. Rejected because RecallScore has already proven PySide6 with NVDA.

### 4.3 Web user interface: Pyodide in a worker, plain JavaScript
* The core runs in Pyodide inside a Web Worker (AD-9). A small bridge module returns plain dictionaries and lists, never Python objects, following RecallScore's web_api pattern.
* The page itself is plain JavaScript with no framework: a key map, a focus manager, an announcer, a tree, a canvas painter, dialogs and a menu. These are modelled on RecallScore's web modules.
* The web application is a static site on GitHub Pages, so it costs nothing to host.
* The first visit downloads about 17 MB (Pyodide, NumPy, Shapely and PyYAML), and starting took 9 to 10 seconds in spike S5, which you accepted (DP96). In spike S4, the core alone was ready in 4 to 4.5 seconds: Pyodide itself took about 2.7 seconds, NumPy and Shapely 0.6, and the core's files 0.8.
* Shapely is loaded in the worker from Phase 1, for the pack reader. It adds 0.8 MB, with GEOS built in (spike S4).
* The Piper voice adds about 60 MB the first time, with the server compressing it. It loads after the map is ready, so TobyMap can be used while the voice downloads (DP98). It is kept in the browser's cache storage, so it downloads only once.

### 4.4 Screen reader output
* Desktop on Windows: Qt accessibility announcements, which NVDA and JAWS receive as UI Automation notifications. For Braille-only output of spatial labels (SON-3), the NVDA Controller Client library is used when NVDA is running.
* Desktop on macOS: the same Qt announcements, which VoiceOver receives as accessibility announcements.
* Web: the browser's ariaNotify, which Firefox and Chrome both support (spike S5). Two alternating live regions, as in RecallScore, are the fall-back for older browsers. You could not tell the two apart with NVDA, so ariaNotify is used unless you report a problem (DP94).

### 4.5 Sound
Decided by spike S1 (AD-10, DP100):

* Two sound modes, on both platforms. Stereo with pitch is the default: equal-power panning, with sounds behind you about three semitones lower. HRTF with pitch is an option: the MIT KEMAR responses, with the same lower pitch behind.
* Desktop: TobyMap's own processing in NumPy, played through the sounddevice library (PortAudio, MIT licence). No outside sound library is used.
* Web: the Web Audio API, with its stereo panner or its HRTF panner and the same pitch change, plus a low-pass filter for muffling.
* Synthizer and OpenAL Soft were tried and are not used. Without the pitch cue, every HRTF, theirs included, left sounds behind unclear to you. Synthizer is also no longer maintained.
* Earcons are WAV files (SON-8). Placeholders are generated by a project script until your files arrive.

### 4.6 The spatial voice
Decided by spike S6 (DP82, DP90, DP98):

* Piper, a neural voice, with Alba, the Scottish voice, as the default. It gave you the best sense of direction. Alba's licence is CC-BY 4.0, so it is credited in the About box and the third-party notices.
* The same voice on the desktop and in the browser (DP90, DP98).
* Piper and its voice add about 75 MB to the installer, and about 60 MB to the web version's first download, with the server compressing it.
* On the desktop, loading the voice takes about 8 seconds, so it is loaded while TobyMap starts. After that each label takes about 100 ms from request to sound, the first one included. The 5 seconds first measured for the first label was the laptop being busy with a build.

Piper in the browser, tried on 2 November 2026:

* The voice runs in a worker of its own, beside the core's worker, so making a label never holds up the map.
* eSpeak NG turns the text into phonemes, using phonemizer.js (Apache-2.0, with eSpeak NG built in, GPL-3.0). ONNX Runtime Web (MIT) runs the Alba voice on them. Both are fetched by tools/fetch_vendor.py, not kept in git.
* The phonemes match the desktop's for 7 of 8 test names. Llívia differs slightly, because the two use different versions of eSpeak NG.
* The page places each label with Web Audio, as for any other sound (section 4.5).
* The voice is ready about 4 to 5 seconds after it starts loading. Most of that is ONNX Runtime preparing the voice, about 3 seconds.
* Each label takes about 380 ms from request to sound with one thread, and about 220 ms with four. Four threads need the site to send cross-origin isolation (glossary), which GitHub Pages cannot send itself.
* As you agreed (DP105), the web version uses four threads, through a small helper script the page loads (a service worker, such as coi-serviceworker, MIT licence) that turns on cross-origin isolation. It is tried first in Phase 2, when the voice is built in (P2-T7). If it causes trouble with NVDA or with downloading packs, the voice falls back to one thread, which works everywhere.
* eSpeak NG was ruled out: you found it dated. The Windows voices were ruled out too, because the web version can't use them (DP90).

In every case, the speech is generated as audio samples and placed in space like any other sound. The screen reader's own voice cannot be used, because it cannot be placed in space (DP46).

### 4.7 Data pipeline tools
The pipeline runs only on the build laptop, so it can use heavier libraries than the application:

* pyosmium for reading OpenStreetMap files.
* GeoDesk for Python (LGPL-3.0, checked in spike S2), for fast queries on the GOL files on drive E:. AtlasDL already used GeoDesk's C++ library and its query language on these files, which shows it works with the planet file. GeoDesk maps the planet file into memory, up to about 24 GB on your laptop, and gives it back only when its process ends. So the planet file is always read in its own short-lived process, which saves what it read to the working folder and ends.
* GDAL through pyogrio, for shapefiles and GeoPackages such as Natural Earth, VLIZ and GMBA.
* rasterio, for the GEBCO and CHELSA grids.
* Shapely, GeoPandas and PyArrow, with GeoParquet as the format for working files.
* DuckDB with its spatial extension, where large joins are easier in SQL.
* Wikidata facts are fetched through the Wikidata API in batches and cached on drive E:, rather than downloading the whole Wikidata dump of over 100 GB.

### 4.8 Packaging and continuous integration
* GitHub repository with GitHub Actions (DEL-1).
* Tests run on Windows and macOS for every change, and the web tests run with Playwright in headless Chromium and Firefox (NFR-5). Firefox is your main browser, and NVDA works particularly well with it, so it is tested as fully as Chromium.
* A licence check fails the build if any dependency is not GPL-compatible (SCP-4).
* Windows: PyInstaller and an NSIS installer, as in RecallScore, built from Phase 0 (AD-20). A portable zip is also offered. Continuous integration builds both on every push.
* The installer installs for the current user, in your own Programs folder, so there is no administrator prompt. It is not signed, so Windows SmartScreen may warn the first time (DP95). In spike S5 the installer was 40 MB and the installed program 140 MB, before Piper.
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
* Tab and Shift+Tab move round the map, the Information panel and Details, but not the menu bar. Alt goes to the menu bar. F2 goes to the map, F3 to the Information panel and F4 to Details, from anywhere (DP93, DP106).
* Sound: TobyMap's own processing in NumPy, played through sounddevice (AD-10).
* Known limitation from spike S5: when the Information panel is rebuilt, Qt 6.12 keeps an out-of-date list of its items for screen readers, so after a key moves to it NVDA doesn't read the item until you arrow. In Phase 1 the panel's items are changed in place instead of being rebuilt.
* Settings and personal data are stored as JSON files in the user's application data folder.

### 5.6 Web shell
* The page holds the same four regions. The map is a canvas. The Information panel is a tree with real focus on its items. The menu is a real menu.
* The worker holds Pyodide, the core and the pack readers. It downloads packs whole into the browser's private file system (OPFS), so they work offline, and reads records from there. While a pack is downloading, it reads records with synchronous range requests, which are allowed in workers (AD-9, DP102).
* The page and the worker exchange small messages. Shape lists are passed as numeric arrays, which cross between worker and page without copying.
* Sound uses Web Audio on the page. The spatial voice, Piper, runs in a second worker, with ONNX Runtime Web, and hands each label to the page as sound (section 4.6).
* Ctrl+Alt+M goes to the menu bar's first menu, Map, without opening it, because the browser keeps Alt for itself (DP93).
* The tree builds each item with its words directly inside it, because Firefox's say current line needs that (spike S5).
* Settings and personal data are stored in the browser.

### 5.7 Threading and responsiveness
* Desktop: movement runs on the user interface thread, because it is fast and its order matters. Everything slower runs in the background and never holds a lock that movement needs. Decoded pack tiles are never changed once loaded, so background threads can read them safely.
* Desktop drawing (P2-T14): the map is drawn in a thread of its own. The scene is worked out and painted onto an image there, and the map widget only shows the latest image. A drawing asked for while one is being made is made next; only the latest is kept.
* Web: the worker handles one message at a time. When keys arrive faster than the worker can answer, the waiting moves are joined and all carried out, and only the last place is spoken (ANN-3). The joining is in the core, so both shells behave the same (spike S5).
* Held keys (DP129, DP140): the core holds the timing rule. The first press steps and is described at once; then a step is due after the repeat delay, and then at the repeat rate. The system's own key repeats only show that the key is still down; if none comes for 1.5 seconds, the key is taken as let go. While a key is held, the Information panel and Details wait for the release, and the map is drawn at most held_draw_rate times a second (4 by default).
  * Desktop: the window's hold clock, a small thread, sleeps until the time the core's hold_due() gives, then tells the window to make the step and its click. Qt's timers on Windows keep to a 15.6 ms beat, which made the clicks uneven by up to 16 ms; Python's sleep is exact to about a millisecond. Python's switch interval is 0.2 ms, so the window never waits long for the drawing thread to let it run.
  * Web: the page keeps the beat from the core's hold_info(): it plays each click on the sound card's clock at its due time and sends the step to the worker, which may be busy drawing. The core also says how many of the next steps will move, so a step that would be blocked at a pole has no click.

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
* Spike S5 found that painting time grows with the number of points. A frame of about 10,000 points or fewer meets the 100 ms redraw target (VIS-1). The whole globe at Natural Earth's 1:50 million scale, about 80,000 points, took 330 ms to paint. So the drawing levels are essential, and each zoom uses the level that keeps the frame to about that size.
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
* The land polygons are downloaded from osmdata.openstreetmap.de, about 900 MB, under ODbL, into the data folder's tobymap\downloads folder.

#### Slivers and gaps
* Where a boundary runs a little inland of the coastline, a thin strip of land can end up in no country. The pipeline finds land that is in no country. A small strip is given to the country it touches along the longest edge, and listed in the quality report. A large one stops the build for a correction rule (DMT-4).
* The no-gaps test then confirms every point on Earth is in a land area or a sea (LOC-6).

#### Country units
OpenStreetMap's level 2 follows sovereignty, so France's area includes French Guiana, Guadeloupe, Martinique, Réunion and Mayotte. Most people, including you, call French Guiana "French Guiana", not "France".

* A short configuration list of country units says which areas replace a level 2 country in the Countries layer. For France: Metropolitan France (OSM level 3, named "France") plus each overseas region as its own entry. AtlasDL did the same with its "Metropolitan France" and "is in France" filters.
* Each unit records its sovereign state as a fact, so French Guiana's details say "overseas region of France".
* The list is checked against Natural Earth's "map units", which already make these splits. The quality report lists every country with parts far from its largest part, so nothing is missed. Expected cases include the Netherlands, Norway (Svalbard), Denmark (Greenland and the Faroe Islands), Portugal, the USA and New Zealand.
* Spike S2 found that distance alone is not enough: most of Svalbard is less than 1,000 km from mainland Norway. The report also lists parts separated from the largest part by more than about 300 km of sea. For the USA, the distance rule found Alaska, Hawaii, Puerto Rico, Guam and the other territories, as expected.
* There is no Sovereign States layer for now. One could be added later, switched off by default, keeping the whole of France as one area, if you decide you want it (DP86).
* Ceuta and Melilla stay part of Spain, because they are Spain, not territories with their own identity. Spain's area simply has parts in Africa. Each part of a country is placed in the continent it is in, so Spain appears under Europe and Africa, as Russia appears under Europe and Asia (DP88).
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

Unnamed islands are announced as "Unnamed island", so standing on one you hear that, then its county and country. There will be many of them. At a high enough zoom, every island is visible, however small (DP87).

What spike S2 counted: the UK's land is in 19,854 parts, of which 11,823 have no name; Norway's is in 118,845 parts, with 7.4 million points. At world zoom the UK is drawn from 3 parts, and at country zoom from 41.

Lakes, lagoons and rivers count as land in the land polygons. So an island in a border lake is joined to the land around it, and Lough Neagh is inside Northern Ireland. Water needs its own layer, over the land.

#### The counties layer
OSM does not use the same level for counties everywhere. Spike S2 found that level 6 leaves gaps: England's metropolitan areas and London have nothing at level 6, Northern Ireland's districts are level 7, and France's overseas departments and Ceuta and Melilla have no level 6 at all. So, as you agreed (DP101):

* The counties layer uses level 6. Where level 6 leaves land uncovered, the gap is filled by the next level down that covers it, level 7 and then level 8. Where nothing below covers it, the region itself is used.
* The pipeline keeps a record, for each country, of which levels make up its counties, so it isn't worked out again on every build.
* The record can be corrected for one country in the pipeline's settings, for example if a country is found to use level 9. The correction is kept and used from then on.
* The quality report lists every gap that was filled, so it can be checked against the OSM wiki.

Spike S2 used this rule for all its countries. Norway and Sweden have nothing at level 6, so their counties come from level 7; Kiribati's come from level 8.

#### Areas held twice in one layer
OSM sometimes holds two areas with exactly the same outline in one layer, one for each side of a dispute. Spike S2 found this for Sevastopol: Ukraine's city and Russia's federal city. As you agreed (DP104):

* The build lists areas in one layer that cover the same land.
* It keeps the one in the country whose outline holds it, which in this planet file is Russia's Sevastopol, and marks it as disputed.
* It keeps the other's name and country for its details, so the dispute is described (ANN-6).
* The overlap check in the quality report also finds one area wholly inside another, which it did not in the spike.

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
* Bounding box and centre: worked out across the line, so Fiji's bounding box is 7.1 degrees wide, not nearly 360.
* Jumping to a country: for a country spread over the ocean, the middle of its bounding box is in the sea (Kiribati's is 56 km from land, and the USA's 1,800 km out in the Pacific). So hierarchy mode and search jump to a point on the country's land, the nearest land to that middle, which the build works out.
* The South Pole: Antarctica's outline is extended to the pole (AD-15), so the pole is in Antarctica, and Antarctica's centre is the pole.
* Isolated drawing (VIS-2) and shape tracing (TCH-1): the drawing is centred on the feature's own centre, so Fiji appears as one compact group of islands, not split to the two edges of the screen.
* Globe drawing: the orthographic projection has no edge at 180 degrees, so the parts either side join seamlessly. The shells fill artificial edges but never outline them, on the globe and in isolated drawings.
* Moving: stepping, distances and "where am I" across the line are covered by tests in Phase 1.

Tests use Fiji, Russia, the USA, Kiribati and Antarctica, both in spike S2 and permanently in the test suite.

Areas against Wikidata, from spike S2: Russia was within 1%. The USA was 3.4% less, because Wikidata counts coastal waters. Antarctica was 1.7% more, probably because the Ross Ice Shelf counts as land, so it needs its own expected figure. Fiji and Kiribati were more, because their lagoons, lakes and wetlands count as land (section 8.2). The areas users hear come from Wikidata, with their source (DAT-7), so these differences only matter for the build's checks.

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
* A drawing has three parts, each timed in the test trace: choosing the shapes in view and cutting them to it, projecting them, and painting them (P2-T14b). The shapes of each pack tile are decoded together, in one pass with NumPy, and kept with the pack tile in the pack tile cache, so a pack tile is decoded once however many drawings use it. This made the first drawing of a new place 3 to 5 times quicker (P2-T14c, docs/plan/p2-t14-drawing-timing.md).

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
4. Repair: fix invalid shapes, close outlines with a short open end (AD-15), and record each repair (DMT-3).
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
17. Validate: run the coverage test (DAT-1), the no-gaps test (LOC-6), the antimeridian checks (section 6.13), the size budget (PCK-1) and the licence check (DMT-6). Each country's land is compared with Wikidata's area after taking away the inland water mapped in OSM, which is reported separately (spike S2).

Spike S2's lessons for the order of work:

* Each slow step in the spike was an operation on a whole country, or a whole gap, made of many thousands of parts, when it needed only the few parts nearby. Steps work on what is nearby, through a spatial index.
* The land polygons are converted once after each download into a land index (glossary), so a build reads only the land tiles in its reading boxes.
* Pack tiles are cut with the cut made for rectangles, and land tiles are joined in groups that touch, which were each several times faster in the spike.
* The counties step needs a faster way to find which areas fill a gap, before France's 34,874 level 8 areas are used (task P1-T16).
* The planet file and the land polygons are taken from close dates.

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

### 8.6 Using the laptop's processor and memory (DP103)
Spike S2 found that most of a build ran on one processor thread, so a world build could take days. As you agreed (DP103), the pipeline uses the laptop's cores as follows. The graphics card is not used: the work is polygon geometry (GEOS, through Shapely), which has no graphics card version for Windows.

* Small independent jobs: every slow step is split into jobs that a pool of worker processes runs, as the OMR project does (mapdata/parallel.py). In the spike this covers cutting areas to the land, the per-layer checks of AD-16, cutting shapes into pack tiles and encoding them, and drawing pictures. Still to do: cutting a very big country region by region, so it is spread across workers.
* Two settings: 3 workers while you use the laptop (the default), and 6 when you are away (`--away`).
* Warning first: before a heavy build, Claude Code tells you how long the laptop will be busy and how many cores it will use. The build's report says the same, and gives the time the last run of the same build took.
* Memory first: memory, not the processor, is the limit, because each worker holds its own shapes. A new job starts only while at least 6 GB is free, so fewer jobs run when memory is short. Below 3 GB free, the build stops cleanly, writes its report and where it stopped, and keeps its cached work. The memory check pauses while the planet file is being read, because that process's mapping of the file is given back when it ends.
* Stop and carry on: each slow step saves its results in the working folder (section 8.3), so a long build can stop and continue later, for example over several nights.
* Timing run first: before the world build, one continent is built and timed, so the world's time can be estimated before it starts.

Tested on spike S2's stage 3 rerun, with 6 workers: the whole run took 13.1 minutes instead of 75.7, with a peak of 3.3 GB of memory instead of 4.6. Drawing the pictures took 36 seconds instead of about 45 minutes, and writing the packs 2 minutes instead of 11.

---

## 9. Delivery and hosting

### 9.1 Where things live
* Source code, issues and continuous integration: one public GitHub repository, TobyMap, under your GitHub account Chessel85 (DP84). The design documents live in its docs/design folder, as Markdown only. The HTML copies are not added.
* Application releases: GitHub Releases, tagged by application version. Releases are made from an early phase, whenever a phase is accepted (DP85). There is no separate preview stage. You decide when to invite other people to try it.
* Packs: GitHub Releases, in separate data releases tagged by date, such as "packs-2027-01" (PCK-4). The web version uses a copy on a TobyMap dataset on Hugging Face (DP102).
* Web application: GitHub Pages, built from the repository.

### 9.2 A risk for the web version
GitHub release downloads redirect to a separate download server. Browsers only allow a web page to read a file from another server if that server permits it. I believe GitHub's download server does not permit this, which would stop the web version reading packs straight from GitHub Releases. The desktop is not affected, because these browser rules do not apply to it.

Spike S3 tests this first. If it fails, the fall-back options, in order of preference, are:

1. A Hugging Face dataset repository. You already have an account (DP83). It is free, needs no card, permits browser access and partial downloads, and allows large files.
2. Cloudflare Pages, using your free Cloudflare account. It needs no card, but each file is limited to 25 MB, so packs would be published in parts (section 6.1).
3. GitHub Pages, which does permit browser access, for the base pack only. Its site limit of about 1 GB rules it out for regional packs.

Cloudflare R2 is not considered unless you decide to add a card to your Cloudflare account, which you said you have not done.

The packs would still be published to GitHub Releases for the desktop, with a copy at the fall-back for the web.

Spike S3 confirmed the risk on 2 November 2026. Chrome, Firefox and Edge all block a web page from reading GitHub Releases, and all three can read from Hugging Face. So the first fall-back, Hugging Face, is used (DP102). Cloudflare Pages and GitHub Pages were not needed.

### 9.3 Browser storage
Browsers limit how much a site can store, often to a share of free disk space. The pack manager reports how much space is left (UX section 14). Spike S3 measures what Firefox, Chrome and Edge allow. Firefox comes first, because it is your main browser.

Spike S3 found a limit of 10 GB for the site in all three browsers, including your own Firefox, which stopped writing at that limit. That is far more than the 250 MB base pack (PCK-1), and enough for several 1 GB packs. The pack manager still asks the browser how much is left, rather than assuming 10 GB.

---

## 10. Cross-cutting concerns

### 10.1 Performance budget for a step
The target is 150 ms from key press to the screen reader (NFR-1). The planned budget on the desktop:

* turning the key into a command: under 1 ms
* the geodesy of the step: under 1 ms
* "where am I" with cached tiles: under 20 ms, or under 80 ms if a tile must be read from disk
* change detection and wording: under 5 ms
* handing the text to the screen reader: a few ms

Pyodide is about three times slower than desktop Python, so the web budget is tighter. Spike S4 measured "where am I" with nothing cached at a median of 6 ms on the desktop and 16 to 18 ms in the browsers, and at most 12 ms and 49 ms. The target stays at 150 ms in the web version too. The store keeps a pack tile cache of decoded shapes, with a size limit, so most steps need no decoding; with it, steps took 1 ms or less at the median. Pack tiles around the location are read in advance in the background, so a step rarely waits for the disk.

The spatial label comes after the announcement and does not count towards the 150 ms. It takes about 100 ms more on the desktop, and about 220 ms in the browser with four threads (section 4.6).

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
* Countries, coastlines and islands may be harder than expected, as you found with AtlasDL. Largely settled by spike S2: the method worked on ten countries, including the 180 degree line and the South Pole. What remains is speed for the whole world, above all the counties step (P1-T16).
* Web hosting of packs may be blocked by browser rules (section 9.2). Spike S3 confirmed it: the web version uses a copy on Hugging Face (DP102).
* Pyodide may be too slow or use too much memory for the 150 ms target. Settled by spike S4: the slowest lookup took 49 ms in the browser, and Python used 52 MB.
* HRTF on the desktop may sound different from the browser. Settled by spike S1: both use the same processing with a pitch cue, and stereo with pitch is the default.
* No built-in voice may be pleasant enough. Settled by spike S6: Piper's Alba voice, on the desktop and in the browser.
* The base pack may not fit 250 MB with the detail wanted. Measured in spike S2 and in Phase 3, then discussed with you (PCK-1).
* OpenStreetMap data is untidy, for example rivers split into many sections, boundaries that almost match, and whole relations that fail to build (AtlasDL found Russia broken in one planet file). Handled by the quality reports and correction rules, starting in spike S2. A relation that fails to build is reported, and the last good version or the Natural Earth shape is used instead, so one broken country never stops a build.
* The macOS version cannot be tested by a person yet (PLT-2). Handled by automatic tests on macOS in continuous integration.
* GeoDesk's licence. Settled by spike S2: it is LGPL-3.0, which is compatible.
* One broken outline can lose a whole country without an error, as Russia's did. Handled by the outline check (AD-15).
* No human developer. Handled by strong tests, short phases, and the CLAUDE.md and design documents kept up to date in the repository.

### 12.2 Spike S1: spatial sound
* Question: which desktop sound backend?
* Method: a small program that plays sounds from chosen directions and distances with each desktop candidate (Synthizer, OpenAL Soft and the project's own HRTF processing) and with Web Audio in Firefox and Chrome. For Synthizer, also check that it is still maintained, that it installs on our Python version, and its licence.
* You listen and give your impressions of direction, front and back, and distance. DP91 asks about your experience with Synthizer in AtMap.
* It decides AD-10, and confirms the plan for the full listening test in Phase 1.
* Result (DP100): stereo with pitch by default and HRTF with pitch as an option, both from TobyMap's own processing. Findings: docs/spikes/S1-spatial-sound.md.

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
* Result: the method works (AD-15, AD-16, AD-17). Stage 1, the UK, France and Spain, passed 22 of 22 places; stage 2, Norway and Sweden, 18 of 18; stage 3, the 180 degree line and the South Pole, 27 of 27. GeoDesk and compact coordinates are used. The packs, at full OSM detail, were 38 to 72 MB for each stage, with compact coordinates. Whether the world's countries at base pack detail fit 250 MB is measured with the base pack lite in Phase 1 (P1-T4, DP89). Stage 1's whole run with the new counties rule, and stage 4, Argentina, moved to Phase 1 (P1-T16). Findings: docs/spikes/S2-countries-coastlines.md.

### 12.4 Spike S3: hosting and the browser
* Question: can a web page read pieces of a file from GitHub Releases, and how much can a browser store?
* Method: publish a test file to a release on the TobyMap repository, then read pieces of it from a worker with synchronous requests in Firefox, Chrome and Edge. Test the browser's private file storage limits. If GitHub Releases fails, test Hugging Face, then Cloudflare Pages with a pack in parts.
* It decides the web hosting (DP83).
* Result (DP102): browsers cannot read GitHub Releases, and can read Hugging Face. The web version downloads packs from Hugging Face into private storage, which allows about 10 GB. Nothing was published to TobyMap's repository: the tests used files other projects had published. Findings: docs/spikes/S3-hosting-browser.md.

### 12.5 Spike S4: the core in Pyodide
* Question: is the core fast enough in the browser?
* Method: run Shapely, NumPy and GeographicLib in a Pyodide worker. Read the S2 pack's tiles and time "where am I" and a step, in Firefox and Chrome. Measure start-up time and download size.
* It confirms AD-9 and the web performance target.
* Result: confirmed. The core runs unchanged, and after decoding with NumPy every lookup was within 49 ms in the browser. Findings: docs/spikes/S4-core-in-browser.md.

### 12.6 Spike S5: the globe, the accessible shell and the installer
* Question: does the four-region window work well with NVDA, can the globe be drawn fast enough, and does the installer work?
* Method: an empty desktop window using the latest PySide6, and a web page, each with the map, the Information panel tree, Details and the menu, plus a globe drawn from Natural Earth countries that turns as you press the arrow keys. Check focus, announcements (including Braille-only through the NVDA Controller Client) and tree navigation with NVDA, using Firefox and Chrome for the web page. Package the desktop window as a Windows installer (AD-20).
* You install it, and try both versions with NVDA.
* It confirms AD-6, AD-20 and the shell patterns.
* Result: confirmed, after five NVDA tests. Each frame must be kept to about 10,000 points (section 6.9). One known limitation remains in the desktop Information panel (section 5.5). Findings: docs/spikes/S5-globe-shell-installer.md.

### 12.7 Spike S6: the spatial voice
* Question: which built-in voice speaks the spatial labels (SON-3, DP82)?
* Method: a small program that speaks the same place names, such as "Berlin", "Bay of Biscay" and "Llívia", from chosen directions, using eSpeak NG, Piper and the Windows voices (section 4.6), plus the web candidates in Firefox. Measure the delay from request to sound, and the download size of each.
* You listen and choose. If you prefer a Windows voice on the desktop, DP90 asks whether the web version may use a different voice.
* It decides the voice for AD-10.
* Result: Piper with the Alba voice (section 4.6), on the desktop and in Chrome and Firefox. About 100 ms from request to sound on the desktop, and about 220 ms in the browser with four threads (DP105). Findings: docs/spikes/S6-spatial-voice.md.

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

### Answered since version 0.2
* DP86: no Sovereign States layer for now. It can be added later if you want it (section 6.12).
* DP87: unnamed islands are announced as "Unnamed island", and at a high enough zoom every island is visible (section 6.12).
* DP88: each part of a country is in the continent it is in, so a country can be under two continents (section 6.12).
* DP89: the base pack's countries and first-level divisions come from OSM if spike S2 shows they fit the size budget.
* DP90: no Windows voices. The desktop and web use the same voice (section 4.6).
* DP91: you had no problems with Synthizer in AtMap, and it was compared in spike S1. It is not used (section 4.5).
* DP92: the automatic tests keep running on macOS, with no Mac downloads until a Mac tester is found.
* DP93: Tab moves round the map, the Information panel and Details only. Alt, or Ctrl+Alt+M in the web version, goes to the menu bar.
* DP94: the web version uses ariaNotify (section 4.4).
* DP95: the installer installs for the current user, with no administrator prompt (section 4.8).
* DP96: the web version's 17 MB download and 9 to 10 second start are acceptable (section 4.3).
* DP97: a key goes to the map from anywhere. It is now Ctrl+Alt+Space, because Ctrl+Alt+G was taken on your laptop.
* DP98: Piper's Alba voice in the browser too, loaded after the map is ready (section 4.3).
* DP99: V says the size of the visible map, and Z the grid value.
* DP100: two sound modes from TobyMap's own processing (AD-10).
* DP101: the counties layer fills gaps from the next level down, and the pipeline keeps a record of each country's levels (section 6.12).
* DP102: packs on GitHub Releases for the desktop, and a copy on Hugging Face for the web (AD-9).

### Answered since version 0.3
* DP103: the build uses the laptop's cores, 3 workers by default and 6 when you are away, tested on stage 3 (section 8.6).
* DP104: areas held twice in one layer, such as Sevastopol, keep the one in the country whose outline holds it, marked as disputed (section 6.12).
* DP105: the web version uses four threads for the voice, through a helper script that turns on cross-origin isolation, tried first in Phase 2 (section 4.6).

### Answered since version 0.4
* DP106: F2, F3 and F4 go to the map, the Information panel and Details from any region, on the desktop and the web (section 5.5).
* DP107: no time limits for the build; at least two approaches are tried for each slow step, on a small dataset, and the fastest is kept (implementation plan, P1-T16).
* DP108: a map display setting for outlines and fill colours, built with the themes in Phase 2 (VIS-2).

### New questions
* DP109: whether the Information panel's groups keep their own keys, such as I for Contains, now that F3 goes to the panel.

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
