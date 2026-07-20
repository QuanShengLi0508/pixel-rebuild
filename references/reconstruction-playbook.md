# Reconstruction Playbook

## Contents

1. Establish the target
2. Measure the source
3. Recover coordinate systems
4. Reconstruct regions and curves
5. Reproduce markers
6. Match typography
7. Rebuild legends
8. Converge efficiently
9. Verify delivery

## 1. Establish the target

Record the source path, dimensions, mode, DPI, and required output path. Work from the native file, never a preview scaled by the chat UI or browser.

Classify the target as one of these:

- a semantic plot with recoverable data coordinates;
- a fixed-layout vector illustration reconstructed in pixel coordinates;
- a hybrid with coordinate-driven plot content and pixel-positioned annotations or legend.

For a one-off raster reference, pixel coordinates are usually the shortest route to fidelity. Define mathematical transforms where they remove repeated manual placement.

Create a component inventory before coding:

| Component | Evidence to record |
|---|---|
| Canvas | width, height, mode, DPI, background |
| Plot frame | left, top, right, bottom, line coverage |
| Regions | flat colors, outline samples, overlaps, layer order |
| Curves | centers, endpoints, width, cap/join style |
| Markers | center, outer size, fill, outline, orientation |
| Text | string, font candidate, size, anchor, baseline |
| Legend | frame, row centers, symbol centers, label anchor |

## 2. Measure the source

Run `inspect_reference.py` first. Use dominant exact colors to identify backgrounds, filled regions, and primary strokes. Antialiased edge colors are normally lower-frequency variants and should not be mistaken for intentional fills.

Use row and column coverage to find long rules, spines, legend boundaries, and axis breaks. Use targeted scanlines on focused crops to determine exact runs. A scan through text produces noisy runs; move it to a clean section of the same border.

Inspect exact-color bounding boxes for region extents. Compare those bounds with the visible antialiased edge: the saturated core and the true geometric boundary are different measurements.

For repeated legend rows, measure all row centers once. Do not assume uniform spacing until first-to-last interpolation agrees with interior rows.

Keep measurements in a compact table or constants block inside the renderer. Label values as native pixels; do not mix them with supersampled coordinates.

## 3. Recover coordinate systems

For logarithmic axes:

```python
from math import log10

def log_map(value, data_min, data_max, pixel_min, pixel_max):
    ratio = (log10(value) - log10(data_min)) / (log10(data_max) - log10(data_min))
    return pixel_min + ratio * (pixel_max - pixel_min)
```

For an upward-growing data axis on a downward-growing canvas, pass the bottom pixel before the top pixel.

For a broken axis, define separate rectangles and separate mapping functions for the visible intervals. Draw the break slashes in screen space. Never force values across the hidden gap through one continuous transform.

Generate logarithmic minor ticks from decades and multipliers `2..9`. Measure tick length, direction, and line width separately for each edge. Position labels independently when optical alignment differs from the tick center.

Use semantic coordinates for points and curves when they can be inferred reliably. Keep annotations and legend layout in native pixels because they are page layout, not data.

## 4. Reconstruct regions and curves

Draw large flat shapes before curves, markers, and text so the compositing order matches the source.

Use these representations:

- sampled polygons for irregular regions;
- closed Catmull-Rom or cubic Bezier outlines for smooth silhouettes;
- dense parametric samples for ellipses and envelopes;
- exact rectangles for frames and flat bands.

At 4x supersampling, route every point, radius, and width through scaling helpers. Downsample only once. Repeated resizing compounds blur and changes flat-color coverage.

When an overlap appears translucent, sample its interior. If it is a stable flat RGB value, draw it as an explicit intersection color instead of alpha blending. Alpha math, color profiles, and rounding often produce a different pixel value.

Line endpoints, caps, and joins matter. Draw explicit endpoint circles when a reference uses round caps but the backend's cap behavior differs.

## 5. Reproduce markers

Create shared functions for circles, squares, diamonds, triangles, pentagons, and compound markers. Accept center, outer size, fill, outline, width, and orientation.

For a half-filled marker:

1. Create the marker interior mask.
2. Intersect it with the requested half-plane.
3. Composite the fill through the clipped mask.
4. Draw the complete outline last.
5. Draw the dividing diameter last when it is visible in the reference.

Measure marker size from the outer antialiased boundary. Hollow markers often require a slightly different radius or outline width from filled markers to preserve the same apparent size after downsampling.

Optical centers are shape-specific. A triangle's bounding-box center is usually below its perceived center; allow a small vertical correction instead of forcing every legend symbol to the row center.

## 6. Match typography

Search installed fonts and render candidates. Match family, weight, point size, glyph width, and rasterization independently. Record the selected font path in the renderer so a fallback does not silently change output.

Use Pillow anchors and `textbbox`/`textlength`, then apply measured optical offsets. A mathematically centered glyph often needs a one-pixel correction.

Compose scientific text as separate runs when necessary:

- base and exponent for powers of ten;
- base text and chemical subscripts;
- axis units with superscripts;
- mixed roman and italic fragments.

Position smaller runs from the measured base bounding box. Unicode superscripts and subscripts can select different glyphs or fallback fonts and change spacing.

Text antialiasing may remain the largest difference after geometry is correct. Match the font and baseline before trying to imitate fringe colors.

## 7. Rebuild legends

Treat the legend as a small table:

- frame bounding box;
- row center list;
- symbol center and reserved width;
- label anchor and font metrics;
- per-row symbol type, fill state, and color.

Reuse the plot's marker functions. Do not implement separate approximate legend icons. Draw the frame independently so long sample lines cannot overwrite its border.

Store entries as data, for example:

```python
entries = [
    {"label": "[110]", "shape": "square", "fill": "solid", "color": BLUE},
    {"label": "[112]", "shape": "circle", "fill": "hollow", "color": BLUE},
]
```

## 8. Converge efficiently

Use global metrics as a compass, then inspect the overlay, heatmap, binary mask, ROI metrics, and flat-color IoU to choose the next edit.

Fix errors in this order:

1. canvas, plot frame, and large region geometry;
2. missing objects and incorrect layering;
3. flat colors and long rules;
4. marker centers, shapes, and widths;
5. labels and legend typography;
6. antialiasing fringes and isolated pixels.

Large white backgrounds inflate exact-pixel percentages. Compare plot, legend, and axes as separate ROIs. Flat-color IoU is more informative than MAE when tuning a large region silhouette.

Keep a single source of truth for coordinates. Small edits should be attributable to a named shape or text item rather than scattered pixel patches.

## 9. Verify delivery

Run the renderer twice from clean invocations and compare SHA-256 hashes. Confirm:

- exact image width and height;
- mode and alpha behavior;
- DPI or other required metadata;
- no runtime read of the reference;
- no clipped text or missing objects;
- correct output path;
- identical repeated output.

Keep diagnostic artifacts outside the requested delivery path unless the user asks for them. Report similarity metrics honestly and show the rendered result.
