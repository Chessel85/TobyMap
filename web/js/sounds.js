// The stand-in sound player (P1-T10/T11, SON-7): the earcons through Web Audio.
// Each is a short WAV, fetched and decoded once, and played at the same time
// as speech. The page's mute is the core's: muted earcons never arrive here.

let context = null;
const buffers = new Map();

function audio() {
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
