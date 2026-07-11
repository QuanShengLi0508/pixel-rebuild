# Mask Strategy

The mask is the proof boundary. A zero-diff rebuild proves only that pixels inside the mask were faithfully exported and re-applied onto the background.

## Good Mask

- Includes all visible data strokes, markers, anti-aliased edges, and small overlap pixels.
- Excludes title, legend text, axis labels, tick labels, and annotation text unless the task explicitly includes them.
- Excludes axis/grid lines unless they were inpainted or modified.
- Uses plot ROI and explicit exclusion rectangles before dilation.

## Workflow

1. Detect colored/black data candidates using RGB threshold rules.
2. Apply include ROI for the plot panel.
3. Apply exclusion ROIs for title, legend, labels, annotations, and axes if needed.
4. Dilate by 1-3 pixels to capture anti-aliased edges and any vector redraw footprint.
5. Save the mask and inspect it visually.
6. Inpaint the masked pixels to create the no-data background.
7. Rebuild from the visual CSV and verify zero-diff.

## Troubleshooting

- If rebuilt image is not zero-diff: the mask missed changed pixels or the background differs outside the mask.
- If the visual CSV is too broad: tighten ROI/exclusions; do not use full-image masks unless the user asks for whole-image pixel data.
- If inpaint artifacts show in final rebuild: those pixels were not exported back into the visual CSV; expand the mask.
- If text appears in the visual data layer: add exclusion rectangles.

