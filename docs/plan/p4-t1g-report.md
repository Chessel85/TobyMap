# P4-T1g report: rivers and streams at full detail

Design: docs/plan/p4-t1-design.md section 3.9. Requirements: DAT-2, DAT-3.

## What was done

* A new stage, osm-waterways (mapdata/stages/osm_waterways.py). It reads every river, canal, stream, ditch and drain way within the coverage. Rivers and canals go into the rivers layer, and streams, ditches and drains into the streams layer.
* Ways of one name that meet are joined end to end. Each way keeps the direction it is drawn in, which is the way the water flows. So each feature runs from source to mouth with its sections in order. It uses osm-rivers' own joining function.
* A water named on both river and stream ways, such as Ober Water, is one feature. It goes in the layer and type of most of its length.
* Unnamed ways of one type that meet are joined within one parish. They are named "Unnamed stream", "Ditch", "Drain", "Unnamed river" or "Unnamed canal". These words are new in the templates, under details, unnamed_waterways.
* A river way that the osm-rivers stage has already used is not read again. It is found by the river's Wikidata link, by a feature's id, or by lying along the river's line (within 5 metres for nine tenths of its length). This is needed because osm-rivers keeps no list of its ways, and its code stays unchanged.
* Each feature's way numbers are kept in ways.json, as for streets.
* The osm-rivers and osm-waterways blocks are in great-britain.yaml and hampshire-isle-of-wight.yaml. The test region has osm-waterways only, as osm-rivers cannot read the raw samples.
* The stage's section is in docs/data-manager/configuration.md.

## What the test region gives

* Rivers: 26 ways joined into 19 features (18 rivers, 1 canal), 12 km of line.
* Streams: 202 ways joined into 60 features (54 streams, 3 ditches, 3 drains), 33 km of line.

## Choices made

* Tidal channels, which the Lymington sample has, are not read. The design names only rivers, canals, streams, ditches and drains.
* Nothing in the world pack or the Western Europe trial changes. The osm-water stage's words are left as they were, so its fingerprint does not change.

## Tests

tests/mapdata/test_waterways.py, 21 tests, among them:

* The River Itchen's side streams in Winchester are streams, each running the way the water flows.
* The Weir at Brockenhurst, five stream ways and one river way, is one feature from source to mouth with its sections in order.
* A river the osm-rivers stage made is not read twice, found by its line (River Itchen) or by its Wikidata link (Lymington River).
