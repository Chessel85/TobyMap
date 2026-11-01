# Data sources

Version 0.7, 1 November 2026. The product owner's original notes are kept unchanged in the first section. Everything after that is the architect's research and recommendations, for review.

## Changes in version 0.7

* Shortbread, the open vector tile schema from Geofabrik, is used as a starting point and quality check for which OSM features go in each layer, and from which zoom they appear. It is a reference only: no code or data is taken from it. This came from a reply to the PO's OpenStreetMap forum post.

## Changes in version 0.6

* Coastline and land: how countries are cut to the coast, why that removes territorial waters whatever the administrative level, and how slivers are handled. The full method is in architecture section 6.12.
* Countries: a "country units" list splits places such as French Guiana from France (DP86). Gibraltar is its own entry, and Ceuta and Melilla stay in Spain.
* New "Islands" section: named islands, unnamed islands (DP87), and the UK's thousands of islands.
* The base pack's countries might come from OSM rather than Natural Earth, if spike S2 shows they fit (DP89).
* The OSM land polygons are not yet on drive E:. Spike S2 downloads them, about 1 GB.
* Graticule: corrected to match the architecture. Lines of latitude and longitude are stored in the base pack as data (AD-11), because that keeps the graticule a layer like any other.
* AtlasDL used Natural Earth and Marine Regions, and GeoDesk on the planet file. Those choices carry forward.

## Changes in version 0.5

* The files on drive E: are kept for now (DP75).
* The pipeline may use GeoDesk and the GOL files. This was left to me in DP75, and I recommend it, subject to a licence check in the pipeline spike.
* You said I may look at anything in E:\osmdata. I have now read your notes, the batch file and the web folder. What I learned is in "Data already on drive E:".
* Each layer now has a zoom range and its own sounds, set in the pack configuration (SCP-7, DP74). This affects how the pipeline describes layers, not which sources are used.

## Changes in version 0.4

* Seas and oceans: how the water hierarchy is built (UXReview, LOC-6, DAT-4).
* New layer: graticule and special lines (DAT-13, DP74).
* The build machine section now records the laptop's memory and processor, and what data is already on drive E: (DP60).
* Regional packs follow Geofabrik's boundaries, and climate grids are separate packs. Both agreed (DP59).

## Changes in version 0.3

* Licensing is settled: the code is GPL-3.0 and the packs are ODbL (DP40).
* Hosting is settled: GitHub Releases (DP48).
* Pack sizes: the base pack has a soft limit of 250 MB, and other packs aim for 1 GB or less (DP50). The volumes section now shows what fits in 250 MB, and proposes separate grid packs (DP59).
* Wikidata and Wikipedia are accepted as sources for facts (DP51).
* Continents built from groups of countries are agreed (DP55).
* New section on the build machine: your laptop with the external SSD (DP53, DP60).

## Product owner's initial notes

* OpenStreetMap is free and very broad.  Cons are that it is very large, does not have much information on oceans and seas, includes maritime borders at the highest admin level data making it hard to tell where the physical land/sea boundary is for sovereign level polygons.
* Natural Earth  is free and more compact but does not contain the wealth of information desired for this solution e.g. Road networks.
* IHO (International Hydrological Organisation) has numerous shapefiles available for download providing ocean and sea specific data
* Various data  sources for specific features can be found e.g. mountains, deserts.

---

## Summary of recommendations

1. OpenStreetMap (OSM) is the backbone for regional detail and for most named features worldwide.
2. Natural Earth is the backbone for the worldwide base pack. It is small, public domain, and its features are already generalised and cleanly named.
3. Coastlines are fixed by clipping administrative areas against the OSM land polygons. This is the standard approach, and it resolves the land and sea boundary problem in the PO's notes.
4. Oceans and seas come from the Flanders Marine Institute's (VLIZ) "Global Oceans and Seas" dataset, which is based on IHO S-23 and published under CC-BY 4.0. It is preferred over the "IHO Sea Areas" download, which appears to carry a non-commercial share-alike licence (see the licence warnings below).
5. Elevation and depth come from the GEBCO grid. It is public domain and covers both land and sea in one grid.
6. Climate grids (precipitation and temperature) come from CHELSA, which is CC0. WorldClim does not allow redistribution, so it cannot be used.
7. Wikidata (CC0) supplies population, area, Wikipedia links and multilingual names. OSM features usually carry a Wikidata ID, which makes the join reliable.
8. Specialist sources fill gaps: the GMBA mountain inventory for mountain ranges, and HydroLAKES for lakes in the base pack.

