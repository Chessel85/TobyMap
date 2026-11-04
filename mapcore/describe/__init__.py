"""Announcement templates and wording (architecture 3.4)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

TEMPLATES_FILE = Path(__file__).resolve().parent / "templates.yaml"


@lru_cache(maxsize=1)
def templates() -> dict:
    return yaml.safe_load(TEMPLATES_FILE.read_text(encoding="utf-8"))


def say(template: str, /, **values) -> str:
    """Fill a template. Dotted keys reach into groups: say("panel.within")."""
    node = templates()
    for part in template.split("."):
        node = node[part]
    return node.format(**values) if values else node


@lru_cache(maxsize=1)
def earcon_list() -> tuple[dict, ...]:
    """Every earcon: event, file name, label and meaning (SON-6, SON-8)."""
    return tuple(yaml.safe_load((Path(__file__).resolve().parent / "earcons.yaml").read_text(encoding="utf-8")))
