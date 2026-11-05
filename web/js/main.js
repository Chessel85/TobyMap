// The web shell (architecture 5.6): the regions around the core in the
// worker. It only translates keys and clicks into commands, and the core's
// responses into speech, sound, painting and focus. Every key comes from the
// command registry, and every word from the core.
import { speak, log } from "./announcer.js";
import { keyName } from "./keys.js";
import { MenuBar } from "./menu.js";
import { paintScene } from "./painter.js";
import * as sounds from "./sounds.js";
import { Tree } from "./tree.js";
import { WorkerClient } from "./worker_client.js";

const $ = (id) => document.getElementById(id);
const mapEl = $("map"), canvas = $("canvas"), treeEl = $("tree"), details = $("details");
const dialog = $("dialog"), dialogTitle = $("dialog-title"), dialogText = $("dialog-text"), dialogClose = $("dialog-close");
const settingsDialog = $("settings"), keyDialog = $("keydialog");
const REGIONS = ["map", "panel", "details"];  // Tab never reaches the menu bar (DP93)
const STORAGE_KEY = "tobymap";

const client = new WorkerClient(new URL("../worker.js", import.meta.url));
let registry = null, words = null, menubar = null, tree = null;
let lastScene = null, returnFocus = null, describing = false, heldKey = null, lastSave = null;
let toggles = { "step.link": false, "sound.mute": false, "help.describer": false };

// window.tobymap is for the browser tests and diagnostics only.
window.tobymap = { announcements: log, earcons: sounds.played, ready: false, error: null, paints: 0, timings: [] };

function mapSize() {
  const r = mapEl.getBoundingClientRect();
  return { width: Math.max(1, Math.round(r.width)), height: Math.max(1, Math.round(r.height)) };
}

function paint(scene) {
  lastScene = scene;
  const ms = paintScene(canvas, scene);
  window.tobymap.paints += 1;
  client.send({ type: "painted", paintMs: ms }).catch(() => {});
}

