import json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

D = sys.argv[1]
API = "https://www.worldcubeassociation.org/api/v0"
SINGLE_EVENTS = {"333bf", "444bf", "555bf", "333mbf"}

def get(url, path):
    if os.path.exists(path):
        return json.load(open(path, encoding="utf-8"))
    for i in range(12):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "cubing-stats-script"})
            data = json.load(urllib.request.urlopen(req, timeout=60))
            json.dump(data, open(path, "w", encoding="utf-8"))
            return data
        except Exception as e:
            print("retry", url, e); time.sleep(15 * (i + 1))
    raise RuntimeError(url)

wcif = json.load(open(os.path.join(D, "wcif.json"), encoding="utf-8"))
events = [e["id"] for e in wcif["events"]]
persons = [p for p in wcif["persons"] if p.get("registration") and p["registration"]["status"] == "accepted" and p.get("wcaId")]

def key(p, ev):
    pbs = {(b["eventId"], b["type"]): b["best"] for b in p["personalBests"]}
    s, a = pbs.get((ev, "single")), pbs.get((ev, "average"))
    if ev in SINGLE_EVENTS:
        return None if s is None else (s,)
    if a is None and s is None:
        return None
    return (0, a, s) if a is not None else (1, s, 0)

top, top_es = {}, {}
iso = {p["wcaId"]: p["countryIso2"] for p in persons}
for ev in events:
    cands = [(key(p, ev), p["wcaId"]) for p in persons if ev in p["registration"]["eventIds"]]
    cands = sorted([c for c in cands if c[0] is not None])
    top[ev] = [w for _, w in cands[:20]]
    top_es[ev] = [w for _, w in cands if iso[w] == "ES"][:20]
json.dump(top, open(os.path.join(D, "top.json"), "w"))
json.dump(top_es, open(os.path.join(D, "top_es.json"), "w"))
ids = sorted({w for v in list(top.values()) + list(top_es.values()) for w in v})
print(len(ids), "persons")

os.makedirs(os.path.join(D, "persons"), exist_ok=True)
def fetch_person(w):
    get(f"{API}/persons/{w}", os.path.join(D, "persons", f"{w}.json"))
    get(f"{API}/persons/{w}/results", os.path.join(D, "persons", f"{w}_results.json"))
    get(f"{API}/persons/{w}/competitions", os.path.join(D, "persons", f"{w}_comps.json"))
with ThreadPoolExecutor(2) as ex:
    list(ex.map(fetch_person, ids))

champs = ["SpanishChampionship2026"]  # placeholder removed below
champs = [c for c in [
    "Spain2004","Spain2005","Spain2006","Spain2007","Spain2008","SpanishChampionship2009","SpanishChampionship2010",
    "SpanishChampionship2011","SpanishChampionship2012","SpanishChampionships2013","SpanishChampionship2014",
    "SpanishChampionship2015","SpanishChampionship2016","SpanishChampionship2017","Spain2018","SpanishChampionship2019",
    "SpanishChampionship2022","SpanishChampionship2023","SpanishChampionship2024","SpanishChampionship2025",
    "FMCSpanishChampionship2023","FMCSpanishChampionship2024",
    "Euro2004","Euro2006","Euro2008","Euro2010","Euro2012","Euro2014","Euro2016","Euro2018","Euro2020","Euro2022","Euro2024","Euro2026",
    "WC2003","WC2005","WC2007","WC2009","WC2011","WC2013","WC2015","WC2017","WC2019","WC2023","WC2025"]]
os.makedirs(os.path.join(D, "champs"), exist_ok=True)
def fetch_champ(c):
    try:
        get(f"{API}/competitions/{c}/results", os.path.join(D, "champs", f"{c}.json"))
        get(f"{API}/competitions/{c}", os.path.join(D, "champs", f"{c}_info.json"))
    except Exception as e:
        print("FAIL", c, e)
with ThreadPoolExecutor(2) as ex:
    list(ex.map(fetch_champ, champs))
print("done")
