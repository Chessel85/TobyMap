# Discussion points in detail: responses

Responses to "Discussion points in detail.txt" (17 November 2026). The first part is a statement of how TobyMap draws the map and orders what it says. It is written from your comments and decisions of 17 November, so it can become the definition. The rest, from DP199, is still my first response.

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

## DP199: distant parts and the legal position

### Is what you said right?

Mostly yes. The law does give a clear distinction, and it is not the continent.

* Canary Islands and Madrid: right. Both are autonomous communities of Spain, and fully part of Spain. The Canary Islands have some extra arrangements, such as their own tax system and the EU status of an "outermost region", but they are no less Spanish.
* French Guiana, Corsica and Marseille: legally, all three are part of France. French Guiana is an overseas region and department, under French law with some adaptations, part of the EU, and it uses the euro. Corsica has a special status of its own, but is also fully part of France. So legally French Guiana is no more separate than Corsica. That is why option 2 (as Google does it) gets it backwards: it leaves out France for exactly the place that is legally part of France. Google may do so because French Guiana has its own country code in addresses, but that is a postal habit, not the law.
* Jersey and Guernsey: these are Crown Dependencies. They belong to the British Crown but are not part of the United Kingdom, have their own parliaments and laws, and were never in the EU. The UK looks after their defence and foreign affairs. The Isle of Man is the same.
* The Falkland Islands: a British Overseas Territory. It is under British sovereignty but not part of the United Kingdom, and Argentina claims it.

### The two kinds of distant part

The law sorts places into two kinds:

* Integral parts, legally as much part of the country as its capital: the Canary Islands, Madeira and the Azores, French Guiana and Réunion, Hawaii, Corsica, and Svalbard.
* Dependent territories, which belong to a country but are not part of it, and usually have their own government: Jersey, Guernsey and the Isle of Man, the Falkland Islands and the other British Overseas Territories, Greenland and the Faroe Islands, Aruba and Curaçao, Puerto Rico and Guam, French Polynesia and New Caledonia.

There are grey cases. French Polynesia is part of the French Republic, but governs itself and is outside the EU. Bonaire is a municipality of the Netherlands itself, while Curaçao, nearby, is a country within the Kingdom of the Netherlands. This is why your idea of a list is a good one.

### What the world pack does now

I checked these with the world pack today. The continent rule and the legal rule disagree:

* Jersey, the Isle of Man, the Falkland Islands and Greenland are countries of their own, with no sovereign state said. This matches the law, because OpenStreetMap already keeps them separate.
* The Canary Islands, Madeira, French Guiana, Réunion and Hawaii are distant parts: areas of their own, with the sovereign state stored but not said. Legally they are integral parts, so this is the case that feels wrong to you.
* Puerto Rico says United States, because it is on the same continent as the rest of the United States. Hawaii, a full US state, does not. Legally it is the other way round: Puerto Rico is a territory, not a state.
* Svalbard says Norway, because Norway's mainland is on the same continent. This happens to be legally right.

### Recommendation: a legal rule, held in a list

One rule: say the sovereign state after any area that is legally part of it, and not after a dependent territory. Details gives every area's status and sovereign state in words.

What you would hear:

* Tenerife: Santa Cruz de Tenerife, Tenerife, Canary Islands, Spain, Africa.
* Honolulu: Honolulu County, Oahu, Hawaii, United States, Oceania.
* Cayenne: Cayenne, French Guiana, France, South America.
* Jersey: Saint Lawrence, Jersey, Europe. Details says: Crown Dependency of the British Crown, not part of the United Kingdom.
* Stanley: East Falkland, Falkland Islands, South America. Details says: British Overseas Territory, claimed by Argentina.
* Puerto Rico: Orocovis, Puerto Rico, North America. Details says: territory of the United States. This would make Puerto Rico an area of its own in the Countries layer, a change to the build.

The pack keeps the distant parts as areas of their own (DP191), so France still fits Europe and its neighbours stay in Europe. Only what is said changes, apart from places such as Puerto Rico.

> go with this recommendation 

### The list you suggested

Yes. A small CSV file in the build settings, one row for each place, about 70 rows. Its columns would be:

* The place.
* The sovereign state.
* The legal status, in plain words: integral part, autonomous part, Crown Dependency, overseas territory, freely associated state, or disputed.
* Whether the sovereign state is said.
* What is said under each of the rule options, so you can compare them.
> is csv robust enough?  I thought there would be more robust ways to keep this list which are still human readable enough.


A ready-made starting point exists. Natural Earth, which TobyMap already uses, marks each country-level area as a sovereign country, a country, a dependency, disputed or indeterminate, and names its sovereign state. Wikidata says what kind of territory each place is. I'd build the list from these, check each row, and give you the grey cases to decide. I can make the list next if you want it.
> make the entire list, but flag any you want my input on.

## DP200: lakes and the areas round them

### Is what you said right?

Yes. Being on a lake and in a canton at the same time is right, and the hierarchy already says it that way: Lake Geneva, Upper Savoy, Auvergne-Rhône-Alpes, France, Europe.

### How cantons in a lake are drawn

See "How TobyMap draws the map": the lake is painted over the land, and the borders are drawn across it as lines.

### Bordering seas

Your point is a good one, and it is the mirror of option 1's "Shores" heading:

