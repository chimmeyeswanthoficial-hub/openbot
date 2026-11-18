#!/usr/bin/env bash
# Linux -> genuine Windows x64 PE executable, using MinGW and the pinned WebView2 SDK.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
: "${WEBVIEW2_SDK:?Set WEBVIEW2_SDK to the extracted Microsoft.Web.WebView2 1.0.2903.40 NuGet package.}"
CACHE="${OPENBOT_BUILD_CACHE:-$HOME/.cache/openbot-control}"
WORK="$CACHE/windows-build"
OUT="$ROOT/releases/windows-x64"
mkdir -p "$WORK" "$OUT"
python3 - "$WEBVIEW2_SDK" "$WORK" "$ROOT" <<'PY'
from pathlib import Path
import re,sys
sdk,work,root=map(Path,sys.argv[1:])
header=(sdk/'build/native/include/WebView2.h').read_text()
# Windows headers are case-insensitive; Debian's MinGW headers are not.
(work/'EventToken.h').write_text('#include <eventtoken.h>\n')
assert 'IID_ICoreWebView2DownloadStartingEventHandler' in header, 'Unexpected SDK header'
rc='''#include <windows.h>
101 RCDATA "%s"
201 ICON "%s"
1 RT_MANIFEST "%s"
1 VERSIONINFO
 FILEVERSION 0,3,0,0
 PRODUCTVERSION 0,3,0,0
 FILEFLAGSMASK 0x3fL
 FILEFLAGS 0
 FILEOS VOS_NT_WINDOWS32
 FILETYPE VFT_APP
BEGIN
 BLOCK "StringFileInfo"
 BEGIN
  BLOCK "040904b0"
  BEGIN
   VALUE "FileDescription", "OpenBot Workspace Light Test\\0"
   VALUE "FileVersion", "0.3.0-local\\0"
   VALUE "ProductName", "OpenBot Workspace Test\\0"
   VALUE "ProductVersion", "0.3.0-local\\0"
   VALUE "OriginalFilename", "OpenBot-Control-Local-x64.exe\\0"
  END
 END
 BLOCK "VarFileInfo"
 BEGIN
  VALUE "Translation", 0x409, 1200
 END
END
'''%((root/'web/index.html').as_posix(),(root/'native/windows/app.ico').as_posix(),(root/'native/windows/app.manifest').as_posix())
(work/'app.rc').write_text(rc)
PY
x86_64-w64-mingw32-windres --codepage=65001 "$WORK/app.rc" -o "$WORK/resources.o"
x86_64-w64-mingw32-g++ -std=c++17 -Os -Wall -Wextra -Wno-unknown-pragmas -Wno-cast-function-type -municode -mwindows -static -static-libgcc -static-libstdc++ -Wl,--dynamicbase,--nxcompat,--high-entropy-va,--no-insert-timestamp,--major-os-version,10,--minor-os-version,0,--major-subsystem-version,10,--minor-subsystem-version,0 -I"$WEBVIEW2_SDK/build/native/include" -I"$WORK" "$ROOT/native/windows/main.cpp" "$WORK/resources.o" -o "$OUT/OpenBot-Control-Local-x64.exe" -lole32 -luuid -lshell32 -lgdi32 -luser32
x86_64-w64-mingw32-strip "$OUT/OpenBot-Control-Local-x64.exe"
cp "$WEBVIEW2_SDK/build/native/x64/WebView2Loader.dll" "$OUT/WebView2Loader.dll"
cp "$WEBVIEW2_SDK/LICENSE.txt" "$OUT/WebView2-LICENSE.txt"
cp "$ROOT/native/windows/README-Windows.txt" "$OUT/README-Windows.txt"
file "$OUT/OpenBot-Control-Local-x64.exe"
x86_64-w64-mingw32-objdump -p "$OUT/OpenBot-Control-Local-x64.exe" | grep -E 'Subsystem|DllCharacteristics|DLL Name|Security Directory'
echo "Built UNSIGNED portable x64 executable: $OUT/OpenBot-Control-Local-x64.exe"
echo 'Requires the current Microsoft Edge WebView2 x64 Runtime. Not Windows-launch-tested by this script.'
