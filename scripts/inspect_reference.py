#!/usr/bin/env python3
"""Measure a raster reference before recreating it as Python drawing code."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image


Box = tuple[int, int, int, int]
RGB = tuple[int, int, int]


def parse_box(value: str) -> Box:
    try:
        parts = tuple(int(part.strip()) for part in value.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected x0,y0,x1,y1") from exc
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("expected x0,y0,x1,y1")
    return parts


def parse_rgb(value: str) -> RGB:
    try:
        parts = tuple(int(part.strip()) for part in value.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected r,g,b") from exc
    if len(parts) != 3 or any(channel < 0 or channel > 255 for channel in parts):
        raise argparse.ArgumentTypeError("expected r,g,b with channels in 0..255")
    return parts


def bbox_from_mask(mask: np.ndarray, offset: tuple[int, int]) -> list[int] | None:
    ys, xs = np.nonzero(mask)
    if not len(xs):
        return None
    ox, oy = offset
    return [
        int(xs.min() + ox),
        int(ys.min() + oy),
        int(xs.max() + ox + 1),
        int(ys.max() + oy + 1),
    ]


def contiguous_runs(mask: np.ndarray, minimum: int, offset: int) -> list[list[int]]:
    padded = np.pad(mask.astype(np.int8), (1, 1))
    changes = np.diff(padded)
    starts = np.flatnonzero(changes == 1)
    ends = np.flatnonzero(changes == -1) - 1
    return [
        [int(start + offset), int(end + offset)]
        for start, end in zip(starts, ends)
        if end - start + 1 >= minimum
    ]


def top_coverage(mask: np.ndarray, axis: int, limit: int, offset: int) -> list[dict[str, Any]]:
    counts = mask.sum(axis=axis)
    denominator = mask.shape[axis]
    order = np.argsort(counts)[::-1][: max(limit, 0)]
    return [
        {
            "position": int(position + offset),
            "dark_pixels": int(counts[position]),
            "coverage": float(counts[position] / denominator),
        }
        for position in order
        if counts[position] > 0
    ]


def scan_line(
    data: np.ndarray,
    axis: str,
    global_position: int,
    origin: tuple[int, int],
    threshold: int,
    minimum_run: int,
) -> dict[str, Any]:
    ox, oy = origin
    if axis == "x":
        local = global_position - ox
        if not 0 <= local < data.shape[1]:
            raise ValueError(f"x={global_position} is outside the analyzed area")
        values = data[:, local, :3]
        run_offset = oy
    else:
        local = global_position - oy
        if not 0 <= local < data.shape[0]:
            raise ValueError(f"y={global_position} is outside the analyzed area")
        values = data[local, :, :3]
        run_offset = ox
    dark = np.min(values, axis=1) < threshold
    return {
        "axis": axis,
        "position": global_position,
        "threshold": threshold,
        "dark_runs_inclusive": contiguous_runs(dark, minimum_run, run_offset),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("--crop", type=parse_box, help="global x0,y0,x1,y1 analysis area")
    parser.add_argument("--top-colors", type=int, default=16)
    parser.add_argument("--top-lines", type=int, default=10, help="strongest dark rows and columns")
    parser.add_argument("--color", type=parse_rgb, action="append", default=[], help="additional exact RGB bbox")
    parser.add_argument("--scan-x", type=int, action="append", default=[], help="global x coordinate")
    parser.add_argument("--scan-y", type=int, action="append", default=[], help="global y coordinate")
    parser.add_argument("--dark-threshold", type=int, default=180)
    parser.add_argument("--white-threshold", type=int, default=250)
    parser.add_argument("--minimum-run", type=int, default=2)
    parser.add_argument("--json", type=Path, help="write the report to this path")
    args = parser.parse_args()

    with Image.open(args.image) as source:
        source.load()
        profile = source.info.get("icc_profile", b"")
        metadata = {
            "path": str(args.image.resolve()),
            "format": source.format,
            "size": [source.width, source.height],
            "mode": source.mode,
            "dpi": list(source.info.get("dpi", ())) or None,
            "icc_profile_bytes": len(profile),
            "icc_profile_sha256": hashlib.sha256(profile).hexdigest() if profile else None,
        }
        rgb = source.convert("RGB")

    origin = (0, 0)
    area: Box = (0, 0, rgb.width, rgb.height)
    if args.crop:
        x0, y0, x1, y1 = args.crop
        if not (0 <= x0 < x1 <= rgb.width and 0 <= y0 < y1 <= rgb.height):
            parser.error("crop lies outside the image")
        area = args.crop
        origin = (x0, y0)
        rgb = rgb.crop(area)

    data = np.asarray(rgb)
    pixels = data.reshape(-1, 3)
    colors, counts = np.unique(pixels, axis=0, return_counts=True)
    order = np.argsort(counts)[::-1][: max(args.top_colors, 0)]
    top_colors: list[dict[str, Any]] = []
    for index in order:
        color = tuple(int(channel) for channel in colors[index])
        mask = np.all(data == color, axis=2)
        top_colors.append(
            {
                "rgb": list(color),
                "count": int(counts[index]),
                "fraction": float(counts[index] / len(pixels)),
                "bbox": bbox_from_mask(mask, origin),
            }
        )

    requested_colors = []
    for color in args.color:
        mask = np.all(data == color, axis=2)
        requested_colors.append(
            {
                "rgb": list(color),
                "count": int(mask.sum()),
                "fraction": float(mask.mean()),
                "bbox": bbox_from_mask(mask, origin),
            }
        )

    dark = np.min(data, axis=2) < args.dark_threshold
    nonwhite = np.min(data, axis=2) < args.white_threshold
    scans = [
        scan_line(data, "x", position, origin, args.dark_threshold, args.minimum_run)
        for position in args.scan_x
    ] + [
        scan_line(data, "y", position, origin, args.dark_threshold, args.minimum_run)
        for position in args.scan_y
    ]

    report = {
        "metadata": metadata,
        "analysis_area": list(area),
        "content_bbox": bbox_from_mask(nonwhite, origin),
        "top_colors": top_colors,
        "requested_colors": requested_colors,
        "strongest_dark_rows": top_coverage(dark, axis=1, limit=args.top_lines, offset=origin[1]),
        "strongest_dark_columns": top_coverage(dark, axis=0, limit=args.top_lines, offset=origin[0]),
        "scans": scans,
    }
    rendered = json.dumps(report, indent=2, ensure_ascii=False)
    print(rendered)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
