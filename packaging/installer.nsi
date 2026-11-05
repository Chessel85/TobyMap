; NSIS installer for TobyMap (AD-20, DEL-5).
; Built by packaging/build.ps1:  makensis /DVERSION=x.y.z packaging\installer.nsi
;
; Installs for the current user only, into the user's own Programs folder, so
; no administrator prompt is needed. Standard Windows dialogs throughout, which
; NVDA reads: Welcome, Install location, Installing, Finished.
; The uninstaller removes only the files it installed.

Unicode true
!include "MUI2.nsh"

!ifndef VERSION
  !define VERSION "0.0.0"
!endif
!define APP "TobyMap"
!define UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP}"

Name "${APP} ${VERSION}"
OutFile "..\dist_installer\${APP}-${VERSION}-setup.exe"
InstallDir "$LOCALAPPDATA\Programs\${APP}"
InstallDirRegKey HKCU "Software\${APP}" "InstallDir"
RequestExecutionLevel user
SetCompressor /SOLID lzma
BrandingText "${APP} ${VERSION}"

VIProductVersion "${VERSION}.0"
VIAddVersionKey "ProductName" "${APP}"
VIAddVersionKey "FileDescription" "${APP} installer"
VIAddVersionKey "FileVersion" "${VERSION}"
VIAddVersionKey "ProductVersion" "${VERSION}"
VIAddVersionKey "LegalCopyright" "GNU General Public License version 3"

!define MUI_ABORTWARNING
!define MUI_WELCOMEPAGE_TEXT "This installs ${APP} ${VERSION}, the accessible map, for you on this computer.$\r$\n$\r$\nThis is the Phase 1 walking skeleton: you step round the world and hear where you are.$\r$\n$\r$\nChoose Next to continue."
!define MUI_FINISHPAGE_RUN "$INSTDIR\${APP}.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Start ${APP} now"
!define MUI_FINISHPAGE_SHOWREADME ""
!define MUI_FINISHPAGE_SHOWREADME_NOTCHECKED
!define MUI_FINISHPAGE_SHOWREADME_TEXT "Put a shortcut on the desktop"
!define MUI_FINISHPAGE_SHOWREADME_FUNCTION DesktopShortcut

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

Function DesktopShortcut
  CreateShortcut "$DESKTOP\${APP}.lnk" "$INSTDIR\${APP}.exe"
FunctionEnd

Section "Install"
  SetOutPath "$INSTDIR"
  ; An older copy's program files are replaced, never mixed with the new ones.
  RMDir /r "$INSTDIR\_internal"
  File "..\dist\${APP}\${APP}.exe"
  File /r "..\dist\${APP}\_internal"
  WriteUninstaller "$INSTDIR\Uninstall ${APP}.exe"
  CreateShortcut "$SMPROGRAMS\${APP}.lnk" "$INSTDIR\${APP}.exe"
!ifdef PACK
  ; The base pack lite, into TobyMap's own folder in your application data folder, where the program looks (AD-18).
  SetOutPath "$APPDATA\${APP}\packs"
  File "${PACK}"
  SetOutPath "$INSTDIR"
!endif

  WriteRegStr HKCU "Software\${APP}" "InstallDir" "$INSTDIR"
  WriteRegStr HKCU "${UNINST_KEY}" "DisplayName" "${APP}"
  WriteRegStr HKCU "${UNINST_KEY}" "DisplayVersion" "${VERSION}"
  WriteRegStr HKCU "${UNINST_KEY}" "Publisher" "TobyMap project"
  WriteRegStr HKCU "${UNINST_KEY}" "DisplayIcon" "$INSTDIR\${APP}.exe"
  WriteRegStr HKCU "${UNINST_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${UNINST_KEY}" "UninstallString" '"$INSTDIR\Uninstall ${APP}.exe"'
  WriteRegDWORD HKCU "${UNINST_KEY}" "NoModify" 1
  WriteRegDWORD HKCU "${UNINST_KEY}" "NoRepair" 1
SectionEnd

Section "Uninstall"
  ; Only what the installer put there. The folder itself is removed only if empty,
  ; so nothing else the user keeps in it is ever deleted.
  Delete "$INSTDIR\${APP}.exe"
  Delete "$INSTDIR\Uninstall ${APP}.exe"
  RMDir /r "$INSTDIR\_internal"
  RMDir "$INSTDIR"
!ifdef PACK
  ; The pack the installer put there, nothing else. Your settings file stays.
  Delete "$APPDATA\${APP}\packs\world.pack"
  Delete "$APPDATA\${APP}\packs\world.pack.sha256"
  RMDir "$APPDATA\${APP}\packs"
!endif
  Delete "$SMPROGRAMS\${APP}.lnk"
  Delete "$DESKTOP\${APP}.lnk"
  DeleteRegKey HKCU "${UNINST_KEY}"
  DeleteRegKey HKCU "Software\${APP}"
SectionEnd
