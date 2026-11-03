# Explanations

This document explains how parts of TobyMap work, in plain words, for the product owner and anyone else who wants to understand the design without reading the code. Each section covers one topic. The words used follow the glossary (glossary.md), which gives each one exact meaning. The technical decisions themselves are in architecture.md.

## How the build trims countries to the coastline

### The problem

A country's boundary in OSM includes its territorial waters, usually 12 nautical miles out to sea. The UK's boundary covers 403,068 square kilometres, but only 243,533 square kilometres of that is land. Without trimming, standing 5 km off Brighton would say "United Kingdom" instead of the sea.

### Words used in this section

These are defined in full in the glossary.

* Area: one country, region or county, as its OSM boundary draws it, sea included.
* Land tile: one shape in the land polygons file. It is either a whole small island, or a slice of a bigger island or a continent, cut along the lines of latitude and longitude at every whole degree. So Great Britain is not one shape in the file; it is many land tiles, each no bigger than one degree north to south by one degree east to west. Each land tile overlaps its neighbours very slightly, so there are no cracks between them.
* Reading box: a rectangle on the map, given as its west, south, east and north edges in degrees. It is used only to decide which land tiles to read from the file. For example, the Europe reading box runs from 19 degrees west to 16 degrees east, and from 27 degrees north (below the Canary Islands) to 61.5 degrees north (above Shetland). The reading boxes for spike S2 are listed in mapdata/config/s2_stage1.yaml.
* Part: one separate bit of an area's finished shape. The mainland of Great Britain is one part of the UK, Skye is another, and every islet and rock is another.

### The land polygons

* OSM has a separate, worldwide product called the land polygons, made from the coastline lines that mappers draw (tagged natural=coastline).
* The OpenStreetMap community's coastline tools join all those lines into closed shapes every day. The result is all the land in the world, including every island, with the sea removed.
* It comes ready to download, already cut into land tiles: about 870,000 for the world. Spike S2 fetched it with `mapdata fetch land-polygons`, dated 31 October 2026.
* It was chosen instead of joining coastlines onto boundaries, which is the approach that failed in AtlasDL (decision AD-15).

### The steps

1. Read only the land tiles that are needed. Reading the whole world would be slow, so the build reads only the land tiles inside its reading boxes: one for Europe and the Canary Islands, and one for each French overseas region (French Guiana, Guadeloupe, Martinique, Réunion and Mayotte). The Europe reading box holds 86,656 land tiles. They are saved in the build's working folder, so later runs skip this step.
2. For each area, find the land tiles that overlap it. A spatial index, which works like a catalogue sorted by position, finds them quickly without checking every land tile. England, for example, overlaps a few thousand land tiles.
3. Keep or cut each of those land tiles:
   * a land tile wholly inside the area's boundary is kept as it is. That covers most inland tiles, and small islands that lie well inside the territorial waters;
   * a land tile that crosses the area's boundary is cut, keeping only the part inside. That happens at land borders, such as between England and Wales, where one land tile can lie partly in each;
   * land tiles on the coast need no special handling: the sea was never in them, so the coastline comes through as it is.
4. Join the kept land tiles into one shape for the area. Joining removes the one-degree cuts between neighbouring land tiles, so the mainland becomes one part again. Islands stay separate, because there is sea between them. That's why the UK comes out as 19,854 parts: the mainland, the big islands, and thousands of islets and rocks.
5. Remove the seam points. The land tiles overlap by a thin band along each one-degree line. Where a border between two areas crosses that band, cutting in step 3 can add an extra point to the border on one side but not the other. The build removes points that lie within 0.1 mm of the border line, so two neighbours keep exactly the same border.
6. Clean each layer. A layer means all the areas at one level, such as all the countries. Cleaning closes the tiny gaps that are left where a border meets the coast. It also settles places where OSM's own borders overlap, such as between Burgos and Soria in Spain, by giving each overlap to the neighbour that shares the longer border with it.

The same steps are applied at every level: countries, regions and counties. Because they all use the same land tiles, they line up with each other and with the coast.

### What comes out

These results are from spike S2, stage 1.

