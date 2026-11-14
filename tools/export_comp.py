"""Datos para la app de competidores (sin la información de casters).

Uso:  python -I tools/export_comp.py tools/data competidores/data.json

Fuente preferida: tools/data/wcif.json (WCIF público de la WCA), que trae marcas personales,
rondas (formato, límite de tiempo, corte, cuántos pasan), horario y grupos asignados.
Si no existe, se genera a partir de web/data.json (sin horario ni rondas); la app los
descarga de la WCA la primera vez que tenga internet.

El formato de salida es el mismo que produce slim() en competidores/app.html al descargar
el WCIF desde el móvil: si cambias uno, cambia el otro.
"""
import datetime, json, os, re, sys

D, OUT = sys.argv[1], sys.argv[2]
HERE = os.path.dirname(os.path.abspath(__file__))
COMP_ID = "SpanishChampionship2026"
COMP_NAME = "Campeonato de España 2026"


def competing(p):
    r = p.get("registration") or {}
    return r.get("status") == "accepted" and r.get("isCompeting", True)


def from_wcif(w):
    persons = []
    for p in w["persons"]:
        if not competing(p):
            continue
        persons.append(dict(
            r=p["registrantId"], n=p["name"], w=p.get("wcaId"), c=p.get("countryIso2"), g=p.get("gender"),
            a=(p.get("avatar") or {}).get("thumbUrl"), e=p["registration"]["eventIds"],
            pb=[[b["eventId"], b["type"][0], b["best"], b.get("worldRanking"), b.get("nationalRanking")] for b in p.get("personalBests", [])],
            asg=[[a["activityId"], a.get("assignmentCode"), a.get("stationNumber")] for a in p.get("assignments", [])],
        ))
    keep_r = ("id", "format", "timeLimit", "cutoff", "advancementCondition")
    events = [dict(id=e["id"], rounds=[{k: r.get(k) for k in keep_r} for r in e.get("rounds", [])]) for e in w["events"]]
    act = lambda a: dict(id=a["id"], name=a["name"], activityCode=a["activityCode"], startTime=a["startTime"], endTime=a["endTime"],
                         childActivities=[act(c) for c in a.get("childActivities", [])])
    sch = w.get("schedule") or {}
    schedule = dict(startDate=sch.get("startDate"), numberOfDays=sch.get("numberOfDays"),
                    venues=[dict(name=v["name"], timezone=v["timezone"],
                                 rooms=[dict(id=r["id"], name=r["name"], color=r.get("color"), activities=[act(a) for a in r.get("activities", [])])
                                        for r in v.get("rooms", [])]) for v in sch.get("venues", [])]) if sch.get("venues") else None
    return dict(id=w["id"], name=COMP_NAME, source="wcif", persons=persons, events=events, schedule=schedule)


def centis(ev, t):
    """'1:02.34' -> 6234 · '3/4 45:12' -> valor WCA de Multi-BLD · '' -> None"""
    if not t:
        return None
    if ev == "333mbf":
        m = re.match(r"(\d+)/(\d+) (\?|(\d+):(\d+))", t)
        solved, att = int(m.group(1)), int(m.group(2))
        missed = att - solved
        secs = 99999 if m.group(3) == "?" else int(m.group(4)) * 60 + int(m.group(5))
        return (99 - (solved - missed)) * 10000000 + secs * 100 + missed
    parts = t.split(":")
    s = float(parts[-1]) + (60 * int(parts[0]) if len(parts) == 2 else 0)
    return round(s * 100)


def from_caster_data(path):
    d = json.load(open(path, encoding="utf-8"))
    rows = {}
    for e in d["events"]:
        for r in e["rows"]:
            rows.setdefault(r["id"], {})[e["id"]] = r
    persons = []
    for p in d["persons"]:
        pb = []
        for ev, r in rows.get(p["id"], {}).items():
            if r.get("pbS"): pb.append([ev, "s", centis(ev, r["pbS"]), r.get("wrS"), r.get("nrS")])
            if r.get("pbA"): pb.append([ev, "a", centis(ev, r["pbA"]), r.get("wrA"), r.get("nrA")])
        persons.append(dict(r=p["rid"], n=p["name"], w=None if p.get("newcomer") else p["id"], c=p["iso"], g=p.get("gender"),
                            a=p.get("avatar"), e=p["events"], pb=pb, asg=[]))
    return dict(id=COMP_ID, name=COMP_NAME, source="psych", persons=persons,
                events=[dict(id=e["id"], rounds=[]) for e in d["events"]], schedule=None), d["meta"]["updated"]


wcif_path = os.path.join(D, "wcif.json")
if os.path.exists(wcif_path):
    out = from_wcif(json.load(open(wcif_path, encoding="utf-8")))
    out["updated"] = datetime.date.today().isoformat()
else:
    out, upd = from_caster_data(os.path.join(HERE, "..", "web", "data.json"))
    out["updated"] = upd
    print("aviso: no hay", wcif_path, "-> datos de web/data.json, sin horario ni rondas (la app los descarga al tener internet)")
out["v"] = 1
os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("saved", OUT, os.path.getsize(OUT) // 1024, "KB,", len(out["persons"]), "competidores, fuente:", out["source"])
