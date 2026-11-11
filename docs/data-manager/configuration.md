# Configuration reference

The settings files are in `mapdata\config`, written in YAML. Each section below is one file or folder, with each setting and what it does. The guide, guide.md in this folder, says how the commands use them.

## paths.yaml

The local paths file. It is not in git, because it holds a folder on your own computer (AD-18). Copy `paths.example.yaml` to make it.

* data_folder: the data folder. mapdata reads source files there and writes only in its `tobymap` folder. The `--data` option and the MAPDATA_ROOT environment variable override it.

## sources.yaml

Every source a pack can be built from (DMT-6, DAT-9, DAT-11). Under `sources:`, each source has a key, such as land-polygons, which packs and commands use, and these settings:

* name: the source as the pack's manifest names it. Needed.
* licence: its licence, such as ODbL 1.0. Needed: a source without one stops every build.
* attribution: the credit its licence asks for, written into every pack that uses it. Needed.
* about: a sentence on what it is.
* url: where `mapdata fetch` downloads it from.
* file: where the download is kept, inside the downloads folder.
* find: for a source kept by hand, such as the planet file, where to look in the data folder, as patterns where `*` stands for any text. The newest match is used, by the date in its name, or failing that its file date.
* repo: a file or folder in the repository, such as the test samples.
* date: the data's own date, as year-month-day, when the file's date is not it. Repository files need one, as checking out the repository changes their file dates.
* refresh_days: how many days old the source can be before fetch says a newer copy is due.

Each source also needs either url and file, find, or repo. Every source must also be in docs/design/data sources.md, with a licence compatible with sharing packs under the ODbL.

## layers

One file per group of layers, such as `layers\base.yaml`. Under `layers:`, each layer has:

* id: the layer's identifier, which areas name.
* name: the layer's name, as the application shows it.
* rank: orders what is at a point. Lower ranks come first, then smaller areas (LOC-2). Countries and oceans are 2, regions 4, counties 6.
* kind: land or water. The water stage takes the land out of water layers.

These say how the application shows and sounds the layer (SCP-7). They are written into the pack, and the user can change some of them in the layers list. Each may be left out, and then the default in brackets is used. Changing them makes the build write the pack again, but the stages before the writing are not run again, because they do not use them.

* group: the group the layer is listed under in the layers list, such as Boundaries or Water. (None: the list puts it under "Other layers".)
* geometry: area, line or point. (area)
* switched_on: true or false, whether the layer is on until the user changes it. The word "on" is not used, because YAML reads it as true. (true)
* min_zoom_m and max_zoom_m: the zoom range, as zoom distances in metres. The layer is visible from the closer zoom, min_zoom_m, to the farther one, max_zoom_m (NAV-13). (0, and no limit)
* min_size: for an area layer, how wide an area must be, as a share of the zoom distance, to be visible (DP80). (0.02, which is 2%)
* crossing_earcon: the sound played when a line of the layer is crossed, by its event name in mapcore/describe/earcons.yaml, such as line_crossing. (none)
* crossing_earcons: a sound of its own for some types of line in the layer, as each line type with its sound's event name, such as {equator: equator_crossed, prime-meridian: meridian_crossed}. A line of a type not named here plays crossing_earcon. If the user switches the layer's crossing sound off, every line of it is silent. The special-lines layer uses this, so the meridians, the equator, the tropics and the polar circles sound different from the date line. (none)
* sound: the sound of the layer's features in "hear its direction" and look around, by event name. (none)
* line_style: for a line layer, plain or special. A special layer's lines are drawn thicker and in the theme's colour for special lines, on top of the plain lines. The special-lines layer uses this, so the equator, the prime meridian, the tropics, the polar circles and the date line stand out. Changing it rewrites only the pack, in the stage "writing the pack". (plain)

The layer file `samples.yaml` holds three layers for the test pack only: rivers (a line, with a crossing sound), lakes (an area) and railway stations (a point). The samples stage keeps the lines and points of a line or point layer as they are, and checks that a feature's shape fits its layer.

