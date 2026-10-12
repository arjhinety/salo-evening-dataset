"""Exports a fresh build to the Hugging Face layout and (optionally) publishes it.

    python build_dataset.py          # writes salo-evening-dataset/
    python export_hf.py              # writes hf/ (Parquet tables, card, licenses, hash.txt)
    python export_hf.py --push       # also uploads hf/ to huggingface.co/datasets/arjhinety/salo-evening-dataset

The dataset card records the exact GitHub commit the data was built from.
"""
import glob, hashlib, os, shutil, subprocess, sys
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "salo-evening-dataset")
OUT = os.path.join(HERE, "hf")
HF_REPO = "arjhinety/salo-evening-dataset"
GH_REPO = "https://github.com/arjhinety/salo-evening-dataset"

ODBL = ["pantries", "donors", "drivers", "road_distances", "donor_messages"]
CCBY = ["food_offers", "evenings", "pantry_needs", "driver_runs", "storage_rules"]
DESC = {
    "pantries": "fictional pantries placed on real OSM road nodes in Cubao–Project 4",
    "donors": "fictional karinderyas, panaderias, stalls and canteens",
    "drivers": "fictional volunteer drivers; reliability learned on tuning evenings, then frozen",
    "road_distances": "road km and travel time from every donor to every pantry (OSM shortest paths)",
    "donor_messages": "English / Filipino / Taglish donor messages with gold structured fields",
    "food_offers": "lots of surplus food posted on each evening",
    "evenings": "30 seeded evenings (10 tuning, 10 pilot, 10 main_sample)",
    "pantry_needs": "each pantry's need on each evening, fixed at 16:00",
    "driver_runs": "offered deliveries of real lots on tuning evenings E01–E10, with outcomes",
    "storage_rules": "per food item: matched FoodKeeper product, storage times, derived fridge rule",
}
FLOAT_COLS = {"est_kg", "gold_est_kg", "need_kg", "road_km", "lat", "lon", "home_lat", "home_lon", "room_temp_min",
              "room_temp_max", "fridge_min", "fridge_max", "total_need_kg", "total_posted_kg", "supply_ratio",
              "est_min_motorcycle", "est_min_car", "reliability_estimate_frozen"}
sha = lambda f: hashlib.sha256(open(f, "rb").read()).hexdigest()


def git_commit():
    try:
        c = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=HERE, text=True).strip()
        dirty = subprocess.check_output(["git", "status", "--porcelain"], cwd=HERE, text=True).strip()
        return c, bool(dirty)
    except Exception:
        return None, True


def md_table(df):
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in df.itertuples(index=False):
        lines.append("| " + " | ".join(str(v).replace("|", "/") for v in r) + " |")
    return "\n".join(lines)


if not os.path.isdir(SRC):
    sys.exit("Run python build_dataset.py first.")
commit, dirty = git_commit()
if "--push" in sys.argv and (commit is None or dirty):
    sys.exit("Refusing to push: commit your changes first so the card can name the exact commit.")
shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(OUT)

# ---- Parquet tables (typed columns; same values as the CSVs)
n_rows = {}
for t in ODBL + CCBY:
    df = pd.read_csv(os.path.join(SRC, f"{t}.csv"))
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].astype("string")
        elif df[c].dtype == float and c not in FLOAT_COLS and df[c].dropna().apply(float.is_integer).all():
            df[c] = df[c].astype("Int64")
    df.to_parquet(os.path.join(OUT, f"{t}.parquet"), index=False)
    n_rows[t] = len(df)
total = sum(n_rows.values())

with open(os.path.join(OUT, "hash.txt"), "w", encoding="utf-8", newline="\n") as fh:
    for t in sorted(ODBL + CCBY):
        fh.write(f"{sha(os.path.join(OUT, t + '.parquet'))}  {t}.parquet\n")

