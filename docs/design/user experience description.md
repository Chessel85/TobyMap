# User Experience Description

Version 0.22, 10 November 2026. The special lines are drawn thicker and in a colour of their own, and a setting in the Display tab chooses when the current area is outlined (section 11.2; P2-T17v). Version 0.21, 10 November 2026. A switch in the Speech tab says the place after every step, even when it has not changed, instead of the tick (section 3.1; P2-T17q, DP162). Version 0.20, 10 November 2026. Your notes on the Phase 2 sweep (P2-T18): Space and Enter on a group heading in the Information panel say and do nothing (section 6.3); the layers list is a tree whose groups close and open, and the maximum zoom is the closest (section 7.1); an item under a metre away is "here", and a line you are on is not nearby (section 6); the beacon can come from either pole or the equator (section 8.4); and Reset all settings is in the Map menu (section 13). Version 0.19, 10 November 2026. The announcement history is now the location history: the places you stopped at, which Alt+Comma and Alt+Full stop go through, as a list (sections 2, 8.5 and 12; P2-T17t, DP158). Version 0.18: section 5.1 now says that directions are compass directions in every orientation unless you ask for them from the way you face, said with "at your" (P2-T17s, DP159). Section 5.7 has forward and back in Go to (P2-T17r, DP161). Version 0.17: section 8.6 now describes the simpler Earcons tab: one list with a check box for each earcon, and below it the chosen earcon's own volume and file. There is no volume for all the earcons together, and the beacon's own file is in the Sound tab (P2-T17p, DP163). Version 0.16: section 2 now says that a wrong entry in Type a bearing or Go to opens a message box, and that the bearing box has only its label (P2-T17o). Version 0.15: section 12 has the rule that Shift goes the other way round a list, with Shift+O and Shift+A (P2-T17l). Version 0.14: section 6 says what the Information panel does in Phase 2: counts on the group headings, Within's distances, Enter to go to an item, and Go to and Type a bearing from the panel and Details (P2-T17k).

This document describes what using the application is like: what the user does, what they hear, what they see, and why. It does not cover how the application is built. Requirement IDs, such as NAV-3, refer to "requirements catalogue.md". Points that need a decision from you are marked "Decision needed" and cross-referenced to the discussion points file.

Examples of what the user hears are written as quoted speech. "(tick)" and other words in brackets are earcons, which are short sounds rather than speech. Street names, distances and other figures in the examples are made up for illustration.

Note: "user experience description.html" is now out of date. This Markdown file is the current version.

## Changes in version 0.22

Made in P2-T17v, from your notes of 10 November 2026.

* Section 11.2: the special lines (the equator, the prime meridian, the tropics, the polar circles and the date line) are drawn thicker than the other lines and in a colour of their own, in every theme, keeping 7 to 1 in the high contrast themes.
* Section 11.2: a new setting in the Display tab, "Outline the current area": always (at first), not for the oceans, never for oceans and seas, or never. An ocean's outline can run across open water, such as the North Atlantic's edge from Norway to Iceland.

## Changes in version 0.21

Made in P2-T17q, from the answer to DP162.

* Section 3.1: a new switch in the Speech tab, "Say the place after every step, even when it has not changed", off at first. It is outside the presets, so changing it never makes the preset Custom.
* With it on, a step that changed nothing says the place instead of the tick. How much follows "After a step": in terse, the smallest area, such as "Kent"; in normal, the smallest area and its country, such as "Kent, United Kingdom"; in detailed, the whole place, such as "Kent, England, United Kingdom". With "Say nothing, only the tick", it still only ticks.
* A held key still clicks on each step, and only the place where you let go is said.

## Changes in version 0.19

Made in P2-T17t, from the answer to DP158.

* Section 12: Ctrl+Shift+Space opens the location history, not the announcement history. It lists the places you stopped at, newest first: the places Alt+Comma and Alt+Full stop go through. Where you are now is marked "Here" and chosen as the list opens. Enter on a place goes there as Alt+Comma or Alt+Full stop would, so no place is added and the way forward is kept.
* A place whose areas are all in layers not shown, switched off or outside their zoom range, is left out of the list, and Alt+Comma and Alt+Full stop pass over it. It is kept, and comes back when the layer is shown again.
* Sections 2 and 8.5: what is said is not kept in a list any more. Shift+Space still repeats the last thing said, including a spoken label.

## Changes in version 0.18

Made in P2-T17r and P2-T17s, from the answers to DP159 and DP161.

* Section 5.1: in cardinal and free facing, directions are said as in north-fixed, unless the setting "In cardinal and free facing, give directions from the way you face" is on, in the Units tab. Then they are in your chosen format, with "at your": "at your north-east", "at your 2 o'clock", "at your 30 degrees".
* Section 5.7: Go to takes forward and back with a distance, in cardinal and free facing.

## Changes in version 0.17

Made in P2-T17p, from the PO's note on desktop checklist 10.6 and the answer to DP163.

* Section 8.6: the Earcons tab is one list of every earcon, each with a check box to play it or not. Below the list is one set of controls, for the earcon chosen in the list: its own volume, your own file, Choose file and Use the default.
* Section 8.6: each earcon has its own volume. The one volume for all the earcons is gone (DP163). A volume saved before becomes each earcon's own volume.
* Sections 8.4 and 8.6: the orientation beacon is not in the Earcons tab's list. Its own file is now in the Sound tab, with its switch, its volume and its other settings.

## Changes in version 0.16

Made in P2-T17o, from the PO's notes on desktop checklist 3.5 and 5.3.

* Section 2: the bearing box's label is only "Enter a bearing in degrees, or a compass direction:", with no help line.
* Section 2: a wrong entry in Type a bearing or Go to opens a message box with an OK button, which names the entry and says what is accepted. After OK, you are back in the box with your text. Before, the words appeared in the box itself.

## Changes in version 0.15

Made in P2-T17l, from the PO's note on desktop checklist 4.4 and in other thoughts.

* Section 12: a rule, that every key that goes round a list goes back with Shift. Shift+O goes back through the orientations, and Shift+A through the verbosity presets. Shift+T already did this for themes.
* Sections 3.1, 5.1 and 12: the orientation key is O, as built, not F.
* Section 12: in every number box, Home sets the largest value and End the smallest (P2-T17m).

## Changes in version 0.14

Made in P2-T17k, from the PO's notes on desktop checklist 10.4, 10.5, 11.5 and 11.7.

* Section 6.1: each group heading says how many items it holds, such as "Nearby, 5 items". Each Within item says the distance and direction to the area's centre, such as "England, centre 140 kilometres west".
* Section 6.3: Enter on an item goes there, at once, rather than opening a list of actions (DP155). Space hears its direction. The focus stays in the panel.
* Section 2: Go to coordinates (Ctrl+G) and Type a bearing (Ctrl+B) work from the Information panel and Details too, and the focus goes back there afterwards.

## Changes in version 0.12

Made in P2-T17c and P2-T17d.

* Section 2: as a dialog closes, the screen reader says once what the dialog's answer said, such as the new place after Go to, or else the place after the dialog's changes.
* Section 2: at the start, the screen reader says the window's title, TobyMap, then the place and "Press F1 for keys", as the map's name.

## Changes in version 0.11

Made in P2-T11, P2-T12 and P2-T13.

* Section 3.1: the verbosity presets, terse, normal and detailed, and their four switches (DP144). A, on the map, goes to the next preset.
* Section 11.2: the four themes, with T and Shift+T; the map display setting (DP108); Isolate, Ctrl+I; names on the map with the label size; heading-up; and how magnifiers follow the map centre (DP146).
* Section 12: the keys A, T, Shift+T and Ctrl+I.
* Section 13: the Speech tab and the Display tab as built. The short Braille format is parked (DP145).

