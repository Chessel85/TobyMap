# Phase 3 tidy-up 2 checklist: desktop version, world pack

This is a short third pass of the desktop checklist, for you to work through with NVDA on Windows 11. It covers only what changed in the second tidy-up plan (docs/plan/phase-3-tidy-up-plan2.md): the fixes and changes of P3-T28, the Information panel group by group as now defined (P3-T29), key maps (P3-T31), and the layer sounds, section 20 of the Phase 3 checklist.

It uses the world pack built on 20 November 2026. That pack has every change that needs a build, except the coast as a border (P3-T30b), which waits for your answers to the coast report.

For each step, write down its number, such as 4.3, and either "works" or what you heard instead. Put your notes in a text file next to this one, docs/checklists/phase-3-tidy-up-2-desktop-results.txt, as before. Lines starting with ">" are fine for answers to questions.

The expected words below come from the templates and the approved wording in the tests, and from the checks on the Western Europe trial pack. The world pack was still being built when this was written, so lengths, counts and distances are given as "about" or "such as" where I could not hear them myself. If the words differ only in a number, say so, but it is not a fault unless the number seems wrong.

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
* 1.6 Only Space names the town. Step once with Right: the place said after the step has no "Near".
* 1.7 How near counts as near: a town's reach grows with its population, from 2 kilometres up to 30. Romsey reaches 3 kilometres, Winchester 4.7, Southampton 13, and London 30. Villages and suburbs are never named. Do these distances feel right?
* 1.8 Go to 51.06,-1.31. Press Page Up twice, to 100 kilometres. Each time you hear only the zoom, such as "Zoom 50 kilometres.", as the place is the same.
* 1.9 Press Page Up once more, to 250 kilometres. You hear "Zoom 250 kilometres." followed by the place, starting with England: counties are not said at this zoom, so what Space would say has changed.
* 1.10 Press Page Down. You hear "Zoom 100 kilometres." and the place again, starting with Hampshire.

## 2. Stand-in areas (P3-T28a)

Zoom 25 kilometres, step 10 kilometres.

* 2.1 Go to 55.76,-6.28, on Islay. Space starts "Argyll and Bute, Scotland, United Kingdom", with Islay later in the list. Before, it said "Scotland" as if it were a county.
* 2.2 Press L, then Shift+2 for Nearby. Neither has "Scotland, 6 kilometres east" any more. Jura is in Nearby.
* 2.3 Go to 50.72,-1.88, in Bournemouth. Press Shift+3 for Bordering. The neighbours are Hampshire and Dorset, with no "England".

## 3. Within, Shift+1 (P3-T29h)

Zoom 25 kilometres, step 10 kilometres.

* 3.1 Go to 51.06,-1.31. Press Shift+1. The heading is "Within, 6 items, smallest first". The items are Hampshire, England, United Kingdom, Great Britain, British Isles and Europe, each with its centre, such as "Hampshire, centre 31 kilometres north-east".
* 3.2 Press Shift+2 for Nearby, move to River Itchen and press Enter. You hear "River Itchen", then the place. River Itchen is now the current feature.
* 3.3 Press Shift+1. The first item is "River Itchen, here", then the areas as before. Before, a line or place was never in Within.
* 3.4 Press M for hierarchy mode, then Up. You go to the smallest area that holds all of the river. If a list opens asking which, England and Great Britain are in it: choose England. Press M to go back to stepping.

## 4. Nearby, Shift+2 (P3-T29b)

* 4.1 Go to 51.06,-1.31. Press Shift+2. The heading is "Nearby, 8 items, by distance". Winchester is among the items, a few hundred metres away.
* 4.2 Move to Winchester and press Enter. You hear "Winchester. Hampshire, England, United Kingdom, Great Britain, British Isles, Europe". You are now on Winchester's own point.
* 4.3 Press Shift+2. Winchester is not in Nearby, as you are at it, and the heading still says 8 items.
* 4.4 Press Shift+1. The first item of Within is "Winchester, here".

## 5. Bordering, Shift+3 (P3-T28b, P3-T28i, P3-T28r)

