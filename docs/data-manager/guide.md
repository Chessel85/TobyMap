# The data manager's guide

This guide is for whoever builds TobyMap's packs. It covers the mapdata commands as they stand after task P1-T3, and it grows with each task. The settings are described in configuration.md, in this folder.

Every command prints plain lines, suited to a screen reader. There are no progress bars, and progress lines come no closer than 10 seconds apart. Every command is run from the repository's top folder, in PowerShell, as `.venv\Scripts\python.exe -m mapdata` followed by the command. Below, that start is shortened to `mapdata`.

## Before the first build

1. Set the data folder: the folder that holds the planet files and that mapdata works in. There are three ways, and the first one given wins:
   * `--data` and the folder, before the command, such as `mapdata --data <folder> check`.
   * The MAPDATA_ROOT environment variable.
   * The local paths file: copy `mapdata\config\paths.example.yaml` to `paths.yaml` in the same folder, and put the folder after `data_folder:`. This file is not in git.
2. Run `mapdata check`.

mapdata writes only inside the data folder's own `tobymap` folder, and never overwrites or deletes a file it did not create. It keeps a list of every file it has made, in `tobymap\created files.txt`. The planet files and anything else in the data folder are only read.

## mapdata check

Says whether the data folder is ready:

* whether it can be reached. If not, for example because the external drive is not connected, it says so and stops there.
* the free space on the drive of each of its folders: downloads, working and output.
* each planet file found, with its date and size, and which one builds use: the newest.
* the land polygons and their date, with a warning if they and the planet file are more than 14 days apart.

Add `--pack` and a pack's name to hear whether that pack's build fits in the free space.

## mapdata fetch

Gets the sources a build needs, one line for each source, then a summary.

* `mapdata fetch list`: every source, with its licence.
* `mapdata fetch land-polygons`: one source. A source that is already downloaded is reused.
* `mapdata fetch --pack test`: every source a pack uses.
* `mapdata fetch all`: every source.

The planet file is never downloaded automatically, because it is about 96 GB and takes hours to convert; fetch reports the newest copy it finds instead. A source older than its refresh interval is reported as due for a newer copy.

## mapdata build

`mapdata build test` builds the pack called test, from `mapdata\config\packs\test.yaml`. The build:

1. checks, before any work, that every source has a licence and attribution, that the data folder can be reached, and that there is enough free space. If anything is wrong it stops, says what and what to do next, and changes nothing.
2. runs each stage in the pack's settings in turn, with a line such as "Stage 2 of 3: taking the land out of the water layers."
3. copies the pack, and its checksum file, to the output folder, `tobymap\output\test`.
4. prints a summary: the pack, its size, the areas in each layer, the stages run and skipped, and the time taken.

The full log, every line with the time since the start, is beside the pack, in `test build log.txt`.

### Stages are kept

Each stage keeps its results in the working folder, under a fingerprint of everything that could change them: its settings, the sources it reads, the stage before it, and its code. If nothing has changed, the stage is skipped. So a second build with nothing changed takes a moment, and after a change only the stages it affects run again. Building the same settings from the same sources always gives the same pack, byte for byte.

### Workers

`--workers 3` uses 3 processor cores for the slowest steps, which leaves the laptop usable. `--away` uses 6, for when nobody is using the laptop. The default is 1, which is enough for the test pack.

### Pausing a long build with continue.txt

continue.txt, in the repository's top folder, is the switch for long builds. Its first line is yes or no.

* Change the first line to no to have the laptop back. The build finishes the job in hand, keeps everything finished so far, and stops with a line saying it is paused.
* To carry on, change the first line back to yes and run the same command again. The finished stages are skipped.
* With `--wait-for-yes`, the build does not stop for good: it waits, in a small process that uses almost no memory or processor, and carries on by itself when the file says yes again. It checks the file every 30 seconds.

A build reads the switch before each stage. Long stages, such as building the world country by country, also read it between countries.

## Building the world pack

`mapdata build world --workers 8 --wait-for-yes` builds the base pack lite, from `mapdata\config\packs\world.yaml`. It takes several hours. The laptop is sluggish while it runs; change continue.txt to no to pause it.

1. Reading the planet file: about 5 minutes, and about 24 GB of memory is mapped until that step ends.
2. Building the grid squares: the long step. The world is 64,800 grid squares of 1 degree; open sea is written at once, and the rest are built by the workers. Each finished grid square is kept, so a stopped build carries on from there. A line saying the build is still running is written to the log every 5 minutes.
3. Joining the grid squares: the areas, the colour numbers, and the no-gaps check.
4. Writing the pack: the exact shapes in pack tiles, and the drawing levels in drawing tiles.
5. The checks: the check places from the spike S2 stages, each country in the area checks against Wikidata, and both sides of the 180 degree line.

The report to read afterwards is the build log, `world build log.txt`, in `tobymap\output\world`. Lines starting FAIL need a decision. The lines on overlaps, on unclaimed land and on water in no ocean are the ones that become discussion points.

To prove the pack is the same every time (DMT-1), build the write stage again from its kept results and compare the two files byte for byte: `toolsuild_twice.py world`.

## mapdata inspect

Answers questions about a built pack, so it can be checked without a map. The pack is a pack file, or the name of a pack in the output folder.

* `mapdata inspect test manifest`: the pack's name, version, layers, sources with their licences and dates, and attribution.
* `mapdata inspect test feature osm:r154350`: everything the pack holds about one area, by its identifier.
* `mapdata inspect test at 50.69 -1.30`, or without "at": every area at a point, smallest first. Latitude comes first, then longitude; south and west are negative.

## The test pack

The test pack is built from small samples kept in the repository, in tests/samples, which say how they were made. Continuous integration builds it on every push. It holds Natural Earth's world, VLIZ's Atlantic, and OSM detail at England, France and the Channel, the Isle of Wight and the Solent, Fiji either side of the 180 degree line, the Bering Strait, Antarctica at the South Pole, and Niagara Falls.

## When something goes wrong

Each message says what went wrong, the source or area involved, and what to do next. The ones you may meet:

* "The data folder ... cannot be reached": connect the drive, then run the command again.
* "The source ... has no licence": add its licence to `mapdata\config\sources.yaml`.
* "... already exists, and mapdata did not create it": mapdata will not overwrite your file. Move or rename it if it is not needed.
* "The source ... is not in the data folder": run the fetch command the message gives.
