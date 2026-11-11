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
    _c = sorted((k, p["wcaId"]) for p in _wc["persons"] if p.get("wcaId") and p.get("registration") and p["registration"]["status"] == "accepted"
                and _ev in p["registration"]["eventIds"] for k in [_key(p, _ev)] if k is not None)
    full_rank[_ev] = {w: i for i, (_, w) in enumerate(_c, 1)}
reg = {p["wcaId"]: p for p in wcif["persons"] if p.get("wcaId")}
accepted = [p for p in wcif["persons"] if p.get("registration") and p["registration"]["status"] == "accepted"]

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
for w in sorted({x for v in list(top.values()) + list(top_es.values()) for x in v}):
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
# ================= PRESENTATION LAYER =================
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import FormulaRule, DataBarRule

FONT = "Arial"
WHITE = "FFFFFF"
INK = "1A202C"       # main text
MUTED = "5A6577"
NAVY = "14213D"
LINE = "D5DBE5"
ZEBRA = "F4F6FA"
# group colours: (dark band, light header tint)
G = {
    "id":    ("14213D", "D9DEE8"),
    "pb":    ("1D4E89", "D6E4F5"),
    "form":  ("0B7A75", "D2EFEC"),
    "evo":   ("5B3A9B", "E5DCF3"),
    "palm":  ("A8661A", "F8E6CC"),
    "year":  ("475569", "E2E8F0"),
    "med":   ("A8661A", "F8E6CC"),
    "rec":   ("A3214A", "F6D5E0"),
    "es":    ("B4232C", "F9D9DA"),
    "eu":    ("1D4E89", "D6E4F5"),
    "wc":    ("0B7A75", "D2EFEC"),
    "now":   ("5B3A9B", "E5DCF3"),
    "link":  ("475569", "E2E8F0"),
}
GOLD, SILVER, BRONZE = "FFE08A", "DDE1E7", "F3C9A8"
side = Side(style="thin", color=LINE)
BOX = Border(left=side, right=side, top=side, bottom=side)
HB = Border(bottom=Side(style="thin", color=LINE))

def fill(c): return PatternFill("solid", fgColor=c)

def setc(ws, r, c, v=None, bold=False, size=10, color=INK, bg=None, h="center", wrap=False, italic=False, border=HB, v_al="center"):
    cell = ws.cell(row=r, column=c)
    if v is not None: cell.value = v
    cell.font = Font(name=FONT, bold=bold, size=size, color=color, italic=italic)
    if bg: cell.fill = fill(bg)
    cell.alignment = Alignment(horizontal=h, vertical=v_al, wrap_text=wrap, indent=1 if h == "left" else 0)
    if border: cell.border = border
    return cell

def banner(ws, title_txt, sub, c0, c1):
    ws.sheet_view.showGridLines = False
    ws.merge_cells(start_row=1, start_column=c0, end_row=1, end_column=c1)
    ws.merge_cells(start_row=2, start_column=c0, end_row=2, end_column=c1)
    for c in range(c0, c1 + 1):
        ws.cell(row=1, column=c).fill = fill(NAVY); ws.cell(row=2, column=c).fill = fill("E8ECF3")
    setc(ws, 1, c0, title_txt, bold=True, size=16, color=WHITE, bg=NAVY, h="left", border=None)
    setc(ws, 2, c0, sub, size=9, color=MUTED, bg="E8ECF3", h="left", italic=True, border=None)
    ws.row_dimensions[1].height = 34; ws.row_dimensions[2].height = 20

def bands(ws, row, c0, groups):
    """groups: list of (label, ncols, key)"""
    c = c0
    for label, n, key in groups:
        dark = G[key][0]
        if n > 1: ws.merge_cells(start_row=row, start_column=c, end_row=row, end_column=c + n - 1)
        for k in range(c, c + n):
            ws.cell(row=row, column=k).fill = fill(dark)
            ws.cell(row=row, column=k).border = Border(left=Side(style="medium", color=WHITE) if k == c else None)
        setc(ws, row, c, label.upper(), bold=True, size=9, color=WHITE, bg=dark, border=Border(left=Side(style="medium", color=WHITE)))
        c += n
    ws.row_dimensions[row].height = 20

def headers(ws, row, c0, cols, groups, notes=None, special=None):
    keys = [k for _, n, k in groups for _ in range(n)]
    for i, name in enumerate(cols):
        key = keys[i]
        bg = (special or {}).get(name, G[key][1])
        first = i == 0 or keys[i - 1] != key
        cell = setc(ws, row, c0 + i, name, bold=True, size=9, color=INK, bg=bg, wrap=True,
                    border=Border(left=Side(style="medium", color=WHITE) if first else Side(style="thin", color=WHITE),
                                  bottom=Side(style="medium", color=G[key][0])))
        if notes and name in notes:
            cell.comment = Comment(notes[name], "Datos WCA")
    ws.row_dimensions[row].height = 40

def body(ws, r0, r1, c0, c1, left=(), bold=(), zebra=True, height=19, wrap=()):
    for r in range(r0, r1 + 1):
        bg = ZEBRA if zebra and (r - r0) % 2 else WHITE
        for c in range(c0, c1 + 1):
            setc(ws, r, c, None, bold=c in bold, bg=bg, h="left" if c in left else "center", wrap=c in wrap)
        ws.row_dimensions[r].height = height

