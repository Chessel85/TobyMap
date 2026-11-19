# Phase 3 tidy-up plan 2: progress ledger

The orchestrator's record of work on docs/plan/phase-3-tidy-up-plan2.md. Only the orchestrator (Opus, the main session) edits this file. Subagents never do.

## How the work is run

* One task at a time. Each task goes to a fresh subagent, Sonnet or Opus as the plan says, told which files it may change.
* The working tree must be clean before a subagent starts. The subagent does not commit.
* The orchestrator checks the diff, runs that area's tests, then commits under the task's ID and pushes.
* Each subagent runs only the tests of its own area. The full Python suite runs only at the end of the plan, or after a task whose changes reach widely, such as P3-T31a (the PO, 19 November 2026). Browser tests are left to continuous integration on each push, not run locally.
* Long builds (P3-T21a, P3-T21b) and anything waiting on the PO are not started without the PO.

## Current state

Last updated 19 November 2026.

* Paused by the PO after P3-T29e (19 November 2026): "let the current agents finish but don't start any more". Resume with item 1a below when the PO says so.
* git stash holds "P3-T28d unfinished". Keep it until P3-T28d is run again.

## Done

* P3-T28a, b, c, f, g, h, i, j, k, l, m, o, q.
* P3-T29a.
* P3-T29b: Nearby and look around leave out a place you are at, and Nearby keeps its count. The template nearby.here is no longer used by Nearby; left in place.
* P3-T29d: contents.water_may_hold. Oceans and seas hold oceans, seas, sea-places and islands; lakes hold islands and sea-places (bays on lakes, which P3-T28c keeps: the orchestrator's addition to the definition, tell the PO). Applied in Contains, Down and Browse by category. The test pack has no sea holding a river, so its tests patch Longbridge Lake's relationships.
* P3-T29f: places said "Passed nearby to Winchester, closest ..." (name after the words, as the PO chose). Ctrl+S already reached the group; a test now guards it. Test names and comments in test_hear_direction.py, test_window.py, tests/web still say "Crossed and passed": harmless.
* P3-T29g: headings say their order ("Nearby, 8 items, by distance"). Ctrl+S moves focus to the heading and says nothing; when focus is already on the heading, the core speaks the new heading once. For the PO to check with NVDA on the desktop: no double speech. The sort.* templates are unused, left in place.
* P3-T29c: Contains lists only what is wholly inside, in the view by each feature's real nearest point (Store.nearest_many: points together, areas you are in by Store.at, far features on drawing tiles within 2 percent, near ones exact); "you are inside", a line or place you are on "here"; bays and straits one subgroup. Down from Europe loses Azerbaijan, Georgia, Kazakhstan, Turkey; world tree and browse unchanged. World pack timings, Contains filled: England 0.22 s (0.18 before), Europe 3.6 s (3.3 before); Down's _contained on Europe 2.5 s (0.69 before), mostly tiles re-read as the 96 MB tile cache is too small; 400 MB gives 1.5 s. Raising the cache is left for P3-T20d or P7-T4a (it costs browser memory).
* P3-T29e: Overlapping, from stored relationships only, each item measured to its nearest point. For an area: areas of other layers (and of its own layer) by layer with both shares, leaving out shores and its coast waters; "Lines crossing its border", opening to each crossing; "Lines along its border". For a line: areas from its start with shares, not those holding all of it. A place: nothing. The old Crossing code and templates are gone. World pack, first open: England 1.85 s, Germany 1.94 s, Thames 0.11 s, Rhine 0.22 s; later opens 0.15 s or less.
* For the PO, from P3-T29e: (1) coast waters left out of an area's Overlapping, so West Sussex does not list the North Atlantic at 1 percent; (2) same-layer overlaps kept, as they would be in no group; (3) a line lists areas with under 1 percent of it inside, "less than 1 percent": about 70 of the Thames's 77 items are small islands; dropping them is an option.
* P3-T29h (added by the orchestrator from R3): a current line or place is Within's first item, measured with Store.measure (as Nearby), "River Itchen, here". Up from a line already went to the smallest area holding it; now tested.

## To do, in order

1a. Browser test race, Sonnet: test_enter_on_a_layer_check_box_presses_ok_and_never_ticks_it fails now and then in continuous integration (Chromium on c866cad, Firefox on a602b2f): "Nothing to go to" is said in place of "Kent, England, United Kingdom", as if the Enter that closes the Layers dialog also reached the map.
2. P3-T28r, Opus: the Sea of the Hebrides slivers, a seas-stage fault. Rehearsed on Western Europe data.
3. P3-T28n, Opus: share inside measured on land only. Rehearsed on Western Europe data.
4. P3-T28d, Opus: far-apart roads split, from a sample of named roads only.
4b. Build fixes found in P3-T29e, Opus: (1) the world pack stores no crossed_at, so no crossing points or counts; (2) many roundabouts and interchanges are exactly 50 percent inside England, likely a closed way counted twice in the line's length; (3) store on each area only the lines partly inside it (such as partly_by), so a first open of Overlapping for England falls from about 1.9 s to about 0.3 s.
4a. Build fix found in P3-T29c, Opus: Down's "in all" counts (stored holds) still count features only partly inside; count only wholly inside, to agree with Down's list.
5. P3-T28p, Opus: "Near Winchester", distances proposed for the PO.
6. P3-T31a, Opus; P3-T31b, Sonnet; P3-T31c, Sonnet: key maps. The full Python suite after P3-T31a, as key maps reach every command.
7. P3-T30a, Opus: the coast as a border, a report on Hampshire for the PO.
8. P3-T27, Opus: requirements for bookmarks and measuring.
9. Speed of the visible rule, Opus: run test_the_rule_takes_under_25_ms_a_frame_on_the_world_pack alone on a quiet laptop, several times, and propose to the PO a limit from what is measured. Then the end-of-plan run of the full Python suite and the browser tests.

## Waiting for the PO

* P3-T20d: speed in the browsers, waits for agreement.
* DP208: what Down lists.
* P3-T30b: waits for approval of P3-T30a's report.
* P3-T21a and P3-T21b: the builds. The PO is told before they start. The PO (19 November 2026): finish the development work first. The Western Europe trial is the right size for P3-T21a (about 23 minutes); a smaller area would miss Islay, Belfast and the Moselle.
* P3-T22a and P3-T22b: checklists, after the builds.

## Decisions

* 19 November 2026, the PO: the visible rule's speed test limit relaxed from 10 ms to 25 ms, as it often failed on a busy laptop (20.9 ms with the browser tests running). Measured again as the last item of the to-do list.
* 19 November 2026: R1 option B; R2 Contains limited by the view; R3 Within gets the point or line on top; R4 sort order in the heading, focus to the heading on Ctrl+S; R5 networks later; R6 "passed nearby to", "Passed over".
