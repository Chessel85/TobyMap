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

## Run the tests

* Python tests: `.venv\Scripts\python.exe -m pytest --ignore=tests/web`
* Browser tests: `.venv\Scripts\python.exe -m pytest tests/web --browser chromium --browser firefox`

## Kept out of git

These are kept out of git because they are personal or large:

* the virtual environment;
* `mapdata\config\paths.yaml`;
* packs and OSM files;
* sound and voice files;
* build output.

The PO's original "Solution Design" folder is also kept out. Its documents now live in `docs/design`.
