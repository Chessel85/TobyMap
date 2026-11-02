// Spike S3 worker (P0-T6): reads ranges of a file with synchronous range
// requests, as the web version's pack reader will (architecture 4.4), and
// tests the browser's private file storage (OPFS).
"use strict";

const MiB = 1024 * 1024;

function line(text) {
  postMessage({ type: "line", text });
}

// The test file: 4-byte little-endian whole numbers, the one at byte 4k is k.
function patternBytes(start, length) {
  const out = new Uint8Array(length);
  for (let i = 0; i < length; i++) {
    const offset = start + i;
    const word = Math.floor(offset / 4);
    out[i] = (word >>> (8 * (offset % 4))) & 0xff;
  }
  return out;
}

function sameBytes(a, b) {
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) return false;
  return true;
}

function median(values) {
  const sorted = [...values].sort((a, b) => a - b);
  return sorted.length ? sorted[Math.floor(sorted.length / 2)] : 0;
}

function round(value, places = 1) {
  const f = 10 ** places;
  return Math.round(value * f) / f;
}

// One synchronous range request. Throws if the browser blocks it.
function getRange(url, first, last) {
  const xhr = new XMLHttpRequest();
  xhr.open("GET", url, false);
  xhr.responseType = "arraybuffer";
  xhr.setRequestHeader("Range", "bytes=" + first + "-" + last);
  const t0 = performance.now();
  xhr.send();
  const ms = performance.now() - t0;
  return {
    status: xhr.status,
    bytes: new Uint8Array(xhr.response || new ArrayBuffer(0)),
    contentRange: xhr.getResponseHeader("Content-Range"),
    finalUrl: xhr.responseURL,
    ms,
  };
}

// A seeded random number generator, so every run reads the same places.
function seeded(seed) {
  let s = seed >>> 0;
  return () => {
    s = (s * 1664525 + 1013904223) >>> 0;
    return s / 4294967296;
  };
}

async function readTest(source) {
  const result = { name: source.name, url: source.url, works: false };
  line("Place: " + source.name);
  line("  Address: " + source.url);

  // 1. The first 16 bytes. This shows whether the browser allows it at all.
  // Chrome and Edge throw when they block a request; Firefox answers with status 0.
  let first;
  try {
    first = getRange(source.url, 0, 15);
    if (first.status === 0) throw new Error("status 0");
  } catch (err) {
    result.blocked = true;
    result.error = String(err.name === "Error" ? err.message : (err.name || err));
    line("  Blocked: the browser did not let the page read this file (" + result.error + ").");
    try {
      await fetch(source.url, { headers: { Range: "bytes=0-15" } });
      line("  An ordinary fetch was allowed, though.");
      result.fetchAllowed = true;
    } catch (e) {
      line("  An ordinary fetch was blocked too.");
      result.fetchAllowed = false;
    }
    return result;
  }
  result.status = first.status;
  result.firstMs = round(first.ms);
  result.finalHost = first.finalUrl ? new URL(first.finalUrl).host : "";
  if (first.status !== 206) {
    line("  Not a partial answer: status " + first.status + ", " + first.bytes.length + " bytes.");
    result.error = "status " + first.status;
    return result;
  }
  if (first.bytes.length !== 16) {
    line("  Wrong length: asked for 16 bytes, got " + first.bytes.length + ".");
    result.error = "wrong length";
    return result;
  }
  let size = source.size || 0;
  if (first.contentRange) {
    const m = first.contentRange.match(/\/(\d+)$/);
    if (m) size = Number(m[1]);
    result.sizeVisible = true;
  } else {
    result.sizeVisible = false;
    line("  The file's size was not visible to the page.");
  }
  result.size = size;
  line("  Allowed. The first 16 bytes took " + result.firstMs + " ms. Served from " + result.finalHost + ".");

  // 2. Small reads from all over the file, as when stepping round the map.
  const random = seeded(42);
  const pieces = [];
  const times = [];
  const pieceSize = 4096;
  let wrong = 0;
  const top = Math.max(1, (size || 1024 * 1024) - pieceSize);
  for (let i = 0; i < 20; i++) {
    const start = Math.floor(random() * top);
    const r = getRange(source.url, start, start + pieceSize - 1);
    times.push(r.ms);
    const ok = r.status === 206 && r.bytes.length === pieceSize &&
      (!source.pattern || sameBytes(r.bytes, patternBytes(start, pieceSize)));
    if (!ok) wrong++;
    pieces.push({ start, bytes: r.bytes });
  }
  result.smallMedianMs = round(median(times));
  result.smallSlowestMs = round(Math.max(...times));
  result.smallWrong = wrong;
  line("  20 reads of 4 KB from all over the file: middle time " + result.smallMedianMs +
       " ms, slowest " + result.smallSlowestMs + " ms. " +
       (wrong ? wrong + " came back wrong." : (source.pattern ? "All checked correct." : "All the right length.")));

  // 3. The last 16 bytes.
  if (size) {
    const r = getRange(source.url, size - 16, size - 1);
    result.lastOk = r.status === 206 && r.bytes.length === 16 &&
      (!source.pattern || sameBytes(r.bytes, patternBytes(size - 16, 16)));
    line("  The last 16 bytes: " + (result.lastOk ? "correct." : "wrong."));
  }

  // 4. One larger read of 4 MB, for the download speed.
  const bigSize = Math.min(4 * MiB, size || 4 * MiB);
  const big = getRange(source.url, 0, bigSize - 1);
  result.bigOk = big.status === 206 && big.bytes.length === bigSize &&
    (!source.pattern || sameBytes(big.bytes, patternBytes(0, bigSize)));
  result.megabytesPerSecond = round((bigSize / MiB) / (big.ms / 1000));
  line("  One read of " + round(bigSize / MiB) + " MB took " + round(big.ms) + " ms, about " +
       result.megabytesPerSecond + " megabytes a second. " + (result.bigOk ? "Correct." : "Wrong."));

  // 5. Keep what the small reads returned in private storage, and read it back,
  //    as the pack cache will do so that places already visited work offline.
  try {
    result.cacheOk = await cacheRoundTrip(pieces);
    line("  Keeping what the 20 reads returned in private storage, and reading it back: " +
         (result.cacheOk ? "correct." : "wrong."));
  } catch (err) {
    result.cacheOk = false;
    line("  Keeping the reads in private storage failed: " + err);
  }

  result.works = !wrong && result.bigOk && (result.lastOk !== false);
  line("  Result: " + (result.works ? "works." : "does not work."));
  return result;
}

