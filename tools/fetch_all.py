import json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

D = sys.argv[1]
API = "https://www.worldcubeassociation.org/api/v0"

def get(url, path):
    if os.path.exists(path):
        return
    for i in range(12):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "cubing-stats-script"})
            data = json.load(urllib.request.urlopen(req, timeout=60))
            json.dump(data, open(path, "w", encoding="utf-8"))
            return
        except Exception as e:
            time.sleep(15 * (i + 1))
    print("FAIL", url)

wcif = json.load(open(os.path.join(D, "wcif.json"), encoding="utf-8"))
ids = sorted(p["wcaId"] for p in wcif["persons"] if p.get("wcaId") and p.get("registration") and p["registration"]["status"] == "accepted")
print(len(ids), "persons")

def fetch_person(w):
    b = os.path.join(D, "persons", w)
    get(f"{API}/persons/{w}", b + ".json")
    get(f"{API}/persons/{w}/results", b + "_results.json")
    get(f"{API}/persons/{w}/competitions", b + "_comps.json")

with ThreadPoolExecutor(2) as ex:
    list(ex.map(fetch_person, ids))
print("done", len(os.listdir(os.path.join(D, "persons"))) // 3)
