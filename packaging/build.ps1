# Build the Windows installer and the portable zip (AD-20).
# Run from the repository folder, after .\setup.ps1 -Build:
#   .\packaging\build.ps1
# Results, in dist_installer:
#   TobyMap-<version>-setup.exe   the installer
#   TobyMap-<version>-portable.zip   the same program, to unzip and run anywhere
param([string]$Pack = "")
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

$py = ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }  # continuous integration has no venv
$version = (Get-Content version.txt -Raw).Trim()
$parts = ($version.Split(".") + @("0", "0", "0"))[0..3] -join ", "

$makensis = (Get-Command makensis -ErrorAction SilentlyContinue).Source
if (-not $makensis) {
    foreach ($candidate in "${env:ProgramFiles(x86)}\NSIS\makensis.exe", "$env:ProgramFiles\NSIS\makensis.exe") {
        if (Test-Path $candidate) { $makensis = $candidate; break }
    }
}
if (-not $makensis) { throw "NSIS is not installed. Install it from https://nsis.sourceforge.io, then run this again." }

Write-Output "Making the placeholder earcons that are not there yet"
& $py tools\make_placeholder_sounds.py
if ($LASTEXITCODE -ne 0) { throw "make_placeholder_sounds failed" }

Write-Output "Fetching the NVDA Controller Client, the KEMAR responses and the Alba voice if needed"
& $py tools\fetch_vendor.py --nvda --kemar --voice
if ($LASTEXITCODE -ne 0) { throw "fetch_vendor failed" }

Write-Output "Writing the version information for TobyMap $version"
@"
VSVersionInfo(
  ffi=FixedFileInfo(filevers=($parts), prodvers=($parts)),
  kids=[
    StringFileInfo([StringTable('080904B0', [
      StringStruct('ProductName', 'TobyMap'),
      StringStruct('FileDescription', 'TobyMap, the accessible map'),
      StringStruct('FileVersion', '$version'),
      StringStruct('ProductVersion', '$version'),
      StringStruct('LegalCopyright', 'GNU General Public License version 3')])]),
    VarFileInfo([VarStruct('Translation', [2057, 1200])])
  ]
)
"@ | Set-Content packaging\version_info.txt -Encoding utf8

Write-Output "Running PyInstaller"
& $py -m PyInstaller --noconfirm --clean --log-level WARN --distpath dist --workpath build packaging\tobymap.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

New-Item -ItemType Directory -Force dist_installer | Out-Null
# The base pack lite goes in the installer when it is given: -Pack <path to world.pack>. It is installed for the
# current user into TobyMap's own folder in the application data folder. Without it, the installer holds the program only.
$defines = @("/DVERSION=$version")
if ($Pack) {
    if (-not (Test-Path $Pack)) { throw "The pack $Pack is not there." }
    $defines += "/DPACK=$((Resolve-Path $Pack).Path)"
}
Write-Output "Building the installer with NSIS"
& $makensis /V2 @defines packaging\installer.nsi
if ($LASTEXITCODE -ne 0) { throw "NSIS failed" }

Write-Output "Making the portable zip"
$zip = "dist_installer\TobyMap-$version-portable.zip"
if (Test-Path $zip) { Remove-Item $zip }
Compress-Archive -Path dist\TobyMap -DestinationPath $zip

foreach ($file in Get-ChildItem dist_installer -Filter "TobyMap-$version-*") {
    Write-Output ("Built {0}, {1:N1} MB" -f $file.FullName, ($file.Length / 1MB))
}
