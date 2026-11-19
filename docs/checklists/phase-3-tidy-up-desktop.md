# Phase 3 tidy-up checklist: desktop version, Western Europe trial pack

This is a short second pass of the desktop checklist, for you to work through with NVDA on Windows 11. It covers only what changed in the Phase 3 tidy-up (docs/plan/phase-3-tidy-up.md): the fixes of P3-T19, the speed work of P3-T20, map views (P3-T23), borders, shores, the current layer and enclaves (P3-T24), hierarchy mode's Down lists (P3-T25), disputed and odd areas (P3-T26), and the layer sounds, section 20 of the first checklist.

It uses the Western Europe trial pack built on 17 November 2026, not the world pack. That pack has every change that needs a build, except the distant parts, which wait for the world build.

For each step, write down its number, such as 4.3, and either "works" or what you heard instead. Put your notes in a text file, as before.

The expected words below were taken from the core running on the trial pack on 18 November 2026.

## How to start TobyMap

* Open a terminal in the repository folder and run:

  `.venv\Scripts\python.exe -m desktop --pack E:\osmdata\tobymap\output\trial-western-europe\trial-western-europe.pack --at 51.06,-1.31`

* "Start with 46.8,8.2" below means: close TobyMap, then run the same line with `--at 46.8,8.2` at the end. Up Arrow in the terminal brings back the last line to change.
* Each section gives the zoom and step it needs. Page Up and Page Down change the zoom; Shift+Page Up and Shift+Page Down change the step.

## Before you start

* In Settings, Units: Distances Metric, Directions Compass with 8 points.
* In Settings, Speech: Names "English where there is one". Leave "Show where each fact in Details comes from" and "Say the direction in look around" on, as they start.
* The verbosity preset is Normal and the orientation north-fixed. H says both, and "Stepping."
* In Map views, Ctrl+Shift+V, the Political view is in use.

## What the trial pack holds

* Western Europe and the Alps, from 11 degrees west to 17 degrees east, and from 35 to 61 degrees north. Anything outside is cut off at that edge.
* It has no distant-parts stage, so Ceuta and Melilla are still in Africa only by the continent lines, and the Canary Islands and Hawaii are not in it. P3-T19h, Ceuta and Melilla as distant parts, is checked on the world build.

## Things I already know about

You don't need to report these.

* The whole border in Details is wrong where an area has coast. Hampshire says "Whole border: 560 kilometres, of which land 370 kilometres and coast 370 kilometres", and Spain's coast is longer than its whole border. The coast seems to be counted in a different way from the whole border. I'll fix it before the world build.
* Spain's official name in Details is in Basque, "Espainiako Erresuma". Wikidata gives it in several languages, and the wrong one is chosen. I'll fix it.
* Germany's 5 exclaves beside Belgium, on the Vennbahn railway, are each "Exclave of Germany", and one Spanish rock beside Morocco is "Exclave of Spain". They can be named by hand in the build settings, as Llívia is.
* In Switzerland in the world tree, Basel-Landschaft has nothing under it, and its five districts, such as Bezirk Liestal, are listed beside the cantons. I'll look at why.
* Hampshire's Bordering list has "England, shared border 1.6 kilometres": a sliver of England that is in no county. I'll look at it.
* At Ceuta you hear "Ceuta, Spain, Unnamed island, Africa". The trial cuts Africa off at 35 degrees north, so the bit of Africa left is an island. This is the trial's edge, not a fault.
* Down from Europe says "Islands: 18 shown at this zoom, 36,089 in all". DP208 asks you whether "directly in Europe" is wanted instead.

## 1. Where you are, in the map view's order (P3-T23, DP198)

Zoom and step 25 kilometres.

