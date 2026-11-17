# Phase 3 tidy-up plan

Written on 15 November 2026, from your first pass of the desktop checklist (docs/checklists/phase-3desktop-results.txt).

The plan has six parts:

1. Fixes I make without asking, task P3-T19.
2. Speed, task P3-T20.
3. Discussion points for you, DP198 to DP206, in the discussion points file.
4. The builds, task P3-T21.
5. Testing again, task P3-T22.
6. Answers to the questions in your notes, and mistakes in the checklist.

The order of work is: the fixes and the speed measurements first, while you answer the discussion points. Then a Western Europe trial build with the data changes, then the world build. Then a short second pass of the desktop checklist with section 20, then the web and sighted checklists.

## 1. Fixes, task P3-T19

These are faults, or changes you asked for plainly. I make them without asking. The numbers in brackets are the checklist steps.

### P3-T19a Enter on an item makes it the current feature (14.4, 7.1)

* Now: Enter on an Information panel item, or on the map while look around plays an item, jumps to it and says the place there. So Enter on Winchester said "Hampshire", and Enter on Obwalden in Within went to Obwalden's centre, where Kerns became the current feature.
* After: Enter makes the item the current feature, as search, the world tree and hierarchy mode already do, and says its name first: "Winchester", then the place. The Contains, Bordering, Overlapping and Crossing groups are then about it until you move.

### P3-T19b Details follows the feature you went to (13.3)

* Now: after Enter on the Rhine in search, Details was about the Aare. Most likely, Details was still about an item selected in the panel before the jump, as a selected item comes before the current feature.
* After: a jump clears the selected item, so Details is about the feature you went to.

### P3-T19c The Information panel (6.2, 6.3)

* Shift+4 to Shift+8 put the focus on the group's heading, as the checklist said, so you hear its count first, such as "Bordering Obwalden, 4 items". Now it lands on the first item.
* Every item that is not a heading says its direction and distance, including the items under the headings of Contains, such as a peak.

### P3-T19d Details (4.6)

* The source on each line is shortened: "from Wikidata, as fetched on 13 November 2026" becomes "Wikidata, 13 November 2026".
* "Area, as published" is left out. The area measured from the shape stays.
* A new setting, "Show sources in Details", in the Speech tab, on at first. Off, the source is left off every line.

### P3-T19e The world tree (11.3, 11.5)

* An item with nothing under it no longer says "collapsed". To know this without a wait, the tree needs what is directly inside each area stored in the pack (DP194), so this part comes with the world build.
* The tree remembers which branches were open and where your focus was, until you close TobyMap, so W brings you back where you were.

### P3-T19f Look around says the direction too (14.4)

* While in development, each label in look around says the direction as well, such as "A34, north-east, 1.7 kilometres". A setting in the Speech tab, "Say the direction in look around", on at first, so it can be switched off later.

### P3-T19g The Moselle condominium (13.2)

* It is real: a strip of the river Moselle, about 7 square kilometres, owned jointly by Germany and Luxembourg. It is in the Countries layer as a condominium. Enter on it from the query's answer did nothing, which is a fault to find and fix.
* Whether it should count as a country bordering Germany is part of DP205.

### P3-T19h Ceuta and Melilla (9.8)

* The 17 kilometres of Europe bordering Africa is Ceuta and Melilla, Spain's two towns on the African coast. Their land is in the Europe continent area, because they are within 300 kilometres of mainland Spain, so the distant-parts rule did not separate them. When you answered DP191 you were told it would. This is a fault in the rule.
* After the build, they are distant parts in Africa, like the Canary Islands, and Europe no longer borders Africa.

### P3-T19i The first time, Shift+Page Up only clicked (2.1)

* After "Reset all settings" it worked. Most likely a step saved before the new step sizes (P3-T0f) was not loaded right. I'll try a saved settings file from before 10 November and fix the loading.

### P3-T19j Faults already listed in the checklist

These were in "Things I already know about", and are part of this task:

* Hawaii's Details ends "Source: part".
* Hampshire has no Wikipedia article.
* Ctrl+Shift+F said Lakes 13 in Switzerland, and listed 17.
* The Rhine's countries are out of order.
* The Isle of Wight said twice, which DP206 also touches.

### Progress on 15 November 2026

