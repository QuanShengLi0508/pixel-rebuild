# Pitfalls From Real 1:1 Reconstruction Work

Read this before implementation. Revisit the relevant section when progress stalls.

## False success

### Copying pixels proves transport, not reconstruction

Exporting reference pixels to CSV and pasting them onto a background can produce zero RGB difference, but the program has not reconstructed the figure. The same is true for embedding the reference as base64, cropping source fragments, or using the source as a hidden layer.

Require the renderer to succeed after the reference image is temporarily moved away. Output code must describe shapes, text, axes, and data itself.

### An exact-pixel percentage can be dominated by whitespace

A mostly white figure may score highly while every plotted object is wrong. Inspect named ROIs and use color-mask IoU for large flat regions. Treat the global number as one signal, not the acceptance criterion.

## Source and workspace mistakes

### Stale scripts and outputs can look like progress

An existing renderer may target a different image size or an unrelated chart. Before editing, compare its declared canvas, output metadata, and latest generated file with the current reference. Delete or replace obsolete logic deliberately; do not tune the wrong renderer.

### Preview coordinates are not native coordinates

Chat clients, browsers, and image viewers scale large images. Measurements taken from a displayed preview are unreliable. Use the original file, native crops, scanlines, and array indices.

### Scanlines can cross unrelated content

A row chosen to measure a border may intersect labels, ticks, or symbols and create misleading runs. Inspect neighboring rows and use a crop that isolates the component.

## Geometry and rasterization

### Pillow rectangle endpoints are inclusive

`ImageDraw.rectangle((x0, y0, x1, y1))` includes both endpoints. A measured 4-pixel rule can become 5 pixels after a careless coordinate conversion. Check saturated and antialiased coverage on both sides.

### Half-pixel placement changes antialiasing

A one-pixel line centered at an integer and the same line centered at `.5` distribute coverage differently. Keep coordinates as floats until the supersampling helper rounds them. Test nearby half-pixel offsets for long spines and rules.

### Scaling twice creates four-times errors

Do not pass already-scaled points into helpers that scale again. Keep all layout constants in native coordinates and convert only at drawing boundaries.

### Repeated downsampling compounds blur

Draw every supersampled primitive onto one large canvas and downsample once. If an exact native rule is required, apply that single post-pass after downsampling.

### Native post-passes can improve long measured rules

Some reference rules have a specific coverage pattern across four native rows that no convenient high-resolution width reproduces. After the general supersampled render, draw measured native rows or columns explicitly. Use this narrowly; it should not become pixel painting.

### Line caps and joins alter endpoints

Pillow and Matplotlib defaults may use different caps and joins. A curve with the right centerline can still differ at every segment corner. Use rounded endpoint circles or an appropriate path backend when required.

### Smooth shapes need more than an ellipse guess

Large shaded regions often look elliptical but are asymmetric. Sample silhouette landmarks and interpolate a closed curve. Tune the region with exact-color bounds and IoU instead of adjusting by eye alone.

## Color and layering

### Apparent transparency may be a flat overlap color

The source may contain stable RGB blocks where two regions overlap. Repeating the apparent alpha composition can yield different values because of color-space or rounding differences. Sample the overlap and draw that exact fill in the correct layer order.

### Drawing order affects every intersection

Regions, connecting lines, markers, and text must be layered deliberately. Draw fills first, then curves, then marker fills/outlines, then labels. Redraw outlines last where source markers sit on top of connecting lines.

### Color profiles and modes can create invisible mismatches

Convert intentionally to `RGB` or `RGBA`. Do not let palette mode, premultiplied alpha, or an unexpected ICC conversion silently alter comparisons. Compare metadata alongside pixels.

## Axes and coordinate mapping

### Broken axes require piecewise transforms

A hidden numeric interval cannot be represented by one continuous screen transform. Use separate visible rectangles, tick sets, and mappings. Draw the slashes in screen coordinates and verify the spine restarts on the correct row.

### Logarithmic ticks are not evenly spaced in pixels within a decade

Generate minor ticks from `log10(decade * multiplier)`. Do not linearly interpolate multipliers `2..9`.

### Axis labels often need optical offsets

The tick coordinate is a reliable anchor, not necessarily the final text center. Exponents, minus signs, and rotated labels frequently require separate one- or two-pixel offsets.

## Markers and legends

### Filled and hollow markers do not share apparent size automatically

An outline expands on both sides of a nominal path. Hollow markers may need a smaller radius or different outline width to match a filled marker's outer boundary after downsampling.

### Half-filled markers need masks

Drawing a semicircle and then an outline often leaves gaps or double-width edges. Clip the full interior mask to a half-plane, composite the fill, then draw the full outline and divider.

### Shape centers are optical, not always geometric

Triangles and pentagons can appear vertically displaced even with identical bounding-box centers. Store per-shape optical offsets for dense legends.

### Legend rows are a layout table

Do not hand-place each row while eyeballing. Measure the frame, all row centers, symbol anchor, and text anchor. Use the same marker renderer as the plot to avoid small inconsistencies.

## Typography

### A font family name is not a stable rasterizer input

Different machines may resolve `Arial` to different files. Search known font locations, select an actual path, and fail loudly or document the fallback. The exact file, Pillow version, and rasterizer affect fringe pixels.

### Bounding-box centering is not visual centering

Glyph ascenders, descenders, and side bearings produce optical offsets. Use `textbbox` and `textlength`, then tune anchors from native crops.

### Unicode scientific notation can change the font

Superscript and subscript glyphs may come from a fallback font. Compose base, exponent, and chemical subscripts as separate text runs when exact spacing matters.

### Subpixel text fringes may be impossible to clone exactly

References captured from another platform can contain ClearType-like colored fringes. Match font, size, baseline, weight, and grayscale coverage first. Do not spend early iterations chasing individual fringe colors.

## Metadata and validation

### PNG DPI is stored as integer pixels per meter

Saving `dpi=(240, 240)` may read back as approximately `239.9792`. Compare the decoded metadata from both files rather than requiring the input decimal string to survive unchanged.

### The RMSE formula is easy to report incorrectly

Compute `sqrt(mean((reference - output) ** 2))` over all channels. Do not square channel-level RMS values a second time or average incompatible summaries.

### Diagnostics must never resize a mismatch away

Fail when source and output dimensions differ. Resizing one image for comparison hides the most fundamental reconstruction error.

### Determinism must be tested, not assumed

Render twice and compare hashes. Fix uncontrolled random seeds, font fallbacks, time-dependent metadata, and unstable iteration order before delivery.

## Tooling lessons

### Validate the validator environment

The Skill validator requires PyYAML even when the drawing runtime only needs Pillow and NumPy. If validation fails with `ModuleNotFoundError: yaml`, run it in an environment containing PyYAML or install PyYAML into a temporary validation environment. Do not misdiagnose that as a Skill schema error.

### Clean generated bytecode before packaging

Running `py_compile` creates `__pycache__`. Ensure ignore rules cover it and do not commit generated bytecode or diagnostic images.