def widths(ws, ws_w, start=1):
    for i, w in enumerate(ws_w, start):
        ws.column_dimensions[get_column_letter(i)].width = w

def nm(w): return P[w]["info"]["person"]["name"] if w in P else names.get(w, reg.get(w, {}).get("name", w))

names = {}
for res in champ_res.values():
    for x in res: names[x["wca_id"]] = x["name"]
reg_ids = {p.get("wcaId") for p in accepted if p.get("wcaId")}

wb = Workbook()

# ---------------- Fichas ----------------
ws = wb.active; ws.title = "Fichas competidores"; ws.sheet_properties.tabColor = "14213D"
cols = ["Nombre", "WCA ID", "País", "Género",
        "Debut WCA", "Años compitiendo", "Competiciones", "Solves oficiales",
        "Oros", "Platas", "Bronces", "Medallas totales",
        "NR", "CR (ER)", "WR", "Récords totales", "NR vigente en…",
        "Ctos. España disputados", "Títulos de España", "Podios Cto. España", "Detalle podios España",
        "Europeos disputados", "Podios Europeo", "Detalle podios Europeo",
        "Mundiales disputados", "Podios Mundial", "Detalle podios Mundial",
        "Eventos inscritos 2026", "Nº eventos en top 20", "Seeds (general)", "Seeds (entre españoles)", "Perfil WCA"]
fgroups = [("Competidor", 4, "id"), ("Trayectoria", 4, "year"), ("Medallas WCA (todas las competiciones)", 4, "med"),
           ("Récords", 5, "rec"), ("Campeonato de España", 4, "es"), ("Europeo", 3, "eu"), ("Mundial", 3, "wc"),
           ("En este campeonato", 4, "now"), ("Enlace", 1, "link")]
notes = {"Debut WCA": "Año de la primera competición oficial.",
         "Medallas totales": "Medallas en finales de cualquier competición WCA (según perfil WCA).",
         "NR vigente en…": "Eventos en los que su marca es actualmente el récord de su país. (S) single, (M) media.",
         "Títulos de España": "Veces que fue el mejor español en la final de un evento del Campeonato de España (incluye FMC Spanish Championship).",
         "Podios Europeo": "Podios entre ciudadanos europeos en la final del Campeonato de Europa.",
         "Seeds (general)": "Posición en el psych sheet de este campeonato (por media; BLD/Multi por single)."}
banner(ws, "Fichas de competidores · Campeonato de España 2026",
       f"Todos los que están en el top 20 general o en el top 20 de españoles de algún evento · Fuente: API pública WCA, {TODAY.strftime('%d/%m/%Y')} · Pasa el ratón por las cabeceras con triángulo rojo para ver la definición",
       1, len(cols))
bands(ws, 3, 1, fgroups)
headers(ws, 4, 1, cols, fgroups, notes, special={"Oros": GOLD, "Platas": SILVER, "Bronces": BRONZE})
seeds = collections.defaultdict(list); seeds_es = collections.defaultdict(list)
for ev in events:
    for i, w in enumerate(top[ev], 1): seeds[w].append(f"{EV_NAME[ev]} #{i}")
    for i, w in enumerate(top_es[ev], 1): seeds_es[w].append(f"{EV_NAME[ev]} #{i}")
order = sorted(P, key=lambda w: (-len(seeds[w]), min([int(s.split('#')[1]) for s in seeds[w]] or [99]), -len(seeds_es[w]), w))
r = 5
MEDAL = {1: "🥇", 2: "🥈", 3: "🥉"}
for w in order:
    p = P[w]; info = p["info"]; per = info["person"]
    debut = min(p["cdate"].values()).year if p["cdate"] else None
    nr_events = [EV_NAME.get(ev, ev) + (" (S)" if k == "single" else " (M)") for ev, d in info["personal_records"].items()
                 for k, v in d.items() if v.get("country_rank") == 1]
    def det(t):
        return "  ".join(f"{MEDAL[pl]} {EV_NAME.get(ev, ev)} {y}" for (tt, y, ev, pl, _) in sorted(podiums.get(w, []), key=lambda x: (x[1], x[2])) if tt == t)
    es_att = len({c for c in p["cdate"] if c in champ_info and ctype(c) == "España" and not c.startswith("FMC")})
    eu_att = len({c for c in p["cdate"] if c in champ_info and ctype(c) == "Europeo"})
    wc_att = len({c for c in p["cdate"] if c in champ_info and ctype(c) == "Mundial"})
    row = [per["name"], w, per["country"]["name"], {"m": "M", "f": "F"}.get(per.get("gender"), "O"), debut,
           (TODAY.year - debut + 1) if debut else None, info["competition_count"], info.get("total_solves"),
           info["medals"]["gold"], info["medals"]["silver"], info["medals"]["bronze"], f"=SUM(I{r}:K{r})",
           info["records"]["national"], info["records"]["continental"], info["records"]["world"], f"=SUM(M{r}:O{r})",
           ", ".join(nr_events), es_att, len(podium_str(w, "España", place=1)), len(podium_str(w, "España")), det("España"),
           eu_att, len(podium_str(w, "Europeo")), det("Europeo"), wc_att, len(podium_str(w, "Mundial")), det("Mundial"),
           ", ".join(EV_NAME.get(e, e) for e in reg[w]["registration"]["eventIds"]), len(seeds[w]), ", ".join(seeds[w]), ", ".join(seeds_es[w]), "Ver perfil ↗"]
    for c, v in enumerate(row, 1):
        ws.cell(row=r, column=c, value=v)
    ws.cell(row=r, column=len(cols)).hyperlink = per["url"]
    r += 1
