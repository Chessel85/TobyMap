# mapdata: rules for the pipeline

Read architecture sections 6 and 8, and `docs/design/data sources.md`, before changing the pipeline.

* The data folder comes from `mapdata/paths.py` (AD-18). Never write a drive letter into code or into the shared configuration.
* mapdata writes only inside `<data folder>/tobymap`. The rest of the data folder belongs to the PO (planet and UK .osm.pbf and .gol files, and older work). Read those files, never change or delete them (DP75).
* Output is plain lines, suited to a screen reader (DMT-2). No progress bars that redraw a line, and no tables.
* Report wording follows `docs/design/glossary.md`, for example land tile, pack tile, tile entry, part and reading box. Never "piece" on its own.
* Every source used must be listed in `data sources.md` with its licence, and must be compatible with distributing packs under ODbL.
* Countries are cut to the coast with the OSM land polygons (AD-15), and shared borders are simplified once (AD-16). Do not splice coastline ways into boundaries, which is the approach that failed in AtlasDL.
