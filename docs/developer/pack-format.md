# Pack format specification

Version 4, 13 November 2026 (P3-T2b). Version 3 was 5 November 2026 (P2-T10a), and version 2 3 November 2026 (P1-T2). The code is in `mapcore/packs`. Requirements: PCK-5, DAT-9, NFR-4, DMT-1, and the format for PCK-1. Decisions: AD-5, AD-17, architecture sections 6.1 to 6.4 and 6.9.

Words follow the glossary: pack, record, directory, manifest, feature record, pack tile, drawing tile, tile entry, covered note, compact coordinates, check number and checksum.

## Format numbers

Every pack's header holds a format number.

* Format 1 was the spike S2 pack. It was dropped on 3 November at the PO's request, and nothing reads it: a file with format 1 is not a TobyMap pack. The spike S2 stages now write the current format.
* Format 2 was Phase 1's format. The Phase 1 plan calls it "pack format version 1"; it kept the number 2 so that an old spike pack left in a folder is never mistaken for it.
* Format 3 is format 2 with two more kinds of tile entry, for lines and points (P2-T10a).
* Format 4 is the format described here. It is format 3 with facts in the feature records: each feature's facts from Wikidata, with their sources and dates, and its Wikipedia article (P3-T2b); disputed areas' claimants and the source's view (P3-T2c); and each feature's relationships, in records of their own (P3-T3e). The writer always writes format 4. The reader reads formats 2 and 3 as well, since they are format 4 packs without what it added, so the Phase 1 and P3-T1 world packs still open.
* A number above 4 is refused with packs.newer_format.

## The file

A pack is one file, in three parts:

1. the header, 40 bytes;
2. the records, one after another, each compressed on its own with zlib at level 9;
3. the directory, also compressed with zlib.

All numbers are little-endian.

### The header

In order:

* 8 bytes: the letters TOBYPACK.
* uint16: the format number, 3.
* uint16: flags, 0. No flags are defined yet.
* uint32: reserved, 0.
* uint64: where the directory starts, counted from the start of the file.
* uint64: the directory's stored length in bytes.
* uint32: the directory's check number.
* uint32: the header's check number, over the 36 bytes before it.

A reader reads the header first, then the directory, then only the records it needs. Opening a pack takes four reads: the header, the directory, the manifest and the layer definitions.

### Check numbers

A check number is the CRC-32 (zlib.crc32) of a record's stored bytes, that is, after compression. The reader compares it before decompressing. A mismatch, a record that runs past the end of the file, or one that will not decompress, raises `DamagedRecord`, whose message is packs.damaged_record and names the record. The rest of the pack can still be read (NFR-4). `Pack.check()` reads every record and lists the damaged ones.

If the header, the directory, the manifest or the layer definitions are damaged, the pack cannot be used at all, and opening it raises `DamagedPack`, with the message packs.damaged_pack.

### The directory

zlib-compressed JSON:

* `{"records": {name: [start, stored length, check number], ...}}`

The names are sorted. Every JSON text in a pack is written with sorted keys, no spaces, UTF-8 not escaped, and no NaN or infinity, so the same content always gives the same bytes.

## The records

### manifest

JSON. The builder gives:

* name: the pack's name, such as base-lite.
* version: the pack's own version, a string.
* coverage: where the pack covers in detail. For a world pack, `{"kind": "world"}`. The form for regional packs is settled in Phase 4 (AD-14).
* app_versions: `{"from": "0.1.0"}`, and optionally `"before": "0.3.0"`. The application opens the pack if its own version is at least "from" and less than "before". Versions are dotted numbers, compared number by number, with missing numbers counted as 0.
* sources: a list, at least one, each with name, licence and date (YYYY-MM-DD), and anything else useful, such as a web address.
* drawing_levels: a list, each with id (a whole number), tile_level (the tile level of its drawing tiles), and anything else the drawing code needs, such as the zooms it serves.

The writer adds, and refuses a builder that sets them itself:

