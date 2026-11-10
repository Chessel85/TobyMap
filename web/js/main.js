// The web shell (architecture 5.6): the regions around the core in the
// worker. It only translates keys and clicks into commands, and the core's
// responses into speech, sound, painting and focus. Every key comes from the
// command registry, and every word from the core.
import { speak, log } from "./announcer.js";
import { keyName } from "./keys.js";
import { MenuBar } from "./menu.js";
import * as ownSounds from "./own_sounds.js";
import { paintScene } from "./painter.js";
import * as sounds from "./sounds.js";
import { Tree } from "./tree.js";
import * as voice from "./voice.js";
import { WorkerClient } from "./worker_client.js";

const $ = (id) => document.getElementById(id);
const mapEl = $("map"), mapArea = $("map-area"), canvas = $("canvas"), treeEl = $("tree"), details = $("details");
const dialog = $("dialog"), dialogTitle = $("dialog-title"), dialogText = $("dialog-text"), dialogClose = $("dialog-close");
const settingsDialog = $("settings"), keyDialog = $("keydialog"), inputDialog = $("inputdialog"), layersDialog = $("layersdialog");
const REGIONS = ["map", "panel", "details"];  // Tab never reaches the menu bar (DP93)
const STORAGE_KEY = "tobymap";

const client = new WorkerClient(new URL("../worker.js", import.meta.url));
let registry = null, words = null, menubar = null, tree = null;
let lastScene = null, returnFocus = null, describing = false, heldKey = null, lastSave = null;
let toggles = {};   // the ticks of the menu items, from the core

// window.tobymap is for the browser tests and diagnostics only.
window.tobymap = { announcements: log, earcons: sounds.played, heard: sounds.heard, clicks: sounds.clicks, ready: false, error: null,
  paints: 0, timings: [], placed: sounds.placed, labels: voice.labels, voiceInfo: voice.info, voiceState: voice.getState };
const told = new Set();   // voice problems and own sound files that failed, each said once

// Your own sound file could not be played, so the default was: said once for each file (SON-8).
sounds.setOwnFailed((info) => {
  const key = `own ${info.event} ${info.custom}`;
  if (told.has(key)) return;
  told.add(key);
  const { width, height } = mapSize();
  client.send({ type: "earcon_failed", event: info.event, width, height }).then((b) => handle(b)).catch(showError);
});

function mapSize() {
  const r = mapArea.getBoundingClientRect();
  return { width: Math.max(1, Math.round(r.width)), height: Math.max(1, Math.round(r.height)) };
}

// The focus point goes on the core's square at the map centre after every drawing, a pixel
// to one side each time, so the browser tells a magnifier it moved (ACC-8, DP146).
let nudge = 0;
function placeFocusPoint(f) {
  if (!f) return;
  nudge = 1 - nudge;
  mapEl.style.left = `${f.x + nudge}px`;
  mapEl.style.top = `${f.y}px`;
  mapEl.style.width = `${f.width}px`;
  mapEl.style.height = `${f.height}px`;
}

function paint(scene) {
  lastScene = scene;
  placeFocusPoint(scene.focus);
  const ms = paintScene(canvas, scene);
  window.tobymap.paints += 1;
  client.send({ type: "painted", paintMs: ms }).catch(() => {});
}

// The orientation beacon (P2-T9, SON-10): played at once when it starts, then every interval
// from where the core last placed it, so a turn or a step moves it at the next sound. A
// response's beacon of null changes nothing; placed null stops it.
const beacon = { placed: null, timer: null, intervalMs: 1000 };
function beaconUpdate(b) {
  if (!b) return;
  beacon.placed = b.placed;
  const ms = Math.round(b.interval_s * 1000);
  if (!b.placed || ms !== beacon.intervalMs) { clearInterval(beacon.timer); beacon.timer = null; }
  beacon.intervalMs = ms;
  if (b.placed && beacon.timer === null) {
    sounds.playBeacon(b.placed);
    beacon.timer = setInterval(() => { if (beacon.placed) sounds.playBeacon(beacon.placed); }, ms);
  }
}

