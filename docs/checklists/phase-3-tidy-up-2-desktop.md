# Phase 3 tidy-up 2 checklist: desktop version, world pack

Brought up to date on 21 November 2026 for the Phase 4 changes (P4-T14m). Steps keep their numbers. Sets 10 and 18, which you did not test, move to the Phase 4 checklist. The steps that need the world pack built on 21 November 2026 are 2.2, 5.3, 5.6, 13.4, 13.5, 14.7, 16.4 and 22; on an older pack you hear the old words there. Steps 1.6 and 5.6 are rewritten, as your notes said they were poorly written. New steps are 6.8, 12.7, 12.8, 13.4, 13.5 and section 22.

This is a short third pass of the desktop checklist, for you to work through with NVDA on Windows 11. It covers only what changed in the second tidy-up plan (docs/plan/phase-3-tidy-up-plan2.md): the fixes and changes of P3-T28, the Information panel group by group as now defined (P3-T29), key maps (P3-T31), and the layer sounds, section 20 of the Phase 3 checklist.

It uses the world pack built on 20 November 2026. That pack has every change that needs a build, except the coast as a border (P3-T30b), which waits for your answers to the coast report.

For each step, write down its number, such as 4.3, and either "works" or what you heard instead. Put your notes in a text file next to this one, docs/checklists/phase-3-tidy-up-2-desktop-results.txt, as before. Lines starting with ">" are fine for answers to questions.

The expected words below are what TobyMap's core said on the world pack of 20 November, at the places given. Distances to things depend on exactly where you stand, so those are given as "such as". If the words differ only in a number, say so, but it is not a fault unless the number seems wrong.

The possible faults found on the world pack on 20 November were fixed on 20 November (P3-T32a to P3-T32g), and the steps they affected have been updated with what TobyMap now says on the same pack. No step is marked "Possible fault" any more. The fixes needed no new build. Step 13.3, Ceuta, is new.

Bordering now says each neighbour, each area that nearly touches and each sea of a coast at its nearest point from where you stand, as Overlapping and Nearby do, not at its own point (P3-T32m, your decision of 20 November). Left and Right in hierarchy mode say the direction of that nearest point too, and go round in that order. Steps 2.3, 5.2, 5.3, 14.3, 14.4 and 15.5 give what TobyMap now says.

## How to start TobyMap

* Open a terminal in the repository folder and run:

  `.venv\Scripts\python.exe -m desktop --pack E:\osmdata\tobymap\output\world\world.pack`

* "Go to 51.06,-1.31" below means: go to those coordinates, as you do with Ctrl+G. You never need to restart TobyMap.
* Each section gives the zoom and step it needs. Page Up and Page Down change the zoom; Shift+Page Up and Shift+Page Down change the step.

## Before you start

* Make sure the settings are as they start: in the Map menu, choose Reset all settings, then Reset. You hear "All settings are reset, as on a new installation", then the place.
* That also gives you the Windows desktop key map, all layers on, and the Political view.

## The Information panel's keys have changed

The groups are now in your order, on Shift+1 to Shift+7:

1. Within, Shift+1.
2. Nearby, Shift+2.
3. Bordering, Shift+3.
4. Contains, Shift+4.
5. Overlapping, Shift+5.
6. Passed over, Shift+6. This was "Crossed and passed".
7. Search, Shift+7. This was Shift+8.

Crossing has gone: what it held is now in Overlapping.

## Things I already know about

You don't need to report these.

* The coast is not yet a neighbour with its own ends, such as where Hampshire's coast meets Southampton. That is P3-T30b, and waits for your four decisions in docs/plan/p3-t30a-coast-report.md.
* On Islay, Loch Gruinart is in Nearby twice: OpenStreetMap has it as a point and as an area, with one name.
* Within on the Moselle condominium lists only the condominium and Europe, not Germany and Luxembourg.
* Scotland's stand-in areas are named "Part of Scotland in no county", not "no council area", as the build has no word for Scotland's council areas yet.
* Space on Exmoor says the range between Great Britain and the British Isles.
* A line that crosses an area's border where no crossing point is stored is said as "A449, 44 kilometres west, crosses it". This is the agreed wording for that case.
* The Cornish Main Line "crosses 8 times" Cornwall's border, because the coast counts as border until P3-T30.
* Roads with no number and no name are still one "Unnamed road" for each country.
* Down from Europe takes about 2.5 seconds, a little slower than before. It can be made faster later by giving the map a larger memory store, which costs memory in the browser.

## 1. Where am I: a town you are near (P3-T28p, P3-T28k)

Zoom 25 kilometres, step 10 kilometres.

