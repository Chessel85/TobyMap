"""Where the pipeline's data folder is (architecture AD-18, DMT-7).

No drive letter or personal folder is built in. The data folder is taken from,
in order:

1. the --data option on the command line,
2. the MAPDATA_ROOT environment variable,
3. the local paths file, mapdata/config/paths.yaml, which is not in git.

If none is set, DataFolderNotSet is raised with a message that explains how to
set it.

The data folder holds the large source files, such as the planet .osm.pbf and
.gol files, which mapdata only reads. Everything mapdata creates goes inside
one subfolder, "tobymap", so nothing else in the data folder is ever
overwritten (DP75).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parent / "config"
LOCAL_PATHS_FILE = CONFIG_DIR / "paths.yaml"
ENV_VAR = "MAPDATA_ROOT"


class DataFolderNotSet(RuntimeError):
    """Raised when no data folder has been given anywhere."""


@dataclass(frozen=True)
class DataFolders:
    root: Path
    where_from: str

    @property
    def own(self) -> Path:
        """The only folder mapdata writes into."""
        return self.root / "tobymap"

    @property
    def downloads(self) -> Path:
        return self.own / "downloads"

    @property
    def working(self) -> Path:
        return self.own / "working"

    @property
    def output(self) -> Path:
        return self.own / "output"


def _read_local_file(path: Path) -> str | None:
    """Read data_folder from the local paths file.

    The file is a tiny YAML subset, "data_folder: <path>", read without a YAML
    library so mapdata can explain a missing setting before any heavy import.
    """
    if not path.is_file():
        return None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line.startswith("data_folder:"):
            value = line.split(":", 1)[1].strip().strip("'\"")
            return value or None
    return None


HOW_TO_SET = (
    "The data folder is not set. Set it in one of these ways:\n"
    "1. Add --data followed by the folder, for example: python -m mapdata --data <folder> status\n"
    f"2. Set the {ENV_VAR} environment variable to the folder.\n"
    "3. Copy mapdata\\config\\paths.example.yaml to mapdata\\config\\paths.yaml "
    "and put the folder after data_folder."
)


def resolve_data_folder(
    cli_value: str | None = None,
    environ: dict[str, str] | None = None,
    local_file: Path | None = None,
) -> DataFolders:
    environ = os.environ if environ is None else environ
    local_file = LOCAL_PATHS_FILE if local_file is None else local_file
    if cli_value:
        return DataFolders(Path(cli_value), "the --data option")
    env_value = environ.get(ENV_VAR, "").strip()
    if env_value:
        return DataFolders(Path(env_value), f"the {ENV_VAR} environment variable")
    file_value = _read_local_file(local_file)
    if file_value:
        return DataFolders(Path(file_value), f"the local paths file, {local_file.name}")
    raise DataFolderNotSet(HOW_TO_SET)
