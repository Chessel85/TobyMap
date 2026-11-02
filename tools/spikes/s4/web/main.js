// Spike S4 page (P0-T7). Everything is timed in worker.js, which runs Pyodide
// as the web version does. The page only starts it and shows the lines.
"use strict";

const resultsBox = document.getElementById("results");
const statusLine = document.getElementById("status");

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

async function run(fresh) {
  const config = await (await fetch("config.json")).json();
  addLine(`Spike S4 in ${browserName()}, ${new Date().toISOString()}.`);
  say("The test has started.");
  return new Promise((resolve) => {
    const worker = new Worker("worker.js", { type: "module" });
    worker.onmessage = (e) => {
      if (e.data.type === "line") {
        addLine(e.data.text);
      } else if (e.data.type === "done") {
        worker.terminate();
        say(e.data.result.error ? "The test stopped with an error." : "The test has finished.");
        resolve({ browser: browserName(), ...e.data.result });
      }
    };
    worker.onerror = (e) => {
      addLine("Error in the worker: " + e.message);
      worker.terminate();
      say("The test stopped with an error.");
      resolve({ browser: browserName(), error: e.message });
    };
    worker.postMessage({ config, fresh });
  });
}

document.getElementById("run").addEventListener("click", () => run(document.getElementById("fresh").checked));
document.getElementById("save").addEventListener("click", () => {
  const blob = new Blob([resultsBox.value], { type: "text/plain" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "spike-s4-results.txt";
  a.click();
});

// For the runner (run.py), which drives the page without a window.
window.s4 = { run, browserName };
