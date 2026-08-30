#!/usr/bin/env python3
"""Side-by-side: primary-only (hallucinated fingers) vs fused (filled from 2nd view)."""
import csv, json, cv2
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from fuse_views import load, kabsch, ANCHORS, FILL, CONNECTIONS

GRASP = "Cilindrico"
OUT = f"out/{GRASP}"
OFFSET = json.load(open(f"{OUT}/sync.json"))["offset_sec"]
FRAME = 300  # Derecha frame to inspect (t=10s)

prim = load(f"{OUT}/der.csv")
sec  = load(f"{OUT}/izq.csv")
fps_sec = cv2.VideoCapture("Videos Cinves/Cilíndrico_Izquierda.mp4").get(cv2.CAP_PROP_FPS)

plm = prim[FRAME]
fs = round((FRAME/30.0 + OFFSET) * fps_sec)
slm = sec[fs]
P = np.array([slm[a] for a in ANCHORS]); Q = np.array([plm[a] for a in ANCHORS])
R, scale, tr, rms = kabsch(P, Q)
print(f"frame {FRAME}: anchor RMS = {rms*100:.2f} cm")

fused = {lid: plm[lid] for lid in plm}
for lid in FILL:
    if lid in slm:
        fused[lid] = scale * R @ slm[lid] + tr

def draw(ax, pts, title):
    for a, b in CONNECTIONS:
        if a in pts and b in pts:
            ax.plot([pts[a][0],pts[b][0]],[pts[a][2],pts[b][2]],[pts[a][1],pts[b][1]],color="0.5",lw=2)
    for lid,p in pts.items():
        filled = lid in FILL
        ax.scatter(p[0],p[2],p[1],color="red" if filled and pts is fused else "royalblue",s=45)
    ax.view_init(elev=-70, azim=-90); ax.set_title(title)
    ax.set_xticks([]);ax.set_yticks([]);ax.set_zticks([])

fig = plt.figure(figsize=(12,6))
draw(fig.add_subplot(121,projection="3d"), plm,   "Derecha only (fingertips hallucinated)")
draw(fig.add_subplot(122,projection="3d"), fused, "Fused (fingertips from Izquierda)")
fig.savefig("docs/compare_fill.png", dpi=110, bbox_inches="tight")
print("wrote docs/compare_fill.png")
