# The coast as a border: Hampshire trial (P3-T30a)

Written 20 November 2026, from the Western Europe trial built on 20 November 2026. Nothing in the code or the pack was changed. Requirement: INF-2. Your answer to Q3 in the plan, docs/plan/phase-3-tidy-up-plan2.md, section 3.

## Summary

* Hampshire's coast is 186 kilometres, the same as the pack stores today. It falls into three long stretches with two ends each, and the coast of its islands, which has no ends.
* The three stretches, west to east:
  * 83 kilometres, from Bournemouth, Christchurch and Poole to Southampton: the New Forest shore and the west side of Southampton Water.
  * 53 kilometres, from Southampton to Portsmouth: the east side of Southampton Water, Gosport, Fareham and Portchester, round Portsmouth Harbour to Paulsgrove.
  * 9.4 kilometres, from Portsmouth to West Sussex: the north shore of Langstone Harbour, Havant to Emsworth.
* Hayling Island's coast is 35 kilometres round, with no ends. Smaller islands in Langstone Harbour and Portsmouth Harbour add about 11 kilometres.
* It is quick: Hampshire takes 18 thousandths of a second. Every area with a coast in the Western Europe trial takes about a minute and a half on one core. The world would take about 6 to 9 minutes with 3 workers.
* Two things in the data need care. Along the north shore of Portsmouth Harbour, Portsmouth has about 30 slivers, thin bits of land a few metres wide where its border and the coast do not quite match, which break Hampshire's coast into dozens of short stretches. And the pack has no shapes for the Solent, Southampton Water or the harbours, only their points.

### Decisions asked of you

1. Do you approve stretches of coast as items under Bordering's Coast heading, with the wording proposed below?
> yes 
2. Do you agree that a neighbour's slivers on the shore, bits under 0.05 square kilometres, count as sea, and that a break in the coast shorter than 100 metres is joined over? Then Portsmouth Harbour does not split Hampshire's coast into dozens of short stretches, and Hampshire's coast meets Portsmouth at Paulsgrove, where Portsmouth really begins.
> yes 
3. Do you agree that stretches under 1 kilometre are not listed, but still count in the Coast heading's length?
> yes 
4. Should each stretch name its water as the English Channel only, or also name the bays and straits along it, such as Christchurch Bay and Portsmouth Harbour?
> no just do the sea. the user can discover bays by looking inside the sea object or with nearby.

If you approve, P3-T30b builds it for every area and times it on the Western Europe trial before the world build.

## How it was worked out

* The shapes are the trial's working data, from the relationships stage, the same shapes the pack is written from.
* An area's coast is where its outline meets the ocean's outline. This is how the relationships stage measures coast today, so the total for each area matches what Bordering already says.
* The coast is joined into stretches. A stretch with two ends runs between two neighbours. A stretch that closes on itself is the coast of an island, with no ends.
* At each end, the neighbouring area is the area of the same layer that touches that point.
* Lengths are measured over the Earth, as the build measures every border.
* Positions are given from Winchester, as the application would say them if you stood there, using the application's own words for distance and direction.

## Hampshire's stretches of coast

### From Bournemouth, Christchurch and Poole to Southampton, 83 kilometres

* 82.6 kilometres, 44 percent of the coast.
* West end: where Bournemouth, Christchurch and Poole meets it, at Chewton Bunny near Highcliffe, 45 kilometres south-west of Winchester (50.7374 north, 1.6925 west).
* East end: where Southampton meets it, at the mouth of the River Test off Dock Head, 21 kilometres south of Winchester (50.8805 north, 1.3948 west).
* Named water close to it, west to east: Christchurch Bay, Park Shore, Stanswood Bay. The Solent's point is just over 1 kilometre offshore.

### From Southampton to Portsmouth, 53 kilometres

* 52.8 kilometres, 28 percent of the coast, with Portsmouth's slivers counted as sea (decision 2). The slivers add about 6 kilometres of Hampshire's shore that today is counted as border with Portsmouth.
* Without that rule it splits into 40 kilometres, ending near Portchester, 6.4 kilometres with Portsmouth at both ends, and many bits of a few tens of metres. Joining over breaks under 100 metres alone gives 46.5 kilometres, ending at 50.8408 north, 1.1728 west, about 4 kilometres short of where Portsmouth really begins.
* West end: where Southampton meets it, at Weston Shore, 20 kilometres south of Winchester (50.8800 north, 1.3652 west).
* East end: where Portsmouth meets it, at Paulsgrove by Horsea Island, 28 kilometres south-east of Winchester (50.8430 north, 1.1170 west).
* Named water close to it, west to east: South Camber, Camber Basin, Portsmouth Harbour, Wicor Lake (spelt Wiccor Lake in the data), Cams Bay.