* 5.1 Go to 51.06,-1.31. Press Shift+3. The heading is "Bordering Hampshire", its count, then "clockwise from north".
* 5.2 Press Down through the neighbours. Each says its shared border and its share, such as "West Sussex, 30 kilometres east, shared border 60 kilometres, 12 percent". There is no "England". The Isle of Wight "nearly touches, 1.3 kilometres across".
* 5.3 The last item is a heading, "Coast", then the whole coast's length, about 186 kilometres, said rounded. Open it. It has only "English Channel", with its length of coast. The North Atlantic Ocean and the Sea of the Hebrides are not there any more.
* 5.4 Press Right on West Sussex. The ends of the shared border are listed clockwise from north, so "End of the border with West Sussex, where Surrey meets it", with its distance, comes before "End of the border with West Sussex, at the coast, English Channel".
* 5.5 Press Shift+1, move to England and press Shift+Enter. You hear "Current layer: Regions and constituent countries. England is the current feature."
* 5.6 Press Shift+3. Open England's Coast heading. It lists seas such as the North Sea, the English Channel and the Irish Sea, each with its length. There is no Sea of the Hebrides.

## 6. Contains, Shift+4 (P3-T29c, P3-T29d)

England is still the current feature from 5.5.

* 6.1 Press Shift+4. The heading is "Contains England", its count, then "by name". It opens in under a second.
* 6.2 Open "Counties". Hampshire says "Hampshire, you are inside", with no distance.
* 6.3 Press Shift+1, move to England and press Shift+Enter again. You hear "No current layer. The current feature is the smallest area here, Hampshire."
* 6.4 Press Shift+4: "Contains Hampshire", its count, "by name". It holds only what is wholly inside Hampshire, and only what is within 25 kilometres of you, measured to each feature's nearest point. Towns such as Winchester say a short distance to their point.
* 6.5 The M3 is not in Contains Hampshire, as it runs on into Surrey. Nor is the River Itchen, as its mouth is in Southampton. Both are now in Overlapping, section 7.
* 6.6 Bays and straits, whether drawn as areas or only points, are in one subgroup, "Seas, bays and straits".
* 6.7 Press Ctrl+F, type english channel, and press Enter on the English Channel. Press Shift+4. Contains has only water features and islands, such as islands and bays. There are no rivers, roads, railways or towns.

## 7. Overlapping, Shift+5 (P3-T29e)

Zoom 25 kilometres, step 10 kilometres.

* 7.1 Go to 51.06,-1.31. Press Shift+5. The heading is "Overlapping Hampshire", its count, "by name".
* 7.2 First come the areas of other layers that cover part of Hampshire, under a heading for each layer, such as "Islands", with items like "Great Britain, you are inside, 98 percent of Hampshire and 2 percent of Great Britain overlap". No sea is listed for Hampshire's coast.
* 7.3 Then the heading "Lines crossing its border", with its count. The M3 is there, such as "M3, crosses once, nearest 20 kilometres north-east". The River Itchen is there too.
* 7.4 Press Right on the M3. Each crossing point is listed, such as "Crossing 1 of M3", with its distance and direction. Press Enter on one: you go there. Alt+Comma comes back.
* 7.5 If there is a heading "Lines along its border", its items say "along its border".
* 7.6 Press Shift+2 for Nearby, move to River Itchen and press Enter. Press Shift+5. The heading is "Overlapping River Itchen", its count, "from its start". The items are the areas the river passes through, in order from its source, each with its share, such as "Hampshire, you are inside, 90 percent of River Itchen is inside it", then Southampton. England is not listed, as it holds all of the river.
* 7.7 Press Shift+2, move to Winchester and press Enter. Press Shift+5. It has no items: "Nothing overlaps Winchester." A place is either inside an area or not.
* 7.8 Search for England with "Only Regions and constituent countries" and press Enter. Press Shift+5. It opens within about 2 seconds the first time, and quickly after that. Tell me how long it feels.

## 8. Passed over, Shift+6 (P3-T29f)

Zoom 25 kilometres, step 10 kilometres.