* format: 4.
* built: the latest of the sources' dates. Never the clock, so a rebuild gives the same bytes (DMT-1).
* layers: the layers' identifiers, in order.
* tile_levels: the tile levels at which pack tiles of exact shapes are stored, ascending.
* coordinates: `{"encoding": "compact", "scale": 10000000}`.
* features: `{"count": N, "groups": G, "group_starts": [...]}`, described under feature records.
* limits: `{"entry_points": 4000, "tile_points": 20000}`.

### attribution

UTF-8 text crediting every source as its licence requires, including "© OpenStreetMap contributors" (DAT-9). It cannot be empty.

### licence

UTF-8 text: the ODbL notice (ODbL section 4.3), `mapcore.packs.pack.ODBL_NOTICE` unless the builder gives another.

### layers

JSON list of layer definitions (SCP-7), in display order. Every feature's layer must be one of them. Each has:

* id and name: always.
* rank: what the build ordered areas by (LOC-2).
* group, geometry, switched_on, min_zoom_m, max_zoom_m, min_size, crossing_earcon and sound: from P2-T3, when the layer file gives them. Their meaning is in docs/data-manager/configuration.md, under layers.

A reader uses defaults for any field left out (mapcore/layers/catalogue.py): no group, area, on, every zoom, 0.02, and no sounds. So a pack built before P2-T3, whose definitions have only id and name, still works, and the format number did not change. The user's own changes are not in the pack: they are kept with the settings, by layer id, so they survive a pack being built again.

### features/G

The feature records, in groups. There are G groups, where G is the number of feature records divided by 256, rounded up, and at least 1.

* A feature record's group is the CRC-32 of its identifier, as UTF-8, modulo G.
* The records are sorted by group, then by identifier, and numbered from 0 in that order. The number is the feature number, which tile entries use.
* Record features/G holds group G's feature records, in order, as a JSON list. A group with no records has no record.
* manifest features.group_starts gives the feature number of each group's first record. An empty group's start is the next group's.

So both lookups take at most one read:

* by feature number: the last group whose start is at most the number;
* by identifier: the group from the CRC-32, then a search of that group.

Each feature record holds, in Phase 1 (architecture 6.4):

* id: the canonical identifier, such as osm:r62149 (AD-13).
* source: where it comes from, such as osm.
* layer: a layer id.
* type: its type in plain words, such as "county".
* names: by language, such as `{"en": "France", "fr": "France"}`.
* rank: a whole number used to order "where am I" (LOC-2).
* area_km2: its area on the ellipsoid.
* bbox: west, south, east, north. West is greater than east when the box crosses the 180 degree line, as for Fiji (AD-17).
* width_km: its width, for the size rule (NAV-13).
* colour: its colour number (AD-19).
* point: longitude and latitude of a point on its land.
* parents: the identifiers of the areas that contain it.

The writer refuses a feature record that lacks any of these, or an identifier given twice. More fields may be added; readers ignore those they don't know.

Optional fields:

* disputed: true for an area that OSM holds twice in one layer, one copy for each side of a dispute, such as Sevastopol (DP104, architecture 6.12). Only one copy is in the pack.
* also_held_as: with disputed, the other copy's details: id, name, name_en and country_code, the ISO 3166-1 code its own ISO 3166-2 code names, such as UA. The details of the area describe the dispute from these (ANN-6).
* tier: for an area of the countries, regions and counties layers, where it sits in its country's government, one of the manifest's tiers, such as constituent_country for England (P3-T17, DP165). Given by the writing stage from mapdata/config/tiers.yaml. Details says it with the area above it, "constituent country of the United Kingdom". A pack written before P3-T17 has none, and Details then says the layer's word.

* facts: from format 4, the feature's facts from Wikidata (P3-T2b, DAT-7, INF-1), by name: population, area_km2, capital, elevation_m, length_km and official_name. Each is an object with value; source, "Wikidata"; fetched, the date it was fetched, YYYY-MM-DD; and date, the fact's own date where Wikidata gives one, cut to its precision, so "2020", "2020-03" or "2020-03-01". A capital's value is a list of names, with wikidata, the list of their Wikidata items. Details says each fact with its source and date. A feature with no facts has no field.
* wikipedia: from format 4, the title of the feature's English Wikipedia article, such as "Rhine". Only the title is stored; the article is opened in the browser, so none of Wikipedia's text is in the pack.
* wikidata: the feature's Wikidata item, such as Q584, from OpenStreetMap's wikidata tag, given by hand, or matched by name and place (P3-T2a).

