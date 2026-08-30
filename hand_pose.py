#!/usr/bin/env python3
"""
Hand pose estimation with MediaPipe HandLandmarker (Tasks API).

Reads a video, detects 21 3D hand landmarks per frame, writes:
  - an annotated video with the skeleton drawn on each frame
  - a CSV of per-frame landmark coordinates (normalized + pixel + world)

Usage:
    python hand_pose.py INPUT.mp4 [--out OUT.mp4] [--csv OUT.csv]
                                  [--model hand_landmarker.task] [--max-hands N]
"""
import argparse
import csv
import os

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

# Human-readable names for the 21 MediaPipe hand landmarks.
LANDMARK_NAMES = [
    "WRIST",
    "THUMB_CMC", "THUMB_MCP", "THUMB_IP", "THUMB_TIP",
    "INDEX_MCP", "INDEX_PIP", "INDEX_DIP", "INDEX_TIP",
    "MIDDLE_MCP", "MIDDLE_PIP", "MIDDLE_DIP", "MIDDLE_TIP",
    "RING_MCP", "RING_PIP", "RING_DIP", "RING_TIP",
    "PINKY_MCP", "PINKY_PIP", "PINKY_DIP", "PINKY_TIP",
]

# Skeleton connections (pairs of landmark ids) for drawing.
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),            # thumb
    (0, 5), (5, 6), (6, 7), (7, 8),            # index
    (5, 9), (9, 10), (10, 11), (11, 12),       # middle
    (9, 13), (13, 14), (14, 15), (15, 16),     # ring
    (13, 17), (17, 18), (18, 19), (19, 20),    # pinky
    (0, 17),                                   # palm base
]


def draw(frame, landmarks, w, h):
    for a, b in HAND_CONNECTIONS:
        pa = (int(landmarks[a].x * w), int(landmarks[a].y * h))
        pb = (int(landmarks[b].x * w), int(landmarks[b].y * h))
        cv2.line(frame, pa, pb, (255, 255, 255), 2)
    for lm in landmarks:
        cv2.circle(frame, (int(lm.x * w), int(lm.y * h)), 4, (0, 0, 255), -1)


def main():
    ap = argparse.ArgumentParser(description="Hand pose estimation (MediaPipe HandLandmarker)")
    ap.add_argument("input", help="input video path")
    ap.add_argument("--out", default=None, help="annotated output video (default: <input>_pose.mp4)")
    ap.add_argument("--csv", default=None, help="landmark CSV (default: <input>_landmarks.csv)")
    ap.add_argument("--model", default="hand_landmarker.task", help="path to .task model bundle")
    ap.add_argument("--max-hands", type=int, default=2, help="max hands to detect (default 2)")
    ap.add_argument("--det-conf", type=float, default=0.5, help="min hand-detection confidence")
    ap.add_argument("--no-video", action="store_true", help="skip writing the annotated video (faster)")
    args = ap.parse_args()

    base, _ = os.path.splitext(args.input)
    out_path = args.out or f"{base}_pose.mp4"
    csv_path = args.csv or f"{base}_landmarks.csv"

    cap = cv2.VideoCapture(args.input)
    if not cap.isOpened():
        raise SystemExit(f"Could not open {args.input}")

    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    writer = None if args.no_video else cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))

    csv_file = open(csv_path, "w", newline="")
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow([
        "frame", "hand_index", "handedness", "score",
        "landmark_id", "name",
        "x_norm", "y_norm", "z_norm",   # normalized to image (z relative to wrist depth)
        "x_px", "y_px",                 # pixel coordinates
        "wx", "wy", "wz",               # world coords in meters (origin at hand center)
    ])

    options = vision.HandLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=args.model),
        running_mode=vision.RunningMode.VIDEO,
        num_hands=args.max_hands,
        min_hand_detection_confidence=args.det_conf,
        min_hand_presence_confidence=args.det_conf,
        min_tracking_confidence=0.5,
    )
    landmarker = vision.HandLandmarker.create_from_options(options)

    frame_idx = 0
    detected_frames = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        timestamp_ms = int(frame_idx * 1000.0 / fps)
        result = landmarker.detect_for_video(mp_image, timestamp_ms)

        if result.hand_landmarks:
            detected_frames += 1
            for hi, landmarks in enumerate(result.hand_landmarks):
                handed = result.handedness[hi][0]
                label, score = handed.category_name, handed.score
                world = result.hand_world_landmarks[hi] if result.hand_world_landmarks else None

                draw(frame, landmarks, w, h)

                for lid, lm in enumerate(landmarks):
                    wl = world[lid] if world else None
                    csv_writer.writerow([
                        frame_idx, hi, label, f"{score:.3f}",
                        lid, LANDMARK_NAMES[lid],
                        f"{lm.x:.5f}", f"{lm.y:.5f}", f"{lm.z:.5f}",
                        int(lm.x * w), int(lm.y * h),
                        f"{wl.x:.5f}" if wl else "", f"{wl.y:.5f}" if wl else "", f"{wl.z:.5f}" if wl else "",
                    ])

                wrist = landmarks[0]
                cv2.putText(frame, f"{label} {score:.2f}",
                            (int(wrist.x * w), int(wrist.y * h) - 12),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        if writer is not None:
            writer.write(frame)
        frame_idx += 1
        if total and frame_idx % 60 == 0:
            print(f"  {frame_idx}/{total} frames  ({detected_frames} with a hand)")

    cap.release()
    if writer is not None:
        writer.release()
    csv_file.close()
    landmarker.close()

    pct = 100.0 * detected_frames / frame_idx if frame_idx else 0.0
    print(f"\nDone. {frame_idx} frames, hand detected in {detected_frames} ({pct:.1f}%).")
    print(f"  annotated video -> {out_path}")
    print(f"  landmarks csv   -> {csv_path}")


if __name__ == "__main__":
    main()