### From Portsmouth to West Sussex, 9.4 kilometres

* 9.4 kilometres, 5 percent of the coast, when breaks under 100 metres are joined over; 9.1 kilometres without, as a 220 metre bit at Emsworth has West Sussex at both ends.
* West end: where Portsmouth meets it, at Farlington Marshes on Langstone Harbour, 32 kilometres south-east of Winchester (50.8425 north, 1.0217 west).
* East end: where West Sussex meets it, at Emsworth, 36 kilometres south-east of Winchester (50.8461 north, 0.9325 west).
* No named water within 1 kilometre, as Langstone Harbour's point lies just beyond that.

### Islands' coast, with no ends

* Hayling Island, 35 kilometres round, 19 percent of the coast, 37 kilometres south-east of Winchester.
* Long Island, 1.8 kilometres; Gull Island, 1.7 kilometres; South Binness Island, 1.3 kilometres; Baker's Island, 1.1 kilometres; and one unnamed islet of 1.0 kilometres. All in Langstone Harbour or Portsmouth Harbour.
* 61 more islets under 1 kilometre each, 4.2 kilometres in all, mostly marsh in Langstone Harbour.

### Short bits

* Found as the coast is today: 28 stretches under 1 kilometre, 1.7 kilometres in all, nearly all along the top of Portsmouth Harbour, between Portsmouth's slivers.
* With the slivers counted as sea and breaks under 100 metres joined over, they become part of the stretch from Southampton to Portsmouth.

## Hampshire's neighbours, for comparison

### Southampton

* One stretch, 2.9 kilometres, from Hampshire at the mouth of the Test to Hampshire at Weston Shore. This is its whole coast, as stored today.
* The rest of Southampton's waterfront, the docks and the Test and Itchen above Dock Head, counts as land in the land polygons. So Southampton's border with Hampshire runs down the middle of the Test, as a land border.

### Portsmouth

* Portsea Island, 29 kilometres round, and Whale Island, 2.3 kilometres round, with no ends.
* 12 kilometres from Hampshire near Horsea Island to Hampshire at Farlington Marshes, along Ports Creek and Langstone Harbour.
* 1.9 kilometres in the top of Portsmouth Harbour, between two points where it meets Hampshire.
* 27 bits under 1 kilometre, 3.2 kilometres in all; joined over breaks under 100 metres, most become one stretch of 4.7 kilometres.

### West Sussex

* One stretch, 146 kilometres, from Hampshire at Emsworth to Brighton and Hove, past Chichester Harbour.
* 20 islets, 5.8 kilometres in all.

### Bournemouth, Christchurch and Poole

* One stretch, 60 kilometres, from Dorset at Lytchett Bay to Hampshire at Chewton Bunny, round Poole Harbour, along Bournemouth's beaches and round Christchurch Harbour.
* Islands in Poole Harbour, such as Pergins Island, 1.3 kilometres.

### Dorset

* One stretch, 210 kilometres, from Devon at Lyme Regis to Bournemouth, Christchurch and Poole at Lytchett Bay, including Portland and the Purbeck shore of Poole Harbour.
* Brownsea Island, 5.8 kilometres, and Furzey Island, 1.7 kilometres, among others.

### Isle of Wight

* All its coast is one island's coast, 122 kilometres round, with no ends. It shares no border with Hampshire, so it is never at the end of a stretch. Bordering already lists it as nearly touching Hampshire, 1.3 kilometres across the Solent.

### Ends that agree

* Each end found from Hampshire's side is the same point as the end found from the neighbour's side, to within about 50 metres. So Hampshire's stretch ends where Bournemouth, Christchurch and Poole's begins, and the two can be said as meeting.

## What is doubtful in the data

* The Solent, Southampton Water, Spithead and the harbours have no shapes in the pack. The Solent and the harbours are points in the bays and straits layer; Southampton Water and Spithead are not in the pack at all. So the only water with a shape along Hampshire is the English Channel, and every stretch would say "English Channel". Bays and straits can be named only as points close to a stretch.
* Southampton's coast is only 2.9 kilometres, because the land polygons close the Test and the Itchen at Dock Head. The end where Southampton meets Hampshire's coast is in the water off Dock Head, not on the shore.
* Along the north shore of Portsmouth Harbour, from Paulsgrove west to Fareham Creek, Portsmouth has about 30 slivers, the largest 0.04 square kilometres, most under 0.01. Its border there and the coast of the land polygons do not quite match. As the coast is found today, Hampshire has 32 stretches with ends, most a few tens of metres long, and Hampshire's border with Portsmouth (16 kilometres) includes about 6 kilometres along these slivers. P3-T28a gives slivers to the county beside them only where land is in no county, so it does not touch these. P3-T30b would count them as sea when finding stretches; giving them to Hampshire in the build would be a separate fix.
* Hampshire's Bordering today lists the North Atlantic Ocean and the English Channel for the same 186 kilometres; P3-T28b already keeps only the English Channel.

