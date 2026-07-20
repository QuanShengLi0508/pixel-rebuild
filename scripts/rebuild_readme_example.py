"""Recreate the supplied broken-log detector comparison figure with Pillow.

The reference image is used only as a visual specification.  This module
constructs every region, axis, marker, label, and legend entry from vector
primitives and writes a deterministic 1485 x 1062 PNG.
"""

from __future__ import annotations

import argparse
import math
import os
from pathlib import Path
from typing import Sequence

from PIL import Image, ImageDraw, ImageFont


WIDTH = 1485
HEIGHT = 1062
SCALE = 4

WHITE = (255, 255, 255, 255)
BLACK = (0, 0, 0, 255)
BLUE = (0, 0, 255, 255)
BLUE_LINE = (115, 115, 255, 255)
BLUE_LEGEND_LINE = (128, 128, 255, 255)
GREEN = (0, 255, 0, 255)
GREEN_LINE = (115, 255, 115, 255)
GREEN_LEGEND_LINE = (128, 255, 128, 255)
RED = (255, 0, 0, 255)
PINK = (252, 194, 194, 255)
SALMON = (250, 112, 112, 255)
DARK_RED = (135, 3, 3, 255)
GRAY = (115, 115, 115, 255)


def find_font(*names: str) -> str:
    roots = (
        "/System/Library/Fonts/Supplemental",
        "/System/Library/Fonts",
        "/Library/Fonts",
        "/usr/share/fonts/truetype/msttcorefonts",
        "/usr/share/fonts/truetype/dejavu",
    )
    for root in roots:
        for name in names:
            candidate = os.path.join(root, name)
            if os.path.exists(candidate):
                return candidate
    raise RuntimeError(f"None of these fonts is installed: {', '.join(names)}")


ARIAL = find_font("Arial.ttf", "Helvetica.ttc", "DejaVuSans.ttf")
TIMES = find_font("Times New Roman.ttf", "Times.ttc", "DejaVuSerif.ttf")


def sc(value: float) -> int:
    return int(round(value * SCALE))


def point(value: Sequence[float]) -> tuple[int, int]:
    return sc(value[0]), sc(value[1])


def get_font(size: float, family: str = "arial") -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(ARIAL if family == "arial" else TIMES, sc(size))


def catmull_rom(points: Sequence[tuple[float, float]], samples: int = 14) -> list[tuple[int, int]]:
    """Return a smooth closed outline through a short set of control points."""
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
            result.append((sc(x), sc(y)))
    return result


def region_mask(points: Sequence[tuple[float, float]]) -> Image.Image:
    mask = Image.new("L", (WIDTH * SCALE, HEIGHT * SCALE), 0)
    ImageDraw.Draw(mask).polygon(catmull_rom(points), fill=255)
    return mask


def draw_regions(image: Image.Image) -> None:
    gray_points = (
        (386, 390), (500, 385), (650, 391), (780, 405), (860, 420),
        (883, 434), (884, 452), (850, 484), (785, 526), (704, 557),
        (653, 581), (620, 606), (602, 636), (586, 682), (576, 727),
        (573, 770), (573, 848), (562, 865), (538, 865), (492, 850),
        (444, 831), (390, 804), (343, 771), (302, 731), (268, 687),
        (246, 641), (238, 596), (240, 547), (254, 501), (279, 462),
        (315, 428), (354, 401),
    )
    blue_points = (
        (960, 86), (1052, 93), (1135, 116), (1180, 148), (1205, 181),
        (1206, 213), (1194, 246), (1156, 284), (1090, 320), (1020, 349),
        (937, 370), (851, 379), (780, 374), (720, 362), (663, 345),
        (646, 330), (620, 315), (607, 300), (595, 281), (595, 255),
        (609, 240), (620, 207), (655, 174),
        (715, 143), (772, 117), (851, 97),
    )
    green_points = (
        (611, 233), (625, 241), (635, 273), (634, 326), (634, 390),
        (648, 450), (658, 520), (658, 550),
        (671, 583), (706, 610), (744, 624), (800, 632), (832, 647),
        (852, 663), (857, 681), (850, 700), (840, 704), (790, 706),
        (748, 702), (718, 695), (683, 682), (637, 663),
        (613, 638), (598, 605), (589, 566), (585, 503), (585, 425),
        (585, 348), (586, 291), (597, 253), (609, 238),
    )

    gray_mask = region_mask(gray_points)
    blue_mask = region_mask(blue_points)
    green_mask = region_mask(green_points)

    image.paste((230, 230, 230, 255), mask=gray_mask)
    image.paste((230, 230, 254, 255), mask=blue_mask)

    green_target = Image.new("RGBA", image.size, (231, 255, 231, 255))
    green_target.paste((207, 231, 207, 255), mask=gray_mask)
    green_target.paste((207, 232, 229, 255), mask=blue_mask)
    image.paste(green_target, mask=green_mask)