## Changes in version 0.10

Made in P2-T9, the orientation beacon.

* Section 8.4: the beacon sounds about once a second, a setting, with the lower pitch behind you. It has its own volume, not the earcon volume. It fades from 200 km and is silent within 100 km of the North Pole; you are told once when it goes silent and when it comes back. Its sound is in the Earcons tab for your own file, with no second switch, because B is its switch. Until pins come in Phase 4, the North Pole is its only target.
* Section 8.6: the beacon has its own volume now.

## Changes in version 0.9

Made in P2-T8, earcons in full.

* Section 8.6: each earcon has its own switch and your own file, in the Earcons tab of Settings, with one volume for all the earcons. The spatial voice has its own volume, and the beacon will have its own. Ctrl+M silences them all. In the web version, Choose file keeps the file you pick in the browser's storage (DP123).

## Changes in version 0.8

Made in P2-T7, the spatial voice.

* Section 8.5: in Phase 2, "hear its direction" is Space on an item of Nearby or Crossed and passed, your key from the key list (DP143). The item's sound plays first, then its name and distance in the spatial voice, from the same place, such as "France, 34 kilometres". The web version has no Braille-only route, so there the label reaches the screen reader only if "also speak spatial labels" is on.

## Changes in version 0.7

These bring the sound sections into line with what you chose after the Phase 1 listening test. Made in P2-T6.

* Section 8.2: stereo with a lower pitch behind is the default, and HRTF with the same lower pitch is the option (DP100). Behind you, a sound is also slightly muffled, in both.
* Section 8.3: loudness falls evenly to the edge of the view, never below the minimum volume, with the "equally quieter for each doubling" curve kept as a setting (DP137). Beyond the view, a sound plays at the minimum volume, muffled, or as a fixed tone if you choose that setting.

## Changes in version 0.6

These come from your answer to DP80 and your agreement that look around plays the Nearby list. All discussion points are now answered.

* Section 4.4: the visible rule is agreed. It now has a size rule for areas, as well as a zoom range for points and lines (DP80).
* Section 8.3: how a feature beyond the view sounds, such as a bordering country while zoomed in to a street (DP80).
* Section 8.5: look around plays the Nearby list.

## Changes in version 0.5

These come from your answers to DP76, DP77 and DP79. DP78 is still open.

* Section 4.1: the zoom is a distance, so the window size never changes what is heard (DP76, agreed).
* Sections 5.4 and 5.7: moving to a feature in hierarchy mode, or jumping to an area, zooms to fit it (DP77, agreed).
* Section 4.3: when linked, the step is one quarter of the zoom distance (DP79).
* Section 12: the zoom, step and sort keys are agreed (DP79).

## Changes in version 0.4

These come from your answers to DP63 to DP75, and your confirmation that switching off a layer removes it both visually and sonically.

* Section 1: the separate focus is gone (DP63, agreed).
* Section 3: "Where am I" is never filtered by zoom or step. If you are in a field, you hear "Field" (DP66). I had misunderstood the point; see section 4.4.
* Section 4 is rewritten. Zoom and step are now separate controls, with an option to link them (DP65).
  * Zoom sets what you see and hear: the map zoom, the hearing range, the Nearby radius and which layers are visible.
  * Step sets how far you move: the step size, where network travel stops, driving speed, and the passed nearby distance.
* Section 4.3: a new idea, "visible", used by the lists. A feature is visible when its layer is on, the zoom is inside the layer's zoom range, and part of the feature is in view.
* Section 5.4: hierarchy "down" lists only visible features. Partly inside features count, with no "partly" label (DP70). Proposed: moving to a feature in hierarchy mode zooms to fit it (DP77).
* Section 6: every list in the Information panel can be sorted by name, distance or bearing (DP70).
* Section 7: a layer's definition includes its sounds (DP74).
* Section 8.3: distance in sound follows the zoom, not the step (DP67). Proposed: the window size does not change what is heard (DP76).
* Section 8.4: the beacon can point at any pin (DP72).
* Section 11: the centre marker is a plus-shaped cross (DP73).
* Section 12: new keys for zoom, step and sorting (DP79).
* Agreed with no change to the design: the Information panel (DP64), network travel stopping (DP68), the turning keys and cardinal facing east and west (DP69), identical boundaries (DP71), driving and tours (DP72), the globe projection (DP73) and the graticule layer (DP74).

---

## 1. The big picture

There is one current location somewhere on the surface of the Earth, and everyone using the computer shares it.

* A blind user moves it with the keyboard and hears where they are.
* A sighted user sees the map always centred on the current location. When the location moves, the map moves under it. A mouse click on the map moves the location there, and the map re-centres.
* A partially sighted user can do both, with a high contrast theme and whatever magnification suits them.

There is one way of moving. It travels across the surface of the world and also takes the user to any feature they are interested in. There is no separate pointer that moves over a still map, and no separate "focus" to manage (DP63).

The current feature is whatever the user is on:

* when stepping, the smallest area under the current location, for example a lake
* in hierarchy mode, the feature they last moved to, for example Hampshire
* in network mode, the junction they are standing at, or the link they are on

Questions such as "what borders this?" are about the current feature. To find out about something else without going there, the user selects it in the Information panel and asks from there (section 6).

## 2. The window

The window has four regions. Tab and Shift+Tab move between the first three, wrapping around from the last back to the first. Tab does not reach the menu bar (DP93): on the desktop, Alt goes to it, and in the web version, Ctrl+Alt+M goes to its first menu, Map, without opening it. In the web version, Tab goes from the menu bar to the map. On the desktop, Tab moves along the menus, and Alt or Escape goes back to the map, as in other Windows programs (PO, Phase 0 acceptance).

1. Map. The main region, where all the movement keys work. It runs in application (focus) mode, so the screen reader passes keys through. Sighted users see the graphical map here.
2. Information panel. A tree view of information about the current location, grouped by relationship. Section 6 describes it.
3. Details. A read-only text panel with the full details of the current feature, or of the item selected in the Information panel. It can be read line by line with the screen reader's normal reading keys.
4. Menu bar. Contains every command, so nothing depends on remembering keys.

When a dialog closes, the focus comes back to the map, and the screen reader says the map's name as it arrives. That name is what the dialog's answer said, such as "Ile-de-France, France" after Go to, or "Facing 90 degrees." after a bearing. If the answer said nothing, as after Cancel or the layers list, the name is the place as it is now, after the dialog's changes. Either way it is said once, and Shift+Space repeats it (P2-T17c). Leaving the map names it after the place again.

In the boxes where you type, Type a bearing (Ctrl+B) and Go to coordinates (Ctrl+G), the label is the only text: "Enter a bearing in degrees, or a compass direction:" and "Enter latitude and longitude:". If what you typed can't be read, a message box opens over the box, with one OK button. It names what you typed and says what you can type, such as "hello is not a valid bearing. Enter a value in degrees in the range 0 to 360. Or enter a compass direction such as north or SW." After OK, you are back in the box with your text, all of it chosen, so typing replaces it and End lets you correct it (P2-T17o).

At the start, the same is true. The screen reader says the window's title, TobyMap, as the window appears, then the map's name as the focus arrives on it. That name is the place, then "Press F1 for keys", such as "Kent, England, United Kingdom. Press F1 for keys." It is not spoken as well, as speaking it was cut off by that reading. Shift+Space repeats it as "TobyMap. Kent, England, United Kingdom. Press F1 for keys." (P2-T17d). Leaving the map names it after the place.

Lessons from RecallScore apply here: tree items take real focus rather than aria-activedescendant, Escape is never relied on, and all speech goes through one announcement queue.

