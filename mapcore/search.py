"""Search by name (P3-T8a, P3-T8b, SRB-1, ACC-9, architecture 7.9).

The rules both sides share: the pipeline builds the search records with them (mapdata/stages/search_index.py),
and the store reads and matches with them (Store.search). Pure Python, so it runs unchanged in the browser.

* A name is made plain to compare: accents taken off, special letters such as ß and ø spelt out, upper case
  made lower, and anything but letters and digits made a space (normalise). "São Paulo" becomes "sao paulo".
* Each name is filed under the first three letters of its words (prefixes): the first word always, and each
  later word of three letters or more that is not a small word such as "of" or "de". So "york" finds New York.
* The prefixes are spread over the search records by a check number (bucket), so the pack's directory stays
  small however many scripts the names are in. A search reads only the records of its own words' prefixes,
  never the whole index.
* A row matches as well as one of these, best first (match): the same name; a name starting with what was
  typed; every word typed starting a word of the name, in any order; or a name close to it in groups of three
  letters (similarity), which finds small misspellings such as "Pariss" and "londn". A word for the kind of
  feature, such as "River" or "Lake" (KIND_WORDS), makes no difference to the match (P3-T32f): "thames" is the
  same name as the River Thames, the Thames River and Thames in New Zealand, and importance puts the River
  Thames first; "michigan" finds Lake Michigan just after the state, not after an island named Michigan.
* Rows are ranked by how well they match, then by importance, a number from 0 to 1,000 the build gives each
  feature from its population, its kind and how many Wikimedia sites have it, with up to NEAR_POINTS more for
  being near where you are (nearness, P3-T32f): enough to put the M3 in England before the other M3s, of
  much the same importance, and Winchester in England before Winchester in Virginia when you are in Hampshire, but not
  Paris in Texas before Paris in France when you are in Texas (rank_key).
"""
from __future__ import annotations

import math
import unicodedata
import zlib

# One row of a search record, as a JSON list, in this order.
ROW = ("key", "name", "id", "layer", "importance", "lon", "lat", "description", "via")
KEY, NAME, ID, LAYER, IMPORTANCE, LON, LAT, DESCRIPTION, VIA = range(len(ROW))

PREFIX = 3
# Small words that are not filed on their own when they are not the first word of a name. They still count in
# matching, so "isle of wight" finds the Isle of Wight.
SMALL_WORDS = frozenset({
    "a", "an", "and", "the", "of", "on", "in", "at", "by", "to",
    "de", "del", "della", "der", "des", "di", "do", "dos", "das", "du", "da", "den", "dem", "het",
    "el", "la", "le", "les", "los", "las", "lo", "il", "al", "y", "e", "et", "und", "van", "von", "zu", "upon",
})

# Words for the kind of feature, made plain, that a name may have or not without being another name: "River
# Thames", "Thames River". Water and land forms only; not words such as "forest" or "park", which are often
# the name itself, as in the New Forest.
KIND_WORDS = frozenset({
    "river", "lake", "loch", "lough", "mount", "mt", "mountain", "mountains", "sea", "bay", "gulf", "island",
    "islands", "isle", "isles", "strait", "cape", "creek", "rio", "riviere", "fleuve", "lac", "lago", "monte",
    "mont", "isla", "ile", "ilha",
})

# Match levels, best first.
SAME, STARTS, WORDS, CLOSE = 4, 3, 2, 1
# The least similarity, in groups of three letters, for a close match.
CLOSE_ENOUGH = 0.5

_FOLD = str.maketrans({
    "ß": "ss", "ẞ": "ss", "æ": "ae", "Æ": "ae", "œ": "oe", "Œ": "oe", "ø": "o", "Ø": "o", "ł": "l", "Ł": "l",
    "đ": "d", "Đ": "d", "ð": "d", "Ð": "d", "þ": "th", "Þ": "th", "ı": "i", "ħ": "h", "Ħ": "h", "ŀ": "l",
    "Ŀ": "l", "ŋ": "n", "Ŋ": "n", "ĸ": "k",
    # Apostrophes and the letters like them are left out, not made a space: "Côtes-d'Armor" is "cotes darmor"
    # whichever apostrophe is typed.
    "'": "", "’": "", "‘": "", "ʼ": "", "ʻ": "", "`": "", "´": "",
})


def normalise(text: str) -> str:
    """A name made plain to compare (architecture 7.9): no accents, lower case, letters and digits only, one
    space between words. Scripts without accents, such as Greek or Japanese, are kept as they are, in lower
    case."""
    text = unicodedata.normalize("NFKD", (text or "").translate(_FOLD))
    text = "".join(c for c in text if not unicodedata.combining(c)).casefold().translate(_FOLD)
    return " ".join("".join(c if c.isalnum() else " " for c in text).split())


