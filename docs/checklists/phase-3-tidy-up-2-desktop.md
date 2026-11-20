# Phase 3 tidy-up 2 checklist: desktop version, world pack

This is a short third pass of the desktop checklist, for you to work through with NVDA on Windows 11. It covers only what changed in the second tidy-up plan (docs/plan/phase-3-tidy-up-plan2.md): the fixes and changes of P3-T28, the Information panel group by group as now defined (P3-T29), key maps (P3-T31), and the layer sounds, section 20 of the Phase 3 checklist.

It uses the world pack built on 20 November 2026. That pack has every change that needs a build, except the coast as a border (P3-T30b), which waits for your answers to the coast report.

For each step, write down its number, such as 4.3, and either "works" or what you heard instead. Put your notes in a text file next to this one, docs/checklists/phase-3-tidy-up-2-desktop-results.txt, as before. Lines starting with ">" are fine for answers to questions.

The expected words below are what TobyMap's core said on the world pack of 20 November, at the places given. Distances to things depend on exactly where you stand, so those are given as "such as". If the words differ only in a number, say so, but it is not a fault unless the number seems wrong.

A few steps now say what TobyMap does where it differs from what was planned, and are marked "Possible fault". You don't need to report those, but tell me if you agree.

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
* The Cornish Main Line "crosses 22 times" England's border, because the coast counts as border until P3-T30.
* Roads with no number and no name are still one "Unnamed road" for each country.
* Down from Europe takes about 2.5 seconds, a little slower than before. It can be made faster later by giving the map a larger memory store, which costs memory in the browser.

## 1. Where am I: a town you are near (P3-T28p, P3-T28k)

Zoom 25 kilometres, step 10 kilometres.

* 1.1 Go to 51.06,-1.31, in Winchester. Press Space. You hear "Near Winchester. Hampshire, England, United Kingdom, Great Britain, British Isles, Europe".
* 1.2 Go to 50.99,-1.49. Space says "Near Romsey. Hampshire, England, ...".
* 1.3 Go to 50.97,-1.35. Space says "Near Eastleigh", not Southampton: the town nearest for its size wins.
* 1.4 Go to 50.91,-1.40. Space says "Southampton, England, United Kingdom, ...", with no "Near", as the area you are in already has the town's name.
* 1.5 Go to 51.15,-1.10, in the country between Winchester and Alton. Space says "Hampshire, England, ..." with no town: none is near enough.
* 1.6 Only Space names the town. Go to 50.95,-1.40, in Southampton, and step once with Down, into Hampshire. You hear only "Hampshire", with no "Near".
* 1.7 How near counts as near: a town's reach grows with its population, from 2 kilometres up to 30. Romsey reaches 3 kilometres, Winchester 4.7, Southampton 13, and London 30. Villages and suburbs are never named. Do these distances feel right?
* 1.8 Go to 51.06,-1.31. Press Page Up twice, to 100 kilometres. You hear only the zoom, "Zoom 50 kilometres." then "Zoom 100 kilometres.", as the place is the same.
* 1.9 Press Page Up once more, to 250 kilometres. You hear "Zoom 250 kilometres. England, United Kingdom, Great Britain, British Isles, Europe": counties are not said at this zoom, so what Space would say has changed. There is no "Near Winchester": only Space names the town.
* 1.10 Press Page Down. You hear "Zoom 100 kilometres. Hampshire, England, United Kingdom, Great Britain, British Isles, Europe".

## 2. Stand-in areas (P3-T28a)

Zoom 25 kilometres, step 10 kilometres.

* 2.1 Go to 55.76,-6.28, on Islay. Space says "Near Bowmore. Argyll and Bute, Scotland, United Kingdom, Islay, British Isles, Europe". Before, it said "Scotland" as if it were a county.
* 2.2 Press L, then Shift+2 for Nearby. Neither has "Scotland, 6 kilometres east" any more. Nearby has 8 items: the Sea of the Hebrides and the North Atlantic Ocean, 37 metres north, Bowmore, 600 metres south-west, then bays and points such as Laggan Bay and Loch Indaal. Jura is not among them: it is further away than these 8.
* 2.3 Go to 50.72,-1.88, in Bournemouth. Press Shift+3 for Bordering. The heading is "Bordering Bournemouth, Christchurch and Poole, 3 items, clockwise from north". The neighbours are Hampshire and Dorset, with no "England", then the heading "Coast, 66 kilometres", with the English Channel under it.

## 3. Within, Shift+1 (P3-T29h)

Zoom 25 kilometres, step 10 kilometres.