// named: a dialog's answer whose words are already the map's name, read as focus returns (P2-T17c).
function handle(result, keyAt, held = false, named = false) {
  if (!result) return;  // a movement replaced by a later one (ANN-3)
  const r = result.response;
  let spoke = false;
  for (const a of r.announcements) {
    if (a.channel === "braille") { if (a.fallback) speak(a.fallback, "polite"); }  // no Braille-only route in a browser
    else if (!named) speak(a.text, a.priority);
    spoke = true;
  }
  for (const info of result.earcons || []) {
    if (!(held && info.event === "tick")) sounds.play(info);   // a held step's click was played on time already
  }
  const ends = (r.sounds || []).map((p) => sounds.playPlaced(p));   // placed in space by the core (P2-T6)
  if (r.voice) {   // a label in the spatial voice (P2-T7), after the item's sound
    const after = r.voice.after && ends.length ? Promise.all(ends).then((t) => Math.max(0, ...t)) : null;
    const state = voice.say(r.voice, after);
    if (state === "loading" || ((state === "missing" || state === "failed") && !told.has(state))) {
      told.add(state);
      const { width, height } = mapSize();
      client.send({ type: "voice_problem", problem: state, width, height }).then((b) => handle(b)).catch(showError);
    }
  }
  beaconUpdate(r.beacon);
  if (spoke && keyAt !== undefined) {
    const now = performance.now();
    window.tobymap.timings.push(now - keyAt);
    client.send({ type: "shell_times", keyMs: now - keyAt, handedMs: 0 }).catch(() => {});
  }
  if (result.describing !== undefined) describing = result.describing;
  if (result.registry) {
    registry = result.registry;
    client.latestOnly = new Set(registry.latest_only);
    if (menubar) { menubar.build(registry.menus); menubar.setChecked(toggles); }
  }
  if (result.toggles) {
    toggles = result.toggles;
    if (menubar) menubar.setChecked(toggles);
  }
  if (result.save && result.save !== lastSave) {
    lastSave = result.save;
    try { localStorage.setItem(STORAGE_KEY, result.save); } catch (e) { /* private browsing: nothing is kept */ }
  }
  if (result.scene) paint(result.scene);
  if (result.panel) tree.fill(result.panel);
  if (result.map_label !== undefined) { if (named) mapLabel = result.map_label; else setMapLabel(result.map_label); }
  if (result.details !== undefined) {
    details.value = result.details;
    details.setSelectionRange(0, 0);  // so Tab or F4 always lands on the first line
    details.scrollTop = 0;
  }
  if (r.focus) {
    if (r.focus.region === "panel") tree.focusItem(r.focus.item, r.focus.group || "within");
    else if (r.focus.region === "menu") menubar.focusBar();
    else if (r.focus.region === "map") { menubar.closeAll(false); mapEl.focus(); }
    else if (r.focus.region === "details") {
      details.setSelectionRange(0, 0);  // before focus, so the first line is read on arrival
      details.scrollTop = 0;
      details.focus();
    }
  }
  if (r.dialog) openDialog(r.dialog);
  if (r.background) {   // the Crossed and passed search, when the worker is free (P2-T5)
    const { width, height } = mapSize();
    client.idle({ type: "crossed", width, height }).then((b) => handle(b)).catch(showError);
  }
}

// The map's name is the place under the centre, so the screen reader says
// just the place when Tab arrives (PO feedback on spike S5). It changes only
// while the map does not have focus, so turning never makes the screen reader
// read the name again as well as the announcement.
let mapLabel = null;
function setMapLabel(label) {
  mapLabel = label;
  if (document.activeElement !== mapEl) mapEl.setAttribute("aria-label", label);
}
mapEl.addEventListener("blur", () => { if (mapLabel) mapEl.setAttribute("aria-label", mapLabel); });

function run(name, args = {}, keyAt) {
  const { width, height } = mapSize();
  return client.send({ type: "run", commands: [[name, args]], width, height }).then((r) => handle(r, keyAt)).catch(showError);
}

function release() {
  const { width, height } = mapSize();
  heldKey = null;
  stopHold();
  return client.send({ type: "release", width, height }).then((r) => handle(r)).catch(showError);
}

// Holding a movement key (DP129, DP140). The page keeps the beat itself: a little
// before each step's due time, from the core's timing, it sets the click on the
// sound card's clock; at the due time it sends the step to the worker. The click
// never waits for the worker, which may be busy drawing the map. Letting go before
// the due time takes back both. The core says how many of the next steps will
// move, so a step that would be blocked, at a pole, has no click.
const HOLD_LEAD_MS = 50;   // wake this early, so a busy page still has the click ready on time
let hold = null;

function startHold(name, pressedAt, info) {
  stopHold();
  if (!info || heldKey !== name) return;
  hold = { name, pressedAt, info, k: 0, sent: 0, left: info.unlimited ? Infinity : info.left,
           seen: performance.now(), timer: null, pending: new Set() };
  armHold();
}

// A click set early whose step is not yet due is taken back with its step, so
// letting go leaves no last click sounding after the key is up (2.10). A click the
// sound card has already started on will be heard, so its step is made at once:
// a click is never heard without its step.
function stopHold() {
  const h = hold;
  if (h) {
    clearTimeout(h.timer);
    for (const p of h.pending) {   // more than one at 30 steps a second, closer than the lead
      clearTimeout(p.timer);
      if (!sounds.cancel(p.click)) sendHeldStep(h, p.sent);
    }
  }
  hold = null;
}

function holdDue(h, k) {
  return h.pressedAt + h.info.delay_ms + k * h.info.every_ms;
}

function armHold() {
  hold.timer = setTimeout(holdStep, Math.max(0, holdDue(hold, hold.k) - HOLD_LEAD_MS - performance.now()));
}

function holdStep() {
  const h = hold;
  if (!h) return;
  if (performance.now() - h.seen > h.info.silence_ms) { release(); return; }   // the key was let go unseen
  const due = holdDue(h, h.k);
  // The click is set now, on the sound card's clock; the step waits for its due time,
  // so a key let go in between takes back both (stopHold).
  const click = h.info.tick && h.left > 0 ? sounds.play(h.info.earcon, due) : null;
  h.left -= 1;
  h.k += 1;
  const sent = ++h.sent;   // counted now, with h.left, so the core's count below stays right
  const p = { click, sent, timer: null };
  p.timer = setTimeout(() => { h.pending.delete(p); sendHeldStep(h, sent); }, Math.max(0, due - performance.now()));
  h.pending.add(p);
  armHold();
}

