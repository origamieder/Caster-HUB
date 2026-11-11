#!/usr/bin/env bash
# Descarga datos frescos de la WCA y regenera el Excel, la web y el APK.
# Uso (Git Bash):  bash actualizar.sh
# Tarda ~30-40 min: la API de la WCA limita las peticiones.
set -euo pipefail
cd "$(dirname "$0")"
D="tools/data"
mkdir -p "$D"
rm -rf "$D/persons"                      # perfiles siempre frescos (las marcas cambian); los campeonatos pasados se reutilizan
curl -s -A "cubing-stats-script" "https://www.worldcubeassociation.org/api/v0/competitions/SpanishChampionship2026/wcif/public" -o "$D/wcif.json"
python -I tools/fetch.py "$D"             # top 20 general + top 20 españoles y campeonatos históricos
python -I tools/fetch_all.py "$D"         # resto de inscritos (para el buscador)
python -I tools/build.py "$D" "Campeonato_Espana_2026_Competidores.xlsx"
python -I tools/export.py "$D" "web/data.json"
python -I web/bundle.py
bash android/build_apk.sh
echo "Listo: web/index.html, web/caster-hub.html, CasterHub.apk y el Excel actualizados."
