# Phase 3 report: information, hierarchy and search

Written on 20 November 2026, when you closed Phase 3 after the tidy-up 2 desktop checklist. It follows section 1.5 of the implementation plan.

## Where the phase stands

* You closed the phase on 20 November 2026, from your results in docs/checklists/phase-3-tidy-up-2-desktop results.txt. Most steps passed. Your notes on them are a task of Phase 4, P4-T14.
* You chose not to run the web and sighted checklists now, and not to build a new world pack. Both move to Phase 4: the checklists into Phase 4's, and the world pack into P4-T15.
* The version is 0.1.1. No release: DP218 asks again, with a recommendation to wait for the end of Phase 4.
* The detail of what was done is in docs/plan/phase-3.md, and in the two tidy-up plans, docs/plan/phase-3-tidy-up.md and phase-3-tidy-up-plan2.md with its ledger.

## What was built

* The complete base pack, now the world pack: countries, regions and constituent countries, counties, continents, named seas, bays and straits, islands, mountain ranges, physical regions, peaks, major rivers, lakes, roads, railways and towns (P3-T1, P3-T17).
* Facts from Wikidata with their sources, Wikipedia links, and disputed and unclaimed areas (P3-T2, P3-T16).
* Relationships worked out in the build: containment, neighbours with shared lengths, overlaps, crossings, and stretches of coast (P3-T3, P3-T30b).
* The Information panel's seven groups, with sorting and their order in each heading; the Details region; hierarchy mode; measuring; search; the world tree, browse by category and the query builder; look around; names in English and the local language (P3-T4 to P3-T12).
* Controls for sighted users, map views, key maps, and "Near Winchester" (P3-T18, P3-T23 onwards, P3-T28, P3-T31).

## How to install and run it

* Desktop, from the repository: `.venv\Scripts\python.exe -m desktop --pack E:\osmdata\tobymap\output\world\world.pack`, or the Western Europe trial you tested on.
* Web: `.venv\Scripts\python.exe tools\serve_web.py --pack E:\osmdata\tobymap\output\world\world.pack`.

## The automatic checks

* The full Python suite: 2,114 passed on 20 November 2026, after the last change (P3-T33b).
* The browser tests: 238 passed in Chromium and Firefox at the end of tidy-up plan 2.
* The world pack of 20 November: every check passed, 536.3 MB against the soft limit of about 400 MB (PCK-1), which you accepted.

## Known problems

* The world pack of 20 November does not have what came after it: the stretches of coast, the search importance changes, and the islands stored for each sea, which make Contains on a sea slow the first time. The Western Europe trial has them. The world rebuild is P4-T15.
* Your notes in the tidy-up 2 results, listed in P4-T14 of docs/plan/phase-4-plan.md.
* The British Isles' rough outline makes Cornwall, Essex and the Isle of Wight overlap it, and Washington state is hard to find by search.
* Two browser tests fail now and then in continuous integration. Carried to Phase 4.

## What was not tested

* The web checklist and the sighted checklist of the tidy-up 2 pass.
* Sets 10 (search) and 18 of the tidy-up 2 desktop checklist, and step 6.6, which had no bay at the place.
* Help (P3-T15) was not written; it is carried to Phase 4.
* Speed in the browsers (P3-T20d) waits for your answer, DP222.