* 1.1 Go to 51.06,-1.31, in Winchester. Go to says "Near Winchester. Hampshire, England, United Kingdom, Great Britain, British Isles, Europe", as Space does. Press Space: you hear the same.
* 1.2 Go to 50.99,-1.49. Go to and Space both say "Near Romsey. Hampshire, England, ...".
* 1.3 Go to 50.97,-1.35. Space says "Near Eastleigh", not Southampton: the town nearest for its size wins.
* 1.4 Go to 50.91,-1.40. Space says "Southampton, England, United Kingdom, ...", with no "Near", as the area you are in already has the town's name.
* 1.5 Go to 51.15,-1.10, in the country between Winchester and Alton. Space says "Hampshire, England, ..." with no town: none is near enough.
* 1.6 Space and Go to name a town you are near; a step never does. Go to 50.95,-1.40, in Southampton. Go to may say a town, such as "Near Hythe", or none: both are right. Now press Down once, to step south. You hear only the place you have stepped to, such as "Hampshire", with no "Near" and no town in front of it. Press Space: it names a town again if one is near. Tell me only if a step says "Near".
* 1.7 How near counts as near: a town's reach grows with its population, from 2 kilometres up to 30. Romsey reaches 3 kilometres, Winchester 4.7, Southampton 13, and London 30. Villages and suburbs are never named. Do these distances feel right?
* 1.8 Go to 51.06,-1.31. Press Page Up twice, to 100 kilometres. You hear only the zoom, "Zoom 50 kilometres." then "Zoom 100 kilometres.", as nothing in the place changed.
* 1.9 Press Page Up once more, to 250 kilometres. You hear "Zoom 250 kilometres. England". Counties are not said at this zoom, so Hampshire has gone from the list and the rest is unchanged; a zoom says only what changed, and when nothing was added it says the first area left. Press Space: it still says all of them, "England, United Kingdom, Great Britain, British Isles, Europe". There is no "Near Winchester" in the zoom.
* 1.10 Press Page Down. You hear "Zoom 100 kilometres. Hampshire": only what was added.

## 2. Stand-in areas (P3-T28a)

Zoom 25 kilometres, step 10 kilometres.

* 2.1 Go to 55.76,-6.28, on Islay. Space says "Near Bowmore. Argyll and Bute, Scotland, United Kingdom, Islay, British Isles, Europe". Before, it said "Scotland" as if it were a county.
* 2.2 Press L, then Shift+2 for Nearby. Neither has "Scotland, 6 kilometres east" any more. Nearby has 8 items: the Inner Seas off the West Coast of Scotland (the Sea of the Hebrides before the world pack of 21 November) and the North Atlantic Ocean, 37 metres north, Bowmore, 600 metres south-west, then bays and points such as Laggan Bay and Loch Indaal. Jura is not among them: it is further away than these 8.
* 2.3 Go to 50.72,-1.88, in Bournemouth. Press Shift+3 for Bordering. The heading is "Bordering Bournemouth, Christchurch and Poole, 3 items, clockwise from north". The neighbours are Dorset, such as "Dorset, 4.9 kilometres north, shared border 34 kilometres, 28 percent", then Hampshire, "8.3 kilometres north-east", with no "England", then the heading "Coast, 66 kilometres", with the English Channel under it, "580 metres south".

## 3. Within, Shift+1 (P3-T29h)

Zoom 25 kilometres, step 10 kilometres.

* 3.1 Go to 51.06,-1.31. Press Shift+1. The heading is "Within, 6 items, smallest first". The items are Hampshire, England, United Kingdom, Great Britain, British Isles and Europe, each with its centre, such as "Hampshire, centre 2.9 kilometres south-west" and "England, centre 210 kilometres north".
* 3.2 Press Shift+2 for Nearby, move to River Itchen and press Enter. You hear "River Itchen. Hampshire, England, United Kingdom, Great Britain, British Isles, Europe". River Itchen is now the current feature. The focus goes to the heading of the group, "Nearby, 8 items, by distance", not to its first item.
* 3.3 Press F2 for the map, then Space. You hear "River Itchen, here. Near Winchester. Hampshire, England, United Kingdom, Great Britain, British Isles, Europe": Space starts with the current line, as Within lists it first. Press Shift+1. The heading is "Within, 7 items, smallest first". The first item is "River Itchen, here", then the areas as before. Before, a line or place was never in Within.
* 3.4 Press M for hierarchy mode: "Hierarchy mode. River Itchen." Then press Up. A list "Up from River Itchen" asks which, with "England, constituent country of the United Kingdom" and "Great Britain, island": choose England. Press M to go back to stepping.

## 4. Nearby, Shift+2 (P3-T29b)