* 8.1 Go to 51.063,-1.20, east of Winchester. Press Left once, to step 10 kilometres west through Winchester.
* 8.2 Press Shift+6. The heading is "Passed over", its count, "along the path". The items come in the order the move met them, such as "M3, crossed", "River Itchen, crossed", and "Passed nearby to Winchester, closest" and how close, each with its distance and direction from where you are now.
* 8.3 Press Ctrl+S. The focus moves to the heading, and you hear it once, now ending "by name". Ctrl+Shift+S goes back.
* 8.4 Is "Passed nearby to Winchester" clear?

## 9. Sorting, and hearing the order (P3-T29g)

* 9.1 Go to 51.06,-1.31. Press Shift+2, then Down to the first item.
* 9.2 Press Ctrl+S. The focus goes to the heading, and NVDA says it once: "Nearby, 8 items, clockwise from north". Listen for it being said twice; it should not be.
* 9.3 Press Ctrl+S again, with the focus on the heading. You hear "Nearby, 8 items, by name", once.
* 9.4 Press Ctrl+Shift+S. You hear "Nearby, 8 items, clockwise from north" again.
* 9.5 Is the order on the heading enough, or do you miss the old "Sorted by" message?

## 10. Search, Shift+7

* 10.1 Press Ctrl+F, type winchester and press Enter on Winchester. Press Shift+7. The heading is "Search", its count, "by name", with Winchester in it.
* 10.2 Press F1 on the map. The list has "Go to Passed over: Shift+6" and "Go to Search: Shift+7". Close it.

## 11. Details and Wikipedia (P3-T28g, P3-T28l)

Zoom 25 kilometres.

* 11.1 Go to 51.06,-1.31. Press F4 and read a line at a time. You hear:
  * Hampshire
  * Type: county of England
  * Part of: England
  * Location: then the coordinates, in your units
  * Area
  * Whole border: then its length, "of which land is", a length, "and coastline is", a length. The land and the coastline add up to the whole border, give or take the rounding.
  * Population, and Official name if Wikidata has one
  * Wikipedia article: Hampshire
  * Shape and name: OpenStreetMap, ODbL licence
* 11.2 There is no Elevation line: heights are now given for places only, such as peaks and towns.
* 11.3 Move to "Wikipedia article: Hampshire" and press Enter. You hear "Opening the Wikipedia article for Hampshire." and the article opens. Come back to TobyMap.
* 11.4 Press F2 for the map, then Ctrl+Alt+W. You hear "Opening the Wikipedia article for Hampshire." again, from the map. Try it from the Information panel too, with F3.
* 11.5 Press Shift+2, move to Winchester and press Enter. Press F4. If Wikidata has a height for Winchester, Details has an Elevation line.

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
* 13.2 Go to 47.697,8.69, in Büsingen. Space says "Landkreis Konstanz, Baden-Württemberg, Germany", then the exclave by its own name, such as "Büsingen am Hochrhein, exclave of Germany in Switzerland".

## 14. Hierarchy mode (P3-T28m, P3-T28o, P3-T28n)

* 14.1 Go to 54,-2 and zoom out to 2,500 kilometres. Space says "United Kingdom, British Isles, Europe". Press Shift+3: the heading is "Bordering United Kingdom", not the British Isles, as the current feature is now the first area Space says.
* 14.2 Zoom in to 25 kilometres. Go to 50.72,-1.88, in Bournemouth. Press M: "Hierarchy mode. Bournemouth, Christchurch and Poole."
* 14.3 Press Right until you reach Hampshire. Press Enter. You hear "Left and Right now go round Hampshire." Before, it said "Nothing to go to".
* 14.4 Press Right a few times. You go round Hampshire's neighbours, such as West Sussex and Surrey, and each says its shared border.
* 14.5 Press M: "Stepping mode."
* 14.6 Press Ctrl+F, type exmoor, and press Enter on Exmoor. Press M, then Up. You go to England, or a list "Up from Exmoor" asks which, with England in it. Before, it said "Nothing holds Exmoor". Press Cancel if the list opened.
* 14.7 Press Shift+5. Overlapping has Somerset and Devon, as each holds only part of Exmoor. Press M to go back to stepping.
* 14.8 Press Ctrl+F, type english channel, and press Enter on it. Press M, then Down. The list "Inside English Channel" has kinds such as Islands and Bays and straits, but no Rivers, Motorways and trunk roads, Main railway lines or Cities and towns. Press Cancel, then M.

