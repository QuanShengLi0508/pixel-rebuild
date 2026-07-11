# Output Contract

Deliver these files when possible:

- `source.png`: source image copy.
- `semantic_data.csv`: optional axis-calibrated curve/point data.
- `data_mask.png`: footprint mask for visual data export.
- `no_data_background.png`: source with data layer removed.
- `visual_data_layer_pixels.csv`: per-pixel visual data table.
- `visual_data_layer.png`: transparent preview of the visual pixel data.
- `rebuilt_from_visual_data.png`: image rebuilt from background plus CSV.
- `rebuilt_diff.png`: raw RGB absolute difference image.
- `pixel_rebuild_metrics.json`: numeric verification.
- `rebuild_from_visual_data.py` or command note if a project-local rebuild script is useful.
- `package.zip`: source, scripts, data, images, diff, and metrics.

Minimum metrics:

```json
{
  "image_size": [1217, 884],
  "mean_abs_rgb": 0.0,
  "mse_rgb": 0.0,
  "max_abs_rgb": 0.0,
  "nonzero_diff_pixels": 0,
  "pixel_arrays_equal": true
}
```

User-facing wording:

```text
The visual pixel data layer can rebuild the image 1:1. The rebuilt image has MAE=0, MSE=0, max_abs=0, and 0 nonzero difference pixels versus the source.
```

