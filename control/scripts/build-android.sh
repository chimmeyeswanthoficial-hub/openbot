#!/usr/bin/env bash
# No Gradle or downloaded runtime dependencies. Build with official Android tools.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
: "${ANDROID_HOME:?Set ANDROID_HOME to an Android SDK with platform android-35 and build-tools 35.0.0.}"
SDK="$ANDROID_HOME"
BT="$SDK/build-tools/35.0.0"
PLATFORM="$SDK/platforms/android-35/android.jar"
WORK="${OPENBOT_BUILD_CACHE:-$HOME/.cache/openbot-control}/android-build"
KEY="${OPENBOT_BUILD_CACHE:-$HOME/.cache/openbot-control}/keys/demo-only.pk8"
CERT="${OPENBOT_BUILD_CACHE:-$HOME/.cache/openbot-control}/keys/demo-only.x509.pem"
OUT="$ROOT/releases/OpenBot-Control-Local-android.apk"
for tool in aapt2 d8 zipalign apksigner; do test -x "$BT/$tool" || { echo "Missing $BT/$tool" >&2; exit 1; }; done
test -f "$PLATFORM"
mkdir -p "$WORK/classes" "$WORK/dex" "$WORK/assets" "$ROOT/releases" "$(dirname "$KEY")"
# Delete only known generated files inside this client's cache, never workspace state.
find "$WORK/classes" -type f -name '*.class' -delete
find "$WORK/dex" -type f -name '*.dex' -delete
cp "$ROOT/web/index.html" "$WORK/assets/index.html"
"$BT/aapt2" compile --dir "$ROOT/native/android/res" -o "$WORK/resources.zip"
"$BT/aapt2" link -o "$WORK/resources.apk" -I "$PLATFORM" --manifest "$ROOT/native/android/AndroidManifest.xml" --min-sdk-version 28 --target-sdk-version 35 -A "$WORK/assets" "$WORK/resources.zip"
find "$ROOT/native/android/src" -name '*.java' -print > "$WORK/java-sources.txt"
javac -encoding UTF-8 --release 8 -classpath "$PLATFORM" -d "$WORK/classes" @"$WORK/java-sources.txt"
find "$WORK/classes" -name '*.class' -print > "$WORK/dex-inputs.txt"
"$BT/d8" --min-api 28 --lib "$PLATFORM" --output "$WORK/dex" @"$WORK/dex-inputs.txt"
cp "$WORK/resources.apk" "$WORK/unsigned.apk"
(cd "$WORK/dex" && zip -q -X "$WORK/unsigned.apk" classes.dex)
"$BT/zipalign" -f -p 4 "$WORK/unsigned.apk" "$WORK/aligned.apk"
if [ ! -f "$KEY" ] || [ ! -f "$CERT" ]; then
    (umask 077; openssl req -x509 -newkey rsa:2048 -nodes -keyout "$KEY.pem" -out "$CERT" -days 3650 -subj '/CN=OpenBot Local Demo Only/OU=Not a release key/O=Local Preview/C=IN'; openssl pkcs8 -topk8 -inform PEM -outform DER -in "$KEY.pem" -out "$KEY" -nocrypt)
fi
# Generated, self-signed demo key is NOT a release-signing identity. No key in sources.
"$BT/apksigner" sign --key "$KEY" --cert "$CERT" --v1-signing-enabled false --v2-signing-enabled true --v3-signing-enabled true --v4-signing-enabled false --out "$OUT" "$WORK/aligned.apk"
"$BT/apksigner" verify --verbose --print-certs "$OUT"
"$BT/zipalign" -c -p 4 "$OUT"
"$BT/aapt" dump badging "$OUT"
echo "Built DEMO-KEY-SIGNED sideload preview: $OUT"
echo 'Not a Play Store release. Not device-tested by this build script.'
