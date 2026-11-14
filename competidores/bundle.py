"""Une competidores/app.html + competidores/data.json (+ logos de web/assets) en un solo HTML para el APK.
Uso: python -I competidores/bundle.py  ->  competidores/build/index.html"""
import base64, json, os, re
here = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(here, "app.html"), encoding="utf-8").read()
data = open(os.path.join(here, "data.json"), encoding="utf-8").read()
json.loads(data)
frag = src.replace("/*__DATA__*/", data.replace("</", "<\\/"), 1)
def img(m):
    p = os.path.join(here, "..", "web", "assets", m.group(1) + ".png")
    return "data:image/png;base64," + base64.b64encode(open(p, "rb").read()).decode()
frag = re.sub(r"__IMG_([a-z0-9-]+)__", img, frag)
full = ('<!doctype html>\n<html lang="es">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '<style>[hidden]{display:none!important}img{max-width:100%}</style>\n'
        '</head>\n<body>\n' + frag + '\n</body>\n</html>\n')
os.makedirs(os.path.join(here, "build"), exist_ok=True)
open(os.path.join(here, "build", "index.html"), "w", encoding="utf-8").write(full)
print("ok", len(full) // 1024, "KB")
