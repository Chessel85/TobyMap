# P4-T14f: fewer messages that only confirm

A proposal for you to read before anything changes. No template, code or other document has been changed yet.

It comes from your notes on checklist steps 11.3, 11.4, set 12 and 14.3 (phase 3 tidy-up 2, desktop). Every template in `mapcore/describe/templates.yaml` was read, and for each message said after a command I checked in the core and in both shells where the focus goes, and what the screen reader reads from it.

## The rule

The user experience description has no section called general principles yet. I propose a new section, "1.1 General principles", at the end of section 1, with these words:

> A message that only confirms what you did is not said when the new focus says enough. When a key or a button moves the focus, to a list item, a group heading, a dialog or a new window, the screen reader reads the new focus, and that tells you your action worked. A message is said only when it tells you something you cannot hear from the focus: a count, a result, a place, a setting that a key switched while the focus stayed where it was, or how to undo what you did, such as "Cancel brings it back". This is a general rule, not a fixed one.

## To take out

* `details.wikipedia_opening`: "Opening the Wikipedia article for {name}." Said after W, Ctrl+Alt+W, or Enter on the Wikipedia line in Details. Instead: the browser opens and the screen reader says its window or tab, with the article's name.
* `hierarchy.round`: "Left and Right now go round {name}." Said after Enter on the map in hierarchy mode, when look around is not playing. Instead: nothing is said, as the focus stays on the map; the next Right or Left says the first neighbour of that feature.
* `views.added`: "Added the {name} view. OK uses it." Said after OK in the Add dialog of Map views. Instead: the focus goes back to the Views list, on the new view, which is read by its name. The help at the top of the dialog already says that OK uses the view chosen.
* `views.renamed`: "{old} is now called {name}." Said after OK in the Rename dialog of Map views. Instead: the focus goes back to the Views list, on the view, read by its new name.
* `views.chosen`: "{name} view." Said after OK in Map views with another view chosen. You were on that view in the list when you pressed OK. Instead: the dialog closes and the map is named with the place, in the new view's order, as after any dialog with no answer of its own.
* `keys.changed`: "{label} is now {key}." Said after OK in the Change key dialog, in Settings, Keys. Instead: the focus goes back to the Keys list on that command, which reads "{label}: {key}". On the desktop it is now said only later, when Settings closes.
* `keys.cleared`: "{label} has no key now." Said after No key, then OK, in the Change key dialog. Instead: the Keys list reads "{label}: no key".
* `keys.keymap_chosen`: "Key map: {name}." Said after choosing in the Key map list in Settings, Keys. Instead: the list itself says the key map's name as you choose it.

## To keep

### Messages after a change the focus does not show

* `views.deleted`: "The {name} view is deleted. Cancel brings it back." The focus goes to the next view, which does not say that one was deleted, and only this says how to undo it.
* `views.saved`: "The layers are saved into the {name} view. OK keeps it." The view's line in the list reads the same before and after Save changes, so nothing else tells you the layers went in.
* `keys.reset_done`: "Your keys are reset. The keys are those of the {name} key map." The focus stays on the Reset keys button; the list behind it changes unheard, and this names the key map.
* `keys.opened`: "Key file opened. The key map is {name}." The key map comes from the file, so you cannot know it before; the focus goes back to the Open key file button.
* `current_layer.none_here` and `current_layer.back`: the focus stays on the item after Shift+Enter, and nothing else tells you which layer is current, or which feature became current instead.

### Messages that say where you are after a jump

* `panel.gone`: "{name}. {place}" after Enter on an item. The focus goes to the group's heading, which does not say the place you arrived at. The name is said only when the place does not start with it, so you know a line or town is now the current feature.
* `search.gone`, `tree.gone` and `hierarchy.moved`: the feature you arrived at and the zoom it was fitted to. The zoom is new, and after an arrow key in hierarchy mode the feature is new too.
* `reset.done` is in "Not sure" below.

