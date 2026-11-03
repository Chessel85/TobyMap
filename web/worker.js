// The web worker (AD-9): Pyodide, the core and the bridge live here, so the
// page never freezes and speech is never held up. It handles one message at
// a time and answers each with {id, ok, result} or {id, ok: false, error}.
import { loadPyodide } from "./vendor/pyodide/pyodide.mjs";

const ARRAY_TYPES = { f32: Float32Array, i32: Int32Array, u8: Uint8Array };
let bridge = null;
let startupMs = 0;

const ready = (async () => {
  const t0 = performance.now();
  const pyodide = await loadPyodide({ indexURL: new URL("./vendor/pyodide/", import.meta.url).href });
  await pyodide.loadPackage(["numpy", "pyyaml"], { messageCallback: () => {} });
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
  startupMs = performance.now() - t0;
})();

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
  const { id, type, commands, width, height, paintMs } = event.data;
  try {
    await ready;
    let out;
    if (type === "start") out = finish(bridge.start(width, height, startupMs));
    else if (type === "run") out = finish(bridge.run(JSON.stringify(commands), width, height));
    else if (type === "scene") out = finish(bridge.scene(width, height));
    else if (type === "painted") { bridge.frame_painted(paintMs); out = { result: null, transfer: [] }; }
    else if (type === "packcheck") out = { result: bridge.pack_selfcheck(), transfer: [] };
    else throw new Error(`Unknown message ${type}`);
    self.postMessage({ id, ok: true, result: out.result }, out.transfer);
  } catch (error) {
    self.postMessage({ id, ok: false, error: String(error && error.message ? error.message : error) });
  }
};
