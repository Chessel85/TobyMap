# Discussion points in detail: responses

Responses to your notes on the discussion points (17 November 2026), written from your comments and decisions of 17 November, so they can become the definition of how TobyMap draws the map, orders what it says, and handles distant parts, lakes, borders, the current layer, and enclaves and exclaves.

## How TobyMap draws the map (DP198)

### The principle

TobyMap is first a political map. A sighted user knows where they are from the shape of the land and the sea. A blind user's best anchor is the country. So in every map view, the country is always said and its borders are always drawn. Physical areas, and later figures such as temperature, are always given in relation to the countries.

### Map views

A map view decides two things:

* For each layer: whether it is shown, its zoom range, whether it is filled, and whether its outline is drawn.
* The order in which "where am I" says areas.

The drawing order is the same in every view.

There are two views to start with: the political view, which is the default, and the physical view. You can save your own settings as a view with a name of your own, and rename or delete it, in a view manager that has Close and Cancel buttons. The two built-in views cannot be deleted. Changing a setting of a view makes it Custom, until you save it as a view.

A view never changes the pack. It only changes how TobyMap draws and orders what the pack holds, while it runs. So the built-in views, and the drawing order, are in a plain text file that the data manager keeps with the application, read each time TobyMap starts. Changing it by hand needs no new build. Views you save are kept with your own settings.

Each layer's outline is drawn, except for oceans and seas. Sea areas blend into each other on the map, and their names show which is which. What is said still uses each sea's exact boundary.

### The order in which areas are said

Each view lists the layers in the order their areas are said. Within a layer, the smallest area is said first. This replaces the rule of saying all areas smallest first. In both views, a lake or sea you are on is said first, as being on water matters most.

The political view says government areas, then natural areas, then the continent. In the Atlas Mountains: "Cercle d'Asni, Marrakech-Safi, Morocco, Western High Atlas, High Atlas, Atlas Mountains, Africa". In Kent: "Kent, England, United Kingdom, Great Britain, British Isles, Europe".

The physical view says natural areas, then government areas, then the continent: "Western High Atlas, High Atlas, Atlas Mountains, Cercle d'Asni, Marrakech-Safi, Morocco, Africa". The country is always said.

### What each view fills

The political view fills the oceans and seas, the countries, regions and counties (see "Which layer has the colours"), and large lakes. A lake is a physical feature, but political atlases show large lakes: they are landmarks, and borders run through them. Mountain ranges, physical regions, islands and continents are not filled.

The physical view fills the oceans and seas, the physical regions, including groups of islands, the islands, the mountain ranges and the lakes, each in a colour for its kind. Countries, regions and counties are not filled, but their outlines are drawn.

### The drawing order

Later layers are painted over earlier ones. The data manager sets the drawing order in the views file. The user cannot change it.

1. Oceans and seas. Countries are cut to the coast, so they never overlap the sea.
2. Countries.
3. Regions.
4. Counties.
5. Physical regions, including groups of islands, larger under smaller.
6. Islands.
7. Mountain ranges, larger under smaller.
8. Lakes and rivers. A country's area reaches across a lake to its border, so the lake must be painted after it.
9. Outlines, as lines over everything painted so far. So the France–Switzerland border is a line across Lake Geneva.
10. Roads and railway lines, then places.
11. The current feature, on top of everything.

### Which layer has the colours

In the political view, the most detailed of the countries, regions and counties shown at the zoom is filled in colours, so that neighbours differ. The layers above it are drawn as outlines only, with country borders thicker.

* Zoomed out to the whole of Europe, the countries have the colours.
* At the middle zooms, where regions are shown but counties are not, England, Wales, Scotland and Northern Ireland each have a colour, inside the thick border of the United Kingdom. France's regions have colours too.
* Zoomed in close, the counties have the colours.

So at the middle zooms a country is not one colour: a sighted user tells the United Kingdom from France by the thick border. A country with no regions in the data is filled in one colour itself. The "Draw the borders of regions" setting goes.

### Islands

An island is a physical feature. In the political view it is not filled: it shows as land in the colour of the area it is in. Its name is still drawn on the map, and it is said: "Islay, Argyll and Bute, Scotland, United Kingdom, British Isles, Europe".

