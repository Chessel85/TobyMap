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
* Layer: all the areas of one kind in a build, such as the Countries layer. A layer can hold lines or places instead of areas.
* Line: a feature with length but no area, such as a line of latitude or the date line. Build reports count a line layer in lines.
* Place: a feature at one position, such as a railway station. Build reports count a point layer in places, because "point" means a corner on an outline.
* Shape: everything an area covers, all its parts together.
* Part: one separate bit of a shape, which doesn't touch any other bit of the same shape. The British mainland is one part of the UK's shape, and Skye is another. Land that is in no area is also counted in parts.
* Point: one corner on the outline of a shape. The number of points is a measure of how detailed, and how large, a shape is.
* Border: the line where two areas meet on land.
* Coast: where an area meets the sea, after trimming.
* Shared island: an island whose land is in two countries, with a border across it, such as Märket, shared by Sweden and Finland.
* The 180 degree line: the meridian at 180 degrees east and west (the antimeridian). OSM splits every shape that crosses it, so Fiji's shape has parts either side.
* Artificial edge: an edge of a shape that is only there because the shape was split, along the 180 degree line or at the South Pole. It is never a border or coast, never announced and never outlined (AD-17).
* Ellipsoid: the shape the application uses for the Earth, a ball slightly flattened at the poles, called WGS 84. Every distance, bearing and step is worked out on it (AD-7). A perfect ball, the sphere, is wrong by up to about half a percent.
* Move path: the line a step follows, as a list of positions no more than 10 km apart, so it bends with the Earth. Phase 2 uses it to find what a step crossed and passed.
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
* Gap: land in a country that is in none of the areas chosen so far for a layer. After Belgium's provinces, the Brussels-Capital Region is a gap, because it is in no province.
* Sliver: a thin part of a gap that is there only because two outlines do not quite match, such as an area's coast in OSM and the coast of the land polygons. Slivers are measured and counted, but they are not missing areas.
* Grid square: one square of a grid along lines of latitude and longitude. A large shape is cut along the grid so that each step works on a small part of it. In the counties step, the grid squares are a quarter of a degree each way.
* Face: in one grid square of the base pack lite's build, a part of the grid square bounded by the outlines of the land, the countries, the regions and the oceans, with no outline crossing it. Each face is wholly inside or wholly outside each area, so it is named by testing one point inside it. Together, the faces cover the grid square with no gaps.
* Unclaimed land: land that is in no country and is too big or too wide to be a sliver, such as Bir Tawil between Egypt and Sudan, or a small island outside every country's boundary. It is announced as "Unclaimed" (DP114), and the build lists every one for the PO to review.
* Disputed land: land that more than one party claims and that the base pack lite holds as an area of its own, such as the West Bank and the Ilemi Triangle (DP120). Its record is marked disputed, so a later phase can list all disputed areas (DP119). It is announced by its name, not as "Unclaimed".
* Condominium: land that two countries hold together, such as the Moselle between Germany and Luxembourg (DP117). It is one area in the Countries layer, held by both.
* Bounding box: the smallest rectangle, with edges along lines of latitude and longitude, that contains a shape.
* Trimming: removing the sea from an area by keeping only the land tiles inside it, cutting those that cross its boundary.

## Packs

* Pack: one file of map data that the application reads (AD-5).
* Record: one named, compressed item in a pack, such as the manifest, the list of areas, or one pack tile. The application reads a pack one record at a time, from disk or later over the internet.
* Directory: the list at the end of a pack of every record's name, where it starts and how long it is. A reader reads it first, then only the records it needs.
* Manifest: the record that describes a pack: its name, sources, licence, and how it is laid out.
* Feature record: what a pack holds about one area apart from its shape, such as its names, type, size and the country it is in.
* Feature number: a feature record's number within one pack, which tile entries use to say which area they belong to. It is not the identifier, which stays the same in every pack.
* Format number: the number at the start of a pack that says how it is laid out. Packs from Phase 1 on have format 2. Format 1, the spike S2 packs, is no longer read.
* Check number: a short number stored for each record, worked out from its bytes. If a record is damaged, its bytes no longer give the same check number, so the damage is found when that record is read, and the rest of the pack can still be used.
* Checksum: a long number worked out from every byte of a whole pack, kept in a small file beside it and later in the catalogue. After a download, the application works it out again; if it differs, the download is damaged or incomplete.
* Byte source: where a pack's bytes are read from: a file on the desktop, the browser's private storage in the web version, and later the internet. The pack reader works the same with any of them.
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
* Base detail: how far the base pack lite's shapes are simplified, about 100 metres (DP112). No point of a border or coast moves further than that. Lookups and distances use the shapes at base detail; the drawing levels are simplified further from them.
* Base pack lite: the Phase 1 world pack, with countries, first-level divisions, oceans and seas, cut to the coast. The full base pack replaces it in Phase 3.
* Test pack: a small pack built from samples kept in the repository, so the automatic tests never need the data folder (architecture 11.1).

## Building packs

