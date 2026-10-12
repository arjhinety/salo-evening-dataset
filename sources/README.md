# Pinned source files

These are the exact input files my build reads. I keep them **unchanged** here, so that anyone can rebuild the same dataset. `verify.py` checks their SHA-256 against `../SHA256SUMS`.

| File | Source | License | SHA-256 |
|---|---|---|---|
| `osm_roads_cubao_project4.json` | OpenStreetMap, via the Overpass API (overpass-api.de), retrieved 2026-10-12 | ODbL 1.0, © OpenStreetMap contributors | `d5976c2a…4807e` |
| `foodgo-orders.csv` | FoodGo Test Dataset v1, Rubinstein, Z. B., Carnegie Mellon University, Zenodo, doi:10.5281/zenodo.3801643 | CC BY 4.0 | `9573fb96…a841` |
| `foodgo-volunteers.csv` | same as above | CC BY 4.0 | `0773ef70…7be` |
| `foodkeeper.json` | USDA FSIS FoodKeeper Data, data version 128, https://catalog.data.gov/dataset/fsis-foodkeeper-data | CC0 1.0 | `037df0d3…91a` |

## How each file was obtained

**OpenStreetMap roads.** This Overpass query covers the Cubao–Project 4 area:

```
[out:json][timeout:60];
(way["highway"~"^(primary|secondary|tertiary|residential|unclassified|trunk|living_street)$"](14.612,121.040,14.640,121.080););
(._;>;);
out body;
```

```
curl -G --data-urlencode "data=<query above>" https://overpass-api.de/api/interpreter -o osm_roads_cubao_project4.json
```

OpenStreetMap is edited constantly. Downloading again **will give different data**, so node IDs, distances and the anchor placement would change. Use the pinned file to reproduce my published dataset.

**FoodGo.** Download `foodgo-test-data.zip` from https://zenodo.org/records/3801643 and unzip it. It contains `foodgo-orders.csv` and `foodgo-volunteers.csv`. Only the distributions are used: lot sizes, vehicle capacities and availability-window lengths. The coordinates are in Pittsburgh, USA, and are not used.

**FoodKeeper.** Download the English JSON ("FoodKeeper Data - English") from https://catalog.data.gov/dataset/fsis-foodkeeper-data. FSIS blocks scripted downloads, so use a browser. The pinned copy is data version 128.

**DOST-FNRI ENNS Food Security public use file.** I planned to use it but **didn't obtain it**; the download form needs the requester's details. `build_dataset.py` stops if `sources/fnri_food_security.csv` appears, so its loader can be written before it is used.
