# Phase 3 tidy-up plan

Written on 15 November 2026, from your first pass of the desktop checklist (docs/checklists/phase-3desktop-results.txt).

## Next steps, written 17 November 2026

P3-T23 and P3-T24 are done and committed. Your answers of 17 November: the choices listed in the progress section are fine, and these come next, in this order.

1. Rerun the enclaves rehearsal: the enclaves stage alone on the world's data on disk, the disputes stage's output, with the names setting from world.yaml, nothing written. Check that Ceuta is found once, that Llívia, Jungholz, Büsingen, Campione d'Italia, Point Roberts and Baarle are named, and that French Guiana, Saint Martin and Northern Ireland are not exclaves. It takes about 5 minutes and one process.
2. Write P3-T20c: store in the pack what is directly inside each area (DP194), so the world tree knows at once which items have nothing under them, and the first branches open quickly.
3. Write P3-T25, the build and the core: Down's lines say what is held directly and what is inside in all, and "partly in" for a feature only partly inside; and the list of Europe's 17 islands for you.
4. Write P3-T26, the build and the core: disputed areas grouped by dispute, unclaimed land under 1 square kilometre left out and the rest named by a place near it, and a condominium said with its owners.
5. Run tools/time_drawing_wait.py on the desktop with the world pack, with memory protected: nothing else heavy running, the free memory checked first and watched, and the tool now using one session. Then the same in the browsers, one browser at a time.
6. Tell you, then run the Western Europe trial build, P3-T21a, with a stall watch. It rebuilds most stages.

### Progress on 17 November 2026, the next steps 1 to 6

* Step 1 done: the enclaves rehearsal, on the world's data on disk with world.yaml's names, found 194 in about 6 minutes. Ceuta is found once, and so is Melilla. Llívia, Jungholz, Büsingen am Hochrhein, Campione d'Italia, Point Roberts and Baarle-Hertog and Baarle-Nassau are named. French Guiana, Saint Martin and Northern Ireland are not exclaves. Still unnamed: 5 German exclaves beside Belgium (the Vennbahn), 2 small Belgian ones beside the Netherlands outside the Baarle box, and a Spanish rock beside Morocco.
* Step 2 done in the code, with tests, not committed: P3-T20c. The writing stage stores the world tree and what each area of the tree's layers holds (records tree and holds/G, mapcore/store/contents.py, docs/developer/pack-format.md). On the world pack's own records, this adds 7.0 MB and takes 5 seconds. The world tree marks items with nothing under them, so they are not said as "collapsed", in both versions.
* Step 3 done in the code, with tests, not committed: P3-T25a and b. A finding: Down from Europe does not list the islands no country holds. It lists those big enough to show at the zoom that fits Europe, the size rule of DP188: 11 on the world pack, among them Great Britain, Iceland, Ireland, Sicily, Sardinia, Crete and Cyprus. What DP204 said was wrong. So the line now says "Islands: 11 shown at this zoom, 109,292 in all", and a new discussion point is owed to the PO on whether "directly in" is wanted instead. Also found: an unnamed island of 21,324 square kilometres in Greece, most likely the Peloponnese, cut off by the Corinth Canal. "Partly in" is said in Down, Contains and Browse by category.
* Step 4 done in the code, with tests, not committed: P3-T26.
  * P3-T26a: Disputed areas in the world tree has one item for each dispute, by Natural Earth's name, with its claimants or Natural Earth's note and how many areas it holds, such as "Crimea, claimed by Russia, Ukraine", then the number of areas. It opens to the areas. A dispute of one area, such as the West Bank, is that area. An area with no name from Natural Earth takes its dispute from the area above it, else its own name. On the world pack, 865 areas become 24 disputes and 16 areas of their own. The grouping is stored with the world tree, so the build makes it. Browse by category and the search word "disputed" list one item for each dispute, which goes to its largest area there.
  * P3-T26b: the enclaves stage tidies unclaimed land first, as it has the towns (mapdata/stages/unclaimed.py). Rehearsed on the world's data on disk: 26 left out, 6 kept. The kept ones are Bir Tawil, and 5 named "Unclaimed land near" a place, such as Tantéga and Grande Glorieuse. Doumera Island is kept though small, as it is in a Natural Earth dispute. A finding for you: most of the 26 left out are not slivers between borders but small islets in no country in OpenStreetMap, among the Spratly Islands, the Senkaku Islands and in the Caspian Sea.
  * P3-T26c: a condominium is said with its owners wherever its name is said, "Moselle condominium, shared by Germany and Luxembourg".
  * DP208 is new in the discussion points file: the correction to DP204.
