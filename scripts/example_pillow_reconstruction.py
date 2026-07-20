#!/usr/bin/env python3
"""Complete Pillow example for a deterministic, supersampled figure rebuild.

This script does not read a reference image. It demonstrates reusable patterns for
fixed-layout scientific figures: measured pixel geometry, log transforms, a broken
axis, smooth flat regions, exact overlap colors, compound markers, scientific text,
a structured legend, one native-resolution post-pass, and preserved PNG DPI.
"""

from __future__ import annotations

import argparse
import math
import os
from pathlib import Path
from typing import Sequence

from PIL import Image, ImageChops, ImageDraw, ImageFont


WIDTH = 1100
HEIGHT = 760
SCALE = 4
DPI = (240, 240)

WHITE = (255, 255, 255, 255)
BLACK = (0, 0, 0, 255)
GRAY_FILL = (230, 230, 230, 255)
GRAY = (105, 105, 105, 255)
BLUE_FILL = (230, 230, 254, 255)
BLUE = (0, 0, 255, 255)
BLUE_LINE = (126, 126, 255, 255)
GREEN_FILL = (231, 255, 231, 255)
GREEN_OVER_GRAY = (207, 231, 207, 255)
GREEN = (0, 235, 25, 255)
GREEN_LINE = (116, 245, 126, 255)
RED = (245, 45, 45, 255)
RED_LINE = (255, 180, 180, 255)

PLOT_LEFT = 105
PLOT_RIGHT = 785
UPPER_TOP = 55
UPPER_BOTTOM = 545
LOWER_TOP = 575
LOWER_BOTTOM = 675


def find_font(*names: str) -> str:
    roots = (
        "/System/Library/Fonts/Supplemental",
        "/System/Library/Fonts",
        "/Library/Fonts",
        "/usr/share/fonts/truetype/dejavu",
        "/usr/share/fonts/truetype/liberation2",
        "C:/Windows/Fonts",
    )
    for root in roots:
        for name in names:
            candidate = os.path.join(root, name)
            if os.path.exists(candidate):
                return candidate
    for name in names:
        try:
            ImageFont.truetype(name, 12)
            return name
        except OSError:
            pass
    raise RuntimeError(f"None of these fonts is installed: {', '.join(names)}")


SANS = find_font("Arial.ttf", "Helvetica.ttc", "DejaVuSans.ttf", "LiberationSans-Regular.ttf")
SERIF = find_font("Times New Roman.ttf", "Times.ttc", "DejaVuSerif.ttf", "LiberationSerif-Regular.ttf")


def sc(value: float) -> int:
    """Convert one native-pixel coordinate to the supersampled canvas."""
    return int(round(value * SCALE))


def pt(x: float, y: float) -> tuple[int, int]:
    return sc(x), sc(y)


def font(size: float, family: str = "sans") -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(SANS if family == "sans" else SERIF, sc(size))


def line(
    draw: ImageDraw.ImageDraw,
    points: Sequence[tuple[float, float]],
    fill: tuple[int, int, int, int],
    width: float,
    *,
    rounded: bool = False,
) -> None:
    scaled = [pt(x, y) for x, y in points]
    draw.line(scaled, fill=fill, width=sc(width), joint="curve")
    if rounded:
        radius = width / 2
        for x, y in (points[0], points[-1]):
            draw.ellipse((sc(x - radius), sc(y - radius), sc(x + radius), sc(y + radius)), fill=fill)


def log_map(value: float, low: float, high: float, pixel_low: float, pixel_high: float) -> float:
    ratio = (math.log10(value) - math.log10(low)) / (math.log10(high) - math.log10(low))
    return pixel_low + ratio * (pixel_high - pixel_low)


def x_map(value: float) -> float:
    return log_map(value, 1e-13, 1e-7, PLOT_LEFT, PLOT_RIGHT)


def y_upper(value: float) -> float:
    return log_map(value, 1e7, 1e12, UPPER_BOTTOM, UPPER_TOP)


