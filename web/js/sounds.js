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
export async function play(info) {
  played.push(info.event);
  try {
    const buffer = await load(info.default);
    const source = audio().createBufferSource();
    source.buffer = buffer;
    source.connect(audio().destination);
    source.start();
  } catch (e) {
    // No sound file or no audio: nothing to do, the earcon is only a help.
  }
}