last = r - 1
body(ws, 5, last, 1, len(cols), left=(1, 3, 17, 21, 24, 27, 28, 30, 31), bold=(1, 12, 16, 19))
for rr in range(5, last + 1):
    ws.cell(row=rr, column=len(cols)).font = Font(name=FONT, size=10, color="1D4E89", underline="single")
    ws.cell(row=rr, column=2).font = Font(name=FONT, size=9, color=MUTED)
    for c in (8,): ws.cell(row=rr, column=c).number_format = "#,##0"
ws.conditional_formatting.add(f"L5:L{last}", DataBarRule(start_type="num", start_value=0, end_type="max", color="E0A23B"))
ws.conditional_formatting.add(f"P5:P{last}", DataBarRule(start_type="num", start_value=0, end_type="max", color="C2456E"))
ws.conditional_formatting.add(f"S5:S{last}", FormulaRule(formula=["S5>0"], fill=fill("F9D9DA"), font=Font(name=FONT, bold=True, color="B4232C")))
ws.conditional_formatting.add(f"O5:O{last}", FormulaRule(formula=["O5>0"], fill=fill("FFE08A"), font=Font(name=FONT, bold=True)))
ws.conditional_formatting.add(f"Q5:Q{last}", FormulaRule(formula=["LEN(Q5)>0"], font=Font(name=FONT, color="A3214A", bold=True)))
widths(ws, [30, 12, 14, 8, 9, 12, 12, 10, 7, 7, 8, 12, 7, 7, 6, 10, 30, 11, 10, 10, 50, 10, 9, 36, 10, 9, 30, 50, 9, 50, 50, 12])
ws.freeze_panes = "B5"; ws.auto_filter.ref = f"A4:{get_column_letter(len(cols))}{last}"

# ---------------- Event sheets ----------------
ev_summary = {}
base = wb.create_sheet("Base eventos"); base.sheet_properties.tabColor = "A0AEC0"
years = list(range(TODAY.year - 7, TODAY.year + 1))
DATACOLS = ["Seed general", "Seed España", "Nombre", "País",
            "PB single", "Ranking nacional single", "Ranking mundial single", "PB media", "Ranking nacional media", "Ranking mundial media",
            "Mejor marca últimos 12 meses", "Media de sus resultados (12 m.)", "Mejor marca 12-24 meses atrás", "% mejora último año",
            "Primer año en el evento", "Mejor marca de su primer año", "% mejora desde su primer año", "Rondas disputadas",
            "Títulos de España", "Podios Cto. España", "Mejor puesto en Cto. España", "Podios Europeo / Mundial", "NR vigente"] + [str(y) for y in years]
EGROUPS = [("Competidor", 4, "id"), ("Marcas personales y rankings", 6, "pb"), ("Forma actual", 4, "form"),
           ("Evolución", 4, "evo"), ("Palmarés en este evento", 5, "palm"), ("Mejor marca de cada año", len(years), "year")]
