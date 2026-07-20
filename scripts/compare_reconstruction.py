#!/usr/bin/env python3
"""Compare a Python-rendered reconstruction with its raster reference."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image


Box = tuple[int, int, int, int]
RGB = tuple[int, int, int]


def parse_rgb(value: str) -> RGB:
    try:
        parts = tuple(int(part.strip()) for part in value.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected r,g,b") from exc
    if len(parts) != 3 or any(channel < 0 or channel > 255 for channel in parts):
        raise argparse.ArgumentTypeError("expected r,g,b with channels in 0..255")
    return parts


def parse_roi(value: str) -> tuple[str, Box]:
    if ":" not in value:
        raise argparse.ArgumentTypeError("expected name:x0,y0,x1,y1")
    name, coordinates = value.split(":", 1)
    if not name:
        raise argparse.ArgumentTypeError("ROI name cannot be empty")
    try:
        parts = tuple(int(part.strip()) for part in coordinates.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected name:x0,y0,x1,y1") from exc
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("expected name:x0,y0,x1,y1")
    return name, parts


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_image(path: Path) -> tuple[Image.Image, dict[str, Any]]:
    with Image.open(path) as image:
        image.load()
        profile = image.info.get("icc_profile", b"")
        info = {
            "path": str(path.resolve()),
            "format": image.format,
            "size": list(image.size),
            "mode": image.mode,
            "dpi": list(image.info.get("dpi", ())) or None,
            "icc_profile_bytes": len(profile),
            "icc_profile_sha256": hashlib.sha256(profile).hexdigest() if profile else None,
            "sha256": sha256(path),
        }
        return image.convert("RGB"), info


def different_bbox(pixel_error: np.ndarray, offset: tuple[int, int] = (0, 0)) -> list[int] | None:
    ys, xs = np.nonzero(pixel_error > 0)
    if not len(xs):
        return None
    ox, oy = offset
    return [
        int(xs.min() + ox),
        int(ys.min() + oy),
        int(xs.max() + ox + 1),
        int(ys.max() + oy + 1),
    ]


def metrics(reference: np.ndarray, output: np.ndarray, offset: tuple[int, int] = (0, 0)) -> dict[str, Any]:
    signed = reference.astype(np.float64) - output.astype(np.float64)
    delta = np.abs(signed)
    pixel_error = np.max(delta, axis=2)
    return {
        "mae": float(delta.mean()),
        "rmse": float(np.sqrt(np.mean(np.square(signed)))),
        "p95_absolute_channel_error": float(np.percentile(delta, 95)),
        "max_absolute_channel_error": int(delta.max()),
        "exact_pixel_fraction": float(np.mean(pixel_error == 0)),
        "within_5_fraction": float(np.mean(pixel_error <= 5)),
        "within_10_fraction": float(np.mean(pixel_error <= 10)),
        "within_20_fraction": float(np.mean(pixel_error <= 20)),
        "different_pixel_count": int(np.count_nonzero(pixel_error)),
        "different_bbox": different_bbox(pixel_error, offset),
    }


def color_iou(reference: np.ndarray, output: np.ndarray, color: RGB) -> dict[str, Any]:
    target = np.array(color, dtype=np.uint8)
    a = np.all(reference == target, axis=2)
    b = np.all(output == target, axis=2)
    intersection = int(np.count_nonzero(a & b))
    union = int(np.count_nonzero(a | b))
    return {
        "rgb": list(color),
        "reference_pixels": int(a.sum()),
        "output_pixels": int(b.sum()),
        "intersection": intersection,
        "union": union,
        "iou": float(intersection / union) if union else None,
    }


def validate_box(name: str, box: Box, width: int, height: int) -> None:
    x0, y0, x1, y1 = box
    if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
        raise ValueError(f"ROI {name!r}={box} lies outside {width}x{height}")


def save_diagnostics(
    reference_image: Image.Image,
    output_image: Image.Image,
    reference: np.ndarray,
    output: np.ndarray,
    destination: Path,
) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    Image.blend(reference_image, output_image, 0.5).save(destination / "overlay.png")

    delta = np.abs(reference.astype(np.int16) - output.astype(np.int16)).astype(np.uint8)
    magnitude = np.max(delta, axis=2)
    scale = max(float(np.percentile(magnitude, 99)), 1.0)
    normalized = np.clip(magnitude.astype(np.float64) / scale, 0.0, 1.0)
    heat = np.zeros((*normalized.shape, 3), dtype=np.uint8)
    heat[:, :, 0] = np.round(normalized * 255).astype(np.uint8)
    heat[:, :, 1] = np.round(np.clip(1.0 - np.abs(normalized - 0.5) * 2.0, 0.0, 1.0) * 180).astype(np.uint8)
    Image.fromarray(heat).save(destination / "heatmap.png")
    Image.fromarray(np.clip(delta.astype(np.int16) * 4, 0, 255).astype(np.uint8)).save(
        destination / "difference_x4.png"
    )
    Image.fromarray((magnitude > 0).astype(np.uint8) * 255).save(destination / "error_mask.png")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--output-dir", type=Path, help="write overlay and difference diagnostics")
    parser.add_argument("--json", type=Path, help="write the metric report as JSON")
    parser.add_argument("--roi", type=parse_roi, action="append", default=[])
    parser.add_argument("--color", type=parse_rgb, action="append", default=[], help="exact flat color IoU")
    parser.add_argument("--strict-metadata", action="store_true", help="exit nonzero on mode or DPI mismatch")
    args = parser.parse_args()

    reference_image, reference_info = load_image(args.reference)
    output_image, output_info = load_image(args.output)
    if reference_image.size != output_image.size:
        parser.error(
            f"size mismatch: reference={reference_image.size}, output={output_image.size}; comparison never resizes"
        )

    width, height = reference_image.size
    reference = np.asarray(reference_image)
    output = np.asarray(output_image)
    roi_reports: dict[str, Any] = {}
    for name, box in args.roi:
        try:
            validate_box(name, box, width, height)
        except ValueError as exc:
            parser.error(str(exc))
        x0, y0, x1, y1 = box
        roi_reports[name] = {
            "box": list(box),
            **metrics(reference[y0:y1, x0:x1], output[y0:y1, x0:x1], (x0, y0)),
        }

    metadata_match = {
        "format": reference_info["format"] == output_info["format"],
        "size": reference_info["size"] == output_info["size"],
        "mode": reference_info["mode"] == output_info["mode"],
        "dpi": reference_info["dpi"] == output_info["dpi"],
        "icc_profile": reference_info["icc_profile_sha256"] == output_info["icc_profile_sha256"],
    }
    report = {
        "reference": reference_info,
        "output": output_info,
        "metadata_match": metadata_match,
        "global": metrics(reference, output),
        "regions": roi_reports,
        "flat_color_iou": [color_iou(reference, output, color) for color in args.color],
    }

    if args.output_dir:
        save_diagnostics(reference_image, output_image, reference, output, args.output_dir)
        report["diagnostics"] = str(args.output_dir.resolve())

    rendered = json.dumps(report, indent=2, ensure_ascii=False)
    print(rendered)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(rendered + "\n", encoding="utf-8")

    if args.strict_metadata and not all(metadata_match.values()):
        sys.exit(2)


if __name__ == "__main__":
    main()