A sighted user sees the map filling most of the window, with the Information panel and Details in a side panel. When the blind user opens a group or selects an item, the sighted user sees the same thing in the panel, with the matching features highlighted on the map. This is how the two work together at one computer (DP23).

The desktop and web versions look and behave the same. The differences are listed in Help (PLT-3).

## 3. Where am I?

### 3.1 Moving announces what changed

After each move, the user hears only what has changed (ANN-1). The rule is:

1. The new smallest area under the location, if it changed.
2. Then any larger areas that changed, from smallest to largest.
3. If nothing changed, only a soft tick plays (DP43), unless you have asked for the place after every step (below).

Holding an arrow key, each step clicks, and the place is said when you let go. Letting go adds no tick: if nothing changed, you hear nothing more. In the web version, a step not yet due when you let go is not made, and its click is taken back.

This uses every active layer, whatever the zoom and whatever the step size (ANN-7, DP66). If you are in a field, you hear "Field", even when zoomed out to a whole continent and taking 25 km steps.

Anything the move jumped over or passed close to is not spoken. It goes into the crossed and passed list (section 3.2), and an earcon says that something was added.

Example of stepping in the north-fixed orientation, with a 100 metre step, starting on a lake inside a field in Hampshire near the Wiltshire border:

* Right: "Field." (the user has left the lake)
* Right: "Long Meadow, Wiltshire." (a new field, which is in a new county)
* Right: "(tick)" (nothing changed)
* Right: "(crossed earcon) Ashwood Farm." The step also crossed the River Avon. Its name is not spoken, but Shift+X lists "River Avon, crossed".

Crossing a border needs no special earcon, because the new name says it. The same goes for moving between land and water.

How much is said is chosen with a verbosity preset, in the Speech tab of Settings, or with A on the map, which goes to the next one and says what it does, and Shift+A, which goes back (ACC-5, DP144):

* Terse: only the smallest area that changed, such as "Somme" instead of "Somme, Hauts-de-France". The zoom, the step and the heading are not said when they change; the tick plays instead.
* Normal, the default: the rule above, and the zoom, the step and the heading when they change.
* Detailed: the whole place, as Where am I says it, whenever an area changed, and in free facing the heading after every step.

Under the preset are its four switches: what to say after a step (only the smallest area that changed, every area that changed, the whole place, or nothing), the zoom and step, the heading after a turn, and the heading after every step in free facing. Changing one makes the preset "Custom". The tick, for a step that changed nothing, has its own switch in the Earcons tab.

After the four switches is one more, outside the presets, so changing it never makes the preset Custom: "Say the place after every step, even when it has not changed" (DP162). It is off at first. With it on, a step that changed nothing says the place instead of the tick, as much as "After a step" asks: only the smallest area, such as "Kent"; every area, which says the smallest area and its country, such as "Kent, United Kingdom"; or the whole place, "Kent, England, United Kingdom". At sea, with no country, the smallest area is said alone. With "Say nothing, only the tick", it still only ticks. A step that changes an area is said as before. Holding an arrow key, each step still clicks, and only the place where you let go is said. Where am I, H, the orientation key and crossing a pole are always said.

### 3.2 The crossed and passed list

Large steps jump over things. A 25 km step can cross several rivers and a railway and pass close to a town, all without the location landing on any of them. Shift+X opens the Crossed and passed group in the Information panel. It holds, for the most recent move only (DP58):

* lines crossed, such as rivers, roads, railways and borders
* areas passed over completely, such as a small lake entered and left within the step
* points passed close to, such as a railway station the path came within the passed nearby distance of

The passed nearby distance is 10% of the step size by default. The user can change the percentage or set a fixed distance (DP58).

Which layers count follows the zoom (section 4.3). Zoomed out to 250 km, the list holds motorways, main railways and rivers, not every lane the step crossed. Zoomed in to 1 km, it holds minor roads and bus stops too.

When a move adds anything to the list, a soft earcon plays. It is on by default and can be switched off (DP58).

Each item gives its closest distance and its bearing from the new position.

### 3.3 Asking on demand

* Space: "where am I". Speaks the smallest area plus its main parents, for example: "Lake, in Long Meadow, Wiltshire, England, United Kingdom".
* F3: goes to the Information panel, where the Within group is the full list of areas containing the location (LOC-3).
* C: the coordinates, for example: "50.9312 north, 1.6124 west".
* Shift+C: the plain-language position (LOC-5), for example: "South-west England, 9 kilometres north-west of Southampton city centre".
* H: the heading, orientation, movement mode, zoom and step, for example: "Facing 45 degrees, north-east. Free facing. Stepping. Zoom 5 kilometres, step 250 metres".

### 3.4 Never nowhere

Every point on Earth has a name (LOC-6). At sea, the user hears the name of the sea or ocean they are in.

Water is a hierarchy, just like land. Oceans contain seas. Seas can contain other seas, and also gulfs, bays, straits, channels and sounds. Moving from the Bay of Biscay out into the open Atlantic announces "North Atlantic Ocean", and Within, in the Information panel, lists "Bay of Biscay, North Atlantic Ocean, Atlantic Ocean".

Only the data that is present is announced. In an area with only the base pack installed, the user hears the base data names and nothing about missing detail. The Details panel and the pack manager show what data covers the location, for anyone who wants to check.

## 4. Zoom and step

You pointed out that zoom and step are different things (DP65). Zoom is how much of the world you are looking at and listening to. Step is how far you move each time. A sighted user can look at a whole county and still click just next to the centre, so a blind user can too.

### 4.1 Zoom: what you see and hear

Page Up zooms out and Page Down zooms in (NAV-13). The zoom is announced as a distance, for example "Zoom 5 kilometres". It means that everything within 5 km of the location is in view (DP76). The default list runs from 100 metres to 10,000 kilometres, which shows a whole hemisphere of the globe.

The zoom sets:

* the zoom of the visual map
* the hearing range: everything in view can be heard (section 8.3)
* the Nearby radius, and the range of look around
* which layers are visible, and so what appears in Contains, Nearby, and Crossed and passed (section 4.3)

When a sighted user zooms with the mouse wheel or a pinch, the zoom changes in the same way, and the blind user hears the new zoom.

The zoom distance is how far you hear: everything within it is in view and in hearing range, whatever the size of the window. So making the window smaller never makes things go silent. The map is drawn at a fixed scale for each zoom, as on paper, so a bigger window shows more map round the edges (DP138). You said the application would normally be maximised, so this matters mostly for sighted users with a smaller window.

### 4.2 Step: how far you move

Shift+Page Up makes the step larger and Shift+Page Down makes it smaller (NAV-2). It is announced as "Step 250 metres". The default list runs from 10 metres to 1000 kilometres.

The step sets:

* how far one step moves in stepping mode
* the furthest one move goes along a line in network mode (section 5.5)
* driving speed, which is in steps per second (section 5.6)
* the passed nearby distance, 10% of the step by default (section 3.2)

Changing the step never changes the zoom, unless they are linked.

### 4.3 Linking them

The option "link step to zoom" is off by default. When it is on, they move together: the step is one quarter of the zoom distance (DP79). Zooming to 1 km makes the step 250 m, and both are announced: "Zoom 1 kilometre, step 250 metres". Where a quarter is not in the step list, the nearest step is used. Changing the step changes the zoom to match. This gives the single control from version 0.3 to anyone who prefers it.

### 4.4 What is visible

Many lists would be far too long without a limit. The United Kingdom has 2,570 railway stations and many thousands of bus stops. You said that lists should only include what is visible on the map (DP70). So a feature is visible when all of these are true:

