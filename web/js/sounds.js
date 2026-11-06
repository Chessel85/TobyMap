// The stand-in sound player (P1-T10/T11, SON-7): the earcons through Web Audio.
// Each is a short WAV, fetched and decoded once, and played at the same time
// as speech. The page's mute is the core's: muted earcons never arrive here.

let context = null;
const buffers = new Map();

export function audio() {
  if (!context) {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return null;
    context = new Ctx();
  }
  return context;
}

// Called on a key press, because browsers only start audio after a user action.
export function unlock() {
  const ctx = audio();
  if (ctx && ctx.state === "suspended") ctx.resume();
}

async function load(file) {
  if (buffers.has(file)) return buffers.get(file);
  const promise = (async () => {
    const ctx = audio();
    const response = await fetch(new URL(`../sounds/${file}`, import.meta.url));
    if (!ctx || !response.ok) throw new Error(`No sound ${file}`);
    return ctx.decodeAudioData(await response.arrayBuffer());
  })();
  buffers.set(file, promise);
  promise.catch(() => buffers.delete(file));
  return promise;
}

export function preload(files) {
  for (const f of files) load(f).catch(() => {});
}

// info is the core's earcon_file(). Your own files are a desktop feature: the page plays the default.
export const played = [];
// The clicks of a held key: when each was due and when it was set to sound, on
// the page's clock (performance.now), for the held key test (P2-T14).
export const clicks = [];

// at, if given, is when to play on the page's clock. The sound card's own clock
// then starts it at exactly that moment, however busy the page is (DP140).
export async function play(info, at) {
  played.push(info.event);
  if (at !== undefined) clicks.push({ due: at, at: Math.max(at, performance.now()) });
  try {
    const buffer = await load(info.default);
    const ctx = audio();
    const source = ctx.createBufferSource();
    source.buffer = buffer;
    source.connect(ctx.destination);
    source.start(at === undefined ? 0 : audioTime(ctx, at));
  } catch (e) {
    // No sound file or no audio: nothing to do, the earcon is only a help.
  }
}

// A time on the page's clock as a time on the sound card's clock.
function audioTime(ctx, at) {
  const stamp = ctx.getOutputTimestamp ? ctx.getOutputTimestamp() : null;
  if (stamp && stamp.performanceTime) return Math.max(0, stamp.contextTime + (at - stamp.performanceTime) / 1000);
  return Math.max(0, ctx.currentTime + (at - performance.now()) / 1000);
}

// Sounds placed in space by the core's sound scene (P2-T6c; AD-10, SON-1). The core says
// how each is heard: pan, pitch, loudness and muffling. This only carries the numbers
// out, as the desktop's player does, so both place a sound the same way.
// placed is the list of what was made, for the browser tests.
export const placed = [];

// Plays a placed sound and gives the time on the sound card's clock when it ends, so a label
// that waits for it can start then; 0 if it did not play.
export async function playPlaced(p) {
  try {
    const buffer = await load(p.file.default);
    const source = connectPlaced(buffer, p);
    source.start();
    return audio().currentTime + buffer.duration / p.pitch;
  } catch (e) {
    // No sound file or no audio: nothing to do; the sound is only a help.
    return 0;
  }
}

// A buffer through the core's numbers: pitch, muffling, loudness, then the pan or the browser's
// HRTF. Gives the source, not started. The spatial voice uses it too (js/voice.js).
export function connectPlaced(buffer, p) {
  const ctx = audio();
  const source = ctx.createBufferSource();
  source.buffer = buffer;
  source.playbackRate.value = p.pitch;                  // lower behind you, in both modes
  const filter = ctx.createBiquadFilter();               // the muffling
  filter.type = "lowpass";
  filter.frequency.value = Math.min(p.cutoff_hz, ctx.sampleRate / 2);
  filter.Q.value = -3.0103;                              // in decibels: no peak at the cut-off
  const gain = ctx.createGain();
  gain.gain.value = p.gain;
  let panner;
  if (p.mode === "hrtf") {
    // Web Audio's own HRTF. The listener faces -z with +x to the right; the distance
    // is the core's loudness, so the panner itself changes nothing with distance.
    const r = (p.relative_deg * Math.PI) / 180;
    panner = new PannerNode(ctx, { panningModel: "HRTF", distanceModel: "linear", rolloffFactor: 0,
      positionX: Math.sin(r), positionY: 0, positionZ: -Math.cos(r) });
  } else {
    panner = new StereoPannerNode(ctx, { pan: p.pan });  // equal-power, as the desktop's
  }
  source.connect(filter).connect(gain).connect(panner).connect(ctx.destination);
  placed.push({ sound: p.sound, mode: p.mode, pitch: source.playbackRate.value, cutoff_hz: filter.frequency.value,
    gain: gain.gain.value, pan: p.mode === "hrtf" ? null : panner.pan.value,
    x: p.mode === "hrtf" ? panner.positionX.value : null, z: p.mode === "hrtf" ? panner.positionZ.value : null });
  return source;
}