PCT = [DATACOLS.index("% mejora último año"), DATACOLS.index("% mejora desde su primer año")]
NRV = DATACOLS.index("NR vigente")
setc(base, 1, 1, "Clave", bold=True, color=WHITE, bg="475569"); setc(base, 1, 2, "Evento", bold=True, color=WHITE, bg="475569")
for i, n in enumerate(DATACOLS, 3): setc(base, 1, i, n, bold=True, color=WHITE, bg="475569", wrap=True)
brow = 2
q = '"'
for ev in events:
    name = EV_NAME[ev]; sheet = name[:31]; m = metric(ev)
    ws = wb.create_sheet(sheet); ws.sheet_properties.tabColor = "1D4E89"
    members = sorted(dict.fromkeys(top[ev] + top_es[ev]), key=lambda w: full_rank[ev][w])
    ev_summary[ev] = []
    for w in members:
        st = ev_stats(w, ev)
        per = P[w]["info"]["person"]
        tit = podium_str(w, "España", ev, 1); pods = podium_str(w, "España", ev)
        best_place = None
        for cid, res in champ_res.items():
            if ctype(cid) != "España": continue
            rows = [x for x in res if x["event_id"] == ev]
            fin = []
            for rt in ("f", "c"):
                fin = [x for x in rows if x["round_type_id"] == rt]
                if fin: break
            fin = sorted([x for x in fin if x["best"] > 0], key=lambda x: x["pos"])
            pool = [x for x in fin if x["country_iso2"] == "ES"] if per["country"]["iso2"] == "ES" else fin
            for k, x in enumerate(pool, 1):
                if x["wca_id"] == w:
                    pos = k if per["country"]["iso2"] == "ES" else x["pos"]
                    best_place = pos if best_place is None else min(best_place, pos)
        intl = [f"{MEDAL[pl]} {t} {y}" for (t, y, e2, pl, _) in podiums.get(w, []) if e2 == ev and t != "España"]
        nrv = (["Single"] if st["nr_s"] == 1 else []) + (["Media"] if st["nr_a"] == 1 else [])
        seed_es = top_es[ev].index(w) + 1 if w in top_es[ev] else None
        data = [full_rank[ev][w], seed_es, per["name"], per["country"]["name"], fmt(ev, st["pb_single"]), st["nr_s"], st["wr_s"],
                fmt(ev, st["pb_avg"], "average"), st["nr_a"], st["wr_a"],
                fmt(ev, st["best12"], m) or "—", (fmt(ev, round(st["mean12"]), m) if st["mean12"] else (st["n12"] if ev == "333mbf" else "—")),
                fmt(ev, st["prev12"], m) or "—", st["impr_year"], st["first_year"], fmt(ev, st["first_best"], m), st["impr_total"],
                st["n_rounds"], len(tit), len(pods), (f"{best_place}º" if best_place else "—"), "  ".join(intl), " + ".join(nrv)] + \
               [fmt(ev, st["per_year"].get(y), m) or "·" for y in years]
        base.cell(row=brow, column=1, value=(
            f"=IF('{sheet}'!$D$3={q}Solo españoles{q},IF(D{brow}={q}{q},{q}{q},B{brow}&{q}|{q}&D{brow}),"
            f"IF(C{brow}<=20,B{brow}&{q}|{q}&C{brow},{q}{q}))"))
        base.cell(row=brow, column=2, value=ev)
        for c, v in enumerate(data, 3):
            base.cell(row=brow, column=c, value=v)
        if full_rank[ev][w] <= 20:
            ev_summary[ev].append((w, st, len(tit)))
        brow += 1

    ncol = 1 + len(DATACOLS)
    banner(ws, f"{name}  ·  Top 20 del psych sheet",
           f"Orden por {'mejor single' if m == 'single' else 'mejor media'} oficial, como el psych sheet de la WCA · Los % de mejora se calculan sobre la {'single' if m == 'single' else 'media'} · Verde = ha mejorado, rojo = ha empeorado",
           2, ncol)
    # selector
    ws.merge_cells("B3:C3"); ws.merge_cells("D3:E3")
    setc(ws, 3, 2, "MOSTRAR  ▸", bold=True, size=10, color=NAVY, h="right", border=None)
    sel = setc(ws, 3, 4, "Todos", bold=True, size=11, color=NAVY, bg="FFD45C",
               border=Border(left=Side(style="medium", color=NAVY), right=Side(style="medium", color=NAVY), top=Side(style="medium", color=NAVY), bottom=Side(style="medium", color=NAVY)))
    ws["E3"].border = Border(right=Side(style="medium", color=NAVY), top=Side(style="medium", color=NAVY), bottom=Side(style="medium", color=NAVY))
    ws["E3"].fill = fill("FFD45C")
    dv = DataValidation(type="list", formula1='"Todos,Solo españoles"', allow_blank=False)
    dv.promptTitle = "Filtro de nacionalidad"; dv.prompt = "Todos = top 20 general · Solo españoles = top 20 de españoles"
    ws.add_data_validation(dv); dv.add("D3")
    ws.merge_cells(start_row=3, start_column=6, end_row=3, end_column=14)
    setc(ws, 3, 6, "◂ Despliega la celda amarilla:  Todos  /  Solo españoles (incluye españoles fuera del top 20 general)", size=9, color=MUTED, italic=True, h="left", border=None)
    ws.row_dimensions[3].height = 26
    bands(ws, 4, 2, EGROUPS)
    hl_pb = "PB single" if m == "single" else "PB media"
    headers(ws, 5, 2, DATACOLS, EGROUPS, {
        "Seed general": "Puesto en el psych sheet entre todos los inscritos.",
        "Seed España": "Puesto entre los inscritos con nacionalidad española.",
        "% mejora último año": "Mejor marca de los últimos 12 meses frente a la mejor de los 12 meses anteriores. Positivo = ha mejorado." + (" Multi-BLD: en puntos." if ev == "333mbf" else ""),
        "% mejora desde su primer año": "Mejor marca de su primer año en el evento frente a su PB actual.",
        "Media de sus resultados (12 m.)": "Promedio de todas sus medias/singles oficiales de los últimos 12 meses: regularidad / forma actual." if ev != "333mbf" else "En Multi-BLD: nº de intentos en los últimos 12 meses.",
        "Mejor puesto en Cto. España": "Mejor posición entre españoles en la final del Campeonato de España (extranjeros: puesto general)."},
        special={hl_pb: "9DC0EA"})
    setc(ws, 5, 1, "idx", size=8)
    R0, R1 = 6, 25
    for k in range(1, 21):
        r = R0 - 1 + k
        ws.cell(row=r, column=1, value=f"=IFERROR(MATCH(\"{ev}|\"&{k},'Base eventos'!$A:$A,0),\"\")")
        for j in range(2, ncol + 1):
            col = get_column_letter(j + 1)
            ws.cell(row=r, column=j, value=f"=IF($A{r}=\"\",\"\",IF(INDEX('Base eventos'!${col}:${col},$A{r})=\"\",\"\",INDEX('Base eventos'!${col}:${col},$A{r})))")
    pbcol = 2 + DATACOLS.index(hl_pb)
    body(ws, R0, R1, 2, ncol, left=(4, 5, 23), bold=(2, 4, pbcol), height=21)
    for r in range(R0, R1 + 1):
        ws.cell(row=r, column=pbcol).font = Font(name=FONT, size=11, bold=True, color="1D4E89")
        ws.cell(row=r, column=2).font = Font(name=FONT, size=11, bold=True, color=NAVY)
        ws.cell(row=r, column=3).font = Font(name=FONT, size=10, color=MUTED)
        for p in PCT:
            ws.cell(row=r, column=p + 2).number_format = "+0.0%;-0.0%;0.0%"
        for c in range(2 + DATACOLS.index(str(years[0])), ncol + 1):
            ws.cell(row=r, column=c).font = Font(name=FONT, size=9, color="334155")
    for r, col in ((R0, GOLD), (R0 + 1, SILVER), (R0 + 2, BRONZE)):
        for c in (2, 3, 4, 5):
            ws.cell(row=r, column=c).fill = fill(col)
    for p in PCT:
        L = get_column_letter(p + 2)
        ws.conditional_formatting.add(f"{L}{R0}:{L}{R1}", FormulaRule(formula=[f'AND(ISNUMBER({L}{R0}),{L}{R0}>0)'], font=Font(name=FONT, bold=True, color="0E7A3E"), fill=fill("DCF2E3")))
        ws.conditional_formatting.add(f"{L}{R0}:{L}{R1}", FormulaRule(formula=[f'AND(ISNUMBER({L}{R0}),{L}{R0}<0)'], font=Font(name=FONT, bold=True, color="B42318"), fill=fill("FBE3E1")))
    L = get_column_letter(NRV + 2)
    ws.conditional_formatting.add(f"{L}{R0}:{L}{R1}", FormulaRule(formula=[f'LEN({L}{R0})>0'], fill=fill("A3214A"), font=Font(name=FONT, bold=True, color=WHITE)))
    for name_ in ("Títulos de España",):
        L = get_column_letter(2 + DATACOLS.index(name_))
        ws.conditional_formatting.add(f"{L}{R0}:{L}{R1}", FormulaRule(formula=[f'AND(ISNUMBER({L}{R0}),{L}{R0}>0)'], fill=fill("FFE08A"), font=Font(name=FONT, bold=True)))
    # Spanish seed highlight in Todos mode
    ws.conditional_formatting.add(f"C{R0}:C{R1}", FormulaRule(formula=[f'ISNUMBER(C{R0})'], font=Font(name=FONT, bold=True, color="B4232C")))
    widths(ws, [3, 8, 8, 30, 14, 10, 10, 10, 10, 10, 10, 11, 11, 11, 10, 9, 10, 10, 9, 9, 9, 10, 28, 14] + [9] * len(years))
    ws.column_dimensions["A"].hidden = True
    ws.freeze_panes = "F6"