* its layer is switched on
* the zoom is inside its layer's zoom range. Each layer has one. With the default settings, motorways are visible at every zoom, towns from 250 km in, fields from 10 km in, and bus stops from 1 km in.
* at least part of it is in view
* for an area, it is large enough to see at this zoom (DP80). By default its width must be at least 2% of the zoom distance. At a 5 km zoom, a 50 m pond is not visible, but a 200 m lake is. Each area layer can set its own minimum size.

This works like a sighted map: zoomed out to the whole United Kingdom, you do not see bus stops or fields, so they are not listed either. It also keeps the application fast, because it never has to gather tens of thousands of bus stops (DP80).

The lists split into two kinds (DP80):

* Lists that gather many features in an area are limited to what is visible: Contains, Nearby, look around, and Crossed and passed. For Crossed and passed, only the zoom range and size rule apply, because a long step can reach beyond the view.
* Lists about one feature's own relationships, or about what you asked for, always show everything from the layers that are switched on: Within, Bordering, Overlapping, Crossing and Search. Otherwise, zoomed in to a street in Paris, Bordering for France would be empty, and a search for Tokyo would find nothing.

What is said about where you are follows the layers' zoom ranges, as the map does (DP160). This covers the place said after a step, "Where am I" and Within. A layer outside its zoom range is treated as switched off: with Counties visible to 100 km, at a 250 km zoom you hear "England, United Kingdom", not "Kent, England, United Kingdom". Zooming changes the place the map is named after, but says nothing more; Space says the new place. If every area here is in a layer outside its zoom range, you hear "No data at this zoom level".

The step never limits what is said, and nor does the size rule (DP66). In version 0.3 I proposed skipping small areas, such as fields, after large steps. You rightly said that if you are in a field, you should hear "Field". A field layer's zoom range now decides when it is said, as it decides when it is drawn.

## 5. Moving around

Two independent choices decide how the user moves. They share the same location, so changing either never moves the user, except when entering network mode (NAV-11).

* Orientation: which way the user faces. F cycles through the three orientations, and the new one is announced.
* Movement mode: what the arrow keys move between. The number keys 1 to 3 choose stepping (free roaming), hierarchy or network, and the new mode is announced.

### 5.1 The three orientations (O, and Shift+O the other way)

The orientation decides how directions are described and which way is "ahead" in sound (NAV-12, SON-2).

* North-fixed: the user always faces north. In stepping mode, the arrow keys move north, east, south and west. Directions are given relative to north, in the user's chosen format, for example "north-east" or "45 degrees". In sound, north is ahead. This is the default.
* Cardinal facing: the user faces north, east, south or west. In sound, the way they face is ahead. Directions in words are said as in north-fixed, unless the user asks otherwise (below).
* Free facing (free roaming): the user can face any bearing. Sound and words are as in cardinal facing.

In the Units tab of Settings, "In cardinal and free facing, give directions from the way you face", off at first, measures the words from the way you face instead of from north, in the same format, with "at your" (ANN-5, DP159). For example, facing east, a place to the south-east is "south-east" without the setting, and "at your north-east" with it, that is, ahead and to your right. Other examples: "Berlin, 25 kilometres at your 30 degrees", "at your 2 o'clock", "at about your 50 degrees". Sound in space is always from the way you face, whatever the setting.

### 5.2 Turning

The user can turn in every movement mode, because in network mode the Left and Right arrows are busy choosing links (NAV-12, DP69).

* Shift+Left and Shift+Right turn by the large amount (default 90 degrees, a setting), in free facing.
* Ctrl+Left and Ctrl+Right turn by the fine amount (default 1 degree), in free facing.
* In north-fixed, and in cardinal facing in stepping mode, Shift and Ctrl with Left and Right do nothing and make no sound. In cardinal facing, plain Left and Right turn 90 degrees.
* A types an exact bearing. In north-fixed or cardinal facing, this also switches to free facing, and says so.
* In stepping mode only, plain Left and Right also turn, because there is nothing else for them to do in the facing orientations.

In north-fixed, the turning keys play the blocked sound, because the user always faces north.

### 5.3 Stepping (1): free roaming

Stepping moves the location by the step size (NAV-1, NAV-2, NAV-3).

* In north-fixed:
  * The arrow keys move north, east, south and west.
  * Moving east or west wraps around the world seamlessly.
  * If a step north or south would reach or pass over a pole, the blocked sound plays and the location does not move (DP42).
* In cardinal facing:
  * Up moves forward in the direction the user faces, and Down moves back. Left and Right turn 90 degrees.
  * Facing east or west, the user moves along the line of latitude, as in north-fixed, so "east" always means due east (DP69). Facing north or south, they can carry on over the pole and come out facing the other way: "Crossed the North Pole. Now facing south".
* In free facing:
  * Up and Down move forward and back along the shortest path over the globe (a great circle), which can go over the poles. Left and Right turn by the fine amount.
  * After each step, the heading is the direction of travel on arrival, so on long steps it changes slightly. The change is announced only when it crosses a pole, or at detailed verbosity.

### 5.4 Hierarchy mode (2): containers and neighbours

The user moves between features rather than distances.

Up goes to the parent, for example from Hampshire to England (NAV-4):

* The parent is the smallest larger area that fully contains the current feature. All active layers take part (DP62). If you switch off postcode areas, they stop taking part.
* If two larger areas each contain the feature but neither contains the other, there is a short beep and a menu lists them. Example: a field inside both Hampshire and the New Forest National Park, where the park crosses the county boundary. The user picks one, or chooses Cancel and stays put.
* An area with exactly the same boundary as the current feature is not treated as a parent. For example, the Isle of Wight is a ceremonial county and a unitary authority with the same boundary. It is announced once with both types: "Isle of Wight, county and unitary authority" (DP71). We will see how well this works in testing.

Down goes into the current feature in two stages:

1. First, a list of the types of visible feature it contains, each with a count. For example, in the United Kingdom zoomed to fit: "Countries 4, Counties 92, National parks 15, Cities 76, …". Only types with something visible inside the feature are listed. If Kent contains no national park, "National parks" does not appear under Kent. Bus stops do not appear under the United Kingdom, because they are not visible at that zoom.
2. Choosing a type lists its features. Choosing a feature moves into it.

These lists are the Contains group of the Information panel, so Down and the I key reach the same place.

A feature partly inside counts as inside, with no "partly" label (DP70). The New Forest National Park is listed under Hampshire and under Wiltshire.

Every list can be sorted by name, distance or bearing, and typing the start of a name jumps to it (section 6.1).

Left and Right step through the neighbours of the current feature, ordered clockwise starting from ahead. Each neighbour is announced with its relationship and direction in the current orientation, for example in north-fixed: "Wiltshire, borders to the north-west, shared border 48 kilometres".

The location moves to a representative point inside each feature, so the visual map and the sound field stay in step.

Because "down" only lists what is visible, the zoom matters in hierarchy mode. So moving to a feature in hierarchy mode zooms to fit it (DP77): "United Kingdom. Zoom 1000 kilometres". Moving down to a field zooms back in. The step does not change, unless it is linked to the zoom. The same would apply to jumping to an area (section 5.7).

### 5.5 Network mode (3): junction to junction, along any line

A line is just a simple network, so roads, paths, railways, rivers, coastlines and borders all work the same way.

* Pressing 3 enters network mode. Pressing 3 again cycles through the network types: roads, roads and paths, railways, waterways, coastline, borders, and lines of latitude and longitude. Only line layers that are switched on are offered. The type is announced.
* On entering, the location snaps to the nearest point on the nearest line of that type. If a junction is close by, it snaps to the junction. "Moved 35 metres to junction of Spring Road, Chessel Avenue and West End Road".
* Left and Right cycle through the links leading away. How each link is described depends on the orientation:
  * North-fixed: "Spring Road, north-east, 140 metres, to Catherines Close."
  * Free facing, relative to the way the user faces: "Ahead slightly left, Spring Road, 140 metres, to Catherines Close."
  * Cardinal facing, relative to the cardinal direction faced: "Ahead, Spring Road, 140 metres, to Catherines Close."
