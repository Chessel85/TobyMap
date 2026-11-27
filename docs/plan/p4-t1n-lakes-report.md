# P4-T1n: lakes lying in the sea (DP224)

27 November 2026. Your answer to DP224 was "Accept recommendation". This is done, tested and tried on the Western Europe trial's data on disk. Nothing is committed, and no pack was built.

## What changed

The lakes are made by the osm-layer stage, which reads them from the planet file. It now has a new setting, in_sea, in the world pack and the Western Europe trial:

* A lake with more than half its area in the oceans and seas layers is left out, as the sea already holds it.
* A lake that overlaps the sea less than that keeps only its part outside the sea, so its shore meets the coast.
* A lake cut to nothing, or only to slivers under 1 hectare, is left out too.
* Areas are measured on the Earth's ellipsoid, as elsewhere in the build.
* The share, one half, is in the pack's settings (share: 0.5). The build log lists each lake left out or cut, with its share in the sea.

The England, Great Britain and Hampshire packs do not have the setting yet. Their small lakes and ponds come from another stage, osm-water, which this work does not change.

## Tests

Seven new tests in tests/mapdata/test_lakes.py cover these cases:

* A lake wholly or mostly in the sea is left out.
* A lake partly in the sea is cut.
* A lake on land, or one that only touches the sea, is unchanged.
* A lake cut to slivers is left out.
* The setting is in the world and trial packs.

They pass, as do the tests of the stages that read lakes and places. The test pack does not use this stage, so its expected results are unchanged.

## The trial, on the data on disk

The stage was run alone on the trial's data. It took 60 seconds and used at most 341 MB of memory. The lakes went from 550 to 541.

### Left out: 9 lakes, each 97% or more in the sea

* Ringkøbing Fjord, Denmark, 99% in the sea
* Nissum Bredning, Denmark, 99.8%
* Oderhaff, Germany and Poland, 99.7%
* Großer Jasmunder Bodden, Germany, 99%
* Ria Formosa, Portugal, 98%
* Sado Estuary, Portugal, 99%
* Loch Ewe, Scotland, 99%
* Little Loch Broom, Scotland, 98%
* Dumfries Channel, Scotland, 100%

### Cut to their part outside the sea: 5 lakes

Each loses less than 1% of its area, a thin strip where its shore crosses the coast.

* Venetian Lagoon
* Marano Lagoon
* Laguna di Grado
* Eastern Scheldt
* Deltageul

Every other lake is unchanged.

### One more lake in the HydroLAKES check

The check against HydroLAKES now finds one lake of 100 km2 or more with no lake near it. That lake has no name in HydroLAKES, but it is Ringkøbing Fjord, which the sea now holds. This is expected.

## What a rebuild runs again

* World pack and Western Europe trial: the lakes' stage and every stage after it. That is 17 stages, from osm-layer to the checks. The countries, the grid squares, the join, the graticule and the continents are not run again.
* England, Great Britain and Hampshire: these packs use the same stage's code, so at their next build the lakes' stage and every stage after it run again, even without the new setting. That includes the long stages that read the streets, the land use and the points of interest.

## England and the Hampshire rehearsal

The orchestrator added the same setting to the England and the Hampshire and Isle of Wight packs, which also read lagoons. The rehearsal on Hampshire left out 5 of 888 lakes, all tidal harbours or docks lying in the sea: Basin No. 2, North Camber, Bembridge Harbour, Wootton Creek and West Winner. None was cut. The stage took 1.8 seconds.
