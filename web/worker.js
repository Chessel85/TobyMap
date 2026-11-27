// The web worker (AD-9): Pyodide, the core and the bridge live here, so the
// page never freezes and speech is never held up. It handles one message at
// a time and answers each with {id, ok, result} or {id, ok: false, error}.
//
// The packs: listed in packs/packs.json on the site. Each is downloaded whole
// on the first visit into the browser's private storage (OPFS), with progress
// sent to the page at most every 10 seconds, and read from there afterwards.
// Where private storage is not available, the pack is held in memory instead.
// Packs installed from the catalogue (P4-T6c), name.pack in private storage, are opened too.
//
// Installing a pack from the catalogue (P4-T6c, PCK-4): the message "install" with the catalogue entry. The
// core says whether it may be installed, including whether it fits in the space the browser has left. The
// pack is then downloaded whole into name.pack.part in private storage, written as it comes, and opened at once: records already stored are read from there, the rest
// by range requests, until the download is complete and checked, when it is moved into place as name.pack.
// The core hashes the bytes and gives every word; the worker only moves bytes.
// Cancel and resume (P4-T6f): "install_cancel" stops a download and keeps its .part file, with name.pack.part.json
// beside it saying which version it holds; the next install of the same entry carries on with a range request.
import { loadPyodide } from "./vendor/pyodide/pyodide.mjs";

const ARRAY_TYPES = { f32: Float32Array, i32: Int32Array, u8: Uint8Array };
const PROGRESS_EVERY_MS = 10_000;
let bridge = null;
let startupMs = 0;
let packs = [];
const downloads = new Map();   // the downloads in progress, by pack name: {abort, ending} (P4-T6f cancels)

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

// An answer from the core that no message of the page's asked for, such as a download that went wrong (P4-T6c).
function update(result) {
  const out = finish(result);
  self.postMessage({ update: out.result }, out.transfer);
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
  if (root) {   // packs installed from the catalogue (P4-T6c)
    try {
      for await (const [name, file] of root.entries()) {
        if (file.kind !== "file" || !name.endsWith(".pack") || opened.some((p) => p.name === name)) continue;
        try {
          opened.push({ name, handle: await file.createSyncAccessHandle() });
        } catch (e) {
          console.warn(`${name} could not be opened:`, e);
        }
      }
    } catch (e) {
      console.warn("Private storage could not be listed:", e);
    }
  }
  return opened;
}

// A handle that reads a pack's bytes over the internet with range requests (PCK-4), with the same two methods
// as OPFS's synchronous handle. A worker may make a synchronous request, which the core's reads need.
function rangeHandle(url, size) {
  return {
    getSize: () => size,
    read: (buffer, { at }) => {
      if (!buffer.length) return 0;
      const xhr = new XMLHttpRequest();
      xhr.open("GET", url, false);
      xhr.responseType = "arraybuffer";
      xhr.setRequestHeader("Range", `bytes=${at}-${at + buffer.length - 1}`);
      xhr.send();
      if (xhr.status !== 206 && xhr.status !== 200) throw new Error(`Range request failed: ${xhr.status}`);
      let bytes = new Uint8Array(xhr.response);
      if (xhr.status === 200) bytes = bytes.subarray(at, at + buffer.length);   // a server that ignored the range
      const n = Math.min(bytes.length, buffer.length);
      buffer.set(bytes.subarray(0, n));
      return n;
    },
  };
}

function closeQuietly(handle) {
  try { handle.close(); } catch (e) { /* already closed */ }
}

async function removeQuietly(root, name) {
  try { await root.removeEntry(name); } catch (e) { /* not there */ }
}

// The checked .part file becomes name.pack: moved where the browser can, otherwise copied.
async function moveIntoPlace(root, partName, fileName) {
  await removeQuietly(root, fileName);
  const part = await root.getFileHandle(partName);
  if (typeof part.move === "function") {
    await part.move(fileName);
  } else {
    const target = await (await root.getFileHandle(fileName, { create: true })).createSyncAccessHandle();
    try {
      const reader = (await part.getFile()).stream().getReader();
      let at = 0;
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        target.write(value, { at });
        at += value.length;
      }
      target.flush();
    } finally {
      target.close();
    }
    await root.removeEntry(partName);
  }
  return root.getFileHandle(fileName);
}

// The text of a small file in private storage, or null when it is not there.
async function readText(root, name) {
  try { return await (await (await root.getFileHandle(name)).getFile()).text(); } catch (e) { return null; }
}

async function writeText(root, name, text) {
  const handle = await (await root.getFileHandle(name, { create: true })).createSyncAccessHandle();
  try {
    const bytes = new TextEncoder().encode(text);
    handle.truncate(0);
    handle.write(bytes, { at: 0 });
    handle.flush();
  } finally {
    handle.close();
  }
}