function sendHeldStep(h, sent) {
  if (hold !== h) return;
  const { width, height } = mapSize();
  client.send({ type: "run", commands: [[h.name, { held: true, repeat: true }]], width, height }).then((r) => {
    handle(r, undefined, true);
    // The core's count is from after this step; steps sent since are taken off.
    if (r && r.hold && hold === h) h.left = (r.hold.unlimited ? Infinity : r.hold.left) - (h.sent - sent);
  }).catch(showError);
}

function showError(error) {
  window.tobymap.error = String(error.message || error);
  console.error(error);
}

// Focus between the map, the Information panel and Details, wrapping round
// (UX section 2). Ctrl+Alt+M reaches the menu bar, and Tab leaves it (DP93).
function regionOf(node) {
  if (!node) return null;
  if (mapEl.contains(node)) return "map";
  if (treeEl.contains(node)) return "panel";
  if (node === details) return "details";
  if (menubar && menubar.contains(node)) return "menu";
  return null;
}

function focusRegion(region) {
  if (region === "map") mapEl.focus();
  else if (region === "panel") tree.focusCurrent();
  else if (region === "details") details.focus();
}

function moveRegion(step) {
  const here = regionOf(document.activeElement) || "map";
  if (here === "menu") return focusRegion(step > 0 ? "map" : "details");
  focusRegion(REGIONS[(REGIONS.indexOf(here) + step + REGIONS.length) % REGIONS.length]);
}

function openModal() {
  return dialog.open || settingsDialog.open || keyDialog.open || inputDialog.open || layersDialog.open;
}

document.addEventListener("keydown", (e) => {
  if (!registry) return;
  sounds.unlock();
  if (keyDialog.open) return captureKey(e);
  if (openModal()) {
    if (e.key === "Tab") trapTab(e);
    return;
  }
  if (e.key === "Tab" && !e.ctrlKey && !e.altKey && !describing) {
    e.preventDefault();
    moveRegion(e.shiftKey ? -1 : 1);
    return;
  }
  const key = keyName(e);
  if (!key) return;
  const region = regionOf(document.activeElement);
  const keyAt = performance.now();
  if (describing) {  // the key describer: every key is described, none is carried out
    e.preventDefault();
    const { width, height } = mapSize();
    client.send({ type: "press", key, region: region || "map", width, height }).then((r) => handle(r, keyAt)).catch(showError);
    return;
  }
  // The region's own keys (the map's, or the Information panel's), then the keys that work anywhere.
  const name = (region && registry.keymap[region] && registry.keymap[region][key]) || registry.keymap.global[key];
  if (!name) return;
  e.preventDefault();
  if (registry.held.includes(name)) {
    if (e.repeat) {   // the page's own beat steps; a repeat only shows the key is still down
      if (hold && hold.name === name) hold.seen = performance.now();
      return;
    }
    heldKey = name;
    stopHold();
    const { width, height } = mapSize();
    client.send({ type: "run", commands: [[name, {}]], width, height }).then(async (r) => {
      handle(r, keyAt);
      // Joined to a later movement, the press has no answer of its own: ask for the timing.
      const info = r ? r.hold : (await client.send({ type: "hold" })).hold;
      startHold(name, keyAt, info);
    }).catch(showError);
    return;
  }
  run(name, name === "help.keys" ? { region: region || "map" } : {}, keyAt);
});

document.addEventListener("keyup", (e) => {
  if (!registry || heldKey === null || e.repeat) return;
  const key = keyName(e);
  const name = key && (registry.keymap.map[key] || registry.keymap.global[key]);
  if (name === heldKey) release();
});
window.addEventListener("blur", () => { if (heldKey) release(); });

// What Tab reaches in a dialog: not a hidden page of the settings, and only the
// chosen tab of the tab list.
function tabbable(container) {
  return [...container.querySelectorAll("button, input, select, textarea")]
    .filter((el) => !el.disabled && el.tabIndex >= 0 && !el.closest("[hidden]"));
}

function trapTab(e) {  // keep focus inside a dialog
  const open = [settingsDialog, inputDialog, layersDialog, dialog].find((d) => d.open);
  const items = tabbable(open);
  const i = items.indexOf(document.activeElement);
  e.preventDefault();
  items[(i + (e.shiftKey ? -1 : 1) + items.length) % items.length].focus();
}

// The mouse: a click moves the location, the wheel changes the zoom, a drag turns the globe (NAV-9, NAV-13, VIS-4).
let press = null;
mapArea.addEventListener("pointerdown", (e) => {
  const r = canvas.getBoundingClientRect();
  mapEl.focus();
  press = { x: e.clientX, y: e.clientY, lastX: e.clientX, lastY: e.clientY, dragged: false, w: r.width, h: r.height, left: r.left, top: r.top };
  mapArea.setPointerCapture(e.pointerId);
  e.preventDefault();
});
mapArea.addEventListener("pointermove", (e) => {
  if (!press) return;
  if (!press.dragged && Math.abs(e.clientX - press.x) + Math.abs(e.clientY - press.y) < 5) return;
  press.dragged = true;
  const dx = e.clientX - press.lastX, dy = e.clientY - press.lastY;
  press.lastX = e.clientX;
  press.lastY = e.clientY;
  heldKey = "drag";
  run("map.drag", { dx, dy, width: press.w, height: press.h });
});
mapArea.addEventListener("pointerup", (e) => {
  if (!press) return;
  const p = press;
  press = null;
  if (p.dragged) release();
  else run("map.click", { x: e.clientX - p.left, y: e.clientY - p.top, width: p.w, height: p.h });
});
mapArea.addEventListener("wheel", (e) => {
  e.preventDefault();
  run("map.zoom_to", { direction: e.deltaY < 0 ? -1 : 1 });  // wheel up zooms in
}, { passive: false });