def line(
    draw: ImageDraw.ImageDraw,
    coordinates: Sequence[tuple[float, float]],
    fill: tuple[int, int, int, int],
    width: float,
    rounded: bool = False,
) -> None:
    pts = [point(p) for p in coordinates]
    draw.line(pts, fill=fill, width=sc(width), joint="curve")
    if rounded:
        radius = width / 2
        for x, y in (coordinates[0], coordinates[-1]):
            draw.ellipse(
                (sc(x - radius), sc(y - radius), sc(x + radius), sc(y + radius)),
                fill=fill,
            )


def text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    value: str,
    size: float,
    fill: tuple[int, int, int, int] = BLACK,
    *,
    family: str = "arial",
    anchor: str | None = None,
) -> None:
    draw.text(point(xy), value, font=get_font(size, family), fill=fill, anchor=anchor)


def formula(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    chunks: Sequence[tuple[str, bool]],
    size: float,
    fill: tuple[int, int, int, int],
) -> None:
    """Draw ordinary and subscript chunks from a shared top coordinate."""
    x, y = xy
    normal = get_font(size)
    sub = get_font(size * 0.70)
    for value, is_subscript in chunks:
        active = sub if is_subscript else normal
        offset = size * 0.37 if is_subscript else 0
        draw.text((sc(x), sc(y + offset)), value, font=active, fill=fill)
        x += draw.textlength(value, font=active) / SCALE


def polygon_marker(
    draw: ImageDraw.ImageDraw,
    points: Sequence[tuple[float, float]],
    color: tuple[int, int, int, int],
    *,
    fill: tuple[int, int, int, int] | None = None,
    width: float = 3.5,
) -> None:
    pts = [point(p) for p in points]
    draw.polygon(pts, fill=fill if fill is not None else color)
    if fill is not None:
        draw.line([*pts, pts[0]], fill=color, width=sc(width), joint="curve")


def square(
    draw: ImageDraw.ImageDraw,
    cx: float,
    cy: float,
    color: tuple[int, int, int, int],
    *,
    size: float = 17,
    hollow: bool = False,
    half: str | None = None,
) -> None:
    r = size / 2
    box = (sc(cx - r), sc(cy - r), sc(cx + r), sc(cy + r))
    if not hollow and half is None:
        draw.rectangle(box, fill=color)
        return
    draw.rectangle(box, fill=WHITE)
    if half == "top":
        draw.rectangle((box[0], box[1], box[2], sc(cy)), fill=color)
    elif half == "right":
        draw.rectangle((sc(cx), box[1], box[2], box[3]), fill=color)
    elif half == "left":
        draw.rectangle((box[0], box[1], sc(cx), box[3]), fill=color)
    elif half == "bottom":
        draw.rectangle((box[0], sc(cy), box[2], box[3]), fill=color)
    draw.rectangle(box, outline=color, width=sc(4.5 if hollow else 3))


def circle(
    draw: ImageDraw.ImageDraw,
    cx: float,
    cy: float,
    color: tuple[int, int, int, int],
    *,
    radius: float = 9.5,
    hollow: bool = False,
    half: str | None = None,
    target: bool = False,
    outline_width: float = 3,
) -> None:
    box = (sc(cx - radius), sc(cy - radius), sc(cx + radius), sc(cy + radius))
    if target:
        draw.ellipse(box, fill=color)
        inner = radius * 0.56
        draw.ellipse((sc(cx - inner), sc(cy - inner), sc(cx + inner), sc(cy + inner)), fill=WHITE)
        dot = radius * 0.24
        draw.ellipse((sc(cx - dot), sc(cy - dot), sc(cx + dot), sc(cy + dot)), fill=color)
        return
    if not hollow and half is None:
        draw.ellipse(box, fill=color)
        return
    draw.ellipse(box, fill=WHITE)
    if half == "top":
        draw.pieslice(box, 180, 360, fill=color)
    elif half == "bottom":
        draw.pieslice(box, 0, 180, fill=color)
    elif half == "left":
        draw.pieslice(box, 90, 270, fill=color)
    elif half == "right":
        draw.pieslice(box, 270, 90, fill=color)
    draw.ellipse(box, outline=color, width=sc(outline_width))