* 4.1 Go to 51.06,-1.31. Press Shift+2. The heading is "Nearby, 8 items, by distance". The first two items are "River Itchen, 170 metres east" and "Winchester, 260 metres north-west".
* 4.2 Move to Winchester and press Enter. You hear "Winchester. Hampshire, England, United Kingdom, Great Britain, British Isles, Europe". You are now on Winchester's own point. The focus goes to the heading, "Nearby, 8 items, by distance".
* 4.3 Press Shift+2. Winchester is not in Nearby, as you are at it, and the heading still says 8 items.
* 4.4 Press Shift+1. The first item of Within is "Winchester, here".

## 5. Bordering, Shift+3 (P3-T28b, P3-T28i, P3-T28r, P3-T32m)

* 5.1 Go to 51.06,-1.31. Press Shift+3. The heading is "Bordering Hampshire, 12 items, clockwise from north".
* 5.2 Press Down through the neighbours: Borough of Wokingham, Bracknell Forest, Surrey, West Sussex, Portsmouth, Isle of Wight, Southampton, Bournemouth, Christchurch and Poole, Dorset, Wiltshire and West Berkshire. They are in order clockwise from north by the direction of each one's nearest point, so West Berkshire, just west of north, is last. Each says the distance and direction of its nearest point, its shared border and its share, such as "West Sussex, 29 kilometres south-east, shared border 40 kilometres, 7 percent". Before, it said "61 kilometres east", to West Sussex's own point near Horsham. There is no "England". The Isle of Wight says "nearly touches, 1.3 kilometres across".
* 5.3 The last item is a heading, "Coast, 190 kilometres". Open it. It has only "English Channel", such as "English Channel, 20 kilometres south, 190 kilometres of coast", the nearest point of its water. The North Atlantic Ocean and the Inner Seas off the West Coast of Scotland are not there any more. If territorial waters are listed with the English Channel, tell me.
* 5.4 Press Right on West Sussex. The ends of the shared border are listed clockwise from north. There are two, each said once: first "End of the border with West Sussex, where Surrey meets it, 39 kilometres east", then "End of the border with West Sussex, at the coast, English Channel, 36 kilometres south-east". Before, the coast end was said three times, as the shared border is stored in two parts (P3-T32c).
* 5.5 Press Shift+1, move to England and press Shift+Enter. You hear "Current layer: Regions and constituent countries. England is the current feature."
* 5.6 Press Shift+3. The heading is "Bordering England, 3 items, clockwise from north": Wales, Scotland, then "Coast, 6,270 kilometres". Open the Coast heading. It has five items, each a stretch of coast, with the sea it is on, the distance and direction of its nearest point, its length and its share. The English Channel and the Bristol Channel are now separate stretches, and no stretch is named after the North Atlantic Ocean. The five are, such as:
  * "Coast to Wales, Bristol Channel, 110 kilometres north-west, 610 kilometres, 10 percent": from Land's End up the north coast of Cornwall and Devon to the Severn.
  * "Coast, English Channel, 20 kilometres south, 1,570 kilometres, 25 percent": from Land's End to Dover.
  * "Coast from Wales to Scotland, Irish Sea, 270 kilometres north, 760 kilometres, 12 percent": from the Dee to the Solway.
  * "Coast from Scotland, North Sea, 130 kilometres east, 1,910 kilometres, 30 percent": from the Tweed down the east coast to Dover.
  * "Coast of islands, 1,420 kilometres, 23 percent".
  There are no short stretches with Wales or Scotland at both ends, and no Sea of the Hebrides. Is each stretch's sea the one you would expect, and does each say where it runs from and to?

## 6. Contains, Shift+4 (P3-T29c, P3-T29d)

England is still the current feature from 5.5.

