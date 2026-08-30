#!/usr/bin/env python3
"""
Run the full pipeline (sync -> pose both views -> fuse) for every grasp pair.
Outputs land in out/<grasp>/ . Reuses existing CSVs unless --force.
"""
import json
import os
import subprocess
import sys

V = "Videos Cinves"
PAIRS = [  # (grasp, derecha primary, izquierda secondary)
    ("Cilindrico",   f"{V}/Cilíndrico_Derecha.mp4",        f"{V}/Cilíndrico_Izquierda.mp4"),
    ("Esferico",     f"{V}/Esférico_Derecha.mp4",     f"{V}/Esférico_Izquierda.mp4"),
    ("Pinch",        f"{V}/Pinch_Derecha.mp4",        f"{V}/Pinch_Izquierda.mp4"),
    ("Disco",        f"{V}/Disco_Derecha.mp4",        f"{V}/Disco_Izquierda.mp4"),
    ("Plano",        f"{V}/Plano_Derecha.mp4",        f"{V}/Plano_Izquierda.mp4"),
    ("SelfieStick",  f"{V}/Selfie_Stick_Derecha.mp4", f"{V}/Selfie_Stick_Izquierda.mp4"),
]
FORCE = "--force" in sys.argv


def run(cmd):
    print("  $", " ".join(cmd[:2]), cmd[-1] if len(cmd) > 2 else "")
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def primary_fps(path):
    import cv2
    return cv2.VideoCapture(path).get(cv2.CAP_PROP_FPS)


summary = []
for grasp, der, izq in PAIRS:
    print(f"\n=== {grasp} ===")
    od = f"out/{grasp}"
    os.makedirs(od, exist_ok=True)
    der_csv, izq_csv = f"{od}/der.csv", f"{od}/izq.csv"
    sync_json, fused_csv, fused_vid = f"{od}/sync.json", f"{od}/fused.csv", f"{od}/fused_3d.mp4"

    if not (os.path.exists(der) and os.path.exists(izq)):
        print(f"  !! missing files, skipping ({der} / {izq})")
        summary.append((grasp, "MISSING", "", "", ""))
        continue

    if FORCE or not os.path.exists(der_csv):
        run(["python", "hand_pose.py", der, "--no-video", "--csv", der_csv, "--out", f"{od}/_der.mp4"])
    if FORCE or not os.path.exists(izq_csv):
        run(["python", "hand_pose.py", izq, "--no-video", "--csv", izq_csv, "--out", f"{od}/_izq.mp4"])
    if FORCE or not os.path.exists(sync_json):
        run(["python", "sync_audio.py", der, izq, "--json", sync_json])

    sync = json.load(open(sync_json))
    run(["python", "fuse_views.py", "--primary", der_csv, "--primary-fps", str(primary_fps(der)),
         "--secondary", izq_csv, "--secondary-video", izq, "--offset", str(sync["offset_sec"]),
         "--out-csv", fused_csv, "--out-video", fused_vid])

    # quick stats from fused csv
    import csv as _csv
    frames, filled = set(), 0
    for r in _csv.DictReader(open(fused_csv)):
        frames.add(r["frame"])
        filled += r["source"] == "filled"
    summary.append((grasp, f"sync {sync['confidence']:.1f}",
                    f"off {sync['offset_sec']:+.3f}s", f"{len(frames)} frames", f"{filled} fills"))

print("\n\n==================  SUMMARY  ==================")
for row in summary:
    print(f"{row[0]:14s} {row[1]:12s} {row[2]:12s} {row[3]:14s} {row[4]}")