// The .part files in private storage (P4-T6f), for the pack manager: {downloading: names, parts: {name: {record,
// size}}}. A part still being written is left out: its pack is downloading.
async function packStatus() {
  const parts = {};
  try {
    const root = await navigator.storage.getDirectory();
    for await (const [file, handle] of root.entries()) {
      if (handle.kind !== "file" || !file.endsWith(".pack.part")) continue;
      const name = file.slice(0, -".pack.part".length);
      if (downloads.has(name)) continue;
      try {
        parts[name] = { record: await readText(root, `${file}.json`), size: (await handle.getFile()).size };
      } catch (e) { /* being written */ }
    }
  } catch (e) { /* no private storage */ }
  let free = null;   // the space left in this browser for TobyMap, for the pack manager (P4-T6g)
  try {
    const estimate = await navigator.storage.estimate();
    if (estimate && estimate.quota) free = Math.max(0, estimate.quota - (estimate.usage || 0));
  } catch (e) { /* not known */ }
  return { downloading: [...downloads.keys()], parts, free };
}

// The bytes already held in the .part file, handed to the core a megabyte at a time, so the checksum covers the
// whole pack when the download carries on (P4-T6f).
function hashHeld(name, handle, upTo) {
  const buffer = new Uint8Array(1 << 20);
  let at = 0;
  while (at < upTo) {
    const n = handle.read(buffer.subarray(0, Math.min(buffer.length, upTo - at)), { at });
    if (!n) break;
    bridge.install_held(name, buffer.subarray(0, n));
    at += n;
  }
  return at;
}

async function installPack(raw, width, height, update) {
  let free = -1;
  try {
    const estimate = await navigator.storage.estimate();
    if (estimate && estimate.quota) free = estimate.quota - (estimate.usage || 0);
  } catch (e) { /* not known: the download is tried */ }
  const plan = bridge.install_begin(JSON.stringify(raw), free);
  if (plan.refused) return finish(bridge.install_said(plan.refused, width, height));
  let root = null, handle = null, start = 0;
  const abort = new AbortController();
  let response;
  try {
    root = await navigator.storage.getDirectory();
    if (update) {   // the pack in use is closed and its file deleted first (P4-T6d)
      bridge.install_replace(plan.name);
      await removeQuietly(root, plan.file);
    }
    // A .part file of this very version carries on from where it stopped (P4-T6f): the core decides from its record.
    const record = await readText(root, plan.record);
    handle = await (await root.getFileHandle(plan.part, { create: true })).createSyncAccessHandle();
    let asked = bridge.install_resume(plan.name, record, handle.getSize());
    if (asked) asked = hashHeld(plan.name, handle, asked);
    const headers = asked ? { Range: `bytes=${asked}-` } : {};
    response = await fetch(plan.url, { signal: abort.signal, headers, cache: "no-store" });
    const reply = bridge.install_reply(plan.name, asked, response.status);
    if (reply.start === null || reply.start === undefined || !response.body) throw new Error(`Could not download ${plan.url}`);
    start = reply.start;
    handle.truncate(start);
    if (!start) await writeText(root, plan.record, reply.record);
    if (reply.words) say(reply.words);
  } catch (e) {
    console.warn("The pack could not be downloaded:", e);
    if (handle) closeQuietly(handle);   // what came is kept, to carry on next time (P4-T6f)
    return finish(bridge.install_failed(plan.name, width, height));
  }
  let ended;
  const ending = new Promise((resolve) => { ended = resolve; });
  downloads.set(plan.name, { abort, ending });
  const result = bridge.install_open(plan.name, handle, rangeHandle(plan.url, plan.size), width, height);
  if (!result.opened) {   // not a pack this version can open: the core has said why
    abort.abort();
    closeQuietly(handle);
    await removeQuietly(root, plan.part);
    await removeQuietly(root, plan.record);
    bridge.install_failed(plan.name, width, height, true);
    downloads.delete(plan.name);
    ended();
    return finish(result);
  }
  receive(plan, root, handle, response, abort, start, { width, height }).finally(() => { downloads.delete(plan.name); ended(); });
  return finish(result);
}

