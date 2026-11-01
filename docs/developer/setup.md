# Developer set-up

How to set up a Windows laptop to work on TobyMap.

## What you need first

* Windows 10 or 11.
* Python 3.14, from python.org. The `py` launcher must be installed, which it is by default.
* Git.
* NSIS 3, only if you build the Windows installer. It is installed in the usual place, C:\Program Files (x86)\NSIS.

## Set up

1. Open PowerShell in the repository folder.
2. Run `.\setup.ps1 -Pipeline -Build`.

The script does the following:

* creates a virtual environment in `.venv`;
* installs the Python packages;
* downloads the Chromium and Firefox browsers used by the web tests;
* runs the licence check.

Leave out `-Pipeline` if you will not build data, and leave out `-Build` if you will not build the installer.

## The data folder

The pipeline needs a data folder for large files. It is never assumed to be on any particular drive (AD-18). Give it in one of three ways. The first one that is set wins.

1. The `--data` option, for example `.venv\Scripts\python.exe -m mapdata --data <folder> status`.
2. The `MAPDATA_ROOT` environment variable.
3. The local paths file. Copy `mapdata\config\paths.example.yaml` to `mapdata\config\paths.yaml`, and put your folder after `data_folder:`.

The data folder holds the source files, such as the planet .osm.pbf and .gol files. mapdata only reads them. Everything mapdata creates goes into a subfolder called `tobymap`, which holds:

* downloads
* working
* output

Run `.venv\Scripts\python.exe -m mapdata status` to check the setting.

## Third-party files fetched by a script

Some files are downloaded rather than kept in git. `setup.ps1` fetches them, or run `.venv\Scripts\python.exe tools\fetch_vendor.py`. Each download is checked against a pinned checksum.

* Pyodide, which runs Python in the browser, with NumPy and PyYAML for it. It goes into `web\vendor\pyodide`, about 17 MB.
* The NVDA Controller Client, for Braille-only messages on the desktop. It goes into `desktop\vendor`.

## Run the application

* Desktop: `.venv\Scripts\python.exe -m desktop`
* Web: `.venv\Scripts\python.exe tools\serve_web.py`. This copies the core into `web\py`, serves the web folder at http://127.0.0.1:8765 and opens it in your browser. Press Ctrl+C in that window to stop.

## Build the Windows installer

Run `.\packaging\build.ps1`. It needs NSIS and `setup.ps1 -Build`. The results go in `dist_installer`:

* `TobyMap-<version>-setup.exe`, the installer;
* `TobyMap-<version>-portable.zip`, the same program to unzip and run anywhere.

Continuous integration also builds both on every push. Download them from the run's Artifacts section on GitHub.

## Run the tests

* Python tests: `.venv\Scripts\python.exe -m pytest --ignore=tests/web`
* Browser tests: `.venv\Scripts\python.exe -m pytest tests/web --browser chromium --browser firefox`. These need Pyodide in `web\vendor`. Each test starts Pyodide afresh, so the browser tests take about five minutes.

## Kept out of git

These are kept out of git because they are personal or large:

* the virtual environment;
* `mapdata\config\paths.yaml`;
* packs and OSM files;
* sound and voice files;
* build output;
* the fetched files in `web\vendor` and `desktop\vendor`, and the staged core in `web\py`.

The PO's original "Solution Design" folder is also kept out. Its documents now live in `docs/design`.
