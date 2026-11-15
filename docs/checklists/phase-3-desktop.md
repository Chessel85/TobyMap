# Phase 3 checklist: desktop version

This is the Phase 3 desktop checklist, for you to work through with NVDA on Windows 11. It covers what is new in Phase 3: the complete world pack, facts and Details, the new Information panel groups, hierarchy mode, measuring, search, the world tree, browsing, the query builder, look around and names. What you checked in Phase 2 is not repeated.

The web version has its own checklist, docs/checklists/phase-3-web.md. The parts that need sight are in docs/checklists/phase-3-sighted.md, for a sighted helper if you have one.

For each step, write down its number, such as 4.3, and either "works" or what you heard instead. Put your notes in a text file, as before.

The expected words below were taken from the core running on the world pack of 14 November. They assume tonight's world build, which only writes the pack again, so the words should not change. The one thing tonight's build adds is the layer sounds. Section 20 tests them, and it is for tomorrow.

## How to start TobyMap

Your packs folder still has the older world pack from 8 November, so these steps run TobyMap from the repository, with the new world pack.

* Open a terminal in the repository folder, as you do for the web version, and run:

  `.venv\Scripts\python.exe -m desktop --pack E:\osmdata\tobymap\output\world\world.pack --at 51.2,1.2`

* "Start with 46.8,8.2" below means: close TobyMap, then run the same line with `--at 46.8,8.2` at the end. Up Arrow in the terminal brings back the last line to change.
* TobyMap keeps your last zoom and step. Page Up and Page Down change the zoom, and Shift+Page Up and Shift+Page Down change the step. Each section gives the zoom it needs, because what is said depends on it. For example, counties are said only at a zoom of 100 kilometres or closer.

## Before you start

* In Settings, Units, set Distances to Metric and Directions to Compass with 8 points. The words below assume both.
* Make sure the verbosity preset is Normal and the orientation is north-fixed. Pressing H says both, and also says "Stepping." If it says "Hierarchy mode.", press M.
* In Settings, Speech, set Names to "English where there is one".

## Things I already know about

You don't need to report these. They are listed so they don't surprise you. Tell me if one bothers you more than I expect.

* The Isle of Wight is said twice, "Isle of Wight, Isle of Wight", because the county and the island have the same name and are not quite the same land. On Oahu you hear both "Oʻahu" and "Oahu", for the same reason.
* The order of the countries the Rhine crosses is wrong: Liechtenstein, Austria, Germany, Switzerland, France, Netherlands. A river with branches joins its parts out of order. This was found in P3-T8b.
* Some search results are in an odd order. For example, "nile" gives the Nile Delta and three towns called Niles before the Nile River, and "everest" gives Everest South Peak before Mount Everest.
* The first time a branch of the world tree opens, and each time you list every feature of a kind, there is a wait of 3 to 6 seconds. DP194 stores what is directly inside each area to make this fast. You said yes to it, but it isn't built yet, so tonight's build doesn't include it.
* Hampshire has no Wikipedia article in the pack, so W in Details says "No Wikipedia article for Hampshire." Most other features have one. I'll look at why.
* Hawaii's Details ends "Source: part" instead of naming the source. I'll fix it.
* In Cayenne at a wide zoom, Details is about the region French Guiana and says "Type: region of French Guiana". Go up to the country-level French Guiana in hierarchy mode, or search for it, and Details says "Type: overseas region of France", as DP191 intended.

## 1. Where you are, with the new layers (P3-T1, LOC-1, DAT-5)

Zoom and step 25 kilometres for the whole section.