A setting the build does not know, a geometry other than the three, a closer zoom farther than the farther one, or a sound that is not one of the application's stops the build with the reason.

### The zoom ranges chosen (P2-T4b)

They start from the Shortbread schema (data sources, version 0.7), which says the zoom at which each kind of boundary first appears on a web map. A web map zoom is turned into a view radius: at web zoom 7 a 1,024 pixel wide map is about 1,250 km across, so about 600 km from the centre to the edge. TobyMap's zooms are a list, so the range ends on the nearest zoom in the list.

* countries: no limit. Shortbread draws country boundaries from the whole world down. They are the top of the hierarchy and are heard at every zoom.
* oceans: no limit, for the same reason.
* seas: no limit (P3-T1b). Shortbread names seas and bays as labels on its water from web zoom 0, and the largest, such as the Mediterranean Sea and the Bay of Biscay, are as wide as countries. The smallest are a few kilometres across; the size rule (min_size) leaves out what is too small to see at a zoom, as for every area layer.
* regions: visible to a zoom of 1,000 km (max_zoom_m 1000000). Shortbread draws boundaries at administrative level 4 from web zoom 7, a view radius of about 600 km. Farther out, the regions of large countries are too many to be useful in a list.
* counties: visible to a zoom of 100 km (max_zoom_m 100000). Shortbread draws level 6 boundaries from web zoom 10, a view radius of about 80 km.
* graticule and special lines: no limit. The graticule thins itself by its interval setting (DAT-13), and the special lines are few. They are off at first.
* No layer has a minimum zoom yet: the closest zoom in the list is 100 m, and every layer is useful there.

Where TobyMap differs from Shortbread: it keeps countries at every zoom, because someone listening wants to hear the country however far out they are. Shortbread has no sounds, so there is no other difference yet. Changing a range makes the build write the pack again, which takes about 26 minutes for the world pack.

## packs

One file per pack, such as `packs\test.yaml`. The file name is the pack's name.

* name: the pack's name, the same as the file name.
* title: one sentence on what the pack is.
* version: the pack's version, such as 0.1.0.
* app_versions: the application versions it works with: from, and optionally before.
* coverage: what it covers: kind, world or region.
* layer_groups: the layer files it uses, by name.
* space_needed_mb: about how much disk space a build needs. The build stops before starting if there is less.
* stages: the stages, in order. Each starts with `stage:` and its kind, followed by its own settings.

### The stages