## Timing

* Loading the trial's land areas, oceans and bays and straits: 3 seconds.
* Putting the ocean's outline into an index for quick lookups: 2 seconds, for 874,000 points.
* Hampshire: 18 thousandths of a second. The seven areas above together: about 100 thousandths of a second.
* Every area with a coast in the trial, on one core, 87 seconds in all:
  * countries: 26 areas, 106,000 kilometres of coast, 30 seconds;
  * regions: 115 areas, 103,000 kilometres, 20 seconds;
  * counties: 843 areas, 105,000 kilometres, 21 seconds;
  * islands: 24,333 areas, 65,000 kilometres, 16 seconds.
* Of all the stretches found, 1,990 have two ends and are 1 kilometre or more: 51 for countries, 268 for regions, 1,303 for counties and 368 for islands. The rest are islands' coast, with no ends.

### For the whole world

* The world's ocean outline, in the last world build, is 1.9 million kilometres with 9.5 million points. The trial's is 115,000 kilometres with 874,000 points.
* So the world is about 11 to 17 times the trial: about 16 to 25 minutes on one core, or about 6 to 9 minutes with 3 workers.
* Memory: the ocean's outline in an index needs well under 1 GB for the world.

## Proposal for P3-T30b

### In the build

* A new small stage, coast stretches, after the relationships stage and before the writing stage. A stage of its own, so a change to it never reruns the relationships stage, which took about three hours in the last world build.
* For each area of the countries, regions, counties and islands layers that has a coast, it finds the stretches as this trial did.
* It counts a neighbour's slivers on the shore, bits under 0.05 square kilometres, as sea, and joins over breaks in the coast shorter than 100 metres.
* For each stretch with two ends and 1 kilometre or more, it stores: its length, each end's position and the neighbour there, and the point half way along it.
* For islands' coast it stores nothing new: the island is already in the pack, and the Coast heading's length already counts it.
* Size: about 50 bytes a stretch. About 100 KB for the Western Europe trial, and about 1 to 2 MB for the world, in a pack of about 500 MB.
* Checks: each area's stretches and islands add up to its stored coast length, plus the slivers counted as sea, and each end has a matching end on the neighbour's side.

### In the application

The Coast heading stays as P3-T28b made it, and lists the stretches, west to east as you go round, in place of the waters. Each stretch is said like a neighbour, and opens to its two ends, as a shared border does today. Suggested words, from Winchester:

* Heading: "Coast, 190 kilometres"
* "Coast from Bournemouth, Christchurch and Poole to Southampton, 33 kilometres south, 83 kilometres, 44 percent"
  * "End of the coast, where Bournemouth, Christchurch and Poole meets it, 45 kilometres south-west"
  * "End of the coast, where Southampton meets it, 21 kilometres south"
* "Coast from Southampton to Portsmouth, 33 kilometres south, 53 kilometres, 28 percent"
* "Coast from Portsmouth to West Sussex, 34 kilometres south-east, 9.4 kilometres, 5 percent"
* "Coast of islands, 46 kilometres, 25 percent", which opens to the islands of 1 kilometre or more, each said as Bordering says a stretch with no ends today: "Hayling Island, 35 kilometres round, nearest point 36 kilometres south-east".

Notes on the words:

* The distance and direction on a stretch's item are to its point half way along. Enter goes there; Enter on an end goes to that end.
* The share is of the whole coast, as a neighbour's share is of the whole border. With slivers counted as sea, the shares can add up to a little over 100 percent, here 102.
* A neighbour's own end, under its shared border, would say "where the coast meets it, English Channel", as it does today.
* If you choose to name bays and straits (decision 4), a stretch would add "passing Christchurch Bay and Stanswood Bay", from the points within 1 kilometre of it.
* "Stretch of coast" is a new idea. If you approve, it goes into the glossary first: "Stretch of coast: a length of an area's coast between two neighbours, with an end at each; the coast round an island has no ends."
