import sys, os, json
here = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(here, "app.html"), encoding="utf-8").read()
data = open(os.path.join(here, "data.json"), encoding="utf-8").read()
json.loads(data)
data = data.replace("</", "<\\/")
frag = src.replace("/*__DATA__*/", data, 1)
out = here
open(os.path.join(out, "caster-hub.html"), "w", encoding="utf-8").write(frag)
full = ('<!doctype html>\n<html lang="es">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>\n'
        '</head>\n<body>\n' + frag + '\n</body>\n</html>\n')
open(os.path.join(out, "index.html"), "w", encoding="utf-8").write(full)
print("ok", len(full) // 1024, "KB")
