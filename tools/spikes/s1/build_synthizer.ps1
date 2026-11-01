# Spike S1: build Synthizer 0.12.6 from its source and install it into .venv.
# Synthizer (Unlicense) has no ready-built package for Python 3.14, so it is
# built with Visual Studio 2022's C++ tools. Run from the repository folder:
#   powershell -ExecutionPolicy Bypass -File tools\spikes\s1\build_synthizer.ps1
# It downloads into tools\spikes\s1\downloads and builds in
# tools\spikes\s1\vendor\synthizer-build, neither of which is in git.
$ErrorActionPreference = 'Stop'
$root = Resolve-Path (Join-Path $PSScriptRoot '..\..\..')
$python = Join-Path $root '.venv\Scripts\python.exe'
$downloads = Join-Path $PSScriptRoot 'downloads'
$build = Join-Path $PSScriptRoot 'vendor\synthizer-build'
$sdist = Join-Path $downloads 'synthizer-0.12.6.tar.gz'
$sha256 = 'c5eb8ac7bc0e452d55286f014dc4c8bd973bdeb3edeacb1378bde87c9a4b0130'  # from PyPI

New-Item -ItemType Directory -Force $downloads, $build | Out-Null
if (-not (Test-Path $sdist)) {
    Write-Host 'Downloading the Synthizer 0.12.6 source from PyPI'
    Invoke-WebRequest 'https://files.pythonhosted.org/packages/source/s/synthizer/synthizer-0.12.6.tar.gz' -OutFile $sdist
}
if ((Get-FileHash $sdist -Algorithm SHA256).Hash.ToLower() -ne $sha256) { throw "The download does not match PyPI's hash." }
tar -xzf $sdist -C $build
$src = Join-Path $build 'synthizer-0.12.6'

$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
$vs = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $vs) { throw 'Visual Studio with the C++ tools was not found.' }
$vcvars = Join-Path $vs 'VC\Auxiliary\Build\vcvars64.bat'

Write-Host 'Building Synthizer. This takes a few minutes.'
cmd /c "`"$vcvars`" >nul && `"$python`" -m pip wheel `"$src`" --no-deps -w `"$build`""
if ($LASTEXITCODE) { throw 'The build failed.' }
$wheel = Get-ChildItem $build -Filter 'synthizer-0.12.6-*.whl' | Select-Object -First 1
& $python -m pip install --force-reinstall --no-deps $wheel.FullName
if ($LASTEXITCODE) { throw 'Installing the wheel failed.' }
& $python -c "import synthizer; print('Synthizer', synthizer.__file__)"
Write-Host 'Done. Synthizer is installed in .venv, ready to be added to the S1 demo.'