# ---- licenses and citation
built_from = f"{GH_REPO}/tree/{commit}" if commit else GH_REPO
open(os.path.join(OUT, "LICENSE.md"), "w", encoding="utf-8", newline="\n").write(f"""# Licenses

| Files | License | Why |
|---|---|---|
| {", ".join(f"`{t}.parquet`" for t in ODBL)} | [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/) | These tables contain data derived from OpenStreetMap: street names, road-node coordinates and road distances (`donor_messages` names real streets in its text and `gold_location`). Published derived databases must stay under the ODbL. |
| {", ".join(f"`{t}.parquet`" for t in CCBY)} | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | No OpenStreetMap data. Simulated, partly from FoodGo distributions (CC BY 4.0) and FoodKeeper storage times (CC0). |

The code and the pinned source files that build these tables are in [{GH_REPO}]({GH_REPO}) (code: MIT; each source file keeps its own license).

## Required attribution

- **OpenStreetMap:** © OpenStreetMap contributors. Data available under the Open Database License. https://www.openstreetmap.org/copyright
- **FoodGo:** Rubinstein, Z. B. (2020). *FoodGo Test Dataset* (Version 1). Carnegie Mellon University. Zenodo. https://doi.org/10.5281/zenodo.3801643. CC BY 4.0. Only its lot-size, capacity and availability-window distributions are used; its Pittsburgh coordinates are not.
- **FoodKeeper:** U.S. Department of Agriculture, Food Safety and Inspection Service. *FoodKeeper Data*, data version 128. https://catalog.data.gov/dataset/fsis-foodkeeper-data. CC0 1.0.
""")
open(os.path.join(OUT, "CITATIONS.bib"), "w", encoding="utf-8", newline="\n").write("""@misc{ty2026salo,
  author = {Ty, Arjhine A.},
  title  = {Salo Evening Dataset},
  year   = {2026},
  publisher = {Hugging Face},
  howpublished = {\\url{https://huggingface.co/datasets/arjhinety/salo-evening-dataset}},
  note   = {Build code: https://github.com/arjhinety/salo-evening-dataset}
}
@misc{rubinstein2020foodgo,
  author = {Rubinstein, Zachary B.},
  title  = {FoodGo Test Dataset},
  year   = {2020},
  publisher = {Zenodo},
  version = {1},
  doi    = {10.5281/zenodo.3801643}
}
@misc{usda_foodkeeper,
  author = {{U.S. Department of Agriculture, Food Safety and Inspection Service}},
  title  = {FoodKeeper Data},
  note   = {Data version 128. https://catalog.data.gov/dataset/fsis-foodkeeper-data},
}
@misc{openstreetmap,
  author = {{OpenStreetMap contributors}},
  title  = {OpenStreetMap},
  note   = {Road data for Cubao--Project 4, Quezon City, retrieved via the Overpass API on 2026-10-12. ODbL 1.0. https://www.openstreetmap.org},
}
""")

# ---- dataset card
srcs = pd.read_csv(os.path.join(SRC, "sources.csv"))
params = pd.read_csv(os.path.join(SRC, "parameters.csv"))[["parameter", "value", "unit", "status"]]
msgs = pd.read_csv(os.path.join(SRC, "donor_messages.csv"))
lang = (msgs.language.value_counts(normalize=True) * 100).round().astype(int)
tun = msgs[msgs.split == "tuning"].template_id
seen = {f"{t.split('|')[0]}:{p}" for t in tun for p in t.split("|")[1:]}
test = msgs[msgs.split != "tuning"].template_id
reuse = int(test.map(lambda t: all(f"{t.split('|')[0]}:{p}" in seen for p in t.split("|")[1:])).sum())
configs = "\n".join(
    f"- config_name: {t}\n  data_files: \"{t}.parquet\"" + ("\n  default: true" if t == "food_offers" else "")
    for t in ["food_offers"] + ODBL + [c for c in CCBY if c != "food_offers"])
table_rows = "\n".join(f"| `{t}` | {n_rows[t]:,} | {DESC[t]} | {'ODbL 1.0' if t in ODBL else 'CC BY 4.0'} |"
                       for t in ODBL + CCBY)
commit_line = (f"Built from commit [`{commit[:7]}`]({GH_REPO}/tree/{commit}) of [{GH_REPO.split('github.com/')[1]}]({GH_REPO})."
               if commit else f"Build code: [{GH_REPO}]({GH_REPO}).")

