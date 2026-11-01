// The web shell (architecture 5.6): the four regions around the core in the
// worker. It only translates keys and clicks into commands, and the core's
// responses into speech, painting and focus. Every key comes from the command
// registry, and every word from the core.
import { speak, log } from "./announcer.js";
import { keyName } from "./keys.js";
import { MenuBar } from "./menu.js";
import { paintScene } from "./painter.js";
import { Tree } from "./tree.js";
import { WorkerClient } from "./worker_client.js";

const $ = (id) => document.getElementById(id);
const mapEl = $("map"), canvas = $("canvas"), treeEl = $("tree"), details = $("details");
const dialog = $("dialog"), dialogTitle = $("dialog-title"), dialogText = $("dialog-text"), dialogClose = $("dialog-close");
const REGIONS = ["map", "panel", "details", "menu"];

const client = new WorkerClient(new URL("../worker.js", import.meta.url));
let registry = null, words = null, menubar = null, tree = null;
let lastScene = null, returnFocus = null;

// window.tobymap is for the browser tests and diagnostics only.
window.tobymap = { announcements: log, ready: false, error: null, paints: 0 };

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

function handle(result) {
  if (!result) return;  // a movement replaced by a later one (ANN-3)
  const r = result.response;
  for (const a of r.announcements) {
    if (a.channel === "braille") speak(a.fallback, "polite");  // no Braille-only route in a browser
    else speak(a.text, a.priority);
  }
  if (result.scene) paint(result.scene);
  if (result.panel) tree.fill(result.panel);
  if (result.map_label !== undefined) setMapLabel(result.map_label);
  if (result.details !== undefined) {
    details.value = result.details;
    details.setSelectionRange(0, 0);  // so Tab or D always lands on the first line
    details.scrollTop = 0;
  }
  if (r.focus) {
    if (r.focus.region === "panel") tree.focusGroup(r.focus.group);
    else if (r.focus.region === "details") {
      details.setSelectionRange(0, 0);  // before focus, so NVDA reads the first line on arrival
      details.scrollTop = 0;
      details.focus();
    }
  }
  if (r.dialog) openDialog(r.dialog);
}

// The map's name is the place under the centre, so the screen reader says
// just the place when Tab arrives (PO feedback on spike S5). It changes only
// while the map does not have focus, so turning never makes NVDA read the
// name again as well as the announcement.
let mapLabel = null;
function setMapLabel(label) {
  mapLabel = label;
  if (document.activeElement !== mapEl) mapEl.setAttribute("aria-label", label);
}
mapEl.addEventListener("blur", () => { if (mapLabel) mapEl.setAttribute("aria-label", mapLabel); });

function run(name, args = {}) {
  const { width, height } = mapSize();
  return client.send({ type: "run", commands: [[name, args]], width, height }).then(handle).catch(showError);
}

function showError(error) {
  window.tobymap.error = String(error.message || error);
  console.error(error);
}

// Focus between the four regions, wrapping round (UX section 2).
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
  else if (region === "menu") menubar.focusFirst();
}

function moveRegion(step) {
  const here = regionOf(document.activeElement) || "map";
  focusRegion(REGIONS[(REGIONS.indexOf(here) + step + REGIONS.length) % REGIONS.length]);
}

document.addEventListener("keydown", (e) => {
  if (!registry) return;
  if (dialog.open) {
    if (e.key === "Tab") {  // keep focus inside the dialog
      e.preventDefault();
      (document.activeElement === dialogClose ? dialogText : dialogClose).focus();
    }
    return;
  }
  if (e.key === "Tab" && !e.ctrlKey && !e.altKey) {
    e.preventDefault();
    moveRegion(e.shiftKey ? -1 : 1);
    return;
  }
  const key = keyName(e);
  if (!key) return;
  const region = regionOf(document.activeElement);
  const name = (region === "map" && registry.keymap.map[key]) || registry.keymap.global[key];
  if (name) {
    e.preventDefault();
    run(name);
  }
});

mapEl.addEventListener("mousedown", (e) => {
  const r = canvas.getBoundingClientRect();
  mapEl.focus();
  run("map.click", { x: e.clientX - r.left, y: e.clientY - r.top, width: r.width, height: r.height });
  e.preventDefault();
});

function openDialog({ title, text }) {
  returnFocus = document.activeElement && document.activeElement !== document.body ? document.activeElement : mapEl;
  dialogTitle.textContent = title;
  dialogText.value = text;
  dialogText.setAttribute("aria-label", title);
  dialog.showModal();
  dialogText.focus();
  dialogText.setSelectionRange(0, 0);
}

dialogClose.addEventListener("click", () => dialog.close());
dialog.addEventListener("close", () => {
  // Menu commands return focus to the map, as on the desktop.
  (returnFocus && document.contains(returnFocus) && !menubar.contains(returnFocus) ? returnFocus : mapEl).focus();
});

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
  const { width, height } = mapSize();
  const result = await client.send({ type: "start", width, height });
  registry = result.registry;
  words = result.words;
  client.latestOnly = new Set(registry.latest_only);
  applyWords();
  tree = new Tree(treeEl, (id) => run("panel.select", { item: id }));
  menubar = new MenuBar($("menubar"), registry.menus, (name) => { mapEl.focus(); run(name); }, moveRegion);
  $("loading").remove();
  $("app").removeAttribute("aria-busy");
  handle(result);
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
