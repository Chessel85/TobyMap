// Look around in the browser (P3-T11a; SON-4, SON-3, INF-10, AD-10).
// The core's response.scan lists the items to play, in order, each with its sound and its spatial
// voice label already placed. This plays them one after another, as the desktop's desktop/scan.py
// does: the item's sound, then its label when the sound ends, then, once both have finished, a
// short pause, then the next. As each item starts, onItem(index) tells the core (scan_item), so
// Enter on the map goes to that item; at the end, onItem(null).
//
// Every 20 ms it looks whether the item still sounds: its sound, on the sound card's clock, or its
// label being made or played. An item never holds the scan longer than ITEM_LIMIT_MS, in case the
// voice worker stops answering. A response with stop_voice stops the scan (main.js).
import * as sounds from "./sounds.js";
import * as voice from "./voice.js";

const TICK_MS = 20;
const ITEM_LIMIT_MS = 15000;

let items = [];
let index = -1;
let gapMs = 300;
let pauseUntil = null;
let itemAt = 0;
let timer = null;
let gen = 0;
let soundLoading = false;   // the item's sound is still being loaded
let soundEnds = 0;          // when it ends, on the sound card's clock

let onItem = () => {};
let onSaid = () => {};      // (state, first): the voice's state as each label is asked for
export function setHandlers(item, said) { onItem = item; onSaid = said; }

// The id of each item started, for the browser tests.
export const started = [];

export function playing() {
  return items.length > 0;
}

export function start(scan) {
  stop();
  items = scan.items.slice();
  gapMs = (scan.gap_s ?? 0.3) * 1000;
  index = -1;
  next();
  if (playing()) timer = setInterval(tick, TICK_MS);
}

export function stop() {
  gen += 1;
  clearInterval(timer);
  timer = null;
  items = [];
  index = -1;
  pauseUntil = null;
  soundLoading = false;
  sounds.stopScan();
}

function next() {
  index += 1;
  pauseUntil = null;
  if (index >= items.length) {
    stop();
    onItem(null);
    return;
  }
  const item = items[index];
  const mine = gen;
  started.push(item.id);
  itemAt = performance.now();
  onItem(index);
  let ends = null;
  soundLoading = false;
  soundEnds = 0;
  if (item.sound) {
    soundLoading = true;
    ends = sounds.playPlaced(item.sound, true).then((t) => {
      if (gen === mine) { soundEnds = t; soundLoading = false; }
      return t;
    });
  }
  onSaid(voice.say(item.voice, item.voice.after && ends ? ends : null), index === 0);
}

function sounding() {
  const ctx = sounds.audio();
  return soundLoading || (ctx && ctx.currentTime < soundEnds) || voice.busy();
}

function tick() {
  if (!playing()) return;
  const now = performance.now();
  if (sounding() && now - itemAt < ITEM_LIMIT_MS) return;
  if (pauseUntil === null) pauseUntil = now + gapMs;
  else if (now >= pauseUntil) next();
}
