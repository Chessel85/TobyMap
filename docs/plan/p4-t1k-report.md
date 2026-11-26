# P4-T1k report: relationships, facts and memory at street scale

Written by Claude Code, 26 November 2026, for the orchestrator and the product owner. Design: docs/plan/p4-t1-design.md section 3.12.

## What was done

* The relationships stage has a new setting, light_layers, empty by default. A feature of a light layer gets only the areas it is in ("in") or partly in ("partly", with the share), and, for a line, the areas of the crossing_areas layers it passes through, in order from its start. It gets no neighbours, nothing nearly touching, no overlaps and no outline. It holds nothing, no area lists it or counts it, and two features of light layers are never compared, which is where the time is saved.
* great-britain.yaml and hampshire-isle-of-wight.yaml name the light layers of design 3.12: main roads, streets, paths, streams, land use, parks, school grounds, stops, shops and food, services, street furniture and villages. Their crossing_areas add districts and parishes. test-region.yaml has the same settings, as its samples hold every one of those layers.
* The wikidata stage has a new setting, layers, every layer by default. The two regional packs name the countries, regions, counties, islands, districts, parishes, oceans, seas, lakes, rivers, parks and national parks. A feature of another layer keeps its Wikidata link, but nothing is fetched for it.
* docs/data-manager/configuration.md describes both settings.

## Tests

* tests/mapdata/test_light_layers.py, new: a street in light_layers has its parish, district and county in "in", its parishes in order in its crossings, and no neighbours; light areas hold nothing and are counted nowhere; the regional test pack's streets have their parishes; the wikidata layers setting.
* The test pack's relationships with light_layers empty are the same, byte for byte, as the file made before the change (its SHA-256 is held in the test, compared only on Windows with the same geometry library and NumPy versions).
* Run: test_light_layers, test_relationships, test_wikidata, test_core_rules, test_coverage and test_match. 101 passed, 1 expected failure, none skipped.

## Memory: features.json loaded whole for Great Britain

Measured on the regional test pack's features (2,389 features), and with made-up shapes:

* A street-scale record takes about 600 bytes as Python objects (145 bytes in features.json).
* A shape takes about 360 bytes, plus about 24 bytes a point; shapes.wkb holds about 18 bytes a point.

Scaled to Great Britain's figures in design 7.3 (about 4 million features, about 100 million points):

* Records: about 2.4 GB.
* Shapes: about 3.9 GB.
* While loading, the file's text and the shapes' bytes as well: about 2.4 GB more.
* So about 6.3 GB once loaded, and about 8.7 GB at the peak of loading.

That is under 12 GB, so no stage was changed to load fewer layers. P4-T1j measures the true figures.

## For P4-T1j to watch

* The relationships stage's top boxes are 45 degrees, so all of Great Britain falls in one or two jobs: one worker would compare nearly everything, with a second copy of the shapes in that worker, on top of the 6 to 9 GB in the main process. If the rehearsal shows the relationships stage near 12 GB, or slow on one core, a smaller top_deg in the regional packs' relationships block (such as 1 degree) spreads the work over the workers without changing what is worked out. It was not set here, as the design did not ask for it.
