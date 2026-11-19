# Phase 3 tidy-up plan 2

Written on 19 November 2026, from your second pass of the desktop checklist and your comments on the response to it (docs/checklists/phase-3-tidy-up-desktop-response.md). The first tidy-up plan, docs/plan/phase-3-tidy-up.md, stays as the record of P3-T19 to P3-T27. This plan carries on from it.

## The plan

The plan has six parts, and key maps, task P3-T31, added on 19 November 2026 (section 3a):

1. Faults and changes from your second pass, task P3-T28.
2. The Information panel as defined, task P3-T29.
3. The coast as a border, a trial, task P3-T30.
4. Carried over from the first plan: P3-T20d, DP208, and P3-T27.
5. The builds, task P3-T21.
6. Testing again, task P3-T22.

The order of work:

1. P3-T28 and P3-T29 in the code, starting with what needs no build, while you answer R1 to R6.
2. P3-T30 on a small sample.
3. The Western Europe trial build with the build changes, then the world build.
4. A short desktop checklist, then the web and sighted checklists.

## Who does each task

Each task says which model does it: Opus or Sonnet.

* Opus does the build changes, anything that changes what is stored in a pack, design choices, speed work, the builds themselves, and anything that waits on your answers. These are costly to get wrong: a build fault means another long build.
* Sonnet does changes in the core and the shells that follow a clear definition, such as wording, dialogs, keys and sorting.
* Opus checks each Sonnet task's changes and runs the tests before it is committed.
* Opus also writes the desktop checklist, as it covers what changed across the whole plan. Sonnet brings the web and sighted checklists up to date from it.

In all: 17 tasks for Opus, 15 for Sonnet.

## 1. Faults and changes, task P3-T28

### Faults

* P3-T28a, Opus: Stand-in areas. The build fills a region's land that is in none of its counties with an area named after the region, such as "England" in the Counties layer. Slivers under 1 square kilometre are left out, as unclaimed land is. A larger one is named as what it is, such as "Part of Scotland in no council area", and is never said by the region's bare name. Needs a build. (Checklist 2.3, 7.2; Islay and Bournemouth; LOC-2, INF-2.) Done in the code, 19 November 2026: each separate bit measured on its own, a sliver given to the county beside it rather than left out, so the Counties layer keeps no hole; the rest named "Part of England in no county", with the country's word for its counties where the tiers record has one. Rehearsed on the Western Europe trial's grid squares: about 46,000 slivers given away in 19 seconds. Shows after P3-T21a.
* P3-T28b, Sonnet: The Coast subgroup in Bordering lists only the most detailed water, and its heading gives the whole coast's length, "Coast, 180 kilometres". (7.2; INF-2, DP200.)
* P3-T28c, Opus: Bays and straits keeps a bay only at the coast or on a lake, so river pools such as Hatch Pool are left out of the pack. Needs a build. (2.3; DAT-4.)
* P3-T28d, Opus: A road whose parts are far apart is split into separate roads, so England's M3 and Belfast's M3 are two. Needs a build. (2.3.)
* P3-T28f, Opus: The Moselle condominium in the world tree, done as you choose in R1. (11.4.) Done in the code, 19 November 2026, as option B: not a country but land shared by its owners. The join stage keeps the owners' ids; the writing stage puts it inside each owner by the core's rule. The world tree lists it under Germany and under Luxembourg, not among Europe's countries; Up from it offers both; Down from each lists it, and Contains; it stays a neighbour of each, and is still said "Moselle condominium, shared by Germany and Luxembourg". Tests: 4 in tests/mapcore/test_condominium.py. Shows after P3-T21a.
* P3-T28m, Opus: The current feature, when stepping, is the first area "where am I" says, not the first by layer rank: the United Kingdom, not the British Isles. (Your note in the explanation document; LOC-4.)
* P3-T28n, Opus: A land area's share inside another is measured on its land only, so Exmoor, 1.2 percent of whose outline is in the sea, is wholly inside England, and Up from it goes there. Needs a build. (Set 10; NAV-4.)
* P3-T28r, Opus: Stray slivers of a sea. Found while checking P3-T28b: the Sea of the Hebrides has two tiny parts in Hampshire, at exactly 2 degrees and 1 degree west, near Poole and Portsmouth, so it is listed on Hampshire's coast (310 metres) and England's (59 kilometres). A fault in how the seas stage cuts its shapes at whole degrees. Needs a build. (7.2; DAT-4.)
* P3-T28o, Sonnet: Enter on the map, in hierarchy mode, when look around is not playing, makes the feature you are on the one Left and Right go round. (Set 10; NAV-4.)