// Dialogs -----------------------------------------------------------------------

function openDialog(d) {
  returnFocus = document.activeElement && document.activeElement !== document.body ? document.activeElement : mapEl;
  if (d.kind === "settings") return openSettings(d);
  if (d.kind === "input") return openInput(d);
  if (d.kind === "layers") return openLayers(d);
  if (d.copy && navigator.clipboard) navigator.clipboard.writeText(d.copy).catch(() => {});
  dialogTitle.textContent = d.title;
  dialog.querySelectorAll(".sounds").forEach((el) => el.remove());
  dialog.querySelectorAll(".history").forEach((el) => el.remove());
  if (d.kind === "sounds") soundsList(d);
  if (d.kind === "history") historyList(d);
  dialogText.hidden = d.kind === "sounds" || d.kind === "history";
  dialogText.value = d.text;
  dialogText.setAttribute("aria-label", d.title);
  dialog.showModal();
  if (d.kind === "sounds") return $("sounds-list").focus();
  if (d.kind === "history") return $("history-list").focus();
  dialogText.focus();
  dialogText.setSelectionRange(0, 0);
}

// Help, The sounds: one list, a single stop for Tab, and a Play button. Enter,
// Space or Play plays the chosen sound (DP134, PO feedback on web checklist 9).
function soundsList(d) {
  const list = document.createElement("select");
  list.id = "sounds-list";
  list.className = "sounds";
  list.size = Math.min(d.items.length, 8);
  list.setAttribute("aria-label", d.title);
  for (const item of d.items) {
    const o = document.createElement("option");
    o.value = item.event;
    o.textContent = item.label;
    list.appendChild(o);
  }
  list.selectedIndex = 0;
  const play = () => { if (list.value) run("sound.preview", { event: list.value }); };
  list.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); play(); }
  });
  const playButton = button(d.play, play, "sounds-play");
  playButton.className = "sounds";
  dialogTitle.after(list, playButton);
}

// The announcement history: one list, newest first. Enter on an entry goes back to the place it was
// said at, and closes the list; an entry with no place says so and the list stays (ANN-4, DP141).
function historyList(d) {
  const help = document.createElement("p");
  help.id = "history-help";
  help.className = "history";
  help.textContent = d.help;
  const list = document.createElement("select");
  list.id = "history-list";
  list.className = "history";
  list.size = Math.min(d.lines.length, 10);
  list.setAttribute("aria-label", d.title);
  list.setAttribute("aria-describedby", "history-help");
  for (const line of d.lines) {
    const o = document.createElement("option");
    o.textContent = line;
    list.appendChild(o);
  }
  list.selectedIndex = 0;
  const message = document.createElement("p");
  message.id = "history-message";
  message.className = "history";
  list.addEventListener("keydown", (e) => {
    if (e.key !== "Enter") return;
    e.preventDefault();
    submit(d.go, { index: list.selectedIndex }, message, dialog);
  });
  dialogTitle.after(help, list, message);
}

// Send a typed answer or a chosen entry to the core. If it is refused, show and say why and keep the
// box open; otherwise close the box and carry out the answer.
function submit(name, args, message, box) {
  const { width, height } = mapSize();
  return client.send({ type: "run", commands: [[name, args]], width, height }).then((r) => {
    if (r.response.error) {
      message.textContent = r.response.error;
      speak(r.response.error, "assertive");
      return;
    }
    closeWithAnswer(box, [r]);
  }).catch(showError);
}

// Close a dialog and carry out its answer, such as Go to's place or the layers changed. The screen
// reader reads the map's name as the focus comes back to it, so what the answer says becomes that
// name and is not spoken as well; with nothing to say, the name is the place after the changes.
// Spoken too, the place was said twice; set after the close, the old place was read (P2-T17c, web
// checklist 5.2 and 8.6). The name is set while the box still has focus, as closing it moves the focus.
function closeWithAnswer(box, results) {
  const target = returnTarget();
  if (target === mapEl) {
    const said = [];
    for (const r of results) {
      for (const a of r.response.announcements) if (a.channel !== "braille") said.push(a.text);
      if (r.map_label !== undefined) mapLabel = r.map_label;   // the name again once the map is left
    }
    mapEl.setAttribute("aria-label", said.join(" ") || mapLabel || "");
  }
  box.close();
  for (const r of results) handle(r, undefined, false, target === mapEl);
}

