"""Which name of a feature is said and shown, and its language (P3-T12; ACC-9, DP172).

A pack holds two names of a feature (DP172): "en", its English name, and "local", its name in the
place's own language, only where that differs. Where OpenStreetMap has no English name, "en" holds the
local name. A record may also give "local_lang", the language of its local name, as a language code
such as "de", found by the build where it can tell (language_of_name, used by mapdata/stages/languages.py).

The setting "Names" chooses:

* "english": the English name where there is one, else the local name (the default).
* "local": always the local name.

Every name said or shown comes through name_of, so one setting changes them all. A name is a Name: a str
that also carries its language, or None when it is English or not known. The web page marks the names in
another language with their lang attribute, so a screen reader set to switch voices can (P3-T12b).
"""
from __future__ import annotations

import threading

ENGLISH = "english"
LOCAL = "local"
CHOICES = (ENGLISH, LOCAL)


class Name(str):
    """A feature's name, with its language code (lang), or None when it is English or not known."""
    lang: str | None = None

    def __new__(cls, text: str, lang: str | None = None):
        out = super().__new__(cls, text)
        out.lang = lang if lang and lang != "en" else None
        return out


class Naming:
    """The name chosen, shared by a store and every Area it makes, so changing it changes them all at once."""

    def __init__(self, choice: str = ENGLISH):
        self.choice = choice if choice in CHOICES else ENGLISH

    def name_of(self, record: dict) -> Name:
        name = name_of(record, self.choice)
        if record.get("type") == "condominium" and record.get("sovereign"):
            # Said with its owners wherever its name is said (P3-T26c, DP205): "Moselle condominium, shared by
            # Germany and Luxembourg".
            from mapcore.describe import say

            name = Name(say("place.condominium", name=str(name), owners=record["sovereign"]), name.lang)
        if record.get("layer") in _say_type and record.get("type"):
            kind = str(record["type"])
            if str(name).casefold() != kind.casefold():
                # Said with its type after its name wherever its name is said, unless the name is already the
                # type's words (P4-T1f): "Broadway (Stop E), bus stop", but "Bench".
                from mapcore.describe import say

                name = Name(say("poi_categories.with_type", name=str(name), type=kind), name.lang)
        if name.lang:
            hear(name)
        return name


# The layers whose items are said with their type after their name: those whose definition says say_type, such as a
# regional pack's points of interest (P4-T1f). The layer catalogue sets them from the packs' layer definitions when it
# is made (mapcore/layers/catalogue.py), so every Naming follows them. A layer id means the same layer in every pack.
_say_type: frozenset = frozenset()


def say_type_layers(layer_ids) -> None:
    """The layers whose items are said with their type, in place of those before."""
    global _say_type
    _say_type = frozenset(layer_ids)


# The names in another language put into words since the shell last asked (P3-T12b). mapcore.describe.say notes
# every Name it is given; the session hands them to the shell with each answer, so the web page can mark them.
_heard: dict[str, str] = {}
_heard_lock = threading.Lock()
HEARD_LIMIT = 2000   # a held key's many steps between two answers never grow it without end


def hear(*values) -> None:
    """Note any of these values that is a name in another language."""
    for v in values:
        if isinstance(v, Name) and v.lang:
            with _heard_lock:
                if len(_heard) < HEARD_LIMIT:
                    _heard[str(v)] = v.lang


def take() -> dict[str, str]:
    """The names in another language noted since the last call, {name: language code}, and forget them."""
    global _heard
    with _heard_lock:
        out, _heard = _heard, {}
    return out


DEFAULT = Naming()   # for an Area made without a store, as the tests do


def name_of(record: dict, choice: str = ENGLISH) -> Name:
    """The name of a feature record the setting chooses, with its language."""
    names = record.get("names") or {}
    local_lang = record.get("local_lang")
    english = names.get("en")
    local = names.get("local")
    if choice == LOCAL:
        if local:
            return Name(local, local_lang)
        if english:   # the only name: the local one, whether or not it is also the English
            return Name(english, local_lang)
    else:
        if english:   # with a separate local name, "en" is truly English; without, it is the local name too
            return Name(english, None if local else local_lang)
        if local:
            return Name(local, local_lang)
    others = [v for v in names.values() if v]
    return Name(others[0]) if others else Name(record.get("id", ""))


def _code(text) -> str | None:
    """A plain language code, such as "de" or "ast", or None: not "de-CH" or "sr-Latn", which are left out."""
    text = str(text or "").strip()
    return text if 2 <= len(text) <= 3 and text.isalpha() and text.islower() else None


def language_of_name(tags: dict) -> str | None:
    """The language of an OpenStreetMap feature's name tag (P3-T12b), or None when it cannot be told. Many
    languages often write a name the same way (Italia is Italian, Spanish, Romanian and more), so, in order:

    * "en" when name:en is the same as the name;
    * the feature's own default_language, as countries have, when its name:xx is the same or it has none;
    * the language of its wikipedia tag, such as "de:Österreich", when the article has the same title;
    * the one language whose name:xx tag is the same as the name, when only one is.
    """
    name = tags.get("name")
    if not name:
        return None
    if tags.get("name:en") == name:
        return "en"
    same = {c for c in (_code(k[5:]) for k, v in tags.items() if k.startswith("name:") and v == name) if c}
    default = _code(tags.get("default_language"))
    if default and (default in same or not tags.get("name:" + default)):
        return default
    lang, _, title = str(tags.get("wikipedia") or "").partition(":")
    if _code(lang) and title.replace("_", " ").strip() == name:
        return lang
    return same.pop() if len(same) == 1 else None
