// Spike S3 page (P0-T6). The tests themselves run in worker.js, as the web
// version's pack reader will: in a worker, with synchronous range requests.
"use strict";

const resultsBox = document.getElementById("results");
const statusLine = document.getElementById("status");
let sources = [];

function addLine(text) {
  resultsBox.value += text + "\n";
}

function say(text) {
  statusLine.textContent = "";
  setTimeout(() => { statusLine.textContent = text; }, 50);
}

function browserName() {
  const ua = navigator.userAgent;
  if (ua.includes("Edg/")) return "Edge " + (ua.match(/Edg\/([\d.]+)/) || [])[1];
  if (ua.includes("Firefox/")) return "Firefox " + (ua.match(/Firefox\/([\d.]+)/) || [])[1];
  if (ua.includes("Chrome/")) return "Chrome " + (ua.match(/Chrome\/([\d.]+)/) || [])[1];
  return ua;
}

function runInWorker(message, onLine) {
  return new Promise((resolve) => {
    const worker = new Worker("worker.js");
    worker.onmessage = (e) => {
      if (e.data.type === "line") {
        onLine(e.data.text);
      } else if (e.data.type === "done") {
        worker.terminate();
        resolve(e.data.result);
      }
    };
    worker.onerror = (e) => {
      onLine("Error in the worker: " + e.message);
      worker.terminate();
      resolve({ error: e.message });
    };
    worker.postMessage(message);
  });
}

async function readTest(chosen) {
  addLine("Reading test in " + browserName() + ", " + new Date().toISOString());
  const results = [];
  for (const source of chosen) {
    say("Reading from " + source.name + ".");
    results.push(await runInWorker({ kind: "read", source }, addLine));
  }
  const working = results.filter((r) => r.works).length;
  const summary = "Reading test finished: " + working + " of " + results.length + " places work.";
  addLine(summary);
  addLine("");
  say(summary);
  return results;
}

async function storageTest(megabytes) {
  addLine("Storage test in " + browserName() + ", " + new Date().toISOString());
  say("Storage test started. It may take a minute.");
  const result = await runInWorker({ kind: "storage", megabytes }, addLine);
  if (navigator.storage && navigator.storage.persisted) {
    result.persisted = await navigator.storage.persisted();
    addLine("Storage kept for this site: " + (result.persisted ? "yes" : "no, the browser may clear it when the disk is full"));
  }
  const summary = result.error
    ? "Storage test finished with an error."
    : "Storage test finished: " + result.writtenMegabytes + " megabytes stored.";
  addLine(summary);
  addLine("");
  say(summary);
  return result;
}

function chosenSources() {
  const chosen = sources.filter((s, i) => document.getElementById("source-" + i).checked);
  const other = document.getElementById("other-url").value.trim();
  if (other) chosen.push({ name: "Another address", url: other, pattern: false });
  return chosen;
}

async function loadSources() {
  const box = document.getElementById("sources");
  try {
    const response = await fetch("sources.json", { cache: "no-store" });
    sources = await response.json();
  } catch (e) {
    sources = [];
  }
  box.innerHTML = "";
  if (!sources.length) {
    box.textContent = "No list of places was found. Type an address below.";
    return;
  }
  sources.forEach((source, i) => {
    const div = document.createElement("div");
    const input = document.createElement("input");
    input.type = "checkbox";
    input.id = "source-" + i;
    input.checked = true;
    const label = document.createElement("label");
    label.htmlFor = input.id;
    label.textContent = source.name;
    div.append(input, " ", label);
    box.append(div);
  });
}

document.getElementById("read-test").addEventListener("click", () => readTest(chosenSources()));
document.getElementById("storage-test").addEventListener("click", () => {
  storageTest(Number(document.getElementById("megabytes").value) || 2048);
});
document.getElementById("persist").addEventListener("click", async () => {
  if (!navigator.storage || !navigator.storage.persist) {
    addLine("This browser cannot be asked to keep storage.");
    return;
  }
  const kept = await navigator.storage.persist();
  const text = kept ? "The browser will keep this site's storage." : "The browser said no to keeping this site's storage.";
  addLine(text);
  say(text);
});
document.getElementById("save").addEventListener("click", () => {
  const blob = new Blob([resultsBox.value], { type: "text/plain" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "s3-results-" + new Date().toISOString().slice(0, 16).replace(":", "") + ".txt";
  link.click();
});
document.getElementById("clear").addEventListener("click", () => {
  resultsBox.value = "";
  say("Results cleared.");
});

// For the automatic runner (run.py) and the browser tests.
window.s3 = {
  browserName,
  ready: loadSources(),
  readTest,
  storageTest,
  sources: () => sources,
};