* Gibraltar: 93 square kilometres with its waters, 7 square kilometres of land.
* Andorra: unchanged at 467 square kilometres. It has no coast, so every land tile is either wholly inside it or cut only at its land borders.
* Islands: they come out without any special handling. Skye, the Isle of Wight and the Canary Islands each end up as part of the right country and county.
* Checks: sea points, such as off the Pointe du Raz and in the Solent, are in no area. The build also looks for land that ended up in no country, and found none.

### Limits worth knowing

* Lakes and rivers stay land. The land polygons remove only the sea, so Lough Neagh is still inside Northern Ireland. That's right for saying where you are, but water will need its own layer.
* Estuaries depend on mappers. Where a river meets the sea, mappers decide where the coastline crosses the river. Upstream of that point the river counts as land, so for example the Thames counts as land through London.
* The dates don't match. In spike S2, the boundaries came from the planet file of November 2025, and the land polygons from October 2026. Where either changed in that year, the two might not quite meet. The checks found no problem, but the real pipeline should use a planet file and land polygons from close dates. This is listed for Phase 1 in the S2 findings (docs/spikes/S2-countries-coastlines.md).

## How the build shares its work between the processor's cores

### The problem

Your laptop's processor has 4 cores, and each core can run two threads, so 8 things can happen at once. In spike S2, most of the build ran on one thread. While stage 3 was running, the laptop showed about 30% of the processor in use and 40% of the memory, and some steps took the better part of an hour. At that speed, building the whole world could take days.

The graphics card can't help. It is very fast at the arithmetic used in neural networks, which is why the OMR project uses it, but the map build does polygon geometry: cutting, joining and comparing shapes. The library that does this, GEOS, only runs on the processor.

### Workers

The build now works like a small office. The main process is the manager. It splits a slow step into many small jobs and hands them to worker processes, which run at the same time on different cores. Each worker sends its result back, and only the manager writes the files and the report, so nothing gets mixed up. This is the same method OMR uses.

These steps are shared out among workers:

* Cutting each area to the land. Each area is one job. The biggest go first, so a large country isn't left until the end.
* Checking that neighbours meet exactly. Each layer is one job.
* Writing the pack. The shapes are cut into pack tiles in batches, then the pack tiles are encoded in batches. Both kinds of pack (WKB and compact coordinates) are now written from one cutting, where before each was cut separately.
* Drawing the pictures. Each picture is one job, and the globe views are another.

### How many workers

* 3 by default, while you're using the laptop. The laptop stays usable, though a bit slower. Running all 8 threads flat out also makes the chip hot, and it then slows itself down.
* 6 with `--away`, when nobody is using the laptop.

### Memory comes first

Each worker holds its own copy of the shapes it's working on, so more workers means more memory. On 2 November, two builds running at once ran the laptop out of memory, and Claude Code stopped them both. So:

* a new job only starts while at least 6 GB of memory is free. When memory is short, fewer jobs run at once, and the build carries on more slowly instead of stopping;
* if free memory falls below 3 GB, the build stops by itself, writes its report so far and a note of where it stopped, and keeps everything it has finished, so the next run carries on from there;
* this check pauses while the planet file is being read, because reading it fills memory with a copy of the file that Windows can take back at any time.

### Before a heavy build

Claude Code tells you before a heavy build starts, so you know the laptop will be slower: which build, how many cores, and roughly how long. The first lines of the build's report say the same, including how long the last run of that build took.

### What made the biggest difference

Sharing the work between cores helps, but on 2 November the biggest gains came from doing less work, not from more cores:

* finding land in no county: from over half an hour to seconds, by working first with the boundaries as read, which have few points at sea, and only then cutting the small leftover to the land;
* matching Norway's 150,000 island names to its land: from over 25 minutes to seconds, by preparing each part of the land once;
* checking that neighbours meet: from over half an hour per layer to under two minutes, by checking only within 5 km of the land borders;
* looking up a place in the pack: from 0.75 seconds to 0.02 seconds, by not letting one pack tile hold too many points.

## How map data gets from the planet file into a pack

### The short version

1. OpenStreetMap publishes the whole map every week as one planet file.
2. The GeoDesk program converts the planet file once into a GeoDesk library, which can be searched quickly.
3. A build asks the GeoDesk library for the areas it needs, such as every country, and adds other sources, such as the land polygons and the VLIZ seas.
4. The build trims, cleans and checks the areas, works out facts about each one, and writes them into a pack.
5. The application reads the pack. It never reads the planet file or the GeoDesk library.

