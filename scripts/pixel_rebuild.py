#!/usr/bin/env python3
"""Export, rebuild, and verify pixel-level visual data layers.

The visual data CSV format is:
pixel_x,pixel_y,red,green,blue,alpha
"""

from __future__ import annotations

import argparse
import csv
import json
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageFilter


def load_rgb(path: Path) -> Image.Image:
    return Image.open(path).convert("RGB")


def load_mask(path: Path) -> np.ndarray:
    mask = Image.open(path).convert("L")
    return np.array(mask) > 0


def parse_rect(value: str) -> tuple[int, int, int, int]:
    parts = [int(v.strip()) for v in value.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("rect must be x1,y1,x2,y2")
    x1, y1, x2, y2 = parts
    if x2 < x1 or y2 < y1:
        raise argparse.ArgumentTypeError("rect requires x2>=x1 and y2>=y1")
    return x1, y1, x2, y2


def parse_channel_range(value: str) -> tuple[int, int]:
    if "-" not in value:
        raise argparse.ArgumentTypeError("channel range must be min-max")
    lo, hi = [int(v.strip()) for v in value.split("-", 1)]
    if not (0 <= lo <= hi <= 255):
        raise argparse.ArgumentTypeError("channel range must satisfy 0<=min<=max<=255")
    return lo, hi


def parse_rule(value: str) -> tuple[str, tuple[int, int], tuple[int, int], tuple[int, int]]:
    if ":" in value:
        name, ranges = value.split(":", 1)
    else:
        name, ranges = "rule", value
    parts = [p.strip() for p in ranges.split(",")]
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("rule must be name:rmin-rmax,gmin-gmax,bmin-bmax")
    return name, parse_channel_range(parts[0]), parse_channel_range(parts[1]), parse_channel_range(parts[2])


def morph_mask(mask: np.ndarray, dilate: int = 0, erode: int = 0) -> np.ndarray:
    img = Image.fromarray(mask.astype(np.uint8) * 255, mode="L")
    for _ in range(max(0, dilate)):
        img = img.filter(ImageFilter.MaxFilter(3))
    for _ in range(max(0, erode)):
        img = img.filter(ImageFilter.MinFilter(3))
    return np.array(img) > 0


def color_mask(
    source: Path,
    rules: list[tuple[str, tuple[int, int], tuple[int, int], tuple[int, int]]],
    include_rects: list[tuple[int, int, int, int]],
    exclude_rects: list[tuple[int, int, int, int]],
    out: Path,
    dilate: int = 0,
    erode: int = 0,
) -> int:
    img = load_rgb(source)
    arr = np.array(img)
    if not rules:
        raise ValueError("At least one --rule is required")

    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    mask = np.zeros(arr.shape[:2], dtype=bool)
    for _, rr, gr, br in rules:
        mask |= (
            (r >= rr[0])
            & (r <= rr[1])
            & (g >= gr[0])
            & (g <= gr[1])
            & (b >= br[0])
            & (b <= br[1])
        )

    if include_rects:
        include = np.zeros_like(mask)
        for x1, y1, x2, y2 in include_rects:
            include[y1 : y2 + 1, x1 : x2 + 1] = True
        mask &= include

    for x1, y1, x2, y2 in exclude_rects:
        mask[y1 : y2 + 1, x1 : x2 + 1] = False

    mask = morph_mask(mask, dilate=dilate, erode=erode)
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(mask.astype(np.uint8) * 255, mode="L").save(out)
    return int(mask.sum())


def inpaint_background(source: Path, mask_path: Path, out: Path, radius: float = 3.0, method: str = "telea") -> None:
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError("OpenCV is required for inpaint. Install opencv-python.") from exc

    src = np.array(load_rgb(source))
    mask = (load_mask(mask_path).astype(np.uint8)) * 255
    flag = cv2.INPAINT_TELEA if method == "telea" else cv2.INPAINT_NS
    bgr = cv2.cvtColor(src, cv2.COLOR_RGB2BGR)
    inpainted = cv2.inpaint(bgr, mask, radius, flag)
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(cv2.cvtColor(inpainted, cv2.COLOR_BGR2RGB)).save(out)


def export_visual_data(source: Path, mask_path: Path, csv_out: Path, layer_out: Path | None = None) -> int:
    src = load_rgb(source)
    rgb = np.array(src)
    mask = load_mask(mask_path)
    if mask.shape != rgb.shape[:2]:
        raise ValueError(f"Mask size {mask.shape[::-1]} does not match source size {src.size}")

    yy, xx = np.nonzero(mask)
    vals = rgb[yy, xx]
    csv_out.parent.mkdir(parents=True, exist_ok=True)
    with csv_out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["pixel_x", "pixel_y", "red", "green", "blue", "alpha"])
        for x, y, (r, g, b) in zip(xx, yy, vals):
            writer.writerow([int(x), int(y), int(r), int(g), int(b), 255])

    if layer_out is not None:
        layer = np.zeros((rgb.shape[0], rgb.shape[1], 4), dtype=np.uint8)
        layer[yy, xx, :3] = vals
        layer[yy, xx, 3] = 255
        layer_out.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(layer, mode="RGBA").save(layer_out)

    return int(len(xx))


