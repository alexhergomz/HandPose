#!/usr/bin/env bash
# Download the MediaPipe HandLandmarker model bundle (~7.5 MB) used by hand_pose.py.
set -euo pipefail
URL="https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
DEST="$(dirname "$0")/hand_landmarker.task"
if [ -f "$DEST" ]; then
  echo "already present: $DEST"
  exit 0
fi
echo "downloading hand_landmarker.task ..."
curl -fL --progress-bar "$URL" -o "$DEST"
echo "-> $DEST"