## Licence warnings found during research

These change what we can use, so please read them even if you skip the rest.

* World Database on Protected Areas (WDPA, Protected Planet):
  * It cannot be redistributed in any form without written permission. That includes downloads, web services and interactive maps.
  * It must not be used. Protected areas will come from OSM instead (tags boundary=national_park and boundary=protected_area).
* WorldClim 2.1:
  * It is free for non-commercial use, but redistribution needs permission.
  * Because we ship data packs, it must not be used. Use CHELSA instead.
* IHO Sea Areas v3 (Marine Regions):
  * Its catalogue record gives the licence as CC-BY-NC-SA 4.0.
  * Non-commercial matches the PO's wishes, but share-alike clashes with OSM's own share-alike licence (ODbL) if the two are merged into one database.
  * Use VLIZ Global Oceans and Seas (CC-BY 4.0) instead. If the IHO set is ever needed, keep it as a separate layer.
* OSM's ODbL licence, for the whole project:
  * Our packs are a derived database, so they must be published under ODbL and credited "© OpenStreetMap contributors".
  * ODbL allows commercial use, and we cannot add a non-commercial condition to OSM-derived data. Settled in DP40: OSM is too valuable to exclude, so the packs are ODbL and the code is GPL-3.0.
* The Copernicus DEM licence allows free use, but I have not yet confirmed its redistribution terms. GEBCO avoids the question for v1.
* HydroRIVERS: I have not yet confirmed the licence from a primary source. HydroLAKES is CC-BY 4.0. OSM and Natural Earth rivers are enough for v1 anyway.

## Sources by layer

### Oceans, seas, bays, straits
* Primary source: VLIZ Global Oceans and Seas v1 (DOI 10.14284/542), CC-BY 4.0. It is based on IHO S-23 (1953) and covers oceans and named seas.
* Smaller marine features, such as bays and inlets: Natural Earth "marine polys" (public domain) for the base pack, and OSM natural=bay and natural=strait for regions. In OSM these are often only points or lines, so for some features we will have a name and a point but no area.
* Undersea feature names, such as trenches and ridges: the GEBCO gazetteer. Could priority.
* The water hierarchy (oceans containing seas, seas containing seas, bays, straits and gulfs) is built by the pipeline from containment between these sources, in the same way as the land hierarchy. VLIZ divides the oceans into named parts, such as the North Atlantic Ocean, and the IHO seas nest inside them. Natural Earth and OSM bays and straits are placed inside the sea that contains most of their area.
* Where VLIZ seas overlap the Natural Earth or OSM features of the same name, the VLIZ boundary wins, and the other is used only for its name and Wikidata link. This is checked in the quality report.

### Graticule and special lines
* Lines of latitude and longitude are written into the base pack by the pipeline at every 1 degree, and the interval the user chooses filters them (architecture AD-11). This keeps the graticule an ordinary layer defined by configuration, and costs well under 1 MB.
* The equator, tropics, polar circles and the international date line come from Natural Earth "geographic lines" (public domain). The date line is not a straight line, so it must come from data.
* Agreed (DP74): this is an ordinary layer. Its definition, including its crossing earcons, is configuration (SCP-7).

### Coastline and land
* OSM land polygons from osmdata.openstreetmap.de, under ODbL. They are updated daily and come in a detailed version and a simplified version. The detailed version, split into small pieces, is about 1 GB. It is not on drive E: yet, so spike S2 downloads it.
* They are made by the OpenStreetMap project's OSMCoastline program, which joins every natural=coastline way in the world into closed land shapes, closes small breaks and reports errors. We never have to join coastlines ourselves, which is where AtlasDL ran into trouble at Gibraltar.
* Every land area, at every administrative level, is intersected with them. This removes territorial waters, estuaries and bays from any boundary that includes them, and changes nothing where a boundary already follows the coast. So it does not matter which levels include territorial waters (your question in "architecture thoughts.txt").
* Thin strips of land left in no country, where a boundary runs just inland of the coast, are given to the neighbouring country and listed in the quality report.
* Natural Earth land (public domain) is used for the generalised base pack, unless DP89 moves the base pack to OSM.