* claimants: from format 4, for disputed land two countries both hold, such as Crimea, the two countries' identifiers, in the order of their names, with equal credit (P3-T2c, DP119).
* dispute: from format 4, for an area inside one of Natural Earth's disputed areas: name, Natural Earth's name for that area; source, "Natural Earth"; and view, its note in full words, such as "Administered by Russia. Claimed by Ukraine." (ANN-6, DAT-8).
* tier_name: from format 4, what the area's tier is called in its country, such as "state", from the tiers record's names (DP181). Details says it in place of the tier's word.

The manifest may also have:

* tiers: the tiers, highest first, such as `["country", "constituent_country", "region", "county"]` (P3-T17). "Where am I" orders the areas at a point by rank, then by this list, the lowest tier first, then the smallest. Optional, so the format number did not change.

### relations/G

From format 4 (P3-T3e, architecture 6.5): the relationships of group G's feature records, the same groups as features/G, as a JSON object by identifier, holding only the features that have any. A group with none has no record, so finding a feature's relationships takes at most one read. Each feature's object may have:

* in: the areas that hold it fully, from every layer, smallest first: its parents and their parents.
* same: areas that are the same land, each inside the other (DP71).
* overlaps: for an area, the areas that overlap it with neither holding the other, each as [id, the share of this area covered, the share of the other covered], the largest share first (INF-5).
* partly: for a line or a place, the areas it is partly inside, each as [id, share].
* next: areas of its layer that share a border with it, each as [id, km], the longest border first (INF-2).
* near: areas of its layer within the build's near_km that share no border, each as [id, km].
* crosses: for a line, the areas it passes through, in order from its start (INF-6).
* crossed_by and along: for an area, the lines crossing it, and those along its border.
* water_in: for a water area, the water area of a lower rank that holds most of it (DAT-4).
* counts: for an area, how many features of each layer are inside it, fully or partly, by layer id.

`Pack.relationships(identifier)` returns the object, or an empty one for a feature with none or a pack written before format 4.

### tile/L/X/Y

A pack tile of exact shapes, at tile level L, column X and row Y.

The grid: at tile level L there are 2 to the power L columns, each 360 divided by 2 to the power L degrees wide, starting at 180 degrees west, and as many rows, each 180 divided by 2 to the power L degrees tall, starting at the South Pole. Tile levels run from 0 to 18.

The record holds tile entries, in order of feature number, then of their bytes:

* uint32: the number of tile entries;
* for each: uint32 feature number, uint8 kind, uint32 length, then that many bytes.

Kinds:

* 0: a covered note. The area covers the whole pack tile. No bytes.
* 2: compact coordinates of the part of the area's shape inside the pack tile.
* 3: compact line coordinates of the part of a line feature inside the pack tile, such as a line of the graticule. From format 3.
* 4: compact point coordinates of a point feature's points that are in the pack tile, such as a railway station. Each point is in exactly one pack tile: the one whose grid cell it falls in, by the rule of tile_of. From format 3.
* 1 was WKB in the spike packs and is refused.

Lines and points have no covered notes. "Where am I" looks only at kinds 0 and 2, because a line or a point has no inside. Nearby uses every kind. A layer's definition says which geometry its features have (geometry: area, line or point).

Limits (AD-5, from spike S2), checked by the writer for pack tiles at tile levels below 18:

* a tile entry holds at most 4,000 points;
* a pack tile's tile entries together hold at most 20,000 points.

A point here is a stored point, not counting the closing point of each ring. A line's points and a point feature's points count the same. A pack tile with nothing in it is not stored.

### draw/D/X/Y

A drawing tile for drawing level D: the simplified shapes of that level (architecture 6.9), in the grid of the tile level that the manifest gives for D. The same tile entries as a pack tile, with no point limits. Lookups and distances never use drawing tiles.

## Compact coordinates

One shape, all varints (7 bits to a byte, low bits first, the top bit set on every byte but the last):

