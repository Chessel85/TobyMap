# P4-T1h report: matching to the world pack

Written by Claude Code, 26 November 2026. Design: docs/plan/p4-t1-design.md section 3.11.

## What was done

* A new stage, match (mapdata/stages/match.py), in the three regional pack files, after the points of interest and villages and before Wikidata and relationships. It reads the world pack (the source world-pack) and gives each feature of the ten layers both packs have the world pack's identifier: by the same identifier, then by Wikidata, then by name, type and overlap. A matched feature keeps its own identifier as an alias, and every parent and "within" that names it is changed too.
* An identifier the world pack uses in another layer gets the ending "#as-" and its layer.
* The stage writes matches.csv and match.json. The quality report has a new section, "Matches with the world pack", with matches made by name listed first, so a wrong match is easy to find. A pack with no match stage says so.
* Architecture 6.7 now says the world pack itself is the identifier register. The glossary has "alias". The settings are in docs/data-manager/configuration.md.

## On the regional test pack

* 4 features kept the test pack's identifier, among them Hampshire, England and the United Kingdom.
* The River Itchen took the test pack's identifier by Wikidata, with its own as an alias.
* 1 bus stop's identifier, used by the test pack's stations layer, was given the ending of its layer.
* Every parish sits under a district whose parent is the test pack's Hampshire.

## Not yet known

* How long the stage takes on Great Britain. It reads every feature record of the world pack once, and the world's pack tiles inside the coverage. The rehearsal (P4-T1j) will measure it. The world pack must be built before the rehearsal.
