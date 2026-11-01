# Spike S1 findings: spatial sound

Task P0-T4. Architecture section 12.2. Draft of 31 October 2026, written overnight. It waits for your listening, and for your permission on two candidates.

## The question

Which desktop sound engine should TobyMap use for spatial sound (AD-10)? The browser version uses the browser's own HRTF in any case.

## Short answer so far

* Two desktop candidates are ready to listen to: the project's own HRTF processing, and the stereo speakers mode.
* The browser candidate is ready too, in Firefox and Chrome.
* Synthizer and OpenAL Soft need your permission before I can try them. See "Waiting for your permission".
* No recommendation yet. It depends on what you hear.

## The candidates

### The project's own HRTF processing: ready

* It uses the MIT KEMAR measurements, made with a dummy head at MIT in 1994. Their documentation says they are "provided without any usage restrictions", asking only that the authors, Bill Gardner and Keith Martin, are cited.
* The sound is shaped in NumPy and played through the sounddevice library (MIT licence).
* It uses the same kind of processing as the browser. The desktop and web versions could therefore sound much alike, at the cost of more of our own code.
* In this spike it uses only the horizontal directions, every 5 degrees all the way round.

### Stereo panning with pitch, the speakers mode: ready

* SON-1 asks for a speakers option. Sounds are panned left and right. Sounds behind you are played about three semitones lower, so front and back can be told apart.

### The browser's own HRTF: ready

* Web Audio's HRTF panner, in Firefox and Chrome.
* It uses the same sounds, distance settings and quiz as the desktop demo, so you can compare them.

### Synthizer: needs your permission

* Synthizer is the library AtMap used, and you had no problems with it (DP91).
* Its project was archived in 2025, so it will get no more fixes.
* Its last release was in May 2023. It has no ready-built package for Python 3.14, which TobyMap uses.
* It could be built from its source code with Visual Studio 2022, which is on your laptop. The safety rules stopped me running a download's build code without asking you.
* Its licence, the Unlicense, is compatible with GPL-3.0.

### OpenAL Soft: needs your permission

* OpenAL Soft is a mature 3D audio library with HRTF. Version 1.25.2 was released in May 2026. Its licence is LGPL, which is compatible.
* I downloaded the official release into tools/spikes/s1/downloads, which is not in git. The safety rules stopped me loading its ready-built library without asking you.

## Distance

Distance is heard in two ways, scaled to the zoom as SON-9 says:

* Loudness: full loudness up to a twentieth of the way to the edge of the view. Each doubling of distance is then equally quieter, down to 30 decibels quieter at the edge.
* Muffling, the second cue: the sound gets duller with distance. Beyond the view it is duller still.

Both are starting values, to be tuned in the Phase 1 listening test.

## How to listen

Use headphones.

### The desktop demo

1. In PowerShell, in the repository folder, run: `.venv\Scripts\python.exe tools\spikes\s1\demo.py`
2. It is plain text. Type a number and press Enter. Nothing plays until you press Enter, so NVDA's speech and the sound never overlap.

The main menu has:

1. Walk round eight directions. This starts ahead and goes clockwise, and says each direction before it plays.
2. Near to far. The same sound ahead right, from very near to beyond the view.
3. Side by side. One direction through every engine in turn.
4. Listening quiz. Eight random directions. After each, you type 1 to 8 for where you heard it, or r to hear it again.
   * At the end, it says how many were within 45 degrees and how often front and back were mixed up.
   * Your answers are saved in docs/spikes/s1-listening.
5. Change the engine.
6. Change the sound: noise bursts, a chime, or any WAV file in the sounds folder, such as click.wav and bump.wav.

### The browser demo

1. Open the file tools\spikes\s1\web\index.html in Firefox, then in Chrome. File Explorer, Open with, works, and no server is needed.
2. Choose the engine and sound with the radio buttons. Every direction and distance button plays straight away.
3. The quiz works as on the desktop. The results appear in a text box, which you can copy or save as a file.

## What to listen for

* Left and right: easy, or not?
* Front and back: can you tell ahead from behind, and ahead right from behind right?
* Distance: does near to far sound like distance, or just quieter and duller?
* Which sounds most natural, and which is most tiring?
* Any clicks, delays or other problems.

## Results from the automatic checks

* 16 tests check the sound shaping without opening a sound device. For example:
  * a sound on the right reaches the right ear more strongly, and the left side mirrors the right;
  * the stereo mode pans correctly, and lowers sounds behind you;
  * each doubling of distance is equally quieter, as SON-9 asks;
  * the demo's menus and quiz work, and the quiz saves the right file.
* The browser demo page is checked in Chromium and Firefox: every button works without errors, and the quiz records results.
* Nobody has listened yet. I cannot hear, so whether any of this sounds right is your test.

## Waiting for you

* Permission to build Synthizer from its source code, and to load OpenAL Soft's library. With both, the side-by-side comparison will cover all four candidates.
* Your listening, ideally including a quiz with each engine.