### Words used in this section

These are defined in full in the glossary.

* Node: one point in OSM, with its latitude and longitude.
* Way: a line in OSM, made of nodes in order.
* Relation: a group of ways, together with what they make, such as a county's boundary.
* Planet file: the whole of OSM in one download.
* GeoDesk library: a planet file converted so that it can be searched quickly.
* Layer: all the areas of one kind in a pack, such as the Countries layer.

### Step 1: the planet file

* The planet file is the whole of OpenStreetMap in one compressed file. The one dated 26 October 2026 is 95.6 GB, and it took 53 minutes to download on 3 November.
* OSM doesn't store finished shapes. It stores nodes, ways and relations, each with labels called tags that say what it is. For example:
  * Hampshire is one relation, tagged as an administrative boundary at level 6, with the name Hampshire;
  * its members are the ways around its edge. The way along the border with Dorset is one of them, and the same way is also a member of Dorset's relation. That's why neighbouring areas in OSM meet exactly: they share the same line;
  * each way is a list of nodes, and only the nodes have positions.
* So to get Hampshire's shape, a program must find the relation, find each of its ways, find each node of each way, and join the ways end to end into a closed outline.
* The planet file is arranged for copying, not for searching. Finding Hampshire in it means reading the whole file from start to end.

### Step 2: the GeoDesk library

* GeoDesk is a free program for searching OSM data quickly. Its command `gol build` reads the planet file once and writes a GeoDesk library, a file ending in .gol.
* It files every node, way and relation by where it is on the map, the way a library files books by subject, so a search can go straight to one part of the world.
* A build can then ask, for example, "every area tagged as an administrative boundary at level 2, in the Europe reading box". GeoDesk finds the relations, follows them to their ways and nodes, and gives back each country's finished outline.
* It takes a few hours and most of the laptop's memory, and the result is about 140 GB. It is made once for each planet file, and every build after that uses it.
* The GeoDesk library leaves out some details a build never needs, such as who last edited each feature.

### Step 3: picking out the areas

For the base pack lite in Phase 1, the build asks the GeoDesk library for:

* every country, at OSM level 2;
* every first-level division, at OSM level 4, such as England, Scotland, Wales and Northern Ireland, or Spain's autonomous communities.

Each one comes back as an outline that includes the sea out to 12 nautical miles. Some need repair first. For example, a mapper may have left a small gap where two ways should meet, so the outline doesn't close. The build closes small gaps like this and lists every repair in its report.

### Step 4: adding the other sources

OSM's boundaries aren't enough on their own, so the build adds:

* the land polygons: all the land in the world, made by OSM from the coastlines. They are used to remove the sea from each area;
* the VLIZ seas: the names and shapes of the oceans and seas, such as the English Channel and the North Atlantic Ocean. Without them, a point at sea would have no name.

Each source's licence and date are recorded, and go into the pack's attribution. The planet file and the land polygons should be from close dates, so that the coastline in one matches the coastline in the other. That's why the planet file of 26 October 2026 was downloaded on 3 November, to go with the land polygons of 31 October 2026.

### Step 5: trimming and cleaning

* Each area is trimmed to the coast with the land polygons. The section "How the build trims countries to the coastline" explains this.
* The seas get the land taken away, so a sea and the land beside it meet exactly at the coast.
* Each layer is cleaned, so that neighbours meet with no gaps and no overlaps. For example, where OSM's borders of Burgos and Soria in Spain overlap, the overlap is given to the one that shares the longer border with it.
* Every point on Earth must end up in a country or a sea (LOC-6). Discussion point 114 asks what you should hear where the data gives no name, such as Bir Tawil, which no country claims.

### Step 6: working out facts about each area

The build works out what the application needs to know about each area, without measuring anything while you're using it. For example, for Hampshire:

* its name, and its type, such as "county";
* its size: 3,674 square kilometres of land;
* the areas it is in: England and the United Kingdom;
* a colour number different from every neighbour's, so neighbours look different on the map;
* a point on its land, used when you jump to it.

### Step 7: simplifying for drawing

