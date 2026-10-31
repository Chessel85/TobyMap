# Lessons from AtMap and AtlasDL

Copied from section 15 of architecture.md, version 0.2, in Phase 0 (P0-T10). Further lessons found during the spikes are added at the end, under "Lessons from the spikes".

You allowed me to read your C++ and Qt projects (DP81). This section records what they did, what worked, what was hard, and what this design takes from them. Nothing here changes the agreed user experience.

## 1 What AtMap is
* A Windows desktop application in C++ with Qt 6, version 1.0.1, released as an installer.
* Its map data is one Spatialite database, land.db, about 70 MB, built by AtlasDL. It holds about 5,900 areas and 7,300 points, mostly from Natural Earth at the most detailed scale, plus Marine Regions oceans and seas.
* The window has a compass pane with movement buttons, a location label, and an information pane with tabs such as bordering countries and what is on the map. F6 moves between panes. Speech uses Qt's accessibility announcements.
* Moving is by arrow keys with a step size from 1 m to 1000 km, changed with plus and minus.
* Bordering and contains lists are precomputed into tables by AtlasDL, not worked out while the application runs.
* Each area stores the zoom level at which it becomes big enough to draw, and another for its label.
* Sound uses the Synthizer library, with HRTF sources, a linear distance model, sound types chosen per layer in a settings file, and a beacon.
* The map projection uses the PROJ library.

## 2 What AtlasDL is
* A command-line program in C++ with Qt that builds land.db.
* It is driven by schedule files: plain text lists of steps, such as which OSM tags to fetch, which layer to put them in, and which processing step to run next. It reads the planet file with GeoDesk's C++ library and query language.
* For coastlines, it tried to cut each country's boundary with the OSM coastline ways, by finding where the coastline meets the boundary and splicing the coastline in. The notes record this breaking at Gibraltar, where Spain's coastline is interrupted, and the code was still being tried on one country at a time (Finland).
* It fetched Metropolitan France and the French overseas regions separately, and fetched Russia separately, because Russia failed to build from one planet file.
* Islands were fetched as a separate layer and attached to countries through the territorial waters around them.
* Simplification was done on OSM ways, not on whole areas, so neighbours stayed joined. Several simplification levels were stored, and each area was given a zoom band by its size.
* Neighbours were found for areas in the same layer and across layers, such as countries and seas. A Python script gave neighbouring countries different colours.

## 3 What this design adopts
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

## 4 What this design does differently, and why
* Coastlines come from the OSM land polygons, not by splicing coastline ways into each country (AD-15). The land polygons are already joined and checked for the whole world every day, so a break such as Gibraltar's cannot stop a country being built.
* There is no territorial waters layer as a by-product. Water is simply removed, and maritime zones are an optional layer from a dedicated source later (DAT-3).
* There is no Spatialite or PROJ. Both had to be installed alongside AtMap, and neither can run in a browser. The pack format needs only Python, Shapely and NumPy (AD-5), and the globe projection is a few lines of NumPy (section 7.10).
* Geometry is tiled, so even the UK's islands cost only the tiles in view (section 6.3). AtMap clipped areas to the view with a database query each time it drew.
* The Information panel is one tree with groups, rather than tabs (INF-10). This was agreed in the user experience description.
* Areas in the pipeline are processed as whole shapes with Shapely and GEOS, rather than by tracking individual OSM nodes and ways, which is where much of AtlasDL's complexity came from.
* A relation that fails to build, such as Russia's, is reported and replaced by the last good version or Natural Earth's shape, so it never stops a build.

## 5 Things to keep in mind
* AtMap's land.db shows that the Natural Earth world at country scale fits comfortably in about 70 MB, including indexes. That supports the 250 MB budget for the base pack (PCK-1).
* AtMap's documentation says it needs about 6 GB of disk space because its maps were not optimised. Packs are designed to avoid that.

## Lessons from the spikes

* None yet.

