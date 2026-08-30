#!/usr/bin/env python3
"""Run grasp_metrics + overlay for every grasp in out/, using each Derecha video's fps."""
import subprocess, cv2, os

V = "Videos Cinves"
PRIMARY = {
    "Cilindrico":  f"{V}/Cilíndrico_Derecha.mp4",
    "Esferico":    f"{V}/Esférico_Derecha.mp4",
    "Pinch":       f"{V}/Pinch_Derecha.mp4",
    "Disco":       f"{V}/Disco_Derecha.mp4",
    "Plano":       f"{V}/Plano_Derecha.mp4",
    "SelfieStick": f"{V}/Selfie_Stick_Derecha.mp4",
}
for grasp, vid in PRIMARY.items():
    od = f"out/{grasp}"
    if not os.path.exists(f"{od}/fused.csv"):
        print(f"skip {grasp} (no fused.csv)"); continue
    fps = cv2.VideoCapture(vid).get(cv2.CAP_PROP_FPS) or 30.0
    print(f"\n=== {grasp} (fps {fps:.1f}) ===")
    subprocess.run(["python", "grasp_metrics.py", f"{od}/fused.csv",
                    "--fps", str(fps), "--out-prefix", f"{od}/metrics"], check=False)
    subprocess.run(["python", "overlay_fill.py", "--video", vid,
                    "--primary-csv", f"{od}/der.csv", "--fused-csv", f"{od}/fused.csv",
                    "--out", f"{od}/overlay.mp4"], check=False)
print("\nall done")