An island and a government area with the same name, covering nearly the same land, are said once. The Isle of Wight is an island and a county, and Guernsey is an island, a region and a country. In the world pack, 226 of the 199,278 islands have the same name as an area of about the same size, among them Sicily, Corsica, Tasmania and Cuba. The test compares the shapes, not only the name and the size: the island of Ireland is near the size of the country of Ireland, but it is a different area, as it includes Northern Ireland.

Groups of islands, such as the British Isles and the Balearic Islands, come from Natural Earth's physical regions. That source has some groups and not others: it has no Channel Islands. A fuller source of groups is task P4-T13.

### The Caspian Sea

The Caspian Sea is treated as a sea. It is in the Oceans and seas layer. OpenStreetMap maps its shore as coast, so the countries are cut to it as they are to the sea. Geographers often call it the world's largest lake, but its name, and the treaty its five shore countries signed in 2018, give it a status of its own.

### The current feature

The current feature is outlined in the current-feature outline (red at first), and filled with a translucent tint, in every view and whatever its layer, so it always stands out. When Obwalden is the current feature, its outline and tint run into Lake Lucerne, so a sighted user sees which part of the lake is Obwalden's.

The tint is the only translucent colour, until there are figures such as temperature. Several translucent areas over each other mix into colours that are hard to tell apart, especially with low vision or colour blindness. So a lake shared by several areas is plain water with the borders as lines across it, as atlases and online maps draw it.

### Territorial waters

Territorial waters will be a layer of their own, painted a lighter blue than the open sea. This is requirement DAT-15, in Phase 4 as task P4-T12. The data is already read: OpenStreetMap's country areas reach 12 nautical miles out to sea, and the build now cuts that part off at the coast. Wider zones, such as the 200 nautical mile exclusive economic zones, would need a new source.

### How much of the land the physical view covers

Islands and groups of islands are physical areas, so land off the mainlands is covered. But only part of the land is in a named landform, such as a mountain range, desert, plateau or plain. In Kent, the physical view fills and says Great Britain and the British Isles, but nothing about the land itself, such as the Weald. The physical view is built now, with these gaps.

Covering all the land with named landforms is for a later phase. What I found:

* No worldwide source of named landforms, such as massifs, basins and plains, under an open licence. There are national ones, for the United States and Australia.
* RESOLVE Ecoregions 2017 covers all the land with 846 named areas, under the CC BY 4.0 licence. But they are named for their plants and wildlife, such as "Celtic broadleaf forests", not their landforms.
* Landform classes worked out from land height (plains, hills, mountains and tablelands) cover everything, but have no names.
* Land height itself, coloured in bands as on a paper physical map, is the elevation grid layer (DAT-6).

### Figures for every square, later

Figures such as temperature, held for every 10 kilometre square, are grid layers (DAT-6). Nothing is built for them until there is a working example. They will be drawn as a translucent colour scale over the countries, with a key to the colours, and said only when asked for, or followed by a sound whose pitch rises with the value.

### What changes from today

All of this is built in the Phase 3 tidy-up, as task P3-T23. Nothing is fixed on its own before then. What changes:

* The drawing order moves from the code into the views file. Today lakes are painted with the sea, before the land, so they cannot be seen: at Lake Geneva, 87 land areas are painted over the lake.
* The two map views, the view manager, and the outline setting for each layer.
* Areas said in the order the view gives, in place of smallest first.
* The most detailed layer shown has the colours, with thicker country borders, in place of "Draw the borders of regions".
* The current feature's tint.
* Island names drawn on the map. Today names are drawn only for filled areas.
* An island and an area with the same name and nearly the same land said once. Comparing the shapes is done by the build, so this one comes with the new Western Europe and world builds, task P3-T21. Everything else needs no new build.

## Distant parts and the sovereign state (DP199)

### The rule

The law decides whether a country is said, not the continent. The sovereign state is said after any area that is legally part of it, and not after a dependent territory. Details gives every such area's status and its sovereign state in words.

### The two kinds of area

* Integral parts are legally as much part of their country as its capital, even when they have special arrangements of their own: the Canary Islands, Ceuta and Melilla, Madeira and the Azores, French Guiana and Réunion, Corsica, Hawaii, and Svalbard. Their sovereign state is said.
* Dependent territories belong to a country but are not part of it, and usually have their own government: Jersey, Guernsey and the Isle of Man, the Falkland Islands and the other British Overseas Territories, Greenland and the Faroe Islands, Aruba and Curaçao, Puerto Rico and Guam, French Polynesia and New Caledonia. Their sovereign state is not said.

