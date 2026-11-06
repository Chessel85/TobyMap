# Phase 2 checklist for a sighted helper: themes, names and magnifiers

These steps need sight to judge. They are for a sighted or partially sighted helper, if you have one. If you don't, skip them: the automatic tests check the contrast, that names never overlap, and where the magnifier is pointed, but not how it looks.

Do them on the desktop version first, then in the web version in Firefox and in Chrome or Edge. Start at `--at 51.2,1.2` on the desktop, or `?at=51.2,1.2` in the address of the web version. Write down each step's number and what you saw.

## 1. Themes (VIS-2)

* 1.1 Press T. TobyMap says "High contrast dark theme." The map is dark, with white borders and the current area outlined in yellow.
* 1.2 Press T again: "High contrast light theme." Pale land, black borders, the current area in dark blue.
* 1.3 Press T again: "Colour-blind safe theme." Neighbouring countries are in clearly different colours. If the helper has colour blindness, ask whether neighbours look different.
* 1.4 Press T again: "Standard theme." Shift+T goes back the other way.
* 1.5 In each theme, are the names, borders and the centre cross easy to see?

## 2. The map display setting (DP108)

In Settings, Display:

* 2.1 Set "Fill of the areas" to "One colour for all", and the fill colour to Light grey. Every area is light grey, with borders between them.
* 2.2 Set the fill to "None: outlines only". Only the borders are drawn. The current area's outline is still drawn.
* 2.3 Switch "Draw the borders" off. Only the current area's outline is left.
* 2.4 Choose a high contrast theme, then a border colour close to the land, such as Black in high contrast dark. TobyMap says the colour is too close for the 7 to 1 contrast, and keeps the theme's own.
* 2.5 Put everything back: different colours for neighbours, borders on, the theme's own colours.

## 3. Isolate (VIS-2)

* 3.1 Press Ctrl+I. TobyMap says "Isolated: England. Only it is on the map. Press Ctrl+I again to show everything." Only England and its outline are drawn.
* 3.2 Press Ctrl+I again. TobyMap says "Showing everything." The map is whole again.
* 3.3 Start at `--at -16.5,179.99` (Fiji), zoom 1,000 kilometres, and press Ctrl+I. The region is one shape, across the 180 degree line, with no line along it.

## 4. Names on the map (VIS-3)

* 4.1 Names of countries, regions and seas are on the map, inside their areas, with no two overlapping, and none over the centre cross.
* 4.2 Zoom in with Page Down. Names grow as their areas grow on the map, up to a limit.
* 4.3 In Settings, Display, set "Size of the names, in percent" to 200. Names are twice the size; fewer fit.
* 4.4 Hold an arrow key. The names go while it is held and come back when it is let go.
* 4.5 Switch "Show names on the map" off. The names go.

## 5. Heading-up (VIS-5)

* 5.1 In Settings, Display, switch on "Cardinal and free facing: turn the map so the way you face is up".
* 5.2 Press O for cardinal facing, and Right to face east. The map turns, so east is at the top, and the heading arrow points up.
* 5.3 Click above the centre of the map. The location moves east.
* 5.4 Press O until north-fixed. North is at the top again. Switch the setting off.

## 6. Magnifiers (ACC-8, DP146)

* 6.1 Start Windows Magnifier with Windows+Plus, in full screen view. In its settings, Ctrl+Windows+M, under "Have Magnifier follow", switch on "The text cursor" and "Keyboard focus".
* 6.2 Desktop: put the map in focus, zoom Magnifier in, and move the magnified view away from the map with the mouse. Then press an arrow key. Magnifier should bring the centre of the map, with the cross, back into view.
* 6.3 Desktop: Tab to the Information panel and back to the map. Magnifier should show the centre of the map, not its top corner.
* 6.4 Web version, in Chrome or Edge, then in Firefox: the same as 6.2 and 6.3. In the web version the map's focus point is at its centre; whether Magnifier follows it after a step, as well as when focus arrives, depends on the browser. Write down what each one does, and it goes into Help and the release notes.
* 6.5 If you have ZoomText or another magnifier, the same steps with it.