* 1.1 Start with 51.06,-1.31, in Winchester. You hear "TobyMap. Hampshire, England, United Kingdom, Great Britain, British Isles, Europe. Press F1 for keys." The country now comes before the island.
* 1.2 Start with 50.69,-1.30. You hear "Isle of Wight, England, United Kingdom, British Isles, Europe". The Isle of Wight is said once now, not twice.
* 1.3 Start with 46.45,6.55. You hear "Lake Geneva, Upper Savoy, Auvergne-Rhône-Alpes, France, Europe". The lake is still first.
* 1.4 Start with 46.0,7.75, near Zermatt. You hear "Visp, Valais/Wallis, Switzerland, Pennine Alps, Northwestern Alps, Western Alps, Alps, Europe". The mountain ranges now come after the country.

## 2. Map views (P3-T23, DP198)

Same place, near Zermatt.

* 2.1 Press Ctrl+Shift+V. The Map views list has "Political, in use", "Physical" and "Save the layers as a view", with a line saying what a view is, and a Cancel button.
* 2.2 Choose Physical. You hear "Physical view." Press Space: "Pennine Alps, Northwestern Alps, Western Alps, Alps, Visp, Valais/Wallis, Switzerland, Europe". The mountain ranges now come first.
* 2.3 Start with 51.06,-1.31. In the Physical view, Space says "Great Britain, British Isles, Hampshire, England, United Kingdom, Europe".
* 2.4 Press Ctrl+Shift+V, choose "Save the layers as a view", type a name, such as My view, and press OK. It is in the list. Rename it, then delete it. Each has OK and Cancel, and nothing needs Escape.
* 2.5 Choose Political again. You hear "Political view."
* 2.6 Ctrl+Shift+L, then a layer's settings, has "Draw the outlines of its areas". "Draw the borders of regions" is gone. This is for a sighted helper to check on the map.

## 3. Enclaves and exclaves (P3-T24g, DP207)

Zoom and step 25 kilometres.

* 3.1 Start with 42.465,1.98, in Llívia. You hear "Girona, Catalonia, Spain, exclave in France, Carlit Massif, Northeastern Pyrenees, Eastern Pyrenees, Pyrenees, Europe".
* 3.2 Start with 47.697,8.69, in Büsingen. You hear "Landkreis Konstanz, Baden-Württemberg, Germany, exclave in Switzerland, Europe".
* 3.3 Start with 45.969,8.971, in Campione d'Italia: "Como, Lombardy, Italy, exclave in Switzerland", then the mountain ranges.
* 3.4 Start with 47.574,10.444, in Jungholz: "Bezirk Reutte, Tyrol, Austria, exclave in Germany", then the mountain ranges.
* 3.5 Start with 51.44,4.93, in Baarle: "Antwerp, Flanders, Belgium, exclave in Netherlands, North European Plain, Europe".
* 3.6 Press Ctrl+F, type switzerland, choose "Only Countries", press Down to the result and Enter. You hear "Switzerland, Europe. Zoom 250 kilometres." Press F4. Details has "Contains enclaves: Campione d'Italia, Italy, Büsingen am Hochrhein, Germany".
* 3.7 Search for Spain in the same way. Details has "Exclaves: Ceuta, Exclave of Spain, Melilla, Llívia".
* 3.8 Is "exclave in France" clear, or would you like the exclave's own name said too, such as "Llívia, exclave of Spain in France"?

## 4. Details (P3-T19d, P3-T19j, P3-T24f)

* 4.1 Start with 48.14,11.58, in Munich, zoom 25 kilometres. Press F4 and read a line at a time:
  * Munich
  * Type: urban municipality of Bavaria
  * Part of: Bavaria
  * Area: 310 square kilometres
  * Whole border: 110 kilometres, all on land
  * Population: 1,505,036, Wikidata, 31 December 2025
  * Elevation: 519 metres, Wikidata, 13 November 2026
  * Official name: München, Wikidata, 13 November 2026
  * Wikipedia article: Munich
  * Source: OpenStreetMap planet file, as a GeoDesk library, ODbL 1.0

  The sources are shorter, "Area, as published" is gone, and "Whole border" is new.