There are grey cases. French Polynesia is part of the French Republic, but governs itself and is outside the EU. Bonaire is a municipality of the Netherlands itself, while Curaçao, nearby, is a country within the Kingdom of the Netherlands. Each grey case is decided once, in the territories list.

### What is said

* Tenerife: "Santa Cruz de Tenerife, Tenerife, Canary Islands, Spain, Africa".
* Honolulu: "Honolulu County, Oahu, Hawaii, United States, Oceania".
* Cayenne: "Cayenne, French Guiana, France, South America".
* Ceuta: "Ceuta, Spain, Africa".
* Jersey: "Saint Lawrence, Jersey, Europe". Details says: Crown Dependency of the British Crown, not part of the United Kingdom.
* Stanley: "East Falkland, Falkland Islands, South America". Details says: British Overseas Territory, claimed by Argentina.
* Puerto Rico: "Orocovis, Puerto Rico, North America". Details says: territory of the United States.

A distant part is still an area of its own in the Countries layer (DP191), so France still fits Europe and its neighbours are in Europe. Saying the sovereign state is a change to what is said, not to the pack.

A dependent territory is always an area of its own in the Countries layer, wherever it is. Most already are, because OpenStreetMap keeps them separate. Puerto Rico is not: OpenStreetMap maps it inside the United States, and it is on the same continent, so today it says "United States". The build makes it an area of its own, from the territories list.

### The territories list

The list of territories is a file in the build settings, about 70 entries, one for each place. Each entry gives:

* The place, with its OpenStreetMap and Wikidata identifiers.
* The sovereign state.
* The legal status, in plain words: integral part, autonomous part, Crown Dependency, overseas territory, freely associated state, or disputed.
* Whether the sovereign state is said.
* A note, for a grey case, saying why it was decided as it was.

The file is YAML, not CSV, as the other build settings are. Each entry is a short block with one field on each line, so it reads well line by line with NVDA, and it can carry comments. A CSV row puts every field on one long line, and a comma or quote in a note can break it, especially after editing in a spreadsheet. A test checks every entry when the build starts: each field is present, the status is one of the known ones, and each identifier is found in the data. So a mistake stops the build at once, with the entry named, instead of being heard on the map later.

The list is made from Natural Earth, which marks each country-level area as a sovereign country, a country, a dependency, disputed or indeterminate, and names its sovereign state, and from Wikidata, which says what kind of territory each place is. Every entry is checked, and the grey cases are marked for you to decide.

### What changes from today

* The sovereign state is said after an integral part, in the core, with no new build.
* Details gives the status and sovereign state.
* Puerto Rico, and any other dependent territory OpenStreetMap maps inside its country, becomes an area of its own. This needs the builds, task P3-T21.
* Ceuta and Melilla, in the world pack today, say "Spain, Europe", although they are in Africa. The next builds make them distant parts, as for the Canary Islands (P3-T19h), so they will say "Spain, Africa".

## Lakes, seas and the areas round them (DP200)

### Being on a lake

On a lake you are on the water and in the area that owns that part of it, at the same time. Swiss cantons own their part of each lake, and the borders run across the water. Being in one canton's part of a lake is no different from being on a lake wholly in one canton. "Where am I" says the lake first, then the areas, in the view's order: "Lake Geneva, Upper Savoy, Auvergne-Rhône-Alpes, France, Europe".

The lake is painted over the land, and the borders are drawn across it as lines (see "How TobyMap draws the map").

### Shores and coast

Bordering lists areas of the same layer. Two headings join it, which list the land round water, and the water round land:

* For a lake or sea, "Shores" lists the countries, regions and counties round it, under a heading for each layer, with the length of shore each has: "Obwalden, south, 12 kilometres of shore".
* For a country, region, county or other land area, "Coast" lists the oceans and seas it touches, with its length of coast on each: "Bay of Biscay, north, 712 kilometres of coast".

Land and sea never overlap, as countries are cut to the coast, so the Coast lengths are exact. Both lists are worked out in the build. The distances here are rough figures for illustration, not measured.

### Overlapping

