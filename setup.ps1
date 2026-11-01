# One-command development set-up for Windows (P0-T3).
# Run from the repository folder:  .\setup.ps1
# Add -Pipeline to also install the pipeline libraries, and -Build for the installer tools.
param([switch]$Pipeline, [switch]$Build)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path .venv)) {
    Write-Output "Creating the Python 3.14 virtual environment in .venv"
    py -3.14 -m venv .venv
}
$py = ".venv\Scripts\python.exe"
& $py -m pip install --upgrade pip --quiet

$req = "requirements-dev.txt"
if ($Pipeline) { $req = "requirements-pipeline.txt" }
Write-Output "Installing $req"
& $py -m pip install -r $req --quiet
if ($Build) {
    Write-Output "Installing requirements-build.txt"
    & $py -m pip install -r requirements-build.txt --quiet
}

Write-Output "Installing the Chromium and Firefox browsers for the web tests"
& $py -m playwright install chromium firefox

Write-Output "Fetching Pyodide and the NVDA Controller Client"
& $py tools\fetch_vendor.py

if (-not (Test-Path mapdata\config\paths.yaml)) {
    Write-Output "No local paths file yet. Copy mapdata\config\paths.example.yaml to mapdata\config\paths.yaml and set data_folder."
}

Write-Output "Running the licence check"
& $py tools\check_licences.py | Select-String -Pattern "^FAIL|passed|failed"
Write-Output "Set-up finished. Run the tests with: .venv\Scripts\python.exe -m pytest"