* 6.1 Press Shift+4. The heading is "Contains England, 5 items, by name": Counties 3, Rivers 3, Motorways and trunk roads 20, Main railway lines 6, and Cities and towns 14. It opens in under a second.
* 6.2 Open "Counties 3": Hampshire, Southampton and Wiltshire. Hampshire says "Hampshire, you are inside", with no distance.
* 6.3 Press Shift+1, move to Hampshire and press Shift+Enter. You hear "No current layer. The current feature is the smallest area here, Hampshire.", the first time, even though England's layer was current. Before, you heard "Current layer: Counties". Shift+Enter on the smallest area here puts the usual rule back; Shift+Enter on a larger area again, such as England, says "Current layer: Regions and constituent countries. England is the current feature."
* 6.4 Press Shift+4: "Contains Hampshire, 3 items, by name": Motorways and trunk roads 10, Main railway lines 2, and Cities and towns 13. It holds only what is wholly inside Hampshire, and only what is within 25 kilometres of you, measured to each feature's nearest point. Towns say a short distance to their point, such as "Winchester, 260 metres north-west".
* 6.5 The M3 is not in Contains Hampshire, as it runs on into Surrey. Nor is the River Itchen, as its mouth is in Southampton. Both are now in Overlapping, section 7. Press Shift+5, open "Lines crossing its border", move to the A27 and press Enter. You go to the A27, and it becomes the current feature: the focus goes to the heading of the group, and Shift+1 now starts with "A27, here".
* 6.6 Bays and straits, whether drawn as areas or only points, are in one subgroup, "Seas, bays and straits".
* 6.7 Press Ctrl+F, type english channel, and press Enter on "English Channel, North Atlantic Ocean, sea, bay or strait". You hear "English Channel, North Atlantic Ocean. Zoom 500 kilometres." Press Shift+4. The heading is "Contains English Channel, 2 items, by name". The items are two headings: "Seas, bays and straits 476", such as Alderney Race and Christchurch Bay, and "Islands 3": Guernsey, the Isle of Wight and Jersey, such as "Guernsey, 45 kilometres south-east". At this zoom only the larger islands are listed; hierarchy mode's Down, step 14.8, says how many there are in all. There are no rivers, roads, railways or towns. The first time, it takes about 6 seconds to open on this pack, as the pack does not yet store how many islands each sea holds; the next build stores it (P3-T32g).
* 6.8 Press Ctrl+F, type sark and press Enter on the Sark that is a county or region of Guernsey. Press Space: "Sark, Guernsey, Europe", Sark once. Press Shift+1. The heading is "Within, 3 items, smallest first": Sark, Guernsey and Europe, each once. Before, Sark was listed three times, as its county, region and island are the same land. Press Ctrl+F, choose "Only Islands" and type sark: is Sark found as an island too?

## 7. Overlapping, Shift+5 (P3-T29e)

Zoom 25 kilometres, step 10 kilometres.

* 7.1 Go to 51.06,-1.31. Press Shift+5. The heading is "Overlapping Hampshire, 3 items, by name".
* 7.2 First come the areas of other layers that cover part of Hampshire, under a heading for each layer. There is one, "Islands 1", with "Burrow Island, 31 kilometres south-east, less than 1 percent of Hampshire and 24 percent of Burrow Island overlap" (P3-T32a). Burrow Island is a tiny island in Portsmouth Harbour, cut by the border with Portsmouth. It is the only island listed: Hayling Island is wholly inside Hampshire, so it is in Contains, and Portsea Island is in Portsmouth. No sea is listed for Hampshire's coast. Great Britain is not listed: the build counts Hampshire as wholly inside Great Britain.
* 7.3 Then the heading "Lines crossing its border 24". The M3 is there, "M3, crosses once, nearest 48 kilometres north-east", and the River Itchen, "River Itchen, crosses once, nearest 14 kilometres south".
* 7.4 Press Right on the M3. Its one crossing point is listed: "Crossing of M3, 48 kilometres north-east", where the M3 goes into Surrey. A line with one crossing has no number; a line with two or more says "Crossing 1 of", "Crossing 2 of" and so on (P3-T32k). Press Enter on it: you go there, M3 becomes the current feature, and the focus goes to the heading of the group. Press Shift+1: the first item is "M3, here". Alt+Comma comes back. Before, the two carriageways made two crossings at the same place (P3-T32d).
* 7.5 The last heading is "Lines along its border 3": the River Avon, the River Test and the River Wey, such as "River Test, 14 kilometres west, along its border".
* 7.6 Press Shift+2 for Nearby, move to River Itchen and press Enter. Press Shift+5. The heading is "Overlapping River Itchen, 2 items, from its start". The items are the areas the river passes through, in order from its source: "Hampshire, you are inside, 88 percent of River Itchen is inside it", then "Southampton, 13 kilometres south, 12 percent of River Itchen is inside it". England is not listed, as it holds all of the river.
* 7.7 Press Shift+2, move to Winchester and press Enter. Press Shift+5. The heading is "Overlapping Winchester, no items", and under it "Nothing overlaps Winchester." A place is either inside an area or not.
* 7.8 Search for England with "Only Regions and constituent countries" and press Enter. Press Shift+5. The heading is "Overlapping England, 4 items, by name": Mountain ranges 4, Islands 3, Lines crossing its border 40, and Lines along its border 31. It opens in about half a second, even the first time. Tell me how long it feels.

## 8. Passed over, Shift+6 (P3-T29f)

Zoom 25 kilometres, step 10 kilometres.

