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

* Working on: P3-T29f.
* git stash holds "P3-T28d unfinished". Keep it until P3-T28d is run again.

## Done

* P3-T28a, b, c, f, g, h, i, j, k, l, m, o, q.
* P3-T29a.
* P3-T29b: Nearby and look around leave out a place you are at, and Nearby keeps its count. The template nearby.here is no longer used by Nearby; left in place.
* P3-T29d: contents.water_may_hold. Oceans and seas hold oceans, seas, sea-places and islands; lakes hold islands and sea-places (bays on lakes, which P3-T28c keeps: the orchestrator's addition to the definition, tell the PO). Applied in Contains, Down and Browse by category. The test pack has no sea holding a river, so its tests patch Longbridge Lake's relationships.

## To do, in order

2. P3-T29d, Sonnet: Water holds only water features and islands.
3. P3-T29f, Sonnet: Passed over, "passed nearby to Winchester" (R6), sortable.
4. P3-T29g, Sonnet: the group heading says its sort order; Ctrl+S and Ctrl+Shift+S put focus on the heading (R4).
5. P3-T29h, Sonnet: Within, from R3: on a point or a line, that feature is the top item, such as "River Itchen, Hampshire, England, United Kingdom". Added by the orchestrator, as the plan said Within waited for R3, which is answered.
6. P3-T29c, Opus: Contains, wholly inside, limited by the view by nearest point (R2). Timed on the world pack.
7. P3-T29e, Opus: Overlapping.
8. (No local test run here: continuous integration runs the browser tests on push.)
9. P3-T28r, Opus: the Sea of the Hebrides slivers, a seas-stage fault. Rehearsed on Western Europe data.
10. P3-T28n, Opus: share inside measured on land only. Rehearsed on Western Europe data.
11. P3-T28d, Opus: far-apart roads split, from a sample of named roads only.
12. P3-T28p, Opus: "Near Winchester", distances proposed for the PO.
13. P3-T31a, Opus; P3-T31b, Sonnet; P3-T31c, Sonnet: key maps. The full Python suite after P3-T31a, as key maps reach every command.
14. P3-T30a, Opus: the coast as a border, a report on Hampshire for the PO.
15. P3-T27, Opus: requirements for bookmarks and measuring.
16. Speed of the visible rule, Opus: run test_the_rule_takes_under_25_ms_a_frame_on_the_world_pack alone on a quiet laptop, several times, and propose to the PO a limit from what is measured. Then the end-of-plan run of the full Python suite and the browser tests.

## Waiting for the PO

* P3-T20d: speed in the browsers, waits for agreement.
* DP208: what Down lists.
* P3-T30b: waits for approval of P3-T30a's report.
* P3-T21a and P3-T21b: the builds. The PO is told before they start.
* P3-T22a and P3-T22b: checklists, after the builds.

## Decisions

* 19 November 2026, the PO: the visible rule's speed test limit relaxed from 10 ms to 25 ms, as it often failed on a busy laptop (20.9 ms with the browser tests running). Measured again as item 16.
* 19 November 2026: R1 option B; R2 Contains limited by the view; R3 Within gets the point or line on top; R4 sort order in the heading, focus to the heading on Ctrl+S; R5 networks later; R6 "passed nearby to", "Passed over".
