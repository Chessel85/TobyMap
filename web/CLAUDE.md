# web: rules for the browser shell

Read architecture sections 4.3, 4.4 and 7 before changing the web shell.

* Plain JavaScript, with no framework. The core runs in Pyodide inside a Web Worker (AD-9). The page never runs map logic.
* The bridge (`bridge.py`) returns plain dictionaries and lists, never Python objects. Numeric arrays travel as bytes and become typed arrays in `worker.js`.
* The core is not copied by hand. `tools/stage_web.py` copies `mapcore` into `web/py`, which is not in git. Pyodide lives in `web/vendor`, fetched by `tools/fetch_vendor.py --web`.
* List and tree items take real keyboard focus. Do not use aria-activedescendant, because NVDA stayed silent with it in RecallScore.
* Announcements go through one announcer (`js/announcer.js`): ariaNotify where the browser has it, otherwise two alternating live regions. Both Firefox and Chrome have ariaNotify now. Add `?announcer=live` to the address to force the live regions.
* Keys come from the registry the core sends at start-up. `js/keys.js` only turns browser key events into the registry's key names.
* Movement commands that arrive while the worker is busy are joined, not dropped. The core carries out every one and speaks only the last (ANN-3).
* No words in the page except the loading message, which is shown before the core has loaded. Everything else comes from the core's templates.
* Test in Firefox as fully as in Chromium. Firefox is the PO's main browser.