* Done in the code, with tests: P3-T19a, P3-T19c, P3-T19d, P3-T19e (remembering the tree; "collapsed" waits for the build), P3-T19f, P3-T19g, and Hawaii's source.
* P3-T19a also changed: Enter on an area goes to its own point, which the build puts on its land, as search and hierarchy mode do, not the centre of its bounding box. That is why Enter on the Moselle condominium went nowhere: the centre of a 73 kilometre strip of river is outside it.
* The source fix also covers Natural Earth: its code "ne" matched the "ne" in "OpenStreetMap planet", so the physical regions named OpenStreetMap as their source. Continents, unnamed islands and lines of latitude had the same fault as Hawaii.
* In the build, for the next builds, with tests: Ceuta and Melilla (P3-T19h: parts on different continents are never grouped); Hampshire's article (a Wikidata item with no English article takes one from an item it is "different from", only when that item's label and article are exactly the feature's name; 7,520 counties have no article now); the counts of Ctrl+Shift+F (made by the same test as the list); and the Rhine's order (a river's parts are chained, each going on from the part it starts near, instead of all being measured along the longest part).
* Not reproduced: P3-T19b. Tab from the map through the panel to Details, after Enter on a search result, gives Details about the result. Details is about the item focused in the panel, if any, so the Aare was most likely focused there. A question for you.
* Not reproduced: P3-T19i. The step sizes are not saved, so an old settings file cannot hold old ones. Most likely "Say the zoom and the step when they change" was off in your settings, and Clear all settings switched it on.

## 2. Speed, task P3-T20

Several things took far too long:

* Shift+4, Contains for Obwalden, about 10 seconds (6.2).
* Down from Europe in hierarchy mode, about 10 seconds (9.7).
* Alt+Comma from Austria back to Europe, said nothing for 10 to 15 seconds (9.7).
* The map at a zoom of 1,000 kilometres over Switzerland, slow to draw (4.5).
* The first opening of a branch of the world tree, 3 to 6 seconds (already known).

The work:

* P3-T20a Measure each one on the world pack, and find where the time goes. Report it to you.
* P3-T20b Fix in the code what can be fixed there. For example, Contains may be filling every heading's items before it shows any, and Alt+Comma to Europe fills the panel for all of Europe before speaking.
* P3-T20c Store what is directly inside each area in the pack (DP194, which you accepted). This needs the world build.

### What was measured, 15 November 2026, on the world pack

* Contains for Obwalden at 1,000 kilometres: 6.5 seconds, now 0.4. Most of it was reading the relationships of every feature in view, though only those whose bounding boxes meet Obwalden's can be inside it.
* Down from Europe: 42 seconds, now 5.7. It made an item, with an exact distance, for each of 80,000 features to say 13 counts; it now counts, and makes the items of a kind only when you choose it. It also loaded 12,000 pack tiles to test shapes at the edge of the view; the edge is now decided by bounding boxes, and each candidate is still checked against the stored relationships. Of the 5.7 seconds, 3.4 is reading the relationship records for the first time in a session, which DP194's stored contents will remove.
* Many distances at once are now worked out together, on the ellipsoid as before: 20,000 in a fifth of a second, against about 4 seconds one by one. They agree with the exact method to under a tenth of a millimetre.
* Finding a feature by its identifier searched its record group one record at a time; it now looks it up.
* Alt+Comma back to Europe said nothing because the Contains group was still open from section 6. The words were sent to NVDA, but the window then refilled Contains for the whole of Europe on the same thread, and froze. Contains for Europe now takes 2.6 seconds, still too long to freeze the window. The next step is to fill Contains away from the window's thread, as Crossed and passed is, so speech is never held up.
* Not yet measured: drawing at 1,000 kilometres, and the first panel after start-up, which takes 7 seconds on the world pack to read every feature's record once.

## 3. Discussion points

Your other notes are about how TobyMap should behave, where there is a choice. They are grouped into nine discussion points, each with options and my recommendation:

* DP198: which areas "where am I" says, and in what order (1.7, 3.5).
* DP199: whether a distant part says its country, such as Spain for Tenerife (3.1 to 3.3).
* DP200: lakes and the areas round them (6.4).
* DP201: borders as a share of the whole border, and where a line crosses an area (6.3, 6.5).
* DP202: making a larger area the current feature without moving (7.1).
* DP203: markers, measuring and bookmarks (section 8).
* DP204: what hierarchy mode's Down lists count, such as Europe's 17 islands and Kazakhstan (9.6, 9.11).
* DP205: the disputed and unclaimed lists in the world tree, and odd areas such as the Moselle condominium (11.4, 11.5, 13.2).
* DP206: what Nearby and look around list, such as the area you are in, England, and a sea and its ocean together (14.4).

Data changes chosen in these go into the builds, task P3-T21.

### Map views and the drawing order, task P3-T23

From your decisions on DP198, 17 November 2026. The definition is "How TobyMap draws the map" in docs/design/Discussion points detail - responses.md: the political and physical map views and the view manager, the drawing order in the views file read at start-up (which fixes the hidden lakes), an outline setting for each layer, areas said in the view's order, the most detailed layer shown in colours with thicker country borders, the current feature's tint, island names on the map, and an island with the same name and land as an area said once. Only the last needs the builds, task P3-T21.

### Distant parts, lakes, borders, the current layer, enclaves, task P3-T24

From your decisions on DP199 to DP202 and DP207, 17 November 2026. The definitions are the sections of the same name in docs/design/Discussion points detail - responses.md.

* P3-T24a The drawing never holds up speech (DP202). In the web version, the answer to a key is sent before the map is drawn; then, in both versions, the map is drawn in steps, with a limit on its shapes and "Still drawing the map" after 2 seconds. A test with every layer at every zoom on the world pack, in both versions, where no answer waits more than 100 milliseconds for a drawing. Done first.
* P3-T24b The current layer, set with Shift+Enter (DP202). "Current layer" is in the glossary.
* P3-T24c The territories list, a YAML file in the build settings, about 70 entries, made from Natural Earth and Wikidata and checked online, with the grey cases marked for you (DP199).
* P3-T24d The sovereign state said after an integral part, and the status in Details (DP199). A dependent territory mapped inside its country, such as Puerto Rico, becomes an area of its own in the builds.
* P3-T24e Shores and Coast in Bordering, and Overlapping with headings by kind (DP200). The lengths are stored in the builds.
* P3-T24f The share of the border, the whole border in Details, the ends of a shared border, and the crossing points (DP201).
* P3-T24g Enclaves and exclaves, found in the builds, said by "where am I" and listed in Details (DP207).

## 4. The builds, task P3-T21

* P3-T21a Western Europe trial build, with DP194's stored contents, the layer sounds, Ceuta and Melilla, and the data changes you choose. Checks and timings on it. It also tries the code fixes on fresh data.
* P3-T21b World build. As for the last ones, I'll tell you before the laptop gets sluggish.

## 5. Testing again, task P3-T22

* P3-T22a A short second desktop checklist: only the steps that changed, plus section 20, layer sounds.
* P3-T22b The web and sighted checklists, brought up to date with the changes.

## 6. Answers and mistakes in the checklist

### Answers to your questions

* How loud an earcon and the spoken label are (7.1). Both get quieter with distance, measured against the zoom: at your position, full volume; at the zoom distance, the minimum volume; in between, a straight line from one to the other (DP137). Beyond the zoom distance they stay at the minimum volume and are muffled. Your earcon and voice volume settings then scale them. So zooming in makes far things quieter.
* Why zooming in moved you into Lungern (7.1). The current feature is the smallest area shown where you are. Municipalities are shown only at closer zooms, so at 50 kilometres Lungern appeared and became the current feature. P3-T19a and DP202 are about choosing a larger one.
* Where Enter in hierarchy mode takes you (9.5). To the feature's own point, a place inside it chosen by the build, which is not always its centre, at a zoom that fits the whole feature in view. Europe's own point is in Russia, in the Central Russian Upland, which is why 9.7 said that.
* Is Kazakhstan in Europe (9.6)? Partly. Its land west of the Ural River is in Europe by the usual dividing line, like part of Russia and of Turkey. DP204 suggests saying "partly".
* Does search use fuzzy matching (10.3)? Yes. Besides exact and starting matches, a name is a close match when enough of its groups of three letters are the same. "londn" shares most of its groups with "london". This is how "Pariss" finds Paris.
* Why Bir Tawil is in the disputed section (5.4). Section 5 covers disputed and unclaimed land together, as both come from the same work (P3-T2c). Bir Tawil is the best known unclaimed land.
* Lake Lucerne overlapping Obwalden (6.4). It is not a data fault. Swiss cantons own their part of each lake, and the borders between them run across the water. So the lake really does overlap each canton round it. DP200 is about how to say it.
* Typing letters in the panel (7.2). Moving past the current group is how a Windows tree normally behaves: it searches every item you can see from where you are. As you asked for standard behaviour, I'll leave it.
* The world tree and hierarchy mode (11.5). The world tree is political only: continents, countries, regions and counties. Hierarchy mode goes through every layer, so it also reaches islands, mountain ranges and lakes.

### Mistakes in the checklist

* 2.2: my mistake. The step list has 5 kilometres between 10 and 2.5, and the checklist missed it. TobyMap is right.
* 12.1: my mistake. Space always says where you are, starting with the smallest area, Obwalden. Switzerland was the current feature, but Space does not say the current feature first.
* 13.7: the checklist was unclear. The Rhine was meant to stay in the Search group, to be chosen under "Of" as "Rhine, from the Search group". It was not meant to become the current feature. Did the Of list offer it?
* 6.2 said focus goes to the Contains heading. That was the intended behaviour, and P3-T19c makes it so.