body(base, 2, brow - 1, 1, 2 + len(DATACOLS), left=(1, 5, 6), height=16)
for r in range(2, brow):
    for p in PCT:
        base.cell(row=r, column=p + 3).number_format = "+0.0%;-0.0%;0.0%"
base.freeze_panes = "C2"; base.auto_filter.ref = f"A1:{get_column_letter(2 + len(DATACOLS))}{brow - 1}"
widths(base, [10, 8, 8, 8, 28, 12] + [10] * len(DATACOLS)); base.row_dimensions[1].height = 40

# ---------------- Palmarés ----------------
ws = wb.create_sheet("Palmarés Cto. España"); ws.sheet_properties.tabColor = "B4232C"
banner(ws, "Palmarés del Campeonato de España", "Podio de españoles en la final de cada evento, 2004-2025 · Nombres en rojo = inscritos en 2026", 1, 6)
pg = [("Edición", 3, "id"), ("Podio (mejores españoles)", 3, "es")]
bands(ws, 3, 1, pg)
headers(ws, 4, 1, ["Año", "Competición", "Evento", "🥇 Oro", "🥈 Plata", "🥉 Bronce"], pg, special={"🥇 Oro": GOLD, "🥈 Plata": SILVER, "🥉 Bronce": BRONZE})
es_champs = sorted([c for c in champ_info if ctype(c) == "España"], key=lambda c: champ_info[c]["start_date"], reverse=True)
r = 5; band_rows = []
for i, cid in enumerate(es_champs):
    y = champ_info[cid]["start_date"][:4]
    for ev in events + ["333fm"]:
        if (cid, ev) not in champ_winners: continue
        wl = champ_winners[(cid, ev)]
        vals = [int(y), champ_info[cid]["name"], EV_NAME.get(ev, ev)] + [names.get(x, x) for x in wl] + [""] * (3 - len(wl))
        for c, v in enumerate(vals, 1): ws.cell(row=r, column=c, value=v)
        band_rows.append((r, i % 2, wl))
        r += 1
body(ws, 5, r - 1, 1, 6, left=(2, 3, 4, 5, 6), zebra=False)
for rr, alt, wl in band_rows:
    bg = "FDF1F1" if alt else WHITE
    for c in range(1, 7): ws.cell(row=rr, column=c).fill = fill(bg)
    ws.cell(row=rr, column=1).font = Font(name=FONT, bold=True, color="B4232C")
    for k, x in enumerate(wl):
        if x in reg_ids:
            ws.cell(row=rr, column=4 + k).font = Font(name=FONT, size=10, bold=True, color="B4232C")
widths(ws, [8, 32, 13, 32, 32, 32]); ws.freeze_panes = "A5"; ws.auto_filter.ref = f"A4:F{r - 1}"

