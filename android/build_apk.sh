#!/usr/bin/env bash
# Builds CasterHub.apk with the plain Android SDK tools (no Gradle, works offline).
# Usage: bash build_apk.sh   (expects ../web/index.html to exist)
set -euo pipefail
cd "$(dirname "$0")"
SDK="${ANDROID_HOME:-$LOCALAPPDATA/Android/Sdk}"
BT="$SDK/build-tools/$(ls "$SDK/build-tools" | sort -V | tail -1)"
JAR="$SDK/platforms/android-36/android.jar"
OUT=build
rm -rf "$OUT"; mkdir -p "$OUT/assets" "$OUT/classes" "$OUT/dex"
cp ../web/index.html "$OUT/assets/index.html"

"$BT/aapt2.exe" compile --dir res -o "$OUT/res.zip"
"$BT/aapt2.exe" link -o "$OUT/base.apk" -I "$JAR" --manifest AndroidManifest.xml -R "$OUT/res.zip" -A "$OUT/assets" \
  --min-sdk-version 26 --target-sdk-version 36 --version-code 1 --version-name 1.0 --auto-add-overlay

javac -nowarn -Xlint:none -source 11 -target 11 -cp "$JAR" -d "$OUT/classes" $(find src -name '*.java') 2>&1 | grep -v -i "warning\|deprecat" || true
java -cp "$BT/lib/d8.jar" com.android.tools.r8.D8 --release --lib "$JAR" --min-api 26 --output "$OUT/dex" $(find "$OUT/classes" -name '*.class')

python -I - "$OUT" <<'PY'
import sys, zipfile, shutil
out = sys.argv[1]
shutil.copy(f"{out}/base.apk", f"{out}/unsigned.apk")
with zipfile.ZipFile(f"{out}/unsigned.apk", "a", zipfile.ZIP_DEFLATED) as z:
    z.write(f"{out}/dex/classes.dex", "classes.dex")
PY

"$BT/zipalign.exe" -f -p 4 "$OUT/unsigned.apk" "$OUT/aligned.apk"
KS=casterhub.keystore
if [ ! -f "$KS" ]; then
  keytool -genkeypair -keystore "$KS" -storepass casterhub -keypass casterhub -alias casterhub -keyalg RSA -keysize 2048 -validity 10000 \
    -dname "CN=Caster Hub, O=Speedcubing, C=ES" >/dev/null 2>&1
fi
java -jar "$BT/lib/apksigner.jar" sign --ks "$KS" --ks-pass pass:casterhub --key-pass pass:casterhub --out ../CasterHub.apk "$OUT/aligned.apk"
java -jar "$BT/lib/apksigner.jar" verify ../CasterHub.apk && echo "APK OK: $(cd ..; pwd)/CasterHub.apk"