// The layers list (SCP-6, SCP-7): a check box for each layer under its group; Space switches it. A
// Settings button opens the zoom range and crossing sound of the layer last focused, in the same box.
// OK sends one layers.set for each layer changed, Cancel sends nothing. All words come from the core.
function openLayers(d) {
  const box = layersDialog;
  const layers = {};
  // Pyodide turns None into undefined; null is "no limit" and "no sound" in the lists below.
  for (const g of d.groups) for (const l of g.layers) {
    layers[l.id] = { ...l, max_zoom_m: l.max_zoom_m ?? null, crossing_earcon: l.crossing_earcon ?? null };
  }
  const start = JSON.parse(JSON.stringify(layers));
  let current = null;

  const showList = () => {
    const body = focusModeBody(box);
    box.setAttribute("aria-label", d.title);
    const title = document.createElement("h2");
    title.textContent = d.title;
    body.append(title);
    for (const g of d.groups) {
      const set = document.createElement("fieldset");
      const legend = document.createElement("legend");
      legend.textContent = g.name;
      set.append(legend);
      for (const l of g.layers) {
        const label = document.createElement("label");
        const check = document.createElement("input");
        check.type = "checkbox";
        check.checked = layers[l.id].on;
        check.dataset.layer = l.id;
        check.addEventListener("change", () => { layers[l.id].on = check.checked; });
        check.addEventListener("focus", () => { current = l.id; });
        label.append(check, " " + l.name);
        set.append(label, document.createElement("br"));
      }
      body.append(set);
    }
    current = current || Object.keys(layers)[0];
    const settings = button(d.words.settings_button, () => showSettings(), "layers-settings");
    const ok = button(d.words.ok, apply, "layers-ok");
    const cancel = button(d.words.cancel, () => box.close(), "layers-cancel");
    body.append(settings, ok, cancel);
  };

  const apply = () => {
    const commands = [];
    for (const id of Object.keys(layers)) {
      const values = {};
      for (const f of ["on", "min_zoom_m", "max_zoom_m", "crossing_earcon"]) {
        if (layers[id][f] !== start[id][f]) values[f] = layers[id][f];
      }
      if (Object.keys(values).length) commands.push([d.set, { layer: id, values }]);
    }
    if (!commands.length) return box.close();
    const { width, height } = mapSize();
    client.send({ type: "run", commands, width, height }).then((r) => closeWithAnswer(box, [r])).catch(showError);
  };

  const zoomSelect = (name, value, none) => {
    const sel = document.createElement("select");
    sel.setAttribute("aria-label", name);
    const add = (v, text) => {
      const o = document.createElement("option");
      o.value = JSON.stringify(v);
      o.textContent = text;
      sel.append(o);
    };
    add(none, d.every_zoom);
    for (const z of d.zooms) add(z.value, z.label);
    sel.value = JSON.stringify(value === undefined ? none : value);
    return sel;
  };

  const showSettings = () => {
    const l = layers[current];
    const body = focusModeBody(box);
    const title = document.createElement("h2");
    title.textContent = d.words.settings_title.replace("{layer}", l.name);
    box.setAttribute("aria-label", title.textContent);
    const row = (text, control) => {
      const label = document.createElement("label");
      label.append(text + " ", control);
      return label;
    };
    const minZoom = zoomSelect(d.words.min_zoom, l.min_zoom_m || 0, 0);
    const maxZoom = zoomSelect(d.words.max_zoom, l.max_zoom_m, null);
    const crossing = document.createElement("select");
    crossing.setAttribute("aria-label", d.words.crossing);
    for (const [v, text] of [[null, d.words.no_sound], ...d.earcons.map((e) => [e.event, e.label])]) {
      const o = document.createElement("option");
      o.value = JSON.stringify(v);
      o.textContent = text;
      crossing.append(o);
    }
    crossing.value = JSON.stringify(l.crossing_earcon);
    const message = document.createElement("p");
    message.id = "layer-settings-message";   // shown here and said by the announcer, once
    const ok = button(d.words.ok, () => {
      const low = JSON.parse(minZoom.value), high = JSON.parse(maxZoom.value);
      const { width, height } = mapSize();
      client.send({ type: "run", commands: [[d.check, { low, high }]], width, height }).then((r) => {
        if (r.response.error) { message.textContent = r.response.error; speak(r.response.error, "assertive"); return; }
        Object.assign(l, { min_zoom_m: low, max_zoom_m: high, crossing_earcon: JSON.parse(crossing.value) });
        showList();
        box.querySelector(`[data-layer="${current}"]`).focus();
      }).catch(showError);
    }, "layer-settings-ok");
    const cancel = button(d.words.cancel, () => {
      showList();
      box.querySelector(`[data-layer="${current}"]`).focus();
    }, "layer-settings-cancel");
    body.append(title, row(d.words.min_zoom, minZoom), document.createElement("br"),
               row(d.words.max_zoom, maxZoom), document.createElement("br"),
               row(d.words.crossing, crossing), message, ok, cancel);
    minZoom.focus();
  };

  showList();
  box.showModal();
  box.querySelector("input").focus();
}

// Space ticks a box, and Enter anywhere but on a button presses OK: the list's, or the layer
// settings' (PO feedback on web checklist 2.6, as on the desktop).
layersDialog.addEventListener("keydown", (e) => {
  if (e.key !== "Enter" || e.target.tagName === "BUTTON") return;
  e.preventDefault();
  ($("layer-settings-ok") || $("layers-ok")).click();
});

