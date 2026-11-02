# Spike S6 findings: the spatial voice

Task P0-T9. Architecture section 12.7. Draft of 31 October 2026, updated on 1 November with your listening, and on 2 November with Piper in the browser.

## The question

Which built-in voice should speak the spatial labels, such as "Berlin" heard from the right (SON-3, DP82)? The screen reader's own voice cannot be placed in space, so TobyMap needs a voice of its own.

## Short answer so far

* You listened on 1 November. eSpeak NG is ruled out, and Alba, the Scottish Piper voice, gave the best sense of direction.
* Recommendation: Piper, with Alba as the default voice.
* Windows voices are left out, as you asked (DP90).
* Piper with the Alba voice works in the browser too, in Chrome and Firefox, from a worker, placed in space with Web Audio. See "Piper in the browser, 2 November".
* In the browser each label takes about 380 ms from request to sound with one thread, or about 220 ms with four. On the desktop it takes about 100 ms. You agreed (DP105) that the web version uses four threads, tried first in Phase 2.

## The voices

### eSpeak NG

* GPL-3.0, the same licence as TobyMap.
* It is the voice many screen reader users know: clear, robotic and very fast.
* It comes as a small library in a Python package, so nothing is installed in Windows. Its download is about 20 MB, most of it data for other languages.
* Speed while testing: 4 to 35 ms to make each label. The first label after starting is the slowest.

### Piper

* Piper (GPL-3.0) makes natural-sounding neural voices. It is maintained by the Open Home Foundation.
* Each voice is about 60 MB. Piper also needs ONNX Runtime (MIT licence), about 15 MB.
* Speed while testing: loading a voice took several seconds, and its first label about 5 seconds. Later labels took 140 to 260 ms. These were measured while the S2 build was using the computer, so they will be re-measured.
* Three British English voices are included, chosen because their licences clearly allow use:
  * Cori, a southern English woman. Public domain.
  * Alba, a Scottish woman. CC-BY 4.0, which only asks for credit.
  * A northern English man. CC-BY-SA 4.0: credit, and the voice must be shared under the same licence.
* Left out:
  * Semaine, whose licence forbids commercial use.
  * Alan and Jenny, whose licences are unclear.

## How each label is placed

The label is made into sound in memory, then placed in space by spike S1's HRTF processing, exactly like any other sound. It starts at once, because silence at the start and end is trimmed.

## How to listen

Use headphones.

1. In PowerShell, in the repository folder, run: `.venv\Scripts\python.exe tools\spikes\s6\demo.py`
2. It is plain text, like the S1 demo. Type a number and press Enter. Nothing plays until you press Enter.

The main menu has:

1. Eight place names from eight directions: "Berlin" ahead, "Bay of Biscay" ahead right, "Llívia" right, and so on round the circle.
2. Side by side: choose a name and a direction, then hear every voice say it in turn.
3. Time every voice, without playing anything.
4. Change the voice.
5. Change between HRTF and stereo placing.

## What to listen for

* Which voice is easiest to understand when it comes from the side or behind?
* Which voice is pleasant to hear many times in a row?
* Does any voice sound wrong on names such as Llívia or Saint Petersburg?
* Is any voice too slow to start after you press Enter?

## The web version

On 31 October the browser version was not built, and DP98 asked whether its 60 MB download was acceptable. You accepted the recommendation, so it was built on 2 November. See "Piper in the browser, 2 November" below.

## Results from the automatic checks

* eSpeak NG makes each label into sound in memory, at the right length and loudness.
* The Piper Cori voice does the same.
* The demo's tour works with a stand-in player, so no sound device is opened in the tests.

## Your listening, 1 November

* eSpeak NG sounded dated, like the 1970s, and you would be embarrassed to use it. It is ruled out.
* Alba, the Scottish woman, gave the best sense of direction.
* Cori and the northern English man were about equal to each other.

## What this means

* The desktop uses Piper, with Alba as the default (CC-BY 4.0, so the credit goes in the About box and the third-party notices).
* Piper and its voice add about 75 MB to the installer.
* Piper's slow first label, about 5 seconds, needs fixing before Phase 1. The voice can be loaded, and a first label made silently, while TobyMap starts. Measured again on 2 November with the laptop not busy, the first label took about 100 ms, so the 5 seconds was the busy laptop. Loading the voice still took about 8 seconds, so it is still loaded while TobyMap starts.
* The web version needs Piper in the browser, because DP90 says the desktop and web versions should not differ. That is about 60 MB more to download the first time, which spike S4 must allow for alongside the 17 MB of Pyodide. A new question, DP98, asks whether that is acceptable.

