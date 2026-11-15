# Phase 3 checklist: web version

This is the Phase 3 web checklist, for you to work through with NVDA in Firefox, then the main steps again in Chrome or Edge. The web version uses the same core and the same world pack as the desktop, so the expected words are the same. Rather than repeat them, each section below points to its section of the desktop checklist, docs/checklists/phase-3-desktop.md, and adds what is different in a browser.

For each step, write down its number and either "works" or what you heard instead. If you did the desktop checklist first, you only need to note where the web version differs.

## How to start the web version

* Open a terminal in the repository folder and run:

  `.venv\Scripts\python.exe tools\serve_web.py --pack E:\osmdata\tobymap\output\world\world.pack`

* It opens the web version in your default browser. To start at a place, put it in the address, such as `http://127.0.0.1:8765/index.html?at=51.2,1.2`. Below, "Start with 46.8,8.2" means put `?at=46.8,8.2` at the end of the address.
* If the arrow keys move NVDA's browse cursor instead of the map, press NVDA+Space for focus mode.
* The menu bar is Ctrl+Alt+M, and Settings is Ctrl+Comma.
* Leave the terminal open while you test. Ctrl+C in the terminal stops it.

## Before you start

* Set the same settings as in the desktop checklist's "Before you start". The web version keeps its own settings, in the browser.
* For section 8 below, switch on NVDA's automatic language switching: NVDA+Ctrl+V opens Voice settings, and it is "Automatic language switching (when supported)".

## 1. The first visit with the new pack

* 1.1 Start with 51.2,1.2. Note roughly how long it takes before you hear "TobyMap. Kent, Great Britain, England, British Isles, United Kingdom, Europe. Press F1 for keys." The pack is larger than in Phase 2, 495 MB.

## 2. Where you are, distant parts, Details and disputed land

* 2.1 Do desktop sections 1, 3, 4 and 5, with "Start with" as above.
* 2.2 In Details, W opens the Wikipedia article in a new tab. Ctrl+W on that tab closes it and brings you back to TobyMap's tab. Inside TobyMap, Ctrl+W would close TobyMap's own tab, which is why the key is W.

## 3. The Information panel, sorting and measuring

* 3.1 Do desktop sections 6, 7 and 8.
* 3.2 In the panel's tree, typing letters quickly adds them up, as in a Windows tree: "ar" reaches Arnifirst under "Peaks 119". A pause of a second starts again.
* 3.3 Ctrl+S, Ctrl+Shift+S and Ctrl+Enter work in the tree, and the browser does not take them. Ctrl+S must not open the browser's "Save page" window.

## 4. Hierarchy mode

* 4.1 Do desktop section 9. The ambiguous up list and Down's lists appear in a list like the location history, with Cancel.
* 4.2 Is the ambiguous up sound heard before NVDA reads the list?

## 5. Search

* 5.1 Do desktop section 10.
* 5.2 Ctrl+F opens TobyMap's Search window, not the browser's own find bar. This is the same from the map, the Information panel and Details.
* 5.3 Do the results come quickly enough in the browser? The first search of a word reads part of the pack, so it may take a little longer than the next.

## 6. The world tree, browsing and the query builder

* 6.1 Do desktop sections 11, 12 and 13.
* 6.2 Ctrl+Shift+F is not taken by the browser.
* 6.3 Note how long the first opening of Europe in the world tree takes, and the list of lakes in Switzerland. On the desktop they take about 5 seconds.

## 7. Look around

* 7.1 Do desktop section 14.
* 7.2 A browser can't send text to Braille without speaking it, so labels reach your Braille display only with "Also speak spatial labels through the screen reader" on, in Settings, Sound tab, as in Phase 2.

## 8. Names in another language (P3-T12b)

With NVDA's automatic language switching on, as in "Before you start".

* 8.1 Do desktop section 15, steps 15.1 and 15.2.
* 8.2 With "Always the local name", press F3 and read Within. Does NVDA switch to a German voice for Deutschland and Hessen? Try it in focus mode, and in browse mode (NVDA+Space).
* 8.3 Open the world tree with W, go to Europe, then Germany. Is its name read in German?
* 8.4 Announcements, such as what Space says on the map, are not marked with a language, so they stay in your English voice. To try them marked as well, add `&announcer=live` to the address, such as `?at=51.0,10.0&announcer=live`, and press Space.
* 8.5 Set Names back to "English where there is one".

## 9. Saying the place, layers and the controls

* 9.1 Do desktop sections 16, 17 and 18.
* 9.2 Tab never lands on the status line or the move and zoom buttons, and NVDA in browse mode reads the status line only if you move to it yourself.

## 10. Chrome or Edge

Open the same address in Chrome or Edge. Set the settings as in "Before you start", and do:

* 10.1 Section 1, the first visit.
* 10.2 Desktop section 9, hierarchy mode.
* 10.3 Desktop section 10, steps 10.1 to 10.6, search. Ctrl+F still opens TobyMap's Search, not the browser's find.
* 10.4 Desktop section 11, steps 11.1 and 11.2, the world tree.
* 10.5 Desktop section 14, look around.
* 10.6 Section 8 above, names, steps 8.1 and 8.2.

## 11. Layer sounds: tomorrow, after tonight's world build

* 11.1 Do desktop section 20 in Firefox. Your own sound files and switches are kept in the browser, separately from the desktop's.

## Finishing

When you have been through it, send me your notes, with the desktop's.