* 3.1 Go to 51.06,-1.31. Press Shift+1. The heading is "Within, 6 items, smallest first". The items are Hampshire, England, United Kingdom, Great Britain, British Isles and Europe, each with its centre, such as "Hampshire, centre 2.9 kilometres south-west" and "England, centre 210 kilometres north".
* 3.2 Press Shift+2 for Nearby, move to River Itchen and press Enter. You hear "River Itchen. Hampshire, England, United Kingdom, Great Britain, British Isles, Europe". River Itchen is now the current feature.
* 3.3 Press Shift+1. The heading is "Within, 7 items, smallest first". The first item is "River Itchen, here", then the areas as before. Before, a line or place was never in Within.
* 3.4 Press M for hierarchy mode: "Hierarchy mode. River Itchen." Then press Up. A list "Up from River Itchen" asks which, with "England, constituent country of the United Kingdom" and "Great Britain, island": choose England. Press M to go back to stepping.

## 4. Nearby, Shift+2 (P3-T29b)

* 4.1 Go to 51.06,-1.31. Press Shift+2. The heading is "Nearby, 8 items, by distance". The first two items are "River Itchen, 170 metres east" and "Winchester, 260 metres north-west".
* 4.2 Move to Winchester and press Enter. You hear "Winchester. Hampshire, England, United Kingdom, Great Britain, British Isles, Europe". You are now on Winchester's own point.
* 4.3 Press Shift+2. Winchester is not in Nearby, as you are at it, and the heading still says 8 items.
* 4.4 Press Shift+1. The first item of Within is "Winchester, here".

## 5. Bordering, Shift+3 (P3-T28b, P3-T28i, P3-T28r)

* 5.1 Go to 51.06,-1.31. Press Shift+3. The heading is "Bordering Hampshire, 12 items, clockwise from north".
* 5.2 Press Down through the neighbours: West Berkshire, Borough of Wokingham, Bracknell Forest, Surrey, West Sussex, Portsmouth, Isle of Wight, Southampton, Bournemouth, Christchurch and Poole, Dorset and Wiltshire. Each says its shared border and its share, such as "West Sussex, 61 kilometres east, shared border 40 kilometres, 7 percent". There is no "England". The Isle of Wight says "nearly touches, 1.3 kilometres across".
* 5.3 The last item is a heading, "Coast, 190 kilometres". Open it. It has only "English Channel", such as "English Channel, 130 kilometres south-west, 190 kilometres of coast". The North Atlantic Ocean and the Sea of the Hebrides are not there any more.
* 5.4 Press Right on West Sussex. The ends of the shared border are listed clockwise from north, so "End of the border with West Sussex, where Surrey meets it, 39 kilometres east" comes first. Then "End of the border with West Sussex, at the coast, English Channel, 36 kilometres south-east" is said three times. Possible fault: the shared border is stored in two parts, and three of their four ends are said with the same words, so they sound like one end listed three times.
* 5.5 Press Shift+1, move to England and press Shift+Enter. You hear "Current layer: Regions and constituent countries. England is the current feature."
* 5.6 Press Shift+3. The heading is "Bordering England, 3 items, clockwise from north": Wales, Scotland, then "Coast, 6,270 kilometres". Open the Coast heading. It lists the North Sea, 2,750 kilometres of coast, the English Channel, 1,880, the Irish Sea, 840, and the Bristol Channel, 690. There is no Sea of the Hebrides.

## 6. Contains, Shift+4 (P3-T29c, P3-T29d)

England is still the current feature from 5.5.

* 6.1 Press Shift+4. The heading is "Contains England, 5 items, by name": Counties 3, Rivers 3, Motorways and trunk roads 20, Main railway lines 6, and Cities and towns 14. It opens in under a second.
* 6.2 Open "Counties 3": Hampshire, Southampton and Wiltshire. Hampshire says "Hampshire, you are inside", with no distance.
* 6.3 Press Shift+1, move to Hampshire and press Shift+Enter. You hear "No current layer. The current feature is the smallest area here, Hampshire." Shift+Enter on the smallest area here puts the usual rule back; Shift+Enter on England again only says that England is the current feature.
* 6.4 Press Shift+4: "Contains Hampshire, 3 items, by name": Motorways and trunk roads 10, Main railway lines 2, and Cities and towns 13. It holds only what is wholly inside Hampshire, and only what is within 25 kilometres of you, measured to each feature's nearest point. Towns say a short distance to their point, such as "Winchester, 260 metres north-west".
* 6.5 The M3 is not in Contains Hampshire, as it runs on into Surrey. Nor is the River Itchen, as its mouth is in Southampton. Both are now in Overlapping, section 7.
* 6.6 Bays and straits, whether drawn as areas or only points, are in one subgroup, "Seas, bays and straits".
* 6.7 Press Ctrl+F, type english channel, and press Enter on "English Channel, North Atlantic Ocean, sea, bay or strait". You hear "English Channel, North Atlantic Ocean. Zoom 500 kilometres." Press Shift+4. The heading is "Contains English Channel, 1 item, by name", and the one item is the heading "Seas, bays and straits 476", such as Alderney Race and Christchurch Bay. There are no rivers, roads, railways or towns. Possible fault: there are no islands either, though the plan says a sea contains bays, straits and islands. The Channel Islands are not listed.