## Piper in the browser, 2 November

### How it works

* The voice runs in a worker of its own, beside the core's worker, so making a label never holds up the map.
* eSpeak NG turns the label's text into phonemes. It comes in phonemizer.js (Apache-2.0, with eSpeak NG built in, GPL-3.0). eSpeak NG is only used for this, not as a voice.
* ONNX Runtime Web (MIT) runs the Alba voice on the phonemes. It is the browser version of the ONNX Runtime the desktop's Piper uses.
* The voice is kept in the browser's cache storage, so it downloads once.
* The page places the label in space with the browser's HRTF, as spike S1 decided, and as the S1 web demo does.
* Both libraries are fetched by `toolsetch_vendor.py --piper`, with checksums, and not kept in git. Their licences are compatible with GPL-3.0, and a notice file goes with them.

### What a first visit downloads

* 75.8 MB as stored, or about 60 MB if the server compresses it.
* The voice itself is 60.3 MB, and hardly compresses (55.6 MB).
* ONNX Runtime Web is 14.2 MB, or 3.7 MB compressed.
* phonemizer.js is 1.3 MB, or 0.65 MB compressed.
* This is close to the 60 MB that DP98 expected, on top of the 17 MB for Pyodide.

### Timings in Chrome 156 and Firefox 157

Measured by the runner, without a window, on this laptop, from a local server. Each browser ran twice: first downloading the voice, then reading it from cache storage, as on a later visit.

* Starting eSpeak NG: 160 to 350 ms.
* Getting the voice: about 0.3 to 0.7 seconds from the local server, and 0.1 to 0.25 seconds from cache storage. Over the internet the download depends on the connection; at the 32 MB a second measured from Hugging Face in spike S3, it would take about 2 seconds.
* Starting the voice in ONNX Runtime: 2.7 to 3.5 seconds. This is the largest part.
* The first label, made silently: 0.2 to 0.55 seconds.
* Ready: about 4 to 5 seconds after the voice began to load. The map is usable during this time (DP98).

From request to sound, for the eight demo labels, each spoken twice:

* One thread, Chrome: median 360 to 405 ms, longest 482 ms.
* One thread, Firefox: median 390 to 395 ms, longest 464 ms.
* Four threads, Chrome: median 214 ms, longest 305 ms.
* Four threads, Firefox: median 220 to 234 ms, longest 303 ms.
* The browsers add about 36 to 40 ms in the sound output, as they report it.
* Almost all of the time is the voice. eSpeak NG takes 3 to 55 ms.

On the desktop, the same labels took a median of 99 ms, and at most 123 ms.

### Several threads

* A web page's worker can only use several threads if the site sends cross-origin isolation (see the glossary). The runner's `--isolated` option does that, for the four-thread figures.
* GitHub Pages cannot send it. A small helper script loaded by the page (a service worker) can add it, but that has not been tried yet.
* You agreed (DP105) that the web version uses four threads, through the helper script, tried first in Phase 2 (P2-T7). If it causes trouble, it falls back to one thread.

### The phonemes compared with the desktop

* For 7 of the 8 labels, the browser's phonemes are exactly the desktop's.
* Llívia differs a little: the desktop's eSpeak NG adds a slight "y" sound before the last "a", and the browser's does not. The two use different versions of eSpeak NG. You may hear a slight difference on that name.

### How to listen

Use headphones.

1. In PowerShell, in the repository folder, run: `.venv\Scripts\python.exe tools\spikes\s6\web_run.py --serve`
2. It opens the page in your default browser. To use Firefox, paste the address it prints into Firefox.
3. Press "Load the voice", and wait until the page says the voice is ready.
4. Under "Eight place names from eight directions", each button speaks one name from its direction. Under "Your own words", you can type any words and choose a direction.
5. The Results box shows the timings of each label.
6. To hear four threads, stop the server with Ctrl+C and run it again with `--serve --isolated`.

The runner without `--serve` repeats the timings in Chromium and Firefox without a window. Results: docs/spikes/s6-results.

## Still to do

* Four threads in the browser through the helper script (DP105), built in Phase 2 with the voice (P2-T7).
* The speed of starting the voice in ONNX Runtime, about 3 seconds, could be looked at in Phase 2, but the map is usable while it starts.