### Countries and administrative divisions
* Base pack: Natural Earth admin-0 (countries) and admin-1 (first-level divisions). These are public domain and land-clipped already. Natural Earth also provides "points of view" for disputed areas, which fits DP28.
* Regional packs: OSM administrative boundaries at all levels, clipped to the OSM land polygons.
* Which level is a country: OSM administrative level 2, adjusted by a short "country units" list (architecture 6.12). For example, France's level 2 area includes French Guiana, Guadeloupe, Martinique, Réunion and Mayotte. The list replaces it with Metropolitan France (OSM level 3) and each overseas region as its own entry, with France recorded as the sovereign state. Natural Earth's "map units" are used to check the list. Gibraltar is its own entry. Ceuta and Melilla stay part of Spain.
* Base pack option (DP89): build the base pack's countries and first-level divisions from OSM too, cut to the land and simplified. This would give the same identifiers and the same coastline approach at every zoom. Natural Earth would still provide the disputed-area views (DAT-8) and a fall-back for any country that fails to build. Spike S2 measures whether it fits the 250 MB budget.
* An alternative to consider is geoBoundaries (CC-BY 4.0 for most countries, with a few exceptions per country). It gives harmonised ADM0 to ADM5 levels, which could help the hierarchy mode (DP52). Not recommended for v1, because OSM is more detailed and mixing the two creates boundary mismatches.
* An option to watch is Overture Maps Foundation "divisions". These are OSM-derived (ODbL) and separate land from maritime areas. It is a well-funded, cleaned-up OSM derivative, worth evaluating in the pipeline spike.

### Islands
* Named islands: OSM place=island and place=islet. Where OSM has only a point, the island takes the shape of the land polygon part the point sits on.
* Unnamed islands are part of the land, and of whichever areas cover them. Whether they are also announced as "unnamed island" above a minimum size is DP87.
* The UK has thousands of islands. They cost little, because shapes are stored in small tiles, and islands too small for a zoom level are left out of that level's drawing shapes (architecture 6.9 and 6.12).
* Islands shared between countries, such as Ireland, Usedom and the islands between Sweden and Norway, are split by the land border like any other land.
* Named island groups (OSM place=archipelago) are a later improvement.

### Continents
* No authoritative continent polygon dataset exists. Agreed (DP55): build continents by merging land polygons grouped by Natural Earth's CONTINENT attribute for each country.
* Transcontinental countries, such as Russia, Turkey, Egypt and Kazakhstan, are split along conventional dividing lines, such as the Urals and the Bosphorus. These lines are set in configuration and explained in Help (DAT-12).

### Physical regions
* Mountain ranges: the GMBA Mountain Inventory v2 (CC-BY 4.0). It is a hierarchical inventory of 8,600 ranges, which fits the hierarchy mode well.
* Deserts, plateaus, plains, peninsulas and similar: the Natural Earth geography regions polygons (public domain). They are coarse, but their names are clean.
* Peaks, volcanoes and passes: OSM natural=peak, volcano and saddle points, ranked by elevation and Wikidata prominence for the base pack.

### Water
* Rivers: Natural Earth rivers and lake centrelines for the base pack, and OSM waterways for regions. Rivers in OSM are split into many pieces. The pipeline must join them into whole rivers using OSM's waterway relations and Wikidata IDs, so that "follow the Rhine" works in network mode (NAV-5).
* Lakes: HydroLAKES (CC-BY 4.0, 1.4 million lakes, with area and depth attributes) or Natural Earth for the base pack, and OSM water areas for regions.

### Transport networks
* Base pack: Natural Earth roads and railways (major routes only).
* Regional packs: OSM highway, railway and public transport data.
* For network mode (NAV-5), the pipeline builds a junction-and-link graph from OSM ways. Points of interest along links, such as bus stops and crossings, are snapped to the graph.
* For UK validation only, a useful cross-check is Ordnance Survey's OS Open Roads, together with NaPTAN for bus stops (both under the Open Government Licence).

### Land use, parks, schools, public spaces
* OSM landuse, leisure, amenity and boundary tags. School grounds come from OSM amenity=school areas.
* Coverage varies a lot by country. The quality reports (DMT-3) should flag it.

### Points of interest
* OSM nodes and areas, through a configurable list of categories with friendly names, such as "bus stop", "pedestrian crossing", "waste bin" and "post box". The category mapping is a configuration file, so the data manager can extend it without code changes.

### Settlements and population
* OSM place nodes and Natural Earth populated places.
* Population figures come from Wikidata, falling back to the OSM population tag. Gridded population, such as GHSL or WorldPop (both CC-BY 4.0), is a candidate future grid layer.