P3-T28e is dropped: you understand hierarchy mode now.

### Changes you asked for

* P3-T28g, Sonnet: Details. (4.1, 8.2.)
  * "The location is" becomes "Location:".
  * The border line: "of which land is 370 kilometres and coastline is 180 kilometres", with the coast measured as the whole border is.
  * Enter on the Wikipedia article line opens it, as W does.
  * Elevation for places only, such as peaks and towns (Q1).
  * Source: "Shape and name: OpenStreetMap, ODbL licence" (Q2).
* P3-T28h, Sonnet: The Map views dialog: focus on the view in use; Add, Rename and Delete as buttons; OK, the default, and Cancel; Escape also cancels. (2.4; ACC-7.)
* P3-T28i, Sonnet: A shared border's ends sorted clockwise from north, or from ahead. (6.2; INF-2.)
* P3-T28j, Sonnet: An exclave said with its own name: "Llívia, exclave of Spain in France". (3.8.)
* P3-T28k, Sonnet: A zoom change says the place too, when what Space would say has changed. (Your notes; ANN-1, ANN-7.)
* P3-T28l, Sonnet: Ctrl+Alt+W opens the current feature's Wikipedia article, from anywhere. Checked against NVDA's keys and the browsers' keys first; the web version gets another key if AltGr+W types a letter on a common keyboard. In the command registry (AD-3). (4.3.)
* P3-T28p, Opus: Space names a town you are near: "Near Winchester. Hampshire, England, United Kingdom". The distance grows with the town's size; I'll propose the distances with the first version for you to try. (Q6, part of DP206; LOC-5.)
* P3-T28q, Sonnet: The query builder's "Of" list gets "Search for a feature", which opens search and comes back with the feature chosen. For you to review. (12.3, Q4; INF-9.)

## 2. The Information panel, task P3-T29

The definition is docs/design/explanation.md, section "How the Information panel's groups are filled". Each task makes the code match a part of it. Tests first, with the approved wording in tests/mapcore/test_session.py.

* P3-T29a, Sonnet (INF-10): The groups and their keys: Within, Nearby, Bordering, Contains, Overlapping, Passed over, Search, on Shift+1 to Shift+7, in both versions. Crossing goes; Crossed and passed is renamed Passed over. The command registry, the templates, the glossary and the key list change with it.
* P3-T29b, Sonnet (INF-7): Nearby leaves out a place you are at.
* P3-T29c, Opus (INF-4): Contains holds only features wholly inside the current feature. Which are in the view is decided by each one's nearest point, unless R2 decides otherwise; its distance is to the nearest point; an area you are in says "you are inside". Bays and straits, areas and places, are one subgroup. Hierarchy mode's Down and Browse by category follow it. Timed on the world pack for England and Europe before it is kept.
* P3-T29d, Sonnet (INF-4, DAT-4): Water holds only water features and islands: a sea, an ocean or a lake contains bays, straits and islands, never rivers, roads, railways or towns at the coast.
* P3-T29e, Opus (INF-5, INF-6): Overlapping. For an area: areas of other layers partly covering it; lines partly inside it, each with its crossings, opening to each crossing point; lines along its border. For a line: the areas it passes through, from its start, each with its share. For a place: nothing.
* P3-T29f, Sonnet (ANN-2): Passed over: places said "passed nearby to Winchester", and the group sortable, along the path first.
* P3-T29g, Sonnet: How you hear a group's sort order, as you choose in R4.

Within and Up for a line wait for R3.

For a later phase, not in this plan:

* An area's centre as the centre of its largest part, such as Great Britain for the United Kingdom (your note on Within).
* Networks: rivers joining rivers and lakes, roads and railways joining, and lines crossing lines, if you agree in R5.
* The user guide: a screen reader's object navigation can read the current location from the map, through its accessible name.

## 3. The coast as a border, task P3-T30

Your answer to Q3: the coast like a neighbour, with its length and its ends, where it meets the next area along the coast, such as West Sussex, Portsmouth, Southampton, and Bournemouth, Christchurch and Poole for Hampshire.

* P3-T30a, Opus: Run on a small sample first: Hampshire and its neighbours, from the Western Europe trial's data on disk. A report for you, with each stretch of coast, its length and its ends.
* P3-T30b, Opus: If you approve, a build stage for every area, timed on the Western Europe trial before the world build.

## 3a. Key maps, task P3-T31

Agreed with you on 19 November 2026. The words are in the glossary: command list, key map, your keys, key file, keyboard layout.

### The definition

* Five key maps, each a file read when TobyMap starts: Windows desktop, Mac desktop, Windows browser, Mac browser, and Alternative.
* Keys are written once for both systems where they can be: one modifier means Ctrl on Windows and Cmd on a Mac, as Visual Studio Code does. A Mac key map lists only the keys that differ, such as those that clash with VoiceOver (Control+Option) or with macOS itself.
* Alternative avoids Ctrl+Alt with a letter, which is AltGr on many European keyboards, and keys that move between layouts, such as punctuation.
* The command list keeps the commands, where each works and its menu; the key maps hold the keys.
* In Settings: choose a key map, change any key, Save as a key file, Open a key file. Reset gives back the chosen key map's own keys.
* Your keys are kept as changes on top of the chosen key map, never as a full copy, so a key added in a new version still reaches you. A key file says which key map it is based on.
* When TobyMap first starts, it picks the key map for your system and version. This is where detecting the keyboard layout fits later: the desktop can ask Windows or macOS, and Chrome and Edge can tell the page, but Firefox and Safari cannot. Detection itself is not in this task; the place for it is.
* How a key is recognised stays as today: a letter by the letter it types, Shift with a number by the key's position.
* docs/design/keymap.csv, made from the key map files by tools/make_key_list.py, replaces docs/plan/phase-3-keys.csv. Columns: Command, Where it works, Windows desktop, Mac desktop, Windows browser, Mac browser, Variations, Notes on the variations. The variations come from a small list of common keyboard layouts kept in the repository (UK, US, US International, German, French, Spanish, Italian, Nordic, Polish, Czech and its neighbours, Mac layouts). A test fails if the file is out of date. Before the old file goes, every comment in its "Your key" column is checked and any still open is listed for you.
* The Mac keys are chosen by me, as sensibly as I can, from Apple's and VoiceOver's own keys. You asked not to review them.

### The tasks

* P3-T31a, Opus: the key map files, how they are read, and your keys as changes on top; the Mac and Alternative key maps chosen.
* P3-T31b, Sonnet: Settings in both versions: choose a key map, Save as, Open, Reset.
* P3-T31c, Sonnet: keymap.csv, made by the tool, with the layout list and the test.

## 4. Carried over from the first plan

* P3-T20d, Opus: Speed in the browsers: send a move's answer before the panel is refilled, and run Passed over's search in steps. Proposed on 17 November 2026; waits for your agreement.
* DP208, Opus: Whether Down lists only what is held directly, or everything inside: in the discussion points file, waiting for you. It touches Obwalden's Down list.
* P3-T27, Opus: Writing the requirements for bookmarks and measuring, before Phase 4.
* DP206, parked by you: P3-T28p takes up its towns part.

## 5. The builds, task P3-T21

* P3-T21a, Opus: A Western Europe trial build with P3-T28a, c, d and n, and P3-T30b if approved. Checks and timings on it, with a stall watch.
* P3-T21b, Opus: The world build. I'll tell you before the laptop gets sluggish.

## 6. Testing again, task P3-T22

* P3-T22a, Opus: A short desktop checklist: the steps that changed, the Information panel group by group, and section 20, layer sounds.
* P3-T22b, Sonnet: The web and sighted checklists, brought up to date.
