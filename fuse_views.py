#!/usr/bin/env python3
"""
Fuse two synced, uncalibrated hand views into one 3D skeleton, filling the
fingers occluded in the primary (Derecha) view with the secondary (Izquierda) view.

Method (no camera calibration):
  - pair frames by timestamp using the audio-sync offset
  - per frame, Kabsch-align the secondary view's 3D onto the primary's using the
    palm + knuckles (visible in BOTH), recovering the fixed inter-camera rotation
  - substitute the primary view's occluded fingertip/distal joints with the
    secondary view's aligned ones (only when alignment residual is trustworthy)

Outputs:
  fused_landmarks.csv      world coords per frame, with a per-point `source` column
  fused_pose_3d.mp4        rendered 3D skeleton (blue = primary, red = filled-in)

Usage:
  python fuse_views.py --primary out/Cilindrico/der.csv --primary-fps 30 \
                       --secondary out/Cilindrico/izq.csv \
                       --secondary-video "Videos Cinves/Cilíndrico_Izquierda.mp4" \
                       --offset 0.4724 \
                       --out-csv out/Cilindrico/fused.csv \
                       --out-video out/Cilindrico/fused_3d.mp4
"""
import argparse
import csv
import os

import cv2
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

NAMES = ["WRIST", "THUMB_CMC", "THUMB_MCP", "THUMB_IP", "THUMB_TIP",
         "INDEX_MCP", "INDEX_PIP", "INDEX_DIP", "INDEX_TIP",
         "MIDDLE_MCP", "MIDDLE_PIP", "MIDDLE_DIP", "MIDDLE_TIP",
         "RING_MCP", "RING_PIP", "RING_DIP", "RING_TIP",
         "PINKY_MCP", "PINKY_PIP", "PINKY_DIP", "PINKY_TIP"]
CONNECTIONS = [(0,1),(1,2),(2,3),(3,4),(0,5),(5,6),(6,7),(7,8),(5,9),(9,10),
               (10,11),(11,12),(9,13),(13,14),(14,15),(15,16),(13,17),
               (17,18),(18,19),(19,20),(0,17)]
ANCHORS = [0, 1, 2, 5, 9, 13, 17]                          # palm + knuckles
FILL    = [3, 4, 6, 7, 8, 10, 11, 12, 14, 15, 16, 18, 19, 20]  # distal joints (occluded in primary)


def load(csv_path):
    out = {}
    with open(csv_path) as f:
        for r in csv.DictReader(f):
            if r["wx"] == "":
                continue
            fr = int(r["frame"])
            out.setdefault(fr, {})[int(r["landmark_id"])] = np.array(
                [float(r["wx"]), float(r["wy"]), float(r["wz"])])
    return out


