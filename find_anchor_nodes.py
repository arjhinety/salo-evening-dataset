"""Finds OSM road nodes for the anchor rows so road distances match the study guide's worked example."""
import os
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "build_dataset.py"), encoding="utf-8").read()
exec(src[:src.index("# ---------------------------------------------------------------- FoodGo-derived")])  # graph + helpers

D = os.path.join(HERE, "salo-evening-dataset")
pan = pd.read_csv(os.path.join(D, "pantries.csv"))
don = pd.read_csv(os.path.join(D, "donors.csv"))
other_p = [(r.lat, r.lon) for r in pan.itertuples() if not r.anchor]
other_d = [(r.lat, r.lon) for r in don.itertuples() if not r.anchor]


def on(street):
    return [n for n in cand if node_street[n][0] == street]


def free(n, others, km):
    return all(hav(nodes[n], o) >= km for o in others)


best = []
for dn in on("Aurora Boulevard"):
    if not free(dn, other_d, 0.12):
        continue
    dist = dijkstra(dn)
    bukal = [(abs(dist[n] - 1.1), n) for n in on("15th Avenue") if n in dist and free(n, other_p, 0.25)]
    soc = [(abs(dist[n] - 0.6), n) for n in res_cand if n in dist and free(n, other_p, 0.25)]
    if not bukal or not soc:
        continue
    b, s = min(bukal), min(soc)
    if hav(nodes[b[1]], nodes[s[1]]) < 0.25:
        continue
    best.append((b[0] + s[0], dn, b[1], s[1], dist))
best.sort(key=lambda t: t[0])
err, dn, bn, sn, dist = best[0]
an = [n for n in on("Anonas Street") if free(n, other_p + [nodes[bn], nodes[sn]], 0.25)]
an_n = an[0] if an else None
print("D01 node", dn, node_street[dn][0], nodes[dn])
print("Bukal node", bn, node_street[bn][0], nodes[bn], "road_km", round(dist[bn], 2))
print("Socorro node", sn, node_street[sn][0], nodes[sn], "road_km", round(dist[sn], 2))
if an_n:
    print("Anonas node", an_n, node_street[an_n][0], nodes[an_n], "road_km", round(dist[an_n], 2))
print("candidates found:", len(best))
