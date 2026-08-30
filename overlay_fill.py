#!/usr/bin/env python3
"""
Overlay the fused skeleton onto the primary (Derecha) video, drawing the
filled-in fingers (from the 2nd view) in red so you see the occluded fingers
recovered in 2D.

Projection without intrinsics: per frame, fit an affine camera (3x4) mapping the
primary view's world coords -> its own image pixels using the well-seen points
(which have BOTH world and pixel coords in the primary CSV). Apply that camera to
the fused 3D points to get pixel positions for the filled fingers.

Usage:
  python overlay_fill.py --video "Videos Cinves/Cilíndrico_Derecha.mp4" \
      --primary-csv out/Cilindrico/der.csv \
      --fused-csv out/Cilindrico/fused.csv --out out/Cilindrico/overlay.mp4
"""
import argparse
import csv

import cv2
import numpy as np

CONNECTIONS = [(0,1),(1,2),(2,3),(3,4),(0,5),(5,6),(6,7),(7,8),(5,9),(9,10),
               (10,11),(11,12),(9,13),(13,14),(14,15),(15,16),(13,17),
               (17,18),(18,19),(19,20),(0,17)]
FILL = {3,4,6,7,8,10,11,12,14,15,16,18,19,20}


def load_primary(path):
    """frame -> {lid: (world xyz, pixel xy)}"""
    out = {}
    for r in csv.DictReader(open(path)):
        if r["wx"] == "":
            continue
        out.setdefault(int(r["frame"]), {})[int(r["landmark_id"])] = (
            np.array([float(r["wx"]), float(r["wy"]), float(r["wz"])]),
            np.array([float(r["x_px"]), float(r["y_px"])]))
    return out


def load_fused(path):
    out, srcs = {}, {}
    for r in csv.DictReader(open(path)):
        fr = int(r["frame"]); lid = int(r["landmark_id"])
        out.setdefault(fr, {})[lid] = np.array([float(r["wx"]), float(r["wy"]), float(r["wz"])])
        srcs.setdefault(fr, {})[lid] = r["source"]
    return out, srcs


def fit_affine_cam(world, pixel):
    """least-squares 3x4 affine mapping homogeneous world -> pixel. world:(N,3) pixel:(N,2)"""
    N = len(world)
    A = np.hstack([world, np.ones((N, 1))])      # N x 4
    M, *_ = np.linalg.lstsq(A, pixel, rcond=None)  # 4 x 2
    return M


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--primary-csv", required=True)
    ap.add_argument("--fused-csv", required=True)
    ap.add_argument("--out", default="fused_overlay.mp4")
    args = ap.parse_args()

    prim = load_primary(args.primary_csv)
    fused, srcs = load_fused(args.fused_csv)

    cap = cv2.VideoCapture(args.video)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    vw = cv2.VideoWriter(args.out, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))

    fi, drawn = 0, 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if fi in fused and fi in prim:
            # fit camera from primary points present in BOTH world+pixel
            pl = prim[fi]
            world = np.array([pl[l][0] for l in pl])
            pixel = np.array([pl[l][1] for l in pl])
            if len(world) >= 6:
                M = fit_affine_cam(world, pixel)
                pts = fused[fi]; src = srcs[fi]
                proj = {l: (np.append(pts[l], 1.0) @ M) for l in pts}
                for a, b in CONNECTIONS:
                    if a in proj and b in proj:
                        cv2.line(frame, tuple(proj[a].astype(int)), tuple(proj[b].astype(int)),
                                 (200, 200, 200), 2)
                for l, q in proj.items():
                    filled = src.get(l) == "filled" and l in FILL
                    cv2.circle(frame, tuple(q.astype(int)), 5,
                               (0, 0, 255) if filled else (255, 130, 0), -1)
                drawn += 1
                cv2.putText(frame, "red = finger recovered from 2nd view", (20, 35),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        vw.write(frame)
        fi += 1
    cap.release(); vw.release()
    print(f"overlaid {drawn} frames -> {args.out}")


if __name__ == "__main__":
    main()