## 7. Overlapping, Shift+5 (P3-T29e)

Zoom 25 kilometres, step 10 kilometres.

* 7.1 Go to 51.06,-1.31. Press Shift+5. The heading is "Overlapping Hampshire, 3 items, by name".
* 7.2 First come the areas of other layers that cover part of Hampshire, under a heading for each layer. There is one, "Islands 1", with "Burrow Island, 31 kilometres south-east, 1 percent of Hampshire and 24 percent of Burrow Island overlap". No sea is listed for Hampshire's coast. Great Britain is not listed: the build counts Hampshire as wholly inside Great Britain. Possible fault: Burrow Island is a tiny island in Portsmouth Harbour, far less than 1 percent of Hampshire, but a share of an area is never said as less than 1 percent.
* 7.3 Then the heading "Lines crossing its border 24". The M3 is there, "M3, crosses twice, nearest 48 kilometres north-east", and the River Itchen, "River Itchen, crosses once, nearest 14 kilometres south".
* 7.4 Press Right on the M3. Each crossing point is listed: "Crossing 1 of M3, 48 kilometres north-east" and "Crossing 2 of M3", the same distance and direction. Press Enter on one: you go there. Alt+Comma comes back. Possible fault: both crossings are at the same distance and direction, where the M3 goes into Surrey, so this may be one crossing counted twice.
* 7.5 The last heading is "Lines along its border 3": the River Avon, the River Test and the River Wey, such as "River Test, 14 kilometres west, along its border".
* 7.6 Press Shift+2 for Nearby, move to River Itchen and press Enter. Press Shift+5. The heading is "Overlapping River Itchen, 2 items, from its start". The items are the areas the river passes through, in order from its source: "Hampshire, you are inside, 88 percent of River Itchen is inside it", then "Southampton, 13 kilometres south, 12 percent of River Itchen is inside it". England is not listed, as it holds all of the river.
* 7.7 Press Shift+2, move to Winchester and press Enter. Press Shift+5. The heading is "Overlapping Winchester, no items", and under it "Nothing overlaps Winchester." A place is either inside an area or not.
* 7.8 Search for England with "Only Regions and constituent countries" and press Enter. Press Shift+5. The heading is "Overlapping England, 4 items, by name": Mountain ranges 4, Islands 3, Lines crossing its border 40, and Lines along its border 31. It opens in about half a second, even the first time. Tell me how long it feels.

## 8. Passed over, Shift+6 (P3-T29f)

Zoom 25 kilometres, step 10 kilometres.

* 8.1 Go to 51.063,-1.20, east of Winchester. Press Left once, to step 10 kilometres west through Winchester.
* 8.2 Press Shift+6. The heading is "Passed over, 6 items, along the path". The items come in the order the move met them, each with its distance and direction from where you are now: "A31, crossed, 8.3 kilometres east", "A272, Spitfire Link, crossed", "M3, crossed", "River Itchen, crossed", "Passed nearby to Winchester, closest 190 metres, 2.1 kilometres east", and "South West Main Line, crossed, 1.5 kilometres east".
* 8.3 Press Ctrl+S. The focus moves to the heading, and you hear it once: "Passed over, 6 items, by name". Ctrl+Shift+S goes back.
* 8.4 Is "Passed nearby to Winchester" clear?

## 9. Sorting, and hearing the order (P3-T29g)

* 9.1 Go to 51.06,-1.31. Press Shift+2, then Down to the first item.
* 9.2 Press Ctrl+S. The focus goes to the heading, and NVDA says it once: "Nearby, 8 items, clockwise from north". Listen for it being said twice; it should not be.
* 9.3 Press Ctrl+S again, with the focus on the heading. You hear "Nearby, 8 items, by name", once.
* 9.4 Press Ctrl+Shift+S. You hear "Nearby, 8 items, clockwise from north" again.
* 9.5 Is the order on the heading enough, or do you miss the old "Sorted by" message?

