// The Information panel tree (UX section 6), following the ARIA tree pattern.
// Each item takes real keyboard focus with a roving tabindex; there is no
// aria-activedescendant, which NVDA stayed silent with in RecallScore.
//
// Keys: Up and Down move through visible items, Right opens a group or goes to
// its first item, Left closes a group or goes to its parent, Home and End go
// to the first and last item. Typing a letter jumps to the next item starting
// with it. Enter is the registry's Go there (P2-T17k), as on the desktop, so it does not
// open or close a group.

export class Tree {
  constructor(element, onSelect) {
    this.el = element;
    this.onSelect = onSelect;
    this.current = null;
    this.expanded = new Set();
    this.el.addEventListener("keydown", (e) => this._key(e));
    this.el.addEventListener("focusin", (e) => {
      const item = e.target.closest('[role="treeitem"]');
      if (item) this._setCurrent(item, false);
    });
    this.el.addEventListener("click", (e) => {
      const item = e.target.closest('[role="treeitem"]');
      if (!item) return;
      if (item.hasAttribute("aria-expanded")) this._toggle(item);
      this._setCurrent(item, true);
      e.stopPropagation();
    });
  }

  // Bring the tree up to date in place: existing items keep their identity and only change their
  // words, so the screen reader reads the item that has focus without Up then Down (INF-10).
  fill(groups) {
    const lists = [...this.el.children];
    while (this.el.children.length > groups.length) this.el.lastElementChild.remove();
    groups.forEach((group, gi) => {
      let g = this.el.children[gi];
      if (!g) {
        g = this._item(`group:${group.id}`, group.label, 1, gi + 1, groups.length);
        const list = document.createElement("ul");
        list.setAttribute("role", "group");
        g.appendChild(list);
        g.setAttribute("aria-expanded", String(this.expanded.has(group.id)));
        this.el.appendChild(g);
      }
      this._label(g, group.label);
      g.dataset.id = `group:${group.id}`;
      g.setAttribute("aria-setsize", String(groups.length));
      const list = g.querySelector(':scope > [role="group"]');
      const items = group.items.length ? group.items : (group.empty ? [{ id: "", label: group.empty }] : []);
      while (list.children.length > items.length) {
        const last = list.lastElementChild;
        if (last === this.current) this._setCurrent(g, false, true);
        last.remove();
      }
      items.forEach((item, ii) => {
        let li = list.children[ii];
        if (!li) { li = this._item(item.id, item.label, 2, ii + 1, items.length); list.appendChild(li); }
        this._label(li, item.label);
        li.dataset.id = item.id;
        li.setAttribute("aria-setsize", String(items.length));
      });
    });
    if (!this.current || !this.el.contains(this.current)) {
      this._setCurrent(this.el.querySelector('[role="treeitem"]'), false, true);
    }
  }

  // The words are the item's first child text node, replaced only when they change.
  _label(li, label) {
    const node = li.firstChild;
    if (node.textContent !== label) node.textContent = label;
    if (li.hasAttribute("aria-expanded")) li.setAttribute("aria-label", label);
  }

  // F3: go to an item by its id (the item last focused, or Within's first), opening its group.
  // An area can be in two groups, so the item is looked for in its own group first.
  focusItem(id, groupId) {
    const g = groupId ? this._byId(`group:${groupId}`) : null;
    let item = id ? (g && this._byId(id, g)) || this._byId(id) : null;
    if (!item && g) {
      this._expand(g, true);
      item = g.querySelector('[role="group"] > [role="treeitem"]') || g;
    }
    if (!item) item = this.current;
    if (!item) return;
    const parent = item.parentElement.closest('[role="treeitem"]');
    if (parent) this._expand(parent, true);
    this._setCurrent(item, true);
    item.focus();
  }

  focusCurrent() {
    if (this.current) this.current.focus();
  }

