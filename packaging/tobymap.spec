# PyInstaller recipe for the TobyMap desktop application (AD-20).
# Built by packaging/build.ps1:  pyinstaller packaging/tobymap.spec
# One folder, not one file: it starts faster and the installer copies it whole.
from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent

datas = []
for pattern in ("*.yaml", "data/*.json"):
    for path in (ROOT / "mapcore").rglob(pattern):
        datas.append((str(path), str(path.parent.relative_to(ROOT))))
datas.append((str(ROOT / "version.txt"), "."))
for name in ("nvdaControllerClient.dll", "nvdaControllerClient-license.txt"):
    path = ROOT / "desktop" / "vendor" / name
    if not path.is_file():
        raise SystemExit(f"{path} is missing. Run: python tools/fetch_vendor.py --nvda")
    datas.append((str(path), "desktop/vendor"))
datas.append((str(ROOT / "LICENSE"), "."))
datas.append((str(ROOT / "packaging" / "THIRD_PARTY_NOTICES.txt"), "."))

# Qt modules the desktop shell never uses, left out to keep the download small.
excludes = [
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick", "PySide6.QtWebChannel",
    "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuickWidgets", "PySide6.QtQuick3D", "PySide6.Qt3DCore",
    "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets", "PySide6.QtPdf", "PySide6.QtPdfWidgets",
    "PySide6.QtCharts", "PySide6.QtDataVisualization", "PySide6.QtGraphs", "PySide6.QtNetwork",
    "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtSvg", "PySide6.QtOpenGL", "PySide6.QtOpenGLWidgets",
    "PySide6.QtBluetooth", "PySide6.QtPositioning", "PySide6.QtLocation", "PySide6.QtSerialPort",
    "tkinter", "unittest", "pydoc", "playwright", "pytest", "pytestqt", "shapely", "mapdata",
]

a = Analysis(
    [str(ROOT / "packaging" / "launch.py")],
    pathex=[str(ROOT)],
    datas=datas,
    hiddenimports=[],
    excludes=excludes,
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="TobyMap",
    console=False,
    version=str(ROOT / "packaging" / "version_info.txt"),
)
coll = COLLECT(exe, a.binaries, a.datas, name="TobyMap")