### Grid layers
* Elevation and depth: GEBCO grid, public domain with attribution. It is a single global grid at 15 arc-seconds (about 450 m) covering land elevation and ocean depth. The terms say it must not be used for navigation, which is fine for this product.
* Higher-resolution land elevation, such as Copernicus GLO-90, is a later option once its licence is confirmed.
* Precipitation and temperature: the CHELSA climatologies v2.1 (CC0, about 1 km resolution, 1981 to 2010 averages, monthly and annual). Proposal: ship annual and monthly averages, downsampled to about 5 km for the base pack.

### Facts, names and links
* Wikidata (CC0) supplies population, area, capital, multilingual names, Wikipedia article titles and links. Accepted in DP51. Each fact is shown with its source and date, for example "Population 67 million (Wikidata, 2024)".
* We store only the link to each Wikipedia article. Opening it uses the browser, so Wikipedia's CC BY-SA text is never copied into our packs.
* GeoNames (CC-BY 4.0) is an optional extra gazetteer for alternative names and search. It is probably not needed if Wikidata and OSM cover enough.

### Maritime zones (optional political layer)
* Marine Regions EEZ and territorial sea layers. Some versions are listed as CC-BY 4.0, but the licence must be confirmed for the version we use.
* Could priority (DP29).

## How the sources are combined (outline only)

The detailed pipeline belongs in the architecture document. The key processing steps are:

1. Download the sources: for OSM, regional extracts from Geofabrik (free, updated daily); for everything else, the sources listed above.
2. Filter OSM down to the tags we need. This typically cuts the volume by a large factor.
3. Repair invalid geometries, then clip land features to the land polygons.
4. Build whole features from pieces: rivers, roads and multi-part boundaries.
5. Join Wikidata facts using OSM's Wikidata tags.
6. Work out the relations the application needs quickly, then store them:
   * the containment hierarchy
   * neighbours with shared border lengths
   * the line-crossing index
   * the network graph
7. Generalise the geometry for each zoom tier, then write the packs, each with an attribution file and a manifest.
8. Write the layer definitions: each layer's name, style, default zoom range, minimum area size and default sounds (SCP-7, DP80). The zoom ranges decide which features are "visible" at each zoom, so the pipeline can pre-sort features by the zoom at which they appear. Each area also stores its width, so the size rule for visible areas (DP80) costs nothing at run time. That keeps Contains and Nearby fast, even for the whole United Kingdom.
   * The layer definitions start from the Shortbread schema: its layers, the OSM tags in each, and the zoom at which each kind of feature first appears. Where we choose differently, for example because a feature matters more to someone listening than to someone looking, the layer definition says why. The pipeline's quality report lists where our layers and zooms differ from Shortbread's, so the differences are deliberate and reviewed.

Tools likely to be needed are osmium, GDAL/OGR, GEOS through Shapely, and possibly DuckDB with its spatial extension. They are all free and scriptable from Python.

## Rough data volumes (to be measured in the pipeline spike)

* The full OSM planet file is in the region of 80 GB compressed, and several times that once processed. This confirms that whole-planet street detail can never be one download.
* A Geofabrik extract for Great Britain is roughly 1 to 2 GB compressed. After filtering to our tags it should come down to a few hundred MB.

These numbers are estimates from general knowledge. The first pipeline spike will measure them.

### Fitting the base pack into 250 MB

You set a soft limit of 250 MB for the base pack (DP50). My rough budget is:

* Natural Earth vectors (countries, first-level divisions, physical regions, rivers, roads, railways, populated places), generalised: about 40 to 80 MB.
* VLIZ oceans and seas, simplified: about 10 to 20 MB.
* GMBA mountain ranges, simplified: about 10 to 20 MB.
* Major OSM features (larger lakes, peaks, major named features) with Wikidata facts and multilingual names: about 40 to 80 MB.
* Search index and precomputed relations (containment, neighbours): about 20 to 40 MB.
* Elevation and depth from GEBCO at about 5 km resolution: about 25 to 40 MB compressed.

That totals roughly 145 to 280 MB, so 250 MB is achievable but tight. The main levers are how many names and languages are kept, how much the shapes are simplified, and the grid resolution.

The climate grids do not fit. Monthly and annual rainfall and temperature, even at 5 km, would add several hundred MB. Proposal (DP59): grid layers beyond coarse elevation and depth become separate optional grid packs, such as "Climate, world, 5 km" and "Elevation, Great Britain, 90 m".

HydroLAKES, with 1.4 million lakes, is far too large for the base pack. Only lakes above a size threshold, proposed as 10 km², go into it.

### Regional packs

