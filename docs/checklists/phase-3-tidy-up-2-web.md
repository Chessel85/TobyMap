# Phase 3 tidy-up 2 checklist: web version, world pack

This is the web version of the short third pass, for you to work through with NVDA in Firefox, then a few main steps again in Chrome or Edge. It covers only what changed in the second tidy-up plan (docs/plan/phase-3-tidy-up-plan2.md): the fixes and changes of P3-T28, the Information panel group by group (P3-T29), key maps and key files (P3-T31), and the layer sounds. It also lists what is still owed from the Phase 3 web checklist.

The web version uses the same core and the same world pack as the desktop, so the expected words are the same. Rather than repeat them, each section below points to its section of the desktop checklist, docs/checklists/phase-3-tidy-up-2-desktop.md, and adds what is different in a browser. The desktop checklist's words are what the core said on the world pack, with "such as" only for distances that depend on exactly where you stand. Steps marked "Possible fault" there say what TobyMap does now. A difference only in a number is not a fault unless it seems wrong.

For each step, write down its number, such as 4.3, and either "works" or what you heard instead. If you did the desktop checklist first, you only need to note where the web version differs. Put your notes in a text file next to this one, docs/checklists/phase-3-tidy-up-2-web-results.txt, as before. Lines starting with ">" are fine for answers to questions.

## How to start the web version

* Open a terminal in the repository folder and run:

  `.venv\Scripts\python.exe tools\serve_web.py --pack E:\osmdata\tobymap\output\world\world.pack`

* It opens the web version in your default browser. To start at a place, put it in the address, such as `http://127.0.0.1:8765/index.html?at=51.06,-1.31`. "Go to 51.06,-1.31" below means go to those coordinates with Ctrl+G, as in the desktop checklist. You never need to restart.
* If the arrow keys move NVDA's browse cursor instead of the map, press NVDA+Space for focus mode.
* Leave the terminal open while you test. Ctrl+C in the terminal stops it.

## Before you start

* In the Map menu, choose Reset all settings, then Reset. You hear "All settings are reset, as on a new installation", then the place. The web version keeps its own settings, in the browser, separately from the desktop's.
* That also gives you the Windows browser key map, all layers on, and the Political view.

## Keys that differ in the browser

The Windows browser key map is the Windows desktop one, except for two keys. The full list is the Windows browser column of docs/design/keymap.csv.

* The menu bar is Ctrl+Alt+M. Tab does not reach it, and browsers keep Alt for their own menus.
* The current feature's Wikipedia article is Alt+Shift+W, not Ctrl+Alt+W. Ctrl+W and Ctrl+Shift+W close the browser's tab, and Ctrl+Alt+W is AltGr+W, which types a character on some European keyboards. In desktop steps, read Ctrl+Alt+W as Alt+Shift+W.
* Settings is Ctrl+Comma, and Search is Ctrl+F. TobyMap's Search opens, not the browser's own find bar.

The Information panel's keys are as on the desktop: Shift+1 Within, Shift+2 Nearby, Shift+3 Bordering, Shift+4 Contains, Shift+5 Overlapping, Shift+6 Passed over, Shift+7 Search.

## 1. The first visit with the new pack

* 1.1 Start with `?at=51.06,-1.31`. Note roughly how long it takes before you hear "TobyMap. Hampshire, England, United Kingdom, Great Britain, British Isles, Europe. Press F1 for keys." There is no "Near Winchester" at the start: only Space names the town. The pack is about 536 MB.
* 1.2 Press F1. The list has "Go to Passed over: Shift+6" and "Go to Search: Shift+7". Close it.

## 2. Where am I, stand-in areas and exclaves

* 2.1 Do desktop section 1, the town you are near. Step 1.6, only Space names the town, and 1.8 to 1.10, the zoom, are the ones most worth hearing in the browser.
* 2.2 Do desktop section 2, the stand-in areas, and section 13, exclaves by their own names.
* 2.3 Does the browser add any delay to Space compared with the desktop?

