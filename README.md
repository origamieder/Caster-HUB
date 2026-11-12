# Caster Hub · Campeonato de España de Speedcubing 2026

App con los datos de los 341 inscritos para los casters: psych sheets por evento, fichas de competidores, buscador, filtros y palmarés.
Todos los datos vienen de la API pública de la WCA.

---

## 1. Usar la app (no hace falta instalar nada)

| Dónde | Archivo | Cómo |
|---|---|---|
| PC (Windows, Mac o Linux) | `web/index.html` | Doble clic: se abre en el navegador. Funciona **sin internet**. |
| Tablet o móvil Android (8.0 o superior) | `CasterHub.apk` | Pásalo al dispositivo, ábrelo y permite *"Instalar apps de fuentes desconocidas"* cuando lo pida. |

- Basta con copiar **solo `web/index.html`** (por ejemplo, en un USB) para usarla en el PC de cabina: los datos van dentro del archivo.

### Instalarla en un PC con Windows (recomendado para cabina)

Doble clic en **`Instalar en este PC.bat`**. En unos segundos:

- copia la app a `%LOCALAPPDATA%\CasterHub`, así que sigue funcionando aunque quites el USB;
- crea el acceso directo **Caster Hub** en el Escritorio y en el menú Inicio;
- la abre en una **ventana propia, sin pestañas ni barra de direcciones** (Edge o Chrome en modo aplicación). Si no hay ninguno de los dos, la abre en el navegador predeterminado.

No necesita permisos de administrador ni internet. Para quitarla, usa **`Desinstalar de este PC.bat`**.

Si Windows muestra *"Windows protegió su PC"*, pulsa **Más información → Ejecutar de todas formas**. Es normal con scripts descargados o copiados de un USB.

Para instalar desde un USB basta con llevar estos archivos, respetando las carpetas:
`Instalar en este PC.bat`, `tools/instalar.ps1`, `web/index.html` y `web/casterhub.ico`.

Si actualizas los datos, vuelve a ejecutar el instalador para que el PC use la versión nueva.
- Con internet se ven además las fotos de los competidores y funcionan los enlaces a la WCA. Sin internet se muestran las iniciales.
- En el PC, la tecla `/` lleva directamente al buscador.
- En Android la app gira con el dispositivo (respeta el bloqueo de rotación), va a pantalla completa y no deja que se apague la pantalla.

### Herramientas para el directo

- **Favorito:** en cada evento es el mejor español inscrito, con su ventaja sobre el segundo español. El mejor general sigue siendo el nº 1 de la tabla.
- **Fijados (☆):** marca a los competidores que vas a comentar con la estrella de la tabla o de la ficha. Aparecen en *Resumen* y con el filtro **★ Fijados** de cada evento y de *Competidores*.
- **Datos clave:** cada ficha abre con frases cortas listas para decir (títulos, récords vigentes, podios internacionales, forma actual, participaciones).
- **Notas del caster:** en cada ficha, para pronunciación o anécdotas. Quien tiene notas sale marcado con ✎.
- **Cara a cara:** en un evento, pulsa *Cara a cara* y toca de 2 a 4 competidores para compararlos lado a lado. En verde, el mejor dato de cada fila.
- **Texto grande (Aa):** agranda nombres y tiempos para leer de lejos.
- **Atajos de teclado:** `←` `→` cambian de evento, o de competidor si hay una ficha abierta; `F` fija al competidor de la ficha; `Esc` la cierra.
- Los fijados y las notas se guardan **solo en ese dispositivo y navegador**: no se comparten entre el PC y la tablet.

---

## 2. Actualizar los datos antes del campeonato

Las marcas personales cambian con cada competición, así que conviene actualizar unos días antes. El script `actualizar.sh` hace todo de una vez:

1. Descarga de la WCA los inscritos y sus perfiles.
2. Regenera el Excel `Campeonato_Espana_2026_Competidores.xlsx`.
3. Regenera la web: `web/index.html` y `web/caster-hub.html`.
4. Recompila `CasterHub.apk`.

Tarda **30-40 minutos**, porque la WCA limita el número de peticiones. Es normal que parezca parado un rato.

### Requisitos del PC (una sola vez)