def triangle(
    draw: ImageDraw.ImageDraw,
    cx: float,
    cy: float,
    color: tuple[int, int, int, int],
    *,
    direction: str = "up",
    hollow: bool = False,
    half: str | None = None,
) -> None:
    if direction == "up":
        if hollow or half is not None:
            pts = ((cx, cy - 9.5), (cx + 10, cy + 8), (cx - 10, cy + 8))
        else:
            pts = ((cx, cy - 10.5), (cx + 11, cy + 9.5), (cx - 11, cy + 9.5))
    elif direction == "right":
        pts = ((cx + 11.5, cy), (cx - 10, cy - 12), (cx - 10, cy + 12))
    else:
        pts = ((cx - 11.5, cy), (cx + 10, cy - 12), (cx + 10, cy + 12))
    if not hollow and half is None:
        polygon_marker(draw, pts, color)
        return

    polygon_marker(draw, pts, color, fill=WHITE)
    if half is not None:
        marker_mask = Image.new("L", (WIDTH * SCALE, HEIGHT * SCALE), 0)
        md = ImageDraw.Draw(marker_mask)
        md.polygon([point(p) for p in pts], fill=255)
        clip = Image.new("L", marker_mask.size, 0)
        cd = ImageDraw.Draw(clip)
        if half == "top":
            cd.rectangle((0, 0, WIDTH * SCALE, sc(cy)), fill=255)
        elif half == "right":
            cd.rectangle((sc(cx), 0, WIDTH * SCALE, HEIGHT * SCALE), fill=255)
        elif half == "left":
            cd.rectangle((0, 0, sc(cx), HEIGHT * SCALE), fill=255)
        else:
            cd.rectangle((0, sc(cy), WIDTH * SCALE, HEIGHT * SCALE), fill=255)
        # Restrict the color patch to the marker and then reinforce its outline.
        from PIL import ImageChops

        fill_mask = ImageChops.multiply(marker_mask, clip)
        draw._image.paste(color, mask=fill_mask)
        # Reinforce the outline after clipping the colored half.
        outline = [point(p) for p in pts]
        draw.line([*outline, outline[0]], fill=color, width=sc(3.5), joint="curve")


def diamond(
    draw: ImageDraw.ImageDraw,
    cx: float,
    cy: float,
    color: tuple[int, int, int, int],
    *,
    hollow: bool = False,
) -> None:
    radius = 10.5 if hollow else 12.5
    pts = ((cx, cy - radius), (cx + radius, cy), (cx, cy + radius), (cx - radius, cy))
    polygon_marker(draw, pts, color, fill=WHITE if hollow else None, width=3.5)


def pentagon(draw: ImageDraw.ImageDraw, cx: float, cy: float, color: tuple[int, int, int, int]) -> None:
    pts = []
    for index in range(5):
        angle = math.radians(-90 + index * 72)
        pts.append((cx + 11.5 * math.cos(angle), cy + 11.5 * math.sin(angle)))
    polygon_marker(draw, pts, color)


