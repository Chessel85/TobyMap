// Spike S6 in the browser (P0-T9): Piper's Alba voice in a worker of its own.
// Text becomes the sounds of speech (phonemes) through eSpeak NG in
// phonemizer.js, then sound through the voice model in ONNX Runtime Web. The
// page places the sound in space with Web Audio, as spike S1 decided.
// Nothing here plays sound.
"use strict";

const VENDOR = "../../../../web/vendor/piper/";
const CACHE = "tobymap-s6-voice";
let ort, phonemize, session, voiceConfig;

function line(text) {
  postMessage({ type: "line", text });
}

function ms(start) {
  return Math.round(performance.now() - start);
}

// The voice is kept in the browser's cache storage, so a later visit does not
// download its 60 MB again (DP98).
async function voiceBytes(url, fresh) {
  const cache = await caches.open(CACHE);
  if (fresh) await cache.delete(url);
  const stored = await cache.match(url);
  if (stored) return { bytes: await stored.arrayBuffer(), downloaded: false };
  const response = await fetch(url);
  if (!response.ok) throw new Error(`The voice could not be downloaded: ${response.status}`);
  const bytes = await response.arrayBuffer();
  await cache.put(url, new Response(bytes, { headers: { "Content-Type": "application/octet-stream" } }));
  return { bytes, downloaded: true };
}

async function load({ voiceUrl, configUrl, fresh }) {
  const timings = {};
  const all = performance.now();

  voiceConfig = await (await fetch(configUrl)).json();

  let t = performance.now();
  ({ phonemize } = await import(VENDOR + "phonemizer.js"));
  await phonemize("start", voiceConfigVoice());
  timings.phonemizer_ms = ms(t);
  line(`eSpeak NG (phonemizer.js) loaded and started in ${timings.phonemizer_ms} ms.`);

  t = performance.now();
  ort = await import(VENDOR + "ort.wasm.min.mjs");
  ort.env.wasm.wasmPaths = new URL(VENDOR, import.meta.url).href;
  // Several threads only work on a page that is cross-origin isolated.
  ort.env.wasm.numThreads = self.crossOriginIsolated ? Math.min(4, navigator.hardwareConcurrency || 1) : 1;
  timings.threads = ort.env.wasm.numThreads;
  timings.ort_import_ms = ms(t);

  t = performance.now();
  const { bytes, downloaded } = await voiceBytes(voiceUrl, fresh);
  timings.voice_ms = ms(t);
  timings.voice_downloaded = downloaded;
  timings.voice_mb = +(bytes.byteLength / 2 ** 20).toFixed(1);
  line(`The voice, ${timings.voice_mb} MB, ${downloaded ? "downloaded and stored" : "read from storage"} in ${timings.voice_ms} ms.`);

  t = performance.now();
  session = await ort.InferenceSession.create(new Uint8Array(bytes), { executionProviders: ["wasm"] });
  timings.session_ms = ms(t);
  line(`ONNX Runtime started the voice in ${timings.session_ms} ms, with ${timings.threads} thread(s).`);

  t = performance.now();
  await speak("Berlin");
  timings.first_label_ms = ms(t);
  line(`The first label, made silently, took ${timings.first_label_ms} ms.`);

  timings.total_ms = ms(all);
  line(`Ready ${timings.total_ms} ms after the voice began to load.`);
  return timings;
}

function voiceConfigVoice() {
  return voiceConfig.espeak.voice;
}

// Piper's phoneme ids: start, then each phoneme followed by a gap, then end.
function toIds(phonemes) {
  const map = voiceConfig.phoneme_id_map;
  const ids = [...map["^"], ...map["_"]];
  for (const ch of phonemes) {
    if (map[ch]) ids.push(...map[ch], ...map["_"]);
  }
  ids.push(...map["$"]);
  return ids;
}

// Silence at the start and end is trimmed so the label starts at once, and
// the loudness is evened out, as on the desktop (tools/spikes/s6/voices.py).
function trimAndNormalise(samples, threshold = 0.01, peak = 0.8) {
  let first = 0, last = samples.length - 1;
  while (first < samples.length && Math.abs(samples[first]) <= threshold) first++;
  while (last > first && Math.abs(samples[last]) <= threshold) last--;
  if (first >= samples.length) return samples;
  const out = samples.slice(Math.max(0, first - 100), Math.min(samples.length, last + 400));
  let top = 0;
  for (const v of out) top = Math.max(top, Math.abs(v));
  if (top > 0) for (let i = 0; i < out.length; i++) out[i] = out[i] / top * peak;
  return out;
}

async function speak(text) {
  let t = performance.now();
  const sentences = await phonemize(text, voiceConfigVoice());
  const phonemize_ms = performance.now() - t;
  const inf = voiceConfig.inference;
  t = performance.now();
  const parts = [];
  const allIds = [];
  for (const sentence of sentences) {
    const ids = toIds(sentence);
    allIds.push(ids);
    const feeds = {
      input: new ort.Tensor("int64", BigInt64Array.from(ids, BigInt), [1, ids.length]),
      input_lengths: new ort.Tensor("int64", BigInt64Array.from([BigInt(ids.length)]), [1]),
      scales: new ort.Tensor("float32", Float32Array.from([inf.noise_scale, inf.length_scale, inf.noise_w]), [3]),
    };
    const result = await session.run(feeds);
    parts.push(result.output.data);
  }
  const voice_ms = performance.now() - t;
  const total = parts.reduce((n, p) => n + p.length, 0);
  const joined = new Float32Array(total);
  let at = 0;
  for (const p of parts) { joined.set(p, at); at += p.length; }
  return {
    samples: trimAndNormalise(joined), rate: voiceConfig.audio.sample_rate,
    phonemes: sentences, ids: allIds,
    phonemize_ms: +phonemize_ms.toFixed(1), voice_ms: +voice_ms.toFixed(1),
  };
}

onmessage = async (e) => {
  const msg = e.data;
  try {
    if (msg.type === "load") {
      postMessage({ type: "loaded", timings: await load(msg) });
    } else if (msg.type === "speak") {
      const result = await speak(msg.text);
      postMessage({ type: "audio", id: msg.id, ...result }, [result.samples.buffer]);
    }
  } catch (err) {
    postMessage({ type: "error", id: msg.id, text: String(err && err.stack || err) });
  }
};
