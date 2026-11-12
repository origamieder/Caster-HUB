import json, os, sys, glob, collections, datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.comments import Comment

D, OUT = sys.argv[1], sys.argv[2]
TODAY = datetime.date.today()
SINGLE_EVENTS = {"333bf", "444bf", "555bf", "333mbf"}
EV_NAME = {"333": "3x3x3", "222": "2x2x2", "444": "4x4x4", "555": "5x5x5", "666": "6x6x6", "777": "7x7x7",
           "333bf": "3x3 BLD", "333oh": "3x3 OH", "clock": "Clock", "minx": "Megaminx", "pyram": "Pyraminx",
           "skewb": "Skewb", "sq1": "Square-1", "444bf": "4x4 BLD", "555bf": "5x5 BLD", "333mbf": "Multi-BLD",
           "333fm": "FMC"}
EUROPE = set("AD AL AM AT AZ BA BE BG BY CH CY CZ DE DK EE ES FI FR GB GE GR HR HU IE IS IT LI LT LU LV MC MD ME MK MT NL NO PL PT RO RS RU SE SI SK SM TR UA VA XK".split())
COUNTRY = {}

def load(p):
    return json.load(open(p, encoding="utf-8"))

def fmt(ev, v, kind="single"):
    if v is None or v == 0:
        return ""
    if v == -1: return "DNF"
    if v == -2: return "DNS"
    if ev == "333mbf":
        dd, ttttt, mm = v // 10000000, (v // 100) % 100000, v % 100
        diff = 99 - dd; solved = diff + mm; att = solved + mm
        t = "?" if ttttt == 99999 else f"{ttttt // 60}:{ttttt % 60:02d}"
        return f"{solved}/{att} {t}"
    if ev == "333fm":
        return f"{v / 100:.2f}" if kind == "average" else str(v)
    s = v / 100
    if s >= 60:
        m = int(s // 60)
        return f"{m}:{s - 60 * m:05.2f}"
    return f"{s:.2f}"

def mbf_points(v):
    return 99 - v // 10000000

wcif = load(os.path.join(D, "wcif.json"))
events = [e["id"] for e in wcif["events"]]
top = load(os.path.join(D, "top.json"))
top_es = load(os.path.join(D, "top_es.json"))
def _key(p, ev):
    pbs = {(b["eventId"], b["type"]): b["best"] for b in p["personalBests"]}
    s_, a_ = pbs.get((ev, "single")), pbs.get((ev, "average"))
    if ev in SINGLE_EVENTS:
        return None if s_ is None else (s_,)
    if a_ is None and s_ is None: return None
    return (0, a_, s_) if a_ is not None else (1, s_, 0)
_wc = load(os.path.join(D, "wcif.json"))
full_rank = {}
for _ev in [e["id"] for e in _wc["events"]]:
    _c = sorted((k, p["wcaId"]) for p in _wc["persons"] if p.get("wcaId") and p.get("registration") and p["registration"]["status"] == "accepted" and p["registration"].get("isCompeting", True)
                and _ev in p["registration"]["eventIds"] for k in [_key(p, _ev)] if k is not None)
    full_rank[_ev] = {w: i for i, (_, w) in enumerate(_c, 1)}
reg = {p["wcaId"]: p for p in wcif["persons"] if p.get("wcaId")}
accepted = [p for p in wcif["persons"] if p.get("registration") and p["registration"]["status"] == "accepted" and p["registration"].get("isCompeting", True)]

# ---------- championships ----------
champ_info, champ_res = {}, {}
for f in glob.glob(os.path.join(D, "champs", "*_info.json")):
    cid = os.path.basename(f)[:-10]
    champ_info[cid] = load(f)
    champ_res[cid] = load(os.path.join(D, "champs", cid + ".json"))

def ctype(cid):
    if cid.startswith("WC"): return "Mundial"
    if cid.startswith("Euro"): return "Europeo"
    return "España"

def eligible(t, iso):
    return t == "Mundial" or (t == "Europeo" and iso in EUROPE) or (t == "España" and iso == "ES")

# podium[(wca_id)] -> list of (type, year, event, place)
podiums = collections.defaultdict(list)
champ_winners = {}  # (cid, ev) -> [wca ids 1..3]
for cid, res in champ_res.items():
    t = ctype(cid)
    year = int(champ_info[cid]["start_date"][:4])
    byev = collections.defaultdict(list)
    for r in res:
        byev[r["event_id"]].append(r)
    for ev, rows in byev.items():
        fin_round = None
        for rt in ("f", "c"):
            if any(r["round_type_id"] == rt for r in rows):
                fin_round = rt; break
        if not fin_round:
            continue
        fin = sorted([r for r in rows if r["round_type_id"] == fin_round and r["best"] > 0 and eligible(t, r["country_iso2"])],
                     key=lambda r: r["pos"])
        champ_winners[(cid, ev)] = [r["wca_id"] for r in fin[:3]]
        for place, r in enumerate(fin[:3], 1):
            podiums[r["wca_id"]].append((t, year, ev, place, cid))

# ---------- persons ----------
P = {}
for w in sorted(w for w in reg if os.path.exists(os.path.join(D, "persons", w + "_comps.json"))):
    base = os.path.join(D, "persons", w)
    info = load(base + ".json")
    results = load(base + "_results.json")
    comps = load(base + "_comps.json")
    cdate = {c["id"]: datetime.date.fromisoformat(c["start_date"]) for c in comps}
    for r in results:
        r["_date"] = cdate.get(r["competition_id"])
    P[w] = dict(info=info, results=results, comps=comps, cdate=cdate)

def champ_attended(w, t):
    return sorted({int(champ_info[c]["start_date"][:4]) for c in P[w]["cdate"] if c in champ_info and ctype(c) == t and not c.startswith("FMC")} |
                  {int(champ_info[c]["start_date"][:4]) for c in P[w]["cdate"] if c in champ_info and ctype(c) == t and c.startswith("FMC")})

def metric(ev):
    return "single" if ev in SINGLE_EVENTS else "average"

def ev_stats(w, ev):
    p = P[w]
    pr = p["info"]["personal_records"].get(ev, {})
    s, a = pr.get("single", {}), pr.get("average", {})
    m = metric(ev)
    field = "best" if m == "single" else "average"
    rows = [r for r in p["results"] if r["event_id"] == ev and r[field] and r[field] > 0 and r["_date"]]
    per_year = {}
    for r in rows:
        y = r["_date"].year
        per_year[y] = min(per_year.get(y, 10**12), r[field])
    last12 = [r[field] for r in rows if (TODAY - r["_date"]).days <= 365]
    prev12 = [r[field] for r in rows if 365 < (TODAY - r["_date"]).days <= 730]
    def val(v):
        return mbf_points(v) if ev == "333mbf" else v
    def impr(old, new):
        if old is None or new is None: return None
        if ev == "333mbf":
            o, n = mbf_points(old), mbf_points(new)
            return (n - o) / o if o > 0 else None
        return (old - new) / old
    years = sorted(per_year)
    first = per_year[years[0]] if years else None
    pb = (s if m == "single" else a).get("best")
    all_attempts = [x for r in rows for x in r["attempts"] if x and x > 0] if m == "average" else []
    mean_last12 = sum(last12) / len(last12) if last12 and ev != "333mbf" else None
    return dict(
        pb_single=s.get("best"), pb_avg=a.get("best"),
        nr_s=s.get("country_rank"), wr_s=s.get("world_rank"), cr_s=s.get("continent_rank"),
        nr_a=a.get("country_rank"), wr_a=a.get("world_rank"), cr_a=a.get("continent_rank"),
        first_year=years[0] if years else None, first_best=first,
        impr_total=impr(first, pb),
        best12=min(last12) if last12 else None, prev12=min(prev12) if prev12 else None,
        impr_year=impr(min(prev12) if prev12 else None, min(last12) if last12 else None),
        mean12=mean_last12, n12=len(last12),
        per_year=per_year, n_rounds=len(rows),
        last_comp=max((r["_date"] for r in rows), default=None),
    )

def podium_str(w, t=None, ev=None, place=None):
    items = [x for x in podiums.get(w, []) if (t is None or x[0] == t) and (ev is None or x[2] == ev) and (place is None or x[3] == place)]
    return items

# ================= JSON EXPORT FOR THE APP =================
MEDAL = {1: "🥇", 2: "🥈", 3: "🥉"}
names = {}
for res in champ_res.values():
    for x in res: names[x["wca_id"]] = x["name"]
reg_ids = {p["wcaId"] for p in accepted if p.get("wcaId")}

def nm(w): return P[w]["info"]["person"]["name"] if w in P else names.get(w, reg.get(w, {}).get("name", w))

def pct(x): return None if x is None else round(x * 100, 1)

es_rank = {}
for ev in events:
    es_list = [w for w, _ in sorted(full_rank[ev].items(), key=lambda kv: kv[1]) if reg[w]["countryIso2"] == "ES"]
    es_rank[ev] = {w: i for i, w in enumerate(es_list, 1)}

def best_place_es(w, ev, iso):
    best = None
    for cid, res in champ_res.items():
        if ctype(cid) != "España": continue
        rows = [x for x in res if x["event_id"] == ev]
        fin = []
        for rt in ("f", "c"):
            fin = [x for x in rows if x["round_type_id"] == rt]
            if fin: break
        fin = sorted([x for x in fin if x["best"] > 0], key=lambda x: x["pos"])
        pool = [x for x in fin if x["country_iso2"] == "ES"] if iso == "ES" else fin
        for k, x in enumerate(pool, 1):
            if x["wca_id"] == w:
                pos = k if iso == "ES" else x["pos"]
                best = pos if best is None else min(best, pos)
    return best

years = list(range(TODAY.year - 7, TODAY.year + 1))
EV_OUT = []
for ev in events:
    m = metric(ev)
    rows = []
    for w, seed in sorted(full_rank[ev].items(), key=lambda kv: kv[1]):
        if w not in P: continue
        st = ev_stats(w, ev); iso = reg[w]["countryIso2"]
        rows.append(dict(
            id=w, seed=seed, seedES=es_rank[ev].get(w),
            pbS=fmt(ev, st["pb_single"]), pbA=fmt(ev, st["pb_avg"], "average"),
            nrS=st["nr_s"], wrS=st["wr_s"], nrA=st["nr_a"], wrA=st["wr_a"],
            b12=fmt(ev, st["best12"], m), m12=(fmt(ev, round(st["mean12"]), m) if st["mean12"] else None), n12=st["n12"],
            p12=fmt(ev, st["prev12"], m), iy=pct(st["impr_year"]),
            fy=st["first_year"], fb=fmt(ev, st["first_best"], m), it=pct(st["impr_total"]), rounds=st["n_rounds"],
            tit=len(podium_str(w, "España", ev, 1)), pod=len(podium_str(w, "España", ev)), bp=best_place_es(w, ev, iso),
            intl=[[t, y, pl] for (t, y, e2, pl, _) in podiums.get(w, []) if e2 == ev and t != "España"],
            nrv=(["S"] if st["nr_s"] == 1 else []) + (["M"] if st["nr_a"] == 1 else []),
            years={str(y): fmt(ev, st["per_year"][y], m) for y in sorted(st["per_year"])},
        ))
    newcomers = [p["registrantId"] for p in accepted if not p.get("wcaId") and ev in p["registration"]["eventIds"]]
    last = champ_winners.get(("SpanishChampionship2025", ev), [])
    absw = [x for x in champ_res.get("SpanishChampionship2025", []) if x["event_id"] == ev and x["round_type_id"] in ("f", "c") and x["pos"] == 1]
    top20 = [r for r in rows if r["seed"] <= 20]
    imp = max([(r["iy"], r["id"]) for r in top20 if r["iy"] is not None], default=None)
    tt = max(top20, key=lambda r: r["tit"], default=None)
    EV_OUT.append(dict(
        id=ev, name=EV_NAME[ev], metric=m, rows=rows, newcomers=newcomers,
        champ2025=dict(es=last[0] if last else None, esName=names.get(last[0]) if last else None,
                       podium=[names.get(x) for x in last],
                       defends=bool(last and last[0] in reg_ids),
                       abs=[dict(name=x["name"], iso=x["country_iso2"], here=x["wca_id"] in reg_ids) for x in absw]),
        keys=dict(impr=dict(id=imp[1], v=imp[0]) if imp else None,
                  titles=dict(id=tt["id"], v=tt["tit"]) if tt and tt["tit"] else None),
    ))

PERS = []
for p in accepted:
    w = p.get("wcaId")
    base_ = dict(name=p["name"], iso=p["countryIso2"], gender=p.get("gender"), events=p["registration"]["eventIds"],
                 avatar=(p.get("avatar") or {}).get("thumbUrl"), rid=p["registrantId"])
    if not w or w not in P:
        base_.update(id=w or f"NEW{p['registrantId']}", newcomer=not w)
        PERS.append(base_); continue
    info = P[w]["info"]; per = info["person"]
    debut = min(P[w]["cdate"].values()).year if P[w]["cdate"] else None
    def det(t): return [[EV_NAME.get(ev, ev), y, pl] for (tt_, y, ev, pl, _) in sorted(podiums.get(w, []), key=lambda x: (x[1], x[2])) if tt_ == t]
    att = lambda t: sorted({int(champ_info[c]["start_date"][:4]) for c in P[w]["cdate"] if c in champ_info and ctype(c) == t and not c.startswith("FMC")})
    base_.update(
        id=w, newcomer=False, country=per["country"]["name"], debut=debut, comps=info["competition_count"], solves=info.get("total_solves"),
        medals=[info["medals"]["gold"], info["medals"]["silver"], info["medals"]["bronze"]],
        records=[info["records"]["national"], info["records"]["continental"], info["records"]["world"]],
        nrv=[EV_NAME.get(ev, ev) + (" (S)" if k == "single" else " (M)") for ev, d in info["personal_records"].items() for k, v in d.items() if v.get("country_rank") == 1],
        es=dict(years=att("España"), pod=det("España")), eu=dict(years=att("Europeo"), pod=det("Europeo")), wc=dict(years=att("Mundial"), pod=det("Mundial")),
        seeds={ev: [full_rank[ev].get(w), es_rank[ev].get(w)] for ev in p["registration"]["eventIds"] if ev in full_rank},
        url=per["url"],
    )
    PERS.append(base_)

PAL = []
for cid in sorted([c for c in champ_info if ctype(c) == "España"], key=lambda c: champ_info[c]["start_date"], reverse=True):
    for ev in events + ["333fm"]:
        if (cid, ev) in champ_winners:
            PAL.append(dict(y=int(champ_info[cid]["start_date"][:4]), ev=EV_NAME.get(ev, ev), pod=[dict(name=names.get(x, x), here=x in reg_ids, id=x) for x in champ_winners[(cid, ev)]]))

defend = sum(1 for e in EV_OUT if e["champ2025"]["defends"])
OUTD = dict(
    meta=dict(name="Campeonato de España 2026", start="2026-12-05", end="2026-12-07", updated=TODAY.isoformat(), years=years,
              kpis=dict(competitors=len(accepted), countries=len({p["countryIso2"] for p in accepted}),
                        newcomers=sum(1 for p in accepted if not p.get("wcaId")), events=len(events), defend=defend)),
    events=EV_OUT, persons=PERS, palmares=PAL,
)
json.dump(OUTD, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("saved", OUT, os.path.getsize(OUT) // 1024, "KB", len(PERS), "persons", sum(1 for x in PERS if 'comps' in x), "with data")
