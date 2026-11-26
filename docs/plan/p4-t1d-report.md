# P4-T1d report: roads and paths

## What was done

* A new stage, osm-streets (mapdata/stages/osm_streets.py), reads every main road, street, track and path within the coverage into the layers main-roads, streets and paths, as design section 3.7 says.
* Main roads with a number are joined by number, per country, with the osm-lines stage's rules, imported from osm_lines.py, which is unchanged. An unnamed slip road that meets a numbered road joins it.
* Named ways are joined with the ways of the same name and layer that come within 30 metres of them. Unnamed ways of one layer and type that meet are joined within one parish.
* Every feature's way numbers are in ways.json in the stage's folder. The writing stage does not read it.
* The type words are in mapcore/describe/templates.yaml under details, street_types. They are part of the stage's fingerprint.
* The osm-lines and osm-streets blocks are in great-britain.yaml and hampshire-isle-of-wight.yaml. The osm-streets block is in test-region.yaml.
* The settings are documented in docs/data-manager/configuration.md.

## The test region

* Main roads: 122 ways joined into 9 features.
* Streets: 973 ways joined into 485 features.
* Paths: 980 ways joined into 371 features.

## Points to note

* A cycleway with footway=sidewalk is kept, as the design leaves out only footways that are sidewalks.
* A way is in the parish its middle is in. A single long way that crosses a parish boundary stays one feature.
* The world and Western Europe trial pack settings are unchanged.
* For Great Britain, the joining runs in the build's own process on every way at once, after the reading. The rehearsal should measure its memory.
