// The one announcer of the web shell (ACC-1, architecture 4.4).
// ariaNotify where the browser has it, otherwise two alternating live regions
// of each politeness, so that the same text twice is still spoken.
// Every message is also kept in window.tobymap.announcements, for the
// browser tests and for diagnostics.

const regions = {
  polite: [document.getElementById("live-polite-a"), document.getElementById("live-polite-b")],
  assertive: [document.getElementById("live-assertive-a"), document.getElementById("live-assertive-b")],
};
const next = { polite: 0, assertive: 0 };

export const log = [];

// Adding ?announcer=live to the address forces the live regions, so the two
// ways can be compared with NVDA (spike S5).
const forceLive = new URLSearchParams(location.search).get("announcer") === "live";

export function useAriaNotify() {
  return !forceLive && typeof document.ariaNotify === "function";
}

export function speak(text, priority = "polite") {
  const kind = priority === "assertive" ? "assertive" : "polite";
  log.push({ text, priority: kind, at: performance.now() });
  if (useAriaNotify()) {
    document.ariaNotify(text, { priority: kind === "assertive" ? "high" : "normal" });
    return;
  }
  const [a, b] = regions[kind];
  const target = next[kind] === 0 ? a : b;
  const other = target === a ? b : a;
  next[kind] = 1 - next[kind];
  other.textContent = "";
  target.textContent = text;
}