* Up travels along the selected link. Down travels back the way the user came.

On borders, a junction is a point where three or more borders meet. Going round the border of Germany stops at each tripoint: "Tripoint, Germany, France, Switzerland. 3 links".

Travel along a link stops at whichever comes first (DP68):

* the next junction
* the next stop point, if stopping at points of interest is switched on (NAV-6), such as a bus stop or a bridge
* the step distance

With a large step, this is junction to junction. With a small step, it is a walk along the line, so an island's coastline can be explored a piece at a time. Junctions that are only a bend in the same road, or where only the name changes, are skipped.

After travelling a link, the user faces (NAV-5):

* north, in north-fixed
* the same cardinal direction as before the move, in cardinal facing. The user can arrive at a junction facing back the way they came, which is fine. Shift+Left and Shift+Right turn.
* the direction of the last stretch of the line as it reaches the junction, in free facing. If a road leaves heading north and bends round to arrive heading east, the user faces east.

Rivers have a direction. Links are described as upstream or downstream as well, for example: "River Kennet, downstream, west, 4 kilometres, to where Foudry Brook joins".

### 5.6 Driving

Driving moves the user continuously instead of in steps (NAV-14).

* Ctrl+Up starts driving forward, and any movement key stops it. Ctrl+Page Up and Ctrl+Page Down change the speed.
* Speed is measured in steps per second, so it follows the step size, not the zoom (DP72). With a 10 m step it is a walk along a street. With a 100 km step it is a flight across a country.
* In network mode, driving follows the current link and stops at the next junction where a choice is needed. Bends and name-only junctions do not stop it.
* In stepping mode, driving goes straight ahead along the heading, as a great circle. In north-fixed, it goes in the direction of the last arrow key pressed.
* Changes of area are announced as usual. Passing within the passed nearby distance of a point of interest plays that layer's ding, and the point goes into the crossed and passed list.
* With the orientation beacon on (section 8.4), the beacon swings around as the road bends. This gives a feel for the shape of a curving line.

### 5.7 Jumping

* Ctrl+F searches. Choosing a result jumps there (NAV-8). There is no "focus only" option.
* Ctrl+G goes to typed coordinates, in any common format. In cardinal and free facing, it also takes "f" or "forward", or "b" or "back", and a distance, to move along the way you face, as Up and Down do: "f 24" is 24 of your own unit, kilometres or miles, and units can be typed, such as "F24mi240yds" or "b 2km 500m" (P2-T17r, DP161). In north-fixed, a message box says "Forward and back work in cardinal and free facing."
* Bookmarks and pins (section 9) can be jumped to.
* "Jump" on any item in the Information panel goes there.
* A mouse click on the visual map moves the location and gives the normal announcement. This is the sighted user's equivalent of a step of any size.
* Backspace goes back to the previous position and Shift+Backspace goes forward again (NAV-10). Going back also restores the zoom you had there.

Jumping to an area zooms to fit it (DP77). Jumping to a point, such as a railway station, or to coordinates keeps the current zoom.

## 6. The Information panel

The Information panel answers "what is around me, and how does it relate to me?" It always describes the current location and the current feature. You agreed this design (DP64), and expect to change it once you have used it, so it is built to be easy to change.

### 6.1 The groups

The panel is a tree. Its top level holds these groups:

* Within: every area containing the location, from smallest to largest (LOC-3). Each item says the distance and direction to the area's centre, the centre of its bounding box (DP155): "England, centre 140 kilometres west".
* Contains: the types of visible feature inside the current feature, each with a count, then the features of each type (INF-4).
* Bordering: the neighbours of the current feature, each with the shared border length, or the distance and bearing for areas that only nearly touch (INF-2).
* Overlapping: areas that overlap the current feature, with how much of it each covers (INF-5).
* Crossing: line features crossing the current area. For a line, the areas it passes through in order (INF-6).
* Nearby: the visible features of each active layer, with distance and bearing (INF-7).
* Crossed and passed: what the last move crossed or passed close to (section 3.2).
* Search: the last search results.

Every list can be sorted three ways: by name, by distance, or by bearing clockwise from ahead. Ctrl+S, in the panel, cycles the sort and announces it: "Sorted by distance". Within also has its natural order, smallest to largest, which is its default. Nearby starts sorted by distance, Bordering by bearing, and the rest by name. Typing the start of a name jumps to it, as in any Windows tree.

Each group heading says how many items it holds: "Nearby, 5 items", "Within, 1 item", or "Crossed and passed, no items".

Contains, Nearby, and Crossed and passed show only visible features (section 4.4). Within follows the layers' zoom ranges, as the place does (DP160). The other groups are not limited by zoom (DP80).

Each group is filled when it is opened, so it never slows down movement. After a move, the groups are refreshed the next time the user goes to the panel.

### 6.2 Getting there

F3 goes to the Information panel from any region, back to the item you were last on there. The first time, it goes to the first item of Within (DP106).

A key in the map region opens some groups directly and speaks their first item. Whether these stay is DP109:

* I: Contains.
* N: Bordering.
* O: Overlapping.
* X: Crossing.
* Shift+X: Crossed and passed.

From there, arrow keys move through the tree. Tab returns to the map.

### 6.3 Acting on an item

In Phase 2, two actions have their own keys:

* Enter goes there, as a jump, so Alt+comma comes back (DP155). A point goes to the point. An area goes to its centre, the centre of its bounding box. A line goes to the place its item is about: its nearest point, or where it was crossed. The new place is said, and the focus stays in the panel, on the first item of the same group, as the group's items have changed.
* Space hears its direction (DP143).
* On a group heading, Enter and Space say and do nothing (the PO, 10 November 2026). Right and Left open and close the group.
* An item less than a metre away, such as a station you went to with Enter, says "here" in place of a distance and direction: "Southampton Central, here". A line you stand on, such as the graticule's 100 degrees west at 100 degrees west, is not in Nearby, as an area you are in is not (P2-T18e).

Go to coordinates (Ctrl+G) and Type a bearing (Ctrl+B) work from the panel and from Details as well as from the map. After the box closes, the focus goes back where it was. In the panel, after Go to, it is on the first item of the same group; after a bearing, on the same item. The answer, such as the new place, is spoken after the item is read.

The full set of actions on any item is (INF-10):

* jump: move there, and make it the current feature
* details: show its details in the Details panel
* its own groups: open Bordering, Contains and so on for this item, without moving
* hear its direction
* measure: distance and bearing from the location, and along a line where that makes sense
* bookmark

D speaks and shows the details of the current feature (INF-1). Facts give their source and date, for example "Population 67 million (Wikidata, 2024)".

M measures from the location to the selected item, a search result or a bookmark (INF-3, INF-8).

### 6.4 The query builder

For anything more complex, Q opens the query builder (INF-9). It is a three-field form:

* Find: a layer, such as rivers or schools.
* Relation: within, crossing, bordering, or within a distance of.
* Of: the current feature, a searched feature, or a bookmark.

For example: Find "Rivers", relation "flowing through", of "Germany". The answer goes into the Search group. There is no query language, and no database field names appear.

Every distance is measured along the Earth's surface. Every bearing uses the user's chosen format (ANN-5), relative to north or to the way the user faces, depending on the orientation.

## 7. Search, browse and layers

