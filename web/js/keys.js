// Browser key events to the registry's shared key names
// (mapcore/commands/registry.py): modifiers Ctrl, Alt, Shift, then the key.
const NAMED = {
  ArrowUp: "Up", ArrowDown: "Down", ArrowLeft: "Left", ArrowRight: "Right",
  PageUp: "Page Up", PageDown: "Page Down", Home: "Home", End: "End", " ": "Space",
  Enter: "Enter", Backspace: "Backspace", Delete: "Delete", Escape: "Escape", Tab: "Tab", Insert: "Insert",
};
const MODIFIER_KEYS = new Set(["Control", "Shift", "Alt", "Meta", "AltGraph", "CapsLock"]);

export function keyName(event) {
  if (MODIFIER_KEYS.has(event.key)) return null;
  let base = NAMED[event.key];
  if (!base && /^F([1-9]|1[0-2])$/.test(event.key)) base = event.key;
  // Shift with a number key makes a symbol, which differs by keyboard layout ("%" or "("),
  // so the key itself is used: Shift+5 is "Shift+5" everywhere (DP109).
  const digit = /^Digit([0-9])$/.exec(event.code || "");
  if (!base && digit && event.shiftKey) base = digit[1];
  if (!base && event.key.length === 1) base = event.key.toUpperCase();
  if (!base) return null;
  const parts = [];
  if (event.ctrlKey) parts.push("Ctrl");
  if (event.altKey) parts.push("Alt");
  if (event.shiftKey && (base.length > 1 || base === " " || /[A-Z0-9]/.test(base))) parts.push("Shift");
  parts.push(base);
  return parts.join("+");
}