* 8.1 Go to 51.063,-1.20, east of Winchester. Press Left once, to step 10 kilometres west through Winchester.
* 8.2 Press Shift+6. The heading is "Passed over, 6 items, by distance". The items come nearest first, each with its distance and direction from where you are now, among them: "A31, crossed, 8.3 kilometres east", "A272, Spitfire Link, crossed", "M3, crossed", "River Itchen, crossed", "Passed nearby to Winchester, closest 190 metres, 2.1 kilometres east", and "South West Main Line, crossed, 1.5 kilometres east".
* 8.3 Press Ctrl+S. The focus moves to the heading, and you hear it once: "Passed over, 6 items, clockwise from north". Ctrl+S again says "by name", and once more "by distance". Ctrl+Shift+S goes back.
* 8.4 Is "Passed nearby to Winchester" clear?

## 9. Sorting, and hearing the order (P3-T29g)

* 9.1 Go to 51.06,-1.31. Press Shift+2, then Down to the first item.
* 9.2 Press Ctrl+S. The focus goes to the heading, and NVDA says it once: "Nearby, 8 items, clockwise from north". Listen for it being said twice; it should not be.
* 9.3 Press Ctrl+S again, with the focus on the heading. You hear "Nearby, 8 items, by name", once.
* 9.4 Press Ctrl+Shift+S. You hear "Nearby, 8 items, clockwise from north" again.
* 9.5 Is the order on the heading enough, or do you miss the old "Sorted by" message?

## 10. Search, Shift+7

Not done. This set moves to the Phase 4 checklist; its steps are unchanged.

* 10.1 You are at 51.06,-1.31. Press Ctrl+F and type winchester. The first result is "Winchester, England, United Kingdom, city or town"; the second is "Winchester, Virginia, United States, county of Virginia". Search now puts the nearer of two equal results first (P3-T32f). Press Enter on the first. Press Shift+7. The heading is "Search, 20 items, best match first": the results are in the order the search ranked them (P3-T32k). The first item is "Winchester, England, United Kingdom, here", as you are standing at it; before, it said a direction, "south" (P3-T32l). The others say their direction, such as "Winchester, Virginia, United States, west". Press Ctrl+S: you hear "Search, 20 items, by name". Ctrl+S again gives "by distance"; Ctrl+Shift+S twice comes back to "best match first".
* 10.1a Press Ctrl+F, type hampshire, wait for the results, and press Cancel. Press Shift+7. The first item is "Hampshire, England, United Kingdom, you are inside" (P3-T32l).
* 10.2 Press F1 on the map. The list has "Go to Passed over: Shift+6" and "Go to Search: Shift+7". Close it.

## 11. Details and Wikipedia (P3-T28g, P3-T28l)

Zoom 25 kilometres.

* 11.1 Go to 51.06,-1.31. Press F4 and read a line at a time. You hear:
  * Hampshire
  * Type: county of England
  * Part of: England
  * Area: 3,690 square kilometres
  * Whole border: 560 kilometres, of which land is 370 kilometres and coastline is 190 kilometres. The land and the coastline add up to the whole border, give or take the rounding.
  * Population: 1,416,808, Wikidata, 2022
  * Wikipedia article: Hampshire
  * Shape and name: OpenStreetMap, ODbL licence
* 11.2 There is no Elevation line: heights are now given for places only, such as peaks and towns. There is no Location line either: Details gives one only for an item you chose that is not the area you are in.
* 11.3 Move to "Wikipedia article: Hampshire" and press Enter. You hear "Opening the Wikipedia article for Hampshire." and the article opens. Come back to TobyMap.
* 11.4 Press F2 for the map, then Ctrl+Alt+W. You hear "Opening the Wikipedia article for Hampshire." again, from the map. Try it from the Information panel too, with F3.
* 11.5 Press Shift+2, move to Winchester and press Enter. Press F4. You hear Winchester, "Type: city or town", "Population: 35,200, Wikidata, 13 November 2026", "Official name: Winchester, Wikidata, 13 November 2026", the Wikipedia article and the source. There is no Elevation line, as Wikidata gives no height for Winchester. A peak has one.

## 12. The Map views dialog (P3-T28h)

