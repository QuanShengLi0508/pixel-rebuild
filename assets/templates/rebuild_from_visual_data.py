#!/usr/bin/env python3
"""Project-local rebuild script for pixel-level visual data.

Place this file next to:
- no_data_background.png
- visual_data_layer_pixels.csv

Optionally place source.png next to it to print zero-diff metrics.
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops


HERE = Path(__file__).resolve().parent
BACKGROUND = HERE / "no_data_background.png"
VISUAL_DATA = HERE / "visual_data_layer_pixels.csv"
OUT = HERE / "rebuilt_from_visual_data.png"
DIFF_OUT = HERE / "rebuilt_diff.png"
SOURCE = HERE / "source.png"


def main() -> None:
    img = Image.open(BACKGROUND).convert("RGB")
    pixels = np.array(img)

    with VISUAL_DATA.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if int(row["alpha"]) <= 0:
                continue
            x = int(row["pixel_x"])
            y = int(row["pixel_y"])
            pixels[y, x] = [int(row["red"]), int(row["green"]), int(row["blue"])]

    rebuilt = Image.fromarray(pixels)
    rebuilt.save(OUT)
    print(OUT)

    if SOURCE.exists():
        src = Image.open(SOURCE).convert("RGB")
        diff = ImageChops.difference(src, rebuilt)
        diff.save(DIFF_OUT)
        d = np.array(diff)
        print(f"mean_abs_rgb={d.mean():.12g}")
        print(f"max_abs_rgb={int(d.max())}")
        print(f"nonzero_diff_pixels={int((d.max(axis=2) > 0).sum())}")


if __name__ == "__main__":
    main()

