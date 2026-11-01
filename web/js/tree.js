// The Information panel tree (UX section 6), following the ARIA tree pattern.
// Each item takes real keyboard focus with a roving tabindex; there is no
// aria-activedescendant, which NVDA stayed silent with in RecallScore.
//
// Keys: Up and Down move through visible items, Right opens a group or goes to
// its first item, Left closes a group or goes to its parent, Home and End go
// to the first and last item. Typing a letter jumps to the next item starting
// with it.

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

  fill(groups) {
    const currentId = this.current ? this.current.dataset.id : null;
    this.el.textContent = "";
    groups.forEach((group, gi) => {
      const g = this._item(`group:${group.id}`, group.label, 1, gi + 1, groups.length);
      const open = this.expanded.has(group.id);
      g.setAttribute("aria-expanded", String(open));
      const list = document.createElement("ul");
      list.setAttribute("role", "group");
      const items = group.items.length ? group.items : (group.empty ? [{ id: "", label: group.empty }] : []);
      items.forEach((item, ii) => list.appendChild(this._item(item.id, item.label, 2, ii + 1, items.length)));
      g.appendChild(list);
      this.el.appendChild(g);
    });
    const again = currentId !== null && this._byId(currentId);
    this._setCurrent(again || this.el.querySelector('[role="treeitem"]'), false, true);
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
    const span = document.createElement("span");
    span.className = "label";
    span.id = `ti-${Math.random().toString(36).slice(2)}`;
    span.textContent = label;
    li.setAttribute("aria-labelledby", span.id);  // so a group's name is not its whole contents
    li.appendChild(span);
    return li;
  }

  _byId(id) {
    return [...this.el.querySelectorAll('[role="treeitem"]')].find((i) => i.dataset.id === id) || null;
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
      this.onSelect(id && !id.startsWith("group:") ? id : null);
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
      case "Enter":
        if (item.hasAttribute("aria-expanded")) this._toggle(item);
        break;
      default:
        if (e.key.length === 1 && e.key !== " ") {
          const letter = e.key.toLowerCase();
          const after = visible.slice(i + 1).concat(visible.slice(0, i + 1));
          this._move(after.find((v) => v.querySelector(".label").textContent.toLowerCase().startsWith(letter)));
        } else handled = false;
    }
    if (handled) e.preventDefault();
  }
}