| Programa | Para qué | Cómo comprobarlo |
|---|---|---|
| [Git for Windows](https://git-scm.com/download/win) (incluye Git Bash y `curl`) | Ejecutar el script | `bash --version` |
| [Python 3.10 o superior](https://www.python.org/downloads/) | Descarga y procesado de datos, Excel | `python --version` |
| Librería `openpyxl` | Crear el Excel | `python -c "import openpyxl"` |
| Java JDK 17 o superior (p. ej. [Temurin](https://adoptium.net/)) | Compilar el APK | `java -version` y `javac -version` |
| [Android Studio](https://developer.android.com/studio) (o solo el Android SDK) | Compilar el APK | Ver abajo |

Instala `openpyxl` con:

```bash
python -m pip install openpyxl
```

**Android SDK.** Desde Android Studio, abre *Settings → Languages & Frameworks → Android SDK* y marca:
- En *SDK Platforms*: **Android 16 (API 36)**.
- En *SDK Tools*: **Android SDK Build-Tools** (36 o superior).

Por defecto el script busca el SDK en `%LOCALAPPDATA%\Android\Sdk`. Si está en otro sitio, indícalo antes de ejecutar:

```bash
export ANDROID_HOME="D:/ruta/al/Android/Sdk"
```

Al instalar Python en Windows, marca la casilla **"Add python.exe to PATH"**.

### Ejecutar

Abre **Git Bash** en la carpeta `CasterHub` (clic derecho → *Open Git Bash here*) y ejecuta:

```bash
bash actualizar.sh
```

Al terminar verás `Listo: …`.

### Si solo quieres actualizar la web (sin APK)

Si el PC no tiene Java ni el SDK de Android, ejecuta los pasos uno a uno y omite el último:

```bash
D=tools/data; rm -rf $D/persons
curl -s -A "cubing-stats-script" "https://www.worldcubeassociation.org/api/v0/competitions/SpanishChampionship2026/wcif/public" -o $D/wcif.json
python -I tools/fetch.py $D
python -I tools/fetch_all.py $D
python -I tools/build.py $D Campeonato_Espana_2026_Competidores.xlsx
python -I tools/export.py $D web/data.json
python -I web/bundle.py
```

---

## 3. Contenido de la carpeta

```
CasterHub/
├── CasterHub.apk              App Android lista para instalar
├── Instalar en este PC.bat    Instala la web en Windows con accesos directos
├── Desinstalar de este PC.bat Quita la instalación anterior
├── actualizar.sh              Actualiza datos + Excel + web + APK
├── web/
│   ├── index.html             App completa en un solo archivo (abrir con doble clic)
│   ├── caster-hub.html        Misma app, versión para publicar como página en claude.ai
│   ├── app.html               Código fuente de la app (diseño y lógica)
│   ├── data.json              Datos exportados
│   ├── casterhub.ico          Icono de los accesos directos
│   └── bundle.py              Une app.html + data.json → index.html y caster-hub.html
├── android/
│   ├── AndroidManifest.xml    Configuración de la app (nombre, orientación, permisos)
│   ├── src/…/MainActivity.java
│   ├── res/                   Icono
│   ├── build_apk.sh           Compila el APK sin Gradle (solo herramientas del SDK)
│   └── casterhub.keystore     ⚠ Clave de firma del APK (no está en GitHub, solo en tu PC)
└── tools/
    ├── instalar.ps1           Lógica del instalador (lo lanza el .bat)
    ├── fetch.py               Calcula top 20 general / top 20 españoles y descarga perfiles
    ├── fetch_all.py           Descarga el resto de inscritos
    ├── build.py               Genera el Excel
    ├── export.py              Genera data.json para la app
    └── data/champs/           Resultados de Ctos. de España, Europeos y Mundiales (caché)
```

---

## 4. Avisos importantes

- **La clave de firma `android/casterhub.keystore` no se sube a GitHub** (el repo es público). Guarda una copia aparte, por ejemplo en un USB o en tu nube privada, y cópiala a `android/` en cada PC donde vayas a compilar el APK. Android solo deja instalar una versión nueva encima de la anterior si está firmada con la misma clave. Si no está, `build_apk.sh` crea una nueva y habrá que desinstalar la app de la tablet antes de instalar la versión nueva.
- **Si cambias de campeonato** (por ejemplo, para 2027), cambia `SpanishChampionship2026` en `actualizar.sh` y añade la edición nueva a la lista de campeonatos de `tools/fetch.py`.
- **Página publicada en claude.ai:** es privada. Para que otra persona la abra, compártela desde el menú *Share* de la página. No se actualiza sola: cuando actualices los datos, hay que volver a publicar `web/caster-hub.html`.

---

## 5. Problemas frecuentes

| Síntoma | Solución |
|---|---|
| `python: command not found` | Reinstala Python marcando *"Add python.exe to PATH"*, o usa `py` en lugar de `python`. |
| `ModuleNotFoundError: No module named 'openpyxl'` | `python -m pip install openpyxl` |
| Mensajes `HTTP Error 429` o que parece parado | Es el límite de la WCA: el script espera y reintenta solo. Déjalo terminar. |
| Error con `android-36/android.jar` | Falta la plataforma API 36 en el SDK (ver requisitos), o `ANDROID_HOME` apunta a otra carpeta. |
| `javac: command not found` | Instala el JDK (no solo el JRE) y abre una ventana nueva de Git Bash. |
| La tablet no deja instalar el APK | Ajustes → Seguridad → permitir *Instalar apps desconocidas* para la app con la que abres el archivo (Archivos, Chrome…). |
| "La app no se ha instalado" al actualizar | El APK nuevo se firmó con otra clave: desinstala la versión anterior y vuelve a instalar. |
| En el PC se ven iniciales en vez de fotos | No hay internet. Los datos funcionan igual. |
