# Spike S2 findings: countries, coastlines and islands

Task P0-T5. Architecture sections 6.12 and 12.3. Status note of 1 November 2026, written overnight. Stage 1 is not finished yet.

## Where it stands

* Stage 1 covers the UK, France and Spain. Its build program is written: `.venv\Scripts\python.exe -m mapdata spike-s2-stage1`
* The first run was stopped by the computer during the night, because memory was running low. It had:
  * extracted every area;
  * cut 99 of about 360 of them to the land.
* Those 99 are cached in the data folder's tobymap\working folder, so the next run carries on from there.
* It has not been run again, because it needs your go-ahead. It can be started when the computer is not busy with anything else.

## Found so far

### The tools

* GeoDesk for Python 2.3.0 is LGPL-3.0, which is compatible with GPL-3.0. It opens your planet and UK GOL files read-only, and reads them quickly. For example, finding the UK's level 4 areas took 1.5 seconds.
* The OSM land polygons were downloaded into tobymap\downloads: 885 MB, dated 31 October 2026.
* Your planet GOL file is dated 22 November 2025, so the data is about a year old.

### What was extracted

* 14 countries at level 2: the three, plus their neighbours, so their land borders can be checked.
* France's six country units: metropolitan France, French Guiana, Guadeloupe, Martinique, Réunion and Mayotte.
* United Kingdom: 4 areas at level 4 and 139 at level 6.
* France: 18 at level 4 and 98 at level 6.
* Spain: 20 at level 4 and 50 at level 6.
* One shape needed a repair: Northern Ireland, whose boundary had nested outlines.

### A trial run on the UK alone

* Cutting the UK to the land took 96 seconds.
* The result is 243,533 km² of land, close to the UK's official area.
* The land is in 19,854 separate pieces, almost all of them islands, with 2.2 million points.

## What the full run will produce

* A report in the data folder's tobymap\output\s2-stage1 folder. It covers:
  * the coastline places, such as 2 km off Brittany, Skye, Gibraltar, Ceuta and Llívia, from tests/acceptance/coastline_places.yaml;
  * land in no country, and land in a country but in none of its divisions;
  * the UK's islands, named and unnamed, at each size and drawing level;
  * whether neighbours still meet exactly after simplifying;
  * pack sizes with and without compact coordinates;
  * time, memory and disk use.
* Two small packs, one with each kind of coordinates, which `mapdata inspect` can query.
* Pictures for sighted reviewers.
