"""Donor messages for the Salo Evening Dataset.

Each message is written FROM a structured lot (the answer key), never labelled afterwards,
so the gold fields are correct by construction. Difficulty mix: explicit 50%, implicit 30%,
incomplete 15%, contradictory 5%. Language mix: English 30%, Filipino 25%, Taglish 45%.
"""
import random
import pandas as pd

NUM_FIL = {1: "isang", 2: "dalawang", 3: "tatlong", 4: "apat na", 5: "limang", 6: "anim na", 7: "pitong",
           8: "walong", 9: "siyam na", 10: "sampung"}
NUM_EN = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine",
          10: "ten"}
HOUR_FIL = {5: "alas-singko", 6: "alas-sais", 7: "alas-siyete", 8: "alas-otso", 9: "alas-nuwebe", 10: "alas-diyes"}
UNIT_EN = {"tray": ("tray", "trays"), "bilao": ("bilao", "bilaos"), "pot": ("pot", "pots"),
           "piece": ("piece", "pieces"), "kg": ("kilo", "kilos"), "loaf": ("loaf", "loaves"),
           "can": ("can", "cans"), "pack": ("pack", "packs")}
UNIT_FIL = {"tray": "tray", "bilao": "bilao", "pot": "kaldero", "piece": "piraso", "kg": "kilo",
            "loaf": "balot", "can": "lata", "pack": "pack"}


def link(word):
    """Filipino linker: 'na' after consonants, '-ng' after vowels, '-g' after n."""
    if word[-1] in "aeiou":
        return word + "ng"
    if word[-1] == "n":
        return word + "g"
    return word + " na"


def t12(hhmm):
    h, m = map(int, hhmm.split(":"))
    hh = h - 12 if h > 12 else h
    return f"{hh}:{m:02d} PM" if m else f"{hh} PM"


def t_short(hhmm):
    h, m = map(int, hhmm.split(":"))
    hh = h - 12 if h > 12 else h
    return f"{hh}:{m:02d}" if m else f"{hh}"


def t_fil(hhmm):
    h, m = map(int, hhmm.split(":"))
    hh = h - 12 if h > 12 else h
    base = HOUR_FIL.get(hh, f"{hh}")
    if m == 0:
        return base
    if m == 30:
        return base + " y medya"
    return f"{hh}:{m:02d}"


def qty_en(q, unit, r, spelled=False):
    s, p = UNIT_EN[unit]
    n = NUM_EN.get(q, str(q)) if spelled and q <= 10 else str(q)
    return f"{n} {s if q == 1 else p}"


def qty_fil(q, unit, spelled=False):
    u = UNIT_FIL[unit]
    if spelled and q in NUM_FIL:
        return f"{NUM_FIL[q]} {u}"
    return f"{q} {u}"


GREET_EN = ["Hi!", "Hello,", "Good evening!", "Hi Salo,", "", "Hello there,"]
GREET_FIL = ["Magandang gabi po!", "Hello po,", "Gandang gabi,", "Hi po!", "", "Kumusta po,"]
GREET_TL = ["Hi po!", "Hello po,", "Good evening po!", "Hi Salo,", "", "Gandang gabi po,"]


