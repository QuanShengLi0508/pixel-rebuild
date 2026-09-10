#!/usr/bin/env python3
"""Audit geometry contracts for editable vector schematics.

The audit is intentionally independent of PowerPoint, SVG, or a raster
reference.  A renderer records the geometric facts that must remain stable in
``scene_manifest.json`` and this script catches the small changes that create
cheap-looking artifacts: open shared edges, inconsistent face thickness,
unbalanced dash lengths, blunt arrowheads, unexpected outlines, and reordered
layers.

The manifest is a contract, not a second renderer.  It contains measurements
that can be inspected in code review and can be regenerated from a scene
authoring file when the geometry changes.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Iterable


Point = tuple[float, float]


def point(value: Any, label: str) -> Point:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError(f"{label} must be [x, y]")
    x, y = float(value[0]), float(value[1])
    if not (math.isfinite(x) and math.isfinite(y)):
        raise ValueError(f"{label} contains a non-finite coordinate")
    return x, y


def distance(a: Point, b: Point) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def angle_degrees(tip: Point, left: Point, right: Point) -> float:
    """Return the interior angle at an arrow tip."""

    u = (left[0] - tip[0], left[1] - tip[1])
    v = (right[0] - tip[0], right[1] - tip[1])
    norm = math.hypot(*u) * math.hypot(*v)
    if norm == 0:
        raise ValueError("arrowhead has a zero-length side")
    cosine = max(-1.0, min(1.0, (u[0] * v[0] + u[1] * v[1]) / norm))
    return math.degrees(math.acos(cosine))


def coefficient_of_variation(values: Iterable[float]) -> float | None:
    numbers = [float(value) for value in values]
    if not numbers:
        return None
    mean = sum(numbers) / len(numbers)
    if mean == 0:
        return 0.0 if all(value == 0 for value in numbers) else math.inf
    variance = sum((value - mean) ** 2 for value in numbers) / len(numbers)
    return math.sqrt(variance) / abs(mean)


def check_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def add(name: str, passed: bool, details: dict[str, Any]) -> None:
        checks.append({"name": name, "passed": bool(passed), **details})

    canvas = manifest.get("canvas", {})
    width, height = canvas.get("width"), canvas.get("height")
    canvas_ok = (
        isinstance(width, int)
        and isinstance(height, int)
        and width > 0
        and height > 0
    )
    add("canvas", canvas_ok, {"width": width, "height": height})

    for polygon in manifest.get("polygons", []):
        name = polygon.get("name", "unnamed-polygon")
        raw_points = polygon.get("points", [])
        points = [point(value, f"{name}.points[{index}]") for index, value in enumerate(raw_points)]
        # Shoelace area catches duplicate or collinear vertices that often
        # become visible as a hairline after export/downsampling.
        area = abs(
            sum(
                points[index][0] * points[(index + 1) % len(points)][1]
                - points[(index + 1) % len(points)][0] * points[index][1]
                for index in range(len(points))
            )
            / 2
        ) if len(points) >= 3 else 0.0
        stroke = polygon.get("stroke")
        add(
            f"polygon:{name}",
            len(points) >= 3 and area > 1e-6,
            {"vertices": len(points), "area": area, "stroke": stroke},
        )

    for seam in manifest.get("shared_edges", []):
        name = seam.get("name", "unnamed-seam")
        left = seam.get("left", {})
        right = seam.get("right", {})
        tolerance = float(seam.get("tolerance", 0.5))
        left_a, left_b = point(left.get("a"), f"{name}.left.a"), point(left.get("b"), f"{name}.left.b")
        right_a, right_b = point(right.get("a"), f"{name}.right.a"), point(right.get("b"), f"{name}.right.b")
        endpoint_errors = [distance(left_a, right_a), distance(left_b, right_b)]
        add(
            f"shared-edge:{name}",
            max(endpoint_errors) <= tolerance,
            {"endpoint_errors": endpoint_errors, "tolerance": tolerance},
        )

    for group in manifest.get("thickness_groups", []):
        name = group.get("name", "unnamed-thickness-group")
        values = [float(value) for value in group.get("values", [])]
        tolerance = float(group.get("tolerance", 0.5))
        spread = max(values) - min(values) if values else math.inf
        add(
            f"thickness:{name}",
            bool(values) and spread <= tolerance,
            {"values": values, "spread": spread, "tolerance": tolerance},
        )

    for group in manifest.get("dash_groups", []):
        name = group.get("name", "unnamed-dash-group")
        lengths = [float(value) for value in group.get("lengths", [])]
        spacing = [float(value) for value in group.get("spacing", [])]
        max_cv = float(group.get("max_cv", 0.12))
        length_cv = coefficient_of_variation(lengths)
        spacing_cv = coefficient_of_variation(spacing)
        passed = bool(lengths) and (length_cv or 0.0) <= max_cv and (
            not spacing or (spacing_cv or 0.0) <= max_cv
        )
        add(
            f"dashes:{name}",
            passed,
            {
                "length_cv": length_cv,
                "spacing_cv": spacing_cv,
                "max_cv": max_cv,
                "lengths": lengths,
                "spacing": spacing,
            },
        )

    for arrow in manifest.get("arrowheads", []):
        name = arrow.get("name", "unnamed-arrow")
        tip = point(arrow.get("tip"), f"{name}.tip")
        left = point(arrow.get("left"), f"{name}.left")
        right = point(arrow.get("right"), f"{name}.right")
        angle = angle_degrees(tip, left, right)
        minimum = float(arrow.get("min_angle_deg", 25.0))
        maximum = float(arrow.get("max_angle_deg", 110.0))
        add(
            f"arrowhead:{name}",
            minimum <= angle <= maximum,
            {"angle_deg": angle, "min_angle_deg": minimum, "max_angle_deg": maximum},
        )

    palette = manifest.get("palette_contract", {})
    for name, values in palette.get("groups", {}).items():
        fills = [str(value).upper().lstrip("#") for value in values]
        expected = fills[0] if fills else None
        add(
            f"palette:{name}",
            bool(fills) and all(value == expected for value in fills),
            {"fills": fills, "expected": expected},
        )
    forbidden = {str(value).upper().lstrip("#") for value in palette.get("forbidden_structural_strokes", [])}
    if forbidden:
        seen = [
            str(polygon.get("stroke")).upper().lstrip("#")
            for polygon in manifest.get("polygons", [])
            if polygon.get("stroke") is not None
        ]
        add(
            "palette:structural-outlines",
            not any(value in forbidden for value in seen),
            {"forbidden": sorted(forbidden), "seen": seen},
        )

    order = manifest.get("layer_order", {})
    expected_order = list(order.get("expected", []))
    actual_order = list(order.get("actual", []))
    add(
        "layer-order",
        actual_order == expected_order,
        {"expected": expected_order, "actual": actual_order},
    )

    failed = [check["name"] for check in checks if not check["passed"]]
    return {"passed": not failed, "failed": failed, "checks": checks}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--json", type=Path, help="write the audit report")
    args = parser.parse_args()

    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        report = check_manifest(manifest)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    rendered = json.dumps(report, indent=2, ensure_ascii=False)
    print(rendered)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(rendered + "\n", encoding="utf-8")
    if not report["passed"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