// A box to type in, with OK and Cancel: a bearing or coordinates (NAV-8, NAV-12, ACC-7).
function openInput(d) {
  const box = inputDialog;
  box.replaceChildren();
  const title = document.createElement("h2");
  title.textContent = d.title;
  box.setAttribute("aria-label", d.title);
  const label = document.createElement("label");
  label.textContent = d.label;
  const field = document.createElement("input");
  field.type = "text";
  field.id = "input-field";
  field.autocomplete = "off";
  field.spellcheck = false;
  label.htmlFor = field.id;
  const help = document.createElement("p");
  help.id = "input-help";
  help.textContent = d.help;
  // Go to has no help: its label is enough (the PO, 8 November 2026).
  if (d.help) field.setAttribute("aria-describedby", "input-help");
  const message = document.createElement("p");
  message.id = "input-message";
  const go = () => submit(d.submit, { text: field.value }, message, box).then(() => { if (box.open) field.select(); });
  const ok = button(d.ok, go, "input-ok");
  const cancel = button(d.cancel, () => box.close(), "input-cancel");
  box.append(title, label, field, ...(d.help ? [help] : []), message, ok, cancel);
  field.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); go(); } });
  box.showModal();
  field.focus();
}

dialogClose.addEventListener("click", () => dialog.close());
function returnTarget() {
  // Menu commands return focus to the map, as on the desktop.
  return returnFocus && document.contains(returnFocus) && !menubar.contains(returnFocus) ? returnFocus : mapEl;
}
function afterClose() {
  returnTarget().focus();
}
dialog.addEventListener("close", afterClose);
settingsDialog.addEventListener("close", afterClose);
inputDialog.addEventListener("close", afterClose);
layersDialog.addEventListener("close", afterClose);
// Enter in a settings field presses OK, as on the desktop (web checklist 5).
settingsDialog.addEventListener("keydown", (e) => {
  const el = e.target;
  if (e.key === "Enter" && (el.tagName === "SELECT" || (el.tagName === "INPUT" && el.type !== "file"))
      && el.id !== "settings-keys") {
    e.preventDefault();
    $("settings-ok").click();
  }
});

// NVDA's browse mode turns Enter on a check box into a click, so Enter ticked the box instead
// of pressing OK, and the page never saw the key (P2-T17b, web checklist 8.6 and 10.6). Inside
// role="application" NVDA stays in focus mode, as on the map, so Enter and Space reach the page:
// Space ticks, Enter presses OK, and Enter on a button presses that button.
function focusModeBody(box) {
  const body = document.createElement("div");
  body.className = "dialog-body";
  body.setAttribute("role", "application");
  box.replaceChildren(body);
  return body;
}

function button(label, onClick, id) {
  const b = document.createElement("button");
  b.type = "button";
  b.textContent = label;
  if (id) b.id = id;
  b.addEventListener("click", onClick);
  return b;
}

