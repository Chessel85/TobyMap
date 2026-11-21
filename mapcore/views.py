"""Map views and the drawing order (P3-T23, DP198), from views.yaml.

A map view decides, for each layer, whether it is shown, its zoom range, whether it is filled and how,
whether its outline is drawn, and the order in which "where am I" says the areas. The drawing order is the
same in every view. There are two views built in, political (the first) and physical; the user can save
their own, kept with their settings (Settings.views), each made from a built-in view.

The file is read each time TobyMap starts, so the data manager can change it with no new build.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

VIEWS_FILE = Path(__file__).resolve().parent / "views.yaml"
FILLS = ("colours", "plain", "kind", "water", "light_water", "none")
OUTLINES = "outlines"   # the place in the drawing order where the outlines are drawn
LAYER_FIELDS = ("on", "min_zoom_m", "max_zoom_m", "fill", "outline", "names")


@lru_cache(maxsize=1)
def _data() -> dict:
    data = yaml.safe_load(VIEWS_FILE.read_text(encoding="utf-8")) or {}
    for view in data.get("views", []):
        for layer_id, values in (view.get("layers") or {}).items():
            if values.get("fill") not in (None, *FILLS):
                raise ValueError(f"views.yaml: the fill of {layer_id} in the {view['id']} view must be one of {FILLS}")
    return data


def drawing_order() -> list[str]:
    return list(_data().get("drawing_order", []))


def political_layers() -> list[str]:
    return list(_data().get("political_layers", []))


def built_in() -> list[dict]:
    """The built-in views, the default first: [{id, name, said, layers}]."""
    return [dict(v) for v in _data().get("views", [])]


def default_id() -> str:
    return built_in()[0]["id"]


def find(view_id: str, saved: dict | None = None) -> dict:
    """A view by its identifier: a built-in view, or one the user saved, as {id, name, said, layers, saved}.
    A saved view keeps its layers' values, and takes the said order of the built-in view it was made from.
    An unknown one is the default view."""
    views = {v["id"]: v for v in built_in()}
    mine = (saved or {}).get(view_id)
    if isinstance(mine, dict):
        base = views.get(mine.get("base")) or views[default_id()]
        return {"id": view_id, "name": view_id, "said": base.get("said", []),
                "layers": {k: dict(v) for k, v in (mine.get("layers") or {}).items()}, "saved": True,
                "base": base["id"]}
    view = views.get(view_id) or views[default_id()]
    return {"id": view["id"], "name": view["name"], "said": view.get("said", []),
            "layers": {k: dict(v) for k, v in (view.get("layers") or {}).items()}, "saved": False,
            "base": view["id"]}


def layer_values(view: dict) -> dict[str, dict]:
    """{layer id: the fields the view sets}, only those in LAYER_FIELDS."""
    return {k: {f: v for f, v in values.items() if f in LAYER_FIELDS} for k, values in view["layers"].items()}


def said_rank(view: dict, layer_id: str, pack_rank: int) -> tuple:
    """Where a layer's areas come in what is said: by the view's list, then any other layer, the more
    specific first by the pack's rank."""
    said = view.get("said", [])
    if layer_id in said:
        return (0, said.index(layer_id), 0)
    return (1, 0, -pack_rank)