def prefix(word: str) -> str:
    return word[:PREFIX]


def filed_under(key: str) -> list[str]:
    """The prefixes a plain name is filed under: its first word's, and each later word's of three letters or
    more that is not a small word. In order, each once."""
    words = key.split()
    if not words:
        return []
    out = [prefix(words[0])]
    for w in words[1:]:
        if len(w) >= PREFIX and w not in SMALL_WORDS and prefix(w) not in out:
            out.append(prefix(w))
    return out


def looked_up(key: str, most: int = 3) -> list[str]:
    """The prefixes a search reads for what was typed, made plain: those of its words of three letters or more
    that are not small words, at most `most`, else its first word's. Each is a word a matching name is filed
    under, so the records read always hold every name that can match by word."""
    words = key.split()
    out = []
    for w in words:
        if len(w) >= PREFIX and w not in SMALL_WORDS and prefix(w) not in out:
            out.append(prefix(w))
    if not out and words:
        out = [prefix(words[0])]
    return out[:most]


def bucket(pref: str, buckets: int) -> int:
    """The search record a prefix is in."""
    return (zlib.crc32(pref.encode("utf-8")) & 0xFFFFFFFF) % max(1, buckets)


def trigrams(key: str) -> set[str]:
    """The groups of three letters of a plain name, with two spaces before and one after, so the start counts
    more than the end, as a misspelling is more often at the end."""
    padded = f"  {key} "
    return {padded[i:i + 3] for i in range(len(padded) - 2)}


def similarity(a: str, b: str, grams_a: set[str] | None = None) -> float:
    """How alike two plain names are, from 0 to 1: twice the groups of three letters they share, over how many
    each has (Dice's measure)."""
    ga = grams_a if grams_a is not None else trigrams(a)
    gb = trigrams(b)
    if not ga or not gb:
        return 0.0
    return 2.0 * len(ga & gb) / (len(ga) + len(gb))


def without_kind(key: str) -> str:
    """A plain name without its words for the kind of feature and its small words: "river thames" is "thames",
    "isle of wight" is "wight". A name of nothing but those is kept whole, so "river" is still "river"."""
    words = [w for w in key.split() if w not in KIND_WORDS and w not in SMALL_WORDS]
    return " ".join(words) if words else key


# Nearness (P3-T32f): up to this many points of importance for being where you are, fewer the farther away, on
# a scale of the logarithm of the distance, so the difference between 10 km and 100 km counts as much as that
# between 1,000 and 10,000 km.
NEAR_POINTS = 100
NEAR_FROM_KM = 10.0       # nearer than about this counts nearly in full
NEAR_TO_KM = 20_000.0     # half the way round the world counts nothing
EARTH_M = 6_371_008.8     # the mean radius


def sphere_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """The distance between two points on the mean sphere, which is close enough to rank and narrow a search."""
    a, b = math.radians(lat1), math.radians(lat2)
    h = math.sin((b - a) / 2) ** 2 + math.cos(a) * math.cos(b) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * EARTH_M * math.asin(min(1.0, math.sqrt(h)))


def nearness(metres: float | None) -> int:
    """The points of importance for being this far from where you are: NEAR_POINTS at 0, none at NEAR_TO_KM;
    none when it is not known where either is."""
    if metres is None:
        return 0
    share = math.log1p(metres / 1000 / NEAR_FROM_KM) / math.log1p(NEAR_TO_KM / NEAR_FROM_KM)
    return int(round(NEAR_POINTS * max(0.0, 1.0 - share)))


class Query:
    """What was typed, made ready to match many rows quickly."""

    def __init__(self, text: str):
        self.text = text
        self.key = normalise(text)
        self.words = self.key.split()
        self.grams = trigrams(self.key)
        self.prefixes = looked_up(self.key)
        self.core = without_kind(self.key)

    def match(self, key: str) -> tuple[int, float] | None:
        """How well a row's plain name matches: (level, similarity), or None. Similarity is 1 for the levels
        above CLOSE."""
        q = self.key
        if not q:
            return None
        if key == q or without_kind(key) == self.core:
            return SAME, 1.0
        if key.startswith(q):
            return STARTS, 1.0
        names = key.split()
        if all(any(n.startswith(w) for n in names) for w in self.words):
            return WORDS, 1.0
        if abs(len(key) - len(q)) > max(3, len(q) // 2):
            return None
        s = similarity(q, key, self.grams)
        if s >= CLOSE_ENOUGH:
            return CLOSE, s
        return None


def rank_key(level: int, similar: float, importance: int, name: str, identifier: str, near: int = 0) -> tuple:
    """The order of results: how well they match, then the most important with its points for nearness (near,
    from nearness), then by name and identifier, so the order is always the same."""
    return (-level, -round(similar, 3), -(importance + near), name.casefold(), identifier)