async function cacheRoundTrip(pieces) {
  const root = await navigator.storage.getDirectory();
  const handle = await root.getFileHandle("s3-cache-test.bin", { create: true });
  const file = await handle.createSyncAccessHandle();
  try {
    file.truncate(0);
    let at = 0;
    const index = [];
    for (const p of pieces) {
      file.write(p.bytes, { at });
      index.push([at, p.bytes.length]);
      at += p.bytes.length;
    }
    file.flush();
    for (let i = 0; i < pieces.length; i++) {
      const back = new Uint8Array(index[i][1]);
      file.read(back, { at: index[i][0] });
      if (!sameBytes(back, pieces[i].bytes)) return false;
    }
    return true;
  } finally {
    file.close();
    await root.removeEntry("s3-cache-test.bin");
  }
}

async function estimate() {
  if (!navigator.storage || !navigator.storage.estimate) return null;
  const e = await navigator.storage.estimate();
  return { usageMB: round(e.usage / MiB), quotaMB: round(e.quota / MiB) };
}

async function storageTest(megabytes) {
  const result = { targetMegabytes: megabytes, writtenMegabytes: 0 };
  const before = await estimate();
  result.before = before;
  if (before) {
    line("  The browser says this site may store up to " + before.quotaMB + " MB, about " +
         round(before.quotaMB / 1024) + " GB. It is using " + before.usageMB + " MB.");
  }
  const root = await navigator.storage.getDirectory();
  const name = "s3-storage-test.bin";
  const handle = await root.getFileHandle(name, { create: true });
  const file = await handle.createSyncAccessHandle();
  const chunkMB = 16;
  const chunk = new Uint8Array(chunkMB * MiB);
  for (let i = 0; i < chunk.length; i += 4096) chunk[i] = (i / 4096) & 0xff;
  const t0 = performance.now();
  try {
    file.truncate(0);
    for (let done = 0; done < megabytes; done += chunkMB) {
      chunk[0] = (done / chunkMB) & 0xff;
      const written = file.write(chunk, { at: done * MiB });
      if (written !== chunk.length) {
        result.stopped = "short write";
        line("  The browser stopped the writing: it would take only " + written + " more bytes.");
        break;
      }
      result.writtenMegabytes = done + chunkMB;
      if (result.writtenMegabytes % 512 === 0) line("  Stored " + result.writtenMegabytes + " MB so far.");
    }
    file.flush();
  } catch (err) {
    result.stopped = String(err.name || err);
    line("  The browser stopped the writing: " + result.stopped + ".");
  }
  const seconds = (performance.now() - t0) / 1000;
  result.writeMegabytesPerSecond = round(result.writtenMegabytes / seconds);
  line("  Stored " + result.writtenMegabytes + " MB in " + round(seconds) + " seconds, about " +
       result.writeMegabytesPerSecond + " megabytes a second.");

  // Read back the first and last chunks and check their marks.
  try {
    const back = new Uint8Array(chunkMB * MiB);
    let ok = true;
    for (const n of [0, Math.max(0, result.writtenMegabytes / chunkMB - 1)]) {
      file.read(back, { at: n * chunkMB * MiB });
      if (back[0] !== (n & 0xff) || back[4096] !== 1) ok = false;
    }
    result.readBackOk = ok;
    line("  Reading it back: " + (ok ? "correct." : "wrong."));
  } catch (err) {
    result.readBackOk = false;
    line("  Reading it back failed: " + err);
  }
  result.during = await estimate();
  file.close();
  await root.removeEntry(name);
  result.after = await estimate();
  line("  The test file is deleted. The site is now using " + (result.after ? result.after.usageMB : "?") + " MB.");
  return result;
}

self.onmessage = async (e) => {
  let result;
  try {
    if (e.data.kind === "read") result = await readTest(e.data.source);
    else result = await storageTest(e.data.megabytes);
  } catch (err) {
    line("  Error: " + err);
    result = { error: String(err) };
  }
  postMessage({ type: "done", result });
};