* 4.2 In Settings, Speech, switch off "Show where each fact in Details comes from" and press OK. Details now says "Population: 1,505,036", "Elevation: 519 metres" and "Official name: München", with no source. The last line, Source, stays. Switch it on again, or leave it off if you prefer.
* 4.3 Start with 51.06,-1.31. In Details, press W. You hear "Opening the Wikipedia article for Hampshire." and the article opens. Before, there was none.

## 5. The Information panel's headings and items (P3-T19c, P3-T20)

Start with 46.8,8.2, zoom 1,000 kilometres, step 100 kilometres. You are in Obwalden.

* 5.1 Press Shift+4. The focus lands on the heading, and you hear "Contains Obwalden, 6 items". The first time it takes about 3 seconds on this pack; before the speed work it took 10. Tell me how long it feels.
* 5.2 Press Down to "Peaks 119" and Right to open it. Each peak says its distance and direction, such as "Abgschütz, 3.4 kilometres south-east".
* 5.3 Press Shift+5, Shift+6 and Shift+7. Each lands on its heading with its count: "Bordering Obwalden, 4 items", "Overlapping Obwalden, 2 items", "Crossing Obwalden, 2 items".

## 6. Borders: the share, the ends and the crossings (P3-T24f, DP201)

Same place.

* 6.1 Press Shift+5, then Down. The first item is "Nidwalden, 18 kilometres north-east, shared border 69 kilometres, 42 percent". The four neighbours' shares add up to 100 percent.
* 6.2 Press Right on Nidwalden. It opens to the ends of the shared border, such as "End of the border with Nidwalden, where Lucerne meets it, 19 kilometres north". There are four ends, as the border is in two parts.
* 6.3 Press Enter on an end. You go there, and hear the place. Alt+Comma comes back.
* 6.4 Press Shift+7, then Down. The items are "A8, crosses once, nearest 21 kilometres north" and "Kleine Emme, crosses once, nearest 10 kilometres west". Press Right on A8: "Crossing 1 of A8, 21 kilometres north".
* 6.5 Press F4. Details for Obwalden has "Whole border: 160 kilometres, all on land".

## 7. Shores, coast and Overlapping by kind (P3-T24e, DP200)

* 7.1 Start with 46.8,8.2, zoom 1,000 kilometres. Press Shift+6. Overlapping has headings by kind: "Mountain ranges 2" and "Lakes 1". Under Mountain ranges: "Swiss Prealps, 340 metres north, 90 percent of Obwalden and 7 percent of Swiss Prealps overlap".
* 7.2 Start with 51.06,-1.31, zoom 100 kilometres, step 10 kilometres. Press Shift+5: "Bordering Hampshire, 13 items". The Isle of Wight is "Isle of Wight, 43 kilometres south, nearly touches, 1.3 kilometres across". The last item is a Coast heading.
* 7.3 Press Ctrl+F, choose "Only Lakes", type lake geneva and press Enter on Lake Geneva. You hear "Lake Geneva, Switzerland, France. Zoom 50 kilometres." Press Shift+5. Bordering has "Shores, Countries 2", "Shores, Regions and constituent countries 4" and "Shores, Counties 20".
* 7.4 Search for Germany with "Only Countries" and press Shift+5: "Bordering Germany, 11 items". Among them is "Moselle condominium, shared by Germany and Luxembourg", and the last is "Coast 5".

## 8. Enter makes the item the current feature (P3-T19a, P3-T19b)

* 8.1 Start with 51.06,-1.31, zoom 100 kilometres. Press Shift+2 for Nearby, move to Winchester and press Enter. You hear "Winchester. Hampshire, England, United Kingdom, Great Britain, British Isles, Europe": its name first, then the place.
* 8.2 Press F4. Details is about Winchester.
* 8.3 Start with 46.8,8.2, zoom 1,000 kilometres. Press Shift+5, move to Nidwalden and press Enter. You hear "Nidwalden, Switzerland, Swiss Prealps, Northwestern Alps, Western Alps, Alps, Europe".
* 8.4 Press Shift+5 again: "Bordering Nidwalden, 5 items". The groups are about Nidwalden now. Press F4: Details is about Nidwalden.