* Step 5 done: tools/time_drawing_wait.py on the world pack, with memory checked first and watched (16 to 18 GB free throughout).
  * A fault in the tool, fixed: it drew the whole map at each place before the move it timed, so the timed drawing found its pack tiles already read. It now reads the map once, at start-up.
  * Desktop: no answer waited for the drawing; the longest wait was 0 ms. Drawings took 41 to 285 ms.
  * Chromium and Firefox: the drawing keeps the rule. Its steps take about 25 ms each, and the page paints a finished map in about 5 ms. But answers waited up to 2.4 seconds in Chromium and 1.5 seconds in Firefox at zooms of 1,000 km and more. Two other pieces of work in the worker cause this, not the drawing. After every move, the Information panel's Nearby list is worked out again, even with the panel closed: up to 0.43 seconds in Python at 2,500 km with the default layers, about 1.3 seconds in the browser. And the Crossed and passed search after a move runs in one piece, about 0.6 seconds in the browser, so a key pressed then waits. The desktop timing tool never refilled the panel, so it did not see this. On the desktop the same refill holds the next key for up to about 0.4 seconds.
  * Done so far: Nearby measures a part only when its box could hold a nearer point than the best found. That cuts the parts put into the flat view by about four fifths, with the same answers in 40 of 40 cases checked on the world pack. What is left is reading pack tiles: about 600 for each refill at 2,500 km, as an area within 50 km is searched at every tile level of exact shapes.
  * Proposed, task P3-T20d: send a move's answer before the panel is refilled, in the web version as the drawing now is, and on the desktop off the window's thread; refill the panel and run Crossed and passed in steps, so a key waits for no more than one step; and read fewer pack tiles for Nearby. Not started: it is for you to agree.
* Step 6 done: the Western Europe trial, P3-T21a, built in 23 minutes with 3 workers, from the places stage on. The first three stages were kept, as nothing they use had changed. The pack is 54.6 MB, up from 51.3, and 60 of 60 check places pass. The trial has no distant-parts stage, so Ceuta and Melilla wait for the world build. On the trial pack:
  * W opens the world tree in 9 ms, against 5 seconds on the world pack before; Switzerland's branch opens in 37 ms.
  * Items with nothing under them, such as Gibraltar and Vatican City, are marked as not branches.
  * Browse by category lists Switzerland's 17 lakes in 19 ms, with "Lake Geneva, partly in Switzerland" and three more said as partly in.
  * The Moselle condominium is said as "Moselle condominium, shared by Germany and Luxembourg", among Germany's neighbours too.
  * 27 enclaves and exclaves; 1 area of unclaimed land under 1 square kilometre left out.
  * Still unnamed: Germany's 5 Vennbahn exclaves are each "Exclave of Germany". They can be named by hand in the settings, as Llívia is.
* Tests: 1,822 Python tests pass. One fails on this laptop only: the visible rule's speed on the world pack, 10.6 milliseconds against a limit of 10. It fails on the committed code too, at 13.0, so the work above did not cause it.

## The plan

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

### Progress on 17 November 2026, P3-T23 and P3-T24

All done in the code, with tests in both versions. What needs the builds is noted.

P3-T24a, the drawing never holds up speech:

* In the web version a key's answer is sent at once, and the page then asks for the drawing, a step at a time, only when the worker has nothing else to do. On the desktop the drawing thread works in the same steps, and drops a drawing no longer needed. A drawing half a second old is finished first, so a held key still moves the map.
* The steps and the "Still drawing the map" words are in the core (mapcore/render/drawing.py), so both versions behave the same.
* The drawing limit is 15,000 features. With every layer at every zoom on the world pack, one drawing took up to 17 seconds; now 3 to 5. Most of that time was decoding every road and town from the exact pack tiles.
* A finding: Python's memory clean-up looked at every feature record the store holds, about 4 million objects, and paused everything for about a second, keys included, in both versions. The store now sets what it keeps aside from that clean-up (mapcore/memory.py), and the pauses are gone.
* tools/time_drawing_wait.py measures rule 5, the 100 milliseconds, on the world pack in both versions. Measured by hand on the desktop, most steps take under 60 milliseconds. The tool's first run was stopped as the laptop ran short of memory: it opened a new session for each place, and each kept its records. It now uses one session, as TobyMap does; it has not been run again.

P3-T23, map views:

