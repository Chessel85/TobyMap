# Response to your Phase 3 tidy-up desktop results

Written on 18 November 2026, in answer to docs/checklists/phase-3-tidy-up-desktop-results.txt, and rewritten on 19 November 2026 with your comments. Each point now says where it stands. I checked your new questions against the code and the Western Europe trial pack.

From your run: 60 steps passed, one failed (11.4), and one was not done (12.4).

The document has six parts:

1. Answers to your questions, from both rounds.
2. Faults I'll fix without asking, task P3-T28.
3. Changes you asked for, also in P3-T28.
4. The Information panel, task P3-T29.
5. Your answers to questions Q1 to Q8.
6. New questions, R1 to R6.

The tasks are in a new plan, docs/plan/phase-3-tidy-up-plan2.md. The Information panel's definition is in docs/design/explanation.md, section "How the Information panel's groups are filled", rewritten from your comments rather than added to.

## 1. Answers to your questions

### Elevation in Details (4.1)

It is Wikidata's "elevation above sea level", one height for the whole place, usually at its centre. You chose to drop it for areas and keep it for places, Q1.

### The full place NVDA reads on the map

It is the map's accessible name, read only by screen readers, never shown. It goes into the user guide: a screen reader's object navigation can read the current location from the map. I've noted it for the user guide in the plan.

### "Scotland, 6 kilometres east" on Islay, and England under Counties

A stand-in area: land of a region in none of its counties, which the build filled with an area named after the region. It also gives Hampshire its 1.6 kilometre border with "England", and Bournemouth its 100 metre border with "England", which you met in hierarchy mode. P3-T28a fixes all of these.

### What sets the number of nearby places

The setting "Number of nearby items", in Settings, Movement. It starts at 8. Nearby lists that many of the nearest visible features within the zoom distance, and look around plays the same items. Jura was in Nearby from Islay at 25 kilometres; Great Britain was not, as the 8 nearest were all closer.

### Bath Hole and Hatch Pool (2.3)

They are fishing pools on the River Test, tagged in OpenStreetMap as bays. P3-T28c keeps a bay only at the coast or on a lake. Yes, that means these pools will not be in the pack at all: no layer holds pools in rivers.

### The M3 (2.3, 9.4)

Two faults. Contains measured to the road's own point, near Basingstoke, not its nearest point, which P3-T29c changes. And England's M3 and Belfast's M3 were joined into one road, which P3-T28d splits. Where the M3 crosses the River Itchen is not stored by the build; it is part of question R5, on networks.

### Llívia (3.1)

The town of Llívia is not in the pack, as in Spain the Counties layer stops at the provinces. The exclave will be said by its own name, "Llívia, exclave of Spain in France", P3-T28j.

### Coordinates in Details (8.2)

You retested and it passes. Closed.

### Hierarchy mode (set 10)

You said you understand it much better now. So P3-T28e, the unclear mode after Escape, is dropped, and the explanation section on hierarchy mode is not needed for now. Your new points:

* The order of the kinds in the Down list ("Inside" dialog): the layer order, the same as the Layers dialog. Continents, countries, oceans and seas, seas, bays and straits, mountain ranges, deserts and other regions, peaks, regions, islands, counties, rivers, roads, railways, towns, enclaves and exclaves, lakes.
* England beside Bournemouth: yes, the same stand-in problem, P3-T28a.
* Yes, Left and Right move you: the map redraws and your position changes. It is another way of moving round the map.
* Enter on Hampshire said "Nothing to go to". Left and Right keep going round the feature you started from, Bournemouth, and Enter on the map only goes to what look around is playing. P3-T28o makes Enter on the map, in hierarchy mode, start going round the feature you are on. So Right to Hampshire, Enter, then Left and Right go round Hampshire's neighbours.
* Exmoor had nothing above it. A fault: 1.2 percent of Exmoor's outline is in the sea, so the build found it wholly inside nothing, only overlapping England, Devon and Somerset. P3-T28n measures only the land of a land area, so Up from Exmoor goes to England. Somerset and Devon each hold only part of it, so they are in its Overlapping group. Mountain ranges already contain their peaks: the Alps hold 16,152.
* Obwalden at 1,000 kilometres: Obwalden is itself a canton, in the Regions layer. Below it are its 7 municipalities, in the Counties layer, but at 1,000 kilometres only Kerns is big enough to show, so the Down line says "Counties: 1 shown at this zoom, 7 in all". The Alps hold Obwalden, so they are above it: Up offers them. To see the cantons and the Alps, go down from Switzerland. DP208, still open, asks whether Down should list everything inside, whatever its size.
* Down from the English Channel listed roads, towns and rivers. A fault: the sea's outline from Natural Earth is rough and overlaps the coast, so coastal roads and two towns, Porthleven and Looe, were found inside it. In the new definition, water holds only water features and islands, P3-T29d.
* Networks of rivers, roads and railways, lakes joined to rivers: question R5.
* Islands, bays and towns stay as they are.