* Regional packs aim to be 1 GB or less (DP50). This is a soft limit.
* Proposed: regions follow Geofabrik's extract boundaries, which are countries, with large countries split into sub-regions. That matches where the OSM data comes from. A region that would still exceed 1 GB is split further.

## Hosting the packs (no budget)

* Decided (DP48): GitHub Releases on the project repository. Other options are considered only if user demand needs them.
  * There is no charge, no limit on the total size of a release, and no bandwidth limit.
  * Each file must be under 2 GiB. Packs will be well under that anyway.
  * A spike must confirm that release downloads support partial (range) requests, which on-demand fetching (PCK-3) and the web version need.
* Fall-back options, kept on record only:
  * Cloudflare R2: 10 GB free storage, with no charge for downloads. It needs an account with a payment card on file.
  * Hugging Face datasets or the Internet Archive: free hosting for large datasets.

## The build machine

The pipeline runs on your laptop (DP53).

* The C: drive is 1 TB but about 80% full, leaving roughly 200 GB. It is used only for the software and for small test builds.
* The external 2 TB SSD has about 40% free, roughly 800 GB. It holds the downloaded sources, working files and finished packs. This is enough for every country-sized build, and probably for one whole-planet build at a time, depending on memory.
* The laptop has 32 GB of memory and an Intel Core i7-1185G7 (4 cores, 8 threads) (DP60). That is comfortable for any country-sized build. Whole-planet work is limited to filtering and cutting extracts with osmium, which streams from disk and needs little memory.
* The external SSD is drive E:. On 30 October 2026 it had about 750 GB free.

### Data already on drive E:

You said I may look at anything in E:\osmdata (DP75).

* planet-2025-10-20.osm.pbf (84 GB) and planet-latest.osm.pbf (84 GB, dated 31 October 2025). These are two OSM planet files about 11 days apart.
* planet-2025-10-20.gol and planet-latest.gol (122 GB each). These are GeoDesk feature libraries built from the planet files. GeoDesk is a fast spatial query engine for OSM data, with a Python version.
* uk.osm.pbf (2 GB, October 2025) and uk.gol (3.5 GB).
* In the web folder: an Africa extract (7.4 GB), a South Africa extract (1.5 GB), and a tilemaker configuration that makes a PMTiles file of administrative boundaries for zoom levels 0 to 6.
* In the output folder: admin2.osm, about 170 MB, and a single relation (r62149, the United Kingdom).
* Your notes: gol.txt, osmium.txt and "Overpass API.txt", plus chain.bat.

What I learned from your notes:

* The GOL files were built with the "--waynode-ids" option. That keeps the node IDs of each way, which is what is needed to find where roads meet. So they can be used to build the network graph for network mode (NAV-5), not just for area queries.
* You found that osmium tag filters given together match any of the tags, not all of them, and solved it by chaining filters in chain.bat. The pipeline will do this kind of filtering in Python instead, so the rules live in one configuration file.
* Your Overpass notes confirm several things the design relies on:
  * Seas in OSM are mostly points, not areas. The North Sea is a point tagged as a locality, though Wikidata links it to an OSM relation. This supports using VLIZ for sea areas.
  * Admin level 6 gives the UK counties, and admin level 4 gives England, Scotland, Wales and Northern Ireland.
  * Rivers are split into many ways. The UK has about 32,000 river ways and about 800 river relations. The pipeline must join them into whole rivers.
  * Wide rivers also have water areas (natural=water with water=river), which must be linked to the river line.
  * Coastline in the UK is about 27,000 ways and 2 million nodes.
* Your tilemaker test points to PMTiles for the visual map. A PMTiles file is one file that a browser can read in parts, using the same range requests we need to check on GitHub. It could serve the web version's map directly from GitHub Releases. I will look at this in the architecture, alongside the globe drawing.

What this means:

* The data is about a year old. That is fine for developing and testing the pipeline. Before the first public release, a fresh UK extract (about 2 GB from Geofabrik) and later a fresh planet file will be downloaded.
* All the files are kept for now (DP75). Together they use about 420 GB. If space on E: becomes a problem, I will ask you before anything is deleted.
* Recommended: the pipeline uses GeoDesk and the GOL files where they are faster, especially for "what is inside this area" and for the road network. The .osm.pbf files stay the master copy, so a build can always be repeated from them with osmium alone. The GeoDesk licence is checked in the pipeline spike, before it is relied on.
* Planet files must be cut into regions before processing, using osmium extract or a GeoDesk query. Both work within 32 GB of memory.

## Licence summary