card = f"""---
pretty_name: Salo Evening Dataset
license: other
license_name: odbl-1.0-and-cc-by-4.0
license_link: LICENSE.md
language:
- en
- tl
size_categories:
- 1K<n<10K
tags:
- food-rescue
- multi-agent-systems
- simulation
- synthetic
- philippines
- openstreetmap
configs:
{configs}
---

# Salo Evening Dataset

I built this dataset for **Salo**, the multi-agent food rescue system I proposed for my CS 403 (Intelligent Agents) project at the Technological Institute of the Philippines – Quezon City, 1st Semester S.Y. 2026–2027. Salo matches surplus food from small food businesses (karinderyas, panaderias, stalls) to community pantries in the **Cubao–Project 4 area of Quezon City, Philippines**.

I combined three public sources (OpenStreetMap, the FoodGo Test Dataset and USDA FoodKeeper) with **simulated data** from a seeded script.
- **All business, pantry and volunteer names are fictional, and I included no real person's private information.**
- The roads and street names are real; the places I put on them are not.

**My build code, pinned sources and full regeneration guide:** {GH_REPO}. {commit_line}

```python
from datasets import load_dataset
offers = load_dataset("{HF_REPO}", "food_offers", split="train")
```

## Tables

There are {total:,} rows across 10 tables, and each table is its own subset. `hash.txt` gives the SHA-256 of every file.

| Table | Rows | What one row is | License |
|---|---|---|---|
{table_rows}

## Where the data comes from

| Source | What it supplies | License |
|---|---|---|
| **OpenStreetMap** (Overpass API, retrieved 2026-10-12) | road network; street names and coordinates of every pantry, donor and driver; `road_distances.road_km` | ODbL 1.0 |
| **FoodGo Test Dataset** (Carnegie Mellon University / 412 Food Rescue, Zenodo 10.5281/zenodo.3801643) | lot size classes (1–3 load units), driver capacities (3–5 units), 4-hour availability windows. Distributions only; FoodGo's Pittsburgh coordinates are not used | CC BY 4.0 |
| **USDA FSIS FoodKeeper**, data version 128 | `storage_rules`: FoodKeeper product ID and name, room-temperature and refrigerator times; `needs_fridge_if_kept` is derived from those times | CC0 1.0 |
| **Simulated** (seed 20260927) | pantries, donors, drivers, needs, lots, driver run outcomes, donor messages | this dataset |

FoodKeeper is credited **only** for the `storage_rules` storage-time fields and the `needs_fridge_if_kept` rule derived from them. **`max_hours_unrefrigerated` (the same-evening spoilage limit) is an assumption, not FoodKeeper data.** The one exception is eggplant, whose limit is capped at 24 h because FoodKeeper lists 1 day at room temperature.

I planned to use the DOST-FNRI ENNS food-security survey but **didn't obtain it**, so the food-insecure share (0.30) is my assumption.

### Source of every field

{md_table(srcs)}

### Assumed numbers

{md_table(params)}

## How it was built

- **Need:** each pantry's need is `households_served × turnout (0.3–0.6) × 0.25 kg × weekday factor`, fixed at 16:00 from the evening's seed. `households_served = catchment × 0.30`.
- **Supply:** posted food is **0.6–0.9×** each evening's total need, so methods cannot all hit the same ceiling.
- **Driver reliability:** (shows + 1) ÷ (runs + 2), learned **only** from runs on tuning evenings E01–E10, then frozen.
  - Each run is a real lot from the same evening.
  - No driver has overlapping pickup windows, and no lot is used twice.
- **Donor messages:** each message is written **from** a lot's fields, so the `gold_*` labels are correct by construction.
  - Language mix: {lang.get('taglish', 0)}% Taglish, {lang.get('en', 0)}% English and {lang.get('fil', 0)}% Filipino.
  - Difficulty mix: explicit, implicit, incomplete and contradictory.
- **Splits:** `evenings.split` and `donor_messages.split` are `tuning` (E01–E10), `pilot` (E11–E20) or `main_sample` (E21–E30).
- **Anchor rows:** I hand-set some rows to reproduce my project's worked examples, and marked them `anchor = True`:
  - Bukal (has a fridge, 15th Avenue) and Socorro (no fridge, Columbia Street). By road from Karinderya ni Aling Oning (Aurora Boulevard), Bukal is 1.10 km and Socorro 0.60 km.
  - Anonas (closes at 19:00).
  - R. Dizon: 10 shows in 11 runs, giving 0.85.
  - J. Ramos: no runs, giving 0.50.

## Limitations

- **Simulated.** The data shows how agents behave on plausible inputs. It is not evidence of real-world performance.
- **Assumptions.** Turnout, portion size, travel speeds and the 0.30 food-insecure share are assumptions (see the table above).
- **US storage guidance.** FoodKeeper times may be too generous for a 30 °C Quezon City evening. Some Filipino foods have only approximate matches; for example, instant noodles use "Pasta, dry".
- **Template messages.** All {len(msgs)} messages have `generation = template`.
  - **Any parsing accuracy measured on them is an optimistic upper bound, not real-world accuracy.**
  - Tune a parser prompt only on `tuning` messages and report accuracy only on `pilot` / `main_sample`.
  - Even then, {reuse} of the {len(test)} pilot/main messages use only phrasings that also appear in tuning messages (see `template_id`). So pilot/main accuracy does **not** measure how a parser handles new phrasings.
- **Fictional pantries.** My project proposal planned a real list of pantries that I would gather myself. That list needs the organisers' permission, so I used fictional pantries for now.
- **Simplified map.** Roads are treated as two-way, and only Cubao–Project 4 is covered. Rain is recorded per evening but does not yet affect anything.

## Citation and attribution

See `CITATIONS.bib` and `LICENSE.md`. Please credit: © OpenStreetMap contributors (ODbL); Rubinstein, Z. B. (2020), *FoodGo Test Dataset*, Zenodo, doi:10.5281/zenodo.3801643 (CC BY 4.0); USDA FSIS FoodKeeper Data (CC0).
"""
open(os.path.join(OUT, "README.md"), "w", encoding="utf-8", newline="\n").write(card)
print(f"wrote {OUT} ({total:,} rows; commit {commit[:7] if commit else 'none'}{' (dirty)' if dirty else ''})")

if "--push" in sys.argv:
    from huggingface_hub import HfApi
    api = HfApi()
    api.create_repo(HF_REPO, repo_type="dataset", private=False, exist_ok=True)
    keep = set(os.listdir(OUT)) | {".gitattributes"}
    stale = [f for f in api.list_repo_files(HF_REPO, repo_type="dataset") if f not in keep]
    c = api.upload_folder(repo_id=HF_REPO, repo_type="dataset", folder_path=OUT, delete_patterns=stale or None,
                          commit_message=f"Build from {GH_REPO}/commit/{commit}")
    print("pushed:", c.commit_url, "| removed stale files:", len(stale))