* 1.1 Start with 51.2,1.2. You hear "TobyMap. Kent, Great Britain, England, British Isles, United Kingdom, Europe. Press F1 for keys." Counties, islands, physical regions and continents are all new.
* 1.2 Start with 51.06,-1.31, in Winchester. Space says "Hampshire, Great Britain, England, British Isles, United Kingdom, Europe".
* 1.3 Start with 46.45,6.55, on Lake Geneva. You hear "Lake Geneva, Upper Savoy, Auvergne-Rhône-Alpes, France, Europe". The lake comes first.
* 1.4 Start with 46.0,7.75, near Zermatt. You hear the mountain ranges inside one another: "Visp, Valais/Wallis, Pennine Alps, Northwestern Alps, Western Alps, Alps, Switzerland, Europe".
* 1.5 Start with 45.5,-4.0. You hear "Bay of Biscay, North Atlantic Ocean": a sea inside an ocean.
* 1.6 Start with 23.0,10.0, in the Sahara. You hear "Tazrouk District, Tamanrasset, Ténéré, Sahara, Algeria, Africa".
* 1.7 Is the order of the areas easy to follow? On the Isle of Great Britain you hear the island before England, and the British Isles before the United Kingdom. Tell me if you'd like another order.

## 2. The new step sizes (P3-T0f, DP166)

* 2.1 Start with 51.2,1.2, step 25 kilometres. Press Shift+Page Up four times. You hear "Step 50 kilometres.", "Step 100 kilometres.", "Step 250 kilometres." and "Step 500 kilometres."
* 2.2 Press Shift+Page Down until you hear "Step 10 kilometres.", then once more for "Step 2.5 kilometres."
* 2.3 Set the step back to 25 kilometres.

## 3. Countries' distant parts (DP191, DP192)

* 3.1 Start with 4.93,-52.33, in Cayenne, zoom 1,000 kilometres. You hear "French Guiana, South America". France is not said.
* 3.2 Start with 28.3,-16.5, on Tenerife, zoom 25 kilometres. You hear "Santa Cruz de Tenerife, Tenerife, Canary Islands, Teide, Africa". Spain is not said.
* 3.3 Start with 21.3,-157.85, in Honolulu, zoom 25 kilometres. You hear "Honolulu County, Oʻahu, Hawaii, Oahu, Hawaiian Islands, Polynesia, Oceania".
* 3.4 Start with -22.27,166.45, in Nouméa, zoom 25 kilometres. You hear "South Province, Grande Terre, New Caledonia, Melanesia, Oceania".
* 3.5 Press Ctrl+F, type French Guiana, choose "Only Countries" under "Search in", press Down to the result and Enter. You hear "French Guiana, South America. Zoom 250 kilometres." Press F4 for Details. It says "Type: overseas region of France".

## 4. Details, facts and Wikipedia (P3-T2, P3-T5, P3-T17, INF-1)

* 4.1 Start with 48.14,11.58, in Munich, zoom 25 kilometres. Space says "Munich, Bavaria, Germany, Europe".
* 4.2 Press F4 for Details. Read it a line at a time:
  * Munich
  * Type: urban municipality of Bavaria
  * Part of: Bavaria
  * Area: 310 square kilometres
  * Population: 1,505,036, from Wikidata, 31 December 2025
  * Area, as published: 310 square kilometres, from Wikidata, 31 December 2017
  * Elevation: 519 metres, from Wikidata, as fetched on 13 November 2026
  * Official name: München, from Wikidata, as fetched on 13 November 2026
  * Wikipedia article: Munich
  * Source: OpenStreetMap planet file, as a GeoDesk library, ODbL 1.0
* 4.3 In Details, press W. You hear "Opening the Wikipedia article for Munich." and the article opens in your browser. Come back to TobyMap with Alt+Tab.
* 4.4 Start with 51.06,-1.31, zoom 25 kilometres. In Details: "Type: county of England" and "Part of: England". Press W. You hear "No Wikipedia article for Hampshire.", which is the gap noted above.
* 4.5 Start with 46.8,8.2, zoom 1,000 kilometres. Details is about Obwalden: "Type: canton of Switzerland", with its population, capital, Sarnen, and official name, Kanton Obwalden.
* 4.6 Are the facts useful, and is the order right? Is "from Wikidata, as fetched on 13 November 2026" too long when it is on most lines?

## 5. Disputed and unclaimed land (P3-T2c, DP119, DP182)

Zoom 25 kilometres.