def draw_plot_content(image: Image.Image) -> None:
    draw = ImageDraw.Draw(image)

    # Red-family devices.
    triangle(draw, 259, 270, SALMON, direction="left")
    formula(
        draw,
        (196, 208),
        (("(MoS", False), ("2", True), (" on) G-hBN-G", False)),
        27.5,
        SALMON,
    )
    triangle(draw, 585, 236, DARK_RED, direction="right")
    text(draw, (553, 194), "G-Si", 27.5, DARK_RED)

    line(draw, ((456, 321), (611, 321)), (255, 230, 230, 255), 11, rounded=True)
    square(draw, 456, 321, RED, size=17)
    square(draw, 611, 321, RED, size=17)
    text(draw, (438, 270), "@~1.31μm", 27.5, RED)
    formula(draw, (445, 331), (("MoTe", False), ("2", True), ("-G", False)), 27.5, RED)

    line(draw, ((487, 510), (517, 510)), (245, 206, 206, 255), 11, rounded=True)
    square(draw, 487, 510, PINK, size=17)
    square(draw, 517, 510, PINK, size=17)
    formula(draw, (424, 525), (("MoTe", False), ("2", True), ("-G", False)), 27.5, PINK)
    text(draw, (410, 554), "@~1.31 μm", 27.5, PINK)

    # Black/gray devices.
    line(draw, ((414, 403), (591, 403)), GRAY, 11, rounded=True)
    square(draw, 414, 403, BLACK, size=17)
    square(draw, 591, 403, BLACK, size=17)
    line(draw, ((678, 510), (755, 469), (861, 452)), GRAY, 9)
    square(draw, 678, 510, BLACK, size=16, hollow=True)
    square(draw, 755, 469, BLACK, size=16, hollow=True)
    square(draw, 861, 452, BLACK, size=16, hollow=True)
    diamond(draw, 264, 582, BLACK)
    text(draw, (350, 660), "Metal-BP-Metal", 27.5, BLACK)
    pentagon(draw, 549, 835, BLACK)
    text(draw, (597, 823), "@3.825 μm", 27.5, BLACK)

    # Green devices.
    diamond(draw, 611, 257, GREEN, hollow=True)
    square(draw, 631, 565, GREEN, size=17)
    text(draw, (656, 550), "@1.16 μm", 27.5, GREEN)
    line(draw, ((706, 669), (824, 669)), GREEN_LINE, 11, rounded=True)
    diamond(draw, 706, 669, GREEN)
    diamond(draw, 824, 669, GREEN)
    text(draw, (864, 662), "Metal-TMDC-Metal", 27.5, GREEN)

    # Blue devices, including overlapped studies in the dense upper cluster.
    line(draw, ((665, 186), (797, 186)), BLUE_LINE, 10, rounded=True)
    triangle(draw, 665, 186, BLUE, hollow=True)
    square(draw, 776, 186, BLUE, size=17, half="right")
    square(draw, 786, 186, BLUE, size=17)
    triangle(draw, 797, 186, BLUE, hollow=True)

    circle(draw, 808, 220, BLUE, half="bottom")
    circle(draw, 824, 220, BLUE)
    circle(draw, 840, 220, BLUE, target=True)

    line(draw, ((678, 247), (766, 247)), BLUE_LINE, 10, rounded=True)
    triangle(draw, 678, 247, BLUE, hollow=True)
    circle(draw, 755, 247, BLUE)
    triangle(draw, 766, 247, BLUE, half="top")

    line(draw, ((850, 247), (881, 247)), BLUE_LINE, 10, rounded=True)
    circle(draw, 850, 247, BLUE, half="right")
    circle(draw, 881, 247, BLUE, half="right")
    square(draw, 922, 247, BLUE, size=17)

    square(draw, 835, 264, BLUE, size=17, half="top")
    circle(draw, 775, 297, BLUE, half="top")
    circle(draw, 790, 297, BLUE, half="top")

    line(draw, ((835, 288), (870, 288)), BLUE_LINE, 10, rounded=True)
    triangle(draw, 835, 288, BLUE, half="right")
    triangle(draw, 870, 288, BLUE, half="right")
    text(draw, (886, 272), "@2 μm", 27.5, BLUE)

    line(draw, ((643, 320), (696, 320)), BLUE_LINE, 10, rounded=True)
    circle(draw, 643, 320, BLUE, half="left")
    circle(draw, 696, 320, BLUE, half="left")

    triangle(draw, 1193, 208, BLUE)
    text(draw, (790, 132), "Metal-Graphene-Metal", 27.5, BLUE)


def x_position(exponent: float) -> float:
    return 179 + (exponent + 13) * (1066 / 6)


def upper_y(exponent: float) -> float:
    return 56 + (12 - exponent) * (687 / 5)


def lower_y(exponent: float) -> float:
    return 798 + (3 - exponent) * 138


def power_label(
    draw: ImageDraw.ImageDraw,
    x: float,
    y: float,
    exponent: str,
    *,
    align: str,
    horizontal_axis: bool = False,
) -> None:
    base_font = get_font(33)
    exp_font = get_font(22.5)
    if horizontal_axis:
        x += 0.5
        y -= 0.5
    else:
        x += 0.5
        y -= 1.5
    base_width = draw.textlength("10", font=base_font) / SCALE
    exp_width = draw.textlength(exponent, font=exp_font) / SCALE
    total = base_width + exp_width
    if align == "center":
        left = x - total / 2
    else:
        left = x - total
    if horizontal_axis:
        base_top = y
        exp_top = y - 4
    else:
        base_top = y - 14
        exp_top = y - 19
    draw.text((sc(left), sc(base_top)), "10", font=base_font, fill=BLACK)
    draw.text((sc(left + base_width), sc(exp_top)), exponent, font=exp_font, fill=BLACK)


