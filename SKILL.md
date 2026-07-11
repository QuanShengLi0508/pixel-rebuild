---
name: pixel-rebuild
description: Pixel-level image/plot reconstruction workflow. Use when Codex must extract visual data from a raster plot or figure and prove that exported data can 1:1 rebuild the image, including requests like "数据能够1:1反推图像", "逐像素复刻", "zero-diff", "pixel-level data layer", "视觉数据CSV", or "用数据重建图片并计算误差".
---

# Pixel Rebuild

Use this skill when visual identity matters more than a normal chart redraw. The auditable chain is:

`source image -> no-data background + exported visual data CSV -> rebuilt image -> zero RGB diff`

Keep two data levels separate:

- **Semantic data**: calibrated points/curves extracted from axes. Useful for science but may not reproduce anti-aliasing.
- **Visual pixel data**: per-pixel records `(pixel_x, pixel_y, red, green, blue, alpha)`. Required for exact image rebuilds.

## Workflow

1. Preserve the source image and record its size.
2. Define a data footprint mask for the visible data layer.
3. Create a no-data background by inpainting or otherwise removing only the data footprint.
4. Export visual pixel data from the source image over that footprint.
5. Rebuild the figure from `background + visual_data_pixels.csv`.
6. Verify with pixel metrics.
7. Package source, scripts, semantic CSV, visual CSV, background, rebuilt image, diff images, and metrics.

## Script

Use `scripts/pixel_rebuild.py` for deterministic mask/inpaint/export/rebuild/verify/package commands.

Start with one of these references only when needed:

- `references/commands.md`: ready-to-run command templates.
- `references/mask-strategy.md`: how to create and QA the data footprint mask.
- `references/output-contract.md`: required deliverables and metrics wording.

## Rules

- Treat the mask as the contract: `mask > 0` means "export this source pixel into the visual data CSV."
- Do not claim semantic point data alone proves pixel-perfect anti-aliasing.
- If a pure vector redraw is also produced, save and report it separately from the pixel-level rebuild.
- For a strict 1:1 rebuild, require `mean_abs_rgb=0`, `mse_rgb=0`, `max_abs_rgb=0`, and `nonzero_diff_pixels=0`.

If the user asks whether "the data is right", say explicitly which data level passed:

- semantic points/curves: axis-calibrated numeric data;
- visual pixel layer: exact image-rebuild data.