* Settings file: one of the files in mapdata/config that say what a build does: sources.yaml for the sources, a layers file for each group of layers, and a pack file for each pack. docs/data-manager/configuration.md describes every setting.
* Stage: one step of a build, such as reading the samples or writing the pack. A pack's settings file lists its stages in order.
* Fingerprint: a long number worked out from everything a stage uses: its settings, its sources, the stage before it and its code. If the fingerprint is the same as last time, the stage's kept results are used and the stage is skipped.
* Working folder: the folder in the data folder, tobymap\working, where stages keep their results between builds.
* Created files list: the list, in tobymap\created files.txt, of every file mapdata has made. mapdata overwrites only files on the list, and never deletes any.
* Run switch: continue.txt, in the repository's top folder. Its first line, yes or no, says whether a long build may carry on. On no, the build stops cleanly and keeps its finished work.
* Sample: a small file of areas kept in the repository, in tests/samples, that the test pack is built from.

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
* Time stretching: making speech faster or slower without changing its pitch. TobyMap uses it to make the spatial voice faster than Piper can speak.
* Slice: in time stretching, a short length of the speech, 25 ms, long enough to hold a few repeats of the voice's wave. Time stretching keeps only some slices and fades each into the next.
* Gap: in time stretching, a quiet stretch between words, of 60 ms or more. Gaps are shortened before any slices are dropped.

## Using the application

* Earcon: a short sound that tells you something happened without speech, such as the tick or the blocked sound (SON-6).
* Tick: the earcon for a step that changed nothing.
* Blocked sound: the earcon for a step that could not be taken, such as at a pole. Nothing is spoken with it.
* Held key: an arrow key kept pressed so that it repeats. The steps are all made, but only the place where you let go is spoken (ANN-3).
* Click: the tick each step makes while a key is held, so you can hear the steps being made (DP129). The clicks keep their own even time, and never wait for the map to be drawn (DP140).
* Drawing: making one picture of the map. It has three parts: choosing the shapes in view and cutting them to it, projecting them onto the globe in screen pixels, and painting them. The first two are done by the core, the painting by the desktop or the web page.
* Key describer: a mode, switched on and off with Shift+F1, in which each key you press is described and nothing is carried out.
* Announcement history: the list of what the application has said, newest first, kept to at least 50 entries (ANN-4).
* Hearing range: the distance at which a sound reaches the edge of the view. It is the zoom distance, and the distance curve is measured against it (SON-9).
* Distance curve: how loud and how muffled a sound is for its distance within the hearing range.
* Orientation: which way you face, and so what "ahead" means for directions and sound. There are three: north-fixed, cardinal facing and free facing (NAV-12). F cycles them.
* Facing orientations: cardinal facing and free facing together, the two in which you can turn.
* Jump: going straight to a place without stepping, such as to typed coordinates, a click on the map, or an announcement history entry (NAV-8).
* Position history: the places you were at before each step, jump, Go to and click (a held arrow key is one step, from where the hold started), which Alt+Comma and Alt+Full stop go back and forward through (NAV-10, DP142). Going back or forward adds no place.
* Sound scene: the core's list of the sounds to play, each with its direction relative to ahead, its loudness and its pitch. The desktop and the web version each play it with their own sound player (AD-10).
* Crossed and passed: the Information panel group that lists what the last move went over or near without stopping on it. It is never spoken by itself; a soft earcon says something was added (ANN-2).
* Crossed: a line, such as a river, that a move's path went across.
* Passed over: an area, such as a small lake, that a move's path entered and left, with neither the start nor the end of the move in it.
* Passed: a point, such as a railway station, that a move's path came within the passed nearby distance of.
* Passed nearby distance: how near a move's path must come to a point for it to be listed as passed. A share of the step, 10% at first, or a fixed distance (DP58).
* Beacon: a soft repeating sound from the direction of the North Pole, or later a pin, so you can feel which way you face (SON-10).
* Verbosity preset: a named choice of how much is said by itself after a move: terse, normal or detailed. It sets four switches; changing one makes the preset Custom (ACC-5, DP144).
* Theme: the set of colours the map is drawn in: standard, high contrast dark, high contrast light or colour-blind safe (VIS-2).
* Contrast ratio: how much lighter one colour is than another, from 1 to 1 (the same) to 21 to 1 (black on white), measured as the web accessibility guidelines do. The high contrast themes keep every outline and name at 7 to 1 or more.
* Map display setting: the choice of fill, borders and their colours, on top of the theme (DP108).
* Isolate: showing only the area you are in, and its outline, on the map (VIS-2).
* Names on the map: the areas' names drawn on the map for sighted users, placed by the core.
* Text cursor: the small rectangle a Windows program says its typing point is at, also called the system caret. Magnifiers can follow it. The desktop map holds an invisible one at its centre (ACC-8).
* Focus point: in the web version, the small invisible element at the map centre that has the keyboard focus when the map does, so a magnifier that follows the focus looks there (ACC-8).

## Planning

* Work item: one part of a task in a phase plan, such as P2-T1a, small enough to be done in one session, and labelled with the model that should do it, Opus or Sonnet.
* Test trace: the core's record of every command, announcement and earcon with the time each took. "Copy diagnostics" puts the last five minutes of it on the clipboard.
