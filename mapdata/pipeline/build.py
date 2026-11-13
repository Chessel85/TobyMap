"""mapdata build <pack>: run the stages named in the pack's settings file (architecture 8.2, 8.3, DMT-1).

Each stage's results are kept in the working folder, in a folder named by
the stage and a fingerprint of everything that could change them: the
stage's settings, the pack's layers, the fingerprint of the stage before,
the sources it reads, and the version of its code. If a folder with that
fingerprint is already finished, the stage is skipped. A stage's folder is
finished when its "finished.json" is written, last, so a stage stopped
part-way is run again.

The last stage writes the pack, which is then copied to the output folder,
with its checksum file and, beside them, the build's log.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import time
from dataclasses import dataclass, field
from importlib import import_module
from pathlib import Path

from mapdata.paths import CONFIG_DIR, DataFolders
from mapdata.pipeline import ledger as ledgermod
from mapdata.pipeline.errors import BuildStopped
from mapdata.pipeline.progress import Progress, duration_words
from mapdata.pipeline.settings import REPO, PackSettings, Source, load_pack, stage_sources
from mapdata.pipeline.switch import PAUSED_EXIT, Paused, Switch

ENGINE_VERSION = "pipeline-1"
FINISHED = "finished.json"


@dataclass(frozen=True)
class StageKind:
    title: str              # how progress lines describe it, such as "reading the samples"
    module: str             # the module with run(ctx)
    code: tuple[str, ...]   # the modules whose code is in the fingerprint
    areas_only: bool = False   # it makes or reads only the area layers, so only they are in its fingerprint


STAGES = {
    "samples": StageKind("reading the samples", "mapdata.stages.samples",
                         ("mapdata.stages.samples",)),
    "water": StageKind("taking the land out of the water layers", "mapdata.stages.water",
                       ("mapdata.stages.water",)),
    "osm-areas": StageKind("reading the countries and divisions from the planet file", "mapdata.stages.osm_areas",
                           ("mapdata.stages.osm_areas", "mapdata.stages.boundaries", "mapdata.stages.held_twice",
                            "mapdata.stages.overlaps"), areas_only=True),
    "squares": StageKind("building the grid squares", "mapdata.stages.squares",
                         ("mapdata.stages.squares", "mapdata.stages.grid", "mapdata.stages.seas"), areas_only=True),
    "join": StageKind("joining the grid squares into areas", "mapdata.stages.join",
                      ("mapdata.stages.join", "mapdata.stages.grid", "mapdata.stages.geodesy"), areas_only=True),
    "osm-places": StageKind("reading the named places from the planet file", "mapdata.stages.osm_places",
                            ("mapdata.stages.osm_places",)),
    "graticule": StageKind("writing the graticule and special lines", "mapdata.stages.graticule",
                           ("mapdata.stages.graticule",)),
    "distant-parts": StageKind("making countries' distant parts areas of their own", "mapdata.stages.distant_parts",
                               ("mapdata.stages.distant_parts", "mapdata.stages.continents", "mapdata.stages.clip")),
    "continents": StageKind("building the continents from the countries", "mapdata.stages.continents",
                            ("mapdata.stages.continents",)),
    "osm-layer": StageKind("reading a layer of named areas from the planet file", "mapdata.stages.osm_layer",
                           ("mapdata.stages.osm_layer", "mapdata.stages.osm_places")),
    "osm-rivers": StageKind("reading the rivers from the planet file", "mapdata.stages.osm_rivers",
                            ("mapdata.stages.osm_rivers",)),
    "osm-lines": StageKind("reading the roads and railways from the planet file", "mapdata.stages.osm_lines",
                           ("mapdata.stages.osm_lines", "mapdata.stages.osm_rivers")),
    "physical": StageKind("building the mountain ranges and physical regions", "mapdata.stages.physical",
                          ("mapdata.stages.physical", "mapdata.stages.land")),
    "disputes": StageKind("making the disputed areas", "mapdata.stages.disputes",
                          ("mapdata.stages.disputes",)),
    "relationships": StageKind("working out what each feature is inside, beside and crossing",
                               "mapdata.stages.relationships", ("mapdata.stages.relationships", "mapdata.stages.geodesy")),
    "wikidata": StageKind("taking the facts of each feature from Wikidata", "mapdata.stages.wikidata",
                          ("mapdata.stages.wikidata",)),
    "checks": StageKind("looking up the check places in the pack", "mapdata.stages.checks",
                        ("mapdata.stages.checks", "mapdata.stages.lookup")),
    "write": StageKind("writing the pack", "mapdata.stages.write",
                       ("mapdata.stages.write", "mapdata.stages.pack_write", "mapdata.stages.relationships", "mapdata.stages.drawing_levels", "mapdata.stages.antimeridian",
                        "mapdata.stages.geodesy", "mapcore.geo.geodesy", "mapcore.packs.pack",
                        "mapcore.packs.coords", "mapcore.packs.tiles")),
}


@dataclass
class StageContext:
    """What a stage is given: its settings, the folder of the stage before, its own folder, and the build."""
    pack: PackSettings
    settings: dict
    number: int
    previous: Path | None
    folder: Path
    folders: DataFolders | None
    progress: Progress
    ledger: ledgermod.Ledger
    workers: int
    source_paths: dict[str, Path] = field(default_factory=dict)
    switch: Switch | None = None
    # The folder of each kind of stage run before this one, the latest of each kind, such as "osm-areas", for a
    # stage that needs what an earlier stage kept besides the features, such as the outlines as read (P3-T2c).
    earlier: dict[str, Path] = field(default_factory=dict)

    def claim(self, path: Path) -> Path:
        return self.ledger.claim(path)

    def source(self, key: str) -> tuple[Source, Path]:
        return self.pack.sources[key], self.source_paths[key]

    def check_switch(self, where: str) -> None:
        """For long stages, between jobs: stop cleanly if continue.txt says no. Save each finished job's
        results first, so the stage carries on from there when it is run again."""
        if self.switch is not None:
            self.switch.check(where)


def code_version(modules: tuple[str, ...]) -> str:
    h = hashlib.sha256(ENGINE_VERSION.encode())
    for name in modules:
        path = Path(import_module(name).__file__)
        h.update(name.encode())
        h.update(path.read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()


def resolve_sources(pack: PackSettings, folders: DataFolders | None) -> dict[str, Path]:
    out = {}
    for key, source in pack.sources.items():
        path = source.path(folders)
        if path is None:
            where = (f"It should be in the repository at {source.repo}." if source.repo
                     else f"Run: python -m mapdata fetch {key}")
            raise BuildStopped(f"The source {key}, {source.name}, is not in the data folder. {where}")
        out[key] = path
    return out


def fingerprint(pack: PackSettings, stage: dict, previous: str, source_prints: dict[str, str]) -> str:
    kind = STAGES[stage["stage"]]
    layers = pack.layers
    settings = {k: v for k, v in pack.data.items() if k != "stages"}
    if kind.areas_only:
        # Adding a layer of lines or points, such as the graticule (P2-T10), must not
        # make the countries and divisions again: hours of reading the planet file.
        # Nor must a layer of areas that a stage of its own makes, such as the continents (P3-T1e): only the
        # layers the grid squares and the join make are in these stages' fingerprints.
        layers = {k: v for k, v in layers.items() if v.geometry == "area" and not v.made_by}
        groups = {v.group_file for v in layers.values()}
        settings["layer_groups"] = [g for g in settings.get("layer_groups") or [] if g in groups]
    parts = {
        "stage": stage,
        "layers": {k: v.build_fields() for k, v in layers.items()},
        "pack": settings,
        "previous": previous,
        "sources": {k: source_prints[k] for k in stage_sources(stage)},
        "code": code_version(kind.code),
    }
    extra = getattr(import_module(kind.module), "fingerprint_extra", None)
    extra = extra(stage) if extra is not None else None
    if extra is not None:   # what a stage reads besides its settings and sources, such as the counties record
        parts["extra"] = extra
    if stage["stage"] == "write":   # only the pack's writing uses how layers are shown and sounded (SCP-7)
        parts["layer_definitions"] = [v.definition() for v in pack.layers.values()]
    return hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()


def pack_file_name(name: str) -> str:
    return f"{name}.pack"


def free_mb(path: Path) -> float:
    path = Path(path)
    while not path.exists():
        path = path.parent
    return shutil.disk_usage(path).free / 1e6


def build(name: str, folders: DataFolders, workers: int = 1, say=print, clock=time.monotonic,
          config_dir: Path = CONFIG_DIR, switch: Switch | None = None) -> int:
    """Returns 0 when the pack is built, 1 when the build stopped, and 3 when continue.txt paused it."""
    progress = Progress(say, clock)
    try:
        return _build(name, folders, workers, progress, config_dir, switch or Switch())
    except Paused as stop:
        progress.always(stop.message)
        return PAUSED_EXIT
    except BuildStopped as stop:
        progress.always(f"The build stopped. {stop.message}")
        return 1
    except Exception as error:
        # Written to the log as well, so a fault is never only on a screen nobody is watching.
        import traceback

        progress.always(f"The build stopped because of a fault in mapdata: {type(error).__name__}: {error}. "
                        "The details are in the log.")
        progress.log(traceback.format_exc())
        raise
    finally:
        progress.close()


def _build(name: str, folders: DataFolders, workers: int, progress: Progress, config_dir: Path,
           switch: Switch) -> int:
    # Everything that can stop the build is checked before any work (DMT-6, DMT-7).
    pack = load_pack(name, config_dir)
    if not folders.root.is_dir():
        raise BuildStopped(f"The data folder, {folders.root}, cannot be reached. If it is on an external drive, "
                           "connect the drive, then build again. mapdata check says more.")
    needed = float(pack.data.get("space_needed_mb", 100))
    free = free_mb(folders.own)
    if free < needed:
        raise BuildStopped(f"The pack {name} needs about {needed:,.0f} MB, and the drive holding {folders.own} has "
                           f"{free:,.0f} MB free. Free some space on that drive, then build again.")
    ledger = ledgermod.Ledger(folders.own)
    out_dir = folders.output / name
    log_path = ledger.claim(out_dir / f"{name} build log.txt")
    progress.open_log(log_path)
    progress.start_heartbeat()
    source_paths = resolve_sources(pack, folders)
    source_prints = {k: pack.sources[k].fingerprint(p) for k, p in source_paths.items()}

    progress.line(f"Building the pack {name}: {pack.data['title']}")
    shown = pack.path.relative_to(REPO).as_posix() if REPO in pack.path.parents else pack.path
    progress.log(f"Settings: {shown}. Workers: {workers}.")
    for key, source in pack.sources.items():
        progress.log(f"Source {key}: {source.name}, {source.licence}, dated "
                     f"{source.data_date(source_paths[key])}, from {source_paths[key]}.")

    total = len(pack.stages)
    previous_print, previous_folder = "", None
    ran, skipped = [], []
    stage_folders: list[Path] = []
    earlier: dict[str, Path] = {}
    for n, stage in enumerate(pack.stages, 1):
        if previous_folder is not None:
            stage_folders.append(previous_folder)
        kind_name = stage["stage"]
        if kind_name not in STAGES:
            raise BuildStopped(f"Stage {n} in {pack.path.name} is {kind_name}, which mapdata does not know. "
                               f"The stages are: {', '.join(sorted(STAGES))}.")
        kind = STAGES[kind_name]
        fp = fingerprint(pack, stage, previous_print, source_prints)
        folder = folders.working / name / f"{n:02d}-{kind_name}-{fp[:16]}"
        if (folder / FINISHED).is_file():
            skipped.append(kind_name)
            progress.line(f"Stage {n} of {total}, {kind.title}: skipped, as nothing it uses has changed.")
        else:
            switch.check(f"before stage {n} of {total}, {kind.title}")
            progress.line(f"Stage {n} of {total}: {kind.title}.")
            start = time.perf_counter()
            ctx = StageContext(pack, stage, n, previous_folder, folder, folders, progress, ledger, workers,
                               source_paths, switch, dict(earlier))
            folder.mkdir(parents=True, exist_ok=True)
            import_module(kind.module).run(ctx)
            took = time.perf_counter() - start
            ledger.claim(folder / FINISHED).write_text(
                json.dumps({"stage": kind_name, "fingerprint": fp, "seconds": round(took, 1)}, indent=1) + "\n",
                encoding="utf-8", newline="\n")
            ran.append((kind_name, took))
            progress.line(f"Stage {n} of {total} finished in {duration_words(took)}.")
        previous_print, previous_folder = fp, folder
        earlier[kind_name] = folder

    stage_folders.append(previous_folder)
    built = next((f / pack_file_name(name) for f in reversed(stage_folders) if (f / pack_file_name(name)).is_file()),
                 previous_folder / pack_file_name(name))
    if not built.is_file():
        raise BuildStopped(f"The last stage in {pack.path.name} did not write a pack. Put a 'write' stage near the end, followed only by checks.")
    target = out_dir / pack_file_name(name)
    from mapcore.packs.pack import checksum_path

    for src, dst in ((built, target), (checksum_path(built), checksum_path(target))):
        if not dst.is_file() or dst.read_bytes() != src.read_bytes():
            shutil.copyfile(src, ledger.claim(dst))
    summary(pack, target, ran, skipped, progress, log_path)
    return 0


def summary(pack: PackSettings, target: Path, ran: list, skipped: list, progress: Progress, log_path: Path) -> None:
    from mapcore.packs.pack import Pack

    with Pack(target, check_app=False) as p:
        counts: dict[str, int] = {}
        for n in range(p.manifest["features"]["count"]):
            layer = p.feature(n)["layer"]
            counts[layer] = counts.get(layer, 0) + 1
        layer_names = {layer["id"]: layer["name"] for layer in p.layers}
        geometry = {layer["id"]: layer.get("geometry", "area") for layer in p.layers}
        built = p.manifest["built"]
    progress.always(f"Summary of the build of {pack.name}:")
    progress.always(f"The pack is {target}, {target.stat().st_size / 1e6:.2f} MB, built from sources dated up to "
                    f"{built}.")
    for layer, count in counts.items():
        # "point" is a corner on an outline in the glossary, so a point layer's features are "places".
        word = {"line": "line", "point": "place"}.get(geometry.get(layer, "area"), "area")
        progress.always(f"{layer_names.get(layer, layer)}: {count} {word}{'s' if count != 1 else ''}.")
    if ran:
        progress.always("Stages run: " + ", ".join(f"{k} in {duration_words(t)}" for k, t in ran) + ".")
    if skipped:
        progress.always(f"Stages skipped, as nothing they use had changed: {', '.join(skipped)}.")
    progress.always(f"Time taken: {duration_words(progress.elapsed())}. The full log is {log_path}.")


def build_waiting(argv: list[str], switch: Switch | None = None, say=print, poll_s: float = 30.0,
                  sleep=time.sleep, run=None) -> int:
    """mapdata build --wait-for-yes: run the build in its own process; if continue.txt pauses it, wait,
    using almost no memory or processor, until the file says yes, then run it again. Finished stages are
    skipped, so it carries on where it stopped."""
    import subprocess
    import sys

    switch = switch or Switch()
    run = run or (lambda: subprocess.run([sys.executable, "-m", "mapdata", *argv]).returncode)
    while True:
        if switch.says_no():
            say(f"Waiting, as the first line of {switch.path.name} is not yes. The build starts when its first line is yes.")
            while switch.says_no():
                sleep(poll_s)
            say(f"{switch.path.name} says yes, so the build starts.")
        code = run()
        if code != PAUSED_EXIT:
            return code