// The settings dialog: a tab list with one page for each group, as on the
// desktop, so it is not one long page (PO feedback on web checklist 2). Left and
// Right move along the tabs; Tab goes into the page. Enter in a field is OK.
async function openSettings() {
  const schema = await client.send({ type: "schema" });
  const body = focusModeBody(settingsDialog);
  const title = document.createElement("h2");
  title.textContent = words.settings_title;
  settingsDialog.setAttribute("aria-label", words.settings_title);
  body.appendChild(title);
  const tablist = document.createElement("div");
  tablist.setAttribute("role", "tablist");
  tablist.setAttribute("aria-label", words.settings_title);
  body.appendChild(tablist);
  const tabs = [], pages = [];
  const addPage = (id, label) => {
    const tab = document.createElement("button");
    tab.type = "button";
    tab.id = `settings-tab-${id}`;
    tab.setAttribute("role", "tab");
    tab.setAttribute("aria-controls", `settings-page-${id}`);
    tab.textContent = label;
    const page = document.createElement("div");
    page.id = `settings-page-${id}`;
    page.className = "settings-page";
    page.setAttribute("role", "tabpanel");
    page.setAttribute("aria-labelledby", tab.id);
    const i = tabs.length;
    tab.addEventListener("click", () => choose(i));
    tab.addEventListener("keydown", (e) => {
      const step = { ArrowRight: 1, ArrowLeft: -1 }[e.key];
      if (e.key === "Home" || e.key === "End") { e.preventDefault(); choose(e.key === "Home" ? 0 : tabs.length - 1, true); }
      else if (step) { e.preventDefault(); choose((i + step + tabs.length) % tabs.length, true); }
    });
    tablist.appendChild(tab);
    body.appendChild(page);
    tabs.push(tab);
    pages.push(page);
    return page;
  };
  const choose = (i, focus) => {
    tabs.forEach((tab, k) => {
      tab.setAttribute("aria-selected", String(k === i));
      tab.tabIndex = k === i ? 0 : -1;
      pages[k].hidden = k !== i;
    });
    if (focus) tabs[i].focus();
  };
  const controls = {};
  const ownChanges = new Map();   // your own sound files chosen, kept in the browser only on OK
  for (const tab of schema.tabs) {
    const page = addPage(tab.id, tab.label);
    for (const f of tab.fields) {
      const label = document.createElement("label");
      label.textContent = f.label + " ";
      let control;
      if (f.kind === "choice") {
        control = document.createElement("select");
        for (const [value, text] of f.choices) {
          const o = document.createElement("option");
          o.value = value;
          o.textContent = text;
          control.appendChild(o);
        }
        control.value = schema.values[f.id];
      } else if (f.kind === "yes_no") {
        control = document.createElement("input");
        control.type = "checkbox";
        control.checked = !!schema.values[f.id];
      } else if (f.kind === "sound_file") {
        control = soundFileField(f, schema.values[f.id], ownChanges);
      } else {
        control = document.createElement("input");
        control.type = f.kind === "number" ? "number" : "text";
        if (f.kind === "number") { control.min = f.min; control.max = f.max; }
        control.value = schema.values[f.id];
        // Arriving with Tab chooses the whole value, so typing replaces it (web checklist 8).
        control.addEventListener("focus", () => control.select());
      }
      control.dataset.field = f.id;
      control.dataset.kind = f.kind;
      controls[f.id] = control;
      label.appendChild(control);
      page.appendChild(label);
      if (control.extras) page.append(" ", ...control.extras);
      page.appendChild(document.createElement("br"));
    }
  }
  // The keys: one list, a single stop for Tab, and a Change key button, as on the desktop.
  const keys = addPage("keys", words.keys_tab);
  const keyList = document.createElement("select");
  keyList.id = "settings-keys";
  keyList.size = 10;
  keyList.setAttribute("aria-label", words.keys_tab);
  const fillKeys = () => {
    const keep = Math.max(0, keyList.selectedIndex);
    keyList.textContent = "";
    for (const c of schema.keys) {
      const o = document.createElement("option");
      o.textContent = `${c.label}: ${c.key_text || words.no_key}`;
      keyList.appendChild(o);
    }
    keyList.selectedIndex = keep;
  };
  fillKeys();
  const changeKey = async () => {
    const c = schema.keys[keyList.selectedIndex];
    if (!c) return;
    const k = await askKey(c);
    if (k !== null) { c.key = k; c.key_text = await client.send({ type: "key_text", key: k }); fillKeys(); }
    keyList.focus();
  };
  keyList.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); e.stopPropagation(); changeKey(); } });
  keys.append(keyList, document.createElement("br"), button(words.key_change, changeKey, "settings-change-key"));
  choose(0);
  const bar = document.createElement("div");
  bar.appendChild(button(words.ok, async () => {
    for (const [event, change] of ownChanges) {
      try {
        if (change) await ownSounds.put(event, change.name, change.bytes);
        else await ownSounds.remove(event);
      } catch (e) { /* no storage, as in private browsing: the default plays and you are told */ }
    }
    if (ownChanges.size) sounds.forgetOwn();
    for (const [id, control] of Object.entries(controls)) {
      const value = control.dataset.kind === "yes_no" ? control.checked
        : control.dataset.kind === "number" ? Number(control.value) : control.value;
      if (value !== schema.values[id]) await run("settings.set", { field: id, value });
    }
    settingsDialog.close();
  }, "settings-ok"));
  bar.appendChild(button(words.cancel, () => settingsDialog.close(), "settings-cancel"));
  bar.appendChild(button(words.export, exportSettings, "settings-export"));
  const file = document.createElement("input");
  file.type = "file";
  file.accept = "application/json";
  file.setAttribute("aria-label", words.import);
  file.addEventListener("change", () => importSettings(file));
  bar.appendChild(file);
  body.appendChild(bar);
  settingsDialog.showModal();
  tabs[0].focus();
}

// Your own sound file for an earcon (P2-T8b, SON-8, DP123): a read-only box with the file's
// name, empty for the default, then Choose file and Use the default. A file that is not a
// WAV sound the browser can play is refused, shown and said. Nothing is kept until OK.
function soundFileField(f, value, ownChanges) {
  const control = document.createElement("input");
  control.type = "text";
  control.readOnly = true;
  control.value = value;
  control.placeholder = words.default_sound;
  const picker = document.createElement("input");
  picker.type = "file";
  picker.accept = ".wav,audio/wav,audio/x-wav,audio/wave";
  picker.hidden = true;
  picker.id = `settings-file-${f.earcon}`;
  const message = document.createElement("span");
  message.setAttribute("role", "status");
  message.id = `settings-file-message-${f.earcon}`;
  const choose = button(words.choose_file, () => picker.click(), `settings-choose-${f.earcon}`);
  choose.setAttribute("aria-label", words.choose_file_for.replace("{name}", f.name));
  const useDefault = button(words.use_default, () => {
    control.value = "";
    message.textContent = "";
    ownChanges.set(f.earcon, null);
    control.focus();
  }, `settings-default-${f.earcon}`);
  useDefault.setAttribute("aria-label", words.use_default_for.replace("{name}", f.name));
  picker.addEventListener("change", async () => {
    const file = picker.files[0];
    picker.value = "";
    if (!file) return;
    const bytes = await file.arrayBuffer();
    let ok = ownSounds.isWav(bytes);
    if (ok) {
      try { await sounds.audio().decodeAudioData(bytes.slice(0)); } catch (e) { ok = false; }
    }
    if (ok) {
      control.value = file.name;
      message.textContent = "";
      ownChanges.set(f.earcon, { name: file.name, bytes });
    } else {
      message.textContent = words.file_unreadable.replace("{file}", file.name);   // shown and said once
      speak(message.textContent, "assertive");
    }
    choose.focus();
  });
  control.extras = [choose, useDefault, picker, message];   // on the box's line, after its label
  return control;
}

