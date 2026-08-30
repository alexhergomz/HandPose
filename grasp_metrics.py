#!/usr/bin/env python3
"""
Grasp metrics from a fused (or single-view) landmark CSV with world coords.

Computes per frame:
  - aperture: thumb-tip <-> index-tip distance (cm)
  - per-finger flexion: total joint-angle bend at PIP+DIP (and IP) in degrees
  - contact proxy: fingertip spread (mean tip distance from palm center)
Writes a metrics CSV and a summary plot. Flags an approximate "grasp closed"
window where aperture is below 60% of its range.

Usage:
  python grasp_metrics.py FUSED.csv [--fps 30] [--out-prefix out/Cilindrico/metrics]
"""
import argparse
import csv
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

TIPS = {"thumb": 4, "index": 8, "middle": 12, "ring": 16, "pinky": 20}
# (mcp, pip/ip, dip/tip-1, tip) chains for flexion
CHAINS = {
    "thumb":  [1, 2, 3, 4],
    "index":  [5, 6, 7, 8],
    "middle": [9, 10, 11, 12],
    "ring":   [13, 14, 15, 16],
    "pinky":  [17, 18, 19, 20],
}
PALM = [0, 5, 9, 13, 17]


def load(csv_path):
    """frame -> {lid: xyz}. Works for fused.csv (wx/wy/wz) or *_landmarks.csv."""
    out = {}
    with open(csv_path) as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        if r.get("wx", "") == "":
            continue
        out.setdefault(int(r["frame"]), {})[int(r["landmark_id"])] = np.array(
            [float(r["wx"]), float(r["wy"]), float(r["wz"])])
    return out


def joint_angle(a, b, c):
    """angle at b (degrees) between b->a and b->c."""
    u, v = a - b, c - b
    cos = np.dot(u, v) / (np.linalg.norm(u) * np.linalg.norm(v) + 1e-9)
    return np.degrees(np.arccos(np.clip(cos, -1, 1)))


def flexion(pts, chain):
    """sum of bend (180 - interior angle) over the two interior joints."""
    total = 0.0
    for i in range(1, len(chain) - 1):
        a, b, c = pts[chain[i-1]], pts[chain[i]], pts[chain[i+1]]
        total += 180.0 - joint_angle(a, b, c)
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--fps", type=float, default=30.0)
    ap.add_argument("--out-prefix", default=None)
    args = ap.parse_args()
    prefix = args.out_prefix or os.path.splitext(args.csv)[0] + "_metrics"

    data = load(args.csv)
    frames = sorted(data)
    rows = []
    for fr in frames:
        p = data[fr]
        if not all(i in p for i in range(21)):
            continue
        t = fr / args.fps
        aperture = np.linalg.norm(p[4] - p[8]) * 100  # cm
        flex = {name: flexion(p, ch) for name, ch in CHAINS.items()}
        palm_c = np.mean([p[i] for i in PALM], axis=0)
        spread = np.mean([np.linalg.norm(p[t_] - palm_c) for t_ in TIPS.values()]) * 100
        rows.append((fr, t, aperture, spread, flex))

    # write metrics csv
    finger_names = list(CHAINS)
    with open(prefix + ".csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["frame", "time_s", "aperture_cm", "tip_spread_cm"] +
                   [f"flex_{n}_deg" for n in finger_names])
        for fr, t, ap_, sp, flex in rows:
            w.writerow([fr, f"{t:.3f}", f"{ap_:.2f}", f"{sp:.2f}"] +
                       [f"{flex[n]:.1f}" for n in finger_names])

    # closed window: aperture below 60% of its range
    ap_arr = np.array([r[2] for r in rows])
    ts = np.array([r[1] for r in rows])
    thr = ap_arr.min() + 0.4 * (ap_arr.max() - ap_arr.min())
    closed = ap_arr <= thr

    # plots
    fig, axs = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    axs[0].plot(ts, ap_arr, label="aperture (thumb-index)", color="crimson")
    axs[0].plot(ts, [r[3] for r in rows], label="fingertip spread", color="teal", alpha=.7)
    axs[0].fill_between(ts, 0, ap_arr.max(), where=closed, color="gray", alpha=.15, label="grasp closed")
    axs[0].set_ylabel("cm"); axs[0].legend(loc="upper right"); axs[0].set_title(os.path.basename(args.csv))
    for n in finger_names:
        axs[1].plot(ts, [r[4][n] for r in rows], label=n)
    axs[1].set_ylabel("flexion (deg)"); axs[1].set_xlabel("time (s)"); axs[1].legend(ncol=5, loc="upper right")
    fig.tight_layout(); fig.savefig(prefix + ".png", dpi=110)

    if closed.any():
        print(f"grasp closed ~ {ts[closed][0]:.2f}-{ts[closed][-1]:.2f}s "
              f"(aperture {ap_arr.min():.1f}-{ap_arr.max():.1f} cm)")
    print(f"  metrics csv -> {prefix}.csv")
    print(f"  plot        -> {prefix}.png")


if __name__ == "__main__":
    main()
