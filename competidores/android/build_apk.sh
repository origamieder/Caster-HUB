#!/usr/bin/env bash
# Compila Cto_Espana_2026_Competidores.apk sin Gradle.
# Uso: bash competidores/android/build_apk.sh   (antes: python -I competidores/bundle.py)
#  - Con el Android SDK (Windows / Android Studio): usa aapt2 + d8 de build-tools y android-36.
#  - En Linux sin SDK: apt install aapt dalvik-exchange zipalign apksigner android-sdk-platform-23
set -euo pipefail
cd "$(dirname "$0")"
APK=../../Cto_Espana_2026_Competidores.apk
VCODE=1; VNAME=1.0
OUT=build
rm -rf "$OUT"; mkdir -p "$OUT/assets" "$OUT/classes" "$OUT/dex"
cp ../build/index.html "$OUT/assets/index.html"

SDK="${ANDROID_HOME:-${LOCALAPPDATA:-/nonexistent}/Android/Sdk}"
if [ -d "$SDK/build-tools" ] && [ -f "$SDK/platforms/android-36/android.jar" ]; then
  BT="$SDK/build-tools/$(ls "$SDK/build-tools" | sort -V | tail -1)"; X=""; [ -f "$BT/aapt2.exe" ] && X=".exe"
  JAR="$SDK/platforms/android-36/android.jar"
  "$BT/aapt2$X" compile --dir res -o "$OUT/res.zip"
  "$BT/aapt2$X" link -o "$OUT/base.apk" -I "$JAR" --manifest AndroidManifest.xml -R "$OUT/res.zip" -A "$OUT/assets" \
    --min-sdk-version 26 --target-sdk-version 34 --version-code $VCODE --version-name $VNAME --auto-add-overlay
  javac -nowarn -Xlint:none -source 8 -target 8 -cp "$JAR" -d "$OUT/classes" $(find src -name '*.java') -Xlint:-options 2>&1 | grep -v -i "^warning\|deprecat\|JAVA_TOOL\|^Note:" || true
  ls "$OUT"/classes/es/speedcubing/competidores/MainActivity.class >/dev/null
  java -cp "$BT/lib/d8.jar" com.android.tools.r8.D8 --release --lib "$JAR" --min-api 26 --output "$OUT/dex" $(find "$OUT/classes" -name '*.class')
  ZIPALIGN="$BT/zipalign$X"; SIGN="java -jar $BT/lib/apksigner.jar"
else
  JAR=/usr/lib/android-sdk/platforms/android-23/android.jar
  aapt package -f -M AndroidManifest.xml -S res -A "$OUT/assets" -I "$JAR" -F "$OUT/base.apk" \
    --min-sdk-version 26 --target-sdk-version 34 --version-code $VCODE --version-name $VNAME
  javac -nowarn -Xlint:none -source 8 -target 8 -bootclasspath "$JAR" -d "$OUT/classes" $(find src -name '*.java') -Xlint:-options 2>&1 | grep -v -i "^warning\|deprecat\|JAVA_TOOL\|^Note:" || true
  ls "$OUT"/classes/es/speedcubing/competidores/MainActivity.class >/dev/null
  dalvik-exchange --dex --min-sdk-version=26 --output="$OUT/dex/classes.dex" "$OUT/classes" 2>&1 | grep -v JAVA_TOOL || true
  ZIPALIGN=zipalign; SIGN=apksigner
fi

PY=$(command -v python3 || command -v python)
"$PY" -I - "$OUT" <<'PY'
import sys, zipfile
out = sys.argv[1]
# resources.arsc sin comprimir (obligatorio desde Android 11) y se añade classes.dex
with zipfile.ZipFile(f"{out}/base.apk") as zi, zipfile.ZipFile(f"{out}/unsigned.apk", "w", zipfile.ZIP_DEFLATED) as zo:
    for it in zi.infolist():
        zo.writestr(it, zi.read(it.filename), compress_type=zipfile.ZIP_STORED if it.filename == "resources.arsc" else zipfile.ZIP_DEFLATED)
    zo.write(f"{out}/dex/classes.dex", "classes.dex")
PY

"$ZIPALIGN" -f -p 4 "$OUT/unsigned.apk" "$OUT/aligned.apk"
KS=competidores.keystore
if [ ! -f "$KS" ]; then
  keytool -genkeypair -keystore "$KS" -storepass competidores -keypass competidores -alias competidores -keyalg RSA -keysize 2048 -validity 10000 \
    -dname "CN=Cto Espana 2026 Competidores, O=Speedcubing, C=ES" >/dev/null 2>&1
fi
$SIGN sign --ks "$KS" --ks-pass pass:competidores --key-pass pass:competidores --out "$APK" "$OUT/aligned.apk"
$SIGN verify "$APK" && echo "APK OK: $(cd "$(dirname "$APK")"; pwd)/$(basename "$APK")"