The exact shapes have far too many points to draw the whole world quickly. The UK alone has 2.2 million. So the build also makes simpler copies for drawing, at several drawing levels. At the simplest, used when the whole world is on screen, the UK keeps its main islands and leaves out the thousands of rocks. These simple copies are only ever used for drawing. Where you are, and how far away things are, always come from the exact shapes.

### Step 8: writing the pack

The build cuts every shape into pack tiles and writes the pack, with its manifest, attribution and checksum. The next section explains what is inside.

### Step 9: checking

Before a pack is finished, the build checks it and writes a report. For example:

* a grid of points over the whole Earth, every quarter of a degree: each point must be in a named country or sea;
* check places with known answers, such as a point 2 km off Brittany, which must be in the sea, and points either side of the 180 degree line in Fiji;
* building it twice from the same sources gives exactly the same file.

### Saving work between builds

Each step keeps its results in the data folder's tobymap\working folder. If a step's sources and settings haven't changed since last time, the next build reuses its results and skips it. So a change to the colours doesn't mean reading the GeoDesk library again.

## What is inside a pack

### Words used in this section

These are defined in full in the glossary.

* Pack: one file of map data that the application reads.
* Record: one stored item in a pack, compressed separately from the others.
* Directory: the list of every record's name and where it is in the file.
* Manifest: the record that describes the pack.
* Feature record: what the pack knows about one area, apart from its shape.
* Pack tile: one rectangle of a grid over the world, holding the shapes inside it. Each pack tile is one record.
* Tile level: the size of a pack tile. Each level up halves the width and height.
* Tile entry: what one pack tile holds for one area: either the part of its shape inside the pack tile, or a covered note.
* Covered note: a tile entry that says the area covers the whole pack tile.

### The example used in this section

The examples are taken from a real pack: the one from spike S2, stage 1, built on 2 November 2026. It holds the UK, France, Spain and their neighbours: 21 countries, 42 regions and 287 counties. It is 38.4 MB. The Phase 1 pack format adds more records, but the ideas are the same.

### One file, many records

A pack is like a reference book with its contents page at the back.

* The pages are the records. Each record is compressed on its own, so any one of them can be read without reading the rest.
* The contents page is the directory. It lists every record by name, with where it starts in the file and how long it is.
* To open a pack, the application reads the first 40 bytes of the file, the header, which say where the directory is. Then it reads the directory, and after that only the records it needs.

The example pack has 5,318 records:

* the manifest;
* the feature records, as one list;
* 5,316 pack tiles.

This matters most in the web version. There, each read can be one download, so the browser fetches only the few records for where you are, not the whole pack.

### The manifest

The manifest describes the pack. In the example pack it says:

* its name, s2-stage1;
* its source, the GeoDesk library made from the planet file;
* its licence, ODbL 1.0, OpenStreetMap contributors;
* that shapes are stored in compact coordinates;
* its tile levels, 3 to 17.

The Phase 1 manifest adds the pack's version and date, the application versions it works with, every source with its licence and date, its layers, and its drawing levels.

### Feature records

Each area has one feature record. Two from the example pack:

* the United Kingdom: identifier osm:r62149, in the Countries layer, of type country, 243,533 square kilometres;
* Hampshire: identifier osm:r172799, in the Counties layer, 3,674 square kilometres, and in the United Kingdom.

The identifier is the area's number in OSM, so osm:r62149 means OSM relation 62149. It stays the same in every pack, so a bookmark to it keeps working. In Phase 1, each record also holds the other facts from step 6, such as the colour number and a point on the land.

### Pack tiles: a grid over the world

The pack's shapes are stored in a grid of rectangles over the world, made of lines of latitude and longitude.

* At tile level 3, the world is split into 8 columns, each 45 degrees wide, and 8 rows, each 22.5 degrees tall, so 64 pack tiles in all. For example, the level 3 pack tile around Winchester runs from 45 degrees west to the Greenwich meridian, and from 45 to 67.5 degrees north. It holds Ireland, most of Great Britain, Iceland, the Faroe Islands and a large part of the North Atlantic.
* Each level up splits every pack tile into four, by halving its width and its height. Around Winchester:
  * at level 4, a pack tile is 22.5 degrees by 11.25;
  * at level 9, it is about 49 km east to west by 39 km north to south;
  * at level 10, about 24 km by 20 km;
  * at level 17, the smallest in the example pack, about 190 metres by 150.
