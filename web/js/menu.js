// The menu bar, built from the command registry (AD-3), following the ARIA
// menubar pattern with real focus on each item.
// On the bar: Left and Right move, Enter, Space or Down open a menu.
// In a menu: Up and Down move, Enter or Space choose, Left and Right switch
// menus, Escape goes back to the bar. Tab leaves the menu bar for the next
// region, so Escape is never needed (ACC-7).

export class MenuBar {
  constructor(element, menus, onCommand, onTab) {
    this.el = element;
    this.onCommand = onCommand;
    this.onTab = onTab;
    this.tops = [];
    this.popups = [];
    menus.forEach((menu, mi) => {
      const top = document.createElement("button");
      top.type = "button";
      top.className = "menubar-item";
      top.setAttribute("role", "menuitem");
      top.setAttribute("aria-haspopup", "menu");
      top.setAttribute("aria-expanded", "false");
      top.tabIndex = mi === 0 ? 0 : -1;
      top.textContent = menu.label;
      const popup = document.createElement("ul");
      popup.className = "menu";
      popup.setAttribute("role", "menu");
      popup.setAttribute("aria-label", menu.label);
      popup.hidden = true;
      menu.items.forEach((item) => {
        const li = document.createElement("li");
        li.setAttribute("role", "menuitem");
        li.tabIndex = -1;
        li.dataset.command = item.name;
        const label = document.createElement("span");
        label.textContent = item.label;
        li.appendChild(label);
        if (item.key) {
          li.setAttribute("aria-keyshortcuts", item.key.replace(/ /g, ""));
          const key = document.createElement("span");
          key.className = "key";
          key.textContent = item.key;
          li.appendChild(key);
        }
        li.addEventListener("click", () => this._choose(li));
        popup.appendChild(li);
      });
      top.addEventListener("click", () => (popup.hidden ? this._open(mi, true) : this.closeAll(true)));
      top.addEventListener("keydown", (e) => this._topKey(e, mi));
      popup.addEventListener("keydown", (e) => this._menuKey(e, mi));
      this.el.appendChild(top);
      this.el.appendChild(popup);
      this.tops.push(top);
      this.popups.push(popup);
    });
    this.el.hidden = false;
  }

  // Reaching the menu bar with Tab opens the first menu, as the desktop
  // version does, so both behave the same (UX section 2).
  focusFirst() {
    this._open(0, true);
  }

  contains(node) {
    return this.el.contains(node);
  }

  closeAll(focusTop) {
    this.popups.forEach((p, i) => {
      p.hidden = true;
      this.tops[i].setAttribute("aria-expanded", "false");
    });
    if (focusTop !== false && focusTop !== true) focusTop.focus();
  }

  _open(mi, focusFirstItem) {
    this.closeAll(false);
    const top = this.tops[mi];
    const popup = this.popups[mi];
    popup.style.left = `${top.offsetLeft}px`;
    popup.hidden = false;
    top.setAttribute("aria-expanded", "true");
    this.tops.forEach((t, i) => (t.tabIndex = i === mi ? 0 : -1));
    const items = popup.querySelectorAll('[role="menuitem"]');
    if (focusFirstItem && items.length) items[0].focus();
  }

  _choose(li) {
    this.closeAll(false);
    this.onCommand(li.dataset.command);
  }

  _topKey(e, mi) {
    const n = this.tops.length;
    let handled = true;
    switch (e.key) {
      case "ArrowRight": this._focusTop((mi + 1) % n); break;
      case "ArrowLeft": this._focusTop((mi - 1 + n) % n); break;
      case "ArrowDown": case "Enter": case " ": this._open(mi, true); break;
      case "Home": this._focusTop(0); break;
      case "End": this._focusTop(n - 1); break;
      case "Tab": this.closeAll(false); this.onTab(e.shiftKey ? -1 : 1); break;
      default: handled = false;
    }
    if (handled) { e.preventDefault(); e.stopPropagation(); }
  }

  _focusTop(i) {
    this.tops.forEach((t, k) => (t.tabIndex = k === i ? 0 : -1));
    this.tops[i].focus();
  }

  _menuKey(e, mi) {
    const items = [...this.popups[mi].querySelectorAll('[role="menuitem"]')];
    const i = items.indexOf(document.activeElement);
    const n = this.tops.length;
    let handled = true;
    switch (e.key) {
      case "ArrowDown": items[(i + 1) % items.length].focus(); break;
      case "ArrowUp": items[(i - 1 + items.length) % items.length].focus(); break;
      case "Home": items[0].focus(); break;
      case "End": items[items.length - 1].focus(); break;
      case "Enter": case " ": if (i >= 0) this._choose(items[i]); break;
      case "ArrowRight": this._open((mi + 1) % n, true); break;
      case "ArrowLeft": this._open((mi - 1 + n) % n, true); break;
      case "Escape": this.closeAll(this.tops[mi]); break;
      case "Tab": this.closeAll(false); this.onTab(e.shiftKey ? -1 : 1); break;
      default: handled = false;
    }
    if (handled) { e.preventDefault(); e.stopPropagation(); }
  }
}
