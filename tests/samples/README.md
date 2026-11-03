# The test pack's samples

These small files are built into the test pack by `python -m mapdata build test` (architecture 11.1, P1-T3). The settings are in `mapdata/config/packs/test.yaml`, and the sources, with their licences, in `mapdata/config/sources.yaml`. Continuous integration builds the test pack on every push, and the tests build it once per run, so the automatic tests never need the data folder.

## The files

* `world-naturalearth-110m.geojson`: Natural Earth's 177 countries at 1:110 million, public domain. Ids are "ne:" and the country's three-letter code.
* `oceans-vliz-atlantic.geojson`: the North and South Atlantic Oceans from VLIZ Global Oceans and Seas, version 1, CC-BY 4.0. Simplified to 0.05 degrees, and to 0.002 degrees around England, France and the Channel. Small islands are left out.
* `osm/`: OpenStreetMap areas, ODbL 1.0, © OpenStreetMap contributors. Each file says so in its "licence" member.
  * `england-france-channel.geojson`: countries, regions and counties, simplified to 0.001 degrees (about 100 metres).
  * `isle-of-wight-solent.geojson`: the same areas at 0.0001 degrees (about 10 metres).
  * `fiji.geojson`: Fiji either side of the 180 degree line, at 0.001 degrees.
  * `bering-strait.geojson`: Russia and the USA, with Big and Little Diomede, at 0.002 degrees.
  * `antarctica-south-pole.geojson`: Antarctica south of 86 degrees south.
  * `niagara-falls.geojson`: Canada, Ontario, the USA, New York and their counties at Niagara Falls, at 0.0001 degrees.

Together they are about 4 MB.

## How the samples fit together

Each OSM file has a "box", the rectangles it covers. The samples are read least detailed first. Inside each box, the sample replaces the areas read before it in the same layers, so the most detailed wins, as the most detailed pack will (AD-14). An area with the same id as an earlier one, or that names it in "replaces", takes over what is left of it outside the box. So the United States is one area: Natural Earth's shape, with OSM's at Niagara Falls and in the Bering Strait. The land is then taken out of the oceans.

## How they were made

They were made once, on 3 November 2026, by a script that is not kept in the repository, because it read spike S2's packs in format 1, which the pipeline no longer reads.

* The OSM samples except Niagara Falls were cut from spike S2's packs: stage 1 (1 November, the planet file of 20 October 2025) for England, France and the Isle of Wight; stage 3 (2 November) for Fiji, the Bering Strait and Antarctica. Each area's pack tiles inside the box were joined, and each layer simplified with shared borders kept (Shapely's coverage_simplify). The parent of each region and county is the area of the layer above that holds most of it.
* Niagara Falls was read from the planet file of 26 October 2026 with GeoDesk, in a few seconds.
* Natural Earth and VLIZ came from the data folder's downloads, fetched with `mapdata fetch`.

When the base pack lite exists (P1-T4), the samples can be cut from it instead, and the script kept in tools.