* Pack tiles are rectangles in degrees, not squares. On the ground they get narrower towards the poles, because the lines of longitude come closer together. A level 10 pack tile is about 39 km wide at the equator but 24 km wide at Winchester.
* A pack tile is stored only where something is in it. A pack holding only Europe has no pack tiles over the Pacific.

### How a shape is placed into pack tiles

Each area's shape is put into the grid by one rule: a tile entry may hold at most 4,000 points.

1. The build starts at level 3, with the part of the shape inside each level 3 pack tile.
2. If that part has 4,000 points or fewer, it is stored whole as a tile entry in that pack tile.
3. If it has more, it is cut into the four smaller pack tiles at the next level, and each of those is checked in the same way.
4. If a pack tile lies wholly inside the area, there is no shape to store. Its tile entry is just a covered note, which says "this area covers all of this pack tile".

Three examples from the example pack:

* Aberdeen City is a small area with a simple shape of 3,416 points. It is stored whole, in the level 3 pack tile.
* Hampshire has more than 4,000 points, so it is cut into smaller pack tiles. Around Winchester, the level 10 pack tile, 24 km by 20 km, lies wholly inside Hampshire. Its tile entry is a covered note, and that whole pack tile takes 15 bytes in the file.
* The UK has 2.2 million points, mostly along its coast. Around Winchester, far from the coast, it is a covered note at level 9. Around Skye, the coast is so detailed that the shapes are cut down to level 11, where a pack tile is about 11 km by 10 km. That pack tile holds a 276-point stretch of Skye's coast three times: once for the UK, once for Scotland and once for Highland.

So pack tiles are large where shapes are simple, such as inland or over open sea, and small along detailed coasts. In the example pack, most pack tiles are at levels 10 to 12.

A second rule was added after the example pack was made: a pack tile is also split when all its tile entries together hold more than 20,000 points. Without it, one pack tile in southern Norway held 332 municipalities, and every lookup there took three quarters of a second. In the example pack, the level 3 pack tile around Winchester holds 42 whole shapes of small counties and cities, 360 KB in all. In a Phase 1 pack it would be split.

### Compact coordinates

Each point of a shape is a latitude and a longitude. A pack stores them in compact coordinates:

* each number is a whole number of ten-millionths of a degree, which is about 1 cm. So 51.063 degrees north is stored as 510,630,000;
* each point after the first is stored as the difference from the one before. Points along a coast are close together, so the differences are small numbers, such as 412, and small numbers take only one or two bytes instead of eight.

In spike S2, this made packs about five times smaller. The UK, France and Spain took 38.4 MB instead of 172.3 MB.

### Finding what is at a point: Winchester

Here is what the application does to find what is at Winchester, 51.063 north and 1.308 west, in the example pack.

1. For each tile level from 3 to 17, it works out which pack tile contains Winchester, and looks for that pack tile in the directory. At 7 of the 15 levels a pack tile exists there, so it reads 7 records. At the others there is nothing to read.
2. It goes through every tile entry in those pack tiles:
   * a covered note counts at once. The level 9 pack tile has covered notes for the UK and England, and the level 10 pack tile has one for Hampshire;
   * a shape is tested to see whether Winchester is inside it. Most aren't, because a pack tile holds every area with a shape anywhere in it. For example, the level 8 pack tile holds a shape of the Isle of Wight, and the level 6 pack tile holds Warrington. Both answer no.
3. It sorts what it found, smallest first: Hampshire, England, United Kingdom.

On 3 November this took about 85 milliseconds, while the laptop was busy building the GeoDesk library. Most of that time went on the 42 shapes in the level 3 pack tile. With the second rule above, spike S2 measured about 20 milliseconds for a lookup. The pack tiles it read are kept in memory, in the pack tile cache, so the next step near Winchester needs few or no new reads.

### Finding what is at a point: the sea off Dorset

At 50.6 north, 1.9 west, a few kilometres off the Dorset coast:

* the level 7 pack tile there holds the UK's south coast, as a shape of 3,733 points;
* the point is outside it, and outside every other shape in the pack tiles read;
* so the example pack answers "sea, no land area".

The base pack lite also has the VLIZ seas, so the same point will be in a sea, and you will hear "English Channel".

### Drawing tiles