## 10. Search, Shift+7

* 10.1 Press Ctrl+F and type winchester. The first result is "Winchester, Virginia, United States, county of Virginia"; the second is "Winchester, England, United Kingdom, city or town". Press Enter on the second. Press Shift+7. The heading is "Search, 20 items, by name", with Winchester in it, such as "Winchester, England, United Kingdom, north-east". Possible fault: Winchester in England comes after a county of the same name in Virginia.
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
* 12.2 Tab through the dialog. There are buttons Add, Rename and Delete, then OK and Cancel. "Save the layers as a view" is no longer in the list.
* 12.3 Press Add, type My view, and press OK. You hear "Added the My view view. OK uses it."
* 12.4 With My view chosen, press Rename, type Test view and press OK. You hear "My view is now called Test view." Then press Delete. You hear "The Test view view is deleted. Cancel brings it back."
* 12.5 Move to Physical and press Enter. Enter is OK, the default: you hear "Physical view."
* 12.6 Press Ctrl+Shift+V, choose Political, and press Escape. Escape cancels, as Cancel does, so the Physical view stays. Press Ctrl+Shift+V again, choose Political and press OK: "Political view."

## 13. Exclaves said by their own names (P3-T28j)

Zoom 25 kilometres.

* 13.1 Go to 42.465,1.98, in Llívia. Space says "Girona, Catalonia, Spain, Llívia, exclave of Spain in France", then the mountain ranges.
* 13.2 Go to 47.697,8.69, in Büsingen. Space says "Near Schaffhausen. Landkreis Konstanz, Baden-Württemberg, Germany, Büsingen am Hochrhein, exclave of Germany in Switzerland, Europe".

## 14. Hierarchy mode (P3-T28m, P3-T28o, P3-T28n)

* 14.1 Go to 54,-2 and zoom out to 2,500 kilometres. Space says "United Kingdom, British Isles, Europe". Press Shift+3: the heading is "Bordering United Kingdom", not the British Isles, as the current feature is now the first area Space says.
* 14.2 Zoom in to 25 kilometres. Go to 50.72,-1.88, in Bournemouth. Press M: "Hierarchy mode. Bournemouth, Christchurch and Poole."
* 14.3 Press Right. You reach Hampshire at once: "Hampshire, north-east, shared border 19 kilometres. Zoom 100 kilometres." Press Enter. You hear "Left and Right now go round Hampshire." Before, it said "Nothing to go to".
* 14.4 Press Right a few times. You go round Hampshire's neighbours, each with its shared border and the zoom: "Borough of Wokingham, north-east, shared border 12 kilometres", then Bracknell Forest, then "Surrey, east, shared border 49 kilometres".
* 14.5 Press M: "Stepping mode."
* 14.6 Press Ctrl+F, type exmoor, and press Enter on "Exmoor, England, United Kingdom, mountain range". Press M, then Up. A list "Up from Exmoor" asks which, with England and Great Britain. Before, it said "Nothing holds Exmoor". Press Cancel.
* 14.7 Press Shift+5. The heading is "Overlapping Exmoor, 3 items, by name". Under "Counties 2" are Devon, "31 percent of Exmoor and 1 percent of Devon overlap", and Somerset, "you are inside, 69 percent of Exmoor and 2 percent of Somerset overlap", as each holds only part of Exmoor. There are also "Oceans and seas 1", the North Atlantic Ocean, and "Seas, bays and straits 1", the Bristol Channel, each "1 percent of Exmoor and 1 percent of" the sea: the range's shape reaches past the coast. Possible fault: Exmoor is far less than 1 percent of the North Atlantic Ocean. Press M to go back to stepping.
* 14.8 Press Ctrl+F, type english channel, and press Enter on it. Press M, then Down. It takes about 3 seconds. The list "Inside English Channel" has one kind, "Seas, bays and straits 476", and no Rivers, Motorways and trunk roads, Main railway lines or Cities and towns. Possible fault: there are no Islands either, as in 6.7. Press Cancel, then M.

## 15. The Moselle condominium (P3-T28f)