function handle(result, keyAt) {
  if (!result) return;  // a movement replaced by a later one (ANN-3)
  const r = result.response;
  let spoke = false;
  for (const a of r.announcements) {
    if (a.channel === "braille") speak(a.fallback, "polite");  // no Braille-only route in a browser
    else speak(a.text, a.priority);
    spoke = true;
  }
  for (const info of result.earcons || []) sounds.play(info);
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
  if (r.settings_changed || result.describing !== undefined) {
    toggles["help.describer"] = describing;
    if (result.save) toggles["sound.mute"] = JSON.parse(result.save).settings.values.mute;
    if (result.save) toggles["step.link"] = JSON.parse(result.save).state.link;
    if (menubar) menubar.setChecked(toggles);
  }
  if (result.save && result.save !== lastSave) {
    lastSave = result.save;
    try { localStorage.setItem(STORAGE_KEY, result.save); } catch (e) { /* private browsing: nothing is kept */ }
  }
  if (result.scene) paint(result.scene);
  if (result.panel) tree.fill(result.panel);
  if (result.map_label !== undefined) setMapLabel(result.map_label);
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
  return client.send({ type: "release", width, height }).then(handle).catch(showError);
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
  return dialog.open || settingsDialog.open || keyDialog.open;
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
  const name = (region === "map" && registry.keymap.map[key]) || registry.keymap.global[key];
  if (!name) return;
  e.preventDefault();
  if (registry.held.includes(name)) {
    if (e.repeat) return run(name, { held: true, repeat: true });   // the core paces repeats (DP129) and speaks on release (ANN-3)
    heldKey = name;
    return run(name, {}, keyAt);
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

function trapTab(e) {  // keep focus inside a dialog
  const open = [settingsDialog, dialog].find((d) => d.open);
  const items = [...open.querySelectorAll("button, input, select, textarea")].filter((el) => !el.disabled);
  const i = items.indexOf(document.activeElement);
  e.preventDefault();
  items[(i + (e.shiftKey ? -1 : 1) + items.length) % items.length].focus();
}

// The mouse: a click moves the location, the wheel changes the zoom, a drag turns the globe (NAV-9, NAV-13, VIS-4).
let press = null;
mapEl.addEventListener("pointerdown", (e) => {
  const r = canvas.getBoundingClientRect();
  mapEl.focus();
  press = { x: e.clientX, y: e.clientY, lastX: e.clientX, lastY: e.clientY, dragged: false, w: r.width, h: r.height, left: r.left, top: r.top };
  mapEl.setPointerCapture(e.pointerId);
  e.preventDefault();
});
mapEl.addEventListener("pointermove", (e) => {
  if (!press) return;
  if (!press.dragged && Math.abs(e.clientX - press.x) + Math.abs(e.clientY - press.y) < 5) return;
  press.dragged = true;
  const dx = e.clientX - press.lastX, dy = e.clientY - press.lastY;
  press.lastX = e.clientX;
  press.lastY = e.clientY;
  heldKey = "drag";
  run("map.drag", { dx, dy, width: press.w, height: press.h });
});
mapEl.addEventListener("pointerup", (e) => {
  if (!press) return;
  const p = press;
  press = null;
  if (p.dragged) release();
  else run("map.click", { x: e.clientX - p.left, y: e.clientY - p.top, width: p.w, height: p.h });
});
mapEl.addEventListener("wheel", (e) => {
  e.preventDefault();
  run("map.zoom_to", { direction: e.deltaY < 0 ? -1 : 1 });  // wheel up zooms in
}, { passive: false });

// Dialogs -----------------------------------------------------------------------

function openDialog(d) {
  returnFocus = document.activeElement && document.activeElement !== document.body ? document.activeElement : mapEl;
  if (d.kind === "settings") return openSettings(d);
  if (d.copy && navigator.clipboard) navigator.clipboard.writeText(d.copy).catch(() => {});
  dialogTitle.textContent = d.title;
  dialog.querySelectorAll("button[data-event]").forEach((b) => b.remove());
  if (d.kind === "sounds") {   // Help, The sounds: one button per sound, which plays it (DP134)
    for (const item of [...d.items].reverse()) {
      const b = button(item.label, () => run("sound.preview", { event: item.event }));
      b.dataset.event = item.event;
      dialogTitle.after(b);
    }
  }
  dialogText.hidden = d.kind === "sounds";
  dialogText.value = d.text;
  dialogText.setAttribute("aria-label", d.title);
  dialog.showModal();
  if (d.kind === "sounds") return dialog.querySelector("button[data-event]").focus();
  dialogText.focus();
  dialogText.setSelectionRange(0, 0);
}

dialogClose.addEventListener("click", () => dialog.close());
function afterClose() {
  // Menu commands return focus to the map, as on the desktop.
  (returnFocus && document.contains(returnFocus) && !menubar.contains(returnFocus) ? returnFocus : mapEl).focus();
}
dialog.addEventListener("close", afterClose);
settingsDialog.addEventListener("close", afterClose);

function button(label, onClick, id) {
  const b = document.createElement("button");
  b.type = "button";
  b.textContent = label;
  if (id) b.id = id;
  b.addEventListener("click", onClick);
  return b;
}

async function openSettings() {
  const schema = await client.send({ type: "schema" });
  settingsDialog.textContent = "";
  const title = document.createElement("h2");
  title.textContent = words.settings_title;
  settingsDialog.setAttribute("aria-label", words.settings_title);
  settingsDialog.appendChild(title);
  const controls = {};
  for (const tab of schema.tabs) {
    const set = document.createElement("fieldset");
    const legend = document.createElement("legend");
    legend.textContent = tab.label;
    set.appendChild(legend);
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
      } else {
        control = document.createElement("input");
        control.type = f.kind === "number" ? "number" : "text";
        if (f.kind === "number") { control.min = f.min; control.max = f.max; }
        control.value = schema.values[f.id];
      }
      control.dataset.field = f.id;
      control.dataset.kind = f.kind;
      controls[f.id] = control;
      label.appendChild(control);
      set.appendChild(label);
      set.appendChild(document.createElement("br"));
    }
    settingsDialog.appendChild(set);
  }
  const keys = document.createElement("fieldset");
  const kl = document.createElement("legend");
  kl.textContent = words.keys_tab;
  keys.appendChild(kl);
  for (const c of schema.keys) {
    const row = document.createElement("div");
    const text = document.createElement("span");
    const show = () => { text.textContent = `${c.label}: ${c.key || words.no_key} `; };
    show();
    row.appendChild(text);
    row.appendChild(button(words.key_change, async () => { const k = await askKey(c); if (k !== null) { c.key = k; show(); } }));
    row.lastChild.setAttribute("aria-label", `${words.key_change}: ${c.label}`);
    keys.appendChild(row);
  }
  settingsDialog.appendChild(keys);
  const bar = document.createElement("div");
  bar.appendChild(button(words.ok, async () => {
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
  settingsDialog.appendChild(bar);
  settingsDialog.showModal();
  settingsDialog.querySelector("select, input, button").focus();
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
    field.value = command.key;
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
  if (key) { keyDialog.dataset.key = key; field.value = key; $("key-message").textContent = ""; }
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
  $("map").hidden = false;
  $("side").hidden = false;
  client.onNotice = (text) => speak(text, "polite");   // the map download's progress
  const { width, height } = mapSize();
  let saved = "";
  try { saved = localStorage.getItem(STORAGE_KEY) || ""; } catch (e) { saved = ""; }
  const result = await client.send({ type: "start", width, height, saved });
  registry = result.registry;
  words = result.words;
  client.latestOnly = new Set(registry.latest_only);
  applyWords();
  tree = new Tree(treeEl, (id) => run("panel.select", { item: id }));
  menubar = new MenuBar($("menubar"), registry.menus, (name) => { mapEl.focus(); run(name, name === "help.keys" ? { region: "map" } : {}); }, moveRegion);
  $("loading").remove();
  $("app").removeAttribute("aria-busy");
  handle(result);
  sounds.preload(result.preload);
  mapEl.focus();
  window.tobymap.ready = true;

  let resizeTimer = null;
  new ResizeObserver(() => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      const size = mapSize();
      if (lastScene && size.width === lastScene.width && size.height === lastScene.height) return;
      client.send({ type: "scene", ...size }).then((r) => r && paint(r.scene)).catch(showError);
    }, 100);
  }).observe(mapEl);
}

boot().catch((error) => {
  showError(error);
  $("loading").textContent = `TobyMap could not start: ${window.tobymap.error}`;
});
