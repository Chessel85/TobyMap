// The spatial voice in the browser (P2-T7b; SON-3, ANN-3, AD-10). The voice itself runs in
// voice_worker.js; this asks it for labels and plays them with the core's numbers, through
// the same chain as the other placed sounds (sounds.connectPlaced), so a label is heard from
// the same place as the item's sound, with the lower pitch behind.
//
// * The voice starts loading as soon as the page is up, in its own worker.
// * One label is made at a time. A label asked for while another is being made waits, and
//   only the newest waiting one is made; a newer label stops one already playing (ANN-3).
// * A label that waits for the item's sound starts on the sound card's clock when it ends.
// * Above what Piper can speak, the core's time stretching makes it faster at the same pitch,
//   and behind you lower without slowing it, in the core's worker (P2-T16g, mapcore/sound/stretch.py).
import * as sounds from "./sounds.js";

let worker = null;
let state = "loading";
let making = null;       // the label being made: {gen, voice, after, asked}
let waiting = null;      // the newest label asked for while one was being made
let playing = null;      // the source now playing
let gen = 0;
let stretcher = null;    // (samples, rate, factor, pitch) => a promise of the samples reshaped by the core
export const info = { threads: null, isolated: null, load_ms: null };
// Each label made, for the browser tests: its words, its numbers and the time from asking to sound.
export const labels = [];

export function start() {
  const threads = new URLSearchParams(location.search).get("threads") === "1" ? 1 : 4;
  try {
    worker = new Worker(new URL("../voice_worker.js", import.meta.url), { type: "module" });
  } catch (e) {
    state = "failed";
    return;
  }
  worker.onmessage = (e) => {
    const m = e.data;
    if (m.type === "loaded") {
      state = m.state;
      Object.assign(info, { threads: m.threads ?? null, isolated: m.isolated ?? null, load_ms: m.load_ms ?? null });
    } else if (m.type === "audio" || m.type === "error") {
      finished(m);
    }
  };
  worker.onerror = () => { if (state === "loading") state = "failed"; };
  worker.postMessage({ type: "load", threads });
}

export function setStretcher(fn) {
  stretcher = fn;
}

export function getState() {
  return state;
}

// v is the core's Response.voice; after is a promise of the time the item's sound ends, or
// null. Gives the voice's state at once: unless it is "ready", nothing is said.
export function say(v, after) {
  if (state !== "ready") return state;
  gen += 1;
  stop();
  const job = { gen, voice: v, after, asked: performance.now() };
  if (making) waiting = job;
  else ask(job);
  return state;
}

export function stop() {
  if (playing) {
    try { playing.stop(); } catch (e) { /* already ended */ }
    playing = null;
  }
}

function ask(job) {
  making = job;
  worker.postMessage({ type: "speak", id: job.gen, text: job.voice.text, rate: job.voice.rate });
}

async function finished(m) {
  const job = making;
  making = null;
  if (waiting) {
    const next = waiting;
    waiting = null;
    ask(next);
  }
  if (!job || m.type === "error" || job.gen !== gen) return;   // failed, or a newer label was asked for
  let samples = m.samples;
  const factor = job.voice.stretch || 1;
  const pitch = job.voice.pitch || 1;
  if ((factor > 1 || pitch < 1) && stretcher) {
    try { samples = (await stretcher(samples, m.rate, factor, pitch)) || samples; } catch (e) { /* said as made */ }
    if (job.gen !== gen) return;
  }
  const made = performance.now() - job.asked;   // the label made, before any wait for the item's sound
  const ctx = sounds.audio();
  if (!ctx) return;
  const buffer = ctx.createBuffer(1, samples.length, m.rate);
  buffer.copyToChannel(samples, 0);
  const at = job.after ? await job.after : 0;
  if (job.gen !== gen) return;
  const source = sounds.connectPlaced(buffer, job.voice.placed);
  source.start(Math.max(ctx.currentTime, at));
  playing = source;
  source.onended = () => { if (playing === source) playing = null; };
  labels.push({ text: job.voice.text, relative_deg: job.voice.placed.relative_deg, pitch,
                ms: Math.round(performance.now() - job.asked), made_ms: Math.round(made), threads: info.threads,
                stretch: factor, seconds: samples.length / m.rate, piper_seconds: m.samples.length / m.rate });
}