A Phase 1 pack also holds drawing tiles. They are pack tiles holding the simplified shapes from step 7, one set for each drawing level. They are used only to draw the map. Finding what is at a point, as above, always uses the exact shapes.

### How a pack is checked

Phase 1 packs, in format 2, are checked in three ways.

* A check number for every record. The directory holds a short number worked out from each record's bytes. When the application reads a record, it works the number out again. If one byte of a pack tile is damaged, say by a failing disk, the numbers differ, and that pack tile is reported as damaged. The application carries on without it, and everything else in the pack still works (NFR-4).
* A checksum for the whole pack. The build writes a small file beside the pack, such as base-lite.pack.sha256, holding a long number worked out from every byte. After a download, the application works it out again. If it differs, the download is damaged or incomplete, and you are asked to download it again (PCK-5).
* The versions it works with. The manifest says which application versions the pack is for. An older TobyMap opening a pack that needs a newer one says so and asks you to update, rather than misreading it.

Every message for these comes from the templates, so each is clear when spoken, for example: "world.pack needs TobyMap 0.2.0 or later, and this is TobyMap 0.1.4, so it was not opened. Update TobyMap to use it."

Building the same pack twice from the same sources gives exactly the same file, byte for byte (DMT-1). That is why the build date in the manifest is the date of the newest source, not the day of the build.

### Packs in later phases

The base pack lite covers the whole world, with a few layers. Later phases add other packs. A pack can cover a smaller area, such as Great Britain, and hold other layers, such as roads, and both are stored in the same way, as records, pack tiles and tile entries. Where two installed packs cover the same place, the application uses the more detailed one there (AD-14).

## How TobyMap measures the Earth and moves you on it

This is task P1-T1, core geodesy. It is the arithmetic that every other part of the application relies on when it deals with a position. It isn't about map data: it doesn't know about countries or seas. It answers questions about points on the Earth.

### Words used in this section

* Ellipsoid and move path, as in the glossary.
* Bearing: the direction from one place to another, in degrees clockwise from north.
* The core: the Python shared by the desktop and web versions.

### What it answers

* How far is it from here to there? London to Paris is 343.8 km over the Earth's surface.
* In which direction? From London, Paris is at a bearing of 148 degrees.
* Where do I land if I step 10 km north, or east? A step north or south follows the meridian, the line of longitude. A step east or west follows the line of latitude, so you stay at the same latitude however far you go.
* Can I step at all? A step north that would reach or pass the North Pole is refused, and so is a step south past the South Pole, so the application can play the blocked sound.
* What happens at the 180 degree line? A step east from 179.9 degrees east lands at 179.9 degrees west, in Fiji or the Bering Strait, just as it would anywhere else.
* How big is a country that crosses that line, such as Fiji, and where is its middle? Its parts on both sides are treated as one shape, so its bounding box is a few degrees wide, not nearly the whole world, and its middle is in Fiji.

### Why the ellipsoid, not a ball

The Earth is slightly flattened. Working it out on a perfect ball is wrong by up to about half a percent, which can change a spoken distance. For example, from the start position, Belgium's label point was 424 km on the ball, said as 420 kilometres. On the ellipsoid it is 426 km, said as 430. The application now uses the ellipsoid, through a free library called GeographicLib (MIT licence). It is written in plain Python, so the web version runs exactly the same sums in the browser.

### Numbers, not words

The last part turns a measurement into what should be said, in your chosen style, but only as a number and a short code. For example:

* 344,000 metres in metric is the number 340 and the code for kilometres. In imperial it is 210 and the code for miles.
* A bearing of 47 degrees is 47 exactly, about 50 when rounded to 10 degrees, 2 for 2 o'clock, or the code for north-east with 8, 16 or 32 compass points.
* Coordinates are given to 5 decimal places, about 1 metre, or in degrees, minutes and seconds.

The words themselves, such as "kilometres" and "north-east", are added by the templates in task P1-T7. So every word the application says stays in one file, where it can be checked and, one day, translated.

### What you will notice

Nothing yet, apart from some distances in the Information panel's Nearby group, which may differ by 10 km from version 0.0.7 because they are now worked out on the ellipsoid. Stepping in metres and kilometres, "where am I", and the formats you choose in the settings are built on this in tasks P1-T5 to P1-T9.