* 5.1 Start with 45.0,34.1, in Crimea. You hear "Simferopol (urban okrug), Autonomous Republic of Crimea, Crimean Peninsula, Crimea, disputed, Europe".
* 5.2 Details says, after "Part of", "This land is disputed." and "Natural Earth, for Crimea: Administered by Russia. Claimed by Ukraine."
* 5.3 Start with 45.8326,6.8652, at Mont Blanc. You hear "Courmayeur, Aosta Valley, Graian Alps, Northwestern Alps, Western Alps, Alps, Land claimed by France and Italy, disputed, Europe".
* 5.4 Start with 21.87,33.75, in Bir Tawil. You hear "Nubian Desert, Sahara, Bir Tawil, Africa".

## 6. The Information panel's new groups (P3-T4, INF-10, LOC-4)

Start with 46.8,8.2, zoom 1,000 kilometres, step 100 kilometres. You are in Obwalden, the current feature.

* 6.1 Press F3 and move down the groups. After Within, Nearby and Crossed and passed, there are five new groups: "Contains Obwalden", "Bordering Obwalden", "Overlapping Obwalden", "Crossing Obwalden" and "Search". Until you open them they have no count, and NVDA says "collapsed".
* 6.2 Press Shift+4. Focus goes to Contains, and it fills: "Contains Obwalden, 6 items". Under it are headings with counts, each with items under it: "Peaks 119", "Counties 1" (Kerns), "Rivers 1" (Kleine Emme), "Motorways and trunk roads 1" (A8), "Cities and towns 1" (Sarnen) and "Lakes 1" (Lake Lucerne). NVDA says level 3 for the items under a heading.
* 6.3 Press Shift+5 for Bordering: "Bordering Obwalden, 4 items". The first is "Nidwalden, north-east, shared border 69 kilometres".
* 6.4 Press Shift+6 for Overlapping, 3 items, such as "Swiss Prealps, north, 90 percent of Obwalden and 7 percent of Swiss Prealps overlap". DP186 asks about this wording. Is it clear?
* 6.5 Press Shift+7 for Crossing, 2 items: "A8, south-west, crosses it" and "Kleine Emme, north-west, crosses it".
* 6.6 Press Shift+8 for Search. It is empty until you search, browse or ask a query.
* 6.7 On any item of the new groups, Space plays its direction and says its name and distance, as in Nearby. Enter goes there.
* 6.8 Press F1 on the map. The list of keys has "Go to Contains: Shift+4" and so on to "Go to Search: Shift+8".

## 7. Sorting and moving in the panel (P3-T4d, P3-T4e)

Same place.

* 7.1 Press Shift+5 for Bordering, then Ctrl+S. You hear "Sorted by name", and the items are by name: Bern, Lucerne, Nidwalden, Uri. Ctrl+S again: "Sorted by distance". Again: "Sorted by direction". Ctrl+Shift+S goes back the other way.
* 7.2 In Contains, open "Peaks 119" and type the first letters of a peak quickly, such as "ar". Does it reach Arnifirst, under the heading? This hasn't been tried with NVDA. Type-ahead in the desktop's tree may only search the items at the same level.
* 7.3 On an item, press Ctrl+Enter. You hear "Bookmarks come in Phase 4."

## 8. Measuring (P3-T7, INF-3, DP187)

Same place, in Obwalden.

* 8.1 On the map, press Shift+M. You hear "Obwalden, its border 3.4 kilometres south". Inside an area, it measures to its border. You don't move.
* 8.2 Press Shift+2 for Nearby, move to Lake Lucerne, and press Shift+M. You hear the distance and direction to the nearest point of the lake.
* 8.3 In Settings, Units, set "Measure to" to "The centre of the feature", and press Shift+M again on Lake Lucerne. You hear "Lake Lucerne, centre", then its distance and direction. Set it back to "The nearest point of the feature".

## 9. Hierarchy mode (P3-T6, NAV-4, NAV-11, DP190)

Start with 51.06,-1.31, zoom and step 25 kilometres.