Overlapping keeps only the natural areas, such as the Swiss Prealps, under headings by kind, as Contains has. Today, on Lake Lucerne, Overlapping lists 32 mixed items: every canton, district, municipality, mountain range and physical region that shares some of the lake. The government areas move to Shores.

### What changes from today

* The Shores and Coast headings, with the lengths stored in the builds, task P3-T21.
* Overlapping with headings by kind, and without the government areas round a lake.

## Borders, their ends, and crossings (DP201)

### Bordering

Each Bordering item gives the direction and distance to the neighbour, the length of the shared border, and its share of the whole border: "Nidwalden, north-east, shared border 69 kilometres, 28 percent". Details gives the whole border's length, land and coast.

### The ends of a shared border

Each Bordering item opens to list the ends of the shared border, each as an item with its direction and distance, so Space and Enter work on each one as on any item. Each end says what is there: the coast, or the country where three borders meet.

From Madrid:

* Portugal: two ends. North-west, where the Minho river meets the Atlantic. South-west, where the Guadiana meets the Atlantic.
* France: four ends, because Andorra splits the border into two stretches. One stretch runs from the Atlantic at the Bidasoa river to Andorra. The other runs from Andorra to the Mediterranean. For example: "End of the border with France, at the coast, Mediterranean Sea, 590 kilometres east"; "End of the border with France, where Andorra meets it, 480 kilometres north-east".
* Also with France: Llívia, a small Spanish town wholly inside France. Its border with France is a closed loop, with no ends. It is one item, "Llívia, a stretch with no ends, 13 kilometres round", with the direction and distance to its nearest point.

The distances are rough figures for illustration, not measured. The ends are worked out when the item is opened, from the shared border the build already stores.

### Crossing

Each line that crosses the current feature's border is one item, saying how many times it crosses and where the nearest crossing is: "A8, crosses twice, nearest 6 kilometres south-west". It opens to list each crossing point with its direction and distance, so Space and Enter work on each. The points are worked out from the line and the shape when the group is filled. If that is too slow on large areas, the build stores them.

### Enclaves and exclaves

A shared border round an enclave, such as Llívia's, is the stretch with no ends above. What is said about enclaves and exclaves is in their own section (DP207).

### What changes from today

All of this is in the core, with no new build: the share, the whole border in Details, the ends of a shared border, and the crossing points. Only if crossing points are too slow on large areas does the build store them.

## The current layer (DP202)

### The current feature

The current feature is what you are on. When stepping, it is the smallest area where you are. In hierarchy mode, it is the feature you last moved to. The Information panel's Contains, Bordering, Overlapping and Crossing groups, Details, the outline on the map, isolating it, and Browse by category (Ctrl+Shift+F) are all about the current feature.

### The current layer

Shift+Enter on an item makes its layer the current layer, and its feature the current feature. As you step, the current feature stays in that layer: the area of that layer you are in, not the smallest area.

* Shift+Enter on Obwalden in Within: the Regions layer becomes the current layer, and Obwalden the current feature. The groups are about Obwalden. Step into Nidwalden, and Nidwalden becomes the current feature. The groups follow the cantons.
* Where the current layer has nothing, such as Deserts in the Atlantic, the current feature goes back to the smallest area, and the status line says "Deserts: none here". Step back into a desert, and it is picked up again.
* Shift+Enter on the smallest area, or a key to be chosen, goes back to the usual rule.
* What "where am I" says does not change. Only the current feature, and so the groups, the outline and Details, follow the current layer.
* A current layer is your own choice, so it is followed at any zoom, whatever the layer's zoom range.

This is standard in GIS programs. QGIS has an "active layer", which its tools work on, and its Identify tool can look at the current layer only. What is new for an audio atlas is that sight filters the map for free, while speech has to choose. "Current layer" goes in the glossary.

### Drawing never silences TobyMap

A current layer adds almost nothing to the drawing: only its one feature is outlined and tinted. Following wards zoomed out to the whole world draws one ward. Finding the area of that layer where you are is a look-up the core already makes on every move.

But your worry is right in general. What can slow drawing is a layer shown at far zooms. You can already widen a layer's zoom range in the Layers settings, and a view will do the same. Two things limit this today:

