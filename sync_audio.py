#!/usr/bin/env python3
"""
Find the time offset between two videos by cross-correlating their audio tracks.

Two simultaneous recordings produce a SHARP correlation peak; independent takes
do not -- so the peak sharpness also tells you whether the videos are in sync-able.

Prints (and optionally writes JSON):
    offset_sec : add this to a view-A timestamp to get the matching view-B timestamp
                 (B_time = A_time + offset_sec)
    confidence : peak height / 99th-percentile of correlation (>~5 is a clean match)

Usage:
    python sync_audio.py VIDEO_A.mp4 VIDEO_B.mp4 [--sr 16000] [--json out.json]
"""
import argparse
import json
import subprocess
import tempfile
import os

import numpy as np
from scipy.io import wavfile
from scipy.signal import correlate


def load_audio(path, sr):
    """Extract mono PCM audio at sample rate `sr` via ffmpeg."""
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    subprocess.run(
        ["ffmpeg", "-y", "-i", path, "-ac", "1", "-ar", str(sr),
         "-vn", "-f", "wav", tmp.name],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    rate, data = wavfile.read(tmp.name)
    os.unlink(tmp.name)
    if data.ndim > 1:
        data = data.mean(axis=1)
    data = data.astype(np.float64)
    data -= data.mean()
    n = np.linalg.norm(data)
    if n > 0:
        data /= n
    return data


def main():
    ap = argparse.ArgumentParser(description="Audio-sync two videos via cross-correlation")
    ap.add_argument("video_a")
    ap.add_argument("video_b")
    ap.add_argument("--sr", type=int, default=16000, help="resample rate for correlation")
    ap.add_argument("--json", default=None, help="write result to this JSON file")
    args = ap.parse_args()

    print(f"Extracting audio @ {args.sr} Hz ...")
    a = load_audio(args.video_a, args.sr)
    b = load_audio(args.video_b, args.sr)
    print(f"  A: {len(a)/args.sr:.2f}s   B: {len(b)/args.sr:.2f}s")

    # full cross-correlation; lag = argmax shifted by len(b)-1
    corr = correlate(a, b, mode="full", method="fft")
    lag = np.argmax(np.abs(corr)) - (len(b) - 1)
    offset_sec = lag / args.sr

    peak = np.abs(corr).max()
    baseline = np.percentile(np.abs(corr), 99)
    confidence = float(peak / baseline) if baseline > 0 else 0.0

    # B_time = A_time + offset_sec
    print(f"\noffset_sec = {offset_sec:+.4f}   (B_time = A_time + offset)")
    print(f"confidence = {confidence:.2f}   ", end="")
    if confidence >= 5:
        print("-> clean sync (videos are simultaneous)")
    elif confidence >= 2.5:
        print("-> probable sync, eyeball-check a frame pair")
    else:
        print("-> WEAK: videos may not be simultaneous recordings")

    result = {
        "video_a": args.video_a, "video_b": args.video_b,
        "offset_sec": float(offset_sec), "confidence": confidence, "sr": args.sr,
    }
    if args.json:
        with open(args.json, "w") as f:
            json.dump(result, f, indent=2)
        print(f"wrote {args.json}")


if __name__ == "__main__":
    main()