* 9.1 Press M. You hear "Hierarchy mode. Hampshire." H now says "Hierarchy mode." The Map menu's Hierarchy mode item has a tick.
* 9.2 Press Up. You hear the ambiguous up sound, and a list opens, "Up from Hampshire", with "England, constituent country of the United Kingdom" and "Great Britain, island". Is the sound heard before NVDA reads the list?
* 9.3 Press Enter on England. You hear "England. Zoom 500 kilometres." The map has jumped to England's own point.
* 9.4 Press Up. The list "Up from England" has "United Kingdom, country" and "British Isles, physical region". Press Cancel: you stay on England. Press Up again and choose United Kingdom. You hear "United Kingdom. Zoom 1,000 kilometres."
* 9.5 Press Up. You hear "Europe. Zoom 10,000 kilometres." Press Up again: the blocked sound and "Nothing holds Europe."
* 9.6 Press Down. A list opens, "Inside Europe", with "Countries 41" first, then the other kinds with their counts. Choose Countries. A second list opens, "Countries in Europe": "Albania, south-west", "Austria, west", and so on. Choose Austria. You hear "Austria. Zoom 500 kilometres."
* 9.7 Press Alt+Comma. You hear the place at Europe's own point, "Central Russian Upland, Russia, Europe", and Europe is the current feature again.
* 9.8 Press Right. You hear "Asia, east, shared border 4,160 kilometres. Zoom 10,000 kilometres." Right again: "Africa, south, shared border 17 kilometres. Zoom 10,000 kilometres." Left goes back to Asia. Left and Right go round Europe's neighbours, clockwise.
* 9.9 Hold Up for a second. Nothing repeats.
* 9.10 Press M. You hear "Stepping mode." The arrows step again.
* 9.11 DP190 asks how a move is said: the feature, then the zoom, such as "England. Zoom 500 kilometres."; and for a neighbour, its direction and shared border first. Tell me what you'd change.

## 10. Search (P3-T8, SRB-1, SRB-2, INF-8)

Start with 51.06,-1.31, zoom 100 kilometres, step 10 kilometres.

* 10.1 Press Ctrl+F. The Search window opens, with "Search for", a "Search in" choice, Results, Go and Cancel. A line says "Type a name. The results appear below; press Down to reach them and Enter to go there."
* 10.2 Type paris. After a moment, press Down. The first result is "Paris, Ile-de-France, France, territorial collectivity of Ile-de-France", then "Paris, Texas, United States, city or town", then Paris in Kentucky, Illinois and Tennessee.
* 10.3 Clear the field and type londn, with the letter missing. The first result is "London, England, United Kingdom, city or town".
* 10.4 Type muenchen. The first result is "Munich, Bavaria, Germany, urban municipality of Bavaria, found as München".
* 10.5 Type sao paulo. The first two results are "São Paulo, Brazil, region of Brazil" and "São Paulo, Greater São Paulo, Brazil, city or town". Press Down to the first and Enter. The window closes and you hear "São Paulo, Brazil. Zoom 1,000 kilometres."
* 10.6 Press Alt+Comma. You are back in Hampshire.
* 10.7 Press Shift+8. The Search group has the last results. On São Paulo, press Shift+M. You hear "São Paulo, nearest point 9,070 kilometres south-west". You don't move.
* 10.8 Press Ctrl+F. Under "Search in", the choices are Everywhere, "Inside Hampshire", "Near here, within 100 kilometres", then "Only" each layer, such as "Only Lakes". Choose "Near here, within 100 kilometres" and type winchester: one result, "Winchester, England, United Kingdom, city or town".
* 10.9 Choose "Inside Hampshire" and type itchen: "River Itchen, United Kingdom, river".
* 10.10 Choose "Only Lakes" and type lake. The first is "Lake Baikal, Russia, lake".
* 10.11 Type qqzzxx. You hear "Nothing found for qqzzxx." Press Cancel. You haven't moved.
* 10.12 Do results come quickly enough as you type? SRB-1 asks for under a second. On the desktop each search took under a tenth of a second on the world pack.

## 11. The world tree (P3-T9a, P3-T16)

Start with 51.06,-1.31.