## 9. The current layer (P3-T24b, DP202)

Start with 51.06,-1.31, zoom 100 kilometres, step 10 kilometres.

* 9.1 Press Shift+1 for Within, move to Great Britain and press Shift+Enter. You hear "Current layer: Islands. Great Britain is the current feature."
* 9.2 Press Right to step east. Press F4: Details is still about Great Britain, as you are still on it. Space still says "Hampshire, England, ...": the current layer does not change what "where am I" says.
* 9.3 In Within, press Shift+Enter on Hampshire. You hear "Current layer: Counties. Hampshire is the current feature." Press Shift+Enter on Hampshire once more: "No current layer. The current feature is the smallest area here, Hampshire."
* 9.4 Press Shift+2 for Nearby and Shift+Enter on River Itchen. You hear "Current layer: Rivers. Rivers: none here, so the current feature is the smallest area, Hampshire." You are 170 metres from the river, not on it.
* 9.5 Is the current layer useful, and is what you hear clear?

## 10. What hierarchy mode's Down lists count (P3-T25, DP204, DP208)

* 10.1 Search for Switzerland with "Only Countries" and press Enter. Press M: "Hierarchy mode. Switzerland."
* 10.2 Press Down. The list "Inside Switzerland" opens in about a second. Its lines say what they count, such as "Mountain ranges: 13 shown at this zoom, 16 in all", "Counties: 275 shown at this zoom, 359 in all", and "Lakes 17" where all are shown.
* 10.3 Choose Lakes. The list "Lakes in Switzerland" has "Lago di Lugano, partly in Switzerland, 100 kilometres south-east", "Lake Constance, partly in Switzerland", "Lake Geneva, partly in Switzerland" and "Lake Maggiore, partly in Switzerland". Press Cancel.
* 10.4 Search for Europe and press Enter. Press Down. "Inside Europe" opens in about 2 seconds, with "Countries: 23 shown at this zoom, 35 in all" first, and "Islands: 18 shown at this zoom, 36,089 in all". Press Cancel, then M to go back to stepping.

## 11. The world tree (P3-T19e, P3-T20c, P3-T26a, P3-T26b)

Start with 51.06,-1.31.

* 11.1 Press W. Move to "Europe, continent" and press Right. It opens at once, with no wait. The first country is "Andorra, country".
* 11.2 Move to "Gibraltar, country" and to "Vatican City, country". NVDA does not say "collapsed": they have nothing under them. Switzerland does say "collapsed".
* 11.3 Open Switzerland. Its cantons are listed at once, from "Aargau, canton of Switzerland". Basel-Landschaft's districts are the fault noted above.
* 11.4 "Moselle condominium, shared by Germany and Luxembourg, condominium" is among Europe's countries.
* 11.5 Move to Obwalden, then close the tree with Cancel. Press W again. The tree opens with Europe and Switzerland open, and the focus on Obwalden.
* 11.6 Open "Disputed areas" at the end of the tree. It has three items: "Land claimed by France and Italy, disputed land, claimed by France, Italy", then Germany and Netherlands, then Morocco and Spain. On the world pack the disputes are grouped by name, such as Kashmir; this pack's three have no name from Natural Earth, so each is an area of its own.
* 11.7 Open "Unclaimed areas". You hear "No unclaimed areas are stored." The one in this pack was under 1 square kilometre, so it is left out.
* 11.8 Close the tree with Cancel.

## 12. Listing every feature of a kind, and the query builder (P3-T19j, P3-T25b)