# ---------------- Ranking títulos ----------------
ws = wb.create_sheet("Ranking títulos España"); ws.sheet_properties.tabColor = "B4232C"
banner(ws, "Inscritos 2026 con más títulos de Campeón de España", "Histórico, todos los eventos (incluye FMC Spanish Championship)", 1, 7)
tg = [("Competidor", 2, "id"), ("Podios en el Campeonato de España", 4, "es"), ("Detalle", 1, "link")]
bands(ws, 3, 1, tg)
headers(ws, 4, 1, ["Nombre", "País", "🥇 Títulos", "🥈 Platas", "🥉 Bronces", "Podios totales", "Eventos en los que ha sido campeón"], tg,
        special={"🥇 Títulos": GOLD, "🥈 Platas": SILVER, "🥉 Bronces": BRONZE})
rows = []
for w in reg_ids:
    pl = [x for x in podiums.get(w, []) if x[0] == "España"]
    if not pl: continue
    rows.append((names.get(w, reg[w]["name"]), reg[w]["countryIso2"], sum(1 for x in pl if x[3] == 1), sum(1 for x in pl if x[3] == 2), sum(1 for x in pl if x[3] == 3),
                 ", ".join(sorted({EV_NAME.get(x[2], x[2]) for x in pl if x[3] == 1}))))
rows.sort(key=lambda x: (-x[2], -x[3], -x[4]))
r = 5
for x in rows:
    for c, v in enumerate([x[0], x[1], x[2], x[3], x[4], f"=SUM(C{r}:E{r})", x[5]], 1):
        ws.cell(row=r, column=c, value=v)
    r += 1
body(ws, 5, r - 1, 1, 7, left=(1, 7), bold=(1, 3, 6))
ws.conditional_formatting.add(f"C5:C{r - 1}", DataBarRule(start_type="num", start_value=0, end_type="max", color="E0A23B"))
ws.conditional_formatting.add(f"F5:F{r - 1}", DataBarRule(start_type="num", start_value=0, end_type="max", color="B4232C"))
widths(ws, [32, 8, 12, 10, 10, 12, 60]); ws.freeze_panes = "B5"

# ---------------- Datos para comentar ----------------
ws = wb.create_sheet("Datos para comentar", 0); ws.sheet_properties.tabColor = "FFB703"
NC = 15
banner(ws, "Campeonato de España 2026  ·  Datos clave para la retransmisión",
       f"Fuente: API pública WCA · {TODAY.strftime('%d/%m/%Y')} · Detalle de cada evento en su pestaña; fichas personales en 'Fichas competidores'", 1, NC)
# KPI tiles
defend = sum(1 for ev in events if champ_winners.get(("SpanishChampionship2025", ev)) and champ_winners[("SpanishChampionship2025", ev)][0] in reg_ids)
kpis = [(len(accepted), "competidores", "1D4E89"),
        (len({p['countryIso2'] for p in accepted}), "países", "0B7A75"),
        (sum(1 for p in accepted if not p.get('wcaId')), "debutantes", "5B3A9B"),
        (len(events), "eventos", "A8661A"),
        (f"{defend}/{len(events)}", "campeones 2025 que defienden título", "B4232C")]
ws.row_dimensions[3].height = 8
c = 1
for val, lab, col in kpis:
    ws.merge_cells(start_row=4, start_column=c, end_row=4, end_column=c + 2)
    ws.merge_cells(start_row=5, start_column=c, end_row=5, end_column=c + 2)
    for k in range(c, c + 3):
        ws.cell(row=4, column=k).fill = fill(col); ws.cell(row=5, column=k).fill = fill(col)
    setc(ws, 4, c, val, bold=True, size=22, color=WHITE, bg=col, border=None, v_al="bottom")
    setc(ws, 5, c, lab.upper(), bold=True, size=8, color=WHITE, bg=col, border=None, v_al="top")
    c += 3
ws.row_dimensions[4].height = 34; ws.row_dimensions[5].height = 18; ws.row_dimensions[6].height = 10
cols = ["Evento", "Favorito (seed 1)", "Su PB", "Seed 2", "Seed 3",
        "Mejor español", "2º español", "3º español",
        "Campeón de España 2025", "¿Defiende?", "Ganador absoluto 2025",
        "Récord nacional vigente (inscritos)", "Mayor mejora último año", "Más títulos de España en el evento", "Mejor forma (últ. 12 meses)"]
dg = [("", 1, "id"), ("Favoritos (todas las nacionalidades)", 4, "pb"), ("Favoritos españoles", 3, "es"),
      ("Campeón vigente", 3, "palm"), ("Claves para comentar", 4, "form")]
bands(ws, 7, 1, dg)
headers(ws, 8, 1, cols, dg, {"Mejor español": "Entre paréntesis: puesto en la general (todas las nacionalidades) y su marca.",
                             "Campeón de España 2025": "Mejor español en la final de 2025 (el título nacional).",
                             "Ganador absoluto 2025": "Primer puesto de la final 2025 contando extranjeros.",
                             "Récord nacional vigente (inscritos)": "Inscritos del top 20 que tienen ahora mismo el récord de su país. S = single, M = media."})
def abs_winner(ev):
    rows = [x for x in champ_res.get("SpanishChampionship2025", []) if x["event_id"] == ev and x["round_type_id"] in ("f", "c") and x["pos"] == 1]
    return ", ".join(f"{x['name']} ({x['country_iso2']})" + (" ✔" if x["wca_id"] in reg_ids else "") for x in rows) or "—"