### Counts and results

* `browse.done`, `browse.done_capped`, `query.done` and `query.done_capped`: the count, and that the answer is in the Search group. The focus goes back where it was, not to the Search group, so only this says how many were found.

### Keys that switch something while the focus stays on the map

The focus does not move, so the message is the only thing heard. Each says the new state or value.

* `movement.*`: the zoom and step, widest and closest zoom, largest and smallest step, linking, facing, orientation, mode and crossing a pole.
* `hierarchy.on`, `hierarchy.on_nothing` and `hierarchy.stepping`: the mode, and in hierarchy mode the current feature.
* `beacon.*`: on or off, and why it is silent near a pole or when sound is muted.
* `sound.muted` and `sound.unmuted`.
* `verbosity.terse`, `verbosity.normal` and `verbosity.detailed`: the preset, and what it says (see "Not sure").
* `display.theme` and `display.isolate_off`.
* `describer.started` and `describer.stopped`.

### Messages that say why nothing happened

These are refusals or errors: without them a key would seem to do nothing.

* `details.wikipedia_none`, `current_layer.no_item`, `display.isolate_none`, `display.colour_refused`, `look.go_none`, `look.muted`, `hierarchy.top`, `browse.none_here`, `browse.nothing_inside`.
* `tree.leaf`, `tree.world_go`, `tree.special_go`, `search.nothing`, `query.nothing`, `query.bad_distance`, `query.bad_choice`.
* `keys.taken`, `keys.invalid`, `keys.bad_file`, `views.name_empty`, `views.name_taken`, `settings.bad_value`, `layers.range_error`, `layers.choose_layer`, the `typing` errors, `bookmark.later` and `history.nothing_to_repeat`.

### Answers and warnings

* The answers to a question key, such as where am I, the measuring keys, the key describer's answers, timing, the visible map and the Braille test: the message is the answer.
* Warnings that are not after your own command: `sound.own_file_failed`, `sound.no_device`, `sound.no_hrtf`, `voice.*`, `packs.*`, `map.still_drawing`, `beacon.near_pole` and `beacon.back`.

## Not sure

* `current_layer.chosen`: "Current layer: {layer}. {name} is the current feature." You pressed Shift+Enter on that feature, so its name only confirms. Shall it be shortened to "Current layer: {layer}."?
* `reset.done`: "All settings are reset, as on a new installation. {place}." The dialog closes and the map would say the start place anyway. Shall the first sentence go? I suggest keeping it, as the place alone does not tell you that your keys and layers were reset too.
* `display.isolated`: "Isolated: {name}. Only it is on the map. Press Ctrl+I again to show everything." The name is new, but the rest is help, and says Ctrl+I even when you have given Isolate another key. Shall it be shortened to "Isolated: {name}."?
* `verbosity.*`: each preset says what it does, such as "Terse. Only the smallest area that changed is said." Once you know the presets, shall only the name be said, such as "Terse."?
* `movement.facing` after Type a bearing, when you are already in free facing: "Facing {heading}." It repeats what you typed, but in your bearing style, so "SW" is said as "225 degrees" if you chose degrees. Keep it?
* `hierarchy.round`, once taken out: Enter in hierarchy mode is then silent. Would you like a short sound in its place, or nothing at all? I suggest nothing.

## Found on the way

These are not part of the rule, but you may want them fixed at the same time.

* On the desktop, the messages from the Keys tab, `keys.reset_done`, `keys.opened` and `keys.keymap_chosen`, are said when you act, and said again when Settings closes.
* `describer.started` says "Press Shift+F1 again to leave", and `display.isolated` says "Ctrl+I", even when you have changed those keys.
* `sort.natural`, `sort.name`, `sort.distance`, `sort.bearing` and `panel.empty_later` are no longer said anywhere, and could be deleted. Ctrl+S already follows the rule: the focus goes to the group's heading, which says the order.
