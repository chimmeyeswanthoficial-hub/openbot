#!/usr/bin/env bash
# macOS/Xcode only. Simulator build by default, without a signing identity or upload.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [ "$(uname -s)" != Darwin ] || ! command -v xcodebuild >/dev/null; then
    echo 'BLOCKED: iOS compilation requires macOS with Xcode and the iOS SDK.' >&2
    echo 'No .ipa or simulator .app was built here. Source code is not an installer.' >&2
    exit 2
fi
CACHE="${OPENBOT_BUILD_CACHE:-$HOME/Library/Caches/OpenBotControl}"
mkdir -p "$CACHE"
cp "$ROOT/web/index.html" "$ROOT/native/ios/OpenBotControl/index.html"
xcodebuild -version
xcodebuild -project "$ROOT/native/ios/OpenBotControl.xcodeproj" -scheme OpenBotControl -configuration Debug -sdk iphonesimulator -destination 'generic/platform=iOS Simulator' -derivedDataPath "$CACHE/DerivedData" CODE_SIGNING_ALLOWED=NO build
printf '\nUnsigned SIMULATOR app (not installable on an iPhone):\n%s\n' "$CACHE/DerivedData/Build/Products/Debug-iphonesimulator/OpenBotControl.app"
echo 'For an iPhone, open the project in Xcode, choose your own signing team, then build to your registered device.'
echo 'App Store / TestFlight archive, signing, export and upload require a separate human-authorized release process.'
