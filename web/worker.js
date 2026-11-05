// The web worker (AD-9): Pyodide, the core and the bridge live here, so the
// page never freezes and speech is never held up. It handles one message at
// a time and answers each with {id, ok, result} or {id, ok: false, error}.
//
// The packs: listed in packs/packs.json on the site. Each is downloaded whole
// on the first visit into the browser's private storage (OPFS), with progress
// sent to the page at most every 10 seconds, and read from there afterwards.
// Where private storage is not available, the pack is held in memory instead.
import { loadPyodide } from "./vendor/pyodide/pyodide.mjs";

const ARRAY_TYPES = { f32: Float32Array, i32: Int32Array, u8: Uint8Array };
const PROGRESS_EVERY_MS = 10_000;
let bridge = null;
let startupMs = 0;
let packs = [];

const ready = (async () => {
  const t0 = performance.now();
  const pyodide = await loadPyodide({ indexURL: new URL("./vendor/pyodide/", import.meta.url).href });
  await pyodide.loadPackage(["numpy", "pyyaml", "shapely"], { messageCallback: () => {} });
  const manifest = await (await fetch(new URL("./py/manifest.json", import.meta.url))).json();
  const texts = await Promise.all(manifest.files.map(async (f) => {
    const response = await fetch(new URL(`./py/${f}`, import.meta.url));
    if (!response.ok) throw new Error(`Could not load ${f}`);
    return [f, await response.text()];
  }));
  for (const [file, text] of texts) {
    const parts = `/app/${file}`.split("/");
    for (let i = 2; i < parts.length; i++) {
      const dir = parts.slice(0, i).join("/");
      if (!pyodide.FS.analyzePath(dir).exists) pyodide.FS.mkdir(dir);
    }
    pyodide.FS.writeFile(`/app/${file}`, text);
  }
  pyodide.runPython("import sys; sys.path.insert(0, '/app')");
  bridge = pyodide.pyimport("tobymap_bridge");
  packs = await openPacks();
  startupMs = performance.now() - t0;
})();

function say(text) {
  self.postMessage({ notice: text });
}

// A handle over bytes in memory, with the same two methods as OPFS's synchronous handle.
function memoryHandle(bytes) {
  return {
    getSize: () => bytes.length,
    read: (buffer, { at }) => {
      const n = Math.max(0, Math.min(buffer.length, bytes.length - at));
      buffer.set(bytes.subarray(at, at + n));
      return n;
    },
  };
}

async function listPacks() {
  try {
    const response = await fetch(new URL("./packs/packs.json", import.meta.url));
    if (!response.ok) return [];
    return (await response.json()).packs || [];
  } catch (e) {
    return [];
  }
}

async function download(entry, write) {
  const response = await fetch(new URL(`./packs/${entry.file}`, import.meta.url));
  if (!response.ok) throw new Error(`Could not download ${entry.file}`);
  const total = Number(response.headers.get("content-length")) || entry.bytes || 0;
  const reader = response.body.getReader();
  let loaded = 0, last = performance.now();
  say(bridge.words_text("packs.downloading_first"));
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    write(value, loaded);
    loaded += value.length;
    if (total && performance.now() - last >= PROGRESS_EVERY_MS) {
      last = performance.now();
      say(bridge.progress_text(Math.floor((100 * loaded) / total)));
    }
  }
  return loaded;
}

async function openPacks() {
  const entries = await listPacks();
  const opened = [];
  let root = null;
  try { root = await navigator.storage.getDirectory(); } catch (e) { root = null; }
  for (const entry of entries) {
    if (root) {
      try {
        const file = await root.getFileHandle(entry.file, { create: true });
        const handle = await file.createSyncAccessHandle();
        if (!entry.bytes || handle.getSize() !== entry.bytes) {
          handle.truncate(0);
          const size = await download(entry, (chunk, at) => handle.write(chunk, { at }));
          handle.flush();
          if (entry.bytes && size !== entry.bytes) throw new Error(`${entry.file} is the wrong size`);
          say(bridge.words_text("packs.download_done"));
        }
        opened.push({ name: entry.file, handle });
        continue;
      } catch (e) {
        console.warn("Private storage could not be used:", e);
      }
    }
    const chunks = [];
    await download(entry, (chunk) => chunks.push(chunk.slice()));
    const bytes = new Uint8Array(chunks.reduce((n, c) => n + c.length, 0));
    let at = 0;
    for (const c of chunks) { bytes.set(c, at); at += c.length; }
    opened.push({ name: entry.file, handle: memoryHandle(bytes) });
  }
  return opened;
}

// Bytes from the bridge become typed arrays, with fresh buffers that can be
// handed to the page without copying.
function unpackScene(scene, transfer) {
  for (const [key, value] of Object.entries(scene)) {
    if (value && value.type in ARRAY_TYPES && value.bytes instanceof Uint8Array) {
      const buffer = value.bytes.slice().buffer;
      scene[key] = new ARRAY_TYPES[value.type](buffer);
      transfer.push(buffer);
    }
  }
}

function finish(result) {
  const transfer = [];
  if (result && result.scene) unpackScene(result.scene, transfer);
  return { result, transfer };
}

self.onmessage = async (event) => {
  const { id, type, commands, width, height, paintMs, saved, at, key, region, event: earcon, keyMs, handedMs, slowMs } = event.data;
  try {
    await ready;
    let out;
    if (type === "start") out = finish(bridge.start(width, height, startupMs, packs, saved || "", at || "", slowMs || 0));
    else if (type === "run") out = finish(bridge.run(JSON.stringify(commands), width, height));
    else if (type === "press") out = finish(bridge.press(key, region, width, height));
    else if (type === "release") out = finish(bridge.release(width, height));
    else if (type === "scene") out = finish(bridge.scene(width, height));
    else if (type === "hold") out = { result: bridge.hold(), transfer: [] };
    else if (type === "schema") out = { result: bridge.settings_schema(), transfer: [] };
    else if (type === "key_text") out = { result: bridge.key_text(key), transfer: [] };
    else if (type === "earcon_failed") out = finish(bridge.earcon_failed(earcon, width, height));
    else if (type === "painted") { bridge.frame_painted(paintMs); out = { result: null, transfer: [] }; }
    else if (type === "shell_times") { bridge.shell_times(keyMs, handedMs); out = { result: null, transfer: [] }; }
    else if (type === "packcheck") out = { result: bridge.pack_selfcheck(), transfer: [] };
    else if (type === "storecheck") out = { result: bridge.store_selfcheck(), transfer: [] };
    else throw new Error(`Unknown message ${type}`);
    self.postMessage({ id, ok: true, result: out.result }, out.transfer);
  } catch (error) {
    self.postMessage({ id, ok: false, error: String(error && error.message ? error.message : error) });
  }
};
