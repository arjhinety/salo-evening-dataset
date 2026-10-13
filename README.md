# Salo Evening Dataset: build code

This repository builds my **Salo Evening Dataset**, published at
**https://huggingface.co/datasets/arjhinety/salo-evening-dataset**.

I built this dataset for **Salo**, the multi-agent food rescue system I proposed for my CS 403 (Intelligent Agents) project at the Technological Institute of the Philippines – Quezon City, 1st Semester S.Y. 2026–2027. Salo matches surplus food from small food businesses (karinderyas, panaderias, stalls) to community pantries in the Cubao–Project 4 area of Quezon City, Philippines.

I combined three public sources, pinned in [`sources/`](sources/), with simulated data from a seeded script:
- OpenStreetMap roads;
- FoodGo delivery patterns;
- USDA FoodKeeper storage times.

All business, pantry and volunteer names are fictional, and I included no real person's private information.

## Regenerate the dataset

Requirements: **Python 3.12** and the versions pinned in `requirements.txt`. Other pandas or pyarrow versions should give the same values, but byte-for-byte checksums are only guaranteed with the pinned versions.

```bash
git clone https://github.com/arjhinety/salo-evening-dataset.git
cd salo-evening-dataset
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

python build_dataset.py      # writes salo-evening-dataset/ (11 tables + sources.csv + parameters.csv)
python verify.py             # rebuilds and checks every file against SHA256SUMS
```

`verify.py` should print **`17 of 17 files match SHA256SUMS`**:
- 4 pinned source files;
- 11 tables;
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
| 8. Messages | `messages.py` | Samples 17 lots per evening, each evening with its own seed, and writes one donor message **from** each lot's fields, so the gold labels are correct by construction (510 messages). Records `split` and `template_id`. |
| 9. Provenance | `build_dataset.py` | Writes `sources.csv` (source and status of every field) and `parameters.csv` (every assumed number). |

I keep every assumed number in `params.json`, so they can be changed in one place. Changing any of them changes the data, so run `python verify.py --update` to record new checksums.

## Important caveats

- **The data is simulated.** It shows how agents behave on plausible inputs. It is not evidence of real-world performance.
- **The messages are template-based.** Any parsing accuracy measured on them is an optimistic upper bound.
  - Tune only on `tuning` messages, and report only on `pilot` / `main_sample`.
  - Even pilot/main messages reuse tuning phrasings, so their accuracy does not measure how a parser handles new phrasings.
- **FNRI was not used.** I planned to use the DOST-FNRI survey but didn't obtain it, so the food-insecure share (0.30) is my assumption.
- **The pantries are fictional.** My project proposal planned a real list that I would gather myself. That list needs the organisers' permission, so I used fictional pantries for now.

Full details are in the [dataset card](https://huggingface.co/datasets/arjhinety/salo-evening-dataset).

## Changelog

### v1.2 (2026-10-13)

- **Travel times for every vehicle.** In `road_distances`, the new columns `est_min_bicycle` and `est_min_tricycle` add assumed speeds for bicycles (12 km/h + 2 min handling) and tricycles (15 km/h + 4 min). The 7 bicycle and tricycle drivers had no travel time before.
- **New table `driver_distances`** (2,000 rows): road km from each driver's home road node to each donor (OpenStreetMap shortest paths), and the minutes in the driver's own vehicle. It is the first leg of a run's arrival time. The second leg, donor to pantry, is in `road_distances`.
- **Append-only:** no new random draws. The other 9 data tables are byte-identical to v1.1. The original `road_distances` columns are unchanged, and `parameters.csv` and `sources.csv` gain rows for the new fields. `verify.py` checks 17 files.

### v1.1 (2026-10-13)

- **Donor messages are now sampled per evening.** In v1.0, `messages.py` drew 500 lots from all 30 evenings at once and wrote them from a single random stream. Adding evenings would therefore have changed every earlier evening's messages. I checked this: in a 40-evening test build, only 1 of 164 shared E01–E20 lots kept the same message. Now each evening samples 17 of its own lots and writes their messages with its own generator, seeded from that evening's seed. Message IDs run in evening order. So adding main evenings, if the pilot asks for more, only appends messages at the end.
- **Verified append-only.** A 40-evening test build (20 main evenings) reproduces all 510 v1.1 messages for E01–E30 exactly, in every column including `message_id`. The new evenings' messages start at M0511.
- **What changed in the data** (10 tables, 4,925 rows):
  - `donor_messages` now has 510 rows (170 tuning, 170 pilot, 170 main_sample; v1.0 had 500: 163 / 166 / 171), and every message is new.
  - All other tables are byte-identical to v1.0, and `SHA256SUMS` was updated for `donor_messages.csv` only.
  - 330 of the 340 pilot/main messages use only phrasings that also appear in tuning messages (v1.0: 96%).
- **Code:** `build_dataset.py` sets the number of evenings per split in one place (`N_EVENINGS`).
- **Not affected:** no parser prompt or rule had been tuned on the v1.0 messages. My submitted dataset report (PDF) describes v1.0.

### v1.0 (2026-10-12)

- First release: 10 tables, 4,915 rows, built from commit e6e27a2.

## Licenses

- **Code** (`*.py`, `*.json` configuration): MIT, see [`LICENSE`](LICENSE).
- **Pinned sources:** each keeps its own license (ODbL 1.0, CC BY 4.0, CC0 1.0). See [`sources/README.md`](sources/README.md).
- **Generated tables** (on Hugging Face):
  - ODbL 1.0 for the tables containing OpenStreetMap-derived data: pantries, donors, drivers, road_distances, driver_distances, donor_messages;
  - CC BY 4.0 for the others.

Attribution: © OpenStreetMap contributors; Rubinstein, Z. B. (2020), *FoodGo Test Dataset*, Zenodo, doi:10.5281/zenodo.3801643; USDA FSIS FoodKeeper Data.
