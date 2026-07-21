#!/usr/bin/env python3
"""Deterministically reconstruct Case 2, the solvent-affinity scatter figure.

The renderer is self-contained: it does not read, crop, trace, or composite the
reference image.  All geometry below is expressed in native 1080 x 588 pixels
and rasterized once from a 4x supersampled drawing surface.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
from PIL import Image, ImageDraw, ImageFont


WIDTH, HEIGHT = 1080, 588
SCALE = 4

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
AXIS = (45, 45, 45)
GREEN = (0, 178, 56)
RED = (249, 0, 0)
CARBON = (81, 81, 81)
BLUE = (0, 128, 189)
CYAN = (92, 169, 217)
ORANGE = (255, 162, 53)
ORANGE_DARK = (255, 141, 57)
PURPLE = (163, 73, 168)
BROWN = (133, 75, 77)
LIFSI = (0, 0, 0)
LITFSI = (170, 185, 204)
LIPF6 = (127, 152, 178)

FONT_REGULAR = Path("/System/Library/Fonts/Supplemental/Arial.ttf")
FONT_BOLD = Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf")
FONT_ITALIC = Path("/System/Library/Fonts/Supplemental/Arial Italic.ttf")


def sc(value: float) -> int:
    return round(value * SCALE)


def xy(point: Sequence[float]) -> tuple[int, int]:
    return sc(point[0]), sc(point[1])


def font(path: Path, size: float) -> ImageFont.FreeTypeFont:
    if not path.is_file():
        raise FileNotFoundError(f"Required font is missing: {path}")
    return ImageFont.truetype(str(path), sc(size))


def subpixel_text(
    image: Image.Image,
    position: Sequence[float],
    value: str,
    *,
    font_path: Path = FONT_REGULAR,
    size: float = 14.5,
) -> None:
    """Composite LCD-style RGB text using three horizontal samples per pixel."""
    subpixels = 3
    padding = 4
    used_font = ImageFont.truetype(str(font_path), round(size * subpixels))
    text_width = used_font.getlength(value) / subpixels
    patch_w = max(1, int(np.ceil(text_width)) + padding * 2 + 4)
    patch_h = max(1, int(np.ceil(size * 1.55)) + padding * 2 + 4)

    px = int(np.floor(position[0]))
    py = int(np.floor(position[1]))
    fx = position[0] - px
    fy = position[1] - py
    mask = Image.new("L", (patch_w * subpixels, patch_h * subpixels), 0)
    md = ImageDraw.Draw(mask)
    md.text(
        (round((padding + fx) * subpixels), round((padding + fy) * subpixels)),
        value,
        font=used_font,
        fill=255,
        anchor="lt",
    )

    vertical = np.asarray(
        mask.resize((patch_w * subpixels, patch_h), Image.Resampling.LANCZOS),
        dtype=np.float64,
    )
    # A measured ClearType-like five-tap filter softens pure red/blue fringes.
    kernel = np.array((1, 4, 6, 4, 1), dtype=np.float64) / 16.0
    padded = np.pad(vertical, ((0, 0), (2, 2)), mode="edge")
    filtered = sum(
        weight * padded[:, offset : offset + vertical.shape[1]]
        for offset, weight in enumerate(kernel)
    )
    filtered = 255.0 * np.power(np.clip(filtered / 255.0, 0.0, 1.0), 1.7)
    coverage = np.stack([filtered[:, channel::3] for channel in range(3)], axis=2)

    x0, y0 = px - padding, py - padding
    x1, y1 = x0 + patch_w, y0 + patch_h
    clip_x0, clip_y0 = max(0, x0), max(0, y0)
    clip_x1, clip_y1 = min(image.width, x1), min(image.height, y1)
    if clip_x0 >= clip_x1 or clip_y0 >= clip_y1:
        return
    sx0, sy0 = clip_x0 - x0, clip_y0 - y0
    sx1, sy1 = sx0 + clip_x1 - clip_x0, sy0 + clip_y1 - clip_y0
    base = np.asarray(image.crop((clip_x0, clip_y0, clip_x1, clip_y1)), dtype=np.float64)
    alpha = coverage[sy0:sy1, sx0:sx1] / 255.0
    composed = np.rint(base * (1.0 - alpha)).clip(0, 255).astype(np.uint8)
    image.paste(Image.fromarray(composed, mode="RGB"), (clip_x0, clip_y0))


class Figure:
    def __init__(self) -> None:
        self.image = Image.new("RGB", (WIDTH * SCALE, HEIGHT * SCALE), WHITE)
        self.draw = ImageDraw.Draw(self.image)
        self.label_font = font(FONT_REGULAR, 13.25)
        self.tick_font = font(FONT_REGULAR, 16)
        self.axis_font = font(FONT_REGULAR, 17.5)
        self.small_font = font(FONT_REGULAR, 14)
        self.legend_font = font(FONT_REGULAR, 17)
        self.panel_font = font(FONT_BOLD, 24)

    def line(
        self,
        points: Iterable[Sequence[float]],
        fill: tuple[int, int, int] = AXIS,
        width: float = 1.0,
    ) -> None:
        self.draw.line([xy(p) for p in points], fill=fill, width=max(1, sc(width)), joint="curve")

    def dashed_line(
        self,
        start: Sequence[float],
        end: Sequence[float],
        fill: tuple[int, int, int],
        width: float,
        dash: float = 7,
        gap: float = 7,
    ) -> None:
        x0, y0 = start
        x1, y1 = end
        if abs(y1 - y0) < 0.01:
            x = x0
            while x < x1:
                self.line(((x, y0), (min(x + dash, x1), y0)), fill, width)
                x += dash + gap
        elif abs(x1 - x0) < 0.01:
            y = y0
            while y < y1:
                self.line(((x0, y), (x0, min(y + dash, y1))), fill, width)
                y += dash + gap
        else:
            raise ValueError("Only horizontal and vertical dashed lines are used here")

    def text(
        self,
        position: Sequence[float],
        value: str,
        used_font: ImageFont.FreeTypeFont | None = None,
        anchor: str = "lt",
        fill: tuple[int, int, int] = BLACK,
    ) -> None:
        self.draw.text(xy(position), value, font=used_font or self.label_font, fill=fill, anchor=anchor)

    def marker(
        self,
        center: Sequence[float],
        color: tuple[int, int, int],
        *,
        hollow: bool = False,
        radius: float = 7.45,
    ) -> None:
        cx, cy = center
        box = (sc(cx - radius), sc(cy - radius), sc(cx + radius), sc(cy + radius))
        if hollow:
            self.draw.ellipse(box, fill=WHITE, outline=color, width=sc(4.0))
        else:
            self.draw.ellipse(box, fill=color)

    def square_dash(self, x: float, y: float, color: tuple[int, int, int]) -> None:
        # The legend samples are three compact square-ended strokes.
        for dx in (0, 14, 28):
            self.draw.rectangle(
                (sc(x + dx), sc(y - 3.5), sc(x + dx + 7), sc(y + 3.5)),
                fill=color,
            )


def draw_axes(fig: Figure) -> None:
    left, top, right, bottom = 117.5, 74, 897, 524
    fig.line(((left, top), (left, bottom)), AXIS, 1.0)
    fig.line(((left, bottom), (right, bottom)), AXIS, 1.0)

    for i in range(8):
        x = left + (right - left) * i / 7
        fig.line(((x, bottom), (x, bottom + 9)), AXIS, 1.0)

    for i in range(10):
        y = top + 50 * i
        fig.line(((left - 8, y), (left, y)), AXIS, 1.0)

def draw_thresholds(fig: Figure) -> None:
    fig.dashed_line((125, 245), (884, 245), LIFSI, 0.75, 5, 5)
    fig.dashed_line((125, 255), (741, 255), LITFSI, 0.75, 5, 5)
    fig.dashed_line((125, 275), (844, 275), LIPF6, 0.75, 5, 5)
    fig.dashed_line((884.5, 260), (884.5, 524), (91, 91, 91), 1.0, 5, 5)
    fig.dashed_line((740.5, 268), (740.5, 524), (199, 209, 221), 1.0, 5, 5)
    fig.dashed_line((843.5, 301), (843.5, 524), (142, 164, 187), 1.0, 5, 5)


def draw_leaders(fig: Figure) -> None:
    leaders = [
        ((302, 61), (304, 67)), ((334, 78), (328, 78)),
        ((268, 108), (275, 129)), ((229, 122), (243, 140), (252, 140)),
        ((260, 141), (283, 160)), ((181, 157), (187, 167)),
        ((368, 124), (372, 196), (380, 198)),
        ((228, 191), (239, 212), (244, 212)), ((200, 198), (194, 217)),
        ((483, 65), (480, 78)),
        ((665, 120), (683, 132)), ((710, 121), (699, 133)),
        ((630, 173), (617, 206)),
        ((228, 244), (211, 276)), ((260, 247), (248, 278), (227.5, 278)),
        ((184, 276), (194.5, 297)),
        ((164, 318), (171, 307)),
        ((329, 231), (330.5, 287.5)), ((359, 226), (349, 277)),
        ((396, 226), (368, 280)), ((439, 257), (443, 271)),
        ((530, 257), (547, 264)), ((600, 285), (618, 285), (638, 266), (641, 266)),
        ((291, 263), (310, 290)),
        ((466, 288), (475, 308)),
        ((331, 296), (331, 309)), ((375, 285), (384, 295)),
        ((210, 343), (225, 348), (245, 348)),
        ((269, 321), (263, 321), (251, 370), (246, 370)),
        ((289, 330), (279, 369)), ((296, 338), (307, 365)),
        ((521, 333), (540, 348)),
        ((520, 423), (531.5, 394)), ((589, 385), (599, 376)),
        ((605, 410), (614, 410), (624, 379)),
        ((762, 404), (773, 397), (781, 397)),
    ]
    for points in leaders:
        fig.line(points, AXIS, 1.15)


def marker_groups() -> list[tuple[tuple[int, int, int], list[tuple[float, float, bool]]]]:
    return [
        (GREEN, [
            (188.5, 173.5, True), (200, 187, False), (387.5, 196.5, True),
            (211, 276, True), (227.5, 278, False), (330.5, 287.5, True),
            (194.5, 297, False), (225, 298, True), (172, 300, False),
        ]),
        (RED, [
            (580, 124, False), (630, 173, False), (654.5, 187, False),
            (349, 277, False), (343, 284, False), (358, 279, False), (368, 280, False),
            (310, 290, False), (320, 291, False),
            (452, 279, False), (452, 286, False),
            (282, 322, False), (289, 330, False), (296, 338, False),
            (245, 348, False),
        ]),
        (CARBON, [
            (600, 159, False), (457, 297, False), (676, 316, False),
            (360, 346, False), (511, 376, False), (600.5, 379.5, False),
        ]),
        (BLUE, [
            (547, 264, False), (399.5, 337.5, False), (531.5, 394, False),
            (392, 426, False), (384, 473, False),
        ]),
        (CYAN, [
            (491.5, 282.5, False), (549, 274, False), (593, 285, True),
            (540, 348, False), (548, 343, False), (633, 441, False),
        ]),
        (ORANGE, [
            (230, 88, False), (478, 87, True), (275, 129, True),
            (260, 141, True), (260, 150, True), (354, 166, False),
            (385, 176, False), (485, 175, False), (305, 197, False),
            (212, 191, True), (595, 191, False), (643, 128, False),
            (683, 132, False), (693, 135, False),
        ]),
        (PURPLE, [
            (608, 374, False), (593, 410, False), (749, 405, False),
            (599, 495, False),
        ]),
        (ORANGE_DARK, [
            (176, 74, False), (305, 74, True), (318, 78, True),
        ]),
    ]


def draw_points(fig: Figure) -> None:
    # Carbonate behind BN/EC, and overlapping solvent markers above rules/leaders.
    for color, points in marker_groups():
        for x, y, hollow in points:
            radius = 8.0 if color == ORANGE_DARK and not hollow else 7.45
            fig.marker((x, y), color, hollow=hollow, radius=radius)

    fig.marker((741, 258), BROWN, radius=7.45)
    fig.marker((844, 282), BROWN, radius=7.45)
    fig.marker((884, 253), BROWN, radius=7.45)


def plot_labels() -> list[tuple[tuple[int, int], str]]:
    return [
        ((135, 85), "HXE"), ((216, 68), "HFB"), ((254, 51), "DBTFE"),
        ((344, 71), "DIE"), ((245, 95), "FB135"), ((197, 118), "HTC"),
        ((282, 150), "TBCH"), ((302, 120), "TFMTMS"), ((325, 143), "FB13"),
        ((294, 172), "FB"), ((402, 169), "BZTF"), ((129, 142), "HMDSO"),
        ((130, 221), "TMSDMA"), ((246, 207), "MES"),
        ((483, 50), "TCE"), ((558, 100), "TFEO"), ((563, 135), "BTFEC"),
        ((613, 104), "HFC"), ((651, 108), "DCE"), ((690, 111), "HFCP"),
        ((549, 186), "PFB"), ((590, 206), "TTE"), ((632, 199), "BTFE"),
        ((461, 151), "FB123"),
        ((200, 234), "METMS"), ((267, 235), "TEOS"),
        ((139, 262), "DMMS"), ((258, 258), "DMP"), ((254, 296), "DEE"),
        ((124, 322), "DMES"), ((203, 314), "MTES"), ((170, 337), "MTBE"),
        ((302, 218), "TFPDS"), ((359, 214), "DTDL"), ((406, 222), "DOL"),
        ((401, 247), "FDMB"), ((310, 309), "CPME"), ((357, 297), "EGDBE"),
        ((435, 315), "FEMC"), ((479, 301), "F4DEE"),
        ((199, 365), "1,4-DX"), ((264, 372), "THF"), ((307, 368), "DME"),
        ((343, 356), "DMC"), ((389, 349), "TEB"), ((376, 402), "TMP"),
        ((368, 449), "TEP"),
        ((509, 242), "EDFA"), ((466, 262), "TFSPY"), ((559, 250), "DMTMSA"),
        ((639, 261), "TFEMS"), ((660, 292), "FEC"), ((507, 322), "EMS"),
        ((548, 319), "SL"), ((500, 351), "PC"), ((509, 426), "EA"),
        ((609, 350), "BN"), ((561, 377), "EC"), ((623, 374), "EDPN"),
        ((616, 455), "DMSO"), ((589, 471), "AN"), ((783, 392), "FAN"),
        ((720, 234), "LiTFSI"), ((824, 258), "LiPF6"), ((862, 229), "LiFSI"),
    ]


def draw_labels(fig: Figure) -> None:
    pass


def legend_rows() -> list[tuple[int, tuple[int, int, int], str]]:
    return [
        (69, GREEN, "Silanes"), (126, RED, "Ethers"),
        (186, CARBON, "Carbonates"), (241, (17, 127, 184), "Other Esters"),
        (296, CYAN, "Sulfone"), (351, ORANGE, "Alkanes"),
        (403, (121, 43, 166), "Nitriles"),
    ]


def draw_legend(fig: Figure) -> None:
    for y, color, label in legend_rows():
        fig.marker((927, y), color, radius=7.0)

    fig.square_dash(917, 452, BLACK)
    fig.square_dash(917, 488, (179, 188, 198))
    fig.square_dash(917, 524, (127, 152, 178))


def draw_native_text(image: Image.Image) -> None:
    label_x_offsets = {
        "HXE": 2 / 3,
        "DBTFE": -1 / 3,
        "HTC": 1 / 3,
        "TFMTMS": -1 / 3,
        "FB": 1 / 3,
        "TMSDMA": -1 / 3,
        "TCE": 1 / 3,
        "PFB": 1 / 3,
        "FB123": -1 / 3,
        "METMS": -1 / 3,
        "DMMS": 1 / 3,
        "DMP": 1 / 3,
        "DMES": 1 / 3,
        "TFPDS": 1 / 3,
        "DTDL": -1 / 3,
        "FDMB": -1 / 3,
        "EGDBE": -1 / 3,
        "FEMC": 1 / 3,
        "THF": 1 / 3,
        "DMC": -1 / 3,
        "TMP": -1 / 3,
        "TEP": 1 / 3,
        "TFEMS": -1 / 3,
        "SL": -1 / 3,
        "DMSO": 1 / 3,
        "FAN": 1 / 3,
        "LiPF6": 1 / 3,
    }
    for (x, y), value in plot_labels():
        subpixel_text(image, (x + label_x_offsets.get(value, 0), y + 1), value, size=14)

    subpixel_text(image, (648, 59 + 2 / 3), "≈150 solvents", size=15)
    subpixel_text(image, (51, 41), "a", size=25, font_path=FONT_BOLD)
    legend_specs = {
        "Silanes": (959, 63 + 2 / 3, 17.25),
        "Ethers": (960, 121, 16.75),
        "Carbonates": (960, 179 + 1 / 3, 17.75),
        "Other Esters": (961 + 2 / 3, 236 + 2 / 3, 16.75),
        "Sulfone": (959 + 2 / 3, 290 + 2 / 3, 16.75),
        "Alkanes": (959 + 2 / 3, 346, 17.25),
        "Nitriles": (960 + 1 / 3, 396 + 2 / 3, 17.75),
    }
    for y, _, label in legend_rows():
        x, baseline, size = legend_specs[label]
        subpixel_text(image, (x, baseline), label, size=size)
    subpixel_text(image, (960, 445 + 2 / 3), "LiFSI", size=16.75)
    subpixel_text(image, (959 + 2 / 3, 481 + 2 / 3), "LiTFSI", size=16.75)

    subpixel_text(image, (960, 517), "LiPF", size=16.75)
    legend_font = ImageFont.truetype(str(FONT_REGULAR), round(16.75 * 3))
    suffix_x = 960 + legend_font.getlength("LiPF") / 3 + 0.5
    subpixel_text(image, (suffix_x, 524 + 1 / 3), "6", size=10.5)


def draw_math_title(
    image: Image.Image,
    position: Sequence[float],
    base: str,
    symbol: str,
    *,
    size: float = 17.5,
) -> None:
    x, y = position
    regular = ImageFont.truetype(str(FONT_REGULAR), round(size * 3))
    italic = ImageFont.truetype(str(FONT_ITALIC), round(size * 3))
    subscript = ImageFont.truetype(str(FONT_ITALIC), round(11.25 * 3))
    subpixel_text(image, (x, y), base, size=size)
    x += regular.getlength(base) / 3
    subpixel_text(image, (x, y), symbol, size=size, font_path=FONT_ITALIC)
    x += italic.getlength(symbol) / 3
    subpixel_text(image, (x, y + 6), "s", size=11.25, font_path=FONT_ITALIC)
    x += subscript.getlength("s") / 3 + 1
    subpixel_text(image, (x, y), ")", size=size)


def draw_native_axis_titles(image: Image.Image) -> None:
    draw_math_title(
        image,
        (391 + 2 / 3, 564 + 2 / 3),
        "Normalized anion affinity (",
        "β",
        size=17.75,
    )

    strip = Image.new("RGB", (260, 32), WHITE)
    draw_math_title(strip, (2, 2), "Normalized cation affinity (", "α", size=17.75)
    array = np.asarray(strip)
    mask = np.any(array < 250, axis=2)
    yy, xx = np.where(mask)
    cropped = strip.crop((int(xx.min()), int(yy.min()), int(xx.max()) + 1, int(yy.max()) + 1))
    image.paste(cropped.rotate(90, expand=True), (54, 184))


def draw_native_ticks(image: Image.Image) -> None:
    x_positions = (118, 229, 340, 451, 562, 674, 785, 897)
    x_font = ImageFont.truetype(str(FONT_REGULAR), round(18 * 3))
    for index, center in enumerate(x_positions):
        value = str(index * 5)
        width = x_font.getlength(value) / 3
        subpixel_text(image, (center - width / 2 - 0.5, 539 + 2 / 3), value, size=18)

    y_font = ImageFont.truetype(str(FONT_REGULAR), round(15 * 3))
    for index in range(10):
        value = str(-5 * index)
        width = y_font.getlength(value) / 3
        subpixel_text(image, (104 + 2 / 3 - width, 74 + 50 * index - 5 - 1 / 3), value, size=15)


def sharpen_marker_cores(image: Image.Image) -> None:
    """Restore measured flat-color cores after the Lanczos antialiasing pass."""
    draw = ImageDraw.Draw(image)
    for color, points in marker_groups():
        for x, y, hollow in points:
            box = (round(x - 6.2), round(y - 6.2), round(x + 6.2), round(y + 6.2))
            if hollow:
                draw.ellipse(box, outline=color, width=2)
            else:
                draw.ellipse(box, fill=color)

    for x, y in ((741, 258), (844, 282), (884, 253)):
        draw.ellipse((x - 6, y - 6, x + 6, y + 6), fill=BROWN)
    for y, color, _ in legend_rows():
        draw.ellipse((921, y - 6, 933, y + 6), fill=color)


def sharpen_legend_swatches(image: Image.Image) -> None:
    """Restore the measured square-ended flat cores of the three rule samples."""
    draw = ImageDraw.Draw(image)
    for x in (918, 932, 946):
        draw.rectangle((x, 449, x + 5, 455), fill=BLACK)
    for x0, x1 in ((918, 923), (932, 937), (947, 951)):
        draw.rectangle((x0, 486, x1, 491), fill=(179, 188, 198))
        draw.rectangle((x0, 521, x1, 527), fill=(127, 152, 178))


def sharpen_axes(image: Image.Image) -> None:
    """Match the measured one-pixel axis cores and their pale outside fringe."""
    draw = ImageDraw.Draw(image)
    draw.line((118, 74, 118, 524), fill=(24, 24, 24), width=1)
    draw.line((119, 75, 119, 523), fill=(230, 230, 230), width=1)
    draw.line((118, 524, 897, 524), fill=(56, 56, 56), width=1)
    draw.line((119, 525, 897, 525), fill=(198, 198, 198), width=1)

    for y in range(74, 525, 50):
        draw.line((109, y, 118, y), fill=(44, 44, 44), width=1)
    for x in (118, 229, 340, 451, 562, 674, 785, 897):
        draw.line((x, 524, x, 533), fill=(66, 66, 66), width=1)


def render(output: Path) -> None:
    fig = Figure()
    draw_axes(fig)
    draw_thresholds(fig)
    draw_leaders(fig)
    draw_points(fig)
    draw_labels(fig)
    draw_legend(fig)
    result = fig.image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    sharpen_marker_cores(result)
    sharpen_legend_swatches(result)
    sharpen_axes(result)
    draw_native_text(result)
    draw_native_ticks(result)
    draw_native_axis_titles(result)
    result.save(output, format="PNG", optimize=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).with_name("recreated_solvent_affinity.png"),
        help="Output PNG path (default: next to this script)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    render(args.output)