* 12.1 Search for Switzerland with "Only Countries" and press Enter. Press Ctrl+Shift+F. The list "Inside Switzerland" says "Lakes 17", and choosing it says "Lakes: 17 inside Switzerland, in the Search group." The two counts now agree; before, they were 13 and 17.
* 12.2 Press Shift+8. "Search, 17 items", with "Lago di Lugano, partly in Switzerland, south-east" first, then "Lake Bienne, west".
* 12.3 Press Ctrl+F, choose "Only Rivers", type rhine, and press Cancel, so the Rhine stays in the Search group. Press Q. Choose Countries, crossing, and "Rhine, Germany, Netherlands, Switzerland, from the Search group". You hear "Countries crossed by Rhine: 6, in the Search group."
* 12.4 Press Shift+8. The countries are in the river's order now: Switzerland, Liechtenstein, Austria, Germany, France, Netherlands.

## 13. The Moselle condominium (P3-T26c, P3-T19g)

* 13.1 Press Ctrl+F and type moselle condominium. The result is "Moselle condominium, shared by Germany and Luxembourg, Europe, condominium".
* 13.2 Press Enter. You hear "Moselle condominium, shared by Germany and Luxembourg, Europe. Zoom 50 kilometres." Before, Enter on it did nothing.
* 13.3 Space says "Moselle condominium, shared by Germany and Luxembourg, Europe". Details says "Type: condominium" and "Area: 7 square kilometres".

## 14. Look around says the direction (P3-T19f)

Start with 51.06,-1.31, zoom 100 kilometres. Use headphones.

* 14.1 Press L. Each label now says its direction: "A34, north-east, 1.7 kilometres", then "River Itchen, east, 170 metres", and so on to "Winchester, north-west, 260 metres".
* 14.2 Does the direction you hear in the words match where the voice comes from?
* 14.3 In Settings, Speech, "Say the direction in look around" switches it off. Leave it as you like it.

## 15. Speed, and the map never holding up speech (P3-T20, P3-T24a)

* 15.1 Start with 46.8,8.2, zoom 1,000 kilometres. Search for Switzerland and press Enter. Press M, then Up, choosing from the list if one opens, until you reach Europe. Then press Alt+Comma to go back. Each is said within about 2 seconds, with no silence of 10 to 15 seconds as before. Press M to go back to stepping.
* 15.2 Switch on every layer in Ctrl+Shift+L, zoom out to 2,500 kilometres, and hold Right for two seconds. It still clicks, and the place is said when you let go, even if the map is still drawing. After 2 seconds of drawing you may hear "Still drawing the map".
* 15.3 Stop on a place and press Shift+3 for Crossed and passed, then step again at once. Tell me if a key ever waits. The Information panel's Nearby list is worked out after each move; on the world pack this held a key for up to 0.4 seconds. P3-T20d, waiting for your agreement, would fix that.
* 15.4 Switch the layers back to how they were.

## 16. Layer sounds (P3-T11b, SON-3, SON-4, SCP-7)

These were section 20 of the first checklist, which waited for a build with the layer sounds.

* 16.1 Start with 51.06,-1.31, zoom 100 kilometres. Press Shift+2 for Nearby, and press Space on River Itchen, Winchester, M3 and South West Main Line. Each plays a different sound: river, town, road and railway. The sounds are placeholders.
* 16.2 Press L. Each item plays its own layer's sound.
* 16.3 Open Settings, Earcons. The list has the layer sounds, from layer_continent to layer_peak. Each can be switched off, have its volume changed, or use your own file.
* 16.4 Press Ctrl+Shift+L, move to Rivers, and press "Settings for this layer". There is a list "Sound of this layer's features in look around and Hear its direction", with "No sound" first. Choose another sound, press OK, then OK. Space on River Itchen plays the sound you chose. Set it back.
* 16.5 Can you tell the layers apart by sound? Which would you change?

## 17. Overall

* 17.1 Tell me anything else that sounds wrong, slow or unclear.

## Finishing

Send me your notes. The fixes from them, and those in "Things I already know about", go in before the world build, P3-T21b. Then the web and sighted checklists, P3-T22b.
