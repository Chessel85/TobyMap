# P4-T13b Groups of islands as a layer: the practice run

By Claude Code, 26 November 2026. The method is P4-T13a's, in docs/plan/p4-t13a-island-groups-report.md.

## In short

* The island-groups stage makes the Groups of islands layer, each outline grown from its own islands over the sea between them.
* Practice run on the Western Europe trial: the pack built, 55.1 MB, with 61 groups of islands. The checks stage passed all 60 check places.
* Every tested position was right in the Channel Islands, the Isles of Scilly, the Outer and Inner Hebrides, the Hebrides, Orkney, Shetland, the Balearic Islands and the British Isles.
* On Sark, "you are in" lists Sark (island and region), Guernsey, the Channel Islands, the British Isles, then Europe.

## What was finished in this task

* Two faults in the stage were mended. A name was used twice in the same function, so a Natural Earth group stopped the stage. And a trial box given in the settings was not used to cut the outlines.
* A new sample, tests/samples/osm/channel-islands.geojson, holds the Channel Islands' 78 member islands, the countries Guernsey and Jersey, and the outline the stage made. It is described in tests/samples/README.md.
* Two tests were corrected. One expected a mainland 15 kilometres away to be reached by an outline that ends 3 kilometres off the coast. The other read a layer setting by the wrong name.
* The Channel Islands outline is right. It covers 2,017 km2 in one part. It holds Sark, Jersey, the Minquiers, the Écréhous and the sea between Guernsey, Jersey, Sark and Alderney. It does not hold the open Channel 35 kilometres west of Guernsey, the sea 5 kilometres off the Cotentin coast, or Chausey.

## Positions tested in the trial pack

What `mapdata inspect` gave, smallest area first:

* Sark: Sark (island, region and county), Guernsey, Channel Islands, British Isles, Europe.
* At sea between Guernsey and Jersey: Channel Islands, Territorial waters of Guernsey, English Channel, British Isles, North Atlantic Ocean.
* St Mary's Road, Isles of Scilly: Isles of Scilly, then the United Kingdom's territorial waters, British Isles, North Atlantic Ocean.
* Sound of Harris: Outer Hebrides, Hebrides, then the inner seas, territorial waters, British Isles and ocean.
* Mull: Mull, Argyll and Bute, Inner Hebrides, Hebrides, Scotland, United Kingdom, British Isles, Europe.
* Scapa Flow: Orkney Islands, territorial waters, British Isles, North Atlantic Ocean.
* Yell Sound: Shetland, Norwegian Sea, territorial waters, British Isles, North Atlantic Ocean.
* At sea between Mallorca and Menorca: Balearic Islands, Balearic Sea, Territorial waters of Spain, Mediterranean Region.

Positions that are rightly outside: Land's End, the Minch, Skye, Kintyre, Caithness, the open sea between Ibiza and Mallorca, and the Belgian coast.

## The run

* The stage took 6 minutes 56 seconds, most of it growing and shrinking the outlines. It read 495 groups tagged place=archipelago from the planet file in 19 seconds.
* The physical stage ran again, as its code changed. The stages after it ran again too. The osm-layer, osm-places and osm-rivers stages also ran again, from code changes committed earlier, so their working folders are new.
* Whole build: about 31 minutes, with 3 workers. continue.txt was only read.

## For the PO

* The drawing order (DP198) does not yet list the Groups of islands layer. Until it does, the layer is drawn after the other areas and before the outlines. As it is outlined and not filled, only its edge shows. Where it goes in the order is your choice.
* OpenStreetMap names Orkney "Orkney Islands". The record can rename it to "Orkney" if you wish.
* The glossary still needs the two new terms from P4-T13a: "group of islands" and "member island".
* The British Isles covers 466,342 km2 in the trial. Its reach is set by the Channel Islands' distance from Great Britain. It does not cover the Belgian coast. The Irish Sea and the western Channel are still to be checked on the world build.