## 3. The Information panel, group by group

* 3.1 Do desktop sections 3 to 7: Within, Nearby, Bordering, Contains and Overlapping.
* 3.2 Do desktop sections 8 and 9: Passed over, and sorting and hearing the order. Ctrl+S and Ctrl+Shift+S must not open the browser's "Save page" window.
* 3.3 Do desktop section 10, Search, Shift+7.
* 3.4 In the panel's tree, typing letters quickly adds them up, as in a Windows tree. A pause of a second starts again.
* 3.5 Ctrl+Enter works in the tree, and the browser does not take it.
* 3.6 In desktop step 7.8, and in 6.1, tell me how long Overlapping and Contains take to open in the browser. In the core, on this laptop, Overlapping on England takes about half a second and Contains on England under a second.
* 3.7 In desktop step 9.2, listen for the heading being said twice. In a browser it should be said once.

## 4. Details and Wikipedia

* 4.1 Do desktop section 11, with these differences.
* 4.2 In Details, W opens the Wikipedia article in a new tab. Ctrl+W on that tab closes it and brings you back to TobyMap's tab.
* 4.3 Step 11.3: pressing Enter on "Wikipedia article: Hampshire" opens a new tab. You hear "Opening the Wikipedia article for Hampshire." Come back to TobyMap's tab.
* 4.4 Step 11.4: from the map, and from the Information panel, press Alt+Shift+W, not Ctrl+Alt+W. You hear the same words, and the article opens in a new tab.
* 4.5 Does the browser ask you to allow pop-ups the first time? Tell me if it does.
* 4.6 Does Alt+Shift+W do anything else in Firefox, such as open a menu? It should not.

## 5. The Map views dialog

* 5.1 Do desktop section 12.
* 5.2 Escape in the dialog cancels, as Cancel does. The buttons Add, Rename, Delete, OK and Cancel are all reached with Tab, and "Save the layers as a view" is no longer there.
* 5.3 When you press Add or Rename, does the name come in a TobyMap dialog or the browser's own prompt? Tell me which.

## 6. Hierarchy mode, the condominium, roads and bays

* 6.1 Do desktop section 14, hierarchy mode. The ambiguous up list and Down's lists appear in a list like the location history, with Cancel. Is the ambiguous up sound heard before NVDA reads the list?
* 6.2 Do desktop section 15, the Moselle condominium. In step 15.3, press W to open the world tree.
* 6.3 Do desktop section 16, the two M3s and Belfast, and section 17, Hatch Pool and Poole Harbour. Note your choice at 16.4 again.
* 6.4 Ctrl+F in these sections opens TobyMap's Search from the map, the Information panel and Details, not the browser's find bar.

## 7. Key maps and your keys in the browser (P3-T31)

The words "key map", "your keys" and "key file" are in the glossary. Open Settings with Ctrl+Comma and go to the Keys tab.

* 7.1 There is a "Key map" select, set to "Windows browser". Below it are the commands and their keys, then the controls "Save keys as", "Open key file" and "Reset keys". Do the same as the desktop's 18.1.
* 7.2 In the Key map select, choose "Alternative". It is used at once, and you hear "Key map: Alternative." Settings is now on Ctrl+Shift+X, and the Wikipedia article on Alt+Shift+W, as in the browser. Press OK. Ctrl+Comma now does nothing, and Ctrl+Shift+X opens Settings.
* 7.3 Does the browser take Ctrl+Shift+X? It should not, outside a text field.
* 7.4 Change the key of Heading to Ctrl+Q. You hear "Heading is now Ctrl+Q." The browser may take Ctrl+Q, as it can quit Firefox on some systems. Tell me if it does, and choose another key.
* 7.5 Press "Save keys as". In the browser this downloads a file named tobymap-keys.json. Firefox may save it at once into your Downloads folder, or ask where. Tell me which, and whether NVDA says that the download is finished.
* 7.6 Press "Reset keys". You hear "Your keys are reset. The keys are those of the Alternative key map." Heading is back on H.
* 7.7 Press "Open key file". In the browser this is a file input: it opens the browser's file chooser. Choose tobymap-keys.json from your Downloads folder. You hear "Key file opened. The key map is Alternative." Heading is on its changed key again.
* 7.8 Is the file chooser easy to use with NVDA? Is the focus back on the Keys tab afterwards?
* 7.9 Choose a file that is not a key file, such as a text file. You hear that TobyMap cannot read it, and nothing changes.
* 7.10 Choose "Windows browser" in the Key map select: "Key map: Windows browser." Heading stays on its changed key, as your keys are kept on top of the key map.
* 7.11 Press "Reset keys", then OK. Ctrl+Comma opens Settings again.
* 7.12 Reload the page with F5. Are your key map and your keys remembered? Set them back with Reset keys, and the Windows browser key map, if not.
* 7.13 The key list is docs/design/keymap.csv. Look at the Windows browser column, and tell me if a key is wrong, hard to press, or taken by the browser or by NVDA.