### The Moselle condominium (13.3)

You don't like it listed as a separate country, and asked how other maps cope. What I found:

* In OpenStreetMap it is one boundary relation, "Gemeinsames deutsch-luxemburgisches Hoheitsgebiet", tagged as an administrative area, which is why our build found it at country level.
* Luxembourg's national geoportal publishes it as a condominium dataset of its own.
* OpenHistoricalMap holds it as a country-level area too.
* As far as I can find, general maps for the public draw the Germany and Luxembourg border along the river and do not show the condominium as a place of its own. I could not confirm how each one does it.

The options are question R1.

### The panel and the explanation document

Your comments in the explanation document are taken into the rewritten definition. In brief:

* The new order, as you gave it: Within, Nearby, Bordering, Contains, Overlapping, Passed over, Search. Shift+1 to Shift+7 follow it.
* Contains means wholly contains. A feature partly inside is in Overlapping.
* Crossing is folded into Overlapping, as you suggested: lines partly inside an area, with their crossing points, and lines along its border.
* A point has nothing in Overlapping.
* Distances in Contains go to the nearest point, and an area you are in says "you are inside".
* Bays and straits are one subgroup.
* Passed nearby items are said "passed nearby to Winchester", and Passed over can be sorted.
* Nearby leaves out a place you are at.
* For a later phase: an area's centre as the centre of its largest part, such as Great Britain for the United Kingdom.

Your questions there:

* Why "Contains British Isles" at the United Kingdom: the current feature, when you have not just gone to a feature, is picked by layer rank, and the Deserts and other regions layer, which holds the British Isles, ranks above Countries. "Where am I" said "United Kingdom, British Isles, Europe", so the current feature should have been the United Kingdom. P3-T28m picks it as "where am I" says it.
* Bounding boxes and what is contained: what is inside what is already worked out properly by the build, from the real shapes, and stored in the pack. The bounding box is used only to decide which of those features are near enough to list. Measuring to each feature's nearest point instead means reading each one's shape when the list is made. That is slower for long lists, such as everything in England, so I'll time it on the world pack. Whether Contains should be limited by the view at all is R2.
* What "nearly touches" means: two areas of the same layer with no shared border, whose gap is no wider than a quarter of the smaller one's width, and never more than 5 kilometres. Each area keeps the 10 nearest. Hampshire nearly touches the Isle of Wight, 1.3 kilometres across the Solent.
* Overlapping for an area today lists only areas. Lines partly inside are in Contains and Crossing. In the new definition they are in Overlapping.
* A line wholly inside an area shown as "Within": question R3.
* A key to say the sort order: question R4.

## 2. Faults I'll fix without asking, task P3-T28

* P3-T28a The stand-in areas named after a region. Slivers are left out; a larger one is named as what it is, such as "Part of Scotland in no council area", and is never said by the region's bare name. Needs a build.
* P3-T28b The Coast subgroup lists the most detailed water only, and its heading gives the whole coast's length, such as "Coast, 180 kilometres". The Sea of the Hebrides on Hampshire's coast goes.
* P3-T28c Bays and straits keeps a bay only at the coast or on a lake. Needs a build.
* P3-T28d A road whose parts are far apart is split into separate roads. Needs a build.
* P3-T28f The Moselle condominium in the world tree: waits for your answer to R1.
* P3-T28m The current feature, when stepping, is the first area "where am I" says, so the United Kingdom, not the British Isles.
* P3-T28n A land area's share inside another is measured on its land only, so Exmoor is wholly inside England. Needs a build.
* P3-T28o Enter on the map, in hierarchy mode, makes the feature you are on the one Left and Right go round.

P3-T28e is dropped, as you understand hierarchy mode now.

## 3. Changes you asked for, also in P3-T28

* P3-T28g Details:
  * "The location is" becomes "Location:".
  * The border line uses "is": "of which land is 370 kilometres and coastline is 180 kilometres".
  * Enter on the Wikipedia article line opens it, as W does.
  * Elevation is said for places only, such as peaks and towns, not for areas (Q1).
  * Source says "Shape and name: OpenStreetMap, ODbL licence" (Q2).