* Ctrl+F opens a search box. Typing shows matching results as the user types, and pressing Down moves into them. Enter jumps.
* Matching ignores accents, catches common misspellings, and finds names in other languages. Places with the same name are told apart by their parents, for example: "Paris, Île-de-France, France" and "Paris, Texas, United States".
* A filter control limits results to the current area, near the location, or one layer.
* T opens the world as a tree view (SRB-3): World, then continents, then countries, and so on. It works like Windows Explorer's folder tree.
* Help includes a "Data sources" page listing every source, its licence and its date (DAT-9, DP51).

### 7.1 Layers

Shift+L opens the layers list (SCP-6). Each layer, such as roads, railway stations, national parks or postcode areas, can be switched on or off. A layer that is off is gone both visually and sonically: it disappears from the visual map, and from announcements, hierarchy "up", Nearby, look around, network types, crossing earcons and the crossed and passed list. Sighted and blind users therefore always work with the same set of features.

Everything about a layer is defined in one place (SCP-7, DP74):

* how it looks on the map
* its zoom range, from its maximum zoom (the closest, the smaller distance) to its minimum zoom (the farthest), which decides when it is visible and said (P2-T18c)
* its sounds: a crossing earcon, played when you cross one of its lines, or the border of one of its areas, the sound its features make in look around and "hear its direction", and the ding when one is passed while driving
* whether it is a network type in network mode, and whether its points can be stop points

The layers list is a tree, like the Information panel: each group, such as Boundaries, holds its layers, each a check box. Up and Down move, Left closes a group or goes up to it, Right opens it, Space ticks or clears a layer, and Enter presses OK (P2-T18b).

The data manager chooses sensible defaults. In the layers list, each layer also has a settings button where the user can change its sounds and its zoom range. For example, to hear a sound every time you cross a railway, give the railways layer a crossing earcon.

## 8. Sound

### 8.1 What sound is for

Speech says what something is. Sound says where it is, and what is changing as the user moves. Sound never replaces information that speech gives; it adds to it. Everything can be turned down or off, and a single key silences all application sound at once.

### 8.2 Spatial sound

* By default, sounds are placed with stereo panning, and a sound behind you is about three semitones lower, so ahead and behind can be told apart, on headphones or speakers (SON-1, DP100).
* A spoken label behind you is 1.5 semitones lower, at the same speed as ahead (P2-T16g).
* The other sound mode is HRTF, for headphones, with the same lower pitch behind. Without the pitch, every HRTF you tried left sounds behind unclear. The mode is a setting, in the Sound tab.
* Behind you, a sound is also slightly muffled, in both modes.
* Which way is ahead follows the orientation (SON-2). North is ahead in north-fixed. The way the user faces is ahead in cardinal facing and free facing.
* You tested this in the Phase 1 listening test, before the rest of the sound design was built on it (DP47).

### 8.3 Distance follows the zoom

Distance is always heard relative to the zoom, never the step (SON-9, DP67). Whatever is in view can be heard.

* The hearing range is the zoom distance. At a 1 km zoom you hear things up to 1 km away. At 1000 km, up to 1000 km away.
* Within the range, loudness falls evenly with distance, from full loudness at one twentieth of the range to the minimum volume at the edge (DP137). No sound is ever quieter than the minimum volume, a setting, 20% at first. The other curve, in which each doubling of distance is about equally quieter, is a setting too.
* So a feature halfway to the edge of the view sounds the same at every zoom.
* Beyond the range, sounds play at the minimum volume, muffled as much as they ever are, so "far away" is still recognisable. A setting plays a brief fixed tone instead (DP80).
* You asked how loud a bordering country should sound when it is not on the map (DP80). Items in Within, Bordering, Overlapping, Crossing and Search can be out of view. They play from their true direction, at the quiet, muffled "beyond the view" level, and the spoken label gives the real distance: "Spain, south, 680 kilometres". So the sound says "that way, and further than you can see", and the speech gives the figure. We will try this in the Phase 1 listening test. One alternative to try there is a brief fixed tone for anything beyond the view, instead of a quiet version of the normal sound.
* The optional second cue is either reverb (farther sounds more distant) or a repeating click that speeds up as the user gets closer.
* The spoken label always includes the distance, so sound gives the feel and speech gives the figure.
* Because the zoom is a distance rather than a number of pixels (DP76), resizing the window does not change what is heard.

The range and the curve are settings, and you will try them in the Phase 1 listening test.

### 8.4 Orientation beacon

B switches on the orientation beacon (SON-10). It is a soft repeating sound that comes from the North Pole by default, so the user can feel which way they are facing without asking. In the Sound tab, "Orientation beacon: comes from" can choose the South Pole instead, or the equator at 0 degrees east, 90 degrees east, 180 degrees or 90 degrees west (P2-T18g).

* It is most useful in cardinal facing and free facing. In north-fixed it is always straight ahead.
* While driving along a curving road, the beacon swings from side to side as the heading changes. That is how the shape of the line can be felt.
* Near the place it comes from, its direction is unstable. The beacon fades from 200 km and is silent within 100 km of it. Going inside, you hear "Beacon off near the North Pole." once, or the place chosen; coming back out, "Beacon back on." Switched on near it, it says "Beacon on, but silent near the North Pole."
* It plays about once a second; the time between each sound is a setting. Behind you it has the lower pitch and slight muffling, like every sound placed in space. Its loudness does not change with distance.
* The Sound tab of Settings has the beacon on or off, its volume, the seconds between each sound, your own file for it, and where it comes from. Ctrl+M silences it with everything else. Its sound is a placeholder until you choose one.
* The beacon can point at any pin instead, such as "home" (DP72). It then works as a homing sound. Choose the target in settings, or with "Beacon to this pin" in a pin's actions.

### 8.5 Hearing where things are

* "Hear its direction" on any item plays its layer's sound from that feature's direction and distance (on a Within item, from the centre of the area), then says its name and distance in the built-in voice from the same place, such as "France, 34 kilometres". A layer with no sound of its own plays the "item's direction" sound.
  * In Phase 2 it is Space on an item of Nearby or Crossed and passed, in the Information panel (DP143). It joins the item's actions (section 6.3) when they are built.
  * A newer label stops one still being said.
* Look around (L, SON-4) plays the Nearby list as sound. Nearby (R) gives you the features as a list to read. Look around plays the same features one after another in bearing order, clockwise from ahead, each from its own direction, at most 12 of them. So anything you hear in a scan is also in Nearby in the Information panel. Each feature's name is spoken from the same place as its sound (SON-3, DP39).
* The spoken names come from a voice built into the application, because a screen reader voice cannot be placed in space (DP46). The defaults are:
  * The screen reader does not also speak the name, so you do not hear everything twice.
  * Shift+Space repeats the last name, so it can be heard again.
  * On the desktop with NVDA, the names are also sent to the Braille display without being spoken. A browser has no way to send Braille alone, so in the web version the names reach the screen reader only when the setting below is on.
  * A setting, "also speak spatial labels through the screen reader", is off by default.
  * The built-in voice has its own speed and volume settings.

### 8.6 Earcons

Short sounds mark these events (SON-6):

* a step with nothing changed (the soft tick)
* something added to the crossed and passed list (on by default)
* passing a point of interest while driving (the ding, which can differ by layer)
* being blocked, for example at a pole or when turning in north-fixed
* no data available (for example, the network mode has no lines of that type nearby)
* the hierarchy "up" menu appearing (the beep)
* crossing a line of a layer that has a crossing earcon

There are no earcons by default for crossing a border or for moving between land and water, because the new name makes them clear. You can still give an area layer, such as Countries, a crossing earcon if you want one. It plays when a step ends in a different area of that layer from the one it started in, such as from France into Belgium, or from a country out to sea. A step that leaves a country and comes back into it within the same step plays nothing.

