# Pixel Rebuild Command Templates

Set the script path:

```bash
PR=/Users/lqs1314/.codex/skills/pixel-rebuild/scripts/pixel_rebuild.py
```

## Full Pipeline When Mask Exists

```bash
python3 "$PR" inpaint \
  --source source.png \
  --mask data_mask.png \
  --out no_data_background.png

python3 "$PR" all \
  --source source.png \
  --mask data_mask.png \
  --background no_data_background.png \
  --csv visual_data_layer_pixels.csv \
  --layer visual_data_layer.png \
  --rebuilt rebuilt_from_visual_data.png \
  --diff rebuilt_diff.png \
  --metrics pixel_rebuild_metrics.json
```

## Generate A Simple RGB Threshold Mask

```bash
python3 "$PR" color-mask \
  --source source.png \
  --out data_mask.png \
  --rule red:170-255,0-120,0-120 \
  --rule green:0-150,80-255,0-180 \
  --rule blue:0-160,0-160,130-255 \
  --rule black:0-80,0-80,0-80 \
  --include-rect 162,54,1156,765 \
  --exclude-rect 420,112,1160,275 \
  --exclude-rect 310,60,980,115 \
  --dilate 2
```

## Separate Steps

```bash
python3 "$PR" export \
  --source source.png \
  --mask data_mask.png \
  --csv visual_data_layer_pixels.csv \
  --layer visual_data_layer.png

python3 "$PR" rebuild \
  --background no_data_background.png \
  --csv visual_data_layer_pixels.csv \
  --out rebuilt_from_visual_data.png

python3 "$PR" verify \
  --source source.png \
  --candidate rebuilt_from_visual_data.png \
  --diff rebuilt_diff.png \
  --metrics pixel_rebuild_metrics.json
```

## Package Outputs

```bash
python3 "$PR" package \
  --out pixel_rebuild_package.zip \
  --root-name pixel_rebuild_package \
  --file source.png \
  --file data_mask.png \
  --file no_data_background.png \
  --file visual_data_layer_pixels.csv \
  --file rebuilt_from_visual_data.png \
  --file rebuilt_diff.png \
  --file pixel_rebuild_metrics.json
```