def kabsch(P, Q):
    """Similarity transform mapping P->Q. Returns (R, scale, t, rms)."""
    Pc, Qc = P.mean(0), Q.mean(0)
    P0, Q0 = P - Pc, Q - Qc
    U, S, Vt = np.linalg.svd(P0.T @ Q0)
    d = np.sign(np.linalg.det(Vt.T @ U.T))
    R = Vt.T @ np.diag([1, 1, d]) @ U.T
    scale = (S * [1, 1, d]).sum() / (P0 ** 2).sum()
    t = Qc - scale * R @ Pc
    rms = np.sqrt((((scale * (R @ P0.T).T) - Q0) ** 2).sum(1).mean())
    return R, scale, t, rms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--primary", required=True, help="primary view landmark CSV (reference frame)")
    ap.add_argument("--primary-fps", type=float, default=30.0)
    ap.add_argument("--secondary", required=True, help="secondary view landmark CSV")
    ap.add_argument("--secondary-video", required=True, help="secondary video (for fps)")
    ap.add_argument("--offset", type=float, required=True, help="secondary_time = primary_time + offset")
    ap.add_argument("--max-resid", type=float, default=0.020, help="max anchor RMS (m) to trust a fill")
    ap.add_argument("--out-csv", default="fused_landmarks.csv")
    ap.add_argument("--out-video", default="fused_pose_3d.mp4")
    args = ap.parse_args()

    prim = load(args.primary)
    sec = load(args.secondary)
    fps_sec = cv2.VideoCapture(args.secondary_video).get(cv2.CAP_PROP_FPS)

    fused_frames = []   # (frame, {lid: xyz}, {lid: source})
    n_fill, n_total_fillable, n_fused = 0, 0, 0

    for fp in sorted(prim):
        plm = prim[fp]
        if not all(a in plm for a in ANCHORS):
            continue
        t = fp / args.primary_fps + args.offset
        fs = round(t * fps_sec)
        pts = {lid: plm[lid] for lid in plm}      # start from primary
        src = {lid: "primary" for lid in plm}

        slm = sec.get(fs)
        if slm and all(a in slm for a in ANCHORS):
            P = np.array([slm[a] for a in ANCHORS])
            Q = np.array([plm[a] for a in ANCHORS])
            R, scale, tr, rms = kabsch(P, Q)
            if rms <= args.max_resid:
                n_fused += 1
                for lid in FILL:
                    n_total_fillable += 1
                    if lid in slm:
                        pts[lid] = scale * R @ slm[lid] + tr   # secondary -> primary frame
                        src[lid] = "filled"
                        n_fill += 1
        fused_frames.append((fp, pts, src))

    # ---- write fused CSV ----
    with open(args.out_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["frame", "landmark_id", "name", "wx", "wy", "wz", "source"])
        for fr, pts, src in fused_frames:
            for lid in range(21):
                if lid in pts:
                    x, y, z = pts[lid]
                    w.writerow([fr, lid, NAMES[lid], f"{x:.5f}", f"{y:.5f}", f"{z:.5f}", src[lid]])

    # ---- render 3D skeleton video ----
    # fixed axis limits from all points for a stable view
    allp = np.array([p for _, pts, _ in fused_frames for p in pts.values()])
    ctr = allp.mean(0); rad = np.abs(allp - ctr).max() * 1.1
    H, W = 720, 720
    vw = cv2.VideoWriter(args.out_video, cv2.VideoWriter_fourcc(*"mp4v"),
                         args.primary_fps, (W, H))
    fig = plt.figure(figsize=(W/100, H/100), dpi=100)
    for fr, pts, src in fused_frames:
        ax = fig.add_subplot(111, projection="3d")
        for a, b in CONNECTIONS:
            if a in pts and b in pts:
                xs = [pts[a][0], pts[b][0]]; ys = [pts[a][1], pts[b][1]]; zs = [pts[a][2], pts[b][2]]
                ax.plot(xs, zs, ys, color="0.5", lw=2)
        for lid, p in pts.items():
            c = "red" if src[lid] == "filled" else "royalblue"
            ax.scatter(p[0], p[2], p[1], color=c, s=40)
        ax.set_xlim(ctr[0]-rad, ctr[0]+rad); ax.set_zlim(ctr[1]+rad, ctr[1]-rad)
        ax.set_ylim(ctr[2]-rad, ctr[2]+rad)
        ax.set_title(f"frame {fr}   blue=primary  red=filled-from-2nd-view")
        ax.view_init(elev=-70, azim=-90)
        ax.set_xticks([]); ax.set_yticks([]); ax.set_zticks([])
        fig.canvas.draw()
        buf = np.frombuffer(fig.canvas.buffer_rgba(), dtype=np.uint8)
        img = buf.reshape(fig.canvas.get_width_height()[::-1] + (4,))[:, :, :3]
        vw.write(cv2.cvtColor(cv2.resize(img, (W, H)), cv2.COLOR_RGB2BGR))
        fig.clf()
    vw.release(); plt.close(fig)

    print(f"primary frames used      : {len(fused_frames)}")
    print(f"frames with a good fusion : {n_fused}")
    print(f"distal joints filled      : {n_fill}/{n_total_fillable} "
          f"({100*n_fill/max(n_total_fillable,1):.0f}% of fillable in fused frames)")
    print(f"  fused landmarks -> {args.out_csv}")
    print(f"  3D skeleton vid -> {args.out_video}")


if __name__ == "__main__":
    main()
