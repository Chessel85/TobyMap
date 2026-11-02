// Spike S6 in the browser (P0-T9, architecture 4.6 and 12.7). The voice runs
// in voice_worker.js. This page asks it for labels and places the sound in
// space with Web Audio's HRTF, as spike S1 decided, and times each step.
"use strict";

const VOICE = new URL("../../../../voices/piper/en_GB-alba-medium.onnx", location.href).href;
const LABELS = ["Berlin", "Bay of Biscay", "Llívia", "Isle of Skye", "Mont Saint-Michel", "Kilimanjaro",
                "River Thames", "Saint Petersburg"];
const DIRECTIONS = [[0, "ahead"], [45, "ahead right"], [90, "right"], [135, "behind right"],
                    [180, "behind"], [225, "behind left"], [270, "left"], [315, "ahead left"]];

const $ = (id) => document.getElementById(id);
let worker, ctx, playing, nextId = 0;
const waiting = new Map();

function addLine(text) {
  $("results").value += text + "\n";
}

function say(text) {
  $("status").textContent = "";
  setTimeout(() => { $("status").textContent = text; }, 50);
}

function browserName() {
  const ua = navigator.userAgent;
  if (ua.includes("Edg/")) return "Edge " + (ua.match(/Edg\/([\d.]+)/) || [])[1];
  if (ua.includes("Firefox/")) return "Firefox " + (ua.match(/Firefox\/([\d.]+)/) || [])[1];
  if (ua.includes("Chrome/")) return "Chrome " + (ua.match(/Chrome\/([\d.]+)/) || [])[1];
  return ua;
}

function startWorker() {
  worker = new Worker("voice_worker.js", { type: "module" });
  worker.onmessage = (e) => {
    const m = e.data;
    if (m.type === "line") { addLine(m.text); return; }
    const key = m.type === "loaded" || (m.type === "error" && m.id === undefined) ? "load" : m.id;
    const done = waiting.get(key);
    waiting.delete(key);
    if (done) done(m);
  };
  worker.onerror = (e) => {
    addLine("Error in the voice worker: " + e.message);
    for (const done of waiting.values()) done({ type: "error", text: e.message });
    waiting.clear();
  };
}

async function load(fresh) {
  if (worker) worker.terminate();
  startWorker();
  addLine(`Spike S6 in ${browserName()}, ${new Date().toISOString()}.`);
  say("Loading the voice.");
  const m = await new Promise((resolve) => {
    waiting.set("load", resolve);
    worker.postMessage({ type: "load", voiceUrl: VOICE, configUrl: VOICE + ".json", fresh });
  });
  if (m.type === "error") {
    addLine("The voice did not load: " + m.text);
    say("The voice did not load.");
    return { error: m.text };
  }
  say("The voice is ready.");
  return m.timings;
}

// One label, from request to sound. The browser's own report of the delay in
// the sound card is added, where the browser gives one.
async function speakFrom(text, bearing) {
  if (!worker) return { error: "The voice is not loaded." };
  if (!ctx) ctx = new AudioContext();
  if (ctx.state === "suspended") await ctx.resume();
  const start = performance.now();
  const id = nextId++;
  const m = await new Promise((resolve) => {
    waiting.set(id, resolve);
    worker.postMessage({ type: "speak", id, text });
  });
  if (m.type === "error") {
    addLine(`"${text}" failed: ${m.text}`);
    return { error: m.text };
  }
  const buffer = ctx.createBuffer(1, m.samples.length, m.rate);
  buffer.copyToChannel(m.samples, 0);
  const src = new AudioBufferSourceNode(ctx, { buffer });
  const rad = bearing * Math.PI / 180;
  // The same placing as the S1 web demo: the browser's HRTF, with distance switched off.
  const panner = new PannerNode(ctx, { panningModel: "HRTF", distanceModel: "linear", rolloffFactor: 0,
                                       positionX: Math.sin(rad), positionY: 0, positionZ: -Math.cos(rad) });
  src.connect(panner).connect(ctx.destination);
  if (playing) { try { playing.stop(); } catch { /* already ended */ } }
  playing = src;
  src.start();
  const toPlay = performance.now() - start;
  const device = 1000 * (ctx.outputLatency || ctx.baseLatency || 0);
  const result = {
    text, bearing, phonemes: m.phonemes, ids: m.ids,
    phonemize_ms: m.phonemize_ms, voice_ms: m.voice_ms,
    to_play_ms: +toPlay.toFixed(1), device_ms: +device.toFixed(1),
    seconds: +(m.samples.length / m.rate).toFixed(2),
  };
  addLine(`"${text}" from ${bearing} degrees: ${result.to_play_ms} ms to start playing ` +
          `(eSpeak NG ${result.phonemize_ms} ms, voice ${result.voice_ms} ms), plus ${result.device_ms} ms ` +
          `in the sound output as the browser reports it. ${result.seconds} seconds long.`);
  return result;
}

function median(values) {
  const s = [...values].sort((a, b) => a - b);
  return s.length ? s[Math.floor(s.length / 2)] : null;
}

// For the runner (web_run.py): load the voice, then speak every label twice.
async function run(fresh) {
  const timings = await load(fresh);
  if (timings.error) return { browser: browserName(), error: timings.error };
  const labels = [];
  for (let round = 0; round < 2; round++) {
    for (let i = 0; i < LABELS.length; i++) {
      labels.push(await speakFrom(LABELS[i], DIRECTIONS[i][0]));
      await new Promise((r) => setTimeout(r, 300));
    }
  }
  const ok = labels.filter((l) => !l.error);
  const toPlay = ok.map((l) => l.to_play_ms);
  const summary = {
    median_to_play_ms: median(toPlay), max_to_play_ms: Math.max(...toPlay),
    device_ms: ok.length ? ok[ok.length - 1].device_ms : null, failed: labels.length - ok.length,
  };
  addLine(`Labels: ${ok.length} spoken, ${summary.failed} failed. Request to start of playing: median ` +
          `${summary.median_to_play_ms} ms, longest ${summary.max_to_play_ms} ms, plus ${summary.device_ms} ms in the sound output.`);
  say("The test has finished.");
  return { browser: browserName(), crossOriginIsolated: self.crossOriginIsolated, timings, labels, summary };
}

for (const [bearing, name] of DIRECTIONS) {
  const option = document.createElement("option");
  option.value = bearing;
  option.textContent = `${name[0].toUpperCase()}${name.slice(1)}, ${bearing} degrees`;
  $("bearing").appendChild(option);
}
DIRECTIONS.forEach(([bearing, name], i) => {
  const b = document.createElement("button");
  b.type = "button";
  b.textContent = `${LABELS[i]}, ${name}`;
  b.addEventListener("click", () => speakFrom(LABELS[i], bearing));
  $("directions").appendChild(b);
});
$("load").addEventListener("click", () => load($("fresh").checked));
$("speak").addEventListener("click", () => speakFrom($("words").value, Number($("bearing").value)));
$("save").addEventListener("click", () => {
  const blob = new Blob([$("results").value], { type: "text/plain" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "spike-s6-web-results.txt";
  a.click();
});

window.s6 = { run, load, speakFrom, browserName };