The graticule layer (DAT-13) holds the lines of latitude and longitude at an interval you set, and the special lines: the equator, the prime meridian, the antimeridian, the tropics and the polar circles. Each has its own crossing earcon, off by default. Like any layer, it can be shown on the map, listed in the crossed and passed list, and followed in network mode. On the map, the special lines are drawn thicker than the lines of latitude and longitude and in a colour of their own, so a sighted helper can find them (P2-T17v).

Every earcon is a WAV file and can be replaced (SON-8). You will supply all of them (DP61). Until each one arrives, a simple placeholder tone is used. Users can point any earcon at their own file in settings.

The Earcons tab of Settings is one list of every earcon, each with a check box to play it or not. Space ticks the box, and Enter presses OK, as everywhere in Settings. Below the list is one set of controls, for the earcon chosen in the list: its own volume, in percent, and your own file, empty for the default, with Choose file and Use the default buttons. Their labels say which earcon they are for, such as "Tick: volume, in percent". Each earcon's volume also sets how loud it is when placed in space, such as the item's direction sound. There is no volume for all the earcons together (DP163). The spatial voice and the orientation beacon have their own volumes in the Sound tab, and the beacon's own file is there too, with its other settings; it is not in the Earcons tab's list, because B switches it. Ctrl+M silences everything at once. The sounds, in Help, plays any earcon, even one that is switched off, so you can hear it first.

On the desktop, your own file is kept where it is, by its path. In the web version, a page cannot read a path on your computer, so Choose file reads the file you pick and keeps a copy in the browser's storage, and it plays from there from then on (DP123). Every earcon plays in the web version with no set-up. A file that is not a WAV sound is refused when you choose it, and you are told. If your own file cannot be played later, for example because it was moved, the default plays and you are told once.

### 8.7 Grid layers as pitch

* With a grid layer switched on, such as elevation, each move plays the value at the new position as pitch: higher pitch means a higher value (SON-5).
* Z speaks the value with units, for example: "Elevation 1,345 metres" (DP99).
* S sweeps, playing values as a quick run of tones along a line. The default sweep runs from the user's left to their right across the view. In north-fixed that means west to east. The sweep dialog allows other directions, lengths, and "between two pins".

## 9. Pins, bookmarks, collections and tours

* K drops a pin at the location. The user is asked for a name (optional) and a note.
* Ctrl+B bookmarks the current feature, whether it is a country, a river or a bus stop (USR-2).
* Ctrl+K opens Collections: named, ordered lists of pins and bookmarks, such as "Walk to the station" or "Countries in the Andes". A collection opens in the Information panel like any other group.
* Measure on a collection gives the straight-line distance from the first item to the last, and the total length through every item in order (USR-4).
* "Distance along" between two pins on the same road or river gives the length along that line, or explains why it cannot (INF-12).
* Collections can be exported to and imported from GeoJSON for sharing (USR-5).
* Later (USR-6, DP72): a collection can be played as a tour. The application drives from one item to the next, along the network where the two are on the same line and straight across otherwise, pausing at each item to announce it.

## 10. Touch exploration

Touch is used to feel the shape of the data, not as the main way of controlling the application (DP21).

Shape tracing (TCH-1) works like this:

1. The user chooses "Trace shape" for the current feature.
2. The screen shows that area on its own, as large as possible, using the same globe projection as the map, centred on the area.
3. The application announces the scale, for example: "France. North at top. Screen width about 1,000 kilometres. Touch to explore".
4. With a finger inside the area, the user hears a steady high tone. Outside, they hear a low tone. Crossing the edge gives a click.
5. By keeping the tone on the edge, the user follows the coastline and borders.

Line tracing (TCH-2) gives a tone while the finger is on the line. The tone changes at named points, such as towns along a river.

More touch modes will be added one at a time. The first candidate is relief: elevation as pitch under the finger.

Screen readers capture touch for their own gestures. On entering touch mode, the application tells the user how to hand touch over, for example: "Press NVDA+Alt+T to turn off NVDA touch interaction". Touch tracing is planned for the desktop first.

## 11. What a sighted or partially sighted user sees

### 11.1 The globe

Non-visual features never use a projection. Distances, bearings, stepping and great circles are all worked out on the shape of the Earth itself, so blind users never meet the distortions of a flat map. Projection only matters for the visual map and for touch tracing.

The visual map is the Earth viewed from space, an orthographic projection (VIS-5, DP73):

* The map is always centred on the current location, so the least distorted part of the view is always where the user is.
* Zoomed out, the sighted user sees the globe as a ball, so crossing a pole looks natural and no part of the world is stretched.
* Zoomed in to street level, the curve is too small to see, and it looks like an ordinary flat map.
* An option rotates the map so that the user's heading is at the top, in the facing orientations. North-up is the default.

### 11.2 The rest of the view

* A small plus-shaped cross marks the exact centre, so a sighted helper can see the precise point being described. It is on by default and can be switched off (DP73).
* A small heading arrow at the centre shows which way the user faces. The current feature is outlined, and the selected Information panel item is highlighted.
* Themes: standard, high contrast dark, high contrast light, and colour-blind safe (VIS-2). T goes to the next and Shift+T to the previous, and the theme is said. In the high contrast themes, every outline and name reaches at least 7 to 1 contrast against what it is drawn on. The colour-blind safe colours still differ for each of the three common kinds of colour blindness.
* The map display setting, in the Display tab (DP108): the fill as different colours for neighbours (the default), one colour for all, or none, for outlines only; borders on or off; and the colours of the fill, the borders and the current outline. "Outline the current area" chooses when the current outline is drawn: always (at first), not for the oceans, never for oceans and seas, or never (P2-T17v). In a high contrast theme, a colour that would fall below 7 to 1 is not used, and you are told.
* Layers shown on the map are the same as the active layers in the layers list. Isolate, Ctrl+I, shows only the area you are in and its outline, and Ctrl+I again shows everything.
* Names on the map: each area's name is placed inside it where the whole name fits, never over another name or the centre cross, larger areas first. A larger area on the map has a larger name, so names grow as you zoom in. The label size setting goes from 50% to 300% (VIS-3). Names are left out while a key is held.
* Magnifiers (ACC-8, DP146). On the desktop, while the map has focus, it holds an invisible text cursor at the map centre and moves it after every move, so a magnifier that follows the text cursor keeps the location in view. In the web version, the map's focused element is a small invisible point at the map centre, so a magnifier that follows the keyboard focus looks there.

## 12. Draft keyboard map

These are draft bindings, to be tested with NVDA in both the desktop and web versions before they are fixed. All of them can be changed by the user. F1 lists the commands available in the current region, and a key describer mode speaks what a key does without doing it.

