// The web version of listening test blocks 1 (stereo with pitch) and 3 (beyond the view) (P1-T13).
// The numbers match mapcore/sound/curve.py and tools/listening_test/model.py.
"use strict";
const CURVE = { near: 0.05, edgeDb: -30, beyondDb: -36, brightHz: 16000, dullHz: 1500, beyondHz: 900 };
const LEVEL_FRACTION = { 1: 0.04, 2: 0.15, 3: 0.4, 4: 0.9, 5: 1.5 };
const BEHIND_RATE = 0.84;
const BLOCKS = [
  { id: 1, name: "stereo", trials: 12, kind: "static",
    words: "Block 1 of 2: stereo with a lower pitch behind. Press Space to hear a sound. Type the clock hour it came from, 1 to 12, with 12 straight ahead, then Enter. Type 0 if you can't tell. Then the distance from 1, very near, to 5, beyond the view, then Enter. R plays it again." },
  { id: 3, name: "beyond", trials: 10, kind: "beyond",
    words: "Block 2 of 2, which is block 3 of the full test: sounds beyond the view. Some are quiet and muffled, some a fixed tone. Same keys as before." },
];
const $ = (id) => document.getElementById(id);
let ctx = null, state = "idle", blockIndex = -1, trials = [], t = 0;
const rows = [];

function rng(seed) { let s = seed; return () => (s = (s * 1664525 + 1013904223) % 4294967296) / 4294967296; }
function shuffle(a, r) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; }

function makeTrials(block) {
  const r = rng(block.id);
  const hours = shuffle(Array.from({ length: block.trials }, (_, i) => (i % 12) + 1), r);
  const levels = shuffle(Array.from({ length: block.trials }, (_, i) => (i % 4) + 1), r);
  return hours.map((hour, i) => {
    let level = levels[i], style = "";
    if (block.kind === "beyond") { if (i % 2 === 0) { level = 5; style = (i / 2) % 2 === 0 ? "muffled" : "tone"; } }
    return { block: block.name, number: i + 1, hour, bearing: (hour % 12) * 30, level, fraction: LEVEL_FRACTION[level], style, plays: 1 };
  });
}

function gainDb(f) {
  if (f <= CURVE.near) return 0;
  if (f > 1) return CURVE.beyondDb;
  return CURVE.edgeDb * Math.log2(f / CURVE.near) / Math.log2(1 / CURVE.near);
}
function cutoff(f) {
  if (f > 1) return CURVE.beyondHz;
  if (f <= CURVE.near) return CURVE.brightHz;
  const x = Math.log2(f / CURVE.near) / Math.log2(1 / CURVE.near);
  return CURVE.brightHz * Math.pow(CURVE.dullHz / CURVE.brightHz, x);
}

function bursts(tone) {
  const rate = ctx.sampleRate, length = Math.floor(rate * 0.81);
  const buffer = ctx.createBuffer(1, length, rate), data = buffer.getChannelData(0);
  let seed = 1;
  for (let b = 0; b < 3; b++) {
    const start = Math.floor(rate * 0.27 * b), n = Math.floor(rate * 0.18);
    let last = 0;
    for (let i = 0; i < n; i++) {
      seed = (seed * 1664525 + 1013904223) % 4294967296;
      const white = seed / 2147483648 - 1;
      last = 0.97 * last + 0.03 * white;                       // roughly pink: a low-pass of white noise
      const fade = Math.min(1, i / (rate * 0.01), (n - i) / (rate * 0.01));
      data[start + i] = (tone ? 0.5 * Math.sin(2 * Math.PI * 600 * i / rate) : 8 * last) * fade;
    }
  }
  return buffer;
}

function playTrial(trial) {
  const fixedTone = trial.style === "tone";
  const f = fixedTone ? 0.5 : trial.fraction;
  const source = ctx.createBufferSource();
  source.buffer = bursts(fixedTone);
  const behind = Math.cos(trial.bearing * Math.PI / 180) < -1e-9;
  source.playbackRate.value = behind ? BEHIND_RATE : 1;
  const pan = ctx.createStereoPanner();
  pan.pan.value = Math.sin(trial.bearing * Math.PI / 180);
  const filter = ctx.createBiquadFilter();
  filter.type = "lowpass";
  filter.frequency.value = Math.min(cutoff(f), ctx.sampleRate / 2 * 0.9);
  const volume = ctx.createGain();
  volume.gain.value = 0.5 * Math.pow(10, gainDb(f) / 20);
  source.connect(filter).connect(pan).connect(volume).connect(ctx.destination);
  source.start();
}

function say(text) { $("instructions").textContent = text; }

function nextBlock() {
  blockIndex++;
  if (blockIndex >= BLOCKS.length) {
    state = "done";
    download();
    say("The listening test is finished. Your answers were downloaded as a file. Press the Close button.");
    return;
  }
  trials = makeTrials(BLOCKS[blockIndex]);
  t = 0;
  state = "ready";
  say(BLOCKS[blockIndex].words);
}

function download() {
  const cols = ["block", "trial", "style", "played_hour", "played_bearing", "played_level", "heard_hour", "heard_level", "plays"];
  const csv = [cols.join(",")].concat(rows.map((r) => cols.map((c) => r[c]).join(","))).join("\r\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
  a.download = `listening-test-web-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
}

function submit(text) {
  const trial = trials[t];
  const n = Number(text.trim());
  if (state === "hour") {
    if (!/^\d+$/.test(text.trim()) || n > 12) return say("Type an hour from 1 to 12, or 0 if you can't tell, then press Enter.");
    trial.heard_hour = n;
    state = "level";
    return say("Now the distance, from 1, very near, to 5, beyond the view, then Enter.");
  }
  if (state === "level") {
    if (!/^[1-5]$/.test(text.trim())) return say("Type a distance from 1 to 5, then press Enter.");
    rows.push({ block: trial.block, trial: trial.number, style: trial.style, played_hour: trial.hour, played_bearing: trial.bearing,
                played_level: trial.level, heard_hour: trial.heard_hour, heard_level: n, plays: trial.plays });
    t++;
    if (t >= trials.length) return nextBlock();
    state = "ready";
    say(`Trial ${t + 1} of ${trials.length}. Press Space.`);
  }
}

function play() {
  if (state === "ready") state = "hour";
  else if (state === "hour" || state === "level") trials[t].plays++;
  else return;
  playTrial(trials[t]);
}

$("start").addEventListener("click", () => {
  ctx = ctx || new AudioContext();
  ctx.resume();
  $("start").disabled = true;
  nextBlock();
  $("answer").focus();
});
$("close").addEventListener("click", () => window.close());
$("answer").addEventListener("keydown", (e) => {
  const empty = $("answer").value === "";
  if (e.key === " " && (state === "ready" || empty)) { e.preventDefault(); play(); }
  else if (e.key.toLowerCase() === "r" && empty && (state === "hour" || state === "level")) { e.preventDefault(); play(); }
  else if (e.key === "Enter") { e.preventDefault(); const v = $("answer").value; $("answer").value = ""; submit(v); }
});
