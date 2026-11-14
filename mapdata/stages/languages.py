"""The language of an OpenStreetMap feature's local name (P3-T12b, ACC-9).

OSM's name tag is the name in the place's own language, and it rarely says which language that is. The rule is
mapcore.names.language_of_name: name:en, then the feature's default_language, then its wikipedia tag's language,
then the one name:xx tag that is the same as the name. A feature record keeps the answer as "local_lang", which
the writing stage keeps, and the application uses to mark the name with its language in the web version.

Used now by tools/make_phase3_samples.py, so the test pack's samples carry local_lang. The reading stages do not
use it yet: changing them makes the next world build read the planet file again, which the PO chose not to do
for now (DP195). They can use it when a later build reads the planet file anyway.
"""
from __future__ import annotations

from mapcore.names import language_of_name


def name_language(feature) -> str | None:
    """The language code of a GeoDesk feature's name, or None when it cannot be told."""
    return language_of_name({str(k): str(v) for k, v in feature.tags})
