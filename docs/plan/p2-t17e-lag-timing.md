# P2-T17e: the lag after an arrow key

Measured on 10 November 2026, on your laptop, with the world pack and your own settings. Your notes were desktop checklist 2.11 and 4.5: both the spoken place and the blocked sound came late after an arrow key.

## What was measured

Stepping east from the North Atlantic into Belgium, 100 km at a time, and pressing Up at the North Pole for the blocked sound. Each key was timed from the moment it was pressed to each stage.

* The core's answer: 0.3 ms for an ordinary step and for the blocked sound, and up to 20 ms when you cross a border. Not the lag.
* The speech handed to the screen reader, in the whole window while the map was drawn: 2 to 16 ms, with keys pressed every 150 ms and every 300 ms. Not the lag.
* The sound handed to the player: 2 to 5 ms as a rule. One click in ten took up to 88 ms.
* The sound from the player to the sound card: about 105 ms, plus Windows' own mixing. This was the lag in the sounds.

## Why the sounds were late

Windows has several routes for sound to reach the sound card. TobyMap used the one Windows picks by default, MME, the oldest. Asked for its lowest delay, it still holds sound back about 105 ms. The routes measured on your Behringer sound card:

* MME, the route used before: 105 ms.
* DirectSound: 120 ms.
* WASAPI, shared, so other programs such as NVDA still play: about 24 ms.

## What changed

The desktop now plays its sound through WASAPI, shared, with Windows converting TobyMap's rate (44,100 a second) to your card's own (48,000). If WASAPI ever will not open, the default route is used, so you are never left without sound.

* Before: about 105 ms from the player to the sound card.
* After: about 24 ms. That is about 80 ms sooner for the blocked sound, the clicks, the other earcons, the beacon and the spatial voice.
* Checked on your laptop: the player opened WASAPI, at 23.5 ms, and mixed with no gaps.

## The spoken place

TobyMap hands the place to the screen reader within about 16 ms of the key. The rest of the time is the screen reader's own, and, as you asked, nothing is changed for one screen reader alone. The spoken place does not go through the sound player, so it is not changed by this task.

## Still to check

* With NVDA, as only you can: desktop 2.11 and 4.5. The blocked sound and the clicks should now come noticeably sooner.
* The occasional slow click, up to 88 ms in one case in ten, is not yet explained.
