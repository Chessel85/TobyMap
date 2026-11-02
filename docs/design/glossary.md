# Glossary for reports and documents

This glossary is for the words Claude Code uses in build reports, spike findings, design documents and answers to the product owner. Each word has one meaning. When a report needs an idea that isn't here, add a word here first, then use it.

The user glossary in the application's Help is a separate thing (UX section 15). It explains words that users meet, such as bearing and step.

## Words not to use on their own

* Piece: it has been used for land tiles, pack records, tile entries and parts, so it is never used in a report. Say which of those is meant.
* Box: say reading box or bounding box.
* Tile: say land tile or pack tile.

Older documents written before this glossary, such as architecture section 6 and the S2 findings, still say "piece". They are brought into line when they are next edited.

## Places and shapes

* Area: one administrative area from OSM, such as a country, region or county. Before trimming, its boundary includes the sea out to 12 nautical miles.
* Level: OSM's administrative level. In the builds so far, level 2 is countries, level 4 is regions (such as Scotland) and level 6 is counties and similar (such as Highland).
* Layer: all the areas of one kind in a build, such as the Countries layer.
* Shape: everything an area covers, all its parts together.
* Part: one separate bit of a shape, which doesn't touch any other bit of the same shape. The British mainland is one part of the UK's shape, and Skye is another. Land that is in no area is also counted in parts.
* Point: one corner on the outline of a shape. The number of points is a measure of how detailed, and how large, a shape is.
* Border: the line where two areas meet on land.
* Coast: where an area meets the sea, after trimming.
* Shared island: an island whose land is in two countries, with a border across it, such as Märket, shared by Sweden and Finland.
* The 180 degree line: the meridian at 180 degrees east and west (the antimeridian). OSM splits every shape that crosses it, so Fiji's shape has parts either side.
* Artificial edge: an edge of a shape that is only there because the shape was split, along the 180 degree line or at the South Pole. It is never a border or coast, never announced and never outlined (AD-17).
* Counties record: the list, in mapdata/config/county_levels.yaml, of which levels make up each country's Counties layer (DP101). The build writes it once per country; a corrected entry is never overwritten.

## The land polygons

* Land polygons: the worldwide OSM product that holds all the land in the world, with the sea removed (AD-15).
* Land tile: one shape in the land polygons file. It is a whole small island, or a slice of a bigger island or a continent, cut along the lines of latitude and longitude at every whole degree. No land tile is bigger than one degree each way, and neighbouring land tiles overlap very slightly.
* Reading box: a rectangle, given by its west, south, east and north edges in degrees, that says which land tiles a build reads. They are listed in the build's configuration, such as mapdata/config/s2_stage1.yaml.
* Land index: the land polygons converted once, after each download, into a form a build can read in part: the bounding box of every land tile in one list, and the land tiles themselves one after another. A build finds the land tiles in its reading boxes from the list and reads only those. It is kept in the data folder's tobymap\working folder.
* Bounding box: the smallest rectangle, with edges along lines of latitude and longitude, that contains a shape.
* Trimming: removing the sea from an area by keeping only the land tiles inside it, cutting those that cross its boundary.

## Packs

* Pack: one file of map data that the application reads (AD-5).
* Record: one named, compressed item in a pack, such as the manifest, the list of areas, or one pack tile. The application reads a pack one record at a time, from disk or later over the internet.
* Read: fetching one record from a pack. In the web version, each read will be one download, so the number of reads matters.
* Pack tile: one cell of the grid that a pack's shapes are stored in. Each pack tile is stored as one record.
* Tile level: the size of a pack tile. At tile level 3, a pack tile is 45 degrees wide and 22.5 degrees tall. Each level up halves both, so one pack tile is split into four. A pack tile is split only where a shape in it has more than 4,000 points, so pack tiles are small where coasts are detailed and big elsewhere.
* Tile entry: what one pack tile holds for one area. It is either the part of the area's shape inside the tile, or a note that the area covers the whole tile.
* Lookup: finding every area at a point. It reads at most one pack tile at each tile level.

## Hosting and the browser

* Range request: asking a server for only some bytes of a file, given by where they start and end, instead of the whole file. In the web version, each read of a record over the internet is one range request.
* Web permission: a setting a server sends with each file (the Access-Control-Allow-Origin header) that lets web pages from other addresses read the file. Without it, the browser blocks the page from reading the file, even though the file downloads normally in a browser tab or on the desktop.
* Redirect: when one address sends the browser on to another server for the file. GitHub Releases and Hugging Face both do this, so every range request goes to two servers.
* Private storage: the browser's private file system for one web site (OPFS). Other sites and the user's own files can't see it. The web version keeps packs here so they work offline.
* Storage limit: how much the browser lets one web site keep in its private storage.
* Kept storage: private storage that the browser has agreed not to clear when the disk gets full. A site has to ask for it, and Firefox asks the user.
