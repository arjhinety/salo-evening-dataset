"""Builds the Salo Evening Dataset (compiled by Arjhine A. Ty).

Seeded and reproducible: running it again gives the same files.
Inputs (in ./sources):
  foodgo-orders.csv, foodgo-volunteers.csv   FoodGo Test Dataset, Zenodo 10.5281/zenodo.3801643 (CC BY 4.0)
  osm_roads_cubao_project4.json              OpenStreetMap roads via Overpass API (ODbL)
  foodkeeper.json (optional)                 USDA FSIS FoodKeeper (CC0)
  fnri_food_security.csv (optional)          DOST-FNRI ENNS Food Security PUF
Outputs: ./salo-evening-dataset/*.csv and salo-evening-dataset.xlsx
"""
import json, math, os, random, heapq
from collections import defaultdict
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "sources")
OUT = os.path.join(HERE, "salo-evening-dataset")
os.makedirs(OUT, exist_ok=True)
SEED = 20260927
rng = random.Random(SEED)

# ---------------------------------------------------------------- parameters + source detection
PARAMS = json.load(open(os.path.join(HERE, "params.json"), encoding="utf-8"))
P = {k: v["value"] for k, v in PARAMS.items()}
HAVE_FK = os.path.exists(os.path.join(SRC, "foodkeeper.json"))
HAVE_FNRI = os.path.exists(os.path.join(SRC, "fnri_food_security.csv"))
FK_STATUS = "FOODKEEPER" if HAVE_FK else "PLACEHOLDER"
FNRI_STATUS = "ASSUMPTION (FNRI planned, not obtained)"
if HAVE_FNRI:
    # FNRI was skipped for this submission; write its loader before using the real file
    raise SystemExit("FNRI file found: write its loader before building (see README).")

# ---------------------------------------------------------------- road graph (OSM)
osm = json.load(open(os.path.join(SRC, "osm_roads_cubao_project4.json"), encoding="utf-8"))
nodes = {e["id"]: (e["lat"], e["lon"]) for e in osm["elements"] if e["type"] == "node"}
ways = [e for e in osm["elements"] if e["type"] == "way"]