def rebuild(background: Path, csv_path: Path, out: Path) -> int:
    img = load_rgb(background)
    pixels = np.array(img)
    count = 0
    with csv_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"pixel_x", "pixel_y", "red", "green", "blue", "alpha"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing CSV columns: {sorted(missing)}")
        for row in reader:
            if int(row["alpha"]) <= 0:
                continue
            x = int(row["pixel_x"])
            y = int(row["pixel_y"])
            pixels[y, x] = [int(row["red"]), int(row["green"]), int(row["blue"])]
            count += 1

    out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(pixels).save(out)
    return count


def verify(source: Path, candidate: Path, diff_out: Path | None = None, metrics_out: Path | None = None) -> dict[str, object]:
    src = load_rgb(source)
    cand = load_rgb(candidate)
    if src.size != cand.size:
        raise ValueError(f"Size mismatch: source={src.size}, candidate={cand.size}")

    diff = ImageChops.difference(src, cand)
    if diff_out is not None:
        diff_out.parent.mkdir(parents=True, exist_ok=True)
        diff.save(diff_out)

    a = np.array(src).astype(np.float64)
    b = np.array(cand).astype(np.float64)
    d = np.abs(a - b)
    metrics = {
        "image_size": list(src.size),
        "mean_abs_rgb": float(d.mean()),
        "mse_rgb": float(((a - b) ** 2).mean()),
        "max_abs_rgb": float(d.max()),
        "nonzero_diff_pixels": int((d.max(axis=2) > 0).sum()),
        "pixel_arrays_equal": bool(np.array_equal(np.array(src), np.array(cand))),
    }
    if metrics_out is not None:
        metrics_out.parent.mkdir(parents=True, exist_ok=True)
        metrics_out.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


def package_files(out: Path, files: list[Path], root_name: str | None = None) -> int:
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for path in files:
            if not path.exists():
                raise FileNotFoundError(path)
            arcname = path.name if root_name is None else f"{root_name}/{path.name}"
            z.write(path, arcname=arcname)
    return len(files)


def cmd_color_mask(args: argparse.Namespace) -> None:
    count = color_mask(args.source, args.rule, args.include_rect, args.exclude_rect, args.out, args.dilate, args.erode)
    print(args.out)
    print(f"mask_pixels={count}")


def cmd_inpaint(args: argparse.Namespace) -> None:
    inpaint_background(args.source, args.mask, args.out, args.radius, args.method)
    print(args.out)


def cmd_export(args: argparse.Namespace) -> None:
    count = export_visual_data(args.source, args.mask, args.csv, args.layer)
    print(f"visual_data_pixel_records={count}")


def cmd_rebuild(args: argparse.Namespace) -> None:
    count = rebuild(args.background, args.csv, args.out)
    print(args.out)
    print(f"visual_data_pixel_records={count}")


