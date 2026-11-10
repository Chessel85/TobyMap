// Your own earcon files in the web version (P2-T8b; SON-8, DP123). A web page cannot read a
// path on your computer, so a file you choose in the Earcons tab of Settings is kept in the
// browser's own storage (IndexedDB), by earcon, and played from there from then on. The
// core keeps only its name, as the setting earcon_<event>, so it knows one is in use.

const DB_NAME = "tobymap-sounds";
const STORE = "earcons";

let opening = null;
function db() {
  if (!opening) {
    opening = new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, 1);
      request.onupgradeneeded = () => request.result.createObjectStore(STORE);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
    opening.catch(() => { opening = null; });
  }
  return opening;
}

function done(request) {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function store(mode) {
  return (await db()).transaction(STORE, mode).objectStore(STORE);
}

// Keeps a file's bytes for an earcon: { name, bytes }.
export async function put(event, name, bytes) {
  await done((await store("readwrite")).put({ name, bytes }, event));
}

// The kept file for an earcon, or undefined.
export async function get(event) {
  return done((await store("readonly")).get(event));
}

export async function remove(event) {
  await done((await store("readwrite")).delete(event));
}

// Every kept file, for Reset all settings (P2-T18h).
export async function clear() {
  await done((await store("readwrite")).clear());
}

// Whether bytes are a WAV file: "RIFF", a length, then "WAVE".
export function isWav(bytes) {
  const b = new Uint8Array(bytes, 0, Math.min(12, bytes.byteLength));
  const text = (from, to) => String.fromCharCode(...b.slice(from, to));
  return b.length === 12 && text(0, 4) === "RIFF" && text(8, 12) === "WAVE";
}
