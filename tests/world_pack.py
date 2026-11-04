"""Where the world pack is on this computer, if it is built (never needed in continuous integration)."""
from pathlib import Path


def world_pack_path() -> Path | None:
    try:
        from mapdata.paths import resolve_data_folder

        path = resolve_data_folder().output / "world" / "world.pack"
    except Exception:
        return None
    return path if path.exists() else None