  focusGroup(groupId) {
    const g = this._byId(`group:${groupId}`);
    if (!g) return;
    this._expand(g, true);
    const first = g.querySelector('[role="group"] > [role="treeitem"]');
    this._setCurrent(first || g, true);
    this.current.focus();
  }

  _item(id, label, level, pos, size) {
    const li = document.createElement("li");
    li.setAttribute("role", "treeitem");
    li.setAttribute("aria-level", String(level));
    li.setAttribute("aria-posinset", String(pos));
    li.setAttribute("aria-setsize", String(size));
    li.setAttribute("aria-selected", "false");
    li.tabIndex = -1;
    li.dataset.id = id;
    // The words go straight inside the item, with no labelling element, because
    // NVDA's say current line was silent in Firefox otherwise (PO test of
    // tools/spikes/s5/say_line.html). A group also holds its items, so it is
    // named with aria-label, or its name would be all its items' words.
    li.appendChild(document.createTextNode(label));
    if (id.startsWith("group:")) li.setAttribute("aria-label", label);
    return li;
  }

  _byId(id, within = this.el) {
    return [...within.querySelectorAll('[role="treeitem"]')].find((i) => i.dataset.id === id) || null;
  }

  _visible() {
    return [...this.el.querySelectorAll('[role="treeitem"]')].filter((item) => {
      const parent = item.parentElement.closest('[role="treeitem"]');
      return !parent || parent.getAttribute("aria-expanded") === "true";
    });
  }

  _setCurrent(item, select, quiet = false) {
    if (!item) return;
    if (this.current && this.current !== item) {
      this.current.tabIndex = -1;
      this.current.setAttribute("aria-selected", "false");
    }
    this.current = item;
    item.tabIndex = 0;
    item.setAttribute("aria-selected", "true");
    if (!quiet && (select || document.activeElement === item)) {
      const id = item.dataset.id;
      // A group heading is in its own group: Go to comes back to it (P2-T17k).
      const group = item.parentElement.closest('[role="treeitem"]') || (item.hasAttribute("aria-expanded") ? item : null);
      this.onSelect(id && !id.startsWith("group:") ? id : null,
                    group ? group.dataset.id.replace(/^group:/, "") : null);
    }
  }

  _move(item) {
    if (!item) return;
    this._setCurrent(item, true);
    item.focus();
  }

  _expand(item, open) {
    if (!item.hasAttribute("aria-expanded")) return;
    item.setAttribute("aria-expanded", String(open));
    const gid = item.dataset.id.replace(/^group:/, "");
    if (open) this.expanded.add(gid); else this.expanded.delete(gid);
  }

  _toggle(item) {
    this._expand(item, item.getAttribute("aria-expanded") !== "true");
  }

  _key(e) {
    const item = e.target.closest('[role="treeitem"]');
    if (!item || e.ctrlKey || e.altKey || e.metaKey) return;
    const visible = this._visible();
    const i = visible.indexOf(item);
    let handled = true;
    switch (e.key) {
      case "ArrowDown": this._move(visible[i + 1]); break;
      case "ArrowUp": this._move(visible[i - 1]); break;
      case "Home": this._move(visible[0]); break;
      case "End": this._move(visible[visible.length - 1]); break;
      case "ArrowRight":
        if (item.getAttribute("aria-expanded") === "false") this._expand(item, true);
        else if (item.getAttribute("aria-expanded") === "true") this._move(item.querySelector('[role="treeitem"]'));
        break;
      case "ArrowLeft":
        if (item.getAttribute("aria-expanded") === "true") this._expand(item, false);
        else this._move(item.parentElement.closest('[role="treeitem"]'));
        break;
      default:
        if (e.key.length === 1 && e.key !== " ") {
          const letter = e.key.toLowerCase();
          const after = visible.slice(i + 1).concat(visible.slice(0, i + 1));
          this._move(after.find((v) => v.firstChild.textContent.toLowerCase().startsWith(letter)));
        } else handled = false;
    }
    if (handled) e.preventDefault();
  }
}