A rule for every key that goes round a list, now and later: the key goes forward through the list, and the same key with Shift goes back (P2-T17l, the PO's note on desktop checklist 4.4). O and Shift+O go through the orientations, A and Shift+A through the verbosity presets, and T and Shift+T through the themes. A new key that goes round a list gets its Shift partner at the same time.

In every number box, such as those in Settings, Home sets the largest value and End the smallest (P2-T17m, the PO's note on desktop checklist 12.4). Home is above End on the keyboard, so it goes to the top.

Keys changed since version 0.3 (agreed, DP79):

* Page Up and Page Down now change only the zoom.
* Shift+Page Up and Shift+Page Down are new, and change the step size.
* Ctrl+S is new, in the Information panel, and cycles the sort order.
* "Link step to zoom" is in the menu and in settings, with no default key.

### Movement
* Arrow keys: move, with the meaning depending on the movement mode and orientation (section 5).
* O: cycle the orientation: north-fixed, cardinal facing, free facing. Shift+O goes the other way.
* 1, 2, 3: stepping, hierarchy and network modes. 3 again: next network type.
* Shift+Left and Shift+Right: turn 90 degrees.
* Ctrl+Left and Ctrl+Right: fine turn in free facing.
* A: type a bearing.
* Page Up and Page Down: zoom out and in.
* Shift+Page Up and Shift+Page Down: larger and smaller step.
* Ctrl+Up: start driving. Any movement key stops.
* Ctrl+Page Up and Ctrl+Page Down: driving speed.
* G: go to coordinates.
* Alt+Comma and Alt+Full stop: back and forward through the location history: every step, jump, Go to and click (DP142). A place in a layer not shown is passed over (DP158).

### Where am I
* Space: where am I.
* C: coordinates.
* Shift+C: plain-language position.
* H: heading, orientation, movement mode, zoom and step.
* Shift+Space: repeat the last announcement (Ctrl+Space if Shift+Space gets in the way of typing).
* Ctrl+Shift+Space: the location history, the places Alt+Comma and Alt+Full stop go through, newest first. Enter goes to a place (DP158).

### Information panel
* I: Contains.
* N: Bordering.
* O: Overlapping.
* X: Crossing.
* Shift+X: Crossed and passed.
* Ctrl+S, in the panel: cycle the sort order between name, distance and bearing.
* M: measure.
* Q: query builder.
* V: size of the visible map, for example "Visible map: 1,140 kilometres wide by 890 kilometres high" (DP99).
* Z: grid value (DP99).
* Ctrl+F: search.
* T: world tree.
* Shift+L: layers.

### Sound
* L: look around.
* S: sweep.
* B: orientation beacon on or off.
* Ctrl+M: mute or unmute all application sound.

### Personal
* K: drop a pin.
* Ctrl+B: bookmark the current feature.
* Ctrl+K: collections.

### Other
* A: the next verbosity preset (DP144). Shift+A: the previous one.
* T and Shift+T: the next and previous theme.
* Ctrl+I: isolate the area you are in, and again to show everything.
* P: data packs.
* F1: help.
* F2: go to the map, from anywhere (DP106).
* F3: go to the Information panel, from anywhere, back to the item last focused there (DP106).
* F4: go to Details, from anywhere (DP106).
* Ctrl+Alt+M, web version only: go to the menu bar (DP93). The desktop uses Alt.
* Ctrl+comma: settings.

## 13. Settings

Settings are a standard accessible dialog with these tabs:

* Speech: the verbosity preset and its four switches (built in Phase 2). The concise Braille format is parked until a Braille user can try it (DP145), and the preferred name language comes later.
* Units: metric or imperial, nautical miles at sea, bearing format, and coordinate format.
* Movement: default orientation, step list, link step to zoom, fine turn amount, driving speed, points of interest to stop at, and the passed nearby distance (percentage of the step, or fixed).
* Sound: headphones or speakers, volumes for each sound type, the distance cue, the beacon target, the built-in voice's speed and volume, whether spatial labels are also spoken by the screen reader, per-earcon toggles, and custom earcon files.
* Display: the centre cross, announcing places under the mouse, the theme, the map display setting, names on the map, the label size, and heading-up (built in Phase 2). The zoom list comes later.
* Layers: the same list as Shift+L, with each layer's sounds, zoom range, and the graticule interval.
* Keys: view and change bindings.
* Data: installed packs, and on-demand download on or off.

Reset all settings, in the Map menu, puts everything back as on a new installation on a new computer (P2-T18h): every setting, your keys, your layer choices and your own sound files, and it clears your place and the location history. A message box asks first, with Reset and Cancel; Cancel has the focus, so Enter straight away changes nothing. After Reset, the focus comes back to the map, whose name is "All settings are reset, as on a new installation." and the place. To keep your settings, Export settings first.

## 14. Data packs

* P opens the pack manager. It is a list showing each pack's name, size, data date and status (installed, update available, or not installed). From it the user can install, update, remove and cancel.
* On first run, the application explains that it needs the base pack, gives its size (250 MB or less), and offers to download it. Installing a regional pack such as Great Britain is offered after that.
* Regional packs aim to be 1 GB or less, following Geofabrik's region boundaries. Detailed grid layers, such as rainfall and temperature, are separate optional packs (DP59).
* Packs are downloaded from the project's GitHub Releases page (DP48).
* In the web version, packs are stored by the browser. Browsers may limit how much can be stored, and the pack manager says how much space is left.
* When the user moves into an area with no detail installed, only the data that is present is announced. If they are online and on-demand download is switched on, the detail is fetched in the background, and any new, smaller area is announced when it arrives.

## 15. First use and learning

* A short guided tour starts on first run and can be repeated from Help. It covers stepping in north-fixed, "where am I", zoom and step, the Information panel, changing orientation with F, and the crossed and passed list.
* A practice mode limits movement to one familiar country and gives extra hints.
* Help also includes a plain-language glossary of terms such as bearing, great circle, orientation, zoom, step, visible, layer, administrative level and grid layer.

## 16. The data manager's experience

The data manager is technical and may be blind (DP33). The tool is command line only, driven by configuration files, with no editing of geometry (DMT-1 to DMT-7). For now it runs on your laptop, with large files on the external SSD, drive E: (DP53, DP60).

A typical session, using illustrative command names:

1. `mapdata check` confirms that drive E: is connected, reports the free space on each configured folder, and warns if a planned build will not fit.
2. `mapdata fetch --region great-britain` downloads the sources named in the configuration, or reuses a local copy such as the planet file already on E:. It reports one line for each source and a final summary.
3. `mapdata build --pack great-britain` processes the data and writes the pack. Progress lines appear at each stage, for example: "Stage 3 of 7: clipping boundaries to coastline. 12,400 of 31,000 done". There are no animated bars.
4. `mapdata report --pack great-britain` writes the quality reports as text and CSV: repaired geometries, unnamed features, coverage gaps, size by layer, and the difference from the last release.
5. `mapdata publish --pack great-britain` uploads the pack to GitHub Releases and updates the manifest.

Errors always say what went wrong, which source and feature were involved, and what to do next. Data corrections, such as renaming, excluding or reclassifying a feature, are rules in a configuration file, so they are repeatable and can be reviewed. Layer definitions, including their default zoom ranges and sounds, are also configuration files (SCP-7).

## 17. Settled since version 0.3

* DP63: no separate focus.
* DP64: the Information panel and its groups, to be refined after testing.
* DP65: zoom and step are separate, with an option to link them.
* DP66: "where am I" is never filtered by zoom or step.
* DP67: distance in sound follows the zoom.
* DP68: network travel stops at the next junction, stop point or step distance.
* DP69: the turning keys, and cardinal facing east and west following the line of latitude.
* DP70: lists show only visible features, partly inside features count with no label, and lists sort by name, distance or bearing.
* DP71: identical boundaries announced once with both types.
* DP72: the beacon can point at any pin, driving speed is in steps per second, and tours are a later feature.
* DP73: globe projection, and a plus-shaped centre cross.
* DP74: the graticule as a layer, and sounds as part of every layer's definition.
* DP76: the zoom is a distance, so the window size does not change what is heard.
* DP77: moving to a feature in hierarchy mode, or jumping to an area, zooms to fit it.
* DP79: the zoom, step and sort keys, with a linked step of one quarter of the zoom.
* DP78 and DP80: lists that gather many features show only what is visible, using a zoom range for points and lines and a size rule for areas. Lists about one feature's relationships, and Search, always show everything.
* Look around plays the Nearby list as sound.

## 18. Open UX decisions

None. All discussion points, DP1 to DP80, are answered. A few details are marked "proposed" in this document, such as the 2% area size and the sound for features beyond the view. They are tuning values to be settled by testing, not open decisions.