def hav(a, b):
    (la1, lo1), (la2, lo2) = a, b
    r = 6371.0
    p1, p2 = math.radians(la1), math.radians(la2)
    dp, dl = p2 - p1, math.radians(lo2 - lo1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


G = defaultdict(list)
node_street = {}
for w in ways:
    nm = w["tags"].get("name")
    hw = w["tags"]["highway"]
    one = w["tags"].get("oneway") == "yes"
    ns = w["nodes"]
    for a, b in zip(ns, ns[1:]):
        d = hav(nodes[a], nodes[b])
        G[a].append((b, d))
        G[b].append((a, d))  # volunteers on motorbikes: treat roads as two-way (stated limitation)
    if nm:
        for n in ns:
            node_street.setdefault(n, (nm, hw))

# keep the largest connected component
seen, comps = set(), []
for s in G:
    if s in seen:
        continue
    stack, comp = [s], []
    seen.add(s)
    while stack:
        u = stack.pop()
        comp.append(u)
        for v, _ in G[u]:
            if v not in seen:
                seen.add(v)
                stack.append(v)
    comps.append(comp)
main = set(max(comps, key=len))

# core study box (Cubao - Project 4), inside the downloaded box
LAT0, LAT1, LON0, LON1 = 14.615, 14.637, 121.045, 121.077
cand = [n for n in main if n in node_street and LAT0 <= nodes[n][0] <= LAT1 and LON0 <= nodes[n][1] <= LON1]
res_cand = [n for n in cand if node_street[n][1] in ("residential", "unclassified", "tertiary")]
main_cand = [n for n in cand if node_street[n][1] in ("primary", "secondary", "tertiary", "trunk")]


def pick_nodes(pool, k, min_km):
    out = []
    pool = pool[:]
    rng.shuffle(pool)
    for n in pool:
        if all(hav(nodes[n], nodes[m]) >= min_km for m in out):
            out.append(n)
        if len(out) == k:
            break
    assert len(out) == k
    return out


def dijkstra(src):
    dist = {src: 0.0}
    pq = [(0.0, src)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist.get(u, 1e9):
            continue
        for v, w in G[u]:
            nd = d + w
            if nd < dist.get(v, 1e9):
                dist[v] = nd
                heapq.heappush(pq, (nd, v))
    return dist


# ---------------------------------------------------------------- FoodGo-derived distributions
fg_o = pd.read_csv(os.path.join(SRC, "foodgo-orders.csv"))
fg_v = pd.read_csv(os.path.join(SRC, "foodgo-volunteers.csv"))
fg_qty = fg_o["Quantity"].tolist()            # load units 1-3 per order
fg_cap = fg_v["Capacity"].tolist()            # load units 3-5 per volunteer
fg_win = [json.loads(a)[0] for a in fg_v["Availability"]]
fg_win_len = [(b - a) // 100 for a, b in fg_win]  # hours (all 4 h)

# ---------------------------------------------------------------- storage rules
MAX_HOURS = {r["category"]: r["max_hours_unrefrigerated"]
             for r in json.load(open(os.path.join(HERE, "storage_rules.json"), encoding="utf-8"))}
# food item -> (FoodKeeper product ID, match quality)
FK_MAP = {  # food item -> (FoodKeeper product ID, match quality, reason)
    "chicken adobo": (135, "close", "cooked chicken dish"),
    "pork adobo": (173, "close", "cooked leftover with meat"),
    "pancit canton": (177, "close", "cooked noodles ~ cooked pasta"),
    "pancit bihon": (177, "close", "cooked rice noodles ~ cooked pasta"),
    "menudo": (173, "close", "cooked leftover with meat"),
    "chop suey": (174, "close", "cooked vegetables, no meat assumed"),
    "ginisang monggo": (174, "close", "cooked legumes/vegetables, no meat assumed"),
    "chicken tinola": (193, "close", "soup/stew"),
    "pork sinigang": (193, "close", "soup/stew"),
    "fried chicken": (135, "close", "cooked chicken dish"),
    "giniling": (173, "close", "cooked leftover with meat"),
    "steamed rice": (178, "exact", "cooked rice"),
    "lumpiang shanghai": (173, "close", "cooked leftover with meat"),
    "pandesal": (574, "close", "panaderia bread is baked fresh with few preservatives, like homemade bread"),
    "ensaymada": (574, "close", "panaderia pastry baked fresh, like homemade bread"),
    "monay": (574, "close", "panaderia bread baked fresh, like homemade bread"),
    "sliced bread": (195, "close", "packaged white sliced bread is a commercial bread product (461 is whole-wheat only)"),
    "eggplant": (284, "exact", "eggplant"),
    "tomatoes": (306, "exact", "tomatoes"),
    "pechay": (287, "close", "leafy greens"),
    "bananas": (251, "exact", "bananas"),
    "canned sardines": (619, "close", "canned seafood"),
    "instant noodles": (335, "approximate", "no instant-noodle entry; nearest is dry pasta"),
}
if not HAVE_FK:
    raise SystemExit("sources/foodkeeper.json missing: storage rules need it.")
fk = json.load(open(os.path.join(SRC, "foodkeeper.json"), encoding="utf-8"))
flat = lambda row: {k: v for c in row for k, v in c.items()}
FKP = {int(flat(r)["ID"]): flat(r) for r in [s_ for s_ in fk["sheets"] if s_["name"] == "Product"][0]["data"]}
TO_DAYS = {"Days": 1, "Weeks": 7, "Months": 30, "Years": 365}


def span(p, prefix):
    for pre in (prefix, "DOP_" + prefix):
        lo, hi, me = p.get(pre + "_Min"), p.get(pre + "_Max"), p.get(pre + "_Metric")
        if me:
            return lo, hi, me
    return None, None, None

# food items: (item, item_fil, category, unit, kg_per_unit, typical_units(min,max))
FOODS = [
    ("chicken adobo", "adobong manok", "cooked_dish", "tray", 2.0, (1, 4)),
    ("pork adobo", "adobong baboy", "cooked_dish", "tray", 2.0, (1, 3)),
    ("pancit canton", "pancit canton", "cooked_noodles", "bilao", 2.5, (1, 3)),
    ("pancit bihon", "pancit bihon", "cooked_noodles", "bilao", 2.5, (1, 3)),
    ("menudo", "menudo", "cooked_dish", "tray", 2.0, (1, 3)),
    ("chop suey", "chopsuey", "cooked_vegetables", "tray", 1.5, (1, 3)),
    ("ginisang monggo", "ginisang monggo", "cooked_vegetables", "pot", 3.0, (1, 2)),
    ("chicken tinola", "tinolang manok", "cooked_soup", "pot", 4.0, (1, 2)),
    ("pork sinigang", "sinigang na baboy", "cooked_soup", "pot", 4.0, (1, 2)),
    ("fried chicken", "pritong manok", "cooked_dish", "piece", 0.15, (10, 40)),
    ("giniling", "giniling", "cooked_dish", "tray", 2.0, (1, 3)),
    ("steamed rice", "kanin", "cooked_rice", "kg", 1.0, (2, 8)),
    ("lumpiang shanghai", "lumpiang shanghai", "cooked_dish", "piece", 0.03, (30, 120)),
    ("pandesal", "pandesal", "bread", "piece", 0.03, (20, 100)),
    ("ensaymada", "ensaymada", "bread", "piece", 0.08, (6, 30)),
    ("monay", "monay", "bread", "piece", 0.06, (10, 40)),
    ("sliced bread", "tasty", "bread", "loaf", 0.6, (2, 8)),
    ("eggplant", "talong", "fresh_vegetables", "kg", 1.0, (1, 5)),
    ("tomatoes", "kamatis", "fresh_vegetables", "kg", 1.0, (1, 4)),
    ("pechay", "pechay", "leafy_greens", "kg", 1.0, (1, 3)),
    ("bananas", "saging", "fruit", "kg", 1.0, (1, 5)),
    ("canned sardines", "de lata na sardinas", "packaged_shelf_stable", "can", 0.155, (6, 24)),
    ("instant noodles", "instant noodles", "packaged_shelf_stable", "pack", 0.06, (10, 40)),
]
FOOD_W = {"cooked_dish": 30, "cooked_noodles": 12, "cooked_vegetables": 8, "cooked_soup": 6, "cooked_rice": 8,
          "bread": 18, "fresh_vegetables": 6, "leafy_greens": 3, "fruit": 4, "packaged_shelf_stable": 5}

srows = []
for f in FOODS:
    pid, quality, reason = FK_MAP[f[0]]
    p = FKP[pid]
    rlo, rhi, rme = span(p, "Pantry")
    flo, fhi, fme = span(p, "Refrigerate")
    room_days = rlo * TO_DAYS[rme] if (rlo is not None and rme in TO_DAYS) else None
    # rule: needs a fridge if FoodKeeper lists a fridge time and either no room-temperature time
    # or a room-temperature time shorter than 2 days
    needs_fridge = bool(flo is not None and (rme is None or (room_days is not None and room_days < 2)))
    # same-evening limit: the category assumption, capped by FoodKeeper's shorter room-temperature time
    # (room_temp_min in hours) when FoodKeeper gives one in days/weeks/months/years; "When Ripe" or missing -> assumption
    max_h, max_src = MAX_HOURS[f[2]], "ASSUMPTION"
    if room_days is not None and room_days * 24 < max_h:
        max_h, max_src = int(room_days * 24), "ASSUMPTION capped by FoodKeeper"
    srows.append({"food_item": f[0], "food_category": f[2], "foodkeeper_product_id": pid,
                  "foodkeeper_name": p["Name"] + (", " + p["Name_subtitle"] if p.get("Name_subtitle") else ""),
                  "match_quality": quality, "mapping_reason": reason, "room_temp_min": rlo, "room_temp_max": rhi, "room_temp_metric": rme,
                  "fridge_min": flo, "fridge_max": fhi, "fridge_metric": fme,
                  "needs_fridge_if_kept": needs_fridge, "fridge_fields_source": FK_STATUS,
                  "max_hours_unrefrigerated": max_h, "max_hours_source": max_src})
STORAGE = pd.DataFrame(srows)
store = STORAGE.set_index("food_item").to_dict("index")

# ---------------------------------------------------------------- pantries (fictional)
PANTRY_NAMES = [
    "Bukal Community Kitchen", "Socorro Street Pantry", "Anonas Feeding Program", "Kalinga Food Shelf",
    "Pag-asa Kusina", "Bayanihan Pantry", "Sinag Community Kitchen", "Ugnayan Food Bank Corner",
    "Tahanan Feeding Center", "Liwanag Pantry", "Kapitbahay Kitchen", "Busog Bata Program",
    "Silong Community Pantry", "Agapay Kusina", "Himig Feeding Program", "Daluyan Food Shelf",
    "Malasakit Pantry", "Sandigan Kitchen", "Lingap Feeding Center", "Talaba Street Pantry",
    "Tanglaw Community Kitchen", "Pugad Food Shelf", "Sibol Feeding Program", "Alalay Pantry",
    "Kanlungan Kusina", "Hiraya Community Pantry", "Dagitab Kitchen", "Batis Food Shelf",
    "Kaagapay Feeding Center", "Ligaya Pantry",
]
PTYPES = ["community pantry", "parish kitchen", "feeding program", "barangay kitchen"]
p_nodes = pick_nodes(res_cand, len(PANTRY_NAMES), 0.25)
pantries = []
for i, (nm, n) in enumerate(zip(PANTRY_NAMES, p_nodes), 1):
    ptype = "feeding program" if "Feeding" in nm or "Program" in nm else rng.choice(PTYPES)
    catchment = rng.randint(P["catchment_households_min"], P["catchment_households_max"])
    hh = round(catchment * P["food_insecure_share_qc"])
    fridge = rng.random() < P["share_pantries_with_fridge"]
    if nm.startswith("Bukal"):   # anchors from the mockup: about 60 and 35 households at the placeholder share
        fridge, catchment = True, 200
        hh = round(catchment * P["food_insecure_share_qc"])
    if nm.startswith("Socorro"):
        fridge, catchment = False, 117
        hh = round(catchment * P["food_insecure_share_qc"])
    closes = rng.choice(["19:00", "19:30", "20:00", "20:30", "21:00"])
    if nm.startswith("Anonas"):
        closes = "19:00"
    pantries.append({
        "pantry_id": f"P{i:02d}", "pantry_name": nm, "pantry_type": ptype,
        "street": node_street[n][0], "lat": round(nodes[n][0], 6), "lon": round(nodes[n][1], 6), "osm_node_id": n,
        "catchment_households": catchment, "households_served": hh, "households_served_source": FNRI_STATUS,
        "has_fridge": fridge,
        "fridge_capacity_kg": rng.choice([10, 15, 20, 25, 30]) if fridge else 0,
        "dry_storage_kg": rng.choice([20, 30, 40, 60]),
        "opens": rng.choice(["16:00", "16:30", "17:00"]), "closes": closes,
        "anchor": nm.split()[0] in ("Bukal", "Socorro", "Anonas"),
    })
pantries_df = pd.DataFrame(pantries)

# ---------------------------------------------------------------- donors (fictional)
FIRST = ["Oning", "Pacing", "Loleng", "Caring", "Nena", "Baby", "Tessie", "Ising", "Lorna", "Dolor",
         "Ben", "Tonio", "Celso", "Pido", "Andoy", "Kiko", "Nanding", "Berto", "Islaw", "Gorio"]
DTYPES = [("karinderya", 0.44), ("panaderia", 0.24), ("carinderia-canteen", 0.10), ("small grocery stall", 0.10),
          ("catering kitchen", 0.06), ("fruit & vegetable stall", 0.06)]
d_nodes = pick_nodes(main_cand + res_cand, 50, 0.12)
donors = []
used = set()
for i, n in enumerate(d_nodes, 1):
    t = rng.choices([a for a, _ in DTYPES], [b for _, b in DTYPES])[0]
    while True:
        f = rng.choice(FIRST)
        if f not in used or len(used) >= len(FIRST):
            break
    used.add(f)
    title = "Aling" if f in FIRST[:10] else "Mang"
    name = {"karinderya": f"Karinderya ni {title} {f}", "panaderia": f"Panaderia {f}",
            "carinderia-canteen": f"{f}'s Canteen", "small grocery stall": f"Tindahan ni {title} {f}",
            "catering kitchen": f"{f} Home Catering", "fruit & vegetable stall": f"Gulayan ni {title} {f}"}[t]
    if i == 1:
        name, t = "Karinderya ni Aling Oning", "karinderya"
    donors.append({"donor_id": f"D{i:02d}", "donor_name": name, "donor_type": t, "street": node_street[n][0],
                   "lat": round(nodes[n][0], 6), "lon": round(nodes[n][1], 6), "osm_node_id": n,
                   "closing_time": rng.choice(["17:30", "18:00", "18:30", "19:00", "19:30"]),
                   "posts_per_week": rng.choice([1, 2, 2, 3, 3, 4, 5]), "anchor": i == 1})
# de-duplicate donor names without rng: a later donor that repeats a full name takes the first unused
# replacement first name of the same kind (Aling = female, Mang = male), never "Oning" (the anchor's name),
# so no random draw shifts and only the duplicate rows change
EXTRA_F = ["Charing", "Petra", "Senyang", "Iska", "Didang", "Luding", "Puring", "Siony", "Miling", "Osang"]
EXTRA_M = ["Ambo", "Teban", "Dado", "Pepe", "Kulas", "Isko", "Ramon", "Tasyo", "Goryo", "Pablo"]
_taken = {dn["donor_name"] for dn in donors}
_seen = set()
for dn in donors:
    nm = dn["donor_name"]
    if nm in _seen:
        old = next(f for f in FIRST if nm.endswith(" " + f) or nm.startswith(f + "'s") or nm.startswith(f + " "))
        pool = EXTRA_F if (old in FIRST[:10] or "Aling" in nm) else EXTRA_M
        for f in pool:
            cand_name = nm.replace(old, f)
            if cand_name not in _taken:
                dn["donor_name"] = cand_name
                _taken.add(cand_name)
                break
    _seen.add(dn["donor_name"])
donors_df = pd.DataFrame(donors)
DTYPE_CATS = {
    "karinderya": ["cooked_dish", "cooked_noodles", "cooked_vegetables", "cooked_soup", "cooked_rice"],
    "carinderia-canteen": ["cooked_dish", "cooked_noodles", "cooked_rice", "cooked_vegetables"],
    "catering kitchen": ["cooked_dish", "cooked_noodles", "cooked_rice"],
    "panaderia": ["bread"], "small grocery stall": ["packaged_shelf_stable", "bread", "fruit"],
    "fruit & vegetable stall": ["fresh_vegetables", "leafy_greens", "fruit"],
}

# ---------------------------------------------------------------- distances (road network)
dist_rows = []
pantry_node = {p["pantry_id"]: p["osm_node_id"] for p in pantries}
for d in donors:
    dd = dijkstra(d["osm_node_id"])
    for p in pantries:
        km = dd[p["osm_node_id"]]
        dist_rows.append({"donor_id": d["donor_id"], "pantry_id": p["pantry_id"], "road_km": round(km, 2),
                          "est_min_motorcycle": round(km / P["speed_kmh_motorcycle"] * 60 + 3, 1),
                          "est_min_car": round(km / P["speed_kmh_car"] * 60 + 5, 1)})
dist_df = pd.DataFrame(dist_rows)

# ---------------------------------------------------------------- drivers + run history (fictional)
SURN = ["Dizon", "Ramos", "Santos", "Reyes", "Cruz", "Bautista", "Garcia", "Mendoza", "Torres", "Flores",
        "Navarro", "Aquino", "Villanueva", "Castro", "Rivera", "Domingo", "Salazar", "Mercado", "Pascual", "Soriano",
        "Fernandez", "Lopez", "Gonzales", "Morales", "Valdez", "Ramirez", "Aguilar", "De Leon", "Manalo", "Sison",
        "Lim", "Tan", "Ocampo", "Del Rosario", "Lacson", "Robles", "Jimenez", "Panganiban", "Estrada", "Marquez"]
VEH = [("motorcycle", 0.55), ("car", 0.2), ("tricycle", 0.15), ("bicycle", 0.10)]
drivers, planned_outcomes = [], {}
dr_nodes = pick_nodes(res_cand, 40, 0.1)
for i, (sn, n) in enumerate(zip(SURN, dr_nodes), 1):
    initial = chr(ord("A") + rng.randrange(26))
    if sn == "Dizon":
        initial = "R"
    if sn == "Ramos":
        initial = "J"
    veh = rng.choices([a for a, _ in VEH], [b for _, b in VEH])[0]
    if sn == "Dizon":
        veh = "motorcycle"
    if sn == "Ramos":
        veh = "car"
    cap = rng.choice(fg_cap) + (1 if veh == "car" else 0) - (1 if veh == "bicycle" else 0)
    start = rng.choice([16, 17, 18])
    hours = rng.choice(fg_win_len)
    p_show = min(0.98, max(0.45, rng.betavariate(8, 1.6)))
    n_runs = rng.randint(2, 20)
    if sn == "Dizon":
        n_runs, p_show = 11, None
    if sn == "Ramos":
        n_runs = 0
    outcomes = []
    for k in range(n_runs):
        if sn == "Dizon":
            outcomes.append("completed" if k != 4 else "no_show")
            continue
        u = rng.random()
        if u < p_show:
            outcomes.append("completed_late" if rng.random() < 0.12 else "completed")
        elif u < p_show + (1 - p_show) * 0.5:
            outcomes.append("withdrew_after_offer")
        else:
            outcomes.append("no_show")
    planned_outcomes[f"V{i:02d}"] = outcomes
    drivers.append({"driver_id": f"V{i:02d}", "display_name": f"{initial}. {sn}", "vehicle": veh,
                    "capacity_load_units": cap, "street": node_street[n][0], "home_lat": round(nodes[n][0], 6),
                    "home_lon": round(nodes[n][1], 6), "available_from": f"{start}:00",
                    "available_to": f"{min(start + hours, 23)}:00", "anchor": sn in ("Dizon", "Ramos")})
drivers_df = pd.DataFrame(drivers)

# ---------------------------------------------------------------- evenings, needs, offers
evenings, needs, offers = [], [], []
lot = 1
# Evenings per split. Main evenings can be appended (the pilot sets their count, study guide p.19):
# every evening draws from its own seed, so adding evenings never changes an earlier evening's rows.
N_EVENINGS = {"tuning": 10, "pilot": 10, "main_sample": 10}
split = [s for s, k in N_EVENINGS.items() for _ in range(k)]
dow_factor = {0: 1.0, 1: 1.0, 2: 1.05, 3: 1.05, 4: 1.15, 5: 1.25, 6: 0.85}


def tmin(s):
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def tstr(m):
    return f"{m // 60:02d}:{m % 60:02d}"


for e in range(1, len(split) + 1):
    eseed = SEED * 100 + e
    er = random.Random(eseed)
    date = pd.Timestamp("2026-10-01") + pd.Timedelta(days=e - 1)
    rain = er.random() < 0.3
    tot_need = 0.0
    open_p = []
    for p in pantries:
        is_open = er.random() > 0.08
        need = 0.0
        if is_open:
            turnout = er.uniform(P["turnout_min"], P["turnout_max"])
            need = p["households_served"] * turnout * P["kg_per_household_evening"] * dow_factor[date.dayofweek]
            if er.random() < 0.05:
                need = 0.0  # stocked up today: zero reported need
        need = round(need, 1)
        needs.append({"evening_id": f"E{e:02d}", "pantry_id": p["pantry_id"], "is_open": is_open,
                      "need_kg": need, "need_fixed_at": "16:00", "need_source": "ASSUMPTION"})
        tot_need += need
        if is_open:
            open_p.append(p)
    ratio = round(er.uniform(P["supply_ratio_min"], P["supply_ratio_max"]), 2)
    target = ratio * tot_need
    posted = 0.0
    e_lots = []
    while posted < target - 1.0:
        d = er.choice(donors)
        cats = DTYPE_CATS[d["donor_type"]]
        choices = [f for f in FOODS if f[2] in cats]
        f = er.choices(choices, [FOOD_W[c[2]] for c in choices])[0]
        lo, hi = f[5]
        size_class = er.choice(fg_qty)  # FoodGo load units 1-3 -> small/medium/large lot
        units = round(lo + (hi - lo) * (size_class - 1) / 2 + er.uniform(-0.3, 0.3) * (hi - lo) / 2)
        units = max(lo, min(hi, units))
        kg = round(units * f[4], 2)
        if posted + kg > target + 2.0:
            continue
        posted += kg
        close = tmin(d["closing_time"])
        post_t = close + er.randint(-30, 15)
        pick_t = post_t + er.choice([45, 60, 75, 90])
        pick_t = min(21 * 60, 15 * round(pick_t / 15))  # no pickups after 21:00 (latest pantry closing)
        rule = store[f[0]]
        e_lots.append({"lot_id": f"L{lot:04d}", "evening_id": f"E{e:02d}", "donor_id": d["donor_id"],
                       "food_item": f[0], "food_item_fil": f[1], "food_category": f[2], "quantity": units,
                       "unit": f[3], "est_kg": kg, "load_units": size_class,
                       "needs_fridge_if_kept": rule["needs_fridge_if_kept"], "needs_fridge_source": FK_STATUS,
                       "posted_at": tstr(post_t), "pickup_by": tstr(pick_t)})
        lot += 1
    offers.extend(e_lots)
    evenings.append({"evening_id": f"E{e:02d}", "seed": eseed, "date": date.date().isoformat(),
                     "weekday": date.day_name(), "split": split[e - 1], "raining": rain,
                     "pantries_open": len(open_p), "total_need_kg": round(tot_need, 1),
                     "total_posted_kg": round(posted, 1), "supply_ratio": round(posted / tot_need, 2),
                     "lots_posted": len(e_lots)})
ev_df, need_df, off_df = pd.DataFrame(evenings), pd.DataFrame(needs), pd.DataFrame(offers)


# ---------------------------------------------------------------- driver runs (tuning evenings only, real lots)
# Each run is one offered delivery of a real lot posted on a tuning evening (E01-E10).
# A driver never gets two runs whose pickup windows (posted_at -> pickup_by) overlap,
# the lot must fit the driver's capacity and fall inside the driver's available hours,
# and no lot is given to more than one run.
ar = random.Random(SEED + 11)
tun = off_df[off_df["evening_id"].isin([f"E{k:02d}" for k in range(1, 11)])].copy()
tun["t0"] = tun["posted_at"].map(tmin)
tun["t1"] = tun["pickup_by"].map(tmin)
taken = set()
runs, run_id, short = [], 1, []
ev_date = ev_df.set_index("evening_id")["date"].to_dict()
for d in drivers:
    did = d["driver_id"]
    a0, a1 = tmin(d["available_from"]), tmin(d["available_to"])
    pool = tun[(tun["load_units"] <= d["capacity_load_units"]) & (tun["t0"] < a1) & (tun["t1"] > a0)]
    order = list(pool.index)
    ar.shuffle(order)
    mine = []  # (evening_id, t0, t1)
    for outcome in planned_outcomes[did]:
        lot_row = None
        for ix in order:
            if ix in taken:
                continue
            r_ = pool.loc[ix]
            if any(e == r_["evening_id"] and r_["t0"] < b and a < r_["t1"] for e, a, b in mine):
                continue
            lot_row = r_
            taken.add(ix)
            break
        if lot_row is None:
            short.append(did)
            break
        mine.append((lot_row["evening_id"], lot_row["t0"], lot_row["t1"]))
        runs.append({"run_id": "", "driver_id": did, "evening_id": lot_row["evening_id"],
                     "run_date": ev_date[lot_row["evening_id"]], "lot_id": lot_row["lot_id"],
                     "posted_at": lot_row["posted_at"], "pickup_by": lot_row["pickup_by"], "outcome": outcome,
                     "minutes_late": ar.randint(5, 25) if outcome == "completed_late" else 0})
if short:
    print("WARNING: not enough non-overlapping lots for", sorted(set(short)))
runs_df = pd.DataFrame(runs).sort_values(["driver_id", "evening_id", "posted_at"]).reset_index(drop=True)
runs_df["run_id"] = [f"R{k:04d}" for k in range(1, len(runs_df) + 1)]
anchor_ids = {d["driver_id"] for d in drivers if d["anchor"]}
runs_df["anchor"] = runs_df["driver_id"].isin(anchor_ids)
runs_df = runs_df[["run_id", "driver_id", "evening_id", "run_date", "lot_id", "posted_at", "pickup_by",
                   "outcome", "minutes_late", "anchor"]]
shows = runs_df["outcome"].isin(["completed", "completed_late"])
agg = runs_df.assign(show=shows).groupby("driver_id")["show"].agg(["sum", "count"])
drivers_df["tuning_runs"] = drivers_df["driver_id"].map(agg["count"]).fillna(0).astype(int)
drivers_df["tuning_shows"] = drivers_df["driver_id"].map(agg["sum"]).fillna(0).astype(int)
drivers_df["reliability_estimate_frozen"] = ((drivers_df["tuning_shows"] + 1) / (drivers_df["tuning_runs"] + 2)).round(2)

# ---------------------------------------------------------------- anchor placement (no rng)
# Placed AFTER every random draw so no other row moves. Nodes found by find_anchor_nodes.py so that road
# distances from Aling Oning reproduce the study guide's worked example (Bukal 1.1 km, Socorro 0.6 km).
ANCHOR_NODES = {("pantry", "Bukal Community Kitchen"): 8635554600, ("pantry", "Socorro Street Pantry"): 32089044,
                ("pantry", "Anonas Feeding Program"): 7509184586, ("donor", "Karinderya ni Aling Oning"): 523962960}
for (kind, nm), n in ANCHOR_NODES.items():
    df, col = (pantries_df, "pantry_name") if kind == "pantry" else (donors_df, "donor_name")
    ix = df.index[df[col] == nm][0]
    df.loc[ix, ["street", "lat", "lon", "osm_node_id"]] = [node_street[n][0], round(nodes[n][0], 6),
                                                          round(nodes[n][1], 6), n]
    rows = pantries if kind == "pantry" else donors
    rows[ix].update({"street": node_street[n][0], "lat": round(nodes[n][0], 6), "lon": round(nodes[n][1], 6),
                     "osm_node_id": n})
# recompute road distances with the final positions (deterministic shortest paths)
dist_rows = []
for d in donors:
    dd = dijkstra(d["osm_node_id"])
    for p in pantries:
        km = dd[p["osm_node_id"]]
        dist_rows.append({"donor_id": d["donor_id"], "pantry_id": p["pantry_id"], "road_km": round(km, 2),
                          "est_min_motorcycle": round(km / P["speed_kmh_motorcycle"] * 60 + 3, 1),
                          "est_min_car": round(km / P["speed_kmh_car"] * 60 + 5, 1)})
dist_df = pd.DataFrame(dist_rows)

# ---------------------------------------------------------------- donor messages
import messages  # local module
# MESSAGES_PER_EVENING messages per evening, each evening sampled with its own seed (dataset v1.1)
MESSAGES_PER_EVENING = 17
msg_df = messages.build(off_df, donors_df, ev_df, per_evening=MESSAGES_PER_EVENING)
# split comes from the lot's evening (no randomness): tuning / pilot / main_sample
_lot_ev = off_df.set_index("lot_id")["evening_id"]
_ev_split = ev_df.set_index("evening_id")["split"]
msg_df.insert(3, "split", msg_df["lot_id"].map(_lot_ev).map(_ev_split))
assert msg_df["split"].notna().all()

# ---------------------------------------------------------------- field-level sources
SOURCES = [
    ("pantries", "lat, lon, street, osm_node_id", "OpenStreetMap (Overpass API, ODbL)", "REAL (fictional pantry placed on a real road node)"),
    ("pantries", "households_served", "assumed catchment x assumed food-insecure share 0.30 (FNRI ENNS planned to replace the share)", FNRI_STATUS),
    ("pantries", "catchment_households, has_fridge, fridge_capacity_kg, dry_storage_kg, opens, closes", "Created (assumption)", "ASSUMPTION"),
    ("pantry_needs", "need_kg", "households_served x assumed turnout x assumed kg per household", "ASSUMPTION"),
    ("donors", "lat, lon, street, osm_node_id", "OpenStreetMap", "REAL (fictional donor placed on a real road node)"),
    ("road_distances", "road_km", "OpenStreetMap road network, shortest path", "REAL (computed)"),
    ("road_distances", "est_min_motorcycle, est_min_car", "road_km / assumed speeds", "ASSUMPTION"),
    ("drivers", "capacity_load_units", "FoodGo volunteer capacities (3-5 units), +1 car, -1 bicycle", "FOODGO-DERIVED"),
    ("drivers", "available_from, available_to", "FoodGo 4-hour availability windows, shifted to evenings", "FOODGO-DERIVED"),
    ("drivers", "reliability_estimate_frozen", "frozen after tuning: (shows + 1) / (runs + 2) over E01-E10 runs", "DERIVED"),
    ("driver_runs", "outcome, minutes_late", "Created: simulated show-up outcomes", "SYNTHETIC"),
    ("driver_runs", "lot_id, posted_at, pickup_by", "food_offers lots posted on the same tuning evening (E01-E10), no overlapping windows per driver", "LINKED"),
    ("food_offers", "load_units", "FoodGo order quantities (1-3 units)", "FOODGO-DERIVED"),
    ("food_offers", "needs_fridge_if_kept", "storage_rules (derived from FoodKeeper)", "DERIVED FROM FOODKEEPER"),
    ("food_offers", "food_item, quantity, unit, est_kg, posted_at, pickup_by", "Created (simulated)", "SYNTHETIC"),
    ("evenings", "supply_ratio", "design rule 0.6-0.9 (study guide p.13)", "DESIGN RULE"),
    ("storage_rules", "foodkeeper_product_id, foodkeeper_name, room_temp_*, fridge_*", "USDA FSIS FoodKeeper (foodkeeper.json, data version 128)", FK_STATUS),
    ("storage_rules", "needs_fridge_if_kept", "derived from FoodKeeper times: fridge time listed and no room-temp time or one under 2 days", "DERIVED FROM FOODKEEPER"),
    ("storage_rules", "match_quality", "judgement of how closely the FoodKeeper product matches the Filipino food", "ASSUMPTION"),
    ("storage_rules", "max_hours_unrefrigerated", "category assumption (not FoodKeeper), capped by FoodKeeper's room-temp time where that is shorter; see max_hours_source per row", "ASSUMPTION / ASSUMPTION capped by FoodKeeper"),
    ("donor_messages", "all", "Created: written from each lot's fields (labels correct by construction)", "SYNTHETIC"),
    ("donor_messages", "template_id", "recorded from the phrasing chosen for each slot (no extra random draw); pilot/main messages reuse tuning phrasings, so accuracy on them does not measure new phrasings", "DERIVED"),
    ("donor_messages", "split", "copied from the lot's evening (E01-E10 tuning, E11-E20 pilot, E21-E30 main_sample); parser prompt may be tuned only on tuning messages, accuracy reported only on pilot/main", "DERIVED"),
    ("pantries, donors", "anchor placement: Bukal (15th Avenue, OSM 8635554600), Socorro (Columbia Street, OSM 32089044), Anonas (Anonas Street, OSM 7509184586), D01 Aling Oning (Aurora Boulevard, OSM 523962960)", "hand-placed on real OSM road nodes after all random draws so road_km from D01 is Bukal 1.10 km and Socorro 0.60 km, as in the study guide", "ANCHOR (hand-placed)"),
    ("pantries", "anchor rows: Bukal (fridge, catchment 200), Socorro (no fridge, catchment 117), Anonas (closes 19:00)", "hand-set to match the study guide's worked examples", "ANCHOR (hand-set)"),
    ("donors", "anchor row D01: Karinderya ni Aling Oning (karinderya)", "hand-set to match the study guide's worked examples", "ANCHOR (hand-set)"),
    ("drivers", "anchor rows: R. Dizon (initial R, motorcycle, 11 runs), J. Ramos (initial J, car, 0 runs)", "hand-set to match the study guide's worked examples", "ANCHOR (hand-set)"),
    ("driver_runs", "anchor rows: R. Dizon's 11 runs (10 completed, 1 no-show = his 5th planned outcome)", "outcomes hand-set; lots still assigned by the normal no-overlap rule", "ANCHOR (hand-set)"),
]
sources_df = pd.DataFrame(SOURCES, columns=["table", "fields", "source", "status"])
sources_df.to_csv(os.path.join(OUT, "sources.csv"), index=False, lineterminator="\n")
print()
print("per-evening totals (kg):")
print(ev_df[["evening_id", "split", "pantries_open", "total_need_kg", "total_posted_kg", "supply_ratio", "lots_posted"]].to_string(index=False))

# ---------------------------------------------------------------- save
tables = {
    "pantries": pantries_df, "donors": donors_df, "drivers": drivers_df, "driver_runs": runs_df,
    "evenings": ev_df, "pantry_needs": need_df, "food_offers": off_df, "donor_messages": msg_df,
    "road_distances": dist_df, "storage_rules": STORAGE,
}
for k, df in tables.items():
    df.to_csv(os.path.join(OUT, f"{k}.csv"), index=False, encoding="utf-8", lineterminator="\n")
params_df = pd.DataFrame([{"parameter": k, "value": v["value"], "unit": v.get("unit", ""), "status": v["status"],
                           "source": v["source"]} for k, v in PARAMS.items()])
params_df.to_csv(os.path.join(OUT, "parameters.csv"), index=False, lineterminator="\n")
try:
    with pd.ExcelWriter(os.path.join(HERE, "salo-evening-dataset.xlsx")) as xw:
        for k, df in list(tables.items()) + [("parameters", params_df)]:
            df.to_excel(xw, sheet_name=k[:31], index=False)
except ModuleNotFoundError:
    print("openpyxl missing: skipped xlsx")
for k, df in tables.items():
    print(f"{k:16s} {len(df):5d} rows x {len(df.columns)} cols")