def cmd_verify(args: argparse.Namespace) -> None:
    metrics = verify(args.source, args.candidate, args.diff, args.metrics)
    print(json.dumps(metrics, indent=2))


def cmd_all(args: argparse.Namespace) -> None:
    exported = export_visual_data(args.source, args.mask, args.csv, args.layer)
    rebuilt = rebuild(args.background, args.csv, args.rebuilt)
    metrics = verify(args.source, args.rebuilt, args.diff, args.metrics)
    metrics["visual_data_pixel_records_exported"] = exported
    metrics["visual_data_pixel_records_rebuilt"] = rebuilt
    if args.metrics is not None:
        args.metrics.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))


def cmd_package(args: argparse.Namespace) -> None:
    count = package_files(args.out, args.file, args.root_name)
    print(args.out)
    print(f"packaged_files={count}")


def path_arg(value: str) -> Path:
    return Path(value).expanduser().resolve()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("color-mask", help="make a binary mask from RGB threshold rules")
    p.add_argument("--source", type=path_arg, required=True)
    p.add_argument("--out", type=path_arg, required=True)
    p.add_argument(
        "--rule",
        type=parse_rule,
        action="append",
        required=True,
        help="name:rmin-rmax,gmin-gmax,bmin-bmax, e.g. red:170-255,0-120,0-120",
    )
    p.add_argument("--include-rect", type=parse_rect, action="append", default=[], help="x1,y1,x2,y2")
    p.add_argument("--exclude-rect", type=parse_rect, action="append", default=[], help="x1,y1,x2,y2")
    p.add_argument("--dilate", type=int, default=0)
    p.add_argument("--erode", type=int, default=0)
    p.set_defaults(func=cmd_color_mask)

    p = sub.add_parser("inpaint", help="create a no-data background from source plus mask")
    p.add_argument("--source", type=path_arg, required=True)
    p.add_argument("--mask", type=path_arg, required=True)
    p.add_argument("--out", type=path_arg, required=True)
    p.add_argument("--radius", type=float, default=3.0)
    p.add_argument("--method", choices=["telea", "ns"], default="telea")
    p.set_defaults(func=cmd_inpaint)

    p = sub.add_parser("export", help="export source pixels selected by a mask to visual data CSV")
    p.add_argument("--source", type=path_arg, required=True)
    p.add_argument("--mask", type=path_arg, required=True)
    p.add_argument("--csv", type=path_arg, required=True)
    p.add_argument("--layer", type=path_arg)
    p.set_defaults(func=cmd_export)

    p = sub.add_parser("rebuild", help="rebuild an image from background plus visual data CSV")
    p.add_argument("--background", type=path_arg, required=True)
    p.add_argument("--csv", type=path_arg, required=True)
    p.add_argument("--out", type=path_arg, required=True)
    p.set_defaults(func=cmd_rebuild)

    p = sub.add_parser("verify", help="compute pixel-level RGB error metrics")
    p.add_argument("--source", type=path_arg, required=True)
    p.add_argument("--candidate", type=path_arg, required=True)
    p.add_argument("--diff", type=path_arg)
    p.add_argument("--metrics", type=path_arg)
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("all", help="export, rebuild, and verify in one command")
    p.add_argument("--source", type=path_arg, required=True)
    p.add_argument("--mask", type=path_arg, required=True)
    p.add_argument("--background", type=path_arg, required=True)
    p.add_argument("--csv", type=path_arg, required=True)
    p.add_argument("--layer", type=path_arg)
    p.add_argument("--rebuilt", type=path_arg, required=True)
    p.add_argument("--diff", type=path_arg)
    p.add_argument("--metrics", type=path_arg)
    p.set_defaults(func=cmd_all)

    p = sub.add_parser("package", help="zip selected output files")
    p.add_argument("--out", type=path_arg, required=True)
    p.add_argument("--file", type=path_arg, action="append", required=True)
    p.add_argument("--root-name")
    p.set_defaults(func=cmd_package)

    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