## 15. The Moselle condominium (P3-T28f)

* 15.1 Press Ctrl+F, type moselle condominium and press Enter on it. Space says "Moselle condominium, shared by Germany and Luxembourg, Europe".
* 15.2 Press M, then Up. A list asks which to go up to, with Germany and Luxembourg. Press Cancel, then M.
* 15.3 Press W. Open Europe. The condominium is not among Europe's countries.
* 15.4 Open Germany. The condominium is listed under it. Close Germany and open Luxembourg: it is listed there too. Close the tree with Cancel.
* 15.5 Press Shift+3. The condominium's neighbours include Germany and Luxembourg.

## 16. Roads that are far apart, and Belfast (P3-T28d, P3-T21b)

* 16.1 Press Ctrl+F, choose "Only Motorways and trunk roads", and type m3. There are two M3s: one in England and one in Northern Ireland.
* 16.2 Press Enter on the one in Northern Ireland. You go to it, and the place said is in Belfast and Northern Ireland. Before, the two were one road, said "M3, United Kingdom".
* 16.3 Press M, then Up. You go to Belfast, or a list asks which, with Belfast in it: the road is wholly inside Belfast and Northern Ireland, even where it crosses the River Lagan on a bridge. Press Cancel if the list opened, then M.
* 16.4 Go to 54.68,-5.78, in Belfast Lough, at zoom 25 kilometres. Space says "Sea of the Hebrides". This is Natural Earth's own name: its Sea of the Hebrides includes the North Channel and Belfast Lough. Which would you like?
  * Option 1: rename this one area to "Inner Seas off the West Coast of Scotland".
  * Option 2: say the bay or strait you are in first, such as Belfast Lough.
  * Option 3: leave it as it is.

## 17. Bays on rivers (P3-T28c)

* 17.1 Press Ctrl+F and type hatch pool. You hear "Nothing found for hatch pool." The fishing pools on the River Test are no longer in the pack.
* 17.2 Type poole harbour instead. Poole Harbour is found: bays at the coast and on lakes are kept.

## 18. Key maps and your keys (P3-T31)

The words "key map", "your keys" and "key file" are in the glossary.

* 18.1 Press Ctrl+Comma for Settings and go to the Keys tab. There is a "Key map" list, set to "Windows desktop". Below it are the commands and their keys, and buttons "Save keys as", "Open key file" and "Reset keys".
* 18.2 In the Key map list, choose "Alternative". It is used at once, and you hear "Key map: Alternative." The list of commands shows Settings on Ctrl+Shift+X and Open the current feature's Wikipedia article on Alt+Shift+W. Alternative avoids Ctrl+Alt with a letter, which is AltGr on many European keyboards. Press OK.
* 18.3 Press Ctrl+Comma. Nothing opens. Press Ctrl+Shift+X: Settings opens. Go to the Keys tab.
* 18.4 Change the key of Heading to Ctrl+Q. You hear "Heading is now Ctrl+Q."
* 18.5 Press "Save keys as". Save the file in your Documents folder as tobymap-keys.json.
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
* 20.3 Press Ctrl+Comma, and go to the Earcons tab. The list has ten layer sounds, from Continent to Peak, such as River, Road and City or town. Each can be switched off, have its volume changed, or use your own file. Press Cancel.
* 20.4 Press Ctrl+Shift+L, move to Rivers, and press "Settings for this layer". There is a list "Sound of this layer's features in look around and Hear its direction", with "No sound" first. Choose another sound, press OK, then OK. Space on River Itchen in Nearby plays the sound you chose. Set it back.
* 20.5 Can you tell the layers apart by sound? Which would you change?

## 21. Overall

* 21.1 For a line, Overlapping lists areas with less than 1 percent of it inside, said "less than 1 percent of ... is inside it". For the Thames, about 70 of its 77 items are small islands. Search for the Thames with "Only Rivers", press Enter, then Shift+5. Should items under 1 percent be left out?
* 21.2 Tell me anything else that sounds wrong, slow or unclear.

## Finishing

Send me your notes in docs/checklists/phase-3-tidy-up-2-desktop-results.txt. Then the web and sighted checklists are brought up to date from this one, P3-T22b.
