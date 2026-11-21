# Mountain ranges and the sea: DP220 and P4-T14l

Written 21 November 2026, for your note on checklist step 14.7: Exmoor overlapping the North Atlantic Ocean and the Bristol Channel.

## Your questions on Exmoor (P4-T14l)

### Is "1 percent of Exmoor" rounded up from less?

No. The exact share is 1.17 percent, so it is rightly said as 1 percent.

* Exmoor, as the trial pack holds it, is 120.39 square kilometres.
* 1.41 square kilometres of it lay in the sea: 1.17 percent.
* The Bristol Channel and the North Atlantic Ocean get the same figure because the Bristol Channel lies inside the North Atlantic Ocean. It is the same 1.41 square kilometres, not two separate overlaps.
* Under 0.5 percent would have been said as "less than 1 percent". 1.17 percent is well above that.

### Why does it reach the sea?

The mountain ranges were already cut to the land, but to a different coast from the one the pack draws.

* The countries, oceans and seas are drawn with one coast, made at 100 metres detail.
* The mountain ranges and the physical regions, such as deserts and plains, were cut to the OpenStreetMap land polygons simplified to 300 metres. That makes a rougher coast. Its straight lines cut across small bays and headlands.
* So Exmoor's edge ran a little out to sea where the rough coast crossed a bay. It reached at most 144 metres beyond the drawn coast.
* Most of the overlap was in two places: 1.0 square kilometre near Lynmouth and Foreland Point, and 0.37 square kilometres near the Valley of Rocks.
* The rough coast also fell short in other places: 0.24 square kilometres of Exmoor's land, inside its outline, was left out of Exmoor.

## How widespread it was

Measured on the Western Europe trial's data, with its 758 mountain ranges and 14 physical regions:

* 165 of the 772 reached into the sea at all.
* 147 reached in by 0.01 percent of their area or more.
* 15 reached in by 0.5 percent or more, so the Overlapping group said 1 percent or more. The largest were the Frisian Islands (2.8 percent), the Orkney Islands (2.5 percent), the Shetland Islands (2.3 percent), the Outer Hebrides (1.6 percent), Monte Argentario (1.3 percent) and Exmoor (1.2 percent).
* 25 had a sea in their Overlapping group, as a sea is listed when either the range's share or the sea's share is 0.5 percent or more. A narrow fjord, such as the Sognefjord, can be crossed by a range's rough coast.
* In all, 2,158 square kilometres of mountain ranges and physical regions lay in the sea.

## The fix

As DP220 says, every mountain range and physical region is now cut to the land as the pack draws it: the countries, as the join stage made them. Their coast is exactly the coast of the oceans and seas.

* So no mountain range or physical region overlaps a sea.
* Its edge at the coast is the drawn coast, so it no longer falls short of the coast either.
* A range on several islands keeps each island's part.
* The ranges' inland edges are simplified to 300 metres, as before.
* The land polygons are no longer read by this stage.

## Before and after, on the trial's data

* Reaching into the sea at all: 165 before, 11 after. The 11 are rounding at the last decimal place of the coordinates, at most about 2 square metres each.
* Reaching in by 0.01 percent or more: 147 before, none after.
* Reaching in by 0.5 percent or more, said as 1 percent or more: 15 before, none after.
* Area in the sea: 2,158 square kilometres before, under a ten-thousandth of a square kilometre after.
* Exmoor: 120.39 square kilometres with 1.17 percent in the Bristol Channel before; 118.91 square kilometres with nothing in the sea after. When the trial is built again, Exmoor's Overlapping group will list only Somerset and Devon.

## Time and size

* Time: the stage gets faster. On the world's data on disk, the new cutting took 5 minutes 8 seconds in all. The stage took 12 minutes 26 seconds before. On the trial's data it took 20 seconds.
* Size: the ranges and regions now follow the coast at the pack's own detail, with every islet inside their outlines. On the world's data their outlines grow from 5.1 million points to 12.5 million. The largest are island groups, such as the Canadian Arctic Archipelago, Japan, the Malay Archipelago and the British Isles.
* That should add about 30 MB to the world pack, which is now 536 MB, so about 6 percent. Leaving out islets smaller than 0.01 square kilometres would save only about 14 percent of that growth, so it is not done.

## Can the cut to the coast apply to other kinds?

### Deserts, plains and other physical regions

Yes, and it is done. They come from Natural Earth and are cut by the same stage as the mountain ranges, so the fix covers them too. Before it, 8 of the 14 in the trial overlapped a sea, such as the Frisian Islands and the Orkney Islands.

### Roads and railway lines

Not recommended. A road or railway over the sea is real: a bridge, a causeway or a tunnel, such as the Tay Bridge or the Øresund Bridge. Cutting them to the land would break them into bits and lose those crossings. The build already counts a road or railway over tidal water as on the land it joins (P3-T28, item 4c), so a bridge from Scotland to Scotland is wholly inside Scotland. That gives the right answers without cutting.

### Lakes

Not by cutting, but there is a different fault to fix. In the trial, 10 of the 550 lakes overlap the sea:

* 9 lie almost wholly in the sea, such as Ringkøbing Fjord, Ria Formosa, Loch Ewe and the Sado Estuary. OpenStreetMap maps them both as water and inside its coastline, so the seas already hold them. Cut to the land, they would vanish. Kept, you hear a lake and a sea at the same point.
* 1, the Laguna di Grado, overlaps the Adriatic Sea by 0.65 percent, the same kind of rough coast as Exmoor's.
* A lagoon that OpenStreetMap's coastline closes off, at its mouth, is land in the land polygons, so it is in no sea and the Lakes layer is the only water there. That case is right.

Recommendation: a separate small work item for the stage that reads the lakes (osm-layer). Leave out a lake that lies mostly in the sea, as the seas already hold it, and cut away the sea from the rest. It would need that stage, and the stages after it, to run again, but not the countries or the seas.

### Rivers

Not recommended, though not measured for this report. A river is a line, like a road, and ends where it meets the sea; its estuary is often mapped out into the sea. Cutting it would only shorten it at the coast.

## Recommendation

* Accept the fix for the mountain ranges and physical regions, with its cost of about 30 MB on the world pack.
* Do not cut roads, railways or rivers.
* Plan a small work item for the lakes that lie in the sea.