* 11.1 Press W on the map. The World tree opens, with a line saying "Use the arrow keys to move round the tree: Right opens an item and Left closes it. Enter goes to the item." You are on World, at level 1. Under it are the seven continents, each said as "Africa, continent" and so on, then "Disputed areas" and "Unclaimed areas".
* 11.2 Move to "Europe, continent" and press Right. The first time there is a wait of about 5 seconds. Then Europe's countries are listed by name: "Akrotiri and Dhekelia, country", "Albania, country", and so on. Crimea is there as "Crimea, disputed land".
* 11.3 Open the United Kingdom. Under it are "England, constituent country of the United Kingdom", then Northern Ireland, Scotland and Wales. Open England: its counties, by name, from "Barnsley, county of England". Press Enter on Barnsley. The tree closes and you hear "Barnsley. Zoom 25 kilometres."
* 11.4 Press W, open "Disputed areas". Items say who claims them, such as "Abyei, disputed land, claimed by South Sudan, Sudan", or Natural Earth's note, such as "Aalo HQ, county of Arunachal Pradesh, Administered by India. Claimed by China." Some areas are listed twice, such as Abkhazia, once as a region and once as its own county. Tell me if that's confusing.
* 11.5 Open "Unclaimed areas". The first is "Bir Tawil, unclaimed land, no claimant". Many after it are small islands said only as "Unclaimed, unclaimed land, no claimant". Are those worth listing?
* 11.6 Close the tree with its Cancel button.

## 12. Listing every feature of a kind (P3-T9b, SRB-4)

Start with 46.8,8.2, zoom 1,000 kilometres.

* 12.1 Press M, then Up. The list "Up from Obwalden" has "Northwestern Alps, mountain range" and "Switzerland, country". Choose Switzerland. You hear "Switzerland. Zoom 250 kilometres." Press M to go back to stepping. Switzerland stays the current feature until you move.
* 12.2 Press Ctrl+Shift+F. The list "Inside Switzerland" has each kind with its count, such as "Peaks 4749", "Counties 359", "Lakes 13".
* 12.3 Choose Lakes. After a few seconds you hear "Lakes: 17 inside Switzerland, in the Search group." The list said 13: the count before counts only lakes fully inside, and the 17 include lakes partly inside, such as Lake Geneva. I'll make the two agree.
* 12.4 Press Shift+8. "Search, 17 items": Lago di Lugano, Lake Bienne, Lake Brienz, Lake Constance, Lake Geneva, and so on.

## 13. The query builder (P3-T10, INF-9)

Switzerland is still the current feature from section 12. If you have moved, do 12.1 again.

* 13.1 Press Q. The Query window opens, with a line saying "Choose what to find, how it relates, and the feature, then OK. The answer goes into the Search group." There are three lists, Find, Relation and Of, then OK and Cancel.
* 13.2 Choose Lakes, inside, and "Switzerland, the current feature". Press OK. You hear "Lakes inside Switzerland: 17, in the Search group."
* 13.3 Press Q. Choose Rivers, crossing, Switzerland. You hear "Rivers crossing Switzerland: 25, in the Search group."
* 13.4 Press Q. Choose Countries, bordering, Switzerland. You hear "Countries bordering Switzerland: 5, in the Search group."
* 13.5 Press Q. Choose "Cities and towns", "within a distance of", and Switzerland. A distance field appears, "Distance in kilometres". Type abc and press OK. The window stays open and says "Type a distance greater than 0, such as 10." Type 10 and press OK. You hear "Cities and towns within 10 kilometres of Switzerland: 234, in the Search group."
* 13.6 Press Shift+8. The heading is "Cities and towns within 10 kilometres of Switzerland, 234 items".
* 13.7 Search for Rhine, with "Only Rivers", but press Cancel rather than Enter, so the Rhine stays in the Search group. Press Q, choose Countries, crossing, and under Of, "Rhine, Germany, Netherlands, Switzerland, from the Search group". You hear "Countries crossed by Rhine: 6, in the Search group." The order is the known fault listed above.

## 14. Look around (P3-T11a, SON-4)

Start with 51.06,-1.31, zoom 100 kilometres. Use headphones. Tonight every item has the same direction sound. Each layer gets its own sound tomorrow, in section 20.