## 8. The query builder and layer sounds

* 8.1 Do desktop section 19, the query builder that searches for a feature. Is the Search window the TobyMap one, and does Enter on the Rhine bring you back to the query builder?
* 8.2 Do desktop section 20, layer sounds, in Firefox. Your own sound files and switches are kept in the browser, separately from the desktop's.
* 8.3 In step 20.3, "use your own file" is a file input: it opens the browser's file chooser.
* 8.4 Does a sound start at once when you press Space, or is there a delay in the browser? The browser may need a key press before it plays any sound at the start: tell me if the first sound is missing.

## 9. Speed in the browser (P3-T20d)

The speed in the browser is still waiting for your agreement, so nothing here is a fault. Please note, as the desktop checklist's section 7.8 and the known "Down from Europe" do:

* 9.1 How long the first opening of Europe in the world tree takes, and the list of lakes in Switzerland. On the desktop they take about 5 seconds.
* 9.2 How long "Down from Europe" in hierarchy mode takes. On the desktop it takes about 2.5 seconds. The browser cannot make it faster without more memory.
* 9.3 How long the first search of a word takes. It reads part of the pack, so the second search is quicker.
* 9.4 Do you want the browser to use a larger memory store for the map, which makes these faster but costs memory in the browser? Answer with a ">" line.

## 10. Still owed from the Phase 3 web checklist

You may have done these already. Skip any you did.

* 10.1 Names in another language, from docs/checklists/phase-3-web.md section 8. With NVDA's automatic language switching on (NVDA+Ctrl+V, "Automatic language switching (when supported)"), set Names to "Always the local name" and press F3 at 51.0,10.0. Does NVDA switch to a German voice for Deutschland and Hessen, in focus mode and in browse mode? Set Names back to "English where there is one".
* 10.2 A browser cannot send text to Braille without speaking it, so labels reach your Braille display only with "Also speak spatial labels through the screen reader" on, in Settings, Sound tab.
* 10.3 Tab never lands on the status line or the move and zoom buttons, and NVDA in browse mode reads the status line only if you move to it yourself.

## 11. Chrome or Edge

Open the same address in Chrome or Edge. Reset all settings from the Map menu, and do:

* 11.1 Section 1, the first visit.
* 11.2 Section 3, steps 3.1 to 3.3: Within, Nearby and Passed over, and Ctrl+S not opening "Save page".
* 11.3 Section 4, Alt+Shift+W and W in Details.
* 11.4 Section 7, steps 7.1 to 7.7: the Keys controls, the download and the file chooser. Chrome and Edge ask before a download in different ways: tell me what you hear.
* 11.5 Section 8, step 8.2: layer sounds.

## 12. Overall

* 12.1 Tell me anything else that sounds wrong, slow or unclear in the browser.

## Finishing

Send me your notes in docs/checklists/phase-3-tidy-up-2-web-results.txt, with the desktop's.