def y_lower(value: float) -> float:
    return log_map(value, 1e2, 1e3, LOWER_BOTTOM, LOWER_TOP)


def smooth_closed(points: Sequence[tuple[float, float]], samples: int = 16) -> list[tuple[int, int]]:
    """Sample a closed Catmull-Rom curve through measured silhouette points."""
    result: list[tuple[int, int]] = []
    count = len(points)
    for index in range(count):
        p0 = points[(index - 1) % count]
        p1 = points[index]
        p2 = points[(index + 1) % count]
        p3 = points[(index + 2) % count]
        for step in range(samples):
            t = step / samples
            t2 = t * t
            t3 = t2 * t
            x = 0.5 * (
                2 * p1[0]
                + (-p0[0] + p2[0]) * t
                + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3
            )
            y = 0.5 * (
                2 * p1[1]
                + (-p0[1] + p2[1]) * t
                + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3
            )
            result.append(pt(x, y))
    return result


def region_mask(points: Sequence[tuple[float, float]]) -> Image.Image:
    mask = Image.new("L", (WIDTH * SCALE, HEIGHT * SCALE), 0)
    ImageDraw.Draw(mask).polygon(smooth_closed(points), fill=255)
    return mask


def draw_regions(image: Image.Image) -> None:
    gray_points = (
        (185, 315), (270, 285), (410, 290), (560, 320), (610, 370),
        (570, 435), (500, 475), (430, 510), (400, 620), (335, 635),
        (255, 590), (195, 520), (165, 440), (165, 365),
    )
    blue_points = (
        (380, 145), (500, 100), (635, 90), (735, 125), (765, 190),
        (735, 260), (650, 315), (540, 330), (445, 305), (385, 250),
    )
    green_points = (
        (370, 210), (390, 250), (400, 330), (410, 420), (455, 485),
        (535, 520), (545, 565), (500, 590), (430, 570), (375, 520),
        (350, 440), (350, 320),
    )
    gray_mask = region_mask(gray_points)
    blue_mask = region_mask(blue_points)
    green_mask = region_mask(green_points)

    image.paste(GRAY_FILL, mask=gray_mask)
    image.paste(BLUE_FILL, mask=blue_mask)

    green_layer = Image.new("RGBA", image.size, GREEN_FILL)
    green_gray_overlap = ImageChops.multiply(green_mask, gray_mask)
    green_layer.paste(GREEN_OVER_GRAY, mask=green_gray_overlap)
    image.paste(green_layer, mask=green_mask)


def draw_text(
    draw: ImageDraw.ImageDraw,
    x: float,
    y: float,
    value: str,
    size: float,
    fill: tuple[int, int, int, int] = BLACK,
    *,
    family: str = "sans",
    anchor: str | None = None,
) -> None:
    draw.text(pt(x, y), value, font=font(size, family), fill=fill, anchor=anchor)


def power_label(
    draw: ImageDraw.ImageDraw,
    x: float,
    y: float,
    exponent: int,
    *,
    anchor: str,
    size: float = 21,
) -> None:
    base_font = font(size)
    exponent_font = font(size * 0.66)
    base = "10"
    exp = str(exponent)
    base_width = draw.textlength(base, font=base_font) / SCALE
    exp_width = draw.textlength(exp, font=exponent_font) / SCALE
    total = base_width + exp_width
    if anchor == "center":
        start = x - total / 2
    elif anchor == "right":
        start = x - total
    else:
        start = x
    draw.text(pt(start, y), base, font=base_font, fill=BLACK, anchor="lm")
    draw.text(pt(start + base_width, y - size * 0.35), exp, font=exponent_font, fill=BLACK, anchor="lm")