* For a lake or sea, Bordering gets a heading "Shores", listing the land areas round it with their length of shore: "Obwalden, south, 12 kilometres of shore".
* For a country, county or other land area, Bordering gets a heading "Coast", listing the seas and oceans it touches with its length of coast on each: "Bay of Biscay, north, 712 kilometres of coast".

Land and sea never overlap, so both lists are exact. Both are worked out in the build.

### Recommendation

Option 1 with the Coast heading added. Overlapping then keeps only the natural areas, under headings by kind.

## DP201: border share, crossings, and where a border starts and ends

Your answer is already in the discussion points file, and the recommendations stand. On your new idea:

### The ends of a shared border

Yes, this can be done. Each Bordering item can be opened to list the ends of the shared border, each with its direction and distance, so that Space and Enter work on each one as on any item.

From Madrid:

* Portugal: two ends. North-west, where the Minho river meets the Atlantic. South-west, where the Guadiana meets the Atlantic.
* France: four ends, as you say, because Andorra splits the border into two stretches. One stretch runs from the Atlantic at the Bidasoa river to Andorra. The other runs from Andorra to the Mediterranean.
* Also with France: Llívia, a small Spanish town wholly inside France. Its border with France is a closed loop, with no ends. I'd list it as one item, "Llívia, a stretch with no ends, 13 kilometres round", with the direction and distance to its nearest point.

Each end would say what is there: the coast, or the country where three borders meet. The distances in these examples, and in DP200's, are rough figures for illustration, not measured. For example: "End of the border with France, at the coast, Mediterranean Sea, 590 kilometres east"; "End of the border with France, where Andorra meets it, 480 kilometres north-east".

The ends would be worked out when the item is opened, from the shared border the build already stores, like the crossing points in the recommendation you accepted.

## DP202: the current feature

### Is there a current feature?

Yes. It is in the glossary: the current feature is what you are on. When stepping, it is the smallest area where you are. In hierarchy mode, it is the feature you last moved to.

### What can you do with it without moving?

* The Information panel's Contains, Bordering, Overlapping and Crossing groups are all about the current feature.
* Details describes it.
* It is outlined on the map, and can be isolated, so that nothing else is drawn.
* Browse by category (Ctrl+Shift+F) lists the kinds of feature inside it.

But your challenge is fair. If it changes back the moment you move, it is a one-off look, not a way of working.

### Your idea: keep the same kind of area

Your idea is better than my option 1. Shift+Enter on an item makes its layer the current layer, and its feature the current feature. As you step, the current feature stays in that layer: the area of that layer you are in, not the smallest area.

* Shift+Enter on Obwalden in Within: the Regions layer becomes the current layer, and Obwalden the current feature. The groups are about Obwalden. Step into Nidwalden, and Nidwalden becomes the current feature. The groups follow the cantons.
* Where the current layer has nothing, such as Deserts in the Atlantic: the current feature goes back to the smallest area, and the status line says "Deserts: none here". Step back into a desert, and it is picked up again.
* To stop, Shift+Enter on the smallest area, or a key to be chosen, goes back to the usual rule.
* What "where am I" says does not change. Only the current feature, and so the groups, the outline and Details, follow the current layer.

### The zoom rules, and grinding to a halt

Neither is a problem here:

* Following a layer finds only the one feature of that layer at your point. The core already looks this up on every move. It never draws or lists the whole layer, so following villages over Africa costs no more than following countries.
* The zoom rules decide what is drawn and said by itself. A current layer is your own choice, so it is followed at any zoom.

### Is this an industry standard, or a new problem?

It is standard in GIS programs. The audio atlas only makes it matter more.

* QGIS has an "active layer": the layer chosen in its layers list, which its tools work on.
* QGIS's Identify tool, which tells you what is at the point you click, has modes: the current layer only, the top layer only, or all layers.
* Showing each layer only within a range of zooms is standard too. GIS programs call it scale-dependent visibility. It is the same idea as TobyMap's zoom ranges.

What is new for an audio atlas is that sight filters the map for free, while speech has to choose an order. The current layer is how GIS programs answer "which feature does the user mean?", and it suits TobyMap for the same reason.

### Recommendation

Your version, with Shift+Enter, in place of options 1 and 2. "Current layer" would go in the glossary first. It is simple for the user: one key, one idea (follow this kind of area), and the usual behaviour returns with the same key.

## What I need from you

* DP199: the legal rule, and shall I make the list of about 70 territories next?
* DP200: option 1 with the Coast heading added?
* DP201: the ends of a shared border as items under each Bordering item?
* DP202: a current layer, set with Shift+Enter, in place of options 1 and 2?

## Sources

* [iSonic: Interactive Data Sonification for Blind Users, University of Maryland](https://www.cs.umd.edu/projects/hcil/audiomap)
* [Zhao, Plaisant, Shneiderman and Lazar, Data Sonification for Users with Visual Impairment, 2008](https://www.cs.umd.edu/users/ben/papers/Zhao2008Data.pdf)
* [RESOLVE Ecoregions 2017, Google Earth Engine catalogue](https://developers.google.com/earth-engine/datasets/catalog/RESOLVE_ECOREGIONS_2017)
* [Natural Earth, Admin 0 Details](https://www.naturalearthdata.com/downloads/10m-cultural-vectors/10m-admin-0-details/)
* [Natural Earth, Disputed Territories: the "type" field](https://www.naturalearthdata.com/?p=4901)
* The legal status of the territories is from my own knowledge, not checked online today. I'll check each row when making the list.