function exportSettings() {
  const blob = new Blob([lastSave || "{}"], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "tobymap-settings.json";
  a.click();
  URL.revokeObjectURL(a.href);
}

async function importSettings(input) {
  const file = input.files[0];
  if (!file) return;
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(JSON.parse(await file.text()))); } catch (e) { return; }
  location.reload();
}

// Press the key you want for a command (ACC-3). Resolves to the key, or null if cancelled.
function askKey(command) {
  return new Promise((resolve) => {
    keyDialog.textContent = "";
    keyDialog.setAttribute("aria-label", command.label);
    const prompt = document.createElement("p");
    prompt.textContent = words.key_prompt;
    const field = document.createElement("input");
    field.type = "text";
    field.readOnly = true;
    field.value = command.key_text || command.key;
    field.setAttribute("aria-label", words.key_field);
    field.id = "key-field";
    const message = document.createElement("p");
    message.id = "key-message";
    message.setAttribute("role", "status");
    keyDialog.dataset.key = command.key;
    const finish = (value) => { keyDialog.close(); resolve(value); };
    const apply = async () => {
      const { width, height } = mapSize();
      const r = await client.send({ type: "run", commands: [["keys.remap", { command: command.name, key: keyDialog.dataset.key }]], width, height });
      const said = r.response.announcements.map((a) => a.text).join(" ");
      if (r.response.settings_changed) { handle(r); finish(keyDialog.dataset.key); }
      else { message.textContent = said; speak(said, "assertive"); field.focus(); }   // shown and spoken (checklist 2.6)
    };
    const bar = document.createElement("div");
    bar.appendChild(button(words.ok, apply, "key-ok"));
    bar.appendChild(button(words.key_clear, () => { keyDialog.dataset.key = ""; field.value = ""; $("key-message").textContent = ""; field.focus(); }, "key-clear"));
    bar.appendChild(button(words.cancel, () => finish(null), "key-cancel"));
    keyDialog.append(prompt, field, message, bar);
    keyDialog.showModal();
    field.focus();
  });
}

function captureKey(e) {
  const field = $("key-field");
  if (document.activeElement !== field) {
    if (e.key === "Tab") trapKeyTab(e);
    return;
  }
  if (e.key === "Tab") return trapKeyTab(e);
  const key = keyName(e);
  e.preventDefault();
  if (key) {
    keyDialog.dataset.key = key;
    field.value = key;
    $("key-message").textContent = "";
    client.send({ type: "key_text", key }).then((text) => { if (keyDialog.dataset.key === key) field.value = text; }).catch(() => {});
  }
}

function trapKeyTab(e) {
  const items = [...keyDialog.querySelectorAll("button, input")];
  const i = items.indexOf(document.activeElement);
  e.preventDefault();
  items[(i + (e.shiftKey ? -1 : 1) + items.length) % items.length].focus();
}

function applyWords() {
  document.title = words.window_title;
  treeEl.setAttribute("aria-label", words.panel);
  details.setAttribute("aria-label", words.details);
  $("menubar").setAttribute("aria-label", words.menu_bar);
  dialogClose.textContent = words.close;
}

async function boot() {
  mapArea.hidden = false;
  $("side").hidden = false;
  client.onNotice = (text) => speak(text, "polite");   // the map download's progress
  const { width, height } = mapSize();
  let saved = "";
  try { saved = localStorage.getItem(STORAGE_KEY) || ""; } catch (e) { saved = ""; }
  // ?at=43.08,-79.08 in the address starts there instead of the last place (for testing).
  const at = new URLSearchParams(location.search).get("at") || "";
  // ?slowdraw=200 makes every drawing take 200 ms longer, for the held key test only (P2-T14).
  const slowMs = Number(new URLSearchParams(location.search).get("slowdraw")) || 0;
  const result = await client.send({ type: "start", width, height, saved, at, slowMs });
  registry = result.registry;
  words = result.words;
  client.latestOnly = new Set(registry.latest_only);
  applyWords();
  tree = new Tree(treeEl, (id, group) => run("panel.select", { item: id, group }));
  menubar = new MenuBar($("menubar"), registry.menus, (name) => { mapEl.focus(); run(name, name === "help.keys" ? { region: "map" } : {}); },
    moveRegion, () => mapEl.focus());
  $("loading").remove();
  $("app").removeAttribute("aria-busy");
  // The start is not spoken: the screen reader reads the map's name as the focus arrives, which cut
  // the start off, so "Press F1 for keys" was never heard. The map is named with the start, less the
  // page's title, so it is heard once, in full; leaving the map names it after the place (P2-T17d).
  mapEl.setAttribute("aria-label", result.start_label);
  handle(result, undefined, false, true);
  sounds.preload(result.preload);
  mapEl.focus();
  window.tobymap.ready = true;
  voice.start();   // the spatial voice loads in its own worker while you start (P2-T7b)
  voice.setStretcher((samples, rate, factor, pitch) => client.send({ type: "stretch", samples, rate, factor, pitch }));

  let resizeTimer = null;
  new ResizeObserver(() => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      const size = mapSize();
      if (lastScene && size.width === lastScene.width && size.height === lastScene.height) return;
      client.send({ type: "scene", ...size }).then((r) => r && paint(r.scene)).catch(showError);
    }, 100);
  }).observe(mapArea);
}

boot().catch((error) => {
  showError(error);
  $("loading").textContent = `TobyMap could not start: ${window.tobymap.error}`;
});
