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
* write: writes the pack, with its manifest, attribution, licence and checksum. It must be the last stage.

More stages come with P1-T4 and P1-T16: reading the planet file, cutting areas to the land, the counties, checks, and drawing levels.

## Other files

These are used by spike S2's commands, which stay until task P1-T16 is finished:

* s2_stage1.yaml to s2_stage4.yaml: the spike S2 stages.
* country_units.yaml: the areas that replace a level 2 country in the Countries layer, such as French Guiana.
* county_levels.yaml: the counties record, which levels make each country's Counties layer.

## The run switch

continue.txt, in the repository's top folder, is not a settings file, but builds read it: a first line of no pauses a build, and yes lets it carry on. The MAPDATA_SWITCH environment variable can name another file. The guide says more.
