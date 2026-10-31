# web: rules for the browser shell

Read architecture sections 4.3, 4.4 and 7 before changing the web shell.

* Plain JavaScript, with no framework. The core runs in Pyodide inside a Web Worker (AD-9). The page never runs map logic.
* The bridge returns plain dictionaries and lists, never Python objects.
* List and tree items take real keyboard focus. Do not use aria-activedescendant, because NVDA stayed silent with it in RecallScore.
* Announcements go through one announcer: ariaNotify where the browser has it, otherwise two alternating live regions.
* Test in Firefox as fully as in Chromium. Firefox is the PO's main browser.