r = 9
row_h = {}
for ev in events:
    lst = ev_summary[ev]; m = metric(ev)
    w1, st1 = lst[0][0], lst[0][1]
    pb1 = fmt(ev, st1["pb_single"] if m == "single" else st1["pb_avg"], m)
    lastw = champ_winners.get(("SpanishChampionship2025", ev), [])
    defending = lastw[0] if lastw else None
    nrh = [nm(w) + f" ({'S' if st['nr_s'] == 1 else ''}{'+' if st['nr_s'] == 1 and st['nr_a'] == 1 else ''}{'M' if st['nr_a'] == 1 else ''})" for w, st, _ in lst if st["nr_s"] == 1 or st["nr_a"] == 1]
    imp = max([(st["impr_year"], w) for w, st, _ in lst if st["impr_year"] is not None], default=None)
    tt = max(lst, key=lambda x: x[2])
    form = min([(st["best12"], w) for w, st, _ in lst if st["best12"]], default=None)
    _es = top_es[ev]
    def esf(i):
        if len(_es) <= i: return "—"
        w = _es[i]; s = ev_stats(w, ev)
        return f"{nm(w)}\n{full_rank[ev][w]}º general · {fmt(ev, s['pb_single' if m == 'single' else 'pb_avg'], m)}"
    row = [EV_NAME[ev], nm(w1), pb1, nm(lst[1][0]) if len(lst) > 1 else "", nm(lst[2][0]) if len(lst) > 2 else "", esf(0), esf(1), esf(2),
           names.get(defending, "") if defending else "—", ("Sí" if defending in reg_ids else "No") if defending else "—", abs_winner(ev),
           "\n".join(nrh) or "—", f"{nm(imp[1])} ({imp[0]:+.1%})" if imp else "—",
           f"{nm(tt[0])} ({tt[2]})" if tt[2] else "—", f"{nm(form[1])} ({fmt(ev, form[0], m)})" if form else "—"]
    for c, v in enumerate(row, 1): ws.cell(row=r, column=c, value=v)
    row_h[r] = max(48, 14 * max(len(nrh), 2) + 12)
    r += 1
dlast = r - 1
body(ws, 9, dlast, 1, NC, left=tuple(range(2, NC + 1)), wrap=tuple(range(1, NC + 1)), height=48)
for rr in range(9, dlast + 1):
    ws.row_dimensions[rr].height = row_h[rr]
    setc(ws, rr, 1, None, bold=True, size=11, color=WHITE, bg=NAVY, border=Border(bottom=Side(style="thin", color="3B4A6B")))
    ws.cell(row=rr, column=2).font = Font(name=FONT, size=10, bold=True, color="1D4E89")
    ws.cell(row=rr, column=3).font = Font(name=FONT, size=11, bold=True, color="1D4E89")
    ws.cell(row=rr, column=6).font = Font(name=FONT, size=10, bold=True, color="B4232C")
    ws.cell(row=rr, column=9).font = Font(name=FONT, size=10, bold=True, color="A8661A")
ws.conditional_formatting.add(f"J9:J{dlast}", FormulaRule(formula=['J9="Sí"'], fill=fill("DCF2E3"), font=Font(name=FONT, bold=True, color="0E7A3E")))
ws.conditional_formatting.add(f"J9:J{dlast}", FormulaRule(formula=['J9="No"'], fill=fill("FBE3E1"), font=Font(name=FONT, bold=True, color="B42318")))
widths(ws, [12, 22, 9, 20, 20, 24, 24, 24, 22, 9, 24, 28, 26, 24, 24])
ws.freeze_panes = "B9"

