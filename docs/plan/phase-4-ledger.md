# Phase 4: progress ledger

The orchestrator's record of work on docs/plan/phase-4-plan.md. Only the orchestrator (Opus, the main session) edits this file. Subagents never do.

## How the work is run

* The PO's instructions are in toOrchestrate.txt (20 November 2026): one work item at a time, each by a fresh subagent, Sonnet or Opus as the plan labels it, told which files it may change; the orchestrator checks the diff and runs that area's tests, then commits under the work item's ID and pushes.
* The working tree must be clean before a subagent starts (apart from toOrchestrate.txt, the PO's). Subagents do not commit and never edit this ledger, the task list or the discussion points file unless told.
* Each subagent runs only its own area's tests. The full Python suite and the browser tests run at the end, or after a task whose changes reach widely.
* Overnight, nothing that needs the PO is started. Choices the orchestrator makes are listed under "Overnight choices for the PO".
* When the code changes are done, the world pack is rebuilt (P4-T15). The build runs from a snapshot copy of the repository (a detached git worktree, C:\Users\chess\github\Mapping-build, with paths.yaml copied in and MAPDATA_SWITCH pointing at the main folder's continue.txt), so work in the core can carry on without changing the code under the running build. mapdata imports mapcore.geo, packs, store and names, which is why.

## The PO's answers, 20 November 2026

* DP218: no release yet.
* DP219: yes, the bookmarks design as written.
* DP220: agreed, ranges cut to the coast. The PO asks whether other kinds can be cut to the coast too: roads, railways, lakes, deserts.
* DP221: the recommendation, a correction rule renaming the area.
* DP222: yes, Phase 4 takes a serious look at the browser version.
* DP223: Great Britain as Geofabrik draws it.

## Night plan, 20 to 21 November 2026

Started 22:10. About 10 hours. The whole phase does not fit in one night, so the order is:

1. Work that changes the world pack, so the rebuild can start in the small hours: P4-T14i (coast stretches), P4-T5, P4-T4 (with DP221's rule), P4-T11a, DP220 (ranges cut to the land), P4-T12 (territorial waters), each rehearsed on the Western Europe trial.
2. The world rebuild, P4-T15, from a snapshot copy, with the run switch and a stall watch.
3. While it builds, work in the core and shells only: P4-T14's other items, P4-T0d, P4-T0f, then bookmarks (P4-T8, P4-T9), P3-T15 Help, the two unreliable browser tests.

Not started tonight, as they need the PO: P4-T14f's change (the PO sees the list first), P4-T13 (the source of groups of islands is a choice for the PO), P4-T1 and P4-T2 (long design work and builds the PO is told about first), P4-T6h and P4-T11b (publishing), P4-T7b (an hour with the laptop idle), P4-T10 (listening with the PO).

## Progress

* P4-T14i done, checked (22 tests): coast stretches split where the sea changes and short same-neighbour stretches (estuaries of the Dee and the Tweed) joined; settings join_km and sea_km, 20 each. Western Europe trial rebuilt 20 November about 22:40 (coast-stretches, writing, checks only, 6 min 12 s, 53.39 MB, 60 of 60 places). England now: Bristol Channel 610 km, English Channel 1,570 km, Irish Sea 760 km, North Sea 1,910 km, islands 1,420 km. Report: docs/plan/p4-t14i-coast-report.md. Glossary and configuration guide updated by the orchestrator. Left over: no Celtic Sea in Natural Earth's seas; Milford Haven reads as the Irish Sea (a seas-layer fault, not this stage).

## Overnight choices for the PO

* P4-T14i: the plan said you would see the new coast list before it went into the world pack. As you asked for a world build tonight, it goes in; the list is in docs/plan/p4-t14i-coast-report.md. A change afterwards reruns only the coast stretches, writing and checks stages (about 1.5 hours on the world).

## Current state

Last updated 20 November 2026, 22:15. Starting the night plan at item 1.