* OpenStreetMap, including the land polygons: ODbL 1.0. Credit "© OpenStreetMap contributors". Packs are share-alike. Confirmed.
* Natural Earth: public domain. Confirmed.
* VLIZ Global Oceans and Seas v1: CC-BY 4.0. Confirmed from the catalogue record.
* IHO Sea Areas v3: CC-BY-NC-SA 4.0 according to the catalogue record. Avoid it.
* GEBCO grid: public domain, with attribution required. Confirmed.
* CHELSA climatologies v2.1: CC0. Confirmed.
* WorldClim 2.1: no redistribution. Rejected.
* WDPA: no redistribution. Rejected.
* GMBA Mountain Inventory v2: CC-BY 4.0. Confirmed.
* HydroLAKES: CC-BY 4.0. Confirmed.
* HydroRIVERS: to verify.
* Copernicus DEM: free to use, redistribution terms to verify.
* Wikidata: CC0. Confirmed.
* GeoNames: CC-BY 4.0. Confirmed.
* geoBoundaries: mostly CC-BY 4.0, with licences varying by country. To verify for each country if it is used.
* Marine Regions EEZ: CC-BY 4.0 for some versions. To verify for the version used.
* Ordnance Survey OpenData and NaPTAN: Open Government Licence. Confirmed. Used only for UK validation.

### Tools and assets checked in Phase 0

These are not map data, but they are used to build or play TobyMap, so their licences are recorded here too.

* GeoDesk for Python 2.3.0: LGPL-3.0. Confirmed in spike S2, from its package record. It is used only by the pipeline on the build laptop, and it opens the planet and UK GOL files read-only. It is compatible with GPL-3.0.
* OSM land polygons: downloaded on 31 October 2026 into the data folder's tobymap/downloads folder, 885 MB.
* MIT KEMAR HRTF measurements (spike S1): "provided without any usage restrictions", with a request to cite Bill Gardner and Keith Martin, MIT Media Lab, 1994.
* Piper voices (spike S6), each with its own model card:
  * Cori: public domain.
  * Alba: CC-BY 4.0.
  * Northern English male: CC-BY-SA 4.0.
  * Semaine is CC-BY-NC-SA, which forbids commercial use, so it is not used. Alan and Jenny have unclear licences, so they are not used either.
* OpenAL Soft 1.25.2 (spike S1): LGPL-2.1 or later, loaded as a library. Compatible with GPL-3.0.
* Synthizer 0.12.6 (spike S1): the Unlicense. Its bundled libraries, such as miniaudio, are permissive. Compatible with GPL-3.0. Archived in 2025.
* Earcons supplied by the PO, in the sounds folder, which is not in git:
  * bump.wav: the blocked sound, when the user cannot go that way, such as at a pole or when turning in north-fixed (UX sections 5.2 and 5.3).
  * click.wav: the soft tick, when the user moves but nothing changes, such as crossing the UK in 100 metre steps (UX section 3.1, DP43).
  * click.wav is the PO's own recording of their voice, so the PO can choose its licence.
  * bump.wav comes from ZapSplat, under the PO's subscription. ZapSplat's licence allows its sounds in the PO's own projects, but it is not an open licence, so the file cannot be put under GPL-3.0 or shared on its own. It stays out of git, and before a public release, whether the installer and the public web version may include it must be checked against ZapSplat's current terms. An openly licensed or home-made bump would avoid the question.

## Research references

* [IHO Sea Areas licence record (marineinfo.org dataset 5444)](https://marineinfo.org/id/dataset/5444)
* [Global Oceans and Seas, DOI 10.14284/542](https://openpolar.no/Record/ftdatacite:10.14284%2F542/Details)
* [WorldClim terms](https://worldclim.org/about.html)
* [CHELSA climatologies](https://www.chelsa-climate.org/datasets/chelsa_climatologies)
* [GEBCO terms of use](https://www.gebco.net/data-products/gridded-bathymetry/terms-of-use)
* [Protected Planet terms](https://protectedplanet.net/c/terms-and-conditions)
* [GMBA Inventory repository](https://www.github.com/GMBA-biodiversity/Inventory)
* [HydroLAKES licence note](https://git.nayala.duckdns.org/fly/fgdata/src/branch/next/Textures/Globe/02READMElakes.txt)
* [Copernicus DEM on AWS](https://registry.opendata.aws/copernicus-dem/)
* [Shortbread vector tile schema](https://shortbread-tiles.org/schema/)
* [GitHub releases limits](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)