# Curiosities
r = dlast + 2
ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=NC)
for k in range(1, NC + 1): ws.cell(row=r, column=k).fill = fill(NAVY)
setc(ws, r, 1, "CURIOSIDADES Y RÉCORDS DEL CARTEL", bold=True, size=12, color=WHITE, bg=NAVY, h="left", border=None)
ws.row_dimensions[r].height = 26; r += 1
def topby(f, n=5, rev=True): return sorted(P, key=f, reverse=rev)[:n]
es_cnt = lambda w: len({c for c in P[w]['cdate'] if c in champ_info and ctype(c) == 'España' and not c.startswith('FMC')})
facts = [
    ("🏅", "Más medallas WCA", "  ·  ".join(f"{nm(w)} ({P[w]['info']['medals']['total']})" for w in topby(lambda w: P[w]['info']['medals']['total']))),
    ("🥇", "Más oros WCA", "  ·  ".join(f"{nm(w)} ({P[w]['info']['medals']['gold']})" for w in topby(lambda w: P[w]['info']['medals']['gold']))),
    ("🌍", "Han batido un récord mundial", "  ·  ".join(f"{nm(w)} ({P[w]['info']['records']['world']} WR)" for w in P if P[w]['info']['records']['world']) or "Ninguno"),
    ("🇪🇺", "Han batido un récord de Europa", "  ·  ".join(f"{nm(w)} ({P[w]['info']['records']['continental']})" for w in sorted([w for w in P if P[w]['info']['records']['continental']], key=lambda w: -P[w]['info']['records']['continental'])) or "Ninguno"),
    ("📈", "Más récords (NR + ER + WR)", "  ·  ".join(f"{nm(w)} ({P[w]['info']['records']['total']})" for w in topby(lambda w: P[w]['info']['records']['total']) if P[w]['info']['records']['total'])),
    ("🗓", "Más competiciones disputadas", "  ·  ".join(f"{nm(w)} ({P[w]['info']['competition_count']})" for w in topby(lambda w: P[w]['info']['competition_count']))),
    ("🧩", "Más solves oficiales", "  ·  ".join(f"{nm(w)} ({P[w]['info']['total_solves']:,})".replace(",", ".") for w in topby(lambda w: P[w]['info'].get('total_solves') or 0))),
    ("🇪🇸", "Más Campeonatos de España disputados", "  ·  ".join(f"{nm(w)} ({es_cnt(w)})" for w in sorted(P, key=lambda w: -es_cnt(w))[:5])),
    ("🎯", "Presentes en más tops 20", "  ·  ".join(f"{nm(w)} ({len(seeds[w])} eventos)" for w in topby(lambda w: len(seeds[w])))),
    ("👴", "Veteranos (debut más antiguo)", "  ·  ".join(f"{nm(w)} ({min(P[w]['cdate'].values()).year})" for w in topby(lambda w: min(P[w]['cdate'].values()), rev=False))),
    ("🌱", "Debut más reciente", "  ·  ".join(f"{nm(w)} ({min(P[w]['cdate'].values()).strftime('%m/%Y')})" for w in topby(lambda w: min(P[w]['cdate'].values())))),
    ("✨", "Primer Campeonato de España", "  ·  ".join(nm(w) for w in P if not any(c in champ_info and ctype(c) == 'España' for c in P[w]['cdate'])) or "—"),
    ("✈", "Extranjeros inscritos (no optan al título nacional)", "  ·  ".join(f"{n} ({c})" for n, c in sorted({(reg[p['wcaId']]['name'] if p.get('wcaId') else p['name'], p['countryIso2']) for p in accepted if p['countryIso2'] != 'ES'}, key=lambda x: x[1])) or "—"),
]
for i, (ico, k, v) in enumerate(facts):
    bg = ZEBRA if i % 2 else WHITE
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=3)
    for kk in range(1, 4): ws.cell(row=r, column=kk).fill = fill("E8ECF3")
    setc(ws, r, 1, f"{ico}  {k}", bold=True, size=10, color=NAVY, bg="E8ECF3", h="left", wrap=True, border=Border(bottom=Side(style="thin", color=WHITE)))
    ws.merge_cells(start_row=r, start_column=4, end_row=r, end_column=NC)
    for kk in range(4, NC + 1): ws.cell(row=r, column=kk).fill = fill(bg)
    setc(ws, r, 4, v, size=10, bg=bg, h="left", wrap=True, border=HB)
    ws.row_dimensions[r].height = max(24, 15 * (len(v) // 210 + 1) + 8)
    r += 1

# ---------------- Metodología ----------------
ws = wb.create_sheet("Metodología"); ws.sheet_properties.tabColor = "A0AEC0"
banner(ws, "Metodología y fuentes", "Cómo se ha calculado cada dato", 1, 2)
lines = [
    ("Inscritos", f"WCIF público de SpanishChampionship2026 (API WCA), estado 'accepted' a {TODAY.strftime('%d/%m/%Y')}."),
    ("Top 20", "Orden del psych sheet WCA: por mejor media oficial; 3BLD, 4BLD, 5BLD y Multi-BLD por mejor single. Quien no tiene media va detrás de quien sí. Debutantes sin WCA ID no aparecen."),
    ("Selector", "Hojas de evento: celda amarilla 'Mostrar' (D3) con desplegable Todos / Solo españoles. 'Solo españoles' lista los 20 mejores españoles inscritos aunque estén fuera del top 20 general. Los datos salen de la hoja 'Base eventos' (no borrarla)."),
    ("Perfiles", "/api/v0/persons/{id} (medallas, récords, nº competiciones, solves) y /persons/{id}/results (historial completo)."),
    ("Medallas WCA", "Podios en finales de cualquier competición oficial (dato oficial del perfil WCA)."),
    ("Títulos de España", "Final de cada evento en los Campeonatos de España 2004-2025 (+ FMC Spanish Championship), clasificando solo a ciudadanos españoles con resultado válido."),
    ("Europeo / Mundial", "Europeo: finales del Campeonato de Europa, solo ciudadanos europeos. Mundial: puesto en la final."),
    ("% mejora", "Último año: mejor marca de los últimos 12 meses vs la de los 12 meses anteriores. Desde primer año: mejor marca de su primer año en el evento vs PB actual. En Multi-BLD, sobre los puntos."),
    ("Forma actual", "'Media de sus resultados (12 m.)': promedio de todas sus medias (o singles en BLD) oficiales del último año; mide la regularidad."),
    ("Fórmulas", "'Medallas totales', 'Récords totales' y 'Podios totales' son sumas en fórmula."),
    ("Formato", "Tiempos en m:ss.cc; Multi-BLD como resueltos/intentados tiempo."),
]
headers(ws, 3, 1, ["Concepto", "Cómo se calcula"], [("", 2, "id")])
for i, (k, v) in enumerate(lines, 4):
    ws.cell(row=i, column=1, value=k); ws.cell(row=i, column=2, value=v)
body(ws, 4, 3 + len(lines), 1, 2, left=(1, 2), bold=(1,), wrap=(2,), height=34)
widths(ws, [22, 130])

from openpyxl.workbook.properties import CalcProperties
wb.move_sheet("Base eventos", offset=len(wb.sheetnames) - 1 - wb.sheetnames.index("Base eventos"))
wb.active = 0
for s in wb.worksheets: s.sheet_view.tabSelected = (s.title == "Datos para comentar")
wb.calculation = CalcProperties(fullCalcOnLoad=True)
wb.save(OUT)
print("saved", OUT)
