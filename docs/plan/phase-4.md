# Phase 4 task list

Phase 4 is street detail: the England pack (planned as Great Britain), combining packs, the whole pack manager, bookmarks, and the data manager's tools. The tasks are described in "implementation plan.md", section 7, and in detail in phase-4-plan.md, which raises DP218 to DP223 and splits each task into work items, each labelled Opus or Sonnet. This list shows what is done.

Planned on 20 November 2026, when you closed Phase 3. You answered DP218 to DP223 on 20 November, and work started that night. The orchestrator's record of each work item, its checks and the choices made for you is docs/plan/phase-4-ledger.md.

## Start of the phase

* [ ] P4-T0a Versions: newer PySide6 and Pyodide. Not started.
* [x] P4-T0b The questions: DP218 to DP223, added on 20 November 2026.
* [x] P4-T0c The implementation plan, version 0.9, written on 20 November 2026.
* [x] P4-T0d The requirements and documents for bookmarks, 21 November 2026.
* [ ] P4-T0e Samples for the test pack: Winchester's streets, part of the New Forest, the coast at Lymington.
* [x] P4-T0f The key list for Phase 4: a key plan, docs/plan/p4-t0f-keys.md; each key goes in with its command.

## Your notes on the Phase 3 tidy-up 2 checklist

* [ ] P4-T14 Your notes of 20 November 2026: P4-T14a to P4-T14m. All done on 21 November except P4-T14f, a proposal waiting for you (docs/plan/p4-t14f-messages.md); P4-T14n added for faults found on the way, done.

## Carried from Phase 3

* [ ] P3-T15 Help.
* [ ] P3-T20d Speed in the browsers, if DP222 says yes.
* [x] The two unreliable browser tests, and the macOS held-key test, 21 November 2026.
* [ ] P3-T22 The web and sighted checklists, folded into Phase 4's.

## The data manager's tools

* [x] P4-T5 Pipeline safety in full, 20 November 2026.
* [x] P4-T4 Corrections by rule, with DP221's rule, 20 November 2026.
* [ ] P4-T11 Quality reports (P4-T11a, done 20 November 2026) and the publish command (P4-T11b).

## Street detail

* [x] P4-T1 The regional pipeline, rehearsed on Hampshire and the Isle of Wight: 43.22 MB, 20 of 20 check places; Great Britain estimated at about 1.3 GB (docs/plan/p4-t1j-rehearsal-report.md).
* [x] P4-T1l Memory: no stage over 12 GB a process for the England build (the PO, 26 November 2026). Done with P4-T1m, 27 November 2026.
* [x] P4-T1m The writing stage group by group: about 5 to 7 GB for England, not 20 to 30; the pack the same byte for byte, 27 November 2026 (docs/plan/p4-t1m-report.md).
* [ ] P4-T2 The England pack (England only, the PO, 26 November 2026; planned as Great Britain). Work items, each its own session:
  * [x] P4-T2a Estimate and get ready, 26 November 2026: about 850 MB, about 6 million features, 4.5 to 7 hours with --away, no process expected over 12 GB (docs/plan/p4-t2a-estimate-report.md).
  * [x] P4-T2b The build, 26 to 27 November 2026: 968.3 MB, 6,328,884 features, about 4 hours with --away; a slow step in writing fixed (docs/plan/p4-t2-england-report.md).
  * [x] P4-T2c Size by layer: under 1 GB, so no proposal; land use 184 MB, streets 145 MB, paths 97 MB, the pack's own records 317 MB.
  * [x] P4-T2d Checks: 45 of 45 check places (tests/acceptance/street_places_england.yaml added), streets, islands, the sea off Cornwall; steps 99.3 percent within 150 ms (NFR-1).
  * [ ] P4-T2e Built twice, identical: waits for your yes.
* [ ] P4-T3 Combining packs.
  * [x] P4-T3a Several packs open together, 27 November 2026: the regional pack answers for its layers in its covered pack tiles, the world pack everywhere else and for its other layers; drawn together below 250 kilometres.
  * [x] P4-T3b Features and relationships merged, 27 November 2026: a feature both packs hold is one feature, with the whole feature's record; Within, Contains and Bordering give one Hampshire; a parish sits under the world pack's county, and above the country the world pack's holders follow; an alias finds its feature.
  * [x] P4-T3c Search across packs, 27 November 2026: one search over both packs; a feature both hold is listed once, described by the pack that holds all of it, with the better of the two packs' match and importance.
  * [ ] P4-T3d The web version with two packs.
  * [ ] P4-T3e At the edge of the pack.

## Bookmarks

* [x] P4-T8 Bookmarks, P4-T8a to P4-T8g, 21 November 2026.
* [x] P4-T9 Measuring from a bookmark, and bookmark files, P4-T9a to P4-T9d, 21 November 2026.

## The world pack

* [x] P4-T12 Territorial waters, 21 November 2026.
* [ ] P4-T13 Groups of islands.
* [ ] P4-T15 The world pack rebuilt: built 21 November 2026, 552.46 MB (P4-T15b), checklist checked on it; built twice identical (DMT-1) still to do. A second rebuild will follow P4-T13 and P4-T1h.

## Packs for users

* [ ] P4-T6 The pack manager, ending with the test release.
* [ ] P4-T7 Robustness and memory.

## Languages

* [ ] P4-T10 The NVDA language harness. On hold: you want to understand it better first (21 November 2026).

## Closing the phase

* [ ] The checklists for the desktop, the web and a sighted helper.
* [ ] The phase report, docs/plan/phase-4-report.md.
* [ ] Your acceptance.
* [ ] The question about publishing (DP110, DP218).
