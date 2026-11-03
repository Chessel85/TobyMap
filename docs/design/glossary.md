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

## OpenStreetMap data

* Node: one point in OSM, with its latitude and longitude.
* Way: a line in OSM, made of nodes in order. A stretch of border between two counties is one way.
* Relation: a group of ways in OSM, together with what they make. A county's boundary is one relation, made of the ways around it.
* Planet file: the whole of OpenStreetMap in one download, made each week and named by its date, such as the planet file of 26 October 2026. It is about 96 GB, and is kept in the data folder.
* GeoDesk library: a copy of one planet file, converted by the GeoDesk program so that a build can search it quickly. A build can then find, for example, every country's boundary without reading the whole planet file. It is one file ending in .gol, of about 140 GB, and is made once for each planet file. Making it takes some hours and most of the laptop's memory.

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
* Directory: the list at the end of a pack of every record's name, where it starts and how long it is. A reader reads it first, then only the records it needs.
* Manifest: the record that describes a pack: its name, sources, licence, and how it is laid out.
* Feature record: what a pack holds about one area apart from its shape, such as its names, type, size and the country it is in.
* Compact coordinates: the way a pack stores each point of a shape, as a whole number of ten-millionths of a degree (about 1 cm), and as the difference from the point before. It makes packs about five times smaller.
* Read: fetching one record from a pack. In the web version, each read will be one download, so the number of reads matters.
* Pack tile: one cell of the grid that a pack's shapes are stored in. Each pack tile is stored as one record.
* Tile level: the size of a pack tile. At tile level 3, a pack tile is 45 degrees wide and 22.5 degrees tall. Each level up halves both, so one pack tile is split into four. A pack tile is split only where a shape in it has more than 4,000 points, so pack tiles are small where coasts are detailed and big elsewhere.
* Tile entry: what one pack tile holds for one area. It is either the part of the area's shape inside the pack tile, or a covered note.
* Covered note: a tile entry that says an area covers the whole of a pack tile, so no shape needs storing there.
* Lookup: finding every area at a point. It reads at most one pack tile at each tile level.
* Decoding: turning a pack tile's stored bytes back into shapes that can be tested against a point. Compact coordinates must be decoded before use.
* Pack tile cache: the decoded shapes of pack tiles read recently, kept in memory, so a lookup nearby needs no reading or decoding.
* Drawing level: one degree of simplification of a pack's shapes, used to draw the map at a range of zooms. Small parts are left out at each drawing level, so a frame stays quick to draw (architecture 6.9).
* Drawing tile: a pack tile holding the simplified shapes of one drawing level. Lookups and distances never use them, only the exact shapes.
* Base pack lite: the Phase 1 world pack, with countries, first-level divisions, oceans and seas, cut to the coast. The full base pack replaces it in Phase 3.
* Test pack: a small pack built from samples kept in the repository, so the automatic tests never need the data folder (architecture 11.1).

## Testing

* Acceptance script: a small file of key presses and the announcements expected after each, tied to requirement IDs. It runs as an automatic test, and is also turned into the PO's checklist, so both check the same thing (architecture 11.3).

## Hosting and the browser

* Range request: asking a server for only some bytes of a file, given by where they start and end, instead of the whole file. In the web version, each read of a record over the internet is one range request.
* Web permission: a setting a server sends with each file (the Access-Control-Allow-Origin header) that lets web pages from other addresses read the file. Without it, the browser blocks the page from reading the file, even though the file downloads normally in a browser tab or on the desktop.
* Redirect: when one address sends the browser on to another server for the file. GitHub Releases and Hugging Face both do this, so every range request goes to two servers.
* Private storage: the browser's private file system for one web site (OPFS). Other sites and the user's own files can't see it. The web version keeps packs here so they work offline.
* Storage limit: how much the browser lets one web site keep in its private storage.
* Kept storage: private storage that the browser has agreed not to clear when the disk gets full. A site has to ask for it, and Firefox asks the user.
* Cache storage: a second store the browser keeps for one web site, for whole downloaded files. The web version keeps the voice here, so a later visit does not download it again.
* Thread: one line of work inside a program. A program with several threads can use several of the computer's cores at once.
* Cross-origin isolation: a setting a web site sends with its page (two headers) that lets the page's workers use several threads. Without it, a worker has one thread.

## Voice

* Phonemes: the separate sounds of speech, such as the five in Berlin: "b", "er", "l", "i" and "n". Piper is given phonemes, not letters. eSpeak NG works them out from the text.
* Label: a short piece of speech from the spatial voice, such as "Berlin", placed in space.
