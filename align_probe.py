#!/usr/bin/env python3
"""Empirical test: how well do the two views' 3D hands align (Kabsch on palm anchors)?"""
import csv, json, cv2
import numpy as np

GRASP = "Cilindrico"
OUT = f"out/{GRASP}"
# B(izq)_time = A(der)_time + OFFSET, as measured by sync_audio.py
OFFSET = json.load(open(f"{OUT}/sync.json"))["offset_sec"]
ANCHORS = [0, 1, 2, 5, 9, 13, 17]  # wrist + thumb base + 4 finger MCPs (palm, visible in both)

def load(csv_path):
    """frame -> {lid: (wx,wy,wz)} from world landmark columns."""
    out = {}
    with open(csv_path) as f:
        for r in csv.DictReader(f):
            if r["wx"] == "":
                continue
            fr = int(r["frame"])
            out.setdefault(fr, {})[int(r["landmark_id"])] = (
                float(r["wx"]), float(r["wy"]), float(r["wz"]))
    return out

def kabsch(P, Q):
    """Rotation+scale+translation mapping P onto Q. Returns aligned P, rms."""
    Pc, Qc = P.mean(0), Q.mean(0)
    P0, Q0 = P - Pc, Q - Qc
    H = P0.T @ Q0
    U, S, Vt = np.linalg.svd(H)
    d = np.sign(np.linalg.det(Vt.T @ U.T))
    D = np.diag([1, 1, d])
    R = Vt.T @ D @ U.T
    scale = (S * [1, 1, d]).sum() / (P0 ** 2).sum()
    aligned = scale * (R @ P0.T).T + Qc
    rms = np.sqrt(((aligned - Q) ** 2).sum(1).mean())
    return aligned, rms

der = load(f"{OUT}/der.csv")
izq = load(f"{OUT}/izq.csv")
fps_izq = cv2.VideoCapture("Videos Cinves/Cilíndrico_Izquierda.mp4").get(cv2.CAP_PROP_FPS)
fps_der = 30.0

pairs, rmss, sizes = 0, [], []
for fd, dlm in sorted(der.items()):
    t = fd / fps_der + OFFSET
    fi = round(t * fps_izq)
    if fi not in izq:
        continue
    ilm = izq[fi]
    if not all(a in dlm and a in ilm for a in ANCHORS):
        continue
    P = np.array([ilm[a] for a in ANCHORS])  # izq -> der
    Q = np.array([dlm[a] for a in ANCHORS])
    _, rms = kabsch(P, Q)
    pairs += 1
    rmss.append(rms)
    sizes.append(np.linalg.norm(Q.max(0) - Q.min(0)))  # palm span (m)

rmss = np.array(rmss); sizes = np.array(sizes)
print(f"synced pairs with all palm anchors in BOTH views: {pairs}")
print(f"palm span (Derecha world)  : {sizes.mean()*100:.1f} cm")
print(f"Kabsch residual on anchors : median {np.median(rmss)*100:.2f} cm  "
      f"(p25 {np.percentile(rmss,25)*100:.2f}, p75 {np.percentile(rmss,75)*100:.2f})")
print(f"residual / palm span       : median {np.median(rmss/ (sizes+1e-9))*100:.1f}%")
print("\nRule of thumb: <15% of palm span = usable fusion; >30% = views too inconsistent.")
