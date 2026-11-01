# Spike S6 findings: the spatial voice

Task P0-T9. Architecture section 12.7. Draft of 31 October 2026, updated on 1 November with your listening.

## The question

Which built-in voice should speak the spatial labels, such as "Berlin" heard from the right (SON-3, DP82)? The screen reader's own voice cannot be placed in space, so TobyMap needs a voice of its own.

## Short answer so far

* You listened on 1 November. eSpeak NG is ruled out, and Alba, the Scottish Piper voice, gave the best sense of direction.
* Recommendation: Piper, with Alba as the default voice.
* Windows voices are left out, as you asked (DP90).
* The browser version is not built yet. Since eSpeak NG is ruled out, the web version needs Piper in the browser too. See "The web version".

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

The browser needs its own copy of the voice:

* eSpeak NG and Piper both have builds for the web (WebAssembly).
* Trying them means running outside JavaScript libraries, and Piper's voices would add about 60 MB to the web download.
* I have not built that yet. If you prefer eSpeak NG, the web question is simple: it is small and fast in a browser too. If you prefer a Piper voice, the web version needs either the same 60 MB voice, or eSpeak NG in the browser (DP90 asked about different voices).

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
* Piper's slow first label, about 5 seconds, needs fixing before Phase 1. The voice can be loaded, and a first label made silently, while TobyMap starts.
* The web version needs Piper in the browser, because DP90 says the desktop and web versions should not differ. That is about 60 MB more to download the first time, which spike S4 must allow for alongside the 17 MB of Pyodide. A new question, DP98, asks whether that is acceptable.

## Still to do

* Re-measure Piper's speed when the laptop is not busy.
* Try Piper in the browser, during spike S4.