* 12.1 Press Ctrl+Shift+V. The focus is on the view in use: "Political, in use".
* 12.2 Tab through the dialog. The buttons, in order, are Add, Save changes, Rename, Delete, OK and Cancel. With Political chosen, you still reach Save changes, Rename and Delete by Tab, and NVDA says each is unavailable; pressing it does nothing and says nothing. "Save the layers as a view" is no longer in the list.
* 12.3 Press Add, type My view, and press OK. You hear "Added the My view view. OK uses it." My view is chosen in the list. Add keeps the layers as they are at that moment.
* 12.4 With My view chosen, press Rename, type Test view and press OK. You hear "My view is now called Test view." Then press Delete. You hear "The Test view view is deleted. Cancel brings it back."
* 12.5 Move to Physical and press Enter. Enter is OK, the default: you hear "Physical view."
* 12.6 Press Ctrl+Shift+V, choose Political, and press Escape. Escape cancels, as Cancel does, so the Physical view stays. Press Ctrl+Shift+V again, choose Political and press OK: "Political view."
* 12.7 Press Ctrl+Shift+V and choose Political. Tab to Rename, then Delete: each is unavailable, and pressing Enter on it says nothing. You no longer hear a message that only your own views can be renamed or deleted. Press Cancel.
* 12.8 Press Ctrl+Shift+V, press Add, type Mine and press OK, then OK again. Change a setting that a view holds on any layer, such as switching a layer off (Ctrl+Shift+L, then the layer's settings). Press Ctrl+Shift+V. The list has "Custom: your changes to the Mine view, in use". Choose Mine. Save changes is now available. Press it. You hear "The layers are saved into the Mine view. OK keeps it." The Custom line goes. Save changes is unavailable again, as nothing differs. Press OK. Then delete the Mine view, and reset the setting you changed.

## 13. Exclaves said by their own names (P3-T28j)

Zoom 25 kilometres.

* 13.1 Go to 42.465,1.98, in Llívia. Space says "Girona, Catalonia, Spain, Llívia, exclave of Spain in France", then the mountain ranges.
* 13.2 Go to 47.697,8.69, in Büsingen. Space says "Near Schaffhausen. Landkreis Konstanz, Baden-Württemberg, Germany, Büsingen am Hochrhein, exclave of Germany in Switzerland, Europe".
* 13.3 Go to 35.89,-5.31, in Ceuta. Space says "Ceuta, Spain, exclave on the coast of Morocco, Africa". Before, it said "Unnamed island" here, for a small part of Ceuta's land cut off by a narrow channel. Such an island is no longer said when larger land of the same country is within 100 metres (P3-T32e). The exclave's name is said once, not again after Ceuta's county.
* 13.4 Go to 54.71,20.51, in Kaliningrad. Space says the name once, then Russia, then the exclave in words such as "exclave on the coast of Lithuania and Poland", then the rest, such as "Kaliningrad, Russia, exclave of Russia on the coast of Lithuania and Poland, Europe". Before, it left the exclave words out, as the exclave is the same land as the region.
* 13.5 Go to -5.55,12.20, in Cabinda. Space says "Cabinda, Angola" and then the exclave words, such as "exclave on the coast of ...", with the neighbouring countries named. Tell me what you hear.

## 14. Hierarchy mode (P3-T28m, P3-T28o, P3-T28n)

* 14.1 Go to 54,-2, at zoom 25 kilometres. Press Shift+3: the heading is "Bordering" and the county there, such as North Yorkshire. Now zoom out to 2,500 kilometres with Page Up. The zoom lets go of that county. Space says "United Kingdom, British Isles, Europe". Press Shift+3: the heading is "Bordering United Kingdom", not the British Isles, as the current feature is now the first area Space says. It is not North Yorkshire.
* 14.2 Zoom in to 25 kilometres. Go to 50.72,-1.88, in Bournemouth. Press M: "Hierarchy mode. Bournemouth, Christchurch and Poole."
* 14.3 Press Right. You reach Dorset at once, the first neighbour clockwise from north by its nearest point: "Dorset, north, shared border 34 kilometres. Zoom 50 kilometres." Press Enter. You hear "Left and Right now go round Dorset." Before, it said "Nothing to go to".
* 14.4 Press Right a few times. You go round Dorset's neighbours, each with the direction of its nearest point from Dorset's own point, its shared border and the zoom: "Wiltshire, north-east, shared border 39 kilometres. Zoom 50 kilometres.", then "Hampshire, north-east, shared border 42 kilometres. Zoom 100 kilometres.", then "Bournemouth, Christchurch and Poole, east, shared border 34 kilometres. Zoom 25 kilometres.", then "Devon, west, shared border 20 kilometres. Zoom 100 kilometres."
* 14.5 Press M: "Stepping mode."
* 14.6 Press Ctrl+F, type exmoor, and press Enter on "Exmoor, England, United Kingdom, mountain range". Press M, then Up. A list "Up from Exmoor" asks which, with England and Great Britain. Before, it said "Nothing holds Exmoor". Press Cancel.
* 14.7 Press Shift+5. The heading is "Overlapping Exmoor, 1 item, by name". Under "Counties 2" are Devon, "31 percent of Exmoor and less than 1 percent of Devon overlap", and Somerset, "you are inside, 69 percent of Exmoor and 2 percent of Somerset overlap", as each holds only part of Exmoor. There are no "Oceans and seas" or "Seas, bays and straits" headings: Exmoor's shape is now cut to the coast as drawn, and no sea overlaps it. If a sea is listed, tell me its percentage. Press M to go back to stepping.
* 14.8 Press Ctrl+F, type english channel, and press Enter on it. Press M, then Down. It takes about half a second, as step 6.7 has already counted the islands; without 6.7 first it takes about 6 seconds on this pack. The list "Inside English Channel" has two kinds: "Seas, bays and straits 476" and "Islands: 3 shown at this zoom, 606 in all". There are no Rivers, Motorways and trunk roads, Main railway lines or Cities and towns. Press Cancel, then M.

## 15. The Moselle condominium (P3-T28f)

* 15.1 Press Ctrl+F, type moselle condominium and press Enter on it. Space says "Moselle condominium, shared by Germany and Luxembourg, Europe".
* 15.2 Press M, then Up. A list asks which to go up to, with Germany and Luxembourg. Press Cancel, then M.
* 15.3 Press W. Open Europe. The condominium is not among Europe's countries.
* 15.4 Open Germany. The condominium is listed under it. Close Germany and open Luxembourg: it is listed there too. Close the tree with Cancel.
* 15.5 Press Shift+3. The heading is "Bordering Moselle condominium, shared by Germany and Luxembourg, 4 items, clockwise from north". Germany and Luxembourg each have "shared border 130 kilometres, 50 percent". France has "shared border 80 metres, less than 1 percent", at Schengen, and Belgium "touches at a point", such as "Belgium, 41 kilometres west, touches at a point", measured to its nearest point (before, "170 kilometres north-west", to its own point), where the condominium's river Our reaches Belgium. They share only about 7 metres of border, too short for the build to store as a border (P3-T32b).

## 16. Roads that are far apart, and Belfast (P3-T28d, P3-T21b)

* 16.1 Press Ctrl+F, choose "Only Motorways and trunk roads", and type m3. There are M3s in many countries. The two in the United Kingdom come first, as they are the nearest: "M3, England, United Kingdom, road", then "M3, Northern Ireland, United Kingdom, road". Then come Hungary and others (P3-T32f).
* 16.2 Press Enter on the second, the one in Northern Ireland. You hear "M3, Northern Ireland, United Kingdom. Zoom 1 kilometre." Press Space: "Near Belfast. Belfast City District, Northern Ireland, United Kingdom, Ireland, British Isles, Europe". Before, the two were one road, said "M3, United Kingdom".
* 16.3 Press M, then Up. You go straight to Belfast, with no list: "Belfast City District. Zoom 10 kilometres." The road is wholly inside Belfast City District, even where it crosses the River Lagan on a bridge. Press M.
* 16.4 Go to 54.68,-5.78, in Belfast Lough, at zoom 25 kilometres. Space says "Near Belfast. Inner Seas off the West Coast of Scotland, North Atlantic Ocean", then, on the world pack of 21 November, "Territorial waters of the United Kingdom". Before, it said "Sea of the Hebrides", Natural Earth's own name for an area that takes in the North Channel and Belfast Lough. You chose option 1, the Inner Seas name (DP221). Does it sound right here?

## 17. Bays on rivers (P3-T28c)

* 17.1 Press Ctrl+F and type hatch pool. There is no Hatch Pool among the results: the first are names that are near it, such as "Hatch, New Mexico, United States, city or town" and Hatch Cove in Maine. The fishing pools on the River Test are no longer in the pack.
* 17.2 Type poole harbour instead. The first result is "Poole Harbour, English Channel, sea, bay or strait": bays at the coast and on lakes are kept.

## 18. Key maps and your keys (P3-T31)

Not done. This set moves to the Phase 4 checklist. Its steps are unchanged, except that each message on the Keys tab is now said once, and a key named in a message, such as "Press Ctrl+I again" or "Press Shift+F1 again to leave", follows the key map in use.

The words "key map", "your keys" and "key file" are in the glossary.

* 18.1 Press Ctrl+Comma for Settings and go to the Keys tab. There is a "Key map" list, set to "Windows desktop". Below it are the commands and their keys, and buttons "Save keys as", "Open key file" and "Reset keys".
* 18.2 In the Key map list, choose "Alternative". It is used at once, and you hear "Key map: Alternative." The list of commands shows Settings on Ctrl+Shift+X and Open the current feature's Wikipedia article on Alt+Shift+W. Alternative avoids Ctrl+Alt with a letter, which is AltGr on many European keyboards. Press OK.
* 18.3 Press Ctrl+Comma. Nothing opens. Press Ctrl+Shift+X: Settings opens. Go to the Keys tab.
* 18.4 Change the key of Heading to Ctrl+Q. You hear "Heading is now Ctrl+Q."
* 18.5 Press "Save keys as". The file name offered is tobymap-keys.json. Save it in your Documents folder. TobyMap says nothing after saving: the focus comes back to the Keys tab.
* 18.6 Press "Reset keys". You hear "Your keys are reset. The keys are those of the Alternative key map." Heading is back on H.
* 18.7 Press "Open key file" and open tobymap-keys.json. You hear "Key file opened. The key map is Alternative." Heading is on Ctrl+Q again.
* 18.8 In the Key map list, choose "Windows desktop": "Key map: Windows desktop." Heading stays on Ctrl+Q, as your keys are kept on top of the key map.
* 18.9 Press "Reset keys". You hear "Your keys are reset. The keys are those of the Windows desktop key map." Press OK. Ctrl+Comma opens Settings again; close it.
* 18.10 The key list is now docs/design/keymap.csv, made from the key maps. It replaces docs/plan/phase-3-keys.csv. Its columns are Command, Where it works, Windows desktop, Mac desktop, Windows browser, Mac browser, Variations, and Notes on the variations. Open it and tell me if a key is wrong or hard to press.
* 18.11 Your open comments from the old key list, for when you are ready: Measure on Shift+M, to decide after you have tried measuring; Search on Ctrl+F in the browsers, after your browser test; the World tree on W, to confirm; and Wikipedia, which is Ctrl+Alt+W on the Windows desktop and Alt+Shift+W in the browsers, as Ctrl+Shift+W closes the browser tab.

## 19. The query builder searches for a feature (P3-T28q)

* 19.1 Press Q. In Find, choose Countries. In Relation, choose crossing.
* 19.2 In Of, choose "Search for a feature". The search dialog opens. Choose "Only Rivers", type rhine, and press Enter on the Rhine. You are back in the query builder, with the Rhine in Of.
* 19.3 Press OK. You hear "Countries crossed by Rhine: 6, in the Search group."
* 19.4 Press Shift+7. The heading is "Countries crossed by Rhine, 6 items, from its start" (P3-T32k). The countries are in the river's order: Switzerland, Liechtenstein, Austria, Germany, France, Netherlands.
* 19.5 Is this way of choosing the feature better than before? Last time you found pressing Cancel to keep the search unclear.

## 20. Layer sounds (P3-T11b, SON-3, SON-4, SCP-7)

Section 20 of the Phase 3 checklist, now on the world pack. You passed it on the trial pack.

* 20.1 Go to 51.06,-1.31, at zoom 25 kilometres. Press Shift+2 for Nearby, and press Space on River Itchen, Winchester, M3 and South West Main Line. Each plays a different sound from its direction: river, road, railway and town. The sounds are placeholders.
* 20.2 Press L. Each item plays its own layer's sound as it is said.
* 20.3 Press Ctrl+Comma, and go to the Earcons tab. The list has ten layer sounds: Continent, Country, Region or county, Water, River, Road, Railway, City or town, Mountain range or region, and Peak. Each can be switched off, have its volume changed, or use your own file. Press Cancel.
* 20.4 Press Ctrl+Shift+L, move to Rivers, and press "Settings for this layer". There is a list "Sound of this layer's features in look around and Hear its direction", with "No sound" first. Choose another sound, press OK, then OK. Space on River Itchen in Nearby plays the sound you chose. Set it back.
* 20.5 Can you tell the layers apart by sound? Which would you change?

## 21. Overall

* 21.1 For a line, Overlapping lists areas with less than 1 percent of it inside, said "less than 1 percent of ... is inside it". Go to 51.06,-1.31. Search for thames with "Only Rivers". The first result is "River Thames, United Kingdom, river", and the second "Thames River, Ontario, Canada, river". Press Enter on the first, then Shift+5. The heading is "Overlapping River Thames, 77 items, from its start". 50 of the 77 are under 1 percent, such as "Nag's Head Island, 38 kilometres west, less than 1 percent of River Thames is inside it"; 40 of those are small islands, and 10 are counties. Should items under 1 percent be left out?
* 21.2 Tell me anything else that sounds wrong, slow or unclear.

## 22. Territorial waters (P4-T12)

A new layer, on the world pack of 21 November 2026. It is said after the sea you are on, and it is a lighter blue in the Political and Physical views.

* 22.1 Go to 46.20,-1.75, in the Bay of Biscay a few kilometres off France's coast, at zoom 25 kilometres. Space says "Bay of Biscay, North Atlantic Ocean, Territorial waters of France". If the place is beyond the territorial waters, move a little east and try again.
* 22.2 Go to 46.20,-4.0, further out to sea. Space says the sea only, with no territorial waters.
* 22.3 Press Ctrl+Shift+L. The list has a layer for territorial waters. Do its words make sense?


## Finishing

Send me your notes in docs/checklists/phase-3-tidy-up-2-desktop-results.txt. Then the web and sighted checklists are brought up to date from this one, P3-T22b.