def rotated_text(
    image: Image.Image,
    center: tuple[float, float],
    value: str,
    size: float,
    fill: tuple[int, int, int, int],
) -> None:
    active = get_font(size)
    bbox = active.getbbox(value)
    layer = Image.new("RGBA", (bbox[2] - bbox[0] + sc(6), bbox[3] - bbox[1] + sc(6)), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.text((sc(3) - bbox[0], sc(3) - bbox[1]), value, font=active, fill=fill)
    layer = layer.rotate(90, expand=True)
    x = sc(center[0]) - layer.width // 2
    y = sc(center[1]) - layer.height // 2
    image.alpha_composite(layer, (x, y))


def draw_axes(image: Image.Image) -> None:
    draw = ImageDraw.Draw(image)
    axis_width = 3

    # Upper and lower broken-y plot frame.
    line(draw, ((179, 56.5), (1245, 56.5)), BLACK, axis_width)
    line(draw, ((179.5, 56), (179.5, 744)), BLACK, axis_width)
    line(draw, ((1244.5, 56), (1244.5, 744)), BLACK, axis_width)
    line(draw, ((179.5, 757), (179.5, 937)), BLACK, axis_width)
    line(draw, ((1244.5, 757), (1244.5, 937)), BLACK, axis_width)
    line(draw, ((179, 936.5), (1245, 936.5)), BLACK, axis_width)

    # Logarithmic x ticks, directed into the frame at top and bottom.
    for decade in range(-13, -7):
        base_x = x_position(decade)
        for multiplier in range(2, 10):
            x = base_x + (1066 / 6) * math.log10(multiplier)
            line(draw, ((x, 56), (x, 65)), BLACK, 3)
            line(draw, ((x, 937), (x, 928)), BLACK, 3)
    for exponent in range(-13, -6):
        x = x_position(exponent)
        line(draw, ((x, 56), (x, 72)), BLACK, 3)
        line(draw, ((x, 937), (x, 921)), BLACK, 3)
        power_label(draw, x, 956, str(exponent), align="center", horizontal_axis=True)

    # Logarithmic y ticks on both sides of each panel.
    for decade in range(7, 12):
        for multiplier in range(2, 10):
            exponent = decade + math.log10(multiplier)
            y = upper_y(exponent)
            line(draw, ((179, y), (187, y)), BLACK, 3)
            line(draw, ((1245, y), (1237, y)), BLACK, 3)
    for exponent in range(7, 13):
        y = upper_y(exponent)
        line(draw, ((179, y), (195, y)), BLACK, 3)
        line(draw, ((1245, y), (1229, y)), BLACK, 3)
        power_label(draw, 162, y, str(exponent), align="right")

    for multiplier in range(2, 10):
        exponent = 2 + math.log10(multiplier)
        y = lower_y(exponent)
        line(draw, ((179, y), (187, y)), BLACK, 3)
        line(draw, ((1245, y), (1237, y)), BLACK, 3)
    for exponent in (3, 2):
        y = lower_y(exponent)
        line(draw, ((179, y), (195, y)), BLACK, 3)
        line(draw, ((1245, y), (1229, y)), BLACK, 3)
        power_label(draw, 162, y, str(exponent), align="right")

    # Broken-axis slashes overlap the two spine segments and the 10^7 tick.
    line(draw, ((174, 751), (185, 736)), BLACK, 3)
    line(draw, ((174, 766), (185, 751)), BLACK, 3)
    line(draw, ((1240, 751), (1250, 736)), BLACK, 3)
    line(draw, ((1240, 766), (1250, 751)), BLACK, 3)

    rotated_text(image, (72.5, 497), "Bandwidth (Hz)", 41, BLACK)

    # X label with a raised exponent.
    normal = get_font(41)
    superscript = get_font(27)
    prefix = "NEP(W Hz"
    suffix = ")"
    w1 = draw.textlength(prefix, font=normal) / SCALE
    w2 = draw.textlength("-1/2", font=superscript) / SCALE
    w3 = draw.textlength(suffix, font=normal) / SCALE
    left = 712 - (w1 + w2 + w3) / 2
    draw.text((sc(left), sc(1012)), prefix, font=normal, fill=BLACK)
    draw.text((sc(left + w1), sc(1008)), "-1/2", font=superscript, fill=BLACK)
    draw.text((sc(left + w1 + w2), sc(1012)), suffix, font=normal, fill=BLACK)


def draw_legend(image: Image.Image) -> None:
    draw = ImageDraw.Draw(image)
    draw.rectangle((sc(1260), sc(60), sc(1397), sc(919)), fill=WHITE, outline=BLACK, width=sc(1))

    entries = (
        (79, "[110]", "square", BLUE, None, None),
        (114, "[111]", "square", BLUE, "top", None),
        (148, "[108]", "square", BLUE, "right", None),
        (182, "[60]", "circle", BLUE, None, BLUE),
        (217, "[112]", "circle_hollow", BLUE, None, BLUE_LEGEND_LINE),
        (251, "[113]", "circle", BLUE, "top", BLUE_LEGEND_LINE),
        (285, "[114]", "circle", BLUE, "right", BLUE_LEGEND_LINE),
        (319, "[116]", "circle", BLUE, "bottom", None),
        (353, "[117]", "target", BLUE, None, None),
        (388, "[118]", "triangle", BLUE, None, None),
        (422, "[119]", "triangle_hollow", BLUE, None, BLUE_LEGEND_LINE),
        (456, "[58]", "triangle", BLUE, "top", BLUE_LEGEND_LINE),
        (490, "[58]", "triangle", BLUE, "right", BLUE_LEGEND_LINE),
        (524, "[115]", "circle", BLUE, "left", BLUE_LEGEND_LINE),
        (558, "[64]", "square", GREEN, None, None),
        (593, "[70]", "diamond", GREEN, None, GREEN_LEGEND_LINE),
        (627, "[121]", "diamond_hollow", GREEN, None, None),
        (661, "[71]", "square", BLACK, None, (128, 128, 128, 255)),
        (695, "[161]", "diamond", BLACK, None, None),
        (730, "[69]", "pentagon", BLACK, None, None),
        (764, "[72]", "square_hollow", BLACK, None, (128, 128, 128, 255)),
        (798, "[89]", "square", PINK, None, (254, 215, 215, 255)),
        (832, "[90]", "square", RED, None, (255, 230, 230, 255)),
        (866, "[122]", "right_triangle", DARK_RED, None, None),
        (900, "[123]", "left_triangle", SALMON, None, None),
    )

    legend_font = get_font(27.5, "times")
    for cy, label, kind, color, half, line_color in entries:
        if line_color is not None:
            line(draw, ((1265, cy), (1327, cy)), line_color, 10, rounded=True)
        if kind == "square":
            square(draw, 1296, cy, color, size=17, half=half)
        elif kind == "square_hollow":
            square(draw, 1296, cy - 1, color, size=17, hollow=True)
        elif kind == "circle":
            circle(draw, 1296, cy, color, half=half, outline_width=2.5 if half else 3)
        elif kind == "circle_hollow":
            circle(draw, 1296, cy - 1, color, radius=9, hollow=True, outline_width=4)
        elif kind == "target":
            circle(draw, 1296, cy, color, target=True)
        elif kind == "triangle":
            triangle(draw, 1295.5, cy - 3, color, half=half)
        elif kind == "triangle_hollow":
            triangle(draw, 1295.5, cy - 3, color, hollow=True)
        elif kind == "right_triangle":
            triangle(draw, 1299, cy, color, direction="right")
        elif kind == "left_triangle":
            triangle(draw, 1293, cy, color, direction="left")
        elif kind == "diamond":
            diamond(draw, 1296, cy, color)
        elif kind == "diamond_hollow":
            diamond(draw, 1296.5, cy - 1, color, hollow=True)
        elif kind == "pentagon":
            pentagon(draw, 1296, cy, color)

        label_width = draw.textlength(label, font=legend_font)
        draw.text((sc(1393.5) - label_width, sc(cy - 16)), label, font=legend_font, fill=BLACK)


def build_image() -> Image.Image:
    image = Image.new("RGBA", (WIDTH * SCALE, HEIGHT * SCALE), WHITE)
    draw_regions(image)
    draw_plot_content(image)
    draw_axes(image)
    draw_legend(image)

    result = image.convert("RGB").resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)

    # Exact native-resolution antialias ramp of the rule above the chart.
    final_draw = ImageDraw.Draw(result)
    for y, gray in ((11, 202), (12, 15), (13, 0), (14, 11)):
        final_draw.line((0, y, WIDTH - 1, y), fill=(gray, gray, gray))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--output", default="replicated_figure.png", help="PNG output path")
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    build_image().save(output, format="PNG", dpi=(239.9792, 239.9792))
    print(f"wrote {output} ({WIDTH}x{HEIGHT})")


if __name__ == "__main__":
    main()
