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
  * `southampton-itchen.geojson`: the River Itchen through Southampton (a line, in the layer rivers), Longbridge Lake (an area, in lakes) and Southampton Central station (a point, in stations), read from the planet file of 26 October 2026 with GeoDesk and simplified to 0.0001 degrees (P2-T10c). They are for the tests of Crossed and passed (ANN-2) only. The world pack gets rivers and railways in Phase 3. Their layers are in `mapdata/config/layers/samples.yaml`, used by the test pack only. Made by `tools/make_itchen_samples.py`, which needs the planet file.
  * The Phase 3 samples (P3-T0d), read from the planet file of 26 October 2026 with GeoDesk by `tools/make_phase3_samples.py`, which needs the planet file and takes under a minute. Running it again makes the same files byte for byte.
    * `hampshire-wiltshire.geojson`: England and its 21 counties cut to a box round Hampshire and Wiltshire, at 0.001 degrees, keeping shared borders. England here is the counties joined, so it holds each of them. Before it, the Channel sample's box ended at 51.3 degrees north, cutting Wiltshire in two.
    * `switzerland-neighbours.geojson`: Switzerland and Liechtenstein whole, and France, Germany, Italy and Austria cut to a box round them, at 0.002 degrees, keeping shared borders. France has the same id as in the Channel sample, so it stays one area.
    * `rhine.geojson`: the Rhine from Basel to Schaffhausen, where it is the border of Switzerland and Germany, at 0.0002 degrees, in the layer rivers.
    * `new-forest.geojson`: the New Forest National Park, which overlaps Hampshire and Wiltshire, in the layer national_parks, and Brockenhurst station, inside both the park and Hampshire, so "up" from it offers both (P3-T6a), in the test pack from P3-T3, for INF-5's overlaps and NAV-4's ambiguous up. Its layer is in `mapdata/config/layers/samples.yaml`, as national parks come to the real packs in Phase 4. It is not cut to the coast, so a little of it is in the North Atlantic.
    * `bay-of-biscay.geojson`: the Bay of Biscay as OpenStreetMap has it, an area (layer seas).
    * Not yet in the test pack, because its layer comes with the work item that uses it: `shared-names.geojson`, two Parises, two Portlands, two Newports, and São Paulo the city and the state (layers places and regions), each with "where" to tell them apart, for the tests of search.
  * `crimea.geojson` (P3-T2c): Ukraine and Russia cut to a box round Crimea, both holding Crimea, as their OpenStreetMap outlines do (DP119), with Ukraine's Autonomous Republic of Crimea and Sevastopol, simplified to 0.002 degrees. Made by `tools/make_crimea_samples.py` from the world build's working data (the planet file of 26 October 2026), without reading the planet file: Ukraine's land as the build cut it to the coast, and Russia's own land there with the land of Ukraine's that Russia's outline holds added. The disputes stage makes Crimea a disputed area of its own from them.

* `naturalearth-disputed-crimea.geojson`: Natural Earth's Crimea, from its breakaway and disputed areas at 1:10 million, with its note, simplified to 0.01 degrees. Public domain. Made by `tools/make_crimea_samples.py`.
* `wikidata/`: facts from Wikidata, CC0, for the test pack's wikidata stage (P3-T2a), read offline, as the tests never use the network. Made by `tools/make_wikidata_samples.py`, which needs the data folder and the internet, on 13 November 2026.
  * `links.yaml`: each sample feature's Wikidata link, as the samples have none of their own: Natural Earth's countries from Natural Earth's own links, and the OpenStreetMap areas from OSM's wikidata tags, as kept in the world build.
  * `facts-sample.jsonl`: the facts of those items, and of the items found by name, in the same form as the build keeps them in the data folder.
  * `names-sample.jsonl`: the items with the names of the samples' oceans and seas, for matching by name and place.

Together they are about 5.2 MB.

## How the samples fit together

Each OSM file has a "box", the rectangles it covers. The samples are read least detailed first. Inside each box, the sample replaces the areas read before it in the same layers, so the most detailed wins, as the most detailed pack will (AD-14). An area with the same id as an earlier one, or that names it in "replaces", takes over what is left of it outside the box. So the United States is one area: Natural Earth's shape, with OSM's at Niagara Falls and in the Bering Strait. The land is then taken out of the oceans.

## How they were made

They were made once, on 3 November 2026, by a script that is not kept in the repository, because it read spike S2's packs in format 1, which the pipeline no longer reads.

* The OSM samples except Niagara Falls were cut from spike S2's packs: stage 1 (1 November, the planet file of 20 October 2025) for England, France and the Isle of Wight; stage 3 (2 November) for Fiji, the Bering Strait and Antarctica. Each area's pack tiles inside the box were joined, and each layer simplified with shared borders kept (Shapely's coverage_simplify). The parent of each region and county is the area of the layer above that holds most of it.
* Niagara Falls was read from the planet file of 26 October 2026 with GeoDesk, in a few seconds.
* Natural Earth and VLIZ came from the data folder's downloads, fetched with `mapdata fetch`.

When the base pack lite exists (P1-T4), the samples can be cut from it instead, and the script kept in tools.