* 15.1 Press Ctrl+F, type moselle condominium and press Enter on it. Space says "Moselle condominium, shared by Germany and Luxembourg, Europe".
* 15.2 Press M, then Up. A list asks which to go up to, with Germany and Luxembourg. Press Cancel, then M.
* 15.3 Press W. Open Europe. The condominium is not among Europe's countries.
* 15.4 Open Germany. The condominium is listed under it. Close Germany and open Luxembourg: it is listed there too. Close the tree with Cancel.
* 15.5 Press Shift+3. The heading is "Bordering Moselle condominium, shared by Germany and Luxembourg, 4 items, clockwise from north". Germany and Luxembourg each have "shared border 130 kilometres, 50 percent". France has "shared border 80 metres, 1 percent", at Schengen, and Belgium "nearly touches, 0 metres across", where the condominium's river Our reaches Belgium. Possible fault: "0 metres across" is an odd way to say that they nearly touch.

## 16. Roads that are far apart, and Belfast (P3-T28d, P3-T21b)

* 16.1 Press Ctrl+F, choose "Only Motorways and trunk roads", and type m3. There are M3s in many countries, first Iran, Malawi and others. Two are in the United Kingdom, eighth and ninth in the list: "M3, Northern Ireland, United Kingdom, road" and "M3, England, United Kingdom, road".
* 16.2 Press Enter on the one in Northern Ireland. You hear "M3, Northern Ireland, United Kingdom. Zoom 1 kilometre." Press Space: "Near Belfast. Belfast City District, Northern Ireland, United Kingdom, Ireland, British Isles, Europe". Before, the two were one road, said "M3, United Kingdom".
* 16.3 Press M, then Up. You go straight to Belfast, with no list: "Belfast City District. Zoom 10 kilometres." The road is wholly inside Belfast City District, even where it crosses the River Lagan on a bridge. Press M.
* 16.4 Go to 54.68,-5.78, in Belfast Lough, at zoom 25 kilometres. Space says "Near Belfast. Sea of the Hebrides, North Atlantic Ocean". This is Natural Earth's own name: its Sea of the Hebrides includes the North Channel and Belfast Lough. Which would you like?
  * Option 1: rename this one area to "Inner Seas off the West Coast of Scotland".
  * Option 2: say the bay or strait you are in first, such as Belfast Lough.
  * Option 3: leave it as it is.

## 17. Bays on rivers (P3-T28c)

* 17.1 Press Ctrl+F and type hatch pool. There is no Hatch Pool among the results: the first are names that are near it, such as "Hatch, New Mexico, United States, city or town" and Hatch Cove in Maine. The fishing pools on the River Test are no longer in the pack.
* 17.2 Type poole harbour instead. The first result is "Poole Harbour, English Channel, sea, bay or strait": bays at the coast and on lakes are kept.

## 18. Key maps and your keys (P3-T31)

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
* 19.4 Press Shift+7. The countries are in the river's order: Switzerland, Liechtenstein, Austria, Germany, France, Netherlands.
* 19.5 Is this way of choosing the feature better than before? Last time you found pressing Cancel to keep the search unclear.

## 20. Layer sounds (P3-T11b, SON-3, SON-4, SCP-7)

Section 20 of the Phase 3 checklist, now on the world pack. You passed it on the trial pack.

* 20.1 Go to 51.06,-1.31, at zoom 25 kilometres. Press Shift+2 for Nearby, and press Space on River Itchen, Winchester, M3 and South West Main Line. Each plays a different sound from its direction: river, road, railway and town. The sounds are placeholders.
* 20.2 Press L. Each item plays its own layer's sound as it is said.
* 20.3 Press Ctrl+Comma, and go to the Earcons tab. The list has ten layer sounds: Continent, Country, Region or county, Water, River, Road, Railway, City or town, Mountain range or region, and Peak. Each can be switched off, have its volume changed, or use your own file. Press Cancel.
* 20.4 Press Ctrl+Shift+L, move to Rivers, and press "Settings for this layer". There is a list "Sound of this layer's features in look around and Hear its direction", with "No sound" first. Choose another sound, press OK, then OK. Space on River Itchen in Nearby plays the sound you chose. Set it back.
* 20.5 Can you tell the layers apart by sound? Which would you change?

## 21. Overall

* 21.1 For a line, Overlapping lists areas with less than 1 percent of it inside, said "less than 1 percent of ... is inside it". Search for thames with "Only Rivers". The first result is "Thames River, Ontario, Canada, river"; press Enter on the second, "River Thames, United Kingdom, river", then Shift+5. The heading is "Overlapping River Thames, 77 items, from its start". 46 of the 77 are under 1 percent, and 40 of those are small islands. Should items under 1 percent be left out?
* 21.2 Tell me anything else that sounds wrong, slow or unclear.

## Finishing

Send me your notes in docs/checklists/phase-3-tidy-up-2-desktop-results.txt. Then the web and sighted checklists are brought up to date from this one, P3-T22b.
