// Spike S4 worker (P0-T7): Pyodide, the core's pack reader and the timings,
// in a worker, as the web version runs them (AD-9). The pack is copied into
// the browser's private storage and read from there with a synchronous
// access handle, as spike S3 recommends (DP102).
import { loadPyodide } from "../../../../web/vendor/pyodide/pyodide.mjs";

const MB = 1024 * 1024;
let handle = null;

function line(text) {
  self.postMessage({ type: "line", text });
}

function ms(t0) {
  return Math.round(performance.now() - t0);
}

// Called from Python: the bytes of the pack from offset, length long.
self.s4ReadAt = (offset, length) => {
  const out = new Uint8Array(length);
  const got = handle.read(out, { at: offset });
  if (got !== length) throw new Error(`Read ${got} bytes of ${length} at ${offset}`);
  return out;
};

async function copyPack(url, name, size, fresh) {
  const root = await navigator.storage.getDirectory();
  const fileHandle = await root.getFileHandle(name, { create: true });
  handle = await fileHandle.createSyncAccessHandle();
  if (!fresh && handle.getSize() === size) return { copied: false, ms: 0 };
  const t0 = performance.now();
  handle.truncate(0);
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Could not fetch the pack: ${response.status}`);
  const reader = response.body.getReader();
  let at = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    handle.write(value, { at });
    at += value.byteLength;
  }
  handle.flush();
  if (at !== size) throw new Error(`Copied ${at} bytes of the pack, expected ${size}`);
  return { copied: true, ms: ms(t0) };
}

function vendorBytes() {
  // What the browser fetched for Pyodide and its packages.
  let total = 0;
  const files = [];
  for (const e of performance.getEntriesByType("resource")) {
    if (!e.name.includes("/web/vendor/pyodide/")) continue;
    const bytes = e.encodedBodySize || e.decodedBodySize || e.transferSize || 0;
    total += bytes;
    files.push([e.name.split("/").pop(), bytes]);
  }
  return { total, files };
}

async function main(config, fresh) {
  const timings = {};
  let t0 = performance.now();
  const pyodide = await loadPyodide({ indexURL: new URL("../../../../web/vendor/pyodide/", import.meta.url).href });
  timings.pyodide_ms = ms(t0);
  line(`Pyodide started in ${timings.pyodide_ms} ms.`);

  t0 = performance.now();
  await pyodide.loadPackage(config.packages, { messageCallback: () => {} });
  timings.packages_ms = ms(t0);
  line(`Packages loaded (${config.packages.join(", ")}) in ${timings.packages_ms} ms.`);

  t0 = performance.now();
  for (const f of config.coreFiles) {
    const response = await fetch(`/${f.from}`);
    if (!response.ok) throw new Error(`Could not load ${f.from}`);
    const text = await response.text();
    const parts = `/app/${f.to}`.split("/");
    for (let i = 2; i < parts.length; i++) {
      const dir = parts.slice(0, i).join("/");
      if (!pyodide.FS.analyzePath(dir).exists) pyodide.FS.mkdir(dir);
    }
    pyodide.FS.writeFile(`/app/${f.to}`, text);
  }
  pyodide.runPython("import sys; sys.path.insert(0, '/app')");
  pyodide.runPython("import numpy, shapely, s4_bench");
  timings.core_ms = ms(t0);
  line(`The core's pack reader and the timing code loaded and imported in ${timings.core_ms} ms.`);
  timings.startup_ms = timings.pyodide_ms + timings.packages_ms + timings.core_ms;
  line(`Start-up in all: ${timings.startup_ms} ms.`);

  const download = vendorBytes();
  line(`Pyodide and its packages fetched: ${(download.total / MB).toFixed(1)} MB.`);
  for (const [name, bytes] of download.files) line(`  ${name}: ${(bytes / MB).toFixed(2)} MB`);

  const copy = await copyPack(config.packUrl, config.packName, config.packSize, fresh);
  timings.copy_ms = copy.ms;
  line(copy.copied
    ? `The pack (${(config.packSize / MB).toFixed(1)} MB) copied into private storage in ${copy.ms} ms.`
    : "The pack was already in private storage, so it was not copied again.");

  pyodide.globals.set("places_json", JSON.stringify(config.places));
  t0 = performance.now();
  pyodide.runPython(`
import json, js
from mapcore.packs.archive import Pack

class PrivateStorage:
    """The pack's bytes from the browser's private storage."""
    size = ${config.packSize}
    def read(self, offset, length):
        return bytes(js.s4ReadAt(offset, length).to_py())

pack = Pack(PrivateStorage())
`);
  timings.open_ms = ms(t0);
  line(`The pack opened (its directory, manifest and areas read) in ${timings.open_ms} ms.`);

  t0 = performance.now();
  const resultJson = pyodide.runPython(`
result = s4_bench.run(pack, json.loads(places_json), s4_bench.WALKS)
json.dumps(result)
`);
  timings.bench_ms = ms(t0);
  const result = JSON.parse(resultJson);
  const lines = pyodide.runPython(`"\\n".join(s4_bench.report_lines(result, "In this browser"))`);
  for (const l of lines.split("\n")) line(l);

  let heapMB = null;
  try {
    heapMB = Math.round(pyodide._module.HEAPU8.byteLength / MB);
    line(`Python's memory in the browser (the WebAssembly heap) at the end: ${heapMB} MB.`);
  } catch (e) {
    line("Python's memory in the browser could not be read.");
  }
  handle.close();
  handle = null;
  return { timings, download, heap_mb: heapMB, result };
}

self.onmessage = async (event) => {
  const { config, fresh } = event.data;
  try {
    const out = await main(config, fresh);
    self.postMessage({ type: "done", result: out });
  } catch (error) {
    line("Error: " + (error && error.message ? error.message : error));
    if (handle) handle.close();
    self.postMessage({ type: "done", result: { error: String(error && error.message ? error.message : error) } });
  }
};