* P3-T28h The Map views dialog: the focus lands on the view in use; Add, Rename and Delete are buttons; OK and Cancel buttons, OK the default; Escape also cancels, as it is the Windows standard, and Cancel is there too.
* P3-T28i The ends of a shared border are sorted by direction, clockwise from north, or from ahead.
* P3-T28j An exclave is said with its own name: "Llívia, exclave of Spain in France".
* P3-T28k A zoom change says the place too, when what Space would say has changed.
* P3-T28l Ctrl+Alt+W opens the current feature's Wikipedia article, from anywhere. I'll check NVDA's keys and the browsers' keys. In browsers, Ctrl+Alt is the same as AltGr on many European keyboards, which types letters; if AltGr+W types a letter on a common keyboard, the web version gets another key, as you allowed.
* P3-T28p Space names a town you are near: "Near Winchester. Hampshire, England, United Kingdom" (Q6). How near is set by the town's size; I'll propose the distances with the first version for you to try.
* P3-T28q The query builder's "Of" list gets "Search for a feature", which opens search and comes back with what you choose (Q4). You'll review it.

## 4. The Information panel, task P3-T29

The definition is in the explanation document. P3-T29 makes the code match it:

* P3-T29a The new group order and keys, with Crossing folded into Overlapping and Crossed and passed renamed Passed over.
* P3-T29b Nearby leaves out a place you are at.
* P3-T29c Contains holds only features wholly inside, measured to the nearest point, with "you are inside", and bays and straits in one subgroup.
* P3-T29d Water holds only water features and islands.
* P3-T29e Overlapping: lines partly inside an area, with their crossings; lines along its border; for a line, the areas it passes through; nothing for a place.
* P3-T29f Passed over: "passed nearby to", and sortable.

Most of this is in the core and needs no build. Before the world build, so the world pack is checked with the panel as defined.

## 5. Your answers to questions Q1 to Q8

* Q1 Elevation: drop it for areas, keep it for places. In P3-T28g.
* Q2 Source: "Shape and name: OpenStreetMap, ODbL licence". In P3-T28g.
* Q3 The coast as a border: yes, tried on a small sample first. Task P3-T30.
* Q4 The query builder: do it, and you'll review. P3-T28q.
* Q5 "Scottish mainland": not needed, once the stand-in areas are fixed. No task.
* Q6 Towns in "where am I": give it a go. P3-T28p. This takes up part of DP206, which you parked.
* Q7 Loudness in look around: stays as it is. No task.
* Q8 The Information panel review: you started it in the explanation document, so it is P3-T29, before the world build.

As these are answered here, they do not go into the discussion points file.

## 6. New questions, R1 to R6

* R1 The Moselle condominium. Three options:
  * A. Keep it as today: an area in the Countries layer, said "Moselle condominium, shared by Germany and Luxembourg".
  * B. Not a country: an area of its own kind, shared. Stepping onto it says "Moselle condominium, shared by Germany and Luxembourg, Europe". It is not listed among Europe's countries; it is listed under both Germany and Luxembourg, and as a neighbour of each. This is my suggestion: it is true to the law and does not call it a country.
  * C. Leave it out, and draw the border along the middle of the rivers, as most maps seem to. Simplest, but not true: the water belongs to both.
* R2 Should Contains be limited by the view? My suggestion: yes, measured to each feature's nearest point, so the list stays about what is round you, and Browse by category lists everything inside whatever the view. If you'd rather Contains always listed everything inside, it becomes the same list as Browse by category.
* R3 A line wholly inside an area. You suggested showing it under Within. Within is about your position, the areas you are standing in. My suggestion: keep Within about your position, and reach the areas that hold a line with Up in hierarchy mode, as for any feature. Or would you like Within to be about the current feature?
* R4 Hearing a group's sort order. Ctrl+Shift+S is already the key to sort the other way round. My suggestion: the group's heading says its order, such as "Nearby, 8 items, by distance". A screen reader hears it on the heading, and a sighted user sees it, so nothing is missing for them either. Or a key of its own, such as Ctrl+Alt+S.
* R5 Networks: rivers flowing into rivers and lakes, roads and railways joining each other, where a road crosses a river. Left and Right on a river would go to the rivers it joins. This is new build work: every meeting of lines must be found and stored. My suggestion: a later phase, written up as requirements when we plan Phase 4, not now.
* R6 Two smaller wordings to confirm:
  * "passed nearby to Winchester" for a place a move went near. Or "passed near Winchester"?
  * The new group name "Passed over", for what was "Crossed and passed", holding lines crossed, areas passed over and places passed nearby.

## How I'll write checklists from now on

* "Go to 51.06,-1.31", without naming the key.
* "Make sure the settings are as they start: in the Map menu, choose Reset all settings", in place of a list of settings to check.

## What happens next

* I start P3-T28's fixes that need no build, then P3-T29, while you answer R1 to R6.
* The fixes that need a build, P3-T28a, c, d and n, go into the next Western Europe trial build, then the world build, P3-T21b.
* P3-T30, the coast as a border, is tried on a small sample before it goes into any build.