* The views file, mapcore/views.yaml, with the drawing order and the political and physical views. The view manager is Map views in the Map menu, Ctrl+Shift+V: choose a view, save the layers as a view, rename or delete one of your own. It is a list with Cancel, and the name is typed in a box with OK and Cancel.
* The outlines are drawn over everything painted, the country borders thicker; rivers go under them, roads over. Each layer's settings have "Draw the outlines of its areas". "Draw the borders of regions" is gone: the regions are painted in colours over their countries.
* In the physical view the countries are painted one plain land colour, not left empty, as the globe behind them is the sea's colour; their borders are outlines.
* The continents are said but not outlined, as their lines across the land, such as the Urals, are not a map's. This is one line in the views file if you would rather see them.
* An island and an area with the same name and nearly the same land are said once: the build marks them as the same land when each is at least 90 percent inside the other (same_name_share), so the island of Ireland is not the country.
* A difference to look at: the definition says Tenerife as "Santa Cruz de Tenerife, Tenerife, Canary Islands, Spain, Africa", but the political view's order puts islands after countries, so it will say "Santa Cruz de Tenerife, Canary Islands, Spain, Tenerife, Africa".

P3-T24b, the current layer: Shift+Enter in the Information panel, as defined.

P3-T24c and P3-T24d, the territories list: mapdata/config/territories.yaml, 59 entries, checked against Natural Earth and Wikidata on 17 November 2026, with 11 grey cases marked for you, each with a note. The distant-parts stage checks it when it starts, makes Puerto Rico and the United States Virgin Islands areas of their own, and gives each area its status. The core says the sovereign state after an integral part, and Details gives the status and any claim, such as "Claimed by Argentina."

P3-T24e and P3-T24f, borders: Shores and Coast in Bordering, Overlapping by kind, each neighbour's share of the whole border, the whole border in Details, and each neighbour opening to the ends of the shared border, worked out when it is opened. Lines crossing a border say how many times, and open to each crossing. Working the crossings out when the group is filled took 14 seconds for Spain on the world pack, so the build stores them, as the definition allowed. The coast, shores, whole outlines and crossings come with the builds.

P3-T24g, enclaves and exclaves: a new stage, enclaves, after the towns. Rehearsed on the world's data on disk: about 190 found in 4 to 5 minutes, among them Llivia, Alaska, Cabinda, Nakhchivan, Musandam, Point Roberts, Ceuta and Melilla, the Vennbahn and Baarle enclaves, and Lesotho as a whole country. Also many small river islands of Argentina and North Korea inside their neighbours' waters, which are real but many. A part the sea cuts off, such as Northern Ireland, is not an exclave. Villages are not in the Cities and towns layer, so a few are named by hand in the build settings, such as Llivia and Jungholz.

### What hierarchy mode's Down lists count, task P3-T25

From your answer to DP204, 17 November 2026: accept the recommendation.

* P3-T25a Each line of the Down list says what it counts: what the area holds directly, and everything inside it, such as "Islands: 17 directly in Europe, 109,292 in all". Choosing the line lists the ones held directly; the rest are reached through the areas that hold them, such as the countries. The total comes from the stored relationships, as Browse by category's counts do, so it needs no new build.
* P3-T25b A feature only partly inside says so, in the Down list, in Contains and in Browse by category: "Kazakhstan, partly in Europe".
* P3-T25c A list for you of the 17 islands held directly by Europe, from the world pack, with why no country holds each, to check they make sense. Any that are faults go into the builds, task P3-T21.

### Disputed, unclaimed and odd areas, task P3-T26

From your answer to DP205, 17 November 2026: accept the recommendation.

* P3-T26a Disputed areas in the world tree, and in Browse by category, lists one item for each dispute, by Natural Earth's name, such as Kashmir, with its claimants. The areas in that dispute are under it. The build stores which dispute each disputed area belongs to.
* P3-T26b Unclaimed areas leaves out anything under 1 square kilometre, and names the rest by the nearest named place or island and its coordinates: "Unclaimed land near X, 12.3 N, 45.6 E". The build report counts what was left out.
* P3-T26c A condominium stays in the Countries layer, and is said with its owners wherever its name is said: "Moselle condominium, shared by Germany and Luxembourg".
* The build parts of a and b go into the builds, task P3-T21. Part c needs no new build.

### Bookmarks and measuring, written before Phase 4, task P3-T27

From your answer to DP203, 17 November 2026: accept the recommendation.

* Markers and bookmarks become one thing in Phase 4, "bookmarks", kept in groups you name. A bookmark can be a feature or a position. Any two can be measured, distance and bearing, and a chain of them gives its total length.
* Shift+M stays as it is: it measures to a search result without going there, which nothing else does.
* P3-T27 is writing the requirements, INF-3 and USR-1 to USR-4, for you to approve before Phase 4 starts. Phase 4 builds them, as P4-T8 and P4-T9.

### What Nearby and look around list, DP206, parked

You parked DP206 on 17 November 2026, to come back to later, so it has no task yet. Its fourth part, the direction in look around, is already done as P3-T19f. The double "Isle of Wight" is also covered by P3-T23, which says an island and an area with the same name and land once.

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
