# Salo Evening Dataset: build code

This repository builds the **Salo Evening Dataset**, published at
**https://huggingface.co/datasets/arjhinety/salo-evening-dataset**.

Salo is a proposed multi-agent food rescue system. It matches surplus food from small food businesses (karinderyas, panaderias, stalls) to community pantries in the Cubao–Project 4 area of Quezon City, Philippines. It was made for CS 403 (Intelligent Agents), Technological Institute of the Philippines – Quezon City, 1st Semester S.Y. 2026–2027. **Compiled by Arjhine A. Ty** (solo project).

The dataset combines three public sources, pinned in [`sources/`](sources/), with simulated data from a seeded script:
- OpenStreetMap roads;
- FoodGo delivery patterns;
- USDA FoodKeeper storage times.

All business, pantry and volunteer names are fictional, and no real person's private information is included.

## Regenerate the dataset

Requirements: **Python 3.12** and the versions pinned in `requirements.txt`. Other pandas or pyarrow versions should give the same values, but byte-for-byte checksums are only guaranteed with the pinned versions.

```bash
git clone https://github.com/arjhinety/salo-evening-dataset.git
cd salo-evening-dataset
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

python build_dataset.py      # writes salo-evening-dataset/ (10 tables + sources.csv + parameters.csv)
python verify.py             # rebuilds and checks every file against SHA256SUMS
```

`verify.py` should print **`16 of 16 files match SHA256SUMS`**:
- 4 pinned source files;
- 10 tables;
- `sources.csv` and `parameters.csv`.

The build is seeded (`SEED = 20260927`), so it gives the same files every time.

To produce the Hugging Face layout (Parquet tables, dataset card, `LICENSE.md`, `CITATIONS.bib`, `hash.txt`):

```bash
python export_hf.py          # writes hf/
python export_hf.py --push   # maintainer only: uploads hf/ (refuses if the git tree has uncommitted changes)
```

The dataset card records the exact commit of this repository that built the published data.

## What the build does

| Step | Where | What happens |
|---|---|---|
| 1. Road graph | `build_dataset.py` | Loads the pinned OSM extract and keeps the largest connected road network (roads treated as two-way). |
| 2. Distributions | `build_dataset.py` | Reads FoodGo's lot sizes (1–3 units), driver capacities (3–5 units) and 4-hour availability windows. |
| 3. Storage rules | `build_dataset.py` | Matches each food item to a FoodKeeper product. Copies its storage times and derives `needs_fridge_if_kept`. `max_hours_unrefrigerated` is an **assumption** (`storage_rules.json`), capped by FoodKeeper only for eggplant. |
| 4. Places | `build_dataset.py` | Places 30 fictional pantries, 50 donors and 40 drivers on real road nodes. |
| 5. Evenings | `build_dataset.py` | Creates 30 seeded evenings (10 tuning, 10 pilot, 10 main_sample). Need is fixed at 16:00, and posted food is 0.6–0.9× total need. |
| 6. Driver runs | `build_dataset.py` | Creates runs **only** on tuning evenings E01–E10, each a real lot with no overlapping windows. Reliability = (shows + 1) ÷ (runs + 2), then frozen. |
| 7. Anchors | `build_dataset.py`, `find_anchor_nodes.py` | Hand-placed rows reproduce the project's worked examples, after every random draw (`anchor = True`). |
| 8. Messages | `messages.py` | Writes 500 donor messages **from** each lot's fields, so the gold labels are correct by construction. Records `split` and `template_id`. |
| 9. Provenance | `build_dataset.py` | Writes `sources.csv` (source and status of every field) and `parameters.csv` (every assumed number). |

All assumed numbers live in `params.json`, so they can be changed in one place. Changing any of them changes the data, so run `python verify.py --update` to record new checksums.

## Important caveats

- **The data is simulated.** It shows how agents behave on plausible inputs. It is not evidence of real-world performance.
- **The messages are template-based.** Any parsing accuracy measured on them is an optimistic upper bound.
  - Tune only on `tuning` messages, and report only on `pilot` / `main_sample`.
  - Even pilot/main messages reuse tuning phrasings, so their accuracy does not measure how a parser handles new phrasings.
- **FNRI was not used.** The food-insecure share (0.30) is an assumption, and the DOST-FNRI survey was not obtained.
- **The pantries are fictional.** The project proposal planned a real list. That list would need the organisers' permission.

Full details are in the [dataset card](https://huggingface.co/datasets/arjhinety/salo-evening-dataset).

## Licenses

- **Code** (`*.py`, `*.json` configuration): MIT, see [`LICENSE`](LICENSE).
- **Pinned sources:** each keeps its own license (ODbL 1.0, CC BY 4.0, CC0 1.0). See [`sources/README.md`](sources/README.md).
- **Generated tables** (on Hugging Face):
  - ODbL 1.0 for the tables containing OpenStreetMap-derived data: pantries, donors, drivers, road_distances, donor_messages;
  - CC BY 4.0 for the others.

Attribution: © OpenStreetMap contributors; Rubinstein, Z. B. (2020), *FoodGo Test Dataset*, Zenodo, doi:10.5281/zenodo.3801643; USDA FSIS FoodKeeper Data.
