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
* sound: the sound of the layer's features in "hear its direction" and look around, by event name. (none)

A setting the build does not know, a geometry other than the three, a closer zoom farther than the farther one, or a sound that is not one of the application's stops the build with the reason.

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
* osm-areas: reads the countries and their divisions from the planet file, in a short-lived process of its own. Settings: source (planet), levels (the division levels to read, such as 3, 4 and 5), and box (west, south, east, north), for a trial on one part of the world only. The world build has no box.
* squares: builds the world one grid square at a time, from the land polygons, the areas just read and the VLIZ oceans, and keeps each finished grid square, so a stopped build carries on from there. Settings: sources (land-polygons and vliz-oceans), square_degrees (1 by default), tolerance_m (the base detail in metres; the PO chose 100 on 3 November, DP112), box, and condominiums (land two countries hold together, each with id, name and the two countries).
* join: joins the grid squares into whole areas, gives land in no country to its neighbour or names it "Unclaimed", gives water in no ocean to the ocean beside it, works out the colour numbers, and checks that every quarter of a degree is in a country or a sea (LOC-6). Settings: sliver_width_m and sliver_km2 (what counts as a sliver), unclaimed (known unclaimed land, each with name, point and note) and named_waters (water with no ocean beside it, such as the Caspian Sea, each with id, name and point).
* graticule: adds the lines of latitude and longitude at every whole degree (layer graticule, each marked with the intervals it belongs to: 1, 5, 10, 15 or 30 degrees) and the special lines (layer special-lines): the equator, the prime meridian, the 180 degree meridian, the tropics, the polar circles and the international date line. The 0 degree and 180 degree lines are special lines only. Every line has its points at most 1 degree apart, and keeps all of them in the drawing levels. Settings: year (needed: the tropics and polar circles are worked out for it), source (the key of the Natural Earth geographic lines, for the date line; without it the date line is left out), and layer and special_layer (the layers' ids, graticule and special-lines). Put it before write.
* write: writes the pack, with its manifest, attribution, licence and checksum. Its setting drawing_levels is a list of levels, each with tolerance_m (how far the outline may move), min_km2 (parts smaller than this are left out, but each area keeps its largest part), tile_level (the tile level of its drawing tiles) and view_km (it serves views at least this wide). Each layer is simplified as one coverage at each level, so neighbours meet at every level. Without drawing_levels the pack has none.
* checks: looks up the check places in the pack just written. It must come straight after write. Settings: places (the files in tests/acceptance), box, line_180 (true to check both sides of the 180 degree line, and that no edge jumps across the globe), and area_checks (countries compared with Wikidata's areas, each with name, wikidata_km2, tolerance_pct and note).

The write stage must come last, or be followed only by checks.

## Other files

These are used by spike S2's commands, which stay until task P1-T16 is finished:

* s2_stage1.yaml to s2_stage4.yaml: the spike S2 stages.
* country_units.yaml: the areas that replace a level 2 country in the Countries layer, such as French Guiana.
* county_levels.yaml: the counties record, which levels make each country's Counties layer.

## The run switch

continue.txt, in the repository's top folder, is not a settings file, but builds read it: a first line of no pauses a build, and yes lets it carry on. The MAPDATA_SWITCH environment variable can name another file. The guide says more.