* samples: reads small GeoJSON files, for the test pack. Its setting samples lists them, least detailed first, each with source, the source's key, and file, for a file inside a source that is a folder. Each feature in a sample has id, name, layer and type, and may have local_name, parent, sovereign and replaces. A sample may have a box, a list of rectangles as west, south, east, north; inside it, the sample wins over the samples before it. tests/samples/README.md says more.
* water: takes the land out of every water layer. Its setting land_layer names the layer that is the land, countries if not given.
* osm-areas: reads the countries and their divisions from the planet file, in a short-lived process of its own. Settings: source (planet), levels (the division levels to read, such as 3, 4 and 5), and box (west, south, east, north), for a trial on one part of the world only. The world build has no box. With counties: true, it also reads the areas for the Counties layer (P3-T1c): for each country, the levels in the counties record, or 6, 7 and 8 where the record has none. The planet file is still read once. Each county area is set aside on disk, in a file for its country; then, a country at a time, in the worker processes, an area held twice is kept once (DP104), and an area at a later level with less than 1 km2 outside the levels before it is left out, as it can fill no gap. So the whole world's level 7 and 8 areas are never in memory at once. The setting counties_record names another counties record, as a path from the repository's top folder; the tests use it. Correcting a country's levels in the record makes the next build read the planet file again; a new date alone does not.
* squares: builds the world one grid square at a time, from the land polygons, the areas just read and the VLIZ oceans, and keeps each finished grid square, so a stopped build carries on from there. Settings: sources (land-polygons and vliz-oceans), square_degrees (1 by default), tolerance_m (the base detail in metres; the PO chose 100 on 3 November, DP112), box, and condominiums (land two countries hold together, each with id, name and the two countries), counties: true for a Counties layer by the rule of DP101 (P3-T1a), and seas: the source of the named seas, such as naturalearth-marine-areas, for the Seas, bays and straits layer (P3-T1b, DP168). With seas, all water is in the smallest named sea that covers it, as well as its ocean; Natural Earth's own oceans and unnamed areas name no sea, and its reefs are left out. Natural Earth's coasts are rough, so water between a sea's edge and the real coast takes the sea beside it, the one it shares the longest edge with. With counties, all land is in its country's smallest level 6 area; where level 6 leaves a gap, the level 7 area, then the level 8 area; and where none covers it, the region itself, as "region used as county". A country's levels come from the counties record, mapdata/config/county_levels.yaml, when it has them. The osm-areas stage before must have counties: true as well. A county is never the region itself: where a country's counties are level 5 and a region comes from level 5, the next level is used there. The join stage gives a region used as county over less than 1 km2 in all, a sliver or an islet, to the county beside it or nearest.
* join: joins the grid squares into whole areas, gives land in no country to its neighbour or names it "Unclaimed", gives water in no ocean to the ocean beside it, works out the colour numbers, and checks that every quarter of a degree is in a country or a sea (LOC-6). Settings: sliver_width_m and sliver_km2 (what counts as a sliver), unclaimed (known unclaimed land, each with name, point and note) and named_waters (water with no ocean beside it, such as the Caspian Sea, each with id, name and point). With counties, it lists in the log and in the quality report each country's county levels, the land each holds, every gap filled by a later level, and every region used as county; then it writes the counties record for each country the build read whole, marked "worked out by the build of" the pack and the date. A country cut by the reading box is not written. A corrected entry is never overwritten, and an entry that says the same as what was found keeps its date.
* graticule: adds the lines of latitude and longitude at every whole degree (layer graticule, each marked with the intervals it belongs to: 1, 5, 10, 15 or 30 degrees) and the special lines (layer special-lines): the equator, the prime meridian, the 180 degree meridian, the tropics, the polar circles and the international date line. The 0 degree and 180 degree lines are special lines only. Every line has its points at most 1 degree apart, and keeps all of them in the drawing levels. Settings: year (needed: the tropics and polar circles are worked out for it), source (the key of the Natural Earth geographic lines, for the date line; without it the date line is left out), and layer and special_layer (the layers' ids, graticule and special-lines). Put it before write.
* write: writes the pack, with its manifest, attribution, licence and checksum. Its setting drawing_levels is a list of levels, each with tolerance_m (how far the outline may move), min_km2 (parts smaller than this are left out, but each area keeps its largest part), tile_level (the tile level of its drawing tiles) and view_km (it serves views at least this wide). Each layer is simplified as one coverage at each level, so neighbours meet at every level. Without drawing_levels the pack has none.
* checks: looks up the check places in the pack just written. It must come straight after write. Settings: places (the files in tests/acceptance), box, line_180 (true to check both sides of the 180 degree line, and that no edge jumps across the globe), and area_checks (countries compared with Wikidata's areas, each with name, wikidata_km2, tolerance_pct and note).

The write stage must come last, or be followed only by checks.

## Other files

These are used by spike S2's commands, which stay until task P1-T16 is finished:

* s2_stage1.yaml to s2_stage4.yaml: the spike S2 stages.
* country_units.yaml: the areas that replace a level 2 country in the Countries layer, such as French Guiana.
* county_levels.yaml: the counties record, which levels make each country's Counties layer, in order, and which regions are used as their own county. The build writes it; to correct a country, change its levels and start its "how" with "corrected: " and the reason. Argentina, Tunisia and South Sudan are corrected to level 5 first (P3-T1c).

## The run switch

continue.txt, in the repository's top folder, is not a settings file, but builds read it: a first line of yes lets a build carry on, and anything else, such as no, pauses it (the PO, 10 November 2026). A missing file means carry on. The MAPDATA_SWITCH environment variable can name another file. The guide says more.