* 14.1 Press L. Each of the 8 Nearby items plays in turn, clockwise from north: its sound from its direction, then its name and distance in the Alba voice from the same place, then a short pause. The first is "A34, 1.7 kilometres", ahead and to the right, then River Itchen, 170 metres, to the right.
* 14.2 Each label is on your Braille display as it starts. Shift+Space repeats it.
* 14.3 Press L again, and press any other key part-way, such as H. Look around stops at once.
* 14.4 Press L, and press Enter while an item plays. You go there, and its place is said. Alt+Comma comes back.
* 14.5 Let look around play to the end, then press Enter. You hear the blocked sound and "Nothing to go to. Press Enter while look around plays an item to go to it."
* 14.6 Press Ctrl+M to mute, then L. You hear "Sound is muted, so look around has nothing to play." Press Ctrl+M again.
* 14.7 How does the pace feel? Is the pause between items right?

## 15. Names (P3-T12, ACC-9, DP172)

Start with 51.0,10.0, zoom 100 kilometres.

* 15.1 Space says "Werra-Meißner-Kreis, Hesse, Germany, Europe".
* 15.2 In Settings, Speech, set Names to "Always the local name", and press OK. Space says "Werra-Meißner-Kreis, Hessen, Deutschland, Europe". The Information panel and Details use the local names too.
* 15.3 On the desktop, NVDA reads Deutschland with your English voice: the desktop can't tell NVDA which language a name is in. That comes with P4-T10.
* 15.4 Set Names back to "English where there is one".

## 16. Saying the place after every step (P2-T17q, DP162)

Start with 48.85,2.35, zoom and step 25 kilometres.

* 16.1 Press Right. You hear "Seine-et-Marne". Press Right again: only the tick, as the place has not changed.
* 16.2 In Settings, Speech, switch on "Say the place after every step, even when it has not changed". The preset stays Normal. Press Right: you hear "Seine-et-Marne, France" in place of the tick.
* 16.3 Hold Right for two seconds. It still clicks, and only the place where you let go is said.
* 16.4 Switch the setting off again, or leave it on if you like it.

## 17. The layers list (SCP-6)

* 17.1 Press Ctrl+Shift+L. The groups are Boundaries, Water, Physical features, Transport, Places and Graticule. Boundaries has Continents, Countries, "Regions and constituent countries", Islands and Counties.
* 17.2 Switch off Counties and press OK. Start with 51.06,-1.31, zoom 25 kilometres. Space no longer says Hampshire. Switch Counties on again.
* 17.3 Are the group and layer names clear?

## 18. The status line and the buttons, for NVDA (P3-T18)

These are for sighted users. Check they don't get in your way.

* 18.1 Tab and Shift+Tab move between the map, the Information panel and Details, as before. They never land on the status line or the move and zoom buttons.
* 18.2 NVDA never reads the status line by itself as you step.

## 19. Overall

* 19.1 Tell me how Phase 3 feels as a whole: which features you'd use most, what is hard to find, and anything said that is unclear.

## 20. Layer sounds: tomorrow, after tonight's world build (P3-T11b, SON-3, SON-4, SCP-7)

Do this after the world build finishes. Until then the world pack has no layer sounds, and every layer uses the same direction sound.

* 20.1 Start with 51.06,-1.31, zoom 100 kilometres. Press Shift+2 for Nearby, and press Space on River Itchen, Winchester, M3 and South West Main Line. Each plays a different sound: river, town, road and railway. The sounds are placeholders, and you can choose your own.
* 20.2 Press L. Each item now plays its own layer's sound.
* 20.3 Open Settings, Earcons. The list has ten new layer sounds, from layer_continent to layer_peak. Each can be switched off, have its volume changed, or use your own file, like any earcon.
* 20.4 Press Ctrl+Shift+L, move to Rivers, and press "Settings for this layer". There is a list "Sound of this layer's features in look around and Hear its direction", with "No sound" first. Choose another sound and press OK, then OK. Space on River Itchen now plays the sound you chose. Set it back.
* 20.5 Can you tell the layers apart by sound? Which sounds would you change?

## Finishing

When you have been through it, send me your notes. If you accept the desktop version, and the web version passes its own checklist, I ask you about publishing (DP110). That completes Phase 3.