def make(row, street, lang, diff, r):
    rec = {}

    def pk(seq, tag):
        """r.choice with the chosen phrasing's position recorded (no extra random draw)."""
        x = r.choice(seq)
        rec[tag] = seq.index(x)
        return x

    item_en, item_fil = row.food_item, row.food_item_fil
    q, unit, pick = int(row.quantity), row.unit, row.pickup_by
    gold = {"gold_food_item": item_en, "gold_quantity": q, "gold_unit": unit, "gold_est_kg": row.est_kg,
            "gold_pickup_by": pick, "gold_location": street, "requires_clarification": False,
            "missing_or_conflicting": ""}
    drop = set()
    conflict = None
    if diff == "incomplete":
        drop = set(r.sample(["quantity", "pickup_by", "food_item"], r.choice([1, 1, 2])))
    if diff == "contradictory":
        conflict = r.choice(["quantity", "pickup_by"])
    spelled = diff == "implicit"

    # ---- phrases
    if lang == "en":
        g = pk(GREET_EN, "g")
        food = "some food" if "food_item" in drop else item_en
        qty = "" if "quantity" in drop else qty_en(q, unit, r, spelled)
        if diff == "implicit":
            when = pk([f"before {t_short(pick)} tonight", f"by around {t_short(pick)}",
                             f"no later than {t_short(pick)} this evening"], "wh")
        else:
            when = pk([f"pickup before {t12(pick)}", f"please pick up by {t12(pick)}",
                             f"available until {t12(pick)}"], "wh")
        where = pk([f"here on {street}", f"near {street}", f"along {street}"], "wr")
        if "pickup_by" in drop:
            when = pk(["pickup anytime tonight", "please come get it later", ""], "wm")
        if conflict == "quantity":
            other = q + r.choice([1, 2])
            qty = f"{qty_en(q, unit, r)} (maybe {other}, not sure)"
        if conflict == "pickup_by":
            h = int(pick[:2]) - 12
            when = f"pickup before {h} PM... or {h + 1}? whichever"
        core = f"we have {qty + ' of ' if qty else ''}{food} left {where}"
        tails = [f"{when}.", f"{when}, thanks!", f"{when}. Still warm." if row.food_category.startswith("cooked") else f"{when}."]
        text = f"{g} {core[0].upper() + core[1:] if not g else core}, {pk(tails, "tl")}".replace(" ,", ",")
    elif lang == "fil":
        g = pk(GREET_FIL, "g")
        food = "pagkain" if "food_item" in drop else item_fil
        qty = "" if "quantity" in drop else qty_fil(q, unit, spelled)
        if diff == "implicit":
            when = pk([f"bago mag-{t_fil(pick)} ng gabi", f"hanggang {t_fil(pick)} lang po",
                             f"kunin po bago {t_fil(pick)}"], "wh")
        else:
            when = pk([f"kunin po bago {t12(pick)}", f"pakikuha po bago mag-{t12(pick)}",
                             f"hanggang {t12(pick)} lang po"], "wh")
        where = pk([f"dito sa {street}", f"malapit sa {street}", f"sa may {street}"], "wr")
        if "pickup_by" in drop:
            when = pk(["kunin na lang po mamaya", "kahit anong oras po ngayong gabi", ""], "wm")
        if conflict == "quantity":
            qty = f"{qty_fil(q, unit)}, o {qty_fil(q + r.choice([1, 2]), unit)} yata"
        if conflict == "pickup_by":
            h = int(pick[:2]) - 12
            when = f"kunin po bago {HOUR_FIL.get(h, h)}... ay hindi, bago {HOUR_FIL.get(h + 1, h + 1)} pala, ewan ko po"
        lead = pk(["May natira po kaming", "Mayroon pa po kaming", "May sobra po kaming"], "ld")
        if qty:
            text = f"{g} {lead} {link(qty)} {food} {where}, {when}."
        else:
            text = f"{g} {lead} {food} {where}, {when}."
    else:  # Taglish
        g = pk(GREET_TL, "g")
        food = "food" if "food_item" in drop else pk([item_en, item_fil], "fd")
        qty = "" if "quantity" in drop else (qty_fil(q, unit, True) if spelled else qty_en(q, unit, r))
        if diff == "implicit":
            when = pk([f"pa-pickup na lang before {t_short(pick)}", f"kunin before {t_short(pick)} sana",
                             f"bago mag-{t_fil(pick)} sana ma-pickup"], "wh")
        else:
            when = pk([f"pickup before {t12(pick)} po", f"pa-pickup po before {t12(pick)}",
                             f"available until {t12(pick)} lang"], "wh")
        where = pk([f"dito sa {street}", f"near {street}", f"sa {street}"], "wr")
        if "pickup_by" in drop:
            when = pk(["pickup anytime tonight po", "kayo na bahala sa oras", ""], "wm")
        if conflict == "quantity":
            qty = f"{qty_en(q, unit, r)}, or {q + r.choice([1, 2])} yata"
        if conflict == "pickup_by":
            h = int(pick[:2]) - 12
            when = f"pickup before {h}pm, or {h + 1}pm na lang? hindi ko sure"
        lead = pk(["May natira kaming", "May extra kaming", "We still have"], "ld")
        mid = f"{qty} {('ng ' if lead != 'We still have' else 'of ')}{food}" if qty else food
        text = f"{g} {lead} {mid} {where}, {when}."
    text = " ".join(text.replace(" ,", ",").replace(", .", ".").replace(",.", ".").split())
    # sentence case after the greeting: capital at the start and after "!", lower case after ","
    import re
    text = re.sub(r"^(\w)", lambda m: m.group(1).upper(), text)
    text = re.sub(r"(! )(\w)", lambda m: m.group(1) + m.group(2).upper(), text)
    text = re.sub(r"(, )(May|Mayroon|We)\b", lambda m: m.group(1) + m.group(2).lower(), text)

    # ---- gold for missing/conflicting fields
    issues = []
    for fld in sorted(drop):
        key = {"quantity": ["gold_quantity", "gold_unit", "gold_est_kg"], "pickup_by": ["gold_pickup_by"],
               "food_item": ["gold_food_item"]}[fld]
        for k in key:
            gold[k] = None
        issues.append(f"missing {fld}")
    if conflict:
        key = {"quantity": ["gold_quantity", "gold_est_kg"], "pickup_by": ["gold_pickup_by"]}[conflict]
        for k in key:
            gold[k] = None
        issues.append(f"conflicting {conflict}")
    if issues:
        gold["requires_clarification"] = True
        gold["missing_or_conflicting"] = "; ".join(issues)
    # template = language + difficulty + which phrasing was picked for each slot + which fields are missing/conflicting
    parts = [lang, diff] + [f"{k}{rec[k]}" for k in ("g", "ld", "wh", "wm", "wr", "tl", "fd") if k in rec]
    parts += ["miss=" + "+".join(sorted(drop)) if drop else "miss=none", f"conf={conflict or 'none'}"]
    return text, gold, "|".join(parts)


def build(offers, donors, rng_seed, n=500):
    r = random.Random(rng_seed + 7)
    street = donors.set_index("donor_id")["street"].to_dict()
    picks = offers.sample(n=min(n, len(offers)), random_state=rng_seed).sort_values("lot_id")
    langs = ["en"] * 30 + ["fil"] * 25 + ["taglish"] * 45
    diffs = ["explicit"] * 50 + ["implicit"] * 30 + ["incomplete"] * 15 + ["contradictory"] * 5
    rows = []
    for i, row in enumerate(picks.itertuples(), 1):
        lang, diff = r.choice(langs), r.choice(diffs)
        text, gold, tid = make(row, street[row.donor_id], lang, diff, r)
        rows.append({"message_id": f"M{i:04d}", "lot_id": row.lot_id, "donor_id": row.donor_id, "language": lang,
                     "difficulty": diff, "generation": "template", "template_id": tid, "message_text": text, **gold})
    df = pd.DataFrame(rows)
    df["gold_quantity"] = df["gold_quantity"].astype("Int64")
    return df
