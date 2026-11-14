// The languages of names (P3-T12b, ACC-9). The core sends, with each answer, the names in another
// language it has put into words, such as {"Deutschland": "de"}. The page keeps them, and wherever it
// shows words that hold one of them, that name is wrapped in a span with its lang attribute, so a
// screen reader set to switch voices can read it in its own language. The rest keeps the page's English.
//
// Only the words the page shows as elements can be marked: the Information panel, the lists in the
// dialogs, the world tree and the live regions. Details is a text box, which has one language for all of it,
// and ariaNotify takes plain text, so neither is marked.

const known = new Map();   // name -> language code
const LIMIT = 5000;        // names kept, the oldest forgotten first
let pattern = null;        // one regular expression for every name, longest first, made again when names change

export function learn(langs) {
  if (!langs) return;
  let changed = false;
  for (const [name, lang] of Object.entries(langs)) {
    if (!name || known.get(name) === lang) continue;
    known.delete(name);
    known.set(name, lang);
    changed = true;
  }
  while (known.size > LIMIT) known.delete(known.keys().next().value);
  if (changed) pattern = null;
}

function escape(text) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function names() {
  if (pattern === null && known.size) {
    const all = [...known.keys()].sort((a, b) => b.length - a.length).map(escape);
    // A name counts only as whole words: not "Paris" inside "Parisian".
    pattern = new RegExp(`(?<![\\p{L}\\p{N}])(?:${all.join("|")})(?![\\p{L}\\p{N}])`, "gu");
  }
  return pattern;
}

// Put text into an element, with each known name in a span with its lang attribute. Returns the element.
export function setText(el, text) {
  text = text ?? "";
  const re = known.size ? names() : null;
  if (!re) {
    if (el.textContent !== text || el.children.length) el.textContent = text;
    return el;
  }
  const parts = [];
  let at = 0;
  re.lastIndex = 0;
  for (let m = re.exec(text); m; m = re.exec(text)) {
    if (m.index > at) parts.push(document.createTextNode(text.slice(at, m.index)));
    const span = document.createElement("span");
    span.lang = known.get(m[0]);
    span.textContent = m[0];
    parts.push(span);
    at = m.index + m[0].length;
  }
  if (!parts.length) {
    if (el.textContent !== text || el.children.length) el.textContent = text;
    return el;
  }
  if (at < text.length) parts.push(document.createTextNode(text.slice(at)));
  el.replaceChildren(...parts);
  return el;
}

// An option in a list holds plain text only, so it is marked whole, and only when its words are one name.
export function markWhole(el, text) {
  const lang = known.get(text);
  if (lang) el.lang = lang;
  else el.removeAttribute("lang");
  return el;
}

// For the browser tests: the language of a name, if the page knows it.
export function languageOf(name) {
  return known.get(name) || null;
}
