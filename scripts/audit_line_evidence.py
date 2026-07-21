#!/usr/bin/env python3
"""Measure source-pixel evidence for candidate annotation or leader paths."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence, TypedDict

import numpy as np
from PIL import Image, ImageDraw


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path)
    parser.add_argument("paths", type=Path, help="JSON list of polylines or an object with a paths key")
    parser.add_argument("--json", type=Path, dest="json_output", help="write support report")
    parser.add_argument("--visualization", type=Path, help="write a color-coded path overlay")
    parser.add_argument("--threshold", type=int, default=210, help="maximum grayscale intensity")
    parser.add_argument("--gray-tolerance", type=int, default=0, help="maximum RGB channel spread")
    parser.add_argument("--radius", type=int, default=2, help="evidence dilation radius in pixels")
    parser.add_argument("--width", type=float, default=1.15, help="candidate path width in native pixels")
    parser.add_argument("--scale", type=int, default=4, help="candidate path supersampling scale")
    parser.add_argument("--support-threshold", type=float, default=0.4)
    return parser.parse_args()


class CandidatePath(TypedDict):
    name: str
    points: list[tuple[float, float]]


def load_paths(path: Path) -> list[CandidatePath]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload["paths"] if isinstance(payload, dict) else payload
    paths: list[CandidatePath] = []
    for index, row in enumerate(rows):
        name = f"path-{index:02d}"
        if isinstance(row, dict):
            name = str(row.get("name", name))
            row = row.get("points")
        if not isinstance(row, list) or len(row) < 2:
            raise ValueError(f"Path {index} must contain at least two points")
        points: list[tuple[float, float]] = []
        for point in row:
            if not isinstance(point, list) or len(point) != 2:
                raise ValueError(f"Invalid point in path {index}: {point!r}")
            points.append((float(point[0]), float(point[1])))
        paths.append({"name": name, "points": points})
    return paths


def dilate(mask: np.ndarray, radius: int) -> np.ndarray:
    if radius < 0:
        raise ValueError("Dilation radius cannot be negative")
    result = np.zeros_like(mask, dtype=bool)
    height, width = mask.shape
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            target_y0, target_y1 = max(0, -dy), min(height, height - dy)
            target_x0, target_x1 = max(0, -dx), min(width, width - dx)
            result[target_y0:target_y1, target_x0:target_x1] |= mask[
                target_y0 + dy : target_y1 + dy,
                target_x0 + dx : target_x1 + dx,
            ]
    return result


def rasterize_path(
    size: tuple[int, int],
    points: Sequence[tuple[float, float]],
    *,
    width: float,
    scale: int,
) -> np.ndarray:
    canvas = Image.new("L", (size[0] * scale, size[1] * scale), 0)
    draw = ImageDraw.Draw(canvas)
    scaled = [(round(x * scale), round(y * scale)) for x, y in points]
    draw.line(scaled, fill=255, width=max(1, round(width * scale)), joint="curve")
    native = canvas.resize(size, Image.Resampling.LANCZOS)
    return np.asarray(native) >= 35


def visualise(
    reference: Image.Image,
    paths: Sequence[CandidatePath],
    reports: Sequence[dict[str, object]],
    output: Path,
    support_threshold: float,
) -> None:
    faded = Image.blend(reference.convert("RGB"), Image.new("RGB", reference.size, "white"), 0.72)
    draw = ImageDraw.Draw(faded)
    for path, report in zip(paths, reports):
        support = float(report["dilated_support"])
        color = (0, 150, 65) if support >= support_threshold else (225, 35, 35)
        draw.line(path["points"], fill=color, width=2, joint="curve")
    output.parent.mkdir(parents=True, exist_ok=True)
    faded.save(output)


def main() -> None:
    args = parse_args()
    reference = Image.open(args.reference).convert("RGB")
    array = np.asarray(reference)
    channel_spread = array.max(axis=2).astype(np.int16) - array.min(axis=2).astype(np.int16)
    gray = (channel_spread <= args.gray_tolerance) & (array.max(axis=2) <= args.threshold)
    expanded = dilate(gray, args.radius)
    paths = load_paths(args.paths)

    reports: list[dict[str, object]] = []
    for index, path in enumerate(paths):
        candidate = rasterize_path(reference.size, path["points"], width=args.width, scale=args.scale)
        count = int(candidate.sum())
        raw_count = int(np.logical_and(candidate, gray).sum())
        supported_count = int(np.logical_and(candidate, expanded).sum())
        raw = float(raw_count / count) if count else 0.0
        supported = float(supported_count / count) if count else 0.0
        reports.append(
            {
                "index": index,
                "name": path["name"],
                "points": path["points"],
                "candidate_pixels": count,
                "raw_supported_pixels": raw_count,
                "dilated_supported_pixels": supported_count,
                "raw_support": raw,
                "dilated_support": supported,
                "classification": "supported" if supported >= args.support_threshold else "review",
            }
        )

    payload = {
        "reference": str(args.reference),
        "threshold": args.threshold,
        "gray_tolerance": args.gray_tolerance,
        "dilation_radius": args.radius,
        "line_width": args.width,
        "support_threshold": args.support_threshold,
        "paths": reports,
    }
    encoded = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")

    if args.visualization:
        visualise(reference, paths, reports, args.visualization, args.support_threshold)


if __name__ == "__main__":
    main()
