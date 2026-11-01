# Spike S1 findings: spatial sound

Task P0-T4. Architecture section 12.2. Draft of 31 October 2026, updated on 1 November with your first listening. Synthizer and OpenAL Soft are being added, with your permission.

## The question

Which desktop sound engine should TobyMap use for spatial sound (AD-10)? The browser version uses the browser's own HRTF in any case.

## Short answer so far

* Two desktop candidates are ready to listen to: the project's own HRTF processing, and the stereo speakers mode.
* The browser candidate is ready too, in Firefox and Chrome.
* OpenAL Soft is now in the demo too, as a fourth engine, and so is the own HRTF processing with a lower pitch behind you.
* Synthizer is now built and in the demo too, as "Synthizer HRTF, as in AtMap". So all five candidates can be compared.
* No recommendation yet. After the first listening, the own HRTF processing gets left and right right every time, but places sounds on one side only roughly, and sometimes hears ahead as behind.

## The candidates

### The project's own HRTF processing: ready

* It uses the MIT KEMAR measurements, made with a dummy head at MIT in 1994. Their documentation says they are "provided without any usage restrictions", asking only that the authors, Bill Gardner and Keith Martin, are cited.
* The sound is shaped in NumPy and played through the sounddevice library (MIT licence).
* It uses the same kind of processing as the browser. The desktop and web versions could therefore sound much alike, at the cost of more of our own code.
* In this spike it uses only the horizontal directions, every 5 degrees all the way round.

### Own HRTF processing, lower pitch behind: ready

* The own HRTF processing, with sounds behind you about three semitones lower, as in the speakers mode.
* Added because your first quiz heard sounds ahead as behind three times. It tests whether the pitch cue helps.

### Stereo panning with pitch, the speakers mode: ready

* SON-1 asks for a speakers option. Sounds are panned left and right. Sounds behind you are played about three semitones lower, so front and back can be told apart.

### The browser's own HRTF: ready

* Web Audio's HRTF panner, in Firefox and Chrome.
* It uses the same sounds, distance settings and quiz as the desktop demo, so you can compare them.

### Synthizer: ready

* Synthizer is the library AtMap used, and you had no problems with it (DP91).
* Its project was archived in 2025, so it will get no more fixes.
* Its last release was in May 2023. It has no ready-built package for Python 3.14, which TobyMap uses.
* It could be built from its source code with Visual Studio 2022, which is on your laptop. The safety rules stopped me running a download's build code without asking you, and you gave permission on 1 November.
* Its licence, the Unlicense, is compatible with GPL-3.0.
* Built on 1 November from its source, version 0.12.6 from PyPI, checked against PyPI's published hash. The build script is tools\spikes\s1\build_synthizer.ps1.
* Two changes were needed to build it for Python 3.14, both to build settings, not to Synthizer's code:
  * Cython 3 needs a compatibility setting for Synthizer's callbacks, which were written for Cython 0.29.
  * The library is built with the same C runtime as Python.
* The libraries it bundles, such as miniaudio, have permissive licences. The licence check records it.
* It is set up as AtMap's own C++ wrapper set it up (CSpatialSource and CSoundEngine): a 3D source with the HRTF panner, placed by east and north, with the listener facing north. So it should sound as it did in AtMap.
* Synthizer can only play to the sound device, with no way to render into memory. So in the demo it plays live, and the tests check only the sound handed to it.
* As with the other engines, its own distance model is off, and the demo applies the SON-9 loudness and muffling. Only its direction processing is compared.
* For TobyMap itself, being archived counts against it: any fault found later would be ours to fix, in C++.

### OpenAL Soft: ready

* Added on 1 November. Choose "OpenAL Soft, built-in HRTF" with Change the engine.
* It uses OpenAL Soft's own built-in HRTF data set.
* It renders into memory, through OpenAL Soft's loopback extension, and then plays like the other engines. So the tests need no sound device, and distance is applied in the same way for every engine.
* Its library, soft_oal.dll, is in tools\spikes\s1\vendor, which is not in git.

#### Background

* OpenAL Soft is a mature 3D audio library with HRTF. Version 1.25.2 was released in May 2026. Its licence is LGPL, which is compatible.
* I downloaded the official release into tools/spikes/s1/downloads, which is not in git. The safety rules stopped me loading its ready-built library without asking you, and you gave permission on 1 November.

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
* I cannot hear, so whether any of this sounds right is your test.

## Your first listening, 1 November

You used the desktop demo with the own HRTF processing, and did three quizzes: one with noise bursts and two with the chime.

### What you said

* Ahead seemed quite obvious, and you think you learned to tell when a sound was behind.
* The chime was better than the noise bursts.
* Telling right from left was easy.
* Telling apart the three directions on one side, such as ahead right, right and behind right, was hard. They seemed only about 20 degrees apart, when they are really 45 degrees apart.

### What the quizzes recorded

* 24 sounds in all. 10 were heard in exactly the right direction, and 11 more were one direction out (45 degrees).
* Every sound was heard on the correct side, left or right.
* Front and back were mixed up 3 times. Each time, a sound played ahead was heard as behind. Of the 5 sounds played ahead, 2 were heard ahead.
* Sounds on one side were often heard as more to the side than they were. For example, ahead right and behind right were both heard as right.
* The chime did a little better than the noise: an average error of 42 degrees, against 56 for the noise.

### What this suggests

* The KEMAR dummy head gives clear left and right, but its front, side and back differences do not match your ears well. This is common with a head that is not your own, and is the reason to compare other engines.
* The ahead heard as behind mix-ups matter for TobyMap, where ahead means north of you on the map. A small extra cue may help, such as the slightly lower pitch behind you that the speakers mode uses. That can be tried in the comparison.
* The chime will be the default test sound.

## Waiting for you

* A quiz with each engine, using the chime, would give comparable numbers: own HRTF, own HRTF with lower pitch behind, OpenAL Soft, and Synthizer.
* Side by side, menu option 3, plays one direction through all five engines in turn.
* The browser demo, when convenient.