* An area narrower than 2 percent of the zoom distance is not drawn. This is decided from its record, at almost no cost. At a 2,500 kilometre zoom, nothing under 50 kilometres across is drawn, so wards and villages never are.
* Zoomed out, shapes come from the simplified drawing tiles, not the exact shapes.

On the world pack, the slowest drawing measured in P2-T14 was 135 milliseconds on the desktop, and 238 milliseconds in the browsers.

What I found when I looked at the code:

* On the desktop, the map is drawn in a thread of its own. Keys and speech never wait for it. So the desktop cannot go silent while drawing.
* In the web version, the map is drawn in the same worker that answers the keys, and a key's answer is sent together with the drawing. So a slow drawing holds up what is said. This is the one place TobyMap could seem to have crashed.

The rule, in both versions:

1. What is said is sent before the map is drawn. A key's answer never waits for a drawing.
2. The map is drawn in steps, in the drawing order. Between steps, a new key is answered first, and a drawing no longer needed is dropped.
3. A drawing has a limit on its shapes. If a view would draw more, the smallest areas are left out, and the status line says "Some small areas are not drawn at this zoom".
4. If a drawing still takes more than 2 seconds, TobyMap says "Still drawing the map" once.
5. A test holds this: with every layer shown at every zoom, on the world pack, in both versions, no answer waits more than 100 milliseconds for a drawing. The timings are reported, as in P2-T14.

### What changes from today

* The current layer and Shift+Enter, in the core, with no new build.
* The drawing rule above. Its first step, sending the answer before the drawing in the web version, comes first, as it fixes the silence even before the rest.

## Enclaves and exclaves (DP207)

### The words

* An enclave is an area wholly surrounded by one other country. Llívia is an enclave in France. San Marino, the Vatican and Lesotho are whole countries that are enclaves.
* An exclave is a part of a country with a land border, cut off from its main part by another country. Llívia is an exclave of Spain: the same place, seen from Spain. Kaliningrad is an exclave of Russia, and Alaska of the United States.
* Ceuta and Melilla are exclaves of Spain on the African coast, but not enclaves, as each touches the sea as well as Morocco.
* Islands and other parts with no land border, such as Hawaii, are neither.

### How they are found

The build finds them from the shapes alone, so no list is needed. A part of a country with a land border, away from its main part, is an exclave. If its border touches only one other country, and no sea, it is also an enclave in that country. An exclave too small to be an area of its own, such as Llívia, is named after the largest place in it.

### What is said

* "Where am I" says it after the country: "Girona, Catalonia, Spain, exclave in France, Europe". For Ceuta: "Ceuta, Spain, exclave on the coast of Morocco, Africa".
* Details of the country lists its exclaves, and Details of the surrounding country lists the enclaves inside it: "Contains enclaves: Llívia, Spain".

Ceuta and Melilla are not in Morocco's Contains, which is right, as they are not inside Morocco. In the world pack today, Morocco's Bordering lists Spain, with 17 kilometres of shared border, which is the two towns' borders together. After the next builds, Ceuta and Melilla are areas of their own (see DP199), so Morocco's Bordering lists each of them, and each says "Spain".

### What changes from today

Today nothing says Llívia is cut off from Spain: at Llívia you hear "Girona, Catalonia, Spain, Europe". The enclaves and exclaves are worked out in the builds, task P3-T21.

## Next

The tasks for DP199 to DP202 and DP207, with the territories list, are in the Phase 3 tidy-up plan, task P3-T24. The data changes go into the builds, task P3-T21.

## Sources

* [iSonic: Interactive Data Sonification for Blind Users, University of Maryland](https://www.cs.umd.edu/projects/hcil/audiomap)
* [Zhao, Plaisant, Shneiderman and Lazar, Data Sonification for Users with Visual Impairment, 2008](https://www.cs.umd.edu/users/ben/papers/Zhao2008Data.pdf)
* [RESOLVE Ecoregions 2017, Google Earth Engine catalogue](https://developers.google.com/earth-engine/datasets/catalog/RESOLVE_ECOREGIONS_2017)
* [Natural Earth, Admin 0 Details](https://www.naturalearthdata.com/downloads/10m-cultural-vectors/10m-admin-0-details/)
* [Natural Earth, Disputed Territories: the "type" field](https://www.naturalearthdata.com/?p=4901)
* The legal status of the territories is from my own knowledge, not checked online today. I'll check each row when making the list.
