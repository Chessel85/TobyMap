// The spatial voice in the browser (P2-T7b; SON-3, AD-10, DP105): Piper's Alba voice in a
// worker of its own, beside the core's worker, from spike S6. Text becomes the sounds of
// speech (phonemes) through eSpeak NG in phonemizer.js, then sound through the voice model in
// ONNX Runtime Web. The page places the sound in space with the core's numbers (js/voice.js).
// Nothing here plays sound.
//
// Four threads where the page is cross-origin isolated (by the server's headers, or by the
// helper script coi-serviceworker.js on GitHub Pages), else one. ?threads=1 forces one.
// The files are fetched by tools/fetch_vendor.py --piper into vendor/piper; without them the
// voice is "missing" and the rest of the page carries on.
"use strict";

const VENDOR = new URL("./vendor/piper/", import.meta.url).href;
const VOICE = VENDOR + "voice/en_GB-alba-medium.onnx";
const CACHE = "tobymap-voice-1";
let ort, phonemize, session, config;

// The voice is kept in the browser's cache storage, so a later visit does not download its
// 63 MB again (DP98). Where cache storage is not allowed, it is downloaded each visit.
async function voiceBytes(url) {
  let cache = null;
  try { cache = await caches.open(CACHE); } catch { cache = null; }
  const stored = cache && await cache.match(url);
  if (stored) return stored.arrayBuffer();
  const response = await fetch(url);
  if (!response.ok) throw new Error(`The voice could not be downloaded: ${response.status}`);
  const bytes = await response.arrayBuffer();
  if (cache) {
    try { await cache.put(url, new Response(bytes, { headers: { "Content-Type": "application/octet-stream" } })); }
    catch { /* no room: it is downloaded again next time */ }
  }
  return bytes;
}

async function load({ threads }) {
  const started = performance.now();
  const configResponse = await fetch(VOICE + ".json").catch(() => null);
  if (!configResponse || !configResponse.ok) return { state: "missing" };
  config = await configResponse.json();
  ({ phonemize } = await import(VENDOR + "phonemizer.js"));
  ort = await import(VENDOR + "ort.wasm.min.mjs");
  ort.env.wasm.wasmPaths = VENDOR;
  ort.env.wasm.numThreads = self.crossOriginIsolated && threads !== 1
    ? Math.min(4, navigator.hardwareConcurrency || 1) : 1;
  const bytes = await voiceBytes(VOICE);
  session = await ort.InferenceSession.create(new Uint8Array(bytes), { executionProviders: ["wasm"] });
  await speak(".", 1);   // the first label is slow otherwise
  return { state: "ready", threads: ort.env.wasm.numThreads, isolated: self.crossOriginIsolated,
           load_ms: Math.round(performance.now() - started) };
}

// Piper's phoneme ids: start, then each phoneme followed by a gap, then end.
function toIds(phonemes) {
  const map = config.phoneme_id_map;
  const ids = [...map["^"], ...map["_"]];
  for (const ch of phonemes) if (map[ch]) ids.push(...map[ch], ...map["_"]);
  ids.push(...map["$"]);
  return ids;
}

// Silence at the start and end is cut so the label starts at once, and the loudness is
// evened out, as on the desktop (desktop/audio/voice.py).
function trimAndEvenOut(samples, threshold = 0.01, peak = 0.8) {
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

async function speak(text, rate) {
  const sentences = await phonemize(text, config.espeak.voice);
  const inf = config.inference;
  const parts = [];
  for (const sentence of sentences) {
    const ids = toIds(sentence);
    const feeds = {
      input: new ort.Tensor("int64", BigInt64Array.from(ids, BigInt), [1, ids.length]),
      input_lengths: new ort.Tensor("int64", BigInt64Array.from([BigInt(ids.length)]), [1]),
      scales: new ort.Tensor("float32", Float32Array.from([inf.noise_scale, inf.length_scale / Math.max(0.25, rate),
                                                            inf.noise_w]), [3]),
    };
    parts.push((await session.run(feeds)).output.data);
  }
  const joined = new Float32Array(parts.reduce((n, p) => n + p.length, 0));
  let at = 0;
  for (const p of parts) { joined.set(p, at); at += p.length; }
  return { samples: trimAndEvenOut(joined), rate: config.audio.sample_rate };
}

onmessage = async (e) => {
  const msg = e.data;
  try {
    if (msg.type === "load") postMessage({ type: "loaded", ...(await load(msg)) });
    else if (msg.type === "speak") {
      const result = await speak(msg.text, msg.rate || 1);
      postMessage({ type: "audio", id: msg.id, ...result }, [result.samples.buffer]);
    }
  } catch (err) {
    postMessage({ type: msg.type === "load" ? "loaded" : "error", state: "failed", id: msg.id,
                  text: String(err && err.message || err) });
  }
};