def composed_x_title(draw: ImageDraw.ImageDraw) -> None:
    base_font = font(29)
    exponent_font = font(19)
    left = "NEP (W Hz"
    exponent = "-1/2"
    right = ")"
    widths = [
        draw.textlength(left, font=base_font) / SCALE,
        draw.textlength(exponent, font=exponent_font) / SCALE,
        draw.textlength(right, font=base_font) / SCALE,
    ]
    x = (PLOT_LEFT + PLOT_RIGHT - sum(widths)) / 2
    y = 730
    draw.text(pt(x, y), left, font=base_font, fill=BLACK, anchor="lm")
    x += widths[0]
    draw.text(pt(x, y - 10), exponent, font=exponent_font, fill=BLACK, anchor="lm")
    x += widths[1]
    draw.text(pt(x, y), right, font=base_font, fill=BLACK, anchor="lm")


def rotated_y_title(image: Image.Image) -> None:
    active_font = font(29)
    label = "Bandwidth (Hz)"
    bbox = active_font.getbbox(label)
    pad = sc(8)
    tile = Image.new("RGBA", (bbox[2] - bbox[0] + 2 * pad, bbox[3] - bbox[1] + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(tile).text((pad - bbox[0], pad - bbox[1]), label, font=active_font, fill=BLACK)
    tile = tile.rotate(90, expand=True, resample=Image.Resampling.BICUBIC)
    image.alpha_composite(tile, (sc(27) - tile.width // 2, sc(365) - tile.height // 2))


def draw_axes(image: Image.Image) -> None:
    draw = ImageDraw.Draw(image)
    width = 2.5
    line(draw, [(PLOT_LEFT, UPPER_TOP), (PLOT_RIGHT, UPPER_TOP)], BLACK, width)
    line(draw, [(PLOT_LEFT, UPPER_TOP), (PLOT_LEFT, UPPER_BOTTOM)], BLACK, width)
    line(draw, [(PLOT_RIGHT, UPPER_TOP), (PLOT_RIGHT, UPPER_BOTTOM)], BLACK, width)
    line(draw, [(PLOT_LEFT, LOWER_TOP), (PLOT_LEFT, LOWER_BOTTOM)], BLACK, width)
    line(draw, [(PLOT_RIGHT, LOWER_TOP), (PLOT_RIGHT, LOWER_BOTTOM)], BLACK, width)
    line(draw, [(PLOT_LEFT, LOWER_BOTTOM), (PLOT_RIGHT, LOWER_BOTTOM)], BLACK, width)

    for exponent in range(-13, -6):
        decade = 10.0**exponent
        x = x_map(decade)
        line(draw, [(x, LOWER_BOTTOM), (x, LOWER_BOTTOM - 10)], BLACK, 2)
        line(draw, [(x, UPPER_TOP), (x, UPPER_TOP + 8)], BLACK, 2)
        power_label(draw, x, 699, exponent, anchor="center")
        if exponent < -7:
            for multiplier in range(2, 10):
                minor_x = x_map(decade * multiplier)
                line(draw, [(minor_x, LOWER_BOTTOM), (minor_x, LOWER_BOTTOM - 6)], BLACK, 1.5)
                line(draw, [(minor_x, UPPER_TOP), (minor_x, UPPER_TOP + 5)], BLACK, 1.5)

    for exponent in range(7, 13):
        value = 10.0**exponent
        y = y_upper(value)
        line(draw, [(PLOT_LEFT, y), (PLOT_LEFT + 10, y)], BLACK, 2)
        line(draw, [(PLOT_RIGHT, y), (PLOT_RIGHT - 10, y)], BLACK, 2)
        power_label(draw, PLOT_LEFT - 14, y, exponent, anchor="right")
        if exponent < 12:
            for multiplier in range(2, 10):
                minor_y = y_upper(value * multiplier)
                line(draw, [(PLOT_LEFT, minor_y), (PLOT_LEFT + 6, minor_y)], BLACK, 1.5)
                line(draw, [(PLOT_RIGHT, minor_y), (PLOT_RIGHT - 6, minor_y)], BLACK, 1.5)

    for exponent in (2, 3):
        y = y_lower(10.0**exponent)
        line(draw, [(PLOT_LEFT, y), (PLOT_LEFT + 10, y)], BLACK, 2)
        line(draw, [(PLOT_RIGHT, y), (PLOT_RIGHT - 10, y)], BLACK, 2)
        power_label(draw, PLOT_LEFT - 14, y, exponent, anchor="right")

    for x in (PLOT_LEFT, PLOT_RIGHT):
        line(draw, [(x - 5, UPPER_BOTTOM + 6), (x + 5, UPPER_BOTTOM - 6)], BLACK, 2)
        line(draw, [(x - 5, LOWER_TOP + 6), (x + 5, LOWER_TOP - 6)], BLACK, 2)

    composed_x_title(draw)
    rotated_y_title(image)


def square_marker(
    draw: ImageDraw.ImageDraw,
    x: float,
    y: float,
    color: tuple[int, int, int, int],
    *,
    size: float = 13,
    hollow: bool = False,
) -> None:
    radius = size / 2
    box = (sc(x - radius), sc(y - radius), sc(x + radius), sc(y + radius))
    if hollow:
        draw.rectangle(box, fill=WHITE, outline=color, width=sc(2.5))
    else:
        draw.rectangle(box, fill=color)


def diamond_marker(draw: ImageDraw.ImageDraw, x: float, y: float, color: tuple[int, int, int, int]) -> None:
    radius = 9
    draw.polygon([pt(x, y - radius), pt(x + radius, y), pt(x, y + radius), pt(x - radius, y)], fill=color)


def triangle_marker(
    draw: ImageDraw.ImageDraw,
    x: float,
    y: float,
    color: tuple[int, int, int, int],
    *,
    hollow: bool = False,
) -> None:
    points = [pt(x, y - 9), pt(x + 9, y + 8), pt(x - 9, y + 8)]
    draw.polygon(points, fill=WHITE if hollow else color)
    if hollow:
        draw.line([*points, points[0]], fill=color, width=sc(2.5), joint="curve")


def half_circle_marker(
    image: Image.Image,
    x: float,
    y: float,
    color: tuple[int, int, int, int],
    *,
    radius: float = 7,
    half: str = "left",
) -> None:
    marker = Image.new("L", image.size, 0)
    marker_draw = ImageDraw.Draw(marker)
    box = (sc(x - radius), sc(y - radius), sc(x + radius), sc(y + radius))
    marker_draw.ellipse(box, fill=255)
    clip = Image.new("L", image.size, 0)
    clip_draw = ImageDraw.Draw(clip)
    if half == "left":
        clip_draw.rectangle((sc(x - radius), sc(y - radius), sc(x), sc(y + radius)), fill=255)
    else:
        clip_draw.rectangle((sc(x), sc(y - radius), sc(x + radius), sc(y + radius)), fill=255)
    image.paste(color, mask=ImageChops.multiply(marker, clip))
    draw = ImageDraw.Draw(image)
    draw.ellipse(box, outline=color, width=sc(2.2))
    line(draw, [(x, y - radius), (x, y + radius)], color, 1.5)


def draw_data(image: Image.Image) -> None:
    draw = ImageDraw.Draw(image)

    gray_points = [(2e-12, 3e9), (2e-11, 3e9), (7e-11, 5e8), (2e-10, 1e9), (8e-10, 1.4e9)]
    line(draw, [(x_map(x), y_upper(y)) for x, y in gray_points[2:]], GRAY, 6, rounded=True)
    for index, (x, y) in enumerate(gray_points):
        square_marker(draw, x_map(x), y_upper(y), BLACK if index < 2 else GRAY, hollow=index >= 2)

    blue_points = [(7e-11, 4e10), (2e-10, 4e10), (5e-10, 2e10), (2e-9, 4e10)]
    line(draw, [(x_map(x), y_upper(y)) for x, y in blue_points[:2]], BLUE_LINE, 6, rounded=True)
    for index, (x, y) in enumerate(blue_points):
        if index == 0:
            triangle_marker(draw, x_map(x), y_upper(y), BLUE, hollow=True)
        elif index == 1:
            half_circle_marker(image, x_map(x), y_upper(y), BLUE, half="left")
        else:
            square_marker(draw, x_map(x), y_upper(y), BLUE, hollow=index == 2)

    green_points = [(9e-11, 3.5e7), (4e-10, 3.5e7)]
    line(draw, [(x_map(x), y_upper(y)) for x, y in green_points], GREEN_LINE, 7, rounded=True)
    for x, y in green_points:
        diamond_marker(draw, x_map(x), y_upper(y), GREEN)

    red_points = [(4e-12, 1.2e10), (3e-11, 1.2e10)]
    line(draw, [(x_map(x), y_upper(y)) for x, y in red_points], RED_LINE, 7)
    for x, y in red_points:
        square_marker(draw, x_map(x), y_upper(y), RED)

    diamond_marker(draw, x_map(1.5e-11), y_lower(4e2), BLACK)

    draw_text(draw, 485, 125, "Metal-Graphene-Metal", 23, BLUE, anchor="mm")
    draw_text(draw, 265, 490, "Metal-BP-Metal", 21, BLACK, anchor="mm")
    draw_text(draw, 565, 555, "Metal-TMDC-Metal", 20, GREEN, anchor="lm")
    draw_text(draw, 285, 245, "G-Si", 20, (140, 0, 0, 255), anchor="mm")


def legend_symbol(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    kind: str,
    x: float,
    y: float,
    color: tuple[int, int, int, int],
) -> None:
    if kind == "square":
        square_marker(draw, x, y, color)
    elif kind == "hollow-square":
        square_marker(draw, x, y, color, hollow=True)
    elif kind == "half-circle":
        half_circle_marker(image, x, y, color)
    elif kind == "triangle":
        triangle_marker(draw, x, y - 2, color)
    elif kind == "hollow-triangle":
        triangle_marker(draw, x, y - 2, color, hollow=True)
    elif kind == "diamond":
        diamond_marker(draw, x, y, color)
    elif kind == "line-square":
        line(draw, [(x - 21, y), (x + 21, y)], color, 5, rounded=True)
        square_marker(draw, x, y, color)


def draw_legend(image: Image.Image) -> None:
    draw = ImageDraw.Draw(image)
    frame = (sc(815), sc(60), sc(1068), sc(365))
    draw.rectangle(frame, fill=WHITE, outline=BLACK, width=sc(1))
    entries = [
        ("[110]", "square", BLUE),
        ("[111]", "hollow-square", BLUE),
        ("[112]", "half-circle", BLUE),
        ("[118]", "triangle", BLUE),
        ("[119]", "hollow-triangle", BLUE),
        ("[64]", "square", GREEN),
        ("[70]", "diamond", GREEN),
        ("[71]", "line-square", GRAY),
        ("[90]", "line-square", RED),
    ]
    for index, (label, kind, color) in enumerate(entries):
        y = 82 + index * 31
        legend_symbol(image, draw, kind, 850, y, color)
        draw_text(draw, 892, y, label, 20, BLACK, family="serif", anchor="lm")


def render(output: Path) -> None:
    image = Image.new("RGBA", (WIDTH * SCALE, HEIGHT * SCALE), WHITE)
    draw_regions(image)
    draw_data(image)
    draw_axes(image)
    draw_legend(image)

    result = image.convert("RGB").resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)

    # A narrow native post-pass is appropriate only when a measured rule demands it.
    native = ImageDraw.Draw(result)
    native.line((0, 12, WIDTH - 1, 12), fill=(25, 25, 25), width=2)

    output.parent.mkdir(parents=True, exist_ok=True)
    result.save(output, dpi=DPI)
    print(f"wrote {output} ({WIDTH}x{HEIGHT}, RGB, {DPI[0]} DPI requested)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("example_reconstruction.png"))
    args = parser.parse_args()
    render(args.output)


if __name__ == "__main__":
    main()