// The rest of the download, while the worker answers the page as usual between the pieces of data that come.
// A download that went wrong takes its pack out of use: the core's answer goes to the page as an update. One that
// was cancelled or lost its connection keeps its .part file, to carry on next time (P4-T6f).
async function receive(plan, root, handle, response, abort, start, size) {
  try {
    const reader = response.body.getReader();
    let at = start;
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      handle.write(value, { at });
      at += value.length;
      const words = bridge.install_chunk(plan.name, value);
      if (words) say(words);
    }
    handle.flush();
  } catch (e) {
    try { handle.flush(); } catch (e2) { /* closed */ }
    closeQuietly(handle);
    update(bridge.install_failed(plan.name, size.width, size.height, abort.signal.aborted));   // cancelled: said by the core
    return;
  }
  const end = bridge.install_end(plan.name, size.width, size.height);
  closeQuietly(handle);
  if (!end.ok) {
    await removeQuietly(root, plan.part);
    await removeQuietly(root, plan.record);
    update(end.update);
    return;
  }
  try {
    await removeQuietly(root, plan.record);
    const file = await moveIntoPlace(root, plan.part, plan.file);
    bridge.install_stored(plan.name, await file.createSyncAccessHandle());
    update(bridge.install_said(end.text, size.width, size.height));   // an answer, so the pack manager's lines follow
  } catch (e) {
    console.warn("The pack could not be moved into place:", e);
    await removeQuietly(root, plan.part);
    update(bridge.install_failed(plan.name, size.width, size.height));
  }
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
  const { id, type, commands, width, height, paintMs, saved, at, key, region, event: earcon, keyMs, handedMs, slowMs,
          problem, samples, rate, factor, pitch, open, text, scope, index, system, bookmarks, entry, name, update, names } = event.data;
  try {
    await ready;
    let out;
    if (type === "start") out = finish(bridge.start(width, height, startupMs, packs, saved || "", at || "", slowMs || 0, system || "windows",
                                                         bookmarks || ""));
    else if (type === "run") out = finish(bridge.run(JSON.stringify(commands), width, height));
    else if (type === "press") out = finish(bridge.press(key, region, width, height));
    else if (type === "release") out = finish(bridge.release(width, height));
    else if (type === "crossed") out = finish(bridge.crossed(width, height));
    else if (type === "scene") out = finish(bridge.scene(width, height));
    else if (type === "scene_more") out = finish(bridge.scene_more(width, height));   // the drawing's next steps (P3-T24a)
    else if (type === "hold") out = { result: bridge.hold(), transfer: [] };
    else if (type === "panel") out = { result: bridge.panel_open(JSON.stringify(open || [])), transfer: [] };
    else if (type === "schema") out = { result: bridge.settings_schema(), transfer: [] };
    else if (type === "key_file") out = { result: bridge.key_file(), transfer: [] };
    else if (type === "key_text") out = { result: bridge.key_text(key), transfer: [] };
    else if (type === "earcon_failed") out = finish(bridge.earcon_failed(earcon, width, height));
    else if (type === "voice_problem") out = finish(bridge.voice_problem(problem, width, height));
    else if (type === "scan_item") out = finish(bridge.scan_item(index ?? -1, width, height));   // look around (P3-T11a)
    else if (type === "stretch") {   // a spatial voice label, faster at the same pitch (P2-T16g)
      const made = bridge.stretch(new Uint8Array(samples.buffer, samples.byteOffset, samples.byteLength), rate, factor, pitch);
      const buffer = made.bytes.slice().buffer;
      out = { result: new Float32Array(buffer), transfer: [buffer] };
    }
    else if (type === "painted") { bridge.frame_painted(paintMs); out = { result: null, transfer: [] }; }
    else if (type === "shell_times") { bridge.shell_times(keyMs, handedMs); out = { result: null, transfer: [] }; }
    else if (type === "search") out = { result: bridge.search(text || "", JSON.stringify(scope || {})), transfer: [] };
    else if (type === "install") out = await installPack(entry, width, height, update);   // a catalogue entry (P4-T6c)
    else if (type === "remove_files") {   // packs just removed by the pack manager (P4-T6d): the core has closed them
      const root = await navigator.storage.getDirectory();
      for (const file of names || []) await removeQuietly(root, file);
      out = { result: true, transfer: [] };
    }
    else if (type === "install_cancel") {   // a download stopped, its .part file kept to carry on (P4-T6f)
      const running = downloads.get(name);
      if (running) {
        running.abort.abort();
        await running.ending;
      }
      out = { result: !!running, transfer: [] };
    }
    else if (type === "pack_status") out = { result: await packStatus(), transfer: [] };   // for the pack manager (P4-T6f)
    else if (type === "packcheck") out = { result: bridge.pack_selfcheck(), transfer: [] };
    else if (type === "storecheck") out = { result: bridge.store_selfcheck(), transfer: [] };
    else throw new Error(`Unknown message ${type}`);
    self.postMessage({ id, ok: true, result: out.result }, out.transfer);
  } catch (error) {
    self.postMessage({ id, ok: false, error: String(error && error.message ? error.message : error) });
  }
};