1. the number of polygons;
2. for each polygon, its number of rings (the outer ring first, then the holes), then the number of points in each ring, not counting the closing point;
3. every point in order, longitude then latitude, each as a whole number of ten-millionths of a degree, written as the difference from the point before (the first from 0, 0), zig-zag encoded so small negative numbers stay small.

The decoder closes each ring again, and returns the points with ring and polygon offsets, the arrays Shapely's from_ragged_array takes.

Lines (kind 3) use the same numbers with one level less:

1. the number of lines;
2. the number of points in each line, at least 2 for a line;
3. every point, as above. Nothing is closed.

Points (kind 4) are written as lines of one point each, so the header is the number of points followed by that many 1s. Both decode, many shapes at once, to Shapely MultiLineStrings and MultiPoints (coords.to_line_shapes and coords.to_point_shapes). It uses NumPy only, all of a shape at once, with np.intp for offsets because NumPy in Pyodide is 32-bit. It refuses bytes that end in the middle of a number or don't match their own header.

## The checksum of the whole file

The writer writes `<pack name>.sha256` beside the pack: the SHA-256 of the whole file, as lowercase hexadecimal, a space, an asterisk and the file name, the form sha256sum reads. The catalogue will carry the same value (PCK-5). After a download, `require_checksum` raises `ChecksumWrong`, with the message packs.checksum_wrong, if the two don't match.

## Version checks

On opening, in this order:

1. Not TOBYPACK at the start, shorter than a header, or a format below 2: packs.not_a_pack.
2. A format above 4: packs.newer_format. Formats 2, 3 and 4 are read.
3. A damaged header, directory, manifest or layer definitions: packs.damaged_pack.
4. The application's version below app_versions.from: packs.app_too_old. At or above app_versions.before: packs.app_too_new.

The application's version comes from version.txt. A version that is not dotted numbers, such as "unknown" in a copy that cannot find version.txt, is not checked. mapdata opens packs with the check turned off.

## Byte sources

The reader reads only through a byte source: an object with `size` and `read(start, length)`, and optionally `name` and `close()`. There are three:

* `FileSource`, a file on disk, for the desktop and mapdata;
* `MemorySource`, bytes in memory, for the tests and the self-check;
* the browser's private storage, in the web worker (P1-T11).

Range requests over the internet come later (PCK-3). Because each read may become one download, the reader counts its reads in `Pack.reads`.

## Writing

`PackWriter` takes a path or a seekable binary file. The calls are:

1. `add_features(records)`, once, which returns each identifier's feature number;
2. `add_tile(level, x, y, entries)` and `add_drawing_tile(level, x, y, entries)`, any number, where entries are (feature number, kind, bytes);
3. `finish(manifest, attribution, layers)`, which writes the manifest, attribution, licence, layers, directory and header, and for a path, the checksum file.

The same calls in the same order always give the same bytes (DMT-1). Cutting shapes into pack tiles is the pipeline's job (P1-T3, P1-T4); the writer checks the limits.

## The self-check

`mapcore.packs.selfcheck.run()` writes a small pack in memory, reads it back, damages a record, and tries a pack for a later application version. It returns a list of problems, empty when all is well. The browser tests run it in the web worker in Chromium and Firefox (tests/web/test_pack_format_page.py), so the reader is proven in Pyodide's 32-bit NumPy as well.

## Version history

* Format 1, 2 November 2026: spike S2. A 16-byte header, the directory's place in a 16-byte footer, one record for all feature records, WKB or compact coordinates, and no check numbers. Dropped on 3 November.
* Format 2, 3 November 2026: P1-T2. The directory's place and check number in the header, a check number for every record, the checksum file, version checks, feature records in groups with feature numbers, attribution, licence and layer definitions, drawing tiles, compact coordinates only, and the writer's limits.
* Format 3, 5 November 2026: P2-T10a. Tile entry kinds 3 (lines) and 4 (points), the layer definitions' geometry and the other fields from P2-T3, and the reader still reads format 2.
* Format 4, 13 November 2026: P3-T2b, P3-T2c, P3-T3e. Facts and the Wikipedia article, claimants, the source's view of a dispute and tier names in feature records; the relations records; and the reader still reads formats 2 and 3.
