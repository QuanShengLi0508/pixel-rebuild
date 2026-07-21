---
name: pixel-rebuild
description: Recreate raster reference figures as deterministic, standalone Python drawings with matching canvas geometry, flat colors, regions, curves, typography, axes, legends, markers, antialiasing, and image metadata. Use when asked to reproduce, redraw, reverse-engineer, or pixel-match a PNG/JPEG scientific plot, chart, diagram, dashboard, or other mostly vector-like graphic in Python, especially requests containing "1:1", "pixel perfect", "faithful recreation", "Python重绘", or "复刻".
---

# Pixel Rebuild

Reconstruct a raster reference as editable Python drawing code. Treat the image as measurable evidence, reproduce its semantic drawing structure, and iterate against objective image differences.

## Hard requirements

- Produce a standalone Python renderer. Never embed, paste, trace at runtime, or composite pixels from the reference.
- Do not export reference pixels to CSV or hide source fragments in runtime assets. A zero-diff pixel copy is not a reconstruction. A clearly labeled reference/output pair may exist only as README documentation; renderers must never read it.
- Match the reference width, height, mode, and DPI unless the user requests otherwise.
- Make output deterministic with fixed coordinates, colors, font files, seeds, drawing order, and metadata.
- Inspect the native source both visually and programmatically before drawing.
- Continue through implementation, render, comparison, iteration, and verification. Do not stop at analysis or a scaffold.

## Required workflow

1. Locate the source and existing project files. Check for stale or unrelated renderers before editing.
2. View the source at native resolution. Run `scripts/inspect_reference.py` to measure metadata, dominant colors, content bounds, long rows/columns, exact-color bounds, and targeted scanlines.
3. Decompose the image into canvas, frames, coordinate systems, filled regions, curves, symbols, annotations, axes, breaks, and legend rows. Record measured pixel coordinates.
4. Choose the renderer:
   - Prefer Pillow for fixed-layout scientific figures, diagrams, custom markers, and precise layering.
   - Prefer Matplotlib when recovering data transforms matters more than individual pixel placement.
   - Combine them only when one deterministic entry point still controls final rasterization.
5. Build large-to-small: background and flat regions, frames and curves, markers, typography, then antialiasing and metadata.
6. Render at 3x-4x and downsample once with Lanczos when the source is antialiased. Apply native-resolution post-passes only for deliberately measured pixel rows or columns.
7. Run `scripts/compare_reconstruction.py` after every meaningful pass. Inspect the output, overlay, heatmap, binary error mask, global metrics, ROI metrics, and flat-color IoU.
8. Audit optional leaders and annotation strokes instead of assuming they exist. Remove one path at a time and keep it only when its absence raises the local error; for crowded plots, also require grayscale evidence within a 1-2 pixel corridor around the proposed path.
9. Iterate in this order: geometry, missing or invented objects, layering, flat colors, lines/markers, typography, antialiasing fringes.
10. Render twice from clean invocations and compare SHA-256 hashes. Confirm the script runs without the reference file.

## Resources

- Read [references/reconstruction-playbook.md](references/reconstruction-playbook.md) for measurement, coordinate mapping, shapes, typography, legends, and convergence.
- Read [references/pitfalls.md](references/pitfalls.md) before the first implementation pass and again when metrics stop improving.
- Read [references/solvent-affinity-case-study.md](references/solvent-affinity-case-study.md) when reconstructing dense scientific scatter plots. Case 2 documents a real end-to-end result, subpixel text fitting, exact legend swatches, per-line ablation, grayscale line evidence, and the mistakes that produced visually plausible but nonexistent leaders.
- Run `scripts/example_pillow_reconstruction.py` and read it when starting a Pillow renderer. It demonstrates supersampling, log mapping, a broken axis, smooth regions, half-filled markers, composed powers, a structured legend, native post-processing, and DPI preservation.
- Use `scripts/inspect_reference.py` for evidence gathering.
- Use `scripts/compare_reconstruction.py` for numerical and visual QA.
- Use `scripts/audit_line_evidence.py` to screen candidate leaders and annotation strokes against grayscale source-pixel evidence. Treat low support as a review signal, not an automatic deletion rule.

## Typical commands

The bundled tools require Python, Pillow, and NumPy; the complete drawing example itself uses only Pillow. Resolve `SKILL_DIR` to this skill's installed directory:

```bash
python -c "import numpy; from PIL import Image"
python "$SKILL_DIR/scripts/inspect_reference.py" reference.png --top-colors 20 --top-lines 12
python "$SKILL_DIR/scripts/inspect_reference.py" reference.png --crop 150,40,1260,950 --scan-y 56 --scan-x 179
python "$SKILL_DIR/scripts/example_pillow_reconstruction.py" --output example.png
python "$SKILL_DIR/scripts/compare_reconstruction.py" reference.png recreated.png \
  --output-dir comparison \
  --roi plot:179,56,1246,938 \
  --roi legend:1260,60,1397,919 \
  --color 230,230,230 --color 0,0,255
python "$SKILL_DIR/scripts/audit_line_evidence.py" reference.png candidate-paths.json \
  --json line-evidence.json --visualization line-evidence.png
```

## Completion contract

- Deliver the requested `.py` renderer and its generated image.
- Preserve exact requested dimensions, mode, and metadata.
- Include all visible regions, labels, symbols, axes, breaks, borders, and legend entries.
- Do not add leader lines, connector strokes, or decorations without source-pixel evidence.
- Confirm reproducibility and independence from the reference.
- Show the final image inline when supported and link the source and output.
- Report metrics honestly. "1:1" expresses the target and native canvas match; it does not justify claiming byte equality across different font and rasterization engines.
